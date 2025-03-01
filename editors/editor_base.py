#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Base editor component for ANJ DEV terminal."""
import os
import curses
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

class EditorComponent:
    """Base class for editor components."""
    
    def __init__(self, stdscr, filepath: Optional[Path] = None):
        """Initialize editor component.
        
        Args:
            stdscr: Curses window for display
            filepath: Optional path to file being edited
        """
        self.stdscr = stdscr
        self.filepath = filepath
        self.height, self.width = stdscr.getmaxyx()
        
        # Editor state
        self.content = []
        self.cursor_y = 0
        self.cursor_x = 0
        self.scroll_pos = 0
        self.is_modified = False
        self.status_message = ""
        self.status_time = 0
        
        # Color pairs
        self.colors = {
            "normal": curses.color_pair(0),
            "title": curses.color_pair(1) | curses.A_BOLD,
            "status": curses.color_pair(1),
            "error": curses.color_pair(4) | curses.A_BOLD,
            "highlight": curses.color_pair(6) | curses.A_REVERSE,
            "line_number": curses.color_pair(1),
        }
        
        # Load file if provided
        if self.filepath and self.filepath.exists():
            self.load_file()
    
    def resize(self, height: int, width: int):
        """Handle terminal resize.
        
        Args:
            height: New height
            width: New width
        """
        self.height = height
        self.width = width
    
    def load_file(self) -> bool:
        """Load file content.
        
        Returns:
            bool: True if file was loaded successfully
        """
        if not self.filepath or not self.filepath.exists():
            self.set_status("File not found")
            return False
            
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                self.content = f.read().splitlines()
                
            # Handle empty file
            if not self.content:
                self.content = [""]
                
            self.is_modified = False
            self.set_status(f"Loaded {self.filepath.name}")
            return True
            
        except Exception as e:
            self.set_status(f"Error loading file: {e}")
            return False
    
    def save_file(self) -> bool:
        """Save file content.
        
        Returns:
            bool: True if file was saved successfully
        """
        if not self.filepath:
            self.set_status("No file path specified")
            return False
            
        try:
            # Create parent directories if needed
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.filepath, 'w', encoding='utf-8') as f:
                f.write('\n'.join(self.content))
                
            self.is_modified = False
            self.set_status(f"Saved {self.filepath.name}")
            return True
            
        except Exception as e:
            self.set_status(f"Error saving file: {e}")
            return False
    
    def set_status(self, message: str):
        """Set status message.
        
        Args:
            message: Status message
        """
        self.status_message = message
        
        # Update status line
        try:
            self.stdscr.move(self.height - 1, 0)
            self.stdscr.clrtoeol()
            self.stdscr.addstr(self.height - 1, 0, message, self.colors["status"])
            self.stdscr.refresh()
        except curses.error:
            pass
    
    def move_cursor(self, y_diff: int, x_diff: int):
        """Move cursor by given amount.
        
        Args:
            y_diff: Vertical movement
            x_diff: Horizontal movement
        """
        # Calculate new position
        new_y = self.cursor_y + y_diff
        new_x = self.cursor_x + x_diff
        
        # Validate vertical position
        if new_y < 0:
            # Scroll up if needed
            if self.scroll_pos > 0:
                self.scroll_pos = max(0, self.scroll_pos - 1)
                new_y = 0
            else:
                new_y = 0
        elif new_y >= self.height - 2:
            # Scroll down if needed
            if self.scroll_pos + new_y < len(self.content):
                self.scroll_pos += 1
                new_y = self.height - 3
            else:
                new_y = min(self.height - 3, len(self.content) - self.scroll_pos - 1)
                
        # Validate horizontal position
        if new_x < 0:
            new_x = 0
        else:
            # Get current line length
            current_line = self.scroll_pos + new_y
            if current_line < len(self.content):
                line_length = len(self.content[current_line])
                new_x = min(new_x, line_length)
                
        # Update cursor position
        self.cursor_y = max(0, new_y)
        self.cursor_x = max(0, new_x)
    
    def get_visible_content(self) -> List[Tuple[int, str]]:
        """Get content visible in the current view.
        
        Returns:
            List of (line_number, line_content) tuples
        """
        max_lines = self.height - 2  # Account for title and status bars
        start_line = self.scroll_pos
        end_line = min(start_line + max_lines, len(self.content))
        
        return [(i, self.content[i]) for i in range(start_line, end_line)]
    
    def draw_title_bar(self):
        """Draw title bar with file information."""
        title = f" {self.filepath.name if self.filepath else 'Untitled'}"
        if self.is_modified:
            title += " [Modified]"
            
        # Add file info
        if self.filepath and self.filepath.exists():
            size = self.filepath.stat().st_size
            size_str = f"{size} bytes"
            if size > 1024:
                size_str = f"{size / 1024:.1f} KB"
            if size > 1024 * 1024:
                size_str = f"{size / (1024 * 1024):.1f} MB"
                
            title += f" - {size_str}"
            
        # Fill with spaces
        padding = " " * (self.width - len(title) - 1)
        
        try:
            self.stdscr.addstr(0, 0, title, self.colors["title"])
            self.stdscr.addstr(0, len(title), padding)
        except curses.error:
            pass
    
    def draw_status_bar(self):
        """Draw status bar with cursor position and status message."""
        # Create status line
        status = f" Ln {self.scroll_pos + self.cursor_y + 1}, Col {self.cursor_x + 1}"
        
        # Add mode if applicable
        if hasattr(self, 'mode'):
            status += f" | {self.mode.upper()}"
            
        # Add file type if applicable
        if self.filepath:
            status += f" | {self.filepath.suffix[1:].upper()}"
            
        # Add status message
        if self.status_message:
            message = f" | {self.status_message}"
            status += message
            
        # Fill with spaces
        padding = " " * (self.width - len(status) - 1)
        
        try:
            self.stdscr.addstr(self.height - 1, 0, status, self.colors["status"])
            self.stdscr.addstr(self.height - 1, len(status), padding)
        except curses.error:
            pass
    
    def draw(self):
        """Draw editor content. To be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement draw()")
    
    def handle_input(self, key: int) -> bool:
        """Handle keyboard input. To be implemented by subclasses.
        
        Args:
            key: Key code from getch()
            
        Returns:
            bool: True if editor should continue, False to exit
        """
        raise NotImplementedError("Subclasses must implement handle_input()")
    
    def run(self) -> Optional[Any]:
        """Run editor main loop.
        
        Returns:
            Optional[Any]: Result of editor operation
        """
        try:
            # Hide cursor initially
            curses.curs_set(0)
            
            # Enable keypad
            self.stdscr.keypad(True)
            
            # Main loop
            while True:
                # Handle resize if needed
                new_height, new_width = self.stdscr.getmaxyx()
                if new_height != self.height or new_width != self.width:
                    self.resize(new_height, new_width)
                
                # Clear screen
                self.stdscr.clear()
                
                # Draw components
                self.draw_title_bar()
                self.draw()
                self.draw_status_bar()
                
                # Position cursor
                try:
                    self.stdscr.move(self.cursor_y + 1, self.cursor_x)
                except curses.error:
                    pass
                
                # Refresh screen
                self.stdscr.refresh()
                
                # Get input
                key = self.stdscr.getch()
                
                # Handle input
                if not self.handle_input(key):
                    break
                    
            # Return result
            return self.is_modified
            
        except KeyboardInterrupt:
            return None
        except Exception as e:
            self.set_status(f"Error: {e}")
            return None
        finally:
            # Restore cursor
            curses.curs_set(1)