#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test framework for generating and running tests."""
import os
import sys
import re
import ast
import inspect
import importlib
import importlib.util
import subprocess
import curses
import threading
import time
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Set, Union, Callable

class TestManager:
    """Manages test generation and execution."""
    
    def __init__(self, project_root: Path, llm_handler, stdscr=None):
        """Initialize test manager.
        
        Args:
            project_root: Project root directory
            llm_handler: LLM handler for test generation
            stdscr: Optional curses window for display
        """
        self.project_root = project_root
        self.llm_handler = llm_handler
        self.stdscr = stdscr
        self.test_runners = {
            'pytest': self._run_pytest,
            'unittest': self._run_unittest,
            'jest': self._run_jest,
            'mocha': self._run_mocha
        }
        
        # Test state
        self.test_results = {}
        self.current_test_run = None
        self.test_output_buffer = []
        
        # Detect test framework
        self.detected_frameworks = self._detect_test_frameworks()
        self.primary_framework = self._get_primary_framework()
        
        # Color pairs
        if stdscr:
            self.colors = {
                "normal": curses.color_pair(0),
                "title": curses.color_pair(1) | curses.A_BOLD,
                "success": curses.color_pair(2) | curses.A_BOLD,
                "error": curses.color_pair(3) | curses.A_BOLD,
                "warning": curses.color_pair(3),
                "info": curses.color_pair(1),
            }
    
    def _detect_test_frameworks(self) -> Dict[str, bool]:
        """Detect available test frameworks.
        
        Returns:
            Dict[str, bool]: Dictionary of framework availability
        """
        frameworks = {
            'pytest': False,
            'unittest': False,
            'jest': False,
            'mocha': False
        }
        
        # Check for pytest
        if (self.project_root / 'pytest.ini').exists() or (self.project_root / 'conftest.py').exists():
            frameworks['pytest'] = True
        elif list(self.project_root.glob('**/test_*.py')) or list(self.project_root.glob('**/*_test.py')):
            frameworks['pytest'] = True
            
        # Check for unittest
        if list(self.project_root.glob('**/test*.py')):
            frameworks['unittest'] = True
            
        # Check for Jest
        if (self.project_root / 'jest.config.js').exists() or (self.project_root / 'package.json').exists():
            try:
                with open(self.project_root / 'package.json', 'r') as f:
                    import json
                    package_json = json.load(f)
                    if 'jest' in package_json.get('devDependencies', {}) or 'jest' in package_json.get('dependencies', {}):
                        frameworks['jest'] = True
            except:
                pass
                
        # Check for Mocha
        if (self.project_root / 'mocha.opts').exists() or (self.project_root / '.mocharc.js').exists() or (self.project_root / '.mocharc.json').exists():
            frameworks['mocha'] = True
        elif (self.project_root / 'package.json').exists():
            try:
                with open(self.project_root / 'package.json', 'r') as f:
                    import json
                    package_json = json.load(f)
                    if 'mocha' in package_json.get('devDependencies', {}) or 'mocha' in package_json.get('dependencies', {}):
                        frameworks['mocha'] = True
            except:
                pass
                
        return frameworks
    
    def _get_primary_framework(self) -> Optional[str]:
        """Get primary test framework.
        
        Returns:
            Optional[str]: Primary framework name
        """
        # Prioritize frameworks
        for framework in ['pytest', 'jest', 'mocha', 'unittest']:
            if self.detected_frameworks.get(framework, False):
                return framework
                
        # Default to pytest for Python projects, jest for JS projects
        if list(self.project_root.glob('**/*.py')):
            return 'pytest'
        elif list(self.project_root.glob('**/*.js')) or list(self.project_root.glob('**/*.ts')):
            return 'jest'
            
        return None
    
    def _analyze_python_file(self, filepath: Path) -> Dict[str, Any]:
        """Analyze Python file for test generation.
        
        Args:
            filepath: Path to Python file
            
        Returns:
            Dict[str, Any]: Analysis results
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                code = f.read()
                
            # Parse AST
            tree = ast.parse(code)
            
            # Extract classes and functions
            classes = []
            functions = []
            imports = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    methods = []
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            methods.append({
                                'name': item.name,
                                'args': [arg.arg for arg in item.args.args if arg.arg != 'self'],
                                'decorators': [d.id for d in item.decorator_list if isinstance(d, ast.Name)],
                                'is_async': isinstance(item, ast.AsyncFunctionDef),
                                'docstring': ast.get_docstring(item)
                            })
                            
                    classes.append({
                        'name': node.name,
                        'methods': methods,
                        'decorators': [d.id for d in node.decorator_list if isinstance(d, ast.Name)],
                        'bases': [base.id for base in node.bases if isinstance(base, ast.Name)],
                        'docstring': ast.get_docstring(node)
                    })
                elif isinstance(node, ast.FunctionDef) and node.parent_field != 'body':
                    functions.append({
                        'name': node.name,
                        'args': [arg.arg for arg in node.args.args],
                        'decorators': [d.id for d in node.decorator_list if isinstance(d, ast.Name)],
                        'is_async': isinstance(node, ast.AsyncFunctionDef),
                        'docstring': ast.get_docstring(node)
                    })
                elif isinstance(node, ast.Import):
                    for name in node.names:
                        imports.append(name.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        for name in node.names:
                            imports.append(f"{node.module}.{name.name}")
                            
            return {
                'classes': classes,
                'functions': functions,
                'imports': imports,
                'module_docstring': ast.get_docstring(tree)
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'classes': [],
                'functions': [],
                'imports': [],
                'module_docstring': None
            }
    
    def _analyze_js_file(self, filepath: Path) -> Dict[str, Any]:
        """Analyze JavaScript/TypeScript file for test generation.
        
        Args:
            filepath: Path to JS/TS file
            
        Returns:
            Dict[str, Any]: Analysis results
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                code = f.read()
                
            # Simple regex-based analysis (not as robust as AST)
            classes = []
            functions = []
            imports = []
            
            # Extract imports
            import_patterns = [
                r'import\s+{\s*([^}]+)\s*}\s+from\s+[\'"]([^\'"]+)[\'"]',  # import { x } from 'y'
                r'import\s+(\w+)\s+from\s+[\'"]([^\'"]+)[\'"]',  # import x from 'y'
                r'const\s+{\s*([^}]+)\s*}\s*=\s*require\([\'"]([^\'"]+)[\'"]\)',  # const { x } = require('y')
                r'const\s+(\w+)\s*=\s*require\([\'"]([^\'"]+)[\'"]\)'  # const x = require('y')
            ]
            
            for pattern in import_patterns:
                for match in re.finditer(pattern, code):
                    if len(match.groups()) >= 2:
                        imports.append(f"{match.group(2)}: {match.group(1)}")
                        
            # Extract classes
            class_pattern = r'class\s+(\w+)(?:\s+extends\s+(\w+))?\s*{'
            for match in re.finditer(class_pattern, code):
                class_name = match.group(1)
                base_class = match.group(2) if match.group(2) else None
                
                # Find methods in class
                class_start = match.end()
                brace_count = 1
                class_end = class_start
                
                for i in range(class_start, len(code)):
                    if code[i] == '{':
                        brace_count += 1
                    elif code[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            class_end = i
                            break
                            
                class_code = code[class_start:class_end]
                
                # Extract methods
                method_pattern = r'(?:async\s+)?(?:static\s+)?(\w+)\s*\(([^)]*)\)'
                methods = []
                
                for method_match in re.finditer(method_pattern, class_code):
                    method_name = method_match.group(1)
                    if method_name not in ('constructor', 'get', 'set'):
                        args = [arg.strip() for arg in method_match.group(2).split(',') if arg.strip()]
                        methods.append({
                            'name': method_name,
                            'args': args,
                            'is_async': 'async' in method_match.group(0)
                        })
                        
                classes.append({
                    'name': class_name,
                    'methods': methods,
                    'bases': [base_class] if base_class else []
                })
                
            # Extract functions
            function_patterns = [
                r'function\s+(\w+)\s*\(([^)]*)\)',  # function x(...)
                r'const\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>',  # const x = (...) =>
                r'const\s+(\w+)\s*=\s*function\s*\([^)]*\)'  # const x = function(...)
            ]
            
            for pattern in function_patterns:
                for match in re.finditer(pattern, code):
                    func_name = match.group(1)
                    args = []
                    if len(match.groups()) > 1:
                        args = [arg.strip() for arg in match.group(2).split(',') if arg.strip()]
                        
                    functions.append({
                        'name': func_name,
                        'args': args,
                        'is_async': 'async' in match.group(0)
                    })
                    
            return {
                'classes': classes,
                'functions': functions,
                'imports': imports
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'classes': [],
                'functions': [],
                'imports': []
            }
    
    def generate_tests(self, filepath: Path) -> Optional[str]:
        """Generate tests for file.
        
        Args:
            filepath: Path to file
            
        Returns:
            Optional[str]: Generated test code
        """
        if not filepath.exists():
            self._log(f"File not found: {filepath}", "error")
            return None
            
        # Analyze file based on type
        if filepath.suffix.lower() in ('.py'):
            analysis = self._analyze_python_file(filepath)
            framework = self.primary_framework if self.primary_framework in ('pytest', 'unittest') else 'pytest'
        elif filepath.suffix.lower() in ('.js', '.ts', '.jsx', '.tsx'):
            analysis = self._analyze_js_file(filepath)
            framework = self.primary_framework if self.primary_framework in ('jest', 'mocha') else 'jest'
        else:
            self._log(f"Unsupported file type: {filepath.suffix}", "error")
            return None
            
        # Read file content
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                file_content = f.read()
        except Exception as e:
            self._log(f"Error reading file: {e}", "error")
            return None
            
        # Generate tests using LLM
        prompt = self._create_test_generation_prompt(filepath, file_content, analysis, framework)
        
        self._log(f"Generating tests for {filepath.name}...", "info")
        response = self.llm_handler.execute_query(prompt)
        
        if not response:
            self._log("Failed to generate tests", "error")
            return None
            
        # Extract code blocks
        test_code = self._extract_test_code(response)
        
        if not test_code:
            self._log("No test code found in response", "error")
            return None
            
        self._log(f"Generated tests for {filepath.name}", "success")
        return test_code
    
    def _create_test_generation_prompt(self, filepath: Path, content: str, analysis: Dict[str, Any], framework: str) -> str:
        """Create prompt for test generation.
        
        Args:
            filepath: Path to file
            content: File content
            analysis: File analysis results
            framework: Test framework to use
            
        Returns:
            str: Test generation prompt
        """
        # Base prompt
        prompt = f"Generate tests for the following {filepath.suffix} file using {framework}.\n\n"
        prompt += f"File: {filepath.name}\n\n"
        prompt += f"Content:\n```{filepath.suffix}\n{content}\n```\n\n"
        
        # Add analysis
        prompt += "Analysis:\n"
        if 'classes' in analysis and analysis['classes']:
            prompt += "Classes:\n"
            for cls in analysis['classes']:
                prompt += f"- {cls['name']}"
                if 'bases' in cls and cls['bases']:
                    prompt += f" (extends {', '.join(cls['bases'])})"
                prompt += "\n"
                
                if 'methods' in cls and cls['methods']:
                    for method in cls['methods']:
                        prompt += f"  - {method['name']}({', '.join(method.get('args', []))})"
                        if method.get('is_async'):
                            prompt += " (async)"
                        prompt += "\n"
                        
        if 'functions' in analysis and analysis['functions']:
            prompt += "Functions:\n"
            for func in analysis['functions']:
                prompt += f"- {func['name']}({', '.join(func.get('args', []))})"
                if func.get('is_async'):
                    prompt += " (async)"
                prompt += "\n"
                
        # Framework-specific instructions
        if framework == 'pytest':
            prompt += "\nGenerate pytest tests with the following guidelines:\n"
            prompt += "- Use pytest fixtures where appropriate\n"
            prompt += "- Include test cases for normal operation and edge cases\n"
            prompt += "- Use descriptive test names with test_ prefix\n"
            prompt += "- Include docstrings explaining what each test does\n"
            prompt += "- Use assert statements with clear error messages\n"
            prompt += "- Use mocks or patches for external dependencies\n"
            
        elif framework == 'unittest':
            prompt += "\nGenerate unittest tests with the following guidelines:\n"
            prompt += "- Create a test class that extends unittest.TestCase\n"
            prompt += "- Include setUp and tearDown methods if needed\n"
            prompt += "- Use descriptive test method names with test_ prefix\n"
            prompt += "- Include docstrings explaining what each test does\n"
            prompt += "- Use self.assert* methods for assertions\n"
            prompt += "- Use self.mock or unittest.mock for mocking\n"
            
        elif framework == 'jest':
            prompt += "\nGenerate Jest tests with the following guidelines:\n"
            prompt += "- Use describe blocks to group related tests\n"
            prompt += "- Use it or test functions with descriptive names\n"
            prompt += "- Include comments explaining what each test does\n"
            prompt += "- Use expect assertions with clear matchers\n"
            prompt += "- Use jest.mock for mocking dependencies\n"
            prompt += "- Use beforeEach/afterEach for setup/teardown\n"
            
        elif framework == 'mocha':
            prompt += "\nGenerate Mocha tests with the following guidelines:\n"
            prompt += "- Use describe blocks to group related tests\n"
            prompt += "- Use it functions with descriptive names\n"
            prompt += "- Include comments explaining what each test does\n"
            prompt += "- Use chai assertions (expect or should style)\n"
            prompt += "- Use sinon for mocking and spying\n"
            prompt += "- Use before/after hooks for setup/teardown\n"
            
        # Output format
        prompt += f"\nProvide the complete test file as a single code block. The test filename should follow the convention for {framework}.\n"
        prompt += f"For example, if the file is named example.py, the test file should be named test_example.py for pytest.\n"
        prompt += "Include all necessary imports and setup code.\n\n"
        prompt += f"```test_{filepath.stem}{filepath.suffix}\n<Your test code here>\n```"
        
        return prompt
    
    def _extract_test_code(self, response: str) -> Optional[str]:
        """Extract test code from LLM response.
        
        Args:
            response: LLM response
            
        Returns:
            Optional[str]: Extracted test code
        """
        # Look for code block
        code_block_pattern = r'```(?:.*?)\n(.*?)```'
        matches = re.findall(code_block_pattern, response, re.DOTALL)
        
        if matches:
            return matches[0].strip()
            
        return None
    
    def run_tests(self, test_files: Optional[List[Path]] = None) -> Dict[str, Any]:
        """Run tests.
        
        Args:
            test_files: Optional list of test files to run
            
        Returns:
            Dict[str, Any]: Test results
        """
        if not self.primary_framework:
            self._log("No test framework detected", "error")
            return {'success': False, 'error': "No test framework detected"}
            
        # Clear previous results
        self.test_results = {}
        self.test_output_buffer = []
        
        # Run tests using appropriate runner
        runner = self.test_runners.get(self.primary_framework)
        if not runner:
            self._log(f"No test runner for {self.primary_framework}", "error")
            return {'success': False, 'error': f"No test runner for {self.primary_framework}"}
            
        self._log(f"Running tests with {self.primary_framework}...", "info")
        
        # Run tests
        self.current_test_run = threading.Thread(
            target=runner,
            args=(test_files,),
            daemon=True
        )
        self.current_test_run.start()
        
        # Wait for tests to complete
        while self.current_test_run.is_alive():
            time.sleep(0.1)
            
        self._log("Tests completed", "info")
        return self.test_results
    
    def _run_pytest(self, test_files: Optional[List[Path]] = None):
        """Run tests with pytest.
        
        Args:
            test_files: Optional list of test files to run
        """
        try:
            import pytest
            
            # Prepare arguments
            args = ['-v']
            
            # Add test files if specified
            if test_files:
                args.extend([str(f) for f in test_files])
            else:
                # Run all tests
                args.append(str(self.project_root))
                
            # Add output capture
            args.extend(['-s'])
            
            # Run pytest
            result = pytest.main(args)
            
            # Process result
            success = result == 0
            self.test_results = {
                'success': success,
                'framework': 'pytest',
                'output': self.test_output_buffer,
                'exit_code': result
            }
            
        except ImportError:
            # Pytest not installed, try using subprocess
            self._run_test_command(['pytest', '-v'] + ([str(f) for f in test_files] if test_files else []))
        except Exception as e:
            self.test_results = {
                'success': False,
                'framework': 'pytest',
                'error': str(e),
                'output': self.test_output_buffer
            }
    
    def _run_unittest(self, test_files: Optional[List[Path]] = None):
        """Run tests with unittest.
        
        Args:
            test_files: Optional list of test files to run
        """
        try:
            import unittest
            
            # Create test suite
            suite = unittest.TestSuite()
            
            if test_files:
                # Add specified test files
                for test_file in test_files:
                    # Convert path to module name
                    module_name = str(test_file.relative_to(self.project_root)).replace('/', '.').replace('\\', '.')
                    if module_name.endswith('.py'):
                        module_name = module_name[:-3]
                        
                    # Import module
                    spec = importlib.util.spec_from_file_location(module_name, test_file)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Add tests from module
                    for name, obj in inspect.getmembers(module):
                        if name.startswith('Test') and inspect.isclass(obj):
                            suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(obj))
            else:
                # Discover all tests
                suite = unittest.defaultTestLoader.discover(str(self.project_root))
                
            # Run tests
            runner = unittest.TextTestRunner(verbosity=2)
            result = runner.run(suite)
            
            # Process result
            success = result.wasSuccessful()
            self.test_results = {
                'success': success,
                'framework': 'unittest',
                'output': self.test_output_buffer,
                'tests_run': result.testsRun,
                'failures': len(result.failures),
                'errors': len(result.errors)
            }
            
        except Exception as e:
            # Unittest failed, try using subprocess
            self._run_test_command(['python', '-m', 'unittest', 'discover'] + ([str(f) for f in test_files] if test_files else []))
    
    def _run_jest(self, test_files: Optional[List[Path]] = None):
        """Run tests with Jest.
        
        Args:
            test_files: Optional list of test files to run
        """
        # Jest can only be run via command line
        cmd = ['npx', 'jest']
        
        if test_files:
            cmd.extend([str(f) for f in test_files])
            
        self._run_test_command(cmd)
    
    def _run_mocha(self, test_files: Optional[List[Path]] = None):
        """Run tests with Mocha.
        
        Args:
            test_files: Optional list of test files to run
        """
        # Mocha can only be run via command line
        cmd = ['npx', 'mocha']
        
        if test_files:
            cmd.extend([str(f) for f in test_files])
        else:
            # Default pattern
            cmd.append('test/**/*.js')
            
        self._run_test_command(cmd)
    
    def _run_test_command(self, command: List[str]):
        """Run test command and capture output.
        
        Args:
            command: Command to run
        """
        try:
            # Run command
            process = subprocess.Popen(
                command,
                cwd=str(self.project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            # Capture output
            stdout, stderr = process.communicate()
            
            # Add output to buffer
            for line in stdout.splitlines():
                self.test_output_buffer.append(('stdout', line))
                
            for line in stderr.splitlines():
                self.test_output_buffer.append(('stderr', line))
                
            # Process result
            success = process.returncode == 0
            self.test_results = {
                'success': success,
                'framework': command[0],
                'output': self.test_output_buffer,
                'exit_code': process.returncode
            }
            
        except Exception as e:
            self.test_results = {
                'success': False,
                'framework': command[0],
                'error': str(e),
                'output': self.test_output_buffer
            }
    
    def _log(self, message: str, level: str = "info"):
        """Log message.
        
        Args:
            message: Message to log
            level: Log level
        """
        if self.stdscr:
            try:
                height, width = self.stdscr.getmaxyx()
                
                # Get color for level
                color = self.colors.get(level, self.colors["normal"])
                
                # Clear status line
                self.stdscr.move(height - 1, 0)
                self.stdscr.clrtoeol()
                
                # Show message
                self.stdscr.addstr(height - 1, 0, message, color)
                self.stdscr.refresh()
                
            except curses.error:
                pass
        else:
            print(f"[{level.upper()}] {message}")
    
    def get_test_coverage(self, test_files: Optional[List[Path]] = None) -> Dict[str, Any]:
        """Get test coverage.
        
        Args:
            test_files: Optional list of test files to run
            
        Returns:
            Dict[str, Any]: Coverage results
        """
        if self.primary_framework in ('pytest', 'unittest'):
            return self._get_python_coverage(test_files)
        elif self.primary_framework in ('jest', 'mocha'):
            return self._get_js_coverage(test_files)
        else:
            return {'error': 'Unsupported framework for coverage'}
    
    def _get_python_coverage(self, test_files: Optional[List[Path]] = None) -> Dict[str, Any]:
        """Get Python test coverage.
        
        Args:
            test_files: Optional list of test files to run
            
        Returns:
            Dict[str, Any]: Coverage results
        """
        try:
            # Try to import coverage
            import coverage
            
            # Create coverage object
            cov = coverage.Coverage()
            
            # Start coverage
            cov.start()
            
            # Run tests
            self.run_tests(test_files)
            
            # Stop coverage
            cov.stop()
            
            # Get coverage data
            cov.save()
            data = cov.get_data()
            
            # Calculate coverage
            total_lines = 0
            covered_lines = 0
            
            for filename in data.measured_files():
                # Skip test files
                if 'test_' in filename or '_test' in filename:
                    continue
                    
                # Get line coverage
                file_lines = len(open(filename, 'rb').readlines())
                file_covered = len(data.lines(filename))
                
                total_lines += file_lines
                covered_lines += file_covered
                
            # Calculate percentage
            percentage = (covered_lines / total_lines * 100) if total_lines > 0 else 0
            
            return {
                'success': True,
                'percentage': percentage,
                'covered_lines': covered_lines,
                'total_lines': total_lines,
                'files': len(data.measured_files())
            }
            
        except ImportError:
            # Coverage not installed, try using subprocess
            return self._run_coverage_command(['coverage', 'run', '-m', 'pytest'] + ([str(f) for f in test_files] if test_files else []))
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_js_coverage(self, test_files: Optional[List[Path]] = None) -> Dict[str, Any]:
        """Get JavaScript test coverage.
        
        Args:
            test_files: Optional list of test files to run
            
        Returns:
            Dict[str, Any]: Coverage results
        """
        # Jest has built-in coverage
        if self.primary_framework == 'jest':
            cmd = ['npx', 'jest', '--coverage']
        else:
            # Mocha with nyc
            cmd = ['npx', 'nyc', 'mocha']
            
        if test_files:
            cmd.extend([str(f) for f in test_files])
            
        return self._run_coverage_command(cmd)
    
    def _run_coverage_command(self, command: List[str]) -> Dict[str, Any]:
        """Run coverage command and parse results.
        
        Args:
            command: Command to run
            
        Returns:
            Dict[str, Any]: Coverage results
        """
        try:
            # Run command
            process = subprocess.Popen(
                command,
                cwd=str(self.project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Capture output
            stdout, stderr = process.communicate()
            
            # Parse coverage output
            coverage_pattern = r'TOTAL\s+\d+\s+\d+\s+(\d+(?:\.\d+)?)%'
            match = re.search(coverage_pattern, stdout)
            
            if match:
                percentage = float(match.group(1))
                return {
                    'success': True,
                    'percentage': percentage,
                    'output': stdout
                }
            else:
                return {
                    'success': False,
                    'error': 'Could not parse coverage output',
                    'output': stdout
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def cleanup(self):
        """Clean up resources."""
        # Stop any running test
        if self.current_test_run and self.current_test_run.is_alive():
            # Can't really stop a thread, but we can set a flag
            self._log("Stopping test run...", "warning")
            
    def generate_and_run_tests(self, filepath: Path) -> Dict[str, Any]:
        """Generate and run tests for a file.
        
        Args:
            filepath: Path to file
            
        Returns:
            Dict[str, Any]: Test results
        """
        # Generate tests
        test_code = self.generate_tests(filepath)
        if not test_code:
            return {'success': False, 'error': 'Failed to generate tests'}
            
        # Determine test file path
        if filepath.suffix.lower() in ('.py'):
            test_file = filepath.parent / f"test_{filepath.stem}.py"
        elif filepath.suffix.lower() in ('.js', '.ts'):
            test_file = filepath.parent / f"{filepath.stem}.test{filepath.suffix}"
        else:
            return {'success': False, 'error': f"Unsupported file type: {filepath.suffix}"}
            
        # Write test file
        try:
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write(test_code)
        except Exception as e:
            return {'success': False, 'error': f"Failed to write test file: {e}"}
            
        # Run tests
        self._log(f"Running generated tests for {filepath.name}...", "info")
        return self.run_tests([test_file])
    
    def get_test_files(self) -> List[Path]:
        """Get all test files in project.
        
        Returns:
            List[Path]: List of test files
        """
        test_files = []
        
        # Python test files
        test_files.extend(self.project_root.glob('**/test_*.py'))
        test_files.extend(self.project_root.glob('**/*_test.py'))
        
        # JavaScript test files
        test_files.extend(self.project_root.glob('**/*.test.js'))
        test_files.extend(self.project_root.glob('**/*.spec.js'))
        
        # TypeScript test files
        test_files.extend(self.project_root.glob('**/*.test.ts'))
        test_files.extend(self.project_root.glob('**/*.spec.ts'))
        
        return test_files
    
    def get_test_summary(self) -> Dict[str, Any]:
        """Get summary of test status.
        
        Returns:
            Dict[str, Any]: Test summary
        """
        test_files = self.get_test_files()
        
        return {
            'framework': self.primary_framework,
            'test_files': len(test_files),
            'available_frameworks': [
                framework for framework, available in self.detected_frameworks.items()
                if available
            ]
        }
