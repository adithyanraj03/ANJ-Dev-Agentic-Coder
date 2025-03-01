#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import json
import requests
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List, Set, Tuple, Union
import time
from datetime import datetime
import re
import subprocess
import sys

# Force UTF-8 encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
if sys.stderr.encoding != 'utf-8':
    sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', buffering=1)

from agetic_ui import AgeticUI
from dependencies import (
    parse_dependencies,
    format_dependencies,
    load_base_requirements,
    merge_dependencies
)

def load_json_file(file_path: Path) -> Dict[str, Any]:
    """Load a JSON file with proper encoding."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except UnicodeDecodeError:
        # Fallback to system encoding if UTF-8 fails
        with open(file_path, 'r') as f:
            return json.load(f)

def save_json_file(file_path: Path, data: Dict[str, Any]) -> None:
    """Save a JSON file with proper encoding."""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

class AgeticCoder:
    def __init__(self, app_name: str = None, resume_session: str = None):
        """Initialize the AgeticCoder with either a new app or resume a session."""
        self.config = self.load_config()
        self.ui = AgeticUI(self.config)
        self.ui.print_title()
        
        self.root_dir = Path('apps')
        self.root_dir.mkdir(exist_ok=True)
        
        # Initialize or load app with memory check
        if app_name:
            sanitized_name = self.sanitize_name(app_name)
            self.app_dir = self.root_dir / sanitized_name
            
            # Check if app directory exists
            if self.app_dir.exists():
                self.ui.print_warning(f"App directory '{sanitized_name}' already exists")
                if not self.ui.confirm("Use existing directory?"):
                    counter = 1
                    while True:
                        new_dir = self.root_dir / f"{sanitized_name}_{counter}"
                        if not new_dir.exists():
                            self.app_dir = new_dir
                            break
                        counter += 1
                    self.ui.print_info(f"Creating new directory: {self.app_dir.name}")
            
            self.app_dir.mkdir(exist_ok=True)
            self.memory_dir = self.app_dir / '.memory'
            
            # Check for existing memory
            if self.memory_dir.exists():
                self.ui.print_info("Found existing memory data")
                if not self.ui.confirm("Use existing memory?"):
                    backup_dir = self.app_dir / '.memory_backup'
                    if backup_dir.exists():
                        shutil.rmtree(backup_dir)
                    self.memory_dir.rename(backup_dir)
                    self.ui.print_info(f"Backed up existing memory to {backup_dir}")
                    self.memory_dir.mkdir()
            else:
                self.memory_dir.mkdir()
            
            self.app_name = app_name
        elif resume_session:
            session_parts = resume_session.split('/')
            if len(session_parts) != 2:
                raise ValueError("Resume session must be in format: app_name/session_id")
            app_name, session_id = session_parts
            self.app_dir = self.root_dir / app_name
            if not self.app_dir.exists():
                raise ValueError(f"App {app_name} not found")
            self.memory_dir = self.app_dir / '.memory'
            if not self.memory_dir.exists():
                raise ValueError(f"Memory directory not found for app {app_name}")
            self.app_name = app_name
            self.current_session = session_id
        else:
            raise ValueError("Either app_name or resume_session must be provided")
        
        # Set up session
        if hasattr(self, 'current_session'):
            self.session_dir = self.memory_dir / self.current_session
            if not self.session_dir.exists():
                raise ValueError(f"Session {self.current_session} not found")
            
            self.ui.print_success(f"Resumed session: {self.current_session}")
            self._display_session_context()
        else:
            self.current_session = datetime.now().strftime('%Y%m%d_%H%M%S')
            self.session_dir = self.memory_dir / self.current_session
            self.session_dir.mkdir(exist_ok=True)
            self.ui.print_success(f"Created new session: {self.current_session}")
        
        self.modified_files: Set[Path] = set()
        self.current_dependencies: Set[str] = set()
        self.base_requirements = load_base_requirements()

    def _display_session_context(self):
        """Display context from previous session activities."""
        history = self.get_session_history()
        if history:
            self.ui.print_info("\nPrevious actions:")
            for h in history[-5:]:
                action_type = h['type'].capitalize()
                timestamp = datetime.strptime(h['timestamp'], '%Y%m%d_%H%M%S').strftime('%H:%M:%S')
                self.ui.print_info(f"[{timestamp}] {action_type}")

    @staticmethod
    def sanitize_name(name: str) -> str:
        """Sanitize app name for directory creation."""
        return re.sub(r'[^a-zA-Z0-9_-]', '_', name.lower())

    def load_config(self) -> Dict[str, Any]:
        """Load or create configuration file."""
        config_file = Path('config.json')
        if not config_file.exists():
            default_config = {
                'llm_studio_url': 'http://localhost:1234/v1',
                'max_retries': 3,
                'timeout': None,
                'models': ['gpt-3.5-turbo']
            }
            save_json_file(config_file, default_config)
            return default_config
        
        return load_json_file(config_file)

    def save_memory(self, data: Dict[str, Any], category: str):
        """Save data to memory with timestamp."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        memory_file = self.session_dir / f'{category}_{timestamp}.json'
        save_json_file(memory_file, data)

    def get_user_permission(self, action: str) -> bool:
        """Get user permission for an action."""
        return self.ui.confirm(action)

    def validate_filename(self, filename: str) -> str:
        """Sanitize and validate filename."""
        clean_name = re.sub(r'[^a-zA-Z0-9_-]', '_', filename)
        if clean_name.startswith('.') or clean_name.startswith('_'):
            clean_name = 'f' + clean_name
        return clean_name

    def get_session_history(self) -> List[Dict[str, Any]]:
        """Get chronological history of current app and session."""
        history = []
        # Get app-wide history first
        for session_dir in sorted(self.memory_dir.glob('*')):
            if session_dir.is_dir() and session_dir.name != self.current_session:
                for file in sorted(session_dir.glob('*.json')):
                    data = load_json_file(file)
                    history.append({
                        'session': session_dir.name,
                        'type': file.stem.split('_')[0],
                        'timestamp': file.stem.split('_')[1],
                        'data': data
                    })
        
        # Add current session history
        for file in sorted(self.session_dir.glob('*.json')):
            data = load_json_file(file)
            history.append({
                'session': self.current_session,
                'type': file.stem.split('_')[0],
                'timestamp': file.stem.split('_')[1],
                'data': data
            })
        return history

    def install_dependencies(self, requirements: List[str]) -> bool:
        """Install Python package dependencies."""
        # Parse and validate dependencies
        all_deps = merge_dependencies(self.base_requirements, requirements)
        deps_str = format_dependencies(all_deps)
        
        self.ui.print_info("Required packages:")
        print(deps_str)
        
        if not self.ui.confirm("Install these packages?"):
            return False
            
        try:
            self.ui.start_loading("Installing dependencies")
            subprocess.check_call([
                sys.executable, '-m', 'pip', 'install',
                *[dep.split('>=')[0] for dep in all_deps]
            ])
            self.current_dependencies.update(all_deps)
            self.save_memory({
                "installed_packages": list(all_deps)
            }, "dependencies")
            self.ui.print_success("Dependencies installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            self.ui.print_error(f"Failed to install dependencies: {e}")
            return False
        finally:
            self.ui.stop_loading_animation()

    def execute_llm_query(
        self, 
        query: str,
        retries: int = None,
        temperature: float = 0.7
    ) -> Optional[str]:
        """Execute a query against the LLM API."""
        if retries is None:
            retries = self.config['max_retries']
            
        self.ui.start_loading("Generating code")
        try:
            for attempt in range(retries):
                try:
                    response = requests.post(
                        f"{self.config['llm_studio_url']}/chat/completions",
                        json={
                            "model": self.config['models'][0],
                            "messages": [{"role": "user", "content": query}],
                            "temperature": temperature
                        },
                        timeout=self.config['timeout']
                    )
                    response.raise_for_status()
                    result = response.json()['choices'][0]['message']['content']
                    self.ui.print_success("Code generated successfully")
                    return result
                except requests.exceptions.RequestException as e:
                    self.ui.print_warning(f"Attempt {attempt + 1}/{retries} failed: {e}")
                    if attempt < retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                except Exception as e:
                    self.ui.print_error(f"Unexpected error: {e}")
                    break
            return None
        finally:
            self.ui.stop_loading_animation()

    def parse_code_response(self, response: str) -> Tuple[Dict[str, str], List[str]]:
        """Parse the LLM response into files and dependencies."""
        if not response or not response.strip():
            raise ValueError("Empty response from LLM")
            
        files = {}
        current_file = None
        current_content = []
        
        self.ui.start_loading("Parsing response")
        try:
            lines = response.split('\n')
            for i, line in enumerate(lines):
                # Parse code blocks
                if line.startswith('```'):
                    if len(line) > 3:
                        # New file starts
                        if current_file:
                            files[current_file] = '\n'.join(current_content)
                            current_content = []
                        filename = self.validate_filename(line[3:].strip())
                        current_file = filename
                        self.ui.print_info(f"Found file: {filename}")
                    elif current_file:
                        # File ends
                        files[current_file] = '\n'.join(current_content)
                        current_file = None
                        current_content = []
                elif current_file and i < len(lines) - 1:
                    current_content.append(line)
                    
            if not files and response.strip():
                # Default to main.py if no explicit files but have content
                files["main.py"] = response.strip()
                self.ui.print_info("Created default main.py")
                
            # Parse dependencies from all files
            combined_content = '\n'.join(files.values())
            dependencies = parse_dependencies(combined_content)
            
            if dependencies:
                self.ui.print_info(f"Found dependencies: {', '.join(dependencies)}")
                
            return files, dependencies
        finally:
            self.ui.stop_loading_animation()

    def create_program(self, query: str, allow_modifications: bool = False, subfolder: str = None):
        """Create or modify a program based on the query."""
        self.save_memory({"query": query}, "input")
        
        history = self.get_session_history()
        if history:
            context_lines = [f"App: {self.app_name}"]
            for h in history[-5:]:
                context_lines.append(f"Session: {h['session']}")
                context_lines.append(f"Action: {h['type']}")
            context = "\n".join(context_lines)
        else:
            context = f"New app: {self.app_name}"
        
        prompt = (
            f"Context of previous actions:\n{context}\n\n"
            f"Create a program that: {query}\n"
            "Requirements:\n"
            "1. Format each file's code within triple backticks followed by the filename\n"
            "2. Include necessary pip install commands for dependencies\n"
            "3. Create appropriate test files\n"
            "4. Use proper error handling\n"
            "5. Include docstrings and comments\n"
            "Format:\n"
            "```filename.py\n"
            "code here\n"
            "```"
        )
        
        llm_response = self.execute_llm_query(prompt)
        if not llm_response:
            self.ui.print_error("Failed to generate program")
            return False
        
        try:
            generated_files, dependencies = self.parse_code_response(llm_response)
        except ValueError as e:
            self.ui.print_error(f"Error parsing LLM response: {e}")
            return False
        
        self.save_memory({"generated_code": generated_files}, "code")
        
        program_dir = self.app_dir / 'src'
        if subfolder:
            program_dir = program_dir / self.sanitize_name(subfolder)
        
        if program_dir.exists():
            existing_files = set(f for f in program_dir.rglob('*') if f.is_file())
            new_files = set(program_dir / f for f in generated_files)
            
            to_modify = existing_files & new_files
            if to_modify and not allow_modifications:
                if not self.ui.confirm(
                    f"Modify existing files?\n" + 
                    "\n".join(f"- {f.relative_to(program_dir)}" for f in to_modify)
                ):
                    self.ui.print_warning("Operation cancelled")
                    return False
                    
            self.modified_files.update(to_modify)
        
        if dependencies and not self.install_dependencies(dependencies):
            return False
            
        program_dir.mkdir(parents=True, exist_ok=True)
        test_dir = program_dir / 'tests'
        test_dir.mkdir(exist_ok=True)
        
        self.ui.start_loading("Writing files")
        try:
            for filename, content in generated_files.items():
                try:
                    if filename.startswith('test_'):
                        file_path = test_dir / filename
                    else:
                        file_path = program_dir / filename
                        
                    file_path.parent.mkdir(exist_ok=True)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    self.ui.print_success(
                        f"{'Modified' if file_path in self.modified_files else 'Created'} {file_path}"
                    )
                except IOError as e:
                    self.ui.print_error(f"Error writing {filename}: {e}")
                    return False
            return True
        finally:
            self.ui.stop_loading_animation()
            
        return self.run_tests(program_dir)

    def analyze_test_failure(self, failure) -> str:
        """Analyze test failure and generate detailed error report."""
        if hasattr(failure, 'tb_test'):
            return (
                f"Test: {failure.tb_test}\n"
                f"Error: {failure.exception_type}: {failure.message}\n"
                f"File: {failure.filename}, Line {failure.line_number}\n"
                f"Context:\n{failure.context}"
            )
        return str(failure)

    def run_tests(self, program_dir: Path, max_attempts: int = 3) -> bool:
        """Run tests recursively until they pass or user decides to stop."""
        test_dir = program_dir / 'tests'
        if not test_dir.exists() or not list(test_dir.glob('test_*.py')):
            self.ui.print_info("No tests found")
            return True
            
        max_attempts = min(max_attempts, self.config.get('max_test_attempts', 3))
        attempt = 0
        
        while attempt < max_attempts:
            self.save_memory({"test_execution": f"attempt_{attempt + 1}"}, "test")
            
            if not self.ui.confirm(f"Run tests? (Attempt {attempt + 1}/{max_attempts})"):
                return False
                
            self.ui.start_loading(f"Running tests (Attempt {attempt + 1}/{max_attempts})")
            
            try:
                import unittest
                test_loader = unittest.TestLoader()
                test_suite = test_loader.discover(str(test_dir))
                test_runner = unittest.TextTestRunner(verbosity=2)
                result = test_runner.run(test_suite)
                
                if result.wasSuccessful():
                    self.ui.print_success("\nAll tests passed!")
                    self.save_memory({"test_status": "passed"}, "test")
                    return True
                    
                self.ui.print_warning("\nSome tests failed. Attempting to fix...")
                
                failed_tests = [
                    self.analyze_test_failure(failure[0]) 
                    for failure in result.failures + result.errors
                ]
                
                fix_prompt = (
                    "Fix the following test failures:\n" +
                    "\n".join(failed_tests) +
                    "\nCurrent files:\n" +
                    "\n".join(f"- {f.relative_to(program_dir)}" 
                             for f in program_dir.rglob('*.py')) +
                    "\nProvide complete corrected program files."
                )
                
                if not self.create_program(fix_prompt, allow_modifications=True):
                    self.ui.print_error("Failed to generate fixes")
                    return False
                    
            except Exception as e:
                self.ui.print_error(f"Error running tests: {e}")
                self.save_memory({"test_error": str(e)}, "test")
            finally:
                self.ui.stop_loading_animation()
                
            attempt += 1
            
        self.ui.print_warning("\nMax test attempts reached")
        return False

    def deploy_program(self, program_dir: Optional[Path] = None) -> bool:
        """Deploy the program to a versioned directory."""
        if not self.ui.confirm("Deploy program?"):
            return False
            
        self.ui.start_loading("Deploying program")
        try:
            if program_dir is None:
                program_dir = self.app_dir / 'src'
                
            if not program_dir.exists():
                raise FileNotFoundError(f"Program directory not found: {program_dir}")
                # Create deployment directory if it doesn't exist
            deploy_dir = self.app_dir / 'deployed'
            deploy_dir.mkdir(exist_ok=True)
            # Create timestamped deployment folder
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            deployment_path = deploy_dir / timestamp
                     # Backup before deploy if configured
            if self.config.get('deployment', {}).get('backup_before_deploy', True):
                backup_dir = self.app_dir / 'backups' / timestamp
                shutil.copytree(program_dir, backup_dir)
                self.ui.print_info(f"Created backup at: {backup_dir}")
            # Copy program files to deployment directory
            shutil.copytree(program_dir, deployment_path)
                   # Clean old deployments if needed
            max_deployments = self.config.get('deployment', {}).get('max_deployments', 10)
            deployments = sorted(deploy_dir.glob('*'))
            if len(deployments) > max_deployments:
                for old_deploy in deployments[:-max_deployments]:
                    shutil.rmtree(old_deploy)
                self.ui.print_info(f"Cleaned up old deployments, keeping last {max_deployments}")
            
            self.ui.print_success(f"Program deployed to: {deployment_path}")
            self.save_memory({
                "deployment": "successful",
                "location": str(deployment_path),
                "timestamp": timestamp
            }, "deployment")
            return True
            
        except Exception as e:
            self.ui.print_error(f"Deployment failed: {e}")
            self.save_memory({
                "deployment": "failed",
                "error": str(e)
            }, "deployment")
            return False
        finally:
            self.ui.stop_loading_animation()

    def cleanup(self):
        """Clean up generated files."""
        if self.ui.confirm("Clean up generated files?"):
            shutil.rmtree(self.app_dir / 'src', ignore_errors=True)
            self.ui.print_success("Cleaned up generated files")

    def rollback_deployment(self, deployment_path: Path):
        """Rollback a failed deployment."""
        try:
            if deployment_path.exists():
                shutil.rmtree(deployment_path)
            self.ui.print_success(f"Rolled back deployment: {deployment_path}")
        except Exception as e:
            self.ui.print_error(f"Error during rollback: {e}")

    @classmethod
    def list_apps(cls) -> List[str]:
        """List all available apps."""
        root_dir = Path('apps')
        if not root_dir.exists():
            return []
        return [d.name for d in root_dir.iterdir() if d.is_dir()]

    def list_sessions(self) -> List[str]:
        """List all available sessions for current app."""
        return [d.name for d in self.memory_dir.iterdir() if d.is_dir()]

def main():
    try:
        # Create UI instance for initial setup
        config = load_json_file(Path('config.json')) if Path('config.json').exists() else {}
        ui = AgeticUI(config)
                # Display logo
        ui.print_title()
        
                # Initial app selection
        apps = AgeticCoder.list_apps()
        app_name = None
        resume_session = None
        
        if apps:
            choice = ui.print_menu("Available Apps:", apps + ["Create new app"])
            if choice.isdigit():
                choice = int(choice)
                if 0 < choice <= len(apps):
                    app_name = apps[choice-1]
                    coder = AgeticCoder(app_name=app_name)
                    sessions = coder.list_sessions()
                    
                    if sessions:
                        session_choice = ui.print_menu(
                            "Available Sessions:",
                            sessions + ["Create new session"]
                        )
                        if session_choice.isdigit():
                            session_choice = int(session_choice)
                            if 0 < session_choice <= len(sessions):
                                resume_session = f"{app_name}/{sessions[session_choice-1]}"
        
        if not app_name and not resume_session:
            app_name = ui.get_input("\nEnter new app name: ")
        
        try:
            coder = AgeticCoder(
                app_name=None if resume_session else app_name,
                resume_session=resume_session
            )
        except ValueError as e:
            ui.print_error(f"Error: {e}")
            sys.exit(1)
            
        while True:
            choice = ui.print_menu(
                f"Agetic Coder Terminal [{coder.app_name}]",
                [
                    "Create new program",
                    "Modify existing program",
                    "List deployed versions",
                    "List app sessions",
                    "Switch app",
                    "Exit"
                ]
            )
            
            if choice == '1':
                subfolder = ui.get_input("\nEnter subfolder name (optional): ").strip()
                query = ui.get_input("Enter your program request: ")
                if coder.create_program(
                    query,
                    allow_modifications=False,
                    subfolder=subfolder or None
                ):
                    if coder.deploy_program():
                        ui.print_success("\nProgram successfully created and deployed!")
                        
                    if coder.config.get('deployment', {}).get('auto_cleanup', False):
                        coder.cleanup()
                    else:
                        if ui.confirm("Clean up generated files?"):
                            coder.cleanup()
            
            elif choice == '2':
                query = ui.get_input("\nEnter your modification request: ")
                if coder.create_program(query, allow_modifications=True):
                    if coder.deploy_program():
                        ui.print_success("\nProgram successfully modified and deployed!")
                        
            elif choice == '3':
                deploy_dir = coder.app_dir / 'deployed'
                if deploy_dir.exists():
                    ui.print_info("\nDeployed versions:")
                    for version in deploy_dir.iterdir():
                        if version.is_dir():
                            ui.print_info(f"- {version.name}")
                            ui.print_info("  Files:")
                            for file in version.rglob('*'):
                                if file.is_file():
                                    ui.print_info(f"  - {file.relative_to(version)}")
                else:
                    ui.print_warning("\nNo deployments found")
                    
            elif choice == '4':
                sessions = coder.list_sessions()
                if sessions:
                    ui.print_info("\nApp sessions:")
                    for session in sessions:
                        ui.print_info(f"- {session}")
                else:
                    ui.print_warning("\nNo sessions found")
                    
            elif choice == '5':
                return main()
                    
            elif choice == '6':
                break
                
            else:
                ui.print_error("\nInvalid choice. Please try again.")

    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"\nError: {e}")
    finally:
        # Ensure cursor is visible
        cursor.show()

if __name__ == "__main__":
    main()
