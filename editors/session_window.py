#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import curses
import time
import difflib
from pygments import highlight
from pygments.lexers import get_lexer_by_name, TextLexer
from pygments.formatters import TerminalFormatter
from typing import Optional, List, Dict, Any

class SessionWindow:
    """Interactive session window for code generation and editing."""
    
    def __init__(self, stdscr):
        """Initialize session window."""
        self.stdscr = stdscr
        self._init_colors()
        self.loading_frames = ['⣾', '⣽', '⣻', '⢿', '⡿', '⣟', '⣯', '⣷']
        self.current_frame = 0
        self.is_loading = False
        self.loading_thread = None

    def __del__(self):
        """Clean up resources when the window is destroyed."""
        try:
            # Stop any running loading animation
            if self.is_loading:
                self.stop_loading()
            # Wait for thread to finish
            if self.loading_thread and self.loading_thread.is_alive():
                self.loading_thread.join(timeout=0.2)
        except:
            pass
    
    def _init_colors(self) -> None:
        """Initialize color pairs."""
        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
            # Define color pairs
            curses.init_pair(1, curses.COLOR_CYAN, -1)     # Info/title
            curses.init_pair(2, curses.COLOR_GREEN, -1)    # Success/additions
            curses.init_pair(3, curses.COLOR_YELLOW, -1)   # Warning/changes
            curses.init_pair(4, curses.COLOR_RED, -1)      # Error/deletions
            curses.init_pair(5, curses.COLOR_WHITE, -1)    # Normal text
            curses.init_pair(6, curses.COLOR_MAGENTA, -1)  # Highlight
    
    def _draw_branding(self):
        """Draw ANJ DEV branding at top."""
        try:
            width = self.stdscr.getmaxyx()[1]
            # Draw ANJ DEV branding
            self.stdscr.addstr(0, 0, "╔═════ ANJ DEV ════╗", curses.color_pair(1) | curses.A_BOLD)
            self.stdscr.addstr(1, 0, "╚══by Adithyanraj══╝", curses.color_pair(3))

        except curses.error:
            pass

    def _draw_header(self, title: str, chapter: Optional[str] = None):
        """Draw session window header with optional chapter number."""
        try:
            height, width = self.stdscr.getmaxyx()
            # Draw branding first
            self._draw_branding()
            
            # Draw title bar with chapter if provided
            row = 3  # Start after branding
            if chapter:
                header = f"╔═ Chapter {chapter}: {title} "
                header += "═" * (width - len(header) - 1) + "╗"
                self.stdscr.addstr(row, 0, header, curses.color_pair(1) | curses.A_BOLD)
            else:
                self.stdscr.addstr(row, 0, "╔═" + "═" * (width - 4) + "═╗", curses.color_pair(1))
                # Center title
                title_pos = max(0, (width - len(title)) // 2)
                self.stdscr.addstr(row, title_pos, f" {title} ", curses.color_pair(1) | curses.A_BOLD)

            # Draw session border extension
            self.stdscr.addstr(row + 1, 0, "║", curses.color_pair(1))
            self.stdscr.addstr(row + 1, width - 1, "║", curses.color_pair(1))
        except curses.error:
            pass
    
    def _draw_footer(self, prompt: str = None):
        """Draw session window footer."""
        try:
            height, width = self.stdscr.getmaxyx()
            # Draw footer bar
            self.stdscr.addstr(height-1, 0, "╚═" + "═" * (width - 4) + "═╝", curses.color_pair(1))
            if prompt:
                self.stdscr.addstr(height-1, 2, prompt, curses.color_pair(3))
        except curses.error:
            pass
    
    def clear(self):
        """Clear the session window."""
        self.stdscr.clear()
        self.stdscr.refresh()
    
    def start_loading(self, message: str):
        """Start loading animation with message."""
        import threading
        
        def loading_animation():
            while self.is_loading:
                try:
                    height, width = self.stdscr.getmaxyx()
                    box_width = min(len(message) + 10, width - 4)
                    row = height - 4
                    
                    frame = self.loading_frames[self.current_frame]
                    self.current_frame = (self.current_frame + 1) % len(self.loading_frames)
                    
                    # Clear space for loading box
                    for i in range(3):
                        self.stdscr.move(row + i, 0)
                        self.stdscr.clrtoeol()
                    
                    # Draw loading box
                    self.stdscr.addstr(row, 2, "┌─ Loading " + "─" * (box_width - 10) + "┐", curses.color_pair(6))
                    self.stdscr.addstr(row + 1, 2, f"│ {frame} {message.ljust(box_width - 4)} │", curses.color_pair(6))
                    self.stdscr.addstr(row + 2, 2, "└" + "─" * (box_width - 2) + "─┘", curses.color_pair(6))
                    
                    self.stdscr.refresh()
                    time.sleep(0.1)
                except (curses.error, RuntimeError):
                    pass

        # Ensure any existing loading is stopped
        self.stop_loading()
        
        # Start new loading animation
        self.is_loading = True
        self.loading_thread = threading.Thread(target=loading_animation)
        self.loading_thread.daemon = True
        self.loading_thread.start()
    
    def stop_loading(self):
        """Stop loading animation and clean up loading box."""
        self.is_loading = False
        try:
            height, width = self.stdscr.getmaxyx()
            # Clean up loading box area (4 lines total)
            for i in range(4):
                self.stdscr.move(height - 5 + i, 0)
                self.stdscr.clrtoeol()
            self.stdscr.refresh()
        except curses.error:
            pass
    
    def show_plan(self, title: str, description: str, files: Dict[str, List[str]]) -> bool | str:
        """Show the planning step with file operations.
        
        Returns:
            bool: True if accepted, False if rejected
            str: 'edit' if edit requested
        """
        self.clear()
        self._draw_header("Implementation Plan", "1")
        
        try:
            # Create a box for the description
            height, width = self.stdscr.getmaxyx()
            box_width = min(80, width - 4)  # Max width of 80 chars or screen width
            
            # Draw box top
            self.stdscr.addstr(2, 2, "┌" + "─" * (box_width - 2) + "┐", curses.color_pair(1))
            
            # Split and display description in the box
            lines = []
            for para in description.split('\n'):
                while para and len(para) > box_width - 4:
                    # Find last space in the line width
                    space_pos = para[:box_width-4].rfind(' ')
                    if space_pos == -1:
                        space_pos = box_width - 4
                    lines.append(para[:space_pos])
                    para = para[space_pos+1:]
                if para:
                    lines.append(para)
                    
            # Display description lines
            row = 3
            for line in lines:
                if row >= height - 8:  # Leave space for files
                    break
                padded_line = line.ljust(box_width - 4)
                self.stdscr.addstr(row, 2, f"│ {padded_line} │", curses.color_pair(1))
                row += 1
            
            # Draw box bottom
            self.stdscr.addstr(row, 2, "└" + "─" * (box_width - 2) + "┘", curses.color_pair(1))
            row += 2
            
            # Show files in a similar box
            if files.get('create') or files.get('modify'):
                # Title for files section
                self.stdscr.addstr(row, 2, "┌── Files to Modify ───" + "─" * (box_width - 19) + "┐", curses.color_pair(1))
                row += 1
            
            for file in files.get('create', []):
                self.stdscr.addstr(row, 4, f"+ {file}", curses.color_pair(2))
                row += 1
                
            for file in files.get('modify', []):
                self.stdscr.addstr(row, 4, f"* {file}", curses.color_pair(3))
                row += 1
            
            self._draw_footer("Accept changes? [Y/n/e(dit)]")
            self.stdscr.refresh()
            
            response = self.get_input("Accept changes?", ["Y", "n", "e(dit)"])
            if response == 'y':
                return True
            elif response == 'n':
                return False
            elif response == 'e':
                return 'edit'
            return False
                    
        except curses.error:
            pass
    
    def show_preview(self, filename: str, content: str, is_new: bool = True):
        """Show code preview with syntax highlighting."""
        self.clear()
        self._draw_header(f"Code Preview: {filename}", "2")
        
        try:
            height, width = self.stdscr.getmaxyx()
            box_width = min(120, width - 4)  # Max width of 120 chars or screen width
            
            row = 2
            # Show file type indicator in a mini box
            status = " New File " if is_new else " Existing File "
            status_box = "┌" + "─" * len(status) + "┐"
            self.stdscr.addstr(row, 2, status_box, curses.color_pair(2 if is_new else 3))
            row += 1
            self.stdscr.addstr(row, 2, "│" + status + "│", curses.color_pair(2 if is_new else 3))
            row += 1
            self.stdscr.addstr(row, 2, "└" + "─" * len(status) + "┘", curses.color_pair(2 if is_new else 3))
            row += 2
            
            # Draw code box border
            self.stdscr.addstr(row, 2, "┌── Code ──" + "─" * (box_width - 10) + "┐", curses.color_pair(1))
            row += 1
            
            # Get appropriate lexer for syntax highlighting
            try:
                ext = filename.split('.')[-1]
                lexer = get_lexer_by_name(ext)
            except:
                lexer = TextLexer()
            
            # Highlight code with curses-compatible colors
            lines = content.split('\n')
            
            # Define color mappings for different code elements
            code_colors = {
                'keyword': curses.color_pair(6),   # Magenta for keywords
                'string': curses.color_pair(2),    # Green for strings
                'number': curses.color_pair(3),    # Yellow for numbers
                'comment': curses.color_pair(1),   # Cyan for comments
                'default': curses.color_pair(5)    # White for regular text
            }
            
            # Language-specific patterns
            if filename.endswith('.py'):
                patterns = {
                    'keyword': r'\b(def|class|import|from|return|if|elif|else|while|for|in|is|not|try|except|raise|with|as|True|False|None|self)\b',
                    'builtin': r'\b(print|len|range|str|int|float|list|tuple|dict|set|super|__init__|pygame)\b',
                    'string': r'(["\'])((?:(?!\1).)*)\1',
                    'number': r'\b\d+(?:\.\d+)?\b',
                    'comment': r'#.*$',
                    'decorator': r'@\w+',
                    'operator': r'[=<>!+\-*/]+',
                    'parentheses': r'[\(\)\[\]\{\}]'
                }
                code_colors.update({
                    'builtin': curses.color_pair(6),     # Magenta for builtins
                    'decorator': curses.color_pair(6),   # Magenta for decorators
                    'operator': curses.color_pair(3),    # Yellow for operators
                    'parentheses': curses.color_pair(1)  # Cyan for parentheses
                })
            else:
                # Basic syntax highlighting patterns
                patterns = {
                    'keyword': r'\b(def|class|import|from|return|if|else|while|for|in|try|except|raise|True|False|None)\b',
                    'string': r'(["\'])((?:(?!\1).)*)\1',
                    'number': r'\b\d+\b',
                    'comment': r'#.*$'
                }

            import re
            # Add scrolling support
            scroll_pos = 0
            max_display_lines = height - row - 5  # Leave space for borders and prompts
            total_lines = len(lines)
            
            while True:
                # Clear display area
                for i in range(max_display_lines):
                    self.stdscr.move(row + i, 2)
                    self.stdscr.clrtoeol()
                
                # Display visible portion of code
                displayed_lines = 0
                for i in range(scroll_pos, min(scroll_pos + max_display_lines, total_lines)):
                    line = lines[i]
                    
                    # Line number and separator
                    self.stdscr.addstr(row + displayed_lines, 2, f"│ {i+1:4d} │ ", curses.color_pair(1))
                    
                    # Code line with syntax highlighting
                    pos = 10  # Starting position after line number
                    # Process each syntax pattern
                    matches = []
                    for pattern_type, pattern in patterns.items():
                        for match in re.finditer(pattern, line):
                            matches.append((match.start(), match.end(), pattern_type))
                    
                    # Sort matches by start position
                    matches.sort(key=lambda x: x[0])
                    
                    # Display code with highlighting
                    last_pos = 0
                    for start, end, pattern_type in matches:
                        # Add any text before this match
                        if start > last_pos:
                            self.stdscr.addstr(row + displayed_lines, pos + last_pos, 
                                             line[last_pos:start], code_colors['default'])
                        # Add the highlighted match
                        self.stdscr.addstr(row + displayed_lines, pos + start,
                                         line[start:end], code_colors[pattern_type])
                        last_pos = end
                    
                    # Add any remaining text
                    if last_pos < len(line):
                        self.stdscr.addstr(row + displayed_lines, pos + last_pos,
                                         line[last_pos:], code_colors['default'])
                    
                    # Right border
                    self.stdscr.addstr(row + displayed_lines, box_width-1, "│", curses.color_pair(1))
                    displayed_lines += 1
                
                # Show scroll indicators
                if scroll_pos > 0:
                    self.stdscr.addstr(row - 1, 2, "↑ More (PgUp/Up) ↑", curses.color_pair(3))
                if scroll_pos + max_display_lines < total_lines:
                    self.stdscr.addstr(row + displayed_lines, 2, "↓ More (PgDn/Down) ↓", curses.color_pair(3))
                
                self.stdscr.refresh()
                
                # Handle keyboard input
                ch = self.stdscr.getch()
                if ch == curses.KEY_UP and scroll_pos > 0:
                    scroll_pos -= 1
                elif ch == curses.KEY_DOWN and scroll_pos + max_display_lines < total_lines:
                    scroll_pos += 1
                elif ch == curses.KEY_PPAGE:  # Page Up
                    scroll_pos = max(0, scroll_pos - max_display_lines)
                elif ch == curses.KEY_NPAGE:  # Page Down
                    scroll_pos = min(total_lines - max_display_lines, scroll_pos + max_display_lines)
                elif ch == curses.KEY_RESIZE:
                    # Handle terminal resize
                    height, width = self.stdscr.getmaxyx()
                    box_width = min(120, width - 4)
                    max_display_lines = height - row - 5
                    displayed_lines = 0
                    self.stdscr.clear()
                    self._draw_header(f"Code Preview: {filename}", "2")
                    continue
                elif ch in (ord('y'), ord('Y')):
                    return True
                elif ch in (ord('n'), ord('N')):
                    return False 
                elif ch in (ord('e'), ord('E')):
                    return 'edit'
                
        except curses.error:
            return False
        finally:
            # Ensure cursor is hidden and window is cleaned up
            curses.curs_set(0)
            curses.noecho()

    def show_diff(self, filename: str, original: str, modified: str) -> bool | str:
        """Show diff between original and modified code."""
        self.clear()
        self._draw_header(f"Code Changes: {filename}", "3")
        
        try:
            height, width = self.stdscr.getmaxyx()
            box_width = min(120, width - 4)  # Max width or screen width
            
            row = 2
            # Draw info box
            self.stdscr.addstr(row, 2, "┌── Showing changes " + "─" * (box_width - 17) + "┐", curses.color_pair(1))
            row += 1
            self.stdscr.addstr(row, 2, "│ - : Removed lines", curses.color_pair(4))
            row += 1
            self.stdscr.addstr(row, 2, "│ + : Added lines", curses.color_pair(2))
            row += 1
            self.stdscr.addstr(row, 2, "└" + "─" * (box_width - 2) + "┘", curses.color_pair(1))
            row += 2
            
            # Generate diff
            diff = list(difflib.unified_diff(
                original.splitlines(keepends=True),
                modified.splitlines(keepends=True),
                fromfile=f'a/{filename}',
                tofile=f'b/{filename}'
            ))
            
            # Add scrolling support for diff view
            scroll_pos = 0
            max_display_lines = height - row - 5  # Leave space for borders and prompts
            total_lines = len(diff)
            
            while True:
                # Clear display area
                for i in range(max_display_lines):
                    self.stdscr.move(row + i, 2)
                    self.stdscr.clrtoeol()
                
                # Display visible portion of diff
                displayed_lines = 0
                for i in range(scroll_pos, min(scroll_pos + max_display_lines, total_lines)):
                    if displayed_lines >= max_display_lines:
                        break
                    
                    line = diff[i].rstrip('\n')
                
                    # Format each line
                    if line.startswith('+'):
                        self.stdscr.addstr(row + displayed_lines, 2, "│", curses.color_pair(1))
                        self.stdscr.addstr(row + displayed_lines, 3, line.ljust(box_width - 3), curses.color_pair(2))
                    elif line.startswith('-'):
                        self.stdscr.addstr(row + displayed_lines, 2, "│", curses.color_pair(1))
                        self.stdscr.addstr(row + displayed_lines, 3, line.ljust(box_width - 3), curses.color_pair(4))
                    elif line.startswith('@@'):
                        self.stdscr.addstr(row + displayed_lines, 2, "│", curses.color_pair(1))
                        self.stdscr.addstr(row + displayed_lines, 3, line.ljust(box_width - 3), curses.color_pair(6))
                    else:
                        self.stdscr.addstr(row + displayed_lines, 2, "│", curses.color_pair(1))
                        self.stdscr.addstr(row + displayed_lines, 3, line.ljust(box_width - 3), curses.color_pair(5))
                    
                    # Right border
                    self.stdscr.addstr(row + displayed_lines, box_width + 1, "│", curses.color_pair(1))
                    displayed_lines += 1
                
                # Show scroll indicators
                if scroll_pos > 0:
                    self.stdscr.addstr(row - 1, 2, "↑ More (PgUp/Up) ↑", curses.color_pair(3))
                if scroll_pos + max_display_lines < total_lines:
                    self.stdscr.addstr(row + displayed_lines, 2, "↓ More (PgDn/Down) ↓", curses.color_pair(3))
                
                # Draw bottom border
                self.stdscr.addstr(row + displayed_lines, 2, "└" + "─" * (box_width - 2) + "┘", curses.color_pair(1))
                
                self.stdscr.refresh()
                
                # Handle keyboard input
                ch = self.stdscr.getch()
                if ch == curses.KEY_UP and scroll_pos > 0:
                    scroll_pos -= 1
                elif ch == curses.KEY_DOWN and scroll_pos + max_display_lines < total_lines:
                    scroll_pos += 1
                elif ch == curses.KEY_PPAGE:  # Page Up
                    scroll_pos = max(0, scroll_pos - max_display_lines)
                elif ch == curses.KEY_NPAGE:  # Page Down
                    scroll_pos = min(total_lines - max_display_lines, scroll_pos + max_display_lines)
                elif ch == curses.KEY_RESIZE:
                    # Handle terminal resize
                    height, width = self.stdscr.getmaxyx()
                    box_width = min(120, width - 4)
                    max_display_lines = height - row - 5
                    displayed_lines = 0
                    self.stdscr.clear()
                    self._draw_header(f"Code Changes: {filename}", "3")
                    continue
                elif ch in (ord('y'), ord('Y')):
                    return True
                elif ch in (ord('n'), ord('N')):
                    return False 
                elif ch in (ord('e'), ord('E')):
                    return 'edit'
                    
        except curses.error:
            return False
    
    def show_error(self, message: str):
        """Show error message with box formatting."""
        try:
            height, width = self.stdscr.getmaxyx()
            box_width = min(80, width - 4)  # Max width of 80 chars or screen width
            row = height - 6  # Position error box 6 lines from bottom
            
            # Clear space for error box
            for i in range(4):
                self.stdscr.move(row + i, 0)
                self.stdscr.clrtoeol()
            
            # Draw error box with double borders for emphasis
            self.stdscr.addstr(row, 2, "╔═ ERROR " + "═" * (box_width - 9) + "╗", curses.color_pair(4))
            # Split long messages into multiple lines
            remaining_msg = message
            line_count = 0
            while remaining_msg and line_count < 2:  # Limit to 2 lines
                disp_msg = remaining_msg[:box_width-4]
                if len(remaining_msg) > box_width-4:
                    # Find last space to break at
                    last_space = disp_msg.rfind(' ')
                    if last_space != -1:
                        disp_msg = disp_msg[:last_space]
                        remaining_msg = remaining_msg[last_space+1:]
                    else:
                        remaining_msg = remaining_msg[box_width-4:]
                else:
                    remaining_msg = ""
                    
                self.stdscr.addstr(row + 1 + line_count, 2, "║ " + disp_msg.ljust(box_width - 4) + " ║", curses.color_pair(4))
                line_count += 1
                
            # Add ellipsis if message was truncated
            if remaining_msg:
                self.stdscr.addstr(row + 1 + line_count, 2, "║ " + "..." + " "*(box_width - 7) + " ║", curses.color_pair(4))
            
            # Draw bottom border
            #self.stdscr.addstr(row + 3, 2, "╚" + "═" * (box_width - 2) + "╝", curses.color_pair(4))
            #self.stdscr.refresh()
            
        except curses.error:
            pass

    def get_input(self, prompt: str, choices: List[str] = None) -> str:
        """Get user input with prompt and optional choices."""
        try:
            height, width = self.stdscr.getmaxyx()
            prompt_line = f"{prompt}: "
            
            # Draw bottom border with space for input
            self.stdscr.addstr(height-2, 0, "╚" + "═" * (width - 2) + "╝", curses.color_pair(1))
            # Show prompt above border
            self.stdscr.addstr(height-3, 2, prompt_line, curses.color_pair(3))
            
            if choices:
                # Show choices with different colors for Y/N/E
                for i, choice in enumerate(choices):
                    if i > 0:
                        self.stdscr.addstr("/", curses.color_pair(5))
                    if choice.lower() == 'y':
                        self.stdscr.addstr(choice, curses.color_pair(2))  # Green for yes
                    elif choice.lower() == 'n':
                        self.stdscr.addstr(choice, curses.color_pair(4))  # Red for no
                    else:
                        self.stdscr.addstr(choice, curses.color_pair(6))  # Magenta for edit
            
            self.stdscr.refresh()
            
            # Enable cursor and echo
            curses.echo()
            curses.curs_set(1)
            
            # Get single character input
            while True:
                ch = self.stdscr.getch()
                if choices:
                    input_char = chr(ch).lower()
                    valid_chars = [c[0].lower() for c in choices]
                    if input_char in valid_chars:
                        # Disable cursor and echo
                        curses.noecho()
                        curses.curs_set(0)
                        return input_char
                else:
                    # For free-form input
                    value = self.stdscr.getstr(height-3, len(prompt_line) + 3, width-len(prompt_line)-5)
                    curses.noecho()
                    curses.curs_set(0)
                    return value.decode('utf-8') if value else ""
                    
        except curses.error:
            return ""
        finally:
            # Always ensure cursor and echo are disabled when done
            curses.noecho()
            curses.curs_set(0)
