#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import json
import time
import shutil
import git
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Set
from datetime import datetime

class GitRepo:
    """Git repository handler."""
    
    def __init__(self, root: str):
        self.root = root
        try:
            self.repo = git.Repo(root)
        except git.InvalidGitRepositoryError:
            self.repo = git.Repo.init(root)
            
    def is_dirty(self, path: str) -> bool:
        """Check if file has uncommitted changes."""
        try:
            return bool(self.repo.git.diff('--', path))
        except git.GitCommandError:
            return False
            
    def path_in_repo(self, path: str) -> bool:
        """Check if file is tracked in repo."""
        try:
            return bool(self.repo.git.ls_files('--', path))
        except git.GitCommandError:
            return False
            
    def git_ignored_file(self, path: str) -> bool:
        """Check if file matches gitignore patterns."""
        try:
            return bool(self.repo.git.check_ignore(path))
        except git.GitCommandError:
            return False
            
    def get_head_commit_sha(self) -> str:
        """Get current HEAD commit SHA."""
        return self.repo.head.commit.hexsha
        
    def get_tracked_files(self) -> List[str]:
        """Get list of tracked files."""
        try:
            return [
                os.path.relpath(f, self.root)
                for f in self.repo.git.ls_files().splitlines()
            ]
        except git.GitCommandError:
            return []

class ProjectManager:
    """Manages project initialization, memory, and context tracking."""
    
    def __init__(self):
        """Initialize project manager."""
        self.current_project = None
        self.memory_dir = '.memory'
        self.context_file = 'plan_context.txt'
        self.project_config = 'project.json'
        
        # File tracking
        self.abs_fnames: Set[str] = set()
        self.abs_read_only_fnames: Set[str] = set()
        self.edited_files: Set[str] = set()
        self.repo: Optional[GitRepo] = None
        
    def check_memory(self, folder_path: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Check if memory exists for the given folder."""
        memory_path = Path(folder_path) / self.memory_dir
        config_path = memory_path / self.project_config
        
        if memory_path.exists() and config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return True, json.load(f)
            except:
                return True, None
        return False, None

    def initialize_project(
        self,
        folder_path: str,
        create_subfolder: bool = False,
        subfolder_name: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Initialize a new project."""
        base_path = Path(folder_path)
        
        if create_subfolder:
            if not subfolder_name:
                # Generate subfolder name based on date
                subfolder_name = f"project_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            project_path = base_path / subfolder_name
            project_path.mkdir(parents=True, exist_ok=True)
        else:
            project_path = base_path
            
        # Initialize Git repo
        try:
            self.repo = GitRepo(str(project_path))
        except Exception as e:
            print(f"Warning: Could not initialize Git repo: {e}")
            
        # Create memory directory
        memory_path = project_path / self.memory_dir
        memory_path.mkdir(exist_ok=True)
        
        # Initialize project configuration
        config = {
            "created_at": datetime.now().isoformat(),
            "path": str(project_path),
            "files": [],
            "dependencies": {},
            "last_modified": datetime.now().isoformat()
        }
        
        config_path = memory_path / self.project_config
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
            
        # Initialize context file
        context_path = memory_path / self.context_file
        if not context_path.exists():
            with open(context_path, 'w', encoding='utf-8') as f:
                f.write(f"Project initialized at {datetime.now().isoformat()}\n")
                
        self.current_project = str(project_path)
        return True, str(project_path)

    def load_project(self, folder_path: str) -> bool:
        """Load existing project."""
        memory_path = Path(folder_path) / self.memory_dir
        config_path = memory_path / self.project_config
        
        if not config_path.exists():
            return False
            
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            # Validate project structure
            if not all(key in config for key in ['path', 'files', 'dependencies']):
                return False
                
            # Initialize Git repo
            try:
                self.repo = GitRepo(folder_path)
            except Exception as e:
                print(f"Warning: Could not load Git repo: {e}")
                
            self.current_project = folder_path
            
            # Load tracked files
            if self.repo:
                for fname in self.repo.get_tracked_files():
                    abs_path = os.path.abspath(os.path.join(folder_path, fname))
                    if os.path.isfile(abs_path):
                        self.abs_fnames.add(abs_path)
                        
            return True
        except:
            return False

    def add_file(self, filepath: str, read_only: bool = False) -> bool:
        """Add file to project tracking."""
        if not self.current_project:
            return False
            
        abs_path = os.path.abspath(filepath)
        if not os.path.isfile(abs_path):
            return False
            
        if read_only:
            self.abs_read_only_fnames.add(abs_path)
        else:
            self.abs_fnames.add(abs_path)
            
        # Update project config
        self.update_file_status(filepath, "added")
        return True

    def remove_file(self, filepath: str) -> bool:
        """Remove file from project tracking."""
        if not self.current_project:
            return False
            
        abs_path = os.path.abspath(filepath)
        removed = False
        
        if abs_path in self.abs_fnames:
            self.abs_fnames.remove(abs_path)
            removed = True
            
        if abs_path in self.abs_read_only_fnames:
            self.abs_read_only_fnames.remove(abs_path)
            removed = True
            
        if removed:
            self.update_file_status(filepath, "removed")
            
        return removed

    def is_file_tracked(self, filepath: str) -> bool:
        """Check if file is being tracked."""
        abs_path = os.path.abspath(filepath)
        return abs_path in self.abs_fnames or abs_path in self.abs_read_only_fnames

    def is_file_editable(self, filepath: str) -> bool:
        """Check if file can be edited."""
        abs_path = os.path.abspath(filepath)
        
        # Check if file is read-only
        if abs_path in self.abs_read_only_fnames:
            return False
            
        # Check if file is git-ignored
        if self.repo and self.repo.git_ignored_file(filepath):
            return False
            
        return True

    def get_file_status(self, filepath: str) -> Optional[str]:
        """Get current status of file."""
        if not self.current_project:
            return None
            
        rel_path = os.path.relpath(filepath, self.current_project)
        config_path = Path(self.current_project) / self.memory_dir / self.project_config
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                for file_info in config['files']:
                    if file_info['path'] == rel_path:
                        return file_info['status']
        except:
            pass
            
        return None

    def append_context(self, text: str):
        """Append to context file."""
        if not self.current_project:
            return False
            
        context_path = Path(self.current_project) / self.memory_dir / self.context_file
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        with open(context_path, 'a', encoding='utf-8') as f:
            f.write(f"\n[{timestamp}]\n{text}\n")
            f.write("-" * 80 + "\n")

    def save_plan(self, plan: Dict[str, Any]):
        """Save execution plan."""
        if not self.current_project:
            return False
            
        plan_path = Path(self.current_project) / self.memory_dir / 'current_plan.json'
        with open(plan_path, 'w', encoding='utf-8') as f:
            json.dump(plan, f, indent=2)
            
        # Add plan to context
        self.append_context(f"New plan created:\n{json.dumps(plan, indent=2)}")

    def update_file_status(self, filepath: str, status: str, content: Optional[str] = None):
        """Update file status in project config."""
        if not self.current_project:
            return False
            
        config_path = Path(self.current_project) / self.memory_dir / self.project_config
        
        with open(config_path, 'r+', encoding='utf-8') as f:
            config = json.load(f)
            
            # Update file status
            rel_path = os.path.relpath(filepath, self.current_project)
            file_info = {
                "path": rel_path,
                "status": status,
                "last_modified": datetime.now().isoformat()
            }
            
            # Remove existing entry if present
            config['files'] = [f for f in config['files'] if f['path'] != rel_path]
            config['files'].append(file_info)
            
            # Update last modified
            config['last_modified'] = datetime.now().isoformat()
            
            # Write back
            f.seek(0)
            json.dump(config, f, indent=2)
            f.truncate()
            
        # Add to context
        self.append_context(f"File {rel_path}: {status}")
        
        return True

    def get_project_files(self) -> List[Dict[str, Any]]:
        """Get list of project files with status."""
        if not self.current_project:
            return []
            
        config_path = Path(self.current_project) / self.memory_dir / self.project_config
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('files', [])
        except:
            return []

    def get_context_history(self) -> str:
        """Get full context history."""
        if not self.current_project:
            return ""
            
        context_path = Path(self.current_project) / self.memory_dir / self.context_file
        try:
            with open(context_path, 'r', encoding='utf-8') as f:
                return f.read()
        except:
            return ""

    def create_backup(self, filepath: str) -> Optional[str]:
        """Create backup of a file before modification."""
        if not self.current_project:
            return None
            
        try:
            source = Path(filepath)
            if not source.exists():
                return None
                
            # Create backup in .memory/backups
            backup_dir = Path(self.current_project) / self.memory_dir / 'backups'
            backup_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = backup_dir / f"{source.name}.{timestamp}.bak"
            
            # Copy file
            shutil.copy2(source, backup_path)
            
            return str(backup_path)
        except:
            return None

    def restore_backup(self, backup_path: str) -> bool:
        """Restore file from backup."""
        if not self.current_project:
            return False
            
        try:
            backup = Path(backup_path)
            if not backup.exists():
                return False
                
            # Extract original filename
            original_name = backup.stem.split('.')[0]
            original_path = Path(self.current_project) / original_name
            
            # Restore file
            shutil.copy2(backup, original_path)
            
            self.append_context(f"Restored {original_name} from backup {backup.name}")
            return True
        except:
            return False
