#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Component registry for ANJ DEV terminal."""
import os
import curses
from pathlib import Path
from typing import Optional, Dict, Any, List, Type, Union

class ComponentRegistry:
    """Registry for managing components in ANJ DEV terminal."""
    
    def __init__(self, project_root: Path, llm_handler):
        """Initialize component registry.
        
        Args:
            project_root: Project root directory
            llm_handler: LLM handler for code generation
        """
        self.project_root = project_root
        self.llm_handler = llm_handler
        self.stdscr = None
        
        # Component instances
        self.editors = {}
        self.terminals = {}
        self.test_managers = {}
        self.dependency_managers = {}
        
        # Component classes (lazy loaded)
        self._editor_classes = {}
        self._terminal_classes = {}
        self._test_classes = {}
        self._dependency_classes = {}
    
    def set_screen(self, stdscr):
        """Set curses screen for components.
        
        Args:
            stdscr: Curses window for display
        """
        self.stdscr = stdscr
        
        # Initialize color pairs if needed
        if curses.has_colors():
            self._init_colors()
    
    def _init_colors(self):
        """Initialize color pairs."""
        # Check if colors already initialized
        if curses.color_pair(1) == 0:
            curses.start_color()
            curses.use_default_colors()
            
            # Define color pairs
            curses.init_pair(1, curses.COLOR_CYAN, -1)     # Info/title
            curses.init_pair(2, curses.COLOR_GREEN, -1)    # Success
            curses.init_pair(3, curses.COLOR_YELLOW, -1)   # Warning
            curses.init_pair(4, curses.COLOR_RED, -1)      # Error
            curses.init_pair(5, curses.COLOR_WHITE, -1)    # Normal
            curses.init_pair(6, curses.COLOR_MAGENTA, -1)  # Highlight
    
    def get_editor(self, editor_type: str, filepath: Optional[Path] = None):
        """Get editor component.
        
        Args:
            editor_type: Type of editor ('text', 'view', 'diff', 'browser')
            filepath: Optional path to file
            
        Returns:
            Editor component instance
        """
        if not self.stdscr:
            return None
            
        # Lazy load editor classes
        if not self._editor_classes:
            self._load_editor_classes()
            
        # Get editor class
        editor_class = self._editor_classes.get(editor_type)
        if not editor_class:
            return None
            
        # Create key for caching
        key = f"{editor_type}:{str(filepath) if filepath else 'none'}"
        
        # Return cached instance if available
        if key in self.editors:
            return self.editors[key]
            
        # Create new instance
        try:
            editor = editor_class(self.stdscr, filepath)
            self.editors[key] = editor
            return editor
        except Exception as e:
            print(f"Error creating editor: {e}")
            return None
    
    def _load_editor_classes(self):
        """Load editor classes."""
        try:
            from editors.text_editor import TextEditor
            from editors.file_viewer import FileViewer
            from editors.file_diff import FileDiff
            from editors.file_browser import FileBrowser
            
            self._editor_classes = {
                'text': TextEditor,
                'view': FileViewer,
                'diff': FileDiff,
                'browser': FileBrowser
            }
        except ImportError as e:
            print(f"Error loading editor classes: {e}")
            
    def get_terminal_manager(self):
        """Get terminal manager.
        
        Returns:
            Terminal manager instance
        """
        if not self.stdscr:
            return None
            
        # Lazy load terminal manager
        if not self._terminal_classes:
            try:
                from terminal.terminal_manager import TerminalManager
                self._terminal_classes['manager'] = TerminalManager
            except ImportError as e:
                print(f"Error loading terminal manager: {e}")
                return None
                
        # Create new instance if needed
        if 'manager' not in self.terminals:
            try:
                manager_class = self._terminal_classes.get('manager')
                if manager_class:
                    self.terminals['manager'] = manager_class(self.project_root)
            except Exception as e:
                print(f"Error creating terminal manager: {e}")
                return None
                
        return self.terminals.get('manager')
    
    def get_terminal_interface(self):
        """Get terminal interface.
        
        Returns:
            Terminal interface instance
        """
        if not self.stdscr:
            return None
            
        # Get terminal manager
        manager = self.get_terminal_manager()
        if not manager:
            return None
            
        # Lazy load terminal interface
        if not self._terminal_classes.get('interface'):
            try:
                from terminal.terminal_interface import TerminalInterface
                self._terminal_classes['interface'] = TerminalInterface
            except ImportError as e:
                print(f"Error loading terminal interface: {e}")
                return None
                
        # Create new instance if needed
        if 'interface' not in self.terminals:
            try:
                interface_class = self._terminal_classes.get('interface')
                if interface_class:
                    self.terminals['interface'] = interface_class(self.stdscr, manager)
            except Exception as e:
                print(f"Error creating terminal interface: {e}")
                return None
                
        return self.terminals.get('interface')
    
    def get_test_manager(self):
        """Get test manager.
        
        Returns:
            Test manager instance
        """
        if not self.stdscr:
            return None
            
        # Lazy load test manager
        if not self._test_classes:
            try:
                from testing.test_framework import TestManager
                self._test_classes['manager'] = TestManager
            except ImportError as e:
                print(f"Error loading test manager: {e}")
                return None
                
        # Create new instance if needed
        if 'manager' not in self.test_managers:
            try:
                manager_class = self._test_classes.get('manager')
                if manager_class:
                    self.test_managers['manager'] = manager_class(self.project_root, self.llm_handler, self.stdscr)
            except Exception as e:
                print(f"Error creating test manager: {e}")
                return None
                
        return self.test_managers.get('manager')
    
    def get_dependency_manager(self):
        """Get dependency manager.
        
        Returns:
            Dependency manager instance
        """
        if not self._dependency_classes:
            try:
                from dependencies.dependency_manager import DependencyManager
                self._dependency_classes['manager'] = DependencyManager
            except ImportError as e:
                print(f"Error loading dependency manager: {e}")
                return None
                
        # Create new instance if needed
        if 'manager' not in self.dependency_managers:
            try:
                manager_class = self._dependency_classes.get('manager')
                if manager_class:
                    self.dependency_managers['manager'] = manager_class(self.project_root)
            except Exception as e:
                print(f"Error creating dependency manager: {e}")
                return None
                
        return self.dependency_managers.get('manager')
    def run_tests(self, filepath: Optional[Path] = None):
        """Run tests for specified file or all tests.
        
        Args:
            filepath: Optional path to test specific file
        """
        test_manager = self.get_test_manager()
        if not test_manager:
            return
            
        if filepath:
            # Generate and run tests for specific file
            test_code = test_manager.generate_tests(filepath)
            if test_code:
                test_file = filepath.parent / f"test_{filepath.stem}.py"
                with open(test_file, 'w') as f:
                    f.write(test_code)
                test_manager.run_tests([test_file])
        else:
            # Run all tests
            test_manager.run_tests()
            
    def manage_dependencies(self, command: str, *args, **kwargs) -> bool:
        """Manage project dependencies.
        
        Args:
            command: Dependency command ('install', 'add', 'remove', 'update')
            *args: Command arguments
            **kwargs: Command keyword arguments
            
        Returns:
            bool: True if operation was successful
        """
        dep_manager = self.get_dependency_manager()
        if not dep_manager:
            return False
            
        try:
            if command == 'install':
                return dep_manager.install_dependencies()
            elif command == 'add':
                return dep_manager.add_dependency(*args, **kwargs)
            elif command == 'remove':
                return dep_manager.remove_dependency(*args)
            elif command == 'update':
                return dep_manager.update_dependencies()
            return False
            
        except Exception as e:
            print(f"Error in dependency operation: {e}")
            return False
            
    def cleanup(self):
        """Clean up all components."""
        # Close all editors
        for editor in self.editors.values():
            try:
                if hasattr(editor, 'cleanup'):
                    editor.cleanup()
            except Exception as e:
                print(f"Error cleaning up editor: {e}")
        self.editors.clear()
        
        # Clean up terminals
        for terminal in self.terminals.values():
            try:
                if hasattr(terminal, 'cleanup'):
                    terminal.cleanup()
            except Exception as e:
                print(f"Error cleaning up terminal: {e}")
        self.terminals.clear()
            
        # Clean up test managers
        for test_manager in self.test_managers.values():
            try:
                if hasattr(test_manager, 'cleanup'):
                    test_manager.cleanup()
            except Exception as e:
                print(f"Error cleaning up test manager: {e}")
        self.test_managers.clear()
        
        # Clean up dependency managers
        for dep_manager in self.dependency_managers.values():
            try:
                if hasattr(dep_manager, 'cleanup'):
                    dep_manager.cleanup()
            except Exception as e:
                print(f"Error cleaning up dependency manager: {e}")
        self.dependency_managers.clear()
