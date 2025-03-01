#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""File viewer component with syntax highlighting."""
import curses
import os
import re
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from pygments import highlight
from pygments.lexers import get_lexer_for_filename, TextLexer
from pygments.formatters import Terminal256Formatter
from editors.editor_base import EditorComponent

class FileViewer(EditorComponent):
    """File viewer with syntax highlighting and search capabilities."""
    
    def __init__(self, stdscr, filepath: Optional[Path] = None):
        """Initialize file viewer.
        
        Args:
            stdscr: Curses window for display
            filepath: Path to file to view
        """
        super().__init__(stdscr, filepath)
        
        # Viewer state
        self.search_term = ""
        self.search_results = []
        self.current_search_idx = -1
        self.show_line_numbers = True
        self.syntax_highlighting = True
        self.wrap_lines = False
        
        # Initialize syntax highlighting
        self._init_syntax_highlighting()
        
        # Key bindings
        self.key_bindings = {
            ord('q'): self._quit,
            ord('/'): self._start_search,
            ord('n'): self._next_search_result,
            ord('N'): self._prev_search_result,
            ord('g'): self._goto_line,
            ord('G'): self._goto_end,
            ord('0'): self._goto_line_start,
            ord('$'): self._goto_line_end,
            ord('h'): self._show_help,
            ord('l'): self._toggle_line_numbers,
            ord('s'): self._toggle_syntax_highlighting,
            ord('w'): self._toggle_line_wrap,
            curses.KEY_UP: lambda: self.move_cursor(-1, 0),
            curses.KEY_DOWN: lambda: self.move_cursor(1, 0),
            curses.KEY_LEFT: lambda: self.move_cursor(0, -1),
            curses.KEY_RIGHT: lambda: self.move_cursor(0, 1),
            curses.KEY_NPAGE: self._page_down,
            curses.KEY_PPAGE: self._page_up,
            curses.KEY_HOME: self._goto_line_start,
            curses.KEY_END: self._goto_line_end,
        }
    
    def _init_syntax_highlighting(self):
        """Initialize syntax highlighting for current file."""
        self.lexer = None
        self.formatter = Terminal256Formatter()
        
        if self.filepath:
            try:
                self.lexer = get_lexer_for_filename(self.filepath.name)
            except:
                self.lexer = TextLexer()
        else:
            self.lexer = TextLexer()
    
    def _start_search(self):
        """Start search mode."""
        self.search_term = self._get_input("Search: ")
        if self.search_term:
            self._perform_search()
    
    def _perform_search(self):
        """Perform search with current term."""
        self.search_results = []
        
        for i, line in enumerate(self.content):
            for match in re.finditer(re.escape(self.search_term), line):
                self.search_results.append((i, match.start(), match.end()))
                
        if self.search_results:
            self.current_search_idx = 0
            self._goto_search_result(0)
            self.set_status(f"Found {len(self.search_results)} matches")
        else:
            self.set_status(f"No matches for '{self.search_term}'")
    
    def _next_search_result(self):
        """Go to next search result."""
        if not self.search_results:
            self.set_status("No search results")
            return
            
        self.current_search_idx = (self.current_search_idx + 1) % len(self.search_results)
        self._goto_search_result(self.current_search_idx)
    
    def _prev_search_result(self):
        """Go to previous search result."""
        if not self.search_results:
            self.set_status("No search results")
            return
            
        self.current_search_idx = (self.current_search_idx - 1) % len(self.search_results)
        self._goto_search_result(self.current_search_idx)
    
    def _goto_search_result(self, idx: int):
        """Go to specific search result.
        
        Args:
            idx: Index of search result
        """
        if not self.search_results or idx >= len(self.search_results):
            return
            
        line_idx, start, end = self.search_results[idx]
        
        # Adjust scroll position
        if line_idx < self.scroll_pos:
            self.scroll_pos = line_idx
        elif line_idx >= self.scroll_pos + self.height - 2:
            self.scroll_pos = line_idx - (self.height - 3)
            
        # Set cursor position
        self.cursor_y = line_idx - self.scroll_pos
        self.cursor_x = start
        
        self.set_status(f"Match {idx + 1}/{len(self.search_results)}")
    
    def _goto_line(self):
        """Go to specific line number."""
        line_num = self._get_input("Go to line: ")
        try:
            line_num = int(line_num)
            if 1 <= line_num <= len(self.content):
                # Adjust scroll position
                if line_num - 1 < self.scroll_pos:
                    self.scroll_pos = line_num - 1
                elif line_num - 1 >= self.scroll_pos + self.height - 2:
                    self.scroll_pos = line_num - 1 - (self.height - 3)
                    
                # Set cursor position
                self.cursor_y = line_num - 1 - self.scroll_pos
                self.cursor_x = 0
                self.set_status(f"Moved to line {line_num}")
            else:
                self.set_status(f"Line number out of range (1-{len(self.content)})")
        except ValueError:
            self.set_status("Invalid line number")
    
    def _goto_end(self):
        """Go to end of file."""
        if len(self.content) > 0:
            # Adjust scroll position
            if len(self.content) > self.height - 2:
                self.scroll_pos = len(self.content) - (self.height - 2)
                self.cursor_y = self.height - 3
            else:
                self.scroll_pos = 0
                self.cursor_y = len(self.content) - 1
                
            # Set cursor to end of line
            self.cursor_x = len(self.content[self.scroll_pos + self.cursor_y])
    
    def _goto_line_start(self):
        """Go to start of current line."""
        self.cursor_x = 0
    
    def _goto_line_end(self):
        """Go to end of current line."""
        current_line = self.scroll_pos + self.cursor_y
        if current_line < len(self.content):
            self.cursor_x = len(self.content[current_line])
    
    def _page_down(self):
        """Move down one page."""
        page_size = self.height - 3
        self.scroll_pos = min(self.scroll_pos + page_size, max(0, len(self.content) - page_size))
        
        # Adjust cursor if needed
        if self.scroll_pos + self.cursor_y >= len(self.content):
            self.cursor_y = max(0, len(self.content) - self.scroll_pos - 1)
    
    def _page_up(self):
        """Move up one page."""
        page_size = self.height - 3
        self.scroll_pos = max(0, self.scroll_pos - page_size)
    
    def _toggle_line_numbers(self):
        """Toggle display of line numbers."""
        self.show_line_numbers = not self.show_line_numbers
        self.set_status(f"Line numbers {'on' if self.show_line_numbers else 'off'}")
    
    def _toggle_syntax_highlighting(self):
        """Toggle syntax highlighting."""
        self.syntax_highlighting = not self.syntax_highlighting
        self.set_status(f"Syntax highlighting {'on' if self.syntax_highlighting else 'off'}")
    
    def _toggle_line_wrap(self):
        """Toggle line wrapping."""
        self.wrap_lines = not self.wrap_lines
        self.set_status(f"Line wrapping {'on' if self.wrap_lines else 'off'}")
    
    def _show_help(self):
        """Show help information."""
        help_text = [
            "File Viewer Help",
            "---------------",
            "q: Quit",
            "/: Search",
            "n: Next search result",
            "N: Previous search result",
            "g: Go to line",
            "G: Go to end of file",
            "0: Go to start of line",
            "$: Go to end of line",
            "h: Show this help",
            "l: Toggle line numbers",
            "s: Toggle syntax highlighting",
            "w: Toggle line wrapping",
            "Arrow keys: Navigate",
            "Page Up/Down: Scroll page",
            "Home/End: Go to start/end of line",
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
    
    def _quit(self):
        """Quit viewer."""
        return False
    
    def handle_input(self, key: int) -> bool:
        """Handle keyboard input.
        
        Args:
            key: Key code from getch()
            
        Returns:
            bool: True if viewer should continue, False to exit
        """
        # Check for key in bindings
        if key in self.key_bindings:
            result = self.key_bindings[key]()
            if result is not None:
                return result
                
        return True
    
    def draw(self):
        """Draw viewer content."""
        # Calculate line number width
        line_num_width = len(str(len(self.content))) + 1 if self.show_line_numbers else 0
        
        # Get visible content
        visible_content = self.get_visible_content()
        
        # Apply syntax highlighting if enabled
        highlighted_lines = {}
        if self.syntax_highlighting and self.lexer:
            # Join visible content for highlighting
            content_str = "\n".join([line for _, line in visible_content])
            
            # Highlight content
            highlighted = highlight(content_str, self.lexer, self.formatter)
            
            # Split back into lines
            highlighted_lines = dict(enumerate(highlighted.splitlines()))
        
        # Draw content
        for i, (line_idx, line) in enumerate(visible_content):
            y = i + 1  # +1 for title bar
            
            # Draw line number if enabled
            if self.show_line_numbers:
                line_num = str(line_idx + 1).rjust(line_num_width - 1)
                self.stdscr.addstr(y, 0, line_num, self.colors["line_number"])
                self.stdscr.addstr(y, line_num_width - 1, " ")
            
            # Handle line wrapping if enabled
            if self.wrap_lines and len(line) > self.width - line_num_width - 1:
                # Calculate available width
                avail_width = self.width - line_num_width - 1
                
                # Split line into chunks
                chunks = [line[i:i+avail_width] for i in range(0, len(line), avail_width)]
                
                # Draw first chunk
                if self.syntax_highlighting and line_idx in highlighted_lines:
                    # Draw syntax highlighted line (first chunk only)
                    highlighted_line = highlighted_lines[line_idx]
                    self.stdscr.addstr(y, line_num_width, highlighted_line[:avail_width])
                else:
                    self.stdscr.addstr(y, line_num_width, chunks[0])
                    
                # Draw remaining chunks
                for j, chunk in enumerate(chunks[1:], 1):
                    if y + j < self.height - 1:  # Ensure we don't draw past bottom
                        self.stdscr.addstr(y + j, line_num_width, chunk)
            else:
                # Draw single line
                if self.syntax_highlighting and line_idx in highlighted_lines:
                    # Draw syntax highlighted line
                    highlighted_line = highlighted_lines[line_idx]
                    self.stdscr.addstr(y, line_num_width, highlighted_line)
                else:
                    self.stdscr.addstr(y, line_num_width, line)
    
    def run_viewer(self) -> None:
        """Run the viewer as a standalone component."""
        try:
            self.run()
        except Exception as e:
            self.set_status(f"Error: {e}")