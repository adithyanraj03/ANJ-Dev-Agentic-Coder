#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""File browser component for navigating directory structure."""
import curses
import os
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Callable
from editors.editor_base import EditorComponent

class FileBrowser(EditorComponent):
    """File browser for navigating directory structure."""
    
    def __init__(self, stdscr, filepath: Optional[Path] = None):
        """Initialize file browser.
        
        Args:
            stdscr: Curses window for display
            filepath: Path to directory to browse (defaults to current directory)
        """
        # Use directory path instead of file path
        if filepath and filepath.is_file():
            filepath = filepath.parent
        elif not filepath:
            filepath = Path.cwd()
            
        super().__init__(stdscr, filepath)
        
        # Browser state
        self.current_dir = self.filepath
        self.files = []
        self.selected_idx = 0
        self.show_hidden = False
        self.sort_by = "name"  # name, type, size, modified
        self.reverse_sort = False
        self.filter_pattern = ""
        self.clipboard = None
        self.clipboard_op = None  # "copy" or "cut"
        
        # File operations callback
        self.file_open_callback = None
        
        # Load directory contents
        self._load_directory()
        
        # Key bindings
        self.key_bindings = {
            ord('q'): self._quit,
            ord('h'): self._show_help,
            ord('.'): self._toggle_hidden,
            ord('/'): self._filter_files,
            ord('s'): self._change_sort,
            ord('r'): self._refresh,
            ord('n'): self._new_file_or_dir,
            ord('d'): self._delete_file,
            ord('R'): self._rename_file,
            ord('c'): self._copy_file,
            ord('x'): self._cut_file,
            ord('p'): self._paste_file,
            ord('f'): self._find_file,
            10: self._open_selected,  # Enter key
            curses.KEY_UP: self._move_up,
            curses.KEY_DOWN: self._move_down,
            curses.KEY_LEFT: self._go_parent,
            curses.KEY_RIGHT: self._open_selected,
            curses.KEY_NPAGE: self._page_down,
            curses.KEY_PPAGE: self._page_up,
            curses.KEY_HOME: self._goto_top,
            curses.KEY_END: self._goto_bottom,
        }
    
    def _load_directory(self):
        """Load current directory contents."""
        self.files = []
        
        try:
            # Get all files and directories
            entries = list(self.current_dir.iterdir())
            
            # Filter hidden files if needed
            if not self.show_hidden:
                entries = [e for e in entries if not e.name.startswith('.')]
                
            # Apply filter pattern if any
            if self.filter_pattern:
                entries = [e for e in entries if self.filter_pattern.lower() in e.name.lower()]
                
            # Sort entries
            if self.sort_by == "name":
                entries.sort(key=lambda e: e.name.lower(), reverse=self.reverse_sort)
            elif self.sort_by == "type":
                entries.sort(key=lambda e: (not e.is_dir(), e.suffix.lower(), e.name.lower()), reverse=self.reverse_sort)
            elif self.sort_by == "size":
                entries.sort(key=lambda e: e.stat().st_size if e.is_file() else 0, reverse=self.reverse_sort)
            elif self.sort_by == "modified":
                entries.sort(key=lambda e: e.stat().st_mtime, reverse=self.reverse_sort)
                
            # Add parent directory entry if not at root
            if self.current_dir.parent != self.current_dir:
                self.files.append({
                    "path": self.current_dir.parent,
                    "name": "..",
                    "is_dir": True,
                    "size": 0,
                    "modified": 0
                })
                
            # Add entries
            for entry in entries:
                try:
                    stat = entry.stat()
                    self.files.append({
                        "path": entry,
                        "name": entry.name,
                        "is_dir": entry.is_dir(),
                        "size": stat.st_size if entry.is_file() else 0,
                        "modified": stat.st_mtime
                    })
                except (PermissionError, FileNotFoundError):
                    # Skip files we can't access
                    pass
                    
            # Reset selection if needed
            if self.selected_idx >= len(self.files):
                self.selected_idx = max(0, len(self.files) - 1)
                
            self.set_status(f"Loaded {len(self.files)} items")
            
        except PermissionError:
            self.set_status("Permission denied")
            self._go_parent()
        except Exception as e:
            self.set_status(f"Error: {e}")
    
    def _move_up(self):
        """Move selection up."""
        if self.files:
            self.selected_idx = (self.selected_idx - 1) % len(self.files)
            self._ensure_selection_visible()
    
    def _move_down(self):
        """Move selection down."""
        if self.files:
            self.selected_idx = (self.selected_idx + 1) % len(self.files)
            self._ensure_selection_visible()
    
    def _page_up(self):
        """Move up one page."""
        if self.files:
            page_size = self.height - 3
            self.selected_idx = max(0, self.selected_idx - page_size)
            self._ensure_selection_visible()
    
    def _page_down(self):
        """Move down one page."""
        if self.files:
            page_size = self.height - 3
            self.selected_idx = min(len(self.files) - 1, self.selected_idx + page_size)
            self._ensure_selection_visible()
    
    def _goto_top(self):
        """Go to first item."""
        if self.files:
            self.selected_idx = 0
            self._ensure_selection_visible()
    
    def _goto_bottom(self):
        """Go to last item."""
        if self.files:
            self.selected_idx = len(self.files) - 1
            self._ensure_selection_visible()
    
    def _ensure_selection_visible(self):
        """Ensure selected item is visible."""
        if not self.files:
            return
            
        # Adjust scroll position if needed
        if self.selected_idx < self.scroll_pos:
            self.scroll_pos = self.selected_idx
        elif self.selected_idx >= self.scroll_pos + self.height - 2:
            self.scroll_pos = self.selected_idx - (self.height - 3)
    
    def _go_parent(self):
        """Go to parent directory."""
        if self.current_dir.parent != self.current_dir:
            self.current_dir = self.current_dir.parent
            self._load_directory()
    
    def _open_selected(self):
        """Open selected file or directory."""
        if not self.files:
            return
            
        selected = self.files[self.selected_idx]
        
        if selected["is_dir"]:
            # Navigate to directory
            self.current_dir = selected["path"]
            self.selected_idx = 0
            self.scroll_pos = 0
            self._load_directory()
        elif self.file_open_callback:
            # Call file open callback
            self.file_open_callback(selected["path"])
            return False
    
    def _toggle_hidden(self):
        """Toggle display of hidden files."""
        self.show_hidden = not self.show_hidden
        self._load_directory()
        self.set_status(f"Hidden files {'shown' if self.show_hidden else 'hidden'}")
    
    def _filter_files(self):
        """Filter files by pattern."""
        pattern = self._get_input("Filter: ")
        self.filter_pattern = pattern
        self._load_directory()
        if pattern:
            self.set_status(f"Filtered by '{pattern}'")
        else:
            self.set_status("Filter cleared")
    
    def _change_sort(self):
        """Change sort order."""
        options = ["name", "type", "size", "modified"]
        current_idx = options.index(self.sort_by)
        
        # Cycle through sort options
        if self.reverse_sort:
            self.reverse_sort = False
            self.sort_by = options[(current_idx + 1) % len(options)]
        else:
            self.reverse_sort = True
            
        self._load_directory()
        self.set_status(f"Sorted by {self.sort_by} {'descending' if self.reverse_sort else 'ascending'}")
    
    def _refresh(self):
        """Refresh directory listing."""
        self._load_directory()
        self.set_status("Refreshed")
    
    def _new_file_or_dir(self):
        """Create new file or directory."""
        choice = self._get_input("(f)ile or (d)irectory? ")
        if choice.lower() not in ('f', 'd'):
            self.set_status("Cancelled")
            return
            
        name = self._get_input("Name: ")
        if not name:
            self.set_status("Cancelled")
            return
            
        try:
            path = self.current_dir / name
            
            if choice.lower() == 'f':
                # Create file
                path.touch()
                self.set_status(f"Created file: {name}")
            else:
                # Create directory
                path.mkdir()
                self.set_status(f"Created directory: {name}")
                
            self._load_directory()
            
            # Select new item
            for i, item in enumerate(self.files):
                if item["name"] == name:
                    self.selected_idx = i
                    self._ensure_selection_visible()
                    break
                    
        except Exception as e:
            self.set_status(f"Error: {e}")
    
    def _delete_file(self):
        """Delete selected file or directory."""
        if not self.files:
            return
            
        selected = self.files[self.selected_idx]
        
        # Don't allow deleting parent directory
        if selected["name"] == "..":
            self.set_status("Cannot delete parent directory")
            return
            
        confirm = self._get_input(f"Delete {selected['name']}? (y/N): ")
        if confirm.lower() != 'y':
            self.set_status("Cancelled")
            return
            
        try:
            path = selected["path"]
            
            if selected["is_dir"]:
                # Delete directory
                shutil.rmtree(path)
            else:
                # Delete file
                path.unlink()
                
            self.set_status(f"Deleted: {selected['name']}")
            self._load_directory()
            
        except Exception as e:
            self.set_status(f"Error: {e}")
    
    def _rename_file(self):
        """Rename selected file or directory."""
        if not self.files:
            return
            
        selected = self.files[self.selected_idx]
        
        # Don't allow renaming parent directory
        if selected["name"] == "..":
            self.set_status("Cannot rename parent directory")
            return
            
        new_name = self._get_input(f"Rename to: ", selected["name"])
        if not new_name or new_name == selected["name"]:
            self.set_status("Cancelled")
            return
            
        try:
            old_path = selected["path"]
            new_path = old_path.parent / new_name
            
            # Rename file or directory
            old_path.rename(new_path)
            
            self.set_status(f"Renamed to: {new_name}")
            self._load_directory()
            
            # Select renamed item
            for i, item in enumerate(self.files):
                if item["name"] == new_name:
                    self.selected_idx = i
                    self._ensure_selection_visible()
                    break
                    
        except Exception as e:
            self.set_status(f"Error: {e}")
    
    def _copy_file(self):
        """Copy selected file or directory to clipboard."""
        if not self.files:
            return
            
        selected = self.files[self.selected_idx]
        
        # Don't allow copying parent directory
        if selected["name"] == "..":
            self.set_status("Cannot copy parent directory")
            return
            
        self.clipboard = selected["path"]
        self.clipboard_op = "copy"
        self.set_status(f"Copied: {selected['name']}")
    
    def _cut_file(self):
        """Cut selected file or directory to clipboard."""
        if not self.files:
            return
            
        selected = self.files[self.selected_idx]
        
        # Don't allow cutting parent directory
        if selected["name"] == "..":
            self.set_status("Cannot cut parent directory")
            return
            
        self.clipboard = selected["path"]
        self.clipboard_op = "cut"
        self.set_status(f"Cut: {selected['name']}")
    
    def _paste_file(self):
        """Paste file or directory from clipboard."""
        if not self.clipboard:
            self.set_status("Clipboard is empty")
            return
            
        try:
            # Get source and destination paths
            src_path = self.clipboard
            dst_path = self.current_dir / src_path.name
            
            # Check if destination already exists
            if dst_path.exists():
                confirm = self._get_input(f"Overwrite {dst_path.name}? (y/N): ")
                if confirm.lower() != 'y':
                    self.set_status("Cancelled")
                    return
                    
            # Copy or move based on operation
            if self.clipboard_op == "copy":
                if src_path.is_dir():
                    shutil.copytree(src_path, dst_path)
                else:
                    shutil.copy2(src_path, dst_path)
                self.set_status(f"Copied: {src_path.name}")
            else:  # cut
                shutil.move(src_path, dst_path)
                self.set_status(f"Moved: {src_path.name}")
                self.clipboard = None
                self.clipboard_op = None
                
            self._load_directory()
            
            # Select pasted item
            for i, item in enumerate(self.files):
                if item["name"] == src_path.name:
                    self.selected_idx = i
                    self._ensure_selection_visible()
                    break
                    
        except Exception as e:
            self.set_status(f"Error: {e}")
    
    def _find_file(self):
        """Find file by name."""
        pattern = self._get_input("Find: ")
        if not pattern:
            self.set_status("Cancelled")
            return
            
        # Set filter and reload
        self.filter_pattern = pattern
        self._load_directory()
        
        if self.files:
            self.selected_idx = 0
            self._ensure_selection_visible()
            self.set_status(f"Found {len(self.files)} matches for '{pattern}'")
        else:
            self.set_status(f"No matches for '{pattern}'")
    
    def _show_help(self):
        """Show help information."""
        help_text = [
            "File Browser Help",
            "----------------",
            "Enter/Right: Open file/directory",
            "Left: Go to parent directory",
            "Up/Down: Navigate items",
            "q: Quit browser",
            ".: Toggle hidden files",
            "/: Filter files",
            "s: Change sort order",
            "r: Refresh listing",
            "n: New file/directory",
            "d: Delete file/directory",
            "R: Rename file/directory",
            "c: Copy to clipboard",
            "x: Cut to clipboard",
            "p: Paste from clipboard",
            "f: Find file",
            "h: Show this help",
            "Page Up/Down: Scroll page",
            "Home/End: Go to top/bottom",
        ]
        
        # Calculate position
        start_y = max(1, (self.height - len(help_text)) // 2)
        start_x = max(1, (self.width - max(len(line) for line in help_text)) // 2)
        
        # Create help window
        help_height = min(self.height - 2, len(help_text) + 4)
        help_width = min(self.width - 2, max(len(line) for line in help_text) + 4)
        help_win = curses.newwin(help_height, help_width, start_y, start_x)
        
        # Draw border
        help_win.box()
        
        # Draw content
        for i, line in enumerate(help_text):
            if i + 2 < help_height:
                help_win.addstr(i + 2, 2, line)
                
        # Show window
        help_win.refresh()
        
        # Wait for key
        help_win.getch()
    
    def _get_input(self, prompt: str, default: str = "") -> str:
        """Get input from user.
        
        Args:
            prompt: Prompt to display
            default: Default value
            
        Returns:
            str: User input
        """
        # Save current state
        curses.echo()
        curses.curs_set(1)
        
        # Clear status line
        self.stdscr.move(self.height - 1, 0)
        self.stdscr.clrtoeol()
        
        # Show prompt
        self.stdscr.addstr(self.height - 1, 0, prompt)
        
        # Show default value if any
        if default:
            self.stdscr.addstr(self.height - 1, len(prompt), default)
            
        # Get input
        input_str = default
        self.stdscr.move(self.height - 1, len(prompt) + len(input_str))
        
        while True:
            try:
                ch = self.stdscr.getch()
                if ch == 10:  # Enter
                    break
                elif ch == 27:  # Escape
                    input_str = ""
                    break
                elif ch == curses.KEY_BACKSPACE or ch == 127:  # Backspace
                    if input_str:
                        input_str = input_str[:-1]
                        self.stdscr.move(self.height - 1, len(prompt))
                        self.stdscr.clrtoeol()
                        self.stdscr.addstr(self.height - 1, len(prompt), input_str)
                else:
                    input_str += chr(ch)
            except:
                break
                
        # Restore state
        curses.noecho()
        curses.curs_set(0)
        
        return input_str
    
    def _quit(self):
        """Quit browser."""
        return False
    
    def handle_input(self, key: int) -> bool:
        """Handle keyboard input.
        
        Args:
            key: Key code from getch()
            
        Returns:
            bool: True if browser should continue, False to exit
        """
        # Check for key in bindings
        if key in self.key_bindings:
            result = self.key_bindings[key]()
            if result is not None:
                return result
                
        return True
    
    def get_visible_content(self) -> List[Tuple[int, Dict[str, Any]]]:
        """Get content visible in the current view.
        
        Returns:
            List of (index, file_info) tuples
        """
        max_lines = self.height - 2  # Account for title and status bars
        start_line = self.scroll_pos
        end_line = min(start_line + max_lines, len(self.files))
        
        return [(i, self.files[i]) for i in range(start_line, end_line)]
    
    def draw_title_bar(self):
        """Draw title bar with current directory."""
        title = f" {self.current_dir}"
        
        # Fill with spaces
        padding = " " * (self.width - len(title) - 1)
        
        try:
            self.stdscr.addstr(0, 0, title, self.colors["title"])
            self.stdscr.addstr(0, len(title), padding)
        except curses.error:
            pass
    
    def draw(self):
        """Draw browser content."""
        # Get visible content
        visible_content = self.get_visible_content()
        
        # Draw content
        for i, (idx, file_info) in enumerate(visible_content):
            y = i + 1  # +1 for title bar
            
            # Format file info
            if file_info["is_dir"]:
                name = f"📁 {file_info['name']}/"
                color = self.colors["normal"] | curses.A_BOLD | curses.color_pair(1)  # Cyan for directories
            else:
                name = f"📄 {file_info['name']}"
                color = self.colors["normal"]
                
            # Highlight selected item
            if idx == self.selected_idx:
                self.stdscr.addstr(y, 0, " " * (self.width - 1), curses.A_REVERSE)
                self.stdscr.addstr(y, 1, name, color | curses.A_REVERSE)
            else:
                self.stdscr.addstr(y, 1, name, color)
    
    def set_file_open_callback(self, callback: Callable[[Path], None]):
        """Set callback for file open action.
        
        Args:
            callback: Function to call when a file is opened
        """
        self.file_open_callback = callback
    
    def run_browser(self) -> Optional[Path]:
        """Run the browser as a standalone component.
        
        Returns:
            Optional[Path]: Selected file path or None if cancelled
        """
        selected_file = None
        
        def file_selected(path: Path):
            nonlocal selected_file
            selected_file = path
            return False
            
        self.set_file_open_callback(file_selected)
        self.run()
        
        return selected_file