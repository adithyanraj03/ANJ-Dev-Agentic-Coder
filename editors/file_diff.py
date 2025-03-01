#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""File diff component for comparing files."""
import curses
import os
import difflib
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from editors.editor_base import EditorComponent

class FileDiff(EditorComponent):
    """File diff component for comparing files."""
    
    def __init__(self, stdscr, filepath: Optional[Path] = None, compare_path: Optional[Path] = None):
        """Initialize file diff component.
        
        Args:
            stdscr: Curses window for display
            filepath: Path to first file
            compare_path: Path to second file to compare with
        """
        super().__init__(stdscr, filepath)
        
        # Diff state
        self.compare_path = compare_path
        self.diff_lines = []
        self.show_line_numbers = True
        self.unified_diff = True
        self.context_lines = 3
        
        # Load comparison file if provided
        if self.compare_path and self.compare_path.exists():
            self._load_comparison()
        
        # Key bindings
        self.key_bindings = {
            ord('q'): self._quit,
            ord('n'): self._next_diff,
            ord('p'): self._prev_diff,
            ord('u'): self._toggle_unified_diff,
            ord('c'): self._change_context_lines,
            ord('l'): self._toggle_line_numbers,
            ord('h'): self._show_help,
            curses.KEY_UP: lambda: self.move_cursor(-1, 0),
            curses.KEY_DOWN: lambda: self.move_cursor(1, 0),
            curses.KEY_NPAGE: self._page_down,
            curses.KEY_PPAGE: self._page_up,
        }
        
        # Generate diff if both files are available
        if self.filepath and self.compare_path:
            self._generate_diff()
    
    def _load_comparison(self):
        """Load comparison file."""
        try:
            with open(self.compare_path, 'r', encoding='utf-8') as f:
                self.compare_content = f.read().splitlines()
            self.set_status(f"Loaded comparison file: {self.compare_path.name}")
        except Exception as e:
            self.set_status(f"Error loading comparison file: {e}")
            self.compare_content = []
    
    def _generate_diff(self):
        """Generate diff between files."""
        if not self.content or not hasattr(self, 'compare_content'):
            return
            
        # Clear previous diff
        self.diff_lines = []
        self.diff_positions = []
        
        # Generate diff
        if self.unified_diff:
            diff = list(difflib.unified_diff(
                self.content,
                self.compare_content,
                fromfile=str(self.filepath),
                tofile=str(self.compare_path),
                n=self.context_lines,
                lineterm=''
            ))
        else:
            diff = list(difflib.ndiff(self.content, self.compare_content))
            
        # Store diff lines
        self.diff_lines = diff
        
        # Find positions of actual differences
        for i, line in enumerate(diff):
            if line.startswith('+') or line.startswith('-') or line.startswith('?'):
                if line.startswith('?'):
                    continue  # Skip ndiff marker lines
                self.diff_positions.append(i)
                
        self.set_status(f"Found {len(self.diff_positions)} differences")
    
    def _next_diff(self):
        """Go to next difference."""
        if not self.diff_positions:
            self.set_status("No differences found")
            return
            
        current_line = self.scroll_pos + self.cursor_y
        
        # Find next diff position after current line
        next_pos = None
        for pos in self.diff_positions:
            if pos > current_line:
                next_pos = pos
                break
                
        # Wrap around if needed
        if next_pos is None and self.diff_positions:
            next_pos = self.diff_positions[0]
            
        if next_pos is not None:
            # Adjust scroll position
            if next_pos < self.scroll_pos:
                self.scroll_pos = next_pos
            elif next_pos >= self.scroll_pos + self.height - 2:
                self.scroll_pos = next_pos - (self.height - 3)
                
            # Set cursor position
            self.cursor_y = next_pos - self.scroll_pos
            self.cursor_x = 0
            
            self.set_status(f"Difference {self.diff_positions.index(next_pos) + 1}/{len(self.diff_positions)}")
    
    def _prev_diff(self):
        """Go to previous difference."""
        if not self.diff_positions:
            self.set_status("No differences found")
            return
            
        current_line = self.scroll_pos + self.cursor_y
        
        # Find previous diff position before current line
        prev_pos = None
        for pos in reversed(self.diff_positions):
            if pos < current_line:
                prev_pos = pos
                break
                
        # Wrap around if needed
        if prev_pos is None and self.diff_positions:
            prev_pos = self.diff_positions[-1]
            
        if prev_pos is not None:
            # Adjust scroll position
            if prev_pos < self.scroll_pos:
                self.scroll_pos = prev_pos
            elif prev_pos >= self.scroll_pos + self.height - 2:
                self.scroll_pos = prev_pos - (self.height - 3)
                
            # Set cursor position
            self.cursor_y = prev_pos - self.scroll_pos
            self.cursor_x = 0
            
            self.set_status(f"Difference {self.diff_positions.index(prev_pos) + 1}/{len(self.diff_positions)}")
    
    def _toggle_unified_diff(self):
        """Toggle between unified and ndiff formats."""
        self.unified_diff = not self.unified_diff
        self._generate_diff()
        self.set_status(f"Using {'unified' if self.unified_diff else 'ndiff'} diff format")
    
    def _change_context_lines(self):
        """Change number of context lines for unified diff."""
        context = self._get_input("Context lines (0-10): ")
        try:
            context = int(context)
            if 0 <= context <= 10:
                self.context_lines = context
                self._generate_diff()
                self.set_status(f"Context lines set to {context}")
            else:
                self.set_status("Context lines must be between 0 and 10")
        except ValueError:
            self.set_status("Invalid number")
    
    def _toggle_line_numbers(self):
        """Toggle display of line numbers."""
        self.show_line_numbers = not self.show_line_numbers
        self.set_status(f"Line numbers {'on' if self.show_line_numbers else 'off'}")
    
    def _show_help(self):
        """Show help information."""
        help_text = [
            "File Diff Help",
            "-------------",
            "q: Quit",
            "n: Next difference",
            "p: Previous difference",
            "u: Toggle unified/ndiff format",
            "c: Change context lines",
            "l: Toggle line numbers",
            "h: Show this help",
            "Arrow keys: Navigate",
            "Page Up/Down: Scroll page",
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
    
    def _get_input(self, prompt: str) -> str:
        """Get input from user.
        
        Args:
            prompt: Prompt to display
            
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
        
        # Get input
        input_str = ""
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
    
    def _page_down(self):
        """Move down one page."""
        page_size = self.height - 3
        self.scroll_pos = min(self.scroll_pos + page_size, max(0, len(self.diff_lines) - page_size))
        
        # Adjust cursor if needed
        if self.scroll_pos + self.cursor_y >= len(self.diff_lines):
            self.cursor_y = max(0, len(self.diff_lines) - self.scroll_pos - 1)
    
    def _page_up(self):
        """Move up one page."""
        page_size = self.height - 3
        self.scroll_pos = max(0, self.scroll_pos - page_size)
    
    def _quit(self):
        """Quit diff viewer."""
        return False
    
    def handle_input(self, key: int) -> bool:
        """Handle keyboard input.
        
        Args:
            key: Key code from getch()
            
        Returns:
            bool: True if diff viewer should continue, False to exit
        """
        # Check for key in bindings
        if key in self.key_bindings:
            result = self.key_bindings[key]()
            if result is not None:
                return result
                
        return True
    
    def get_visible_content(self) -> List[Tuple[int, str]]:
        """Get content visible in the current view.
        
        Returns:
            List of (line_number, line_content) tuples
        """
        max_lines = self.height - 2  # Account for title and status bars
        start_line = self.scroll_pos
        end_line = min(start_line + max_lines, len(self.diff_lines))
        
        return [(i, self.diff_lines[i]) for i in range(start_line, end_line)]
    
    def draw(self):
        """Draw diff content."""
        # Calculate line number width
        line_num_width = len(str(len(self.diff_lines))) + 1 if self.show_line_numbers else 0
        
        # Get visible content
        visible_content = self.get_visible_content()
        
        # Draw content
        for i, (line_idx, line) in enumerate(visible_content):
            y = i + 1  # +1 for title bar
            
            # Draw line number if enabled
            if self.show_line_numbers:
                line_num = str(line_idx + 1).rjust(line_num_width - 1)
                self.stdscr.addstr(y, 0, line_num, self.colors["line_number"])
                self.stdscr.addstr(y, line_num_width - 1, " ")
            
            # Determine line color based on diff marker
            if line.startswith('+'):
                color = self.colors["normal"] | curses.A_BOLD | curses.color_pair(2)  # Green for additions
            elif line.startswith('-'):
                color = self.colors["normal"] | curses.A_BOLD | curses.color_pair(3)  # Yellow for deletions
            elif line.startswith('?'):
                color = self.colors["normal"] | curses.A_BOLD | curses.color_pair(4)  # Red for ndiff markers
            elif line.startswith('@'):
                color = self.colors["normal"] | curses.A_BOLD | curses.color_pair(1)  # Cyan for unified diff headers
            else:
                color = self.colors["normal"]
                
            # Draw line
            self.stdscr.addstr(y, line_num_width, line, color)
    
    def set_comparison_file(self, filepath: Path):
        """Set comparison file.
        
        Args:
            filepath: Path to comparison file
        """
        self.compare_path = filepath
        if self.compare_path.exists():
            self._load_comparison()
            if self.filepath:
                self._generate_diff()
    
    def run_diff(self, file1: Path, file2: Path) -> None:
        """Run diff between two files.
        
        Args:
            file1: First file to compare
            file2: Second file to compare
        """
        self.filepath = file1
        self.load_file()
        self.set_comparison_file(file2)
        self.run()