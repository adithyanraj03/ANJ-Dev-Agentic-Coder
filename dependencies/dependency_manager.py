#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dependency manager for handling project dependencies."""
import os
import sys
import json
import subprocess
import re
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Set, Union

class DependencyManager:
    """Manages project dependencies for different package managers."""
    
    def __init__(self, project_root: Optional[Path] = None):
        """Initialize dependency manager.
        
        Args:
            project_root: Optional project root directory
        """
        self.project_root = project_root or Path.cwd()
        self.package_managers = {
            'pip': {
                'detect': self._detect_pip,
                'install': self._pip_install,
                'add': self._pip_add,
                'remove': self._pip_remove,
                'update': self._pip_update,
                'list': self._pip_list,
                'file': 'requirements.txt'
            },
            'npm': {
                'detect': self._detect_npm,
                'install': self._npm_install,
                'add': self._npm_add,
                'remove': self._npm_remove,
                'update': self._npm_update,
                'list': self._npm_list,
                'file': 'package.json'
            },
            'yarn': {
                'detect': self._detect_yarn,
                'install': self._yarn_install,
                'add': self._yarn_add,
                'remove': self._yarn_remove,
                'update': self._yarn_update,
                'list': self._yarn_list,
                'file': 'package.json'
            },
            'poetry': {
                'detect': self._detect_poetry,
                'install': self._poetry_install,
                'add': self._poetry_add,
                'remove': self._poetry_remove,
                'update': self._poetry_update,
                'list': self._poetry_list,
                'file': 'pyproject.toml'
            }
        }
        
        # Detect available package managers
        self.available_managers = self._detect_package_managers()
        
        # Load base requirements
        self.base_requirements = self.load_base_requirements()
    
    def _detect_package_managers(self) -> Dict[str, bool]:
        """Detect available package managers.
        
        Returns:
            Dict[str, bool]: Dictionary of package manager availability
        """
        available = {}
        
        for name, manager in self.package_managers.items():
            available[name] = manager['detect']()
            
        return available
    
    def _detect_pip(self) -> bool:
        """Detect if pip is available.
        
        Returns:
            bool: True if pip is available
        """
        # Check for requirements.txt
        if (self.project_root / 'requirements.txt').exists():
            return True
            
        # Check for setup.py
        if (self.project_root / 'setup.py').exists():
            return True
            
        # Check for pyproject.toml
        if (self.project_root / 'pyproject.toml').exists():
            return True
            
        return False
    
    def _detect_npm(self) -> bool:
        """Detect if npm is available.
        
        Returns:
            bool: True if npm is available
        """
        # Check for package.json
        if (self.project_root / 'package.json').exists():
            # Check if yarn.lock exists (prefer yarn if it does)
            if (self.project_root / 'yarn.lock').exists():
                return False
                
            return True
            
        return False
    
    def _detect_yarn(self) -> bool:
        """Detect if yarn is available.
        
        Returns:
            bool: True if yarn is available
        """
        # Check for package.json and yarn.lock
        if (self.project_root / 'package.json').exists() and (self.project_root / 'yarn.lock').exists():
            return True
            
        return False
    
    def _detect_poetry(self) -> bool:
        """Detect if poetry is available.
        
        Returns:
            bool: True if poetry is available
        """
        # Check for pyproject.toml with poetry section
        pyproject_path = self.project_root / 'pyproject.toml'
        if pyproject_path.exists():
            try:
                with open(pyproject_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if '[tool.poetry]' in content:
                        return True
            except:
                pass
                
        return False
    
    def _run_command(self, command: List[str], cwd: Optional[Path] = None) -> Tuple[int, str, str]:
        """Run command and return output.
        
        Args:
            command: Command to run
            cwd: Working directory
            
        Returns:
            Tuple[int, str, str]: Tuple of (exit_code, stdout, stderr)
        """
        try:
            process = subprocess.Popen(
                command,
                cwd=str(cwd or self.project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate()
            return process.returncode, stdout, stderr
            
        except Exception as e:
            return 1, '', str(e)
    
    def _pip_install(self) -> bool:
        """Install pip dependencies.
        
        Returns:
            bool: True if installation was successful
        """
        # Check for requirements.txt
        if (self.project_root / 'requirements.txt').exists():
            exit_code, _, _ = self._run_command(['pip', 'install', '-r', 'requirements.txt'])
            return exit_code == 0
            
        # Check for setup.py
        if (self.project_root / 'setup.py').exists():
            exit_code, _, _ = self._run_command(['pip', 'install', '-e', '.'])
            return exit_code == 0
            
        # Check for pyproject.toml (non-poetry)
        if (self.project_root / 'pyproject.toml').exists():
            exit_code, _, _ = self._run_command(['pip', 'install', '-e', '.'])
            return exit_code == 0
            
        return False
    
    def _pip_add(self, package: str, dev: bool = False) -> bool:
        """Add pip dependency.
        
        Args:
            package: Package to add
            dev: Whether to add as dev dependency
            
        Returns:
            bool: True if package was added successfully
        """
        # Install package
        command = ['pip', 'install']
        if dev:
            # There's no standard way to mark dev dependencies with pip
            # We'll add it to requirements-dev.txt if it exists
            command.append(package)
            exit_code, _, _ = self._run_command(command)
            
            if exit_code == 0 and (self.project_root / 'requirements-dev.txt').exists():
                # Add to requirements-dev.txt
                with open(self.project_root / 'requirements-dev.txt', 'a') as f:
                    f.write(f'\n{package}\n')
        else:
            command.append(package)
            exit_code, _, _ = self._run_command(command)
            
            if exit_code == 0 and (self.project_root / 'requirements.txt').exists():
                # Add to requirements.txt
                with open(self.project_root / 'requirements.txt', 'a') as f:
                    f.write(f'\n{package}\n')
                    
        return exit_code == 0
    
    def _pip_remove(self, package: str) -> bool:
        """Remove pip dependency.
        
        Args:
            package: Package to remove
            
        Returns:
            bool: True if package was removed successfully
        """
        # Uninstall package
        exit_code, _, _ = self._run_command(['pip', 'uninstall', '-y', package])
        
        if exit_code == 0:
            # Remove from requirements.txt if it exists
            if (self.project_root / 'requirements.txt').exists():
                self._remove_from_requirements(self.project_root / 'requirements.txt', package)
                
            # Remove from requirements-dev.txt if it exists
            if (self.project_root / 'requirements-dev.txt').exists():
                self._remove_from_requirements(self.project_root / 'requirements-dev.txt', package)
                
        return exit_code == 0
    
    def _remove_from_requirements(self, file_path: Path, package: str):
        """Remove package from requirements file.
        
        Args:
            file_path: Path to requirements file
            package: Package to remove
        """
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
                
            # Remove package lines
            package_pattern = re.compile(rf'^{re.escape(package)}(==|>=|<=|~=|!=|>|<|@|$)')
            lines = [line for line in lines if not package_pattern.match(line.strip())]
            
            with open(file_path, 'w') as f:
                f.writelines(lines)
                
        except Exception:
            pass
    
    def _pip_update(self, package: Optional[str] = None) -> bool:
        """Update pip dependencies.
        
        Args:
            package: Optional package to update
            
        Returns:
            bool: True if update was successful
        """
        if package:
            # Update specific package
            exit_code, _, _ = self._run_command(['pip', 'install', '--upgrade', package])
        else:
            # Update all packages from requirements.txt
            if (self.project_root / 'requirements.txt').exists():
                exit_code, _, _ = self._run_command(['pip', 'install', '--upgrade', '-r', 'requirements.txt'])
            else:
                return False
                
        return exit_code == 0
    
    def _pip_list(self) -> List[Dict[str, str]]:
        """List installed pip packages.
        
        Returns:
            List[Dict[str, str]]: List of package information
        """
        exit_code, stdout, _ = self._run_command(['pip', 'list', '--format=json'])
        
        if exit_code == 0:
            try:
                packages = json.loads(stdout)
                return [
                    {
                        'name': pkg['name'],
                        'version': pkg['version'],
                        'type': 'regular'
                    }
                    for pkg in packages
                ]
            except:
                pass
                
        return []
    
    def _npm_install(self) -> bool:
        """Install npm dependencies.
        
        Returns:
            bool: True if installation was successful
        """
        exit_code, _, _ = self._run_command(['npm', 'install'])
        return exit_code == 0
    
    def _npm_add(self, package: str, dev: bool = False) -> bool:
        """Add npm dependency.
        
        Args:
            package: Package to add
            dev: Whether to add as dev dependency
            
        Returns:
            bool: True if package was added successfully
        """
        command = ['npm', 'install']
        if dev:
            command.append('--save-dev')
        else:
            command.append('--save')
            
        command.append(package)
        exit_code, _, _ = self._run_command(command)
        return exit_code == 0
    
    def _npm_remove(self, package: str) -> bool:
        """Remove npm dependency.
        
        Args:
            package: Package to remove
            
        Returns:
            bool: True if package was removed successfully
        """
        exit_code, _, _ = self._run_command(['npm', 'uninstall', package])
        return exit_code == 0
    
    def _npm_update(self, package: Optional[str] = None) -> bool:
        """Update npm dependencies.
        
        Args:
            package: Optional package to update
            
        Returns:
            bool: True if update was successful
        """
        if package:
            exit_code, _, _ = self._run_command(['npm', 'update', package])
        else:
            exit_code, _, _ = self._run_command(['npm', 'update'])
            
        return exit_code == 0
    
    def _npm_list(self) -> List[Dict[str, str]]:
        """List installed npm packages.
        
        Returns:
            List[Dict[str, str]]: List of package information
        """
        exit_code, stdout, _ = self._run_command(['npm', 'list', '--json'])
        
        if exit_code == 0:
            try:
                data = json.loads(stdout)
                packages = []
                
                # Get regular dependencies
                if 'dependencies' in data:
                    for name, info in data['dependencies'].items():
                        packages.append({
                            'name': name,
                            'version': info.get('version', ''),
                            'type': 'regular'
                        })
                        
                # Get dev dependencies
                if 'devDependencies' in data:
                    for name, info in data['devDependencies'].items():
                        packages.append({
                            'name': name,
                            'version': info.get('version', ''),
                            'type': 'dev'
                        })
                        
                return packages
            except:
                pass
                
        return []
    
    def _yarn_install(self) -> bool:
        """Install yarn dependencies.
        
        Returns:
            bool: True if installation was successful
        """
        exit_code, _, _ = self._run_command(['yarn', 'install'])
        return exit_code == 0
    
    def _yarn_add(self, package: str, dev: bool = False) -> bool:
        """Add yarn dependency.
        
        Args:
            package: Package to add
            dev: Whether to add as dev dependency
            
        Returns:
            bool: True if package was added successfully
        """
        command = ['yarn', 'add']
        if dev:
            command.append('--dev')
            
        command.append(package)
        exit_code, _, _ = self._run_command(command)
        return exit_code == 0
    
    def _yarn_remove(self, package: str) -> bool:
        """Remove yarn dependency.
        
        Args:
            package: Package to remove
            
        Returns:
            bool: True if package was removed successfully
        """
        exit_code, _, _ = self._run_command(['yarn', 'remove', package])
        return exit_code == 0
    
    def _yarn_update(self, package: Optional[str] = None) -> bool:
        """Update yarn dependencies.
        
        Args:
            package: Optional package to update
            
        Returns:
            bool: True if update was successful
        """
        if package:
            exit_code, _, _ = self._run_command(['yarn', 'upgrade', package])
        else:
            exit_code, _, _ = self._run_command(['yarn', 'upgrade'])
            
        return exit_code == 0
    
    def _yarn_list(self) -> List[Dict[str, str]]:
        """List installed yarn packages.
        
        Returns:
            List[Dict[str, str]]: List of package information
        """
        exit_code, stdout, _ = self._run_command(['yarn', 'list', '--json'])
        
        if exit_code == 0:
            try:
                data = json.loads(stdout)
                packages = []
                
                if 'data' in data and 'trees' in data['data']:
                    for item in data['data']['trees']:
                        name = item.get('name', '')
                        if name:
                            # Extract name and version
                            parts = name.split('@')
                            if len(parts) > 1:
                                pkg_name = '@'.join(parts[:-1]) if name.startswith('@') else parts[0]
                                version = parts[-1]
                                
                                packages.append({
                                    'name': pkg_name,
                                    'version': version,
                                    'type': 'regular'  # Yarn doesn't distinguish in list output
                                })
                                
                return packages
            except:
                pass
                
        return []
    
    def _poetry_install(self) -> bool:
        """Install poetry dependencies.
        
        Returns:
            bool: True if installation was successful
        """
        exit_code, _, _ = self._run_command(['poetry', 'install'])
        return exit_code == 0
    
    def _poetry_add(self, package: str, dev: bool = False) -> bool:
        """Add poetry dependency.
        
        Args:
            package: Package to add
            dev: Whether to add as dev dependency
            
        Returns:
            bool: True if package was added successfully
        """
        command = ['poetry', 'add']
        if dev:
            command.append('--dev')
            
        command.append(package)
        exit_code, _, _ = self._run_command(command)
        return exit_code == 0
    
    def _poetry_remove(self, package: str) -> bool:
        """Remove poetry dependency.
        
        Args:
            package: Package to remove
            
        Returns:
            bool: True if package was removed successfully
        """
        exit_code, _, _ = self._run_command(['poetry', 'remove', package])
        return exit_code == 0
    
    def _poetry_update(self, package: Optional[str] = None) -> bool:
        """Update poetry dependencies.
        
        Args:
            package: Optional package to update
            
        Returns:
            bool: True if update was successful
        """
        if package:
            exit_code, _, _ = self._run_command(['poetry', 'update', package])
        else:
            exit_code, _, _ = self._run_command(['poetry', 'update'])
            
        return exit_code == 0
    
    def _poetry_list(self) -> List[Dict[str, str]]:
        """List installed poetry packages.
        
        Returns:
            List[Dict[str, str]]: List of package information
        """
        exit_code, stdout, _ = self._run_command(['poetry', 'show', '--no-ansi'])
        
        if exit_code == 0:
            packages = []
            
            for line in stdout.splitlines():
                if not line.strip():
                    continue
                    
                parts = line.split()
                if len(parts) >= 2:
                    packages.append({
                        'name': parts[0],
                        'version': parts[1],
                        'type': 'regular'  # Can't determine from this output
                    })
                    
            return packages
            
        return []
    
    def install_dependencies(self) -> bool:
        """Install project dependencies.
        
        Returns:
            bool: True if installation was successful
        """
        success = False
        
        # Try each available package manager
        for name, available in self.available_managers.items():
            if available:
                manager = self.package_managers[name]
                if manager['install']():
                    success = True
                    break
                    
        return success
    
    def add_dependency(self, package: str, dev: bool = False, manager: Optional[str] = None) -> bool:
        """Add dependency to project.
        
        Args:
            package: Package to add
            dev: Whether to add as dev dependency
            manager: Optional package manager to use
            
        Returns:
            bool: True if package was added successfully
        """
        if manager and manager in self.available_managers and self.available_managers[manager]:
            # Use specified manager
            return self.package_managers[manager]['add'](package, dev)
            
        # Try each available package manager
        for name, available in self.available_managers.items():
            if available:
                if self.package_managers[name]['add'](package, dev):
                    return True
                    
        return False
    
    def remove_dependency(self, package: str, manager: Optional[str] = None) -> bool:
        """Remove dependency from project.
        
        Args:
            package: Package to remove
            manager: Optional package manager to use
            
        Returns:
            bool: True if package was removed successfully
        """
        if manager and manager in self.available_managers and self.available_managers[manager]:
            # Use specified manager
            return self.package_managers[manager]['remove'](package)
            
        # Try each available package manager
        for name, available in self.available_managers.items():
            if available:
                if self.package_managers[name]['remove'](package):
                    return True
                    
        return False
    
    def update_dependencies(self, package: Optional[str] = None, manager: Optional[str] = None) -> bool:
        """Update project dependencies.
        
        Args:
            package: Optional package to update
            manager: Optional package manager to use
            
        Returns:
            bool: True if update was successful
        """
        if manager and manager in self.available_managers and self.available_managers[manager]:
            # Use specified manager
            return self.package_managers[manager]['update'](package)
            
        # Try each available package manager
        for name, available in self.available_managers.items():
            if available:
                if self.package_managers[name]['update'](package):
                    return True
                    
        return False
    
    def list_dependencies(self, manager: Optional[str] = None) -> List[Dict[str, str]]:
        """List project dependencies.
        
        Args:
            manager: Optional package manager to use
            
        Returns:
            List[Dict[str, str]]: List of package information
        """
        if manager and manager in self.available_managers and self.available_managers[manager]:
            # Use specified manager
            return self.package_managers[manager]['list']()
            
        # Combine results from all available package managers
        all_packages = []
        
        for name, available in self.available_managers.items():
            if available:
                packages = self.package_managers[name]['list']()
                for pkg in packages:
                    pkg['manager'] = name
                    all_packages.append(pkg)
                    
        return all_packages
    
    def load_base_requirements(self) -> List[str]:
        """Load base requirements from requirements.txt.
        
        Returns:
            List[str]: List of base requirements
        """
        requirements = []
        
        # Check for requirements.txt
        req_file = self.project_root / 'requirements.txt'
        if req_file.exists():
            try:
                with open(req_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            requirements.append(line)
            except:
                pass
                
        return requirements
    
    def merge_requirements(self, base_requirements: List[str], new_requirements: List[str]) -> List[str]:
        """Merge base and new requirements.
        
        Args:
            base_requirements: Base requirements list
            new_requirements: New requirements list
            
        Returns:
            List[str]: Merged requirements list
        """
        # Create set of base requirement names (without version)
        base_names = set()
        for req in base_requirements:
            # Extract package name (remove version specifiers)
            name = re.split(r'[<>=!~]', req)[0].strip()
            base_names.add(name)
            
        # Add new requirements that aren't in base
        merged = base_requirements.copy()
        for req in new_requirements:
            name = re.split(r'[<>=!~]', req)[0].strip()
            if name not in base_names:
                merged.append(req)
                base_names.add(name)
                
        return merged
    
    def save_requirements(self, requirements: List[str]) -> bool:
        """Save requirements to requirements.txt.
        
        Args:
            requirements: Requirements list
            
        Returns:
            bool: True if requirements were saved successfully
        """
        try:
            req_file = self.project_root / 'requirements.txt'
            with open(req_file, 'w', encoding='utf-8') as f:
                for req in requirements:
                    f.write(f"{req}\n")
            return True
        except:
            return False
    
    def get_dependency_file(self, manager: Optional[str] = None) -> Optional[Path]:
        """Get path to dependency file.
        
        Args:
            manager: Optional package manager to use
            
        Returns:
            Optional[Path]: Path to dependency file
        """
        if manager and manager in self.package_managers:
            file_name = self.package_managers[manager]['file']
            file_path = self.project_root / file_name
            if file_path.exists():
                return file_path
                
        # Try each available package manager
        for name, available in self.available_managers.items():
            if available:
                file_name = self.package_managers[name]['file']
                file_path = self.project_root / file_name
                if file_path.exists():
                    return file_path
                    
        return None