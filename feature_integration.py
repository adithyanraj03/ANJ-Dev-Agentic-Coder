#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Feature integration for ANJ DEV terminal."""
import os
import curses
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

class FeatureIntegration:
    """Integration of all features for ANJ DEV terminal."""
    
    def __init__(self, component_registry, config: Dict[str, Any]):
        """Initialize feature integration.
        
        Args:
            component_registry: Component registry
            config: Configuration dictionary
        """
        self.components = component_registry
        self.config = config
        
    def analyze_code(self, filepath: Path, stdscr):
        """Analyze code and provide suggestions.
        
        Args:
            filepath: Path to file to analyze
            stdscr: Curses window for display
        """
        if not filepath.exists():
            self._show_message(stdscr, f"File not found: {filepath}", is_error=True)
            return
            
        # Get file content
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            self._show_message(stdscr, f"Error reading file: {e}", is_error=True)
            return
            
        # Get file extension
        ext = filepath.suffix.lower()
        
        # Determine linter based on file extension
        linter = None
        if ext == '.py':
            linter = self._get_config_value(['refactoring', 'linters', 'python'], ['pylint'])
        elif ext in ('.js', '.jsx'):
            linter = self._get_config_value(['refactoring', 'linters', 'javascript'], ['eslint'])
        elif ext in ('.ts', '.tsx'):
            linter = self._get_config_value(['refactoring', 'linters', 'typescript'], ['tslint'])
            
        if not linter:
            self._show_message(stdscr, f"No linter configured for {ext} files", is_error=True)
            return
            
        # Run linter
        results = []
        for lint_tool in linter:
            if lint_tool == 'pylint':
                try:
                    output = subprocess.check_output(['pylint', '--output-format=text', str(filepath)], 
                                                    stderr=subprocess.STDOUT,
                                                    universal_newlines=True)
                    results.append(('Pylint', output))
                except subprocess.CalledProcessError as e:
                    # Pylint returns non-zero exit code for warnings/errors
                    results.append(('Pylint', e.output))
                except FileNotFoundError:
                    results.append(('Pylint', 'Pylint not installed. Run: pip install pylint'))
            
            elif lint_tool == 'flake8':
                try:
                    output = subprocess.check_output(['flake8', str(filepath)], 
                                                    stderr=subprocess.STDOUT,
                                                    universal_newlines=True)
                    results.append(('Flake8', output))
                except subprocess.CalledProcessError as e:
                    results.append(('Flake8', e.output))
                except FileNotFoundError:
                    results.append(('Flake8', 'Flake8 not installed. Run: pip install flake8'))
            
            elif lint_tool == 'eslint':
                try:
                    output = subprocess.check_output(['eslint', str(filepath)], 
                                                    stderr=subprocess.STDOUT,
                                                    universal_newlines=True)
                    results.append(('ESLint', output))
                except subprocess.CalledProcessError as e:
                    results.append(('ESLint', e.output))
                except FileNotFoundError:
                    results.append(('ESLint', 'ESLint not installed. Run: npm install -g eslint'))
            
            elif lint_tool == 'tslint':
                try:
                    output = subprocess.check_output(['tslint', '-p', '.', str(filepath)], 
                                                    stderr=subprocess.STDOUT,
                                                    universal_newlines=True)
                    results.append(('TSLint', output))
                except subprocess.CalledProcessError as e:
                    results.append(('TSLint', e.output))
                except FileNotFoundError:
                    results.append(('TSLint', 'TSLint not installed. Run: npm install -g tslint'))
        
        # Display results
        self._display_analysis_results(stdscr, filepath, results)
    
    def _display_analysis_results(self, stdscr, filepath: Path, results: List[Tuple[str, str]]):
        """Display analysis results.
        
        Args:
            stdscr: Curses window for display
            filepath: Path to analyzed file
            results: List of (tool_name, output) tuples
        """
        stdscr.clear()
        height, width = stdscr.getmaxyx()
        
        # Draw title
        title = f"Code Analysis: {filepath.name}"
        stdscr.addstr(0, 0, title, curses.color_pair(1) | curses.A_BOLD)
        
        row = 2
        for tool_name, output in results:
            stdscr.addstr(row, 0, f"{tool_name} Results:", curses.color_pair(2) | curses.A_BOLD)
            row += 1
            
            if not output.strip():
                stdscr.addstr(row, 2, "No issues found", curses.color_pair(2))
                row += 1
            else:
                lines = output.split('\n')
                for line in lines:
                    if row >= height - 2:
                        break
                    
                    # Color based on content
                    color = curses.color_pair(1)  # Default
                    if 'error' in line.lower():
                        color = curses.color_pair(4)  # Error
                    elif 'warning' in line.lower():
                        color = curses.color_pair(3)  # Warning
                    
                    # Truncate line if needed
                    if len(line) > width - 2:
                        line = line[:width - 5] + '...'
                        
                    stdscr.addstr(row, 2, line, color)
                    row += 1
            
            row += 1
        
        # Wait for key press
        stdscr.addstr(height - 1, 0, "Press any key to continue...", curses.color_pair(1))
        stdscr.refresh()
        stdscr.getch()
    
    def refactor_code(self, filepath: Path, stdscr):
        """Refactor code.
        
        Args:
            filepath: Path to file to refactor
            stdscr: Curses window for display
        """
        if not filepath.exists():
            self._show_message(stdscr, f"File not found: {filepath}", is_error=True)
            return
            
        # Get file content
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            self._show_message(stdscr, f"Error reading file: {e}", is_error=True)
            return
            
        # Get file extension
        ext = filepath.suffix.lower()
        
        # Determine formatter based on file extension
        formatter = None
        if ext == '.py':
            formatter = self._get_config_value(['refactoring', 'formatter'], 'black')
        elif ext in ('.js', '.jsx', '.ts', '.tsx'):
            formatter = self._get_config_value(['refactoring', 'formatter'], 'prettier')
            
        if not formatter:
            self._show_message(stdscr, f"No formatter configured for {ext} files", is_error=True)
            return
            
        # Run formatter
        if formatter == 'black':
            try:
                subprocess.run(['black', str(filepath)], check=True)
                self._show_message(stdscr, f"Successfully formatted {filepath.name} with Black")
            except subprocess.CalledProcessError as e:
                self._show_message(stdscr, f"Error formatting with Black: {e}", is_error=True)
            except FileNotFoundError:
                self._show_message(stdscr, "Black not installed. Run: pip install black", is_error=True)
        
        elif formatter == 'prettier':
            try:
                subprocess.run(['prettier', '--write', str(filepath)], check=True)
                self._show_message(stdscr, f"Successfully formatted {filepath.name} with Prettier")
            except subprocess.CalledProcessError as e:
                self._show_message(stdscr, f"Error formatting with Prettier: {e}", is_error=True)
            except FileNotFoundError:
                self._show_message(stdscr, "Prettier not installed. Run: npm install -g prettier", is_error=True)
    
    def explain_code(self, filepath: Path, stdscr):
        """Explain code using LLM.
        
        Args:
            filepath: Path to file to explain
            stdscr: Curses window for display
        """
        if not filepath.exists():
            self._show_message(stdscr, f"File not found: {filepath}", is_error=True)
            return
            
        # Get file content
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            self._show_message(stdscr, f"Error reading file: {e}", is_error=True)
            return
            
        # Get LLM handler from components
        llm_handler = self.components.llm_handler
        if not llm_handler:
            self._show_message(stdscr, "LLM handler not available", is_error=True)
            return
            
        # Show loading message
        height, width = stdscr.getmaxyx()
        stdscr.clear()
        stdscr.addstr(0, 0, f"Explaining: {filepath.name}", curses.color_pair(1) | curses.A_BOLD)
        stdscr.addstr(2, 0, "Generating explanation...", curses.color_pair(2))
        stdscr.refresh()
        
        # Generate explanation
        prompt = f"""
        Please explain the following code in a clear and concise manner.
        Focus on:
        1. The overall purpose of the code
        2. Key functions/classes and their roles
        3. Any important algorithms or patterns used
        4. Potential issues or areas for improvement

        ```
        {content}
        ```
        """
        
        explanation = llm_handler.execute_query(prompt)
        
        # Display explanation
        stdscr.clear()
        stdscr.addstr(0, 0, f"Code Explanation: {filepath.name}", curses.color_pair(1) | curses.A_BOLD)
        
        row = 2
        lines = explanation.split('\n')
        for line in lines:
            if row >= height - 2:
                break
                
            # Truncate line if needed
            if len(line) > width - 2:
                # Split into multiple lines
                for i in range(0, len(line), width - 2):
                    if row >= height - 2:
                        break
                    stdscr.addstr(row, 0, line[i:i+width-2], curses.color_pair(1))
                    row += 1
            else:
                stdscr.addstr(row, 0, line, curses.color_pair(1))
                row += 1
        
        # Wait for key press
        stdscr.addstr(height - 1, 0, "Press any key to continue...", curses.color_pair(1))
        stdscr.refresh()
        stdscr.getch()
    
    def show_project_statistics(self, stdscr):
        """Show project statistics.
        
        Args:
            stdscr: Curses window for display
        """
        # Get project root
        project_root = self.components.project_root
        if not project_root or not project_root.exists():
            self._show_message(stdscr, "Project root not found", is_error=True)
            return
            
        # Collect statistics
        stats = {
            'total_files': 0,
            'total_lines': 0,
            'total_size': 0,
            'by_extension': {}
        }
        
        # Walk through project
        for root, dirs, files in os.walk(project_root):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                # Skip hidden files
                if file.startswith('.'):
                    continue
                    
                filepath = Path(root) / file
                
                # Get extension
                ext = filepath.suffix.lower()
                if not ext:
                    ext = '(no extension)'
                    
                # Update stats
                stats['total_files'] += 1
                
                try:
                    # Get file size
                    size = filepath.stat().st_size
                    stats['total_size'] += size
                    
                    # Count lines
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = sum(1 for _ in f)
                        stats['total_lines'] += lines
                        
                    # Update by extension
                    if ext not in stats['by_extension']:
                        stats['by_extension'][ext] = {
                            'files': 0,
                            'lines': 0,
                            'size': 0
                        }
                    
                    stats['by_extension'][ext]['files'] += 1
                    stats['by_extension'][ext]['lines'] += lines
                    stats['by_extension'][ext]['size'] += size
                    
                except Exception:
                    # Skip files that can't be read
                    pass
        
        # Display statistics
        self._display_project_statistics(stdscr, stats)
    
    def _display_project_statistics(self, stdscr, stats: Dict[str, Any]):
        """Display project statistics.
        
        Args:
            stdscr: Curses window for display
            stats: Statistics dictionary
        """
        stdscr.clear()
        height, width = stdscr.getmaxyx()
        
        # Draw title
        title = "Project Statistics"
        stdscr.addstr(0, 0, title, curses.color_pair(1) | curses.A_BOLD)
        
        # Format size
        def format_size(size_bytes):
            if size_bytes < 1024:
                return f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                return f"{size_bytes / 1024:.1f} KB"
            else:
                return f"{size_bytes / (1024 * 1024):.1f} MB"
        
        # Display summary
        row = 2
        stdscr.addstr(row, 0, "Summary:", curses.color_pair(2) | curses.A_BOLD)
        row += 1
        stdscr.addstr(row, 2, f"Total Files: {stats['total_files']}", curses.color_pair(1))
        row += 1
        stdscr.addstr(row, 2, f"Total Lines: {stats['total_lines']}", curses.color_pair(1))
        row += 1
        stdscr.addstr(row, 2, f"Total Size: {format_size(stats['total_size'])}", curses.color_pair(1))
        row += 2
        
        # Display by extension
        stdscr.addstr(row, 0, "By Extension:", curses.color_pair(2) | curses.A_BOLD)
        row += 1
        
        # Sort by number of files
        sorted_exts = sorted(stats['by_extension'].items(), 
                            key=lambda x: x[1]['files'], 
                            reverse=True)
        
        for ext, ext_stats in sorted_exts:
            if row >= height - 2:
                break
                
            stdscr.addstr(row, 2, f"{ext}: {ext_stats['files']} files, {ext_stats['lines']} lines, {format_size(ext_stats['size'])}", curses.color_pair(1))
            row += 1
        
        # Wait for key press
        stdscr.addstr(height - 1, 0, "Press any key to continue...", curses.color_pair(1))
        stdscr.refresh()
        stdscr.getch()
    
    def generate_documentation(self, stdscr):
        """Generate documentation for project.
        
        Args:
            stdscr: Curses window for display
        """
        # Get project root
        project_root = self.components.project_root
        if not project_root or not project_root.exists():
            self._show_message(stdscr, "Project root not found", is_error=True)
            return
            
        # Get documentation format
        doc_format = self._get_config_value(['documentation', 'format'], 'markdown')
        
        # Get output directory
        output_dir = self._get_config_value(['documentation', 'output_dir'], './docs')
        output_path = project_root / output_dir
        
        # Create output directory if it doesn't exist
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Show options
        stdscr.clear()
        height, width = stdscr.getmaxyx()
        
        # Draw title
        title = "Generate Documentation"
        stdscr.addstr(0, 0, title, curses.color_pair(1) | curses.A_BOLD)
        
        row = 2
        stdscr.addstr(row, 0, "Options:", curses.color_pair(2) | curses.A_BOLD)
        row += 1
        stdscr.addstr(row, 2, "1. Generate for entire project", curses.color_pair(1))
        row += 1
        stdscr.addstr(row, 2, "2. Generate for specific file", curses.color_pair(1))
        row += 1
        stdscr.addstr(row, 2, "3. Back", curses.color_pair(1))
        row += 2
        
        stdscr.addstr(row, 0, "Enter your choice (1-3): ", curses.color_pair(2))
        stdscr.refresh()
        
        # Get choice
        choice = stdscr.getch()
        if choice in range(ord('1'), ord('4')):
            choice = int(chr(choice))
        else:
            return
        
        if choice == 1:  # Generate for entire project
            # Show loading message
            stdscr.clear()
            stdscr.addstr(0, 0, "Generating Documentation", curses.color_pair(1) | curses.A_BOLD)
            stdscr.addstr(2, 0, "This may take a while...", curses.color_pair(2))
            stdscr.refresh()
            
            # Generate documentation
            if doc_format == 'markdown':
                self._generate_markdown_docs(project_root, output_path, stdscr)
            else:
                self._show_message(stdscr, f"Documentation format '{doc_format}' not supported", is_error=True)
                
        elif choice == 2:  # Generate for specific file
            # Use file browser to select file
            file_browser = self.components.get_editor('browser')
            if file_browser:
                file_browser.run()
                selected_file = file_browser.selected_file
                if selected_file:
                    # Generate documentation for file
                    if doc_format == 'markdown':
                        self._generate_markdown_doc_for_file(selected_file, output_path, stdscr)
                    else:
                        self._show_message(stdscr, f"Documentation format '{doc_format}' not supported", is_error=True)
    
    def _generate_markdown_docs(self, project_root: Path, output_path: Path, stdscr):
        """Generate markdown documentation for project.
        
        Args:
            project_root: Project root directory
            output_path: Output directory
            stdscr: Curses window for display
        """
        # Create index.md
        index_path = output_path / 'index.md'
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(f"# Project Documentation\n\n")
            f.write(f"Generated documentation for project at {project_root}\n\n")
            f.write(f"## Files\n\n")
            
            # Walk through project
            for root, dirs, files in os.walk(project_root):
                # Skip hidden directories
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                
                # Skip output directory
                rel_path = Path(root).relative_to(project_root)
                if str(rel_path).startswith(str(output_path.relative_to(project_root))):
                    continue
                
                for file in files:
                    # Skip hidden files
                    if file.startswith('.'):
                        continue
                        
                    filepath = Path(root) / file
                    rel_filepath = filepath.relative_to(project_root)
                    
                    # Only document source code files
                    ext = filepath.suffix.lower()
                    if ext not in ('.py', '.js', '.jsx', '.ts', '.tsx', '.html', '.css', '.md'):
                        continue
                        
                    # Add to index
                    f.write(f"- [{rel_filepath}]({rel_filepath}.md)\n")
                    
                    # Generate documentation for file
                    self._generate_markdown_doc_for_file(filepath, output_path, stdscr)
        
        self._show_message(stdscr, f"Documentation generated at {output_path}")
    
    def _generate_markdown_doc_for_file(self, filepath: Path, output_path: Path, stdscr):
        """Generate markdown documentation for file.
        
        Args:
            filepath: Path to file
            output_path: Output directory
            stdscr: Curses window for display
        """
        try:
            # Read file content
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Get LLM handler from components
            llm_handler = self.components.llm_handler
            if not llm_handler:
                self._show_message(stdscr, "LLM handler not available", is_error=True)
                return
                
            # Generate documentation
            prompt = f"""
            Please generate markdown documentation for the following code.
            Include:
            1. A title with the filename
            2. A brief description of the file's purpose
            3. Documentation for classes, functions, and methods
            4. Any important notes or caveats

            ```
            {content}
            ```
            
            Format the output as clean markdown.
            """
            
            documentation = llm_handler.execute_query(prompt)
            
            # Create output file
            rel_filepath = filepath.relative_to(self.components.project_root)
            doc_path = output_path / f"{rel_filepath}.md"
            doc_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(doc_path, 'w', encoding='utf-8') as f:
                f.write(documentation)
                
            return True
            
        except Exception as e:
            self._show_message(stdscr, f"Error generating documentation for {filepath}: {e}", is_error=True)
            return False
    
    def _get_config_value(self, path: List[str], default=None):
        """Get value from config.
        
        Args:
            path: Path to value in config
            default: Default value if not found
            
        Returns:
            Config value or default
        """
        value = self.config
        for key in path:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    def _show_message(self, stdscr, message: str, is_error: bool = False):
        """Show message on screen.
        
        Args:
            stdscr: Curses window for display
            message: Message to display
            is_error: Whether message is an error
        """
        stdscr.clear()
        height, width = stdscr.getmaxyx()
        
        # Draw title
        title = "Error" if is_error else "Message"
        stdscr.addstr(0, 0, title, curses.color_pair(4 if is_error else 1) | curses.A_BOLD)
        
        # Draw message
        row = 2
        lines = message.split('\n')
        for line in lines:
            if row >= height - 2:
                break
                
            # Truncate line if needed
            if len(line) > width - 2:
                # Split into multiple lines
                for i in range(0, len(line), width - 2):
                    if row >= height - 2:
                        break
                    stdscr.addstr(row, 0, line[i:i+width-2], 
                                curses.color_pair(4 if is_error else 1))
                    row += 1
            else:
                stdscr.addstr(row, 0, line, curses.color_pair(4 if is_error else 1))
                row += 1
        
        # Wait for key press
        stdscr.addstr(height - 1, 0, "Press any key to continue...", 
                    curses.color_pair(1))
        stdscr.refresh()
        stdscr.getch()