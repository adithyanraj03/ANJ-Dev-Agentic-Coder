#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Text editor component with syntax highlighting."""
import curses
import os
import re
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from pygments import highlight
from pygments.lexers import get_lexer_for_filename, TextLexer
from pygments.formatters import Terminal256Formatter
from pygments.token import Token
from editors.editor_base import EditorComponent

class TextEditor(EditorComponent):
    """Text editor with syntax highlighting and editing capabilities."""
    
    def __init__(self, stdscr, filepath: Optional[Path] = None):
        """Initialize text editor.
        
        Args:
            stdscr: Curses window for display
            filepath: Optional path to file being edited
        """
        super().__init__(stdscr, filepath)
        
        # Editor state
        self.mode = "normal"  # normal, insert, select
        self.clipboard = []
        self.undo_stack = []
        self.redo_stack = []
        self.search_term = ""
        self.search_results = []
        self.current_search_idx = -1
        self.selection_start = None
        self.show_line_numbers = True
        self.tab_size = 4
        self.syntax_highlighting = True
        
        # Initialize syntax highlighting
        self._init_syntax_highlighting()
        
        # Key bindings
        self.key_bindings = {
            "normal": {
                ord('i'): self._enter_insert_mode,
                ord('a'): self._append_at_cursor,
                ord('o'): self._open_line_below,
                ord('O'): self._open_line_above,
                ord('x'): self._delete_char,
                ord('d'): self._delete_line,
                ord('y'): self._yank_line,
                ord('p'): self._paste_clipboard,
                ord('/'): self._start_search,
                ord('n'): self._next_search_result,
                ord('N'): self._prev_search_result,
                ord('u'): self._undo,
                ord('r'): self._redo,
                ord('g'): self._goto_line,
                ord('G'): self._goto_end,
                ord('0'): self._goto_line_start,
                ord('$'): self._goto_line_end,
                ord('v'): self._enter_select_mode,
                ord('s'): self._save_file,
                ord('q'): self._quit,
                curses.KEY_UP: lambda: self.move_cursor(-1, 0),
                curses.KEY_DOWN: lambda: self.move_cursor(1, 0),
                curses.KEY_LEFT: lambda: self.move_cursor(0, -1),
                curses.KEY_RIGHT: lambda: self.move_cursor(0, 1),
                curses.KEY_NPAGE: self._page_down,
                curses.KEY_PPAGE: self._page_up,
                curses.KEY_HOME: self._goto_line_start,
                curses.KEY_END: self._goto_line_end,
                curses.KEY_F5: self._toggle_line_numbers,
                curses.KEY_F6: self._toggle_syntax_highlighting,
            },
            "insert": {
                curses.KEY_UP: lambda: self.move_cursor(-1, 0),
                curses.KEY_DOWN: lambda: self.move_cursor(1, 0),
                curses.KEY_LEFT: lambda: self.move_cursor(0, -1),
                curses.KEY_RIGHT: lambda: self.move_cursor(0, 1),
                curses.KEY_BACKSPACE: self._backspace,
                curses.KEY_DC: self._delete_char,
                curses.KEY_HOME: self._goto_line_start,
                curses.KEY_END: self._goto_line_end,
                curses.KEY_ENTER: self._insert_newline,
                9: self._insert_tab,  # Tab key
                27: self._enter_normal_mode,  # Escape key
            },
            "select": {
                curses.KEY_UP: self._extend_selection_up,
                curses.KEY_DOWN: self._extend_selection_down,
                curses.KEY_LEFT: self._extend_selection_left,
                curses.KEY_RIGHT: self._extend_selection_right,
                ord('y'): self._yank_selection,
                ord('d'): self._delete_selection,
                ord('c'): self._change_selection,
                27: self._enter_normal_mode,  # Escape key
            }
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
    
    def _save_snapshot(self):
        """Save current state for undo/redo."""
        self.undo_stack.append({
            'content': self.content.copy(),
            'cursor_y': self.cursor_y,
            'cursor_x': self.cursor_x,
        })
        self.redo_stack = []  # Clear redo stack on new changes
    
    def _undo(self):
        """Undo last change."""
        if not self.undo_stack:
            self.set_status("Nothing to undo")
            return
            
        # Save current state to redo stack
        self.redo_stack.append({
            'content': self.content.copy(),
            'cursor_y': self.cursor_y,
            'cursor_x': self.cursor_x,
            'scroll_pos': self.scroll_pos
        })
        
        # Restore previous state
        state = self.undo_stack.pop()
        self.content = state['content']
        self.cursor_y = state['cursor_y']
        self.cursor_x = state['cursor_x']
        self.scroll_pos = state['scroll_pos']
        self.is_modified = True
        self.set_status("Undo")
    
    def _redo(self):
        """Redo last undone change."""
        if not self.redo_stack:
            self.set_status("Nothing to redo")
            return
            
        # Save current state to undo stack
        self.undo_stack.append({
            'content': self.content.copy(),
            'cursor_y': self.cursor_y,
            'cursor_x': self.cursor_x,
            'scroll_pos': self.scroll_pos
        })
        
        # Restore redo state
        state = self.redo_stack.pop()
        self.content = state['content']
        self.cursor_y = state['cursor_y']
        self.cursor_x = state['cursor_x']
        self.scroll_pos = state['scroll_pos']
        self.is_modified = True
        self.set_status("Redo")
    
    def _enter_normal_mode(self):
        """Enter normal mode."""
        self.mode = "normal"
        self.selection_start = None
        self.set_status("Normal mode")
    
    def _enter_insert_mode(self):
        """Enter insert mode."""
        self.mode = "insert"
        self.set_status("Insert mode")
    
    def _enter_select_mode(self):
        """Enter select mode."""
        self.mode = "select"
        self.selection_start = (self.scroll_pos + self.cursor_y, self.cursor_x)
        self.set_status("Select mode")
    
    def _append_at_cursor(self):
        """Move cursor right and enter insert mode."""
        if self.scroll_pos + self.cursor_y < len(self.content):
            line = self.content[self.scroll_pos + self.cursor_y]
            if line:
                self.move_cursor(0, 1)
        self._enter_insert_mode()
    
    def _open_line_below(self):
        """Open new line below current line and enter insert mode."""
        self._save_snapshot()
        
        current_line = self.scroll_pos + self.cursor_y
        if current_line >= len(self.content):
            self.content.append("")
        else:
            self.content.insert(current_line + 1, "")
            
        self.move_cursor(1, 0)
        self.cursor_x = 0
        self._enter_insert_mode()
        self.is_modified = True
    
    def _open_line_above(self):
        """Open new line above current line and enter insert mode."""
        self._save_snapshot()
        
        current_line = self.scroll_pos + self.cursor_y
        self.content.insert(current_line, "")
        self.cursor_x = 0
        self._enter_insert_mode()
        self.is_modified = True
    
    def _delete_char(self):
        """Delete character at cursor."""
        self._save_snapshot()
        
        current_line = self.scroll_pos + self.cursor_y
        if current_line >= len(self.content):
            return
            
        line = self.content[current_line]
        if self.cursor_x < len(line):
            # Delete character at cursor
            new_line = line[:self.cursor_x] + line[self.cursor_x + 1:]
            self.content[current_line] = new_line
            self.is_modified = True
        elif current_line < len(self.content) - 1:
            # Join with next line if at end of line
            next_line = self.content[current_line + 1]
            self.content[current_line] = line + next_line
            self.content.pop(current_line + 1)
            self.is_modified = True
    
    def _backspace(self):
        """Delete character before cursor."""
        self._save_snapshot()
        
        current_line = self.scroll_pos + self.cursor_y
        if current_line >= len(self.content):
            return
            
        line = self.content[current_line]
        if self.cursor_x > 0:
            # Delete character before cursor
            new_line = line[:self.cursor_x - 1] + line[self.cursor_x:]
            self.content[current_line] = new_line
            self.move_cursor(0, -1)
            self.is_modified = True
        elif current_line > 0:
            # Join with previous line if at start of line
            prev_line = self.content[current_line - 1]
            self.cursor_x = len(prev_line)
            self.content[current_line - 1] = prev_line + line
            self.content.pop(current_line)
            self.move_cursor(-1, 0)
            self.cursor_x = len(prev_line)
            self.is_modified = True
    
    def _delete_line(self):
        """Delete current line."""
        self._save_snapshot()
        
        current_line = self.scroll_pos + self.cursor_y
        if current_line < len(self.content):
            # Copy to clipboard
            self.clipboard = [self.content[current_line]]
            
            # Delete line
            self.content.pop(current_line)
            
            # Adjust cursor if needed
            if len(self.content) == 0:
                self.content = [""]
                self.cursor_x = 0
            elif current_line >= len(self.content):
                self.move_cursor(-1, 0)
                self.cursor_x = 0
                
            self.is_modified = True
            self.set_status(f"Deleted line {current_line + 1}")
    
    def _yank_line(self):
        """Copy current line to clipboard."""
        current_line = self.scroll_pos + self.cursor_y
        if current_line < len(self.content):
            self.clipboard = [self.content[current_line]]
            self.set_status(f"Yanked line {current_line + 1}")
    
    def _paste_clipboard(self):
        """Paste clipboard content at cursor."""
        if not self.clipboard:
            self.set_status("Clipboard is empty")
            return
            
        self._save_snapshot()
        
        current_line = self.scroll_pos + self.cursor_y
        if current_line >= len(self.content):
            self.content.extend(self.clipboard)
        else:
            for i, line in enumerate(self.clipboard):
                self.content.insert(current_line + i, line)
                
        self.is_modified = True
        self.set_status(f"Pasted {len(self.clipboard)} line(s)")
    
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
    
    def _insert_char(self, ch: int):
        """Insert character at cursor.
        
        Args:
            ch: Character code
        """
        self._save_snapshot()
        
        current_line = self.scroll_pos + self.cursor_y
        if current_line >= len(self.content):
            self.content.append("")
            
        line = self.content[current_line]
        new_line = line[:self.cursor_x] + chr(ch) + line[self.cursor_x:]
        self.content[current_line] = new_line
        self.move_cursor(0, 1)
        self.is_modified = True
    
    def _insert_newline(self):
        """Insert newline at cursor."""
        self._save_snapshot()
        
        current_line = self.scroll_pos + self.cursor_y
        if current_line >= len(self.content):
            self.content.append("")
            self.move_cursor(1, 0)
            return
            
        line = self.content[current_line]
        
        # Split line at cursor
        first_part = line[:self.cursor_x]
        second_part = line[self.cursor_x:]
        
        # Update current line and insert new line
        self.content[current_line] = first_part
        self.content.insert(current_line + 1, second_part)
        
        # Move cursor to beginning of new line
        self.move_cursor(1, 0)
        self.cursor_x = 0
        self.is_modified = True
    
    def _insert_tab(self):
        """Insert tab (spaces) at cursor."""
        self._save_snapshot()
        
        # Insert spaces for tab
        spaces = " " * self.tab_size
        current_line = self.scroll_pos + self.cursor_y
        
        if current_line >= len(self.content):
            self.content.append("")
            
        line = self.content[current_line]
        new_line = line[:self.cursor_x] + spaces + line[self.cursor_x:]
        self.content[current_line] = new_line
        self.move_cursor(0, self.tab_size)
        self.is_modified = True
    
    def _extend_selection_up(self):
        """Extend selection upward."""
        self.move_cursor(-1, 0)
    
    def _extend_selection_down(self):
        """Extend selection downward."""
        self.move_cursor(1, 0)
    
    def _extend_selection_left(self):
        """Extend selection leftward."""
        self.move_cursor(0, -1)
    
    def _extend_selection_right(self):
        """Extend selection rightward."""
        self.move_cursor(0, 1)
    
    def _get_selection(self) -> List[str]:
        """Get selected text.
        
        Returns:
            List[str]: Selected lines
        """
        if not self.selection_start:
            return []
            
        start_line, start_col = self.selection_start
        end_line, end_col = self.scroll_pos + self.cursor_y, self.cursor_x
        
        # Ensure start is before end
        if start_line > end_line or (start_line == end_line and start_col > end_col):
            start_line, end_line = end_line, start_line
            start_col, end_col = end_col, start_col
            
        # Extract selected text
        selected = []
        for i in range(start_line, end_line + 1):
            if i >= len(self.content):
                break
                
            line = self.content[i]
            if start_line == end_line:
                # Selection on single line
                selected.append(line[start_col:end_col])
            elif i == start_line:
                # First line of multi-line selection
                selected.append(line[start_col:])
            elif i == end_line:
                # Last line of multi-line selection
                selected.append(line[:end_col])
            else:
                # Middle line of multi-line selection
                selected.append(line)
                
        return selected
    
    def _yank_selection(self):
        """Copy selection to clipboard."""
        selected = self._get_selection()
        if selected:
            self.clipboard = selected
            self.set_status(f"Yanked {len(selected)} line(s)")
        self._enter_normal_mode()
    
    def _delete_selection(self):
        """Delete selected text."""
        if not self.selection_start:
            return
            
        self._save_snapshot()
        
        start_line, start_col = self.selection_start
        end_line, end_col = self.scroll_pos + self.cursor_y, self.cursor_x
        
        # Ensure start is before end
        if start_line > end_line or (start_line == end_line and start_col > end_col):
            start_line, end_line = end_line, start_line
            start_col, end_col = end_col, start_col
            
        # Save selection to clipboard
        self.clipboard = self._get_selection()
        
        # Delete selection
        if start_line == end_line:
            # Selection on single line
            line = self.content[start_line]
            self.content[start_line] = line[:start_col] + line[end_col:]
        else:
            # Multi-line selection
            first_line = self.content[start_line]
            last_line = self.content[end_line]
            
            # Combine first and last lines
            self.content[start_line] = first_line[:start_col] + last_line[end_col:]
            
            # Remove lines in between
            for _ in range(end_line - start_line):
                self.content.pop(start_line + 1)
                
        # Move cursor to start of selection
        self.scroll_pos = start_line
        self.cursor_y = 0
        self.cursor_x = start_col
        
        self.is_modified = True
        self._enter_normal_mode()
    
    def _change_selection(self):
        """Delete selection and enter insert mode."""
        self._delete_selection()
        self._enter_insert_mode()
    
    def _save_file(self):
        """Save file."""
        if not self.filepath:
            self.set_status("No file path specified")
            return
            
        if self.save_file():
            self.set_status(f"Saved {self.filepath.name}")
    
    def _quit(self):
        """Quit editor."""
        if self.is_modified:
            choice = self._get_input("Save changes before quitting? (y/n): ")
            if choice.lower() == 'y':
                self._save_file()
                return False
            elif choice.lower() == 'n':
                return False
            else:
                self.set_status("Quit cancelled")
                return True
        return False
    
    def handle_input(self, key: int) -> bool:
        """Handle keyboard input.
        
        Args:
            key: Key code from getch()
            
        Returns:
            bool: True if editor should continue, False to exit
        """
        # Check for key in current mode bindings
        if key in self.key_bindings.get(self.mode, {}):
            result = self.key_bindings[self.mode][key]()
            if result is not None:
                return result
            return True
            
        # Handle insert mode character input
        if self.mode == "insert" and 32 <= key <= 126:
            self._insert_char(key)
            
        return True
    
    def draw(self):
        """Draw editor content."""
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
                
            # Check if line is part of selection
            is_selected = False
            if self.mode == "select" and self.selection_start:
                start_line, start_col = self.selection_start
                end_line, end_col = self.scroll_pos + self.cursor_y, self.cursor_x
                
                # Ensure start is before end
                if start_line > end_line or (start_line == end_line and start_col > end_col):
                    start_line, end_line = end_line, start_line
                    start_col, end_col = end_col, start_col
                    
                is_selected = start_line <= line_idx <= end_line
            
            # Draw line content
            if self.syntax_highlighting and line_idx in highlighted_lines:
                # Draw syntax highlighted line
                highlighted_line = highlighted_lines[line_idx]
                self.stdscr.addstr(y, line_num_width, highlighted_line)
            else:
                # Draw plain line
                if is_selected:
                    # Draw selected text with highlight
                    if line_idx == self.selection_start[0] and line_idx == self.scroll_pos + self.cursor_y:
                        # Selection on single line
                        start_col = min(self.selection_start[1], self.cursor_x)
                        end_col = max(self.selection_start[1], self.cursor_x)
                        
                        # Draw before selection
                        self.stdscr.addstr(y, line_num_width, line[:start_col])
                        
                        # Draw selection
                        self.stdscr.addstr(
                            y, 
                            line_num_width + start_col, 
                            line[start_col:end_col], 
                            self.colors["highlight"]
                        )
                        
                        # Draw after selection
                        if end_col < len(line):
                            self.stdscr.addstr(y, line_num_width + end_col, line[end_col:])
                    elif line_idx == self.selection_start[0]:
                        # First line of multi-line selection
                        start_col = self.selection_start[1]
                        
                        # Draw before selection
                        self.stdscr.addstr(y, line_num_width, line[:start_col])
                        
                        # Draw selection
                        self.stdscr.addstr(
                            y,
                            line_num_width + start_col,
                            line[start_col:],
                            self.colors["highlight"]
                        )
                    elif line_idx == self.scroll_pos + self.cursor_y:
                        # Last line of multi-line selection
                        end_col = self.cursor_x
                        
                        # Draw selection
                        self.stdscr.addstr(
                            y,
                            line_num_width,
                            line[:end_col],
                            self.colors["highlight"]
                        )
                        
                        # Draw after selection
                        if end_col < len(line):
                            self.stdscr.addstr(y, line_num_width + end_col, line[end_col:])
                    else:
                        # Middle line of multi-line selection
                        self.stdscr.addstr(y, line_num_width, line, self.colors["highlight"])
                else:
                    # Draw plain line
                    self.stdscr.addstr(y, line_num_width, line)
                    
    def run_editor(self) -> bool:
        """Run the editor as a standalone component.
        
        Returns:
            bool: True if file was saved, False otherwise
        """
        try:
            result = self.run()
            return result is not None
        except Exception as e:
            self.set_status(f"Error: {e}")
            return False
            
    def get_content(self) -> str:
        """Get current content as string.
        
        Returns:
            str: Current content
        """
        return '\n'.join(self.content)
        
    def set_content(self, content: str):
        """Set editor content.
        
        Args:
            content: New content
        """
        self.content = content.splitlines()
        self.cursor_x = 0
        self.cursor_y = 0
        self.scroll_pos = 0
        self.is_modified = True
        
    def get_cursor_position(self) -> Tuple[int, int]:
        """Get current cursor position.
        
        Returns:
            Tuple[int, int]: (line, column)
        """
        return (self.scroll_pos + self.cursor_y, self.cursor_x)
        
    def set_cursor_position(self, line: int, col: int):
        """Set cursor position.
        
        Args:
            line: Line number (0-based)
            col: Column number (0-based)
        """
        # Ensure line is valid
        if line >= len(self.content):
            line = max(0, len(self.content) - 1)
            
        # Adjust scroll position
        if line < self.scroll_pos:
            self.scroll_pos = line
        elif line >= self.scroll_pos + self.height - 2:
            self.scroll_pos = line - (self.height - 3)
            
        # Set cursor position
        self.cursor_y = line - self.scroll_pos
        
        # Ensure column is valid
        if col > len(self.content[line]):
            col = len(self.content[line])
            
        self.cursor_x = col
