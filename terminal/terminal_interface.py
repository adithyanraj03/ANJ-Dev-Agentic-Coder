#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Terminal interface component for interacting with shell commands."""
import curses
import os
import re
import time
import threading
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Callable

class TerminalInterface:
    """Terminal interface for interacting with shell commands."""
    
    def __init__(self, stdscr, terminal_manager):
        """Initialize terminal interface.
        
        Args:
            stdscr: Curses window for display
            terminal_manager: Terminal manager instance
        """
        self.stdscr = stdscr
        self.terminal_manager = terminal_manager
        self.height, self.width = stdscr.getmaxyx()
        
        # Terminal state
        self.command_history = []
        self.history_idx = -1
        self.output_buffer = []
        self.max_buffer_lines = 1000
        self.scroll_pos = 0
        self.input_buffer = ""
        self.cursor_pos = 0
        self.running_command = False
        self.exit_requested = False
        
        # Color pairs
        self.colors = {
            "normal": curses.color_pair(0),
            "title": curses.color_pair(1) | curses.A_BOLD,
            "prompt": curses.color_pair(2) | curses.A_BOLD,
            "command": curses.color_pair(2),
            "output": curses.color_pair(0),
            "error": curses.color_pair(3),
            "status": curses.color_pair(1),
        }
        
        # Initialize terminal
        self._init_terminal()
        
        # Key bindings
        self.key_bindings = {
            curses.KEY_UP: self._history_prev,
            curses.KEY_DOWN: self._history_next,
            curses.KEY_LEFT: self._cursor_left,
            curses.KEY_RIGHT: self._cursor_right,
            curses.KEY_HOME: self._cursor_home,
            curses.KEY_END: self._cursor_end,
            curses.KEY_NPAGE: self._page_down,
            curses.KEY_PPAGE: self._page_up,
            curses.KEY_BACKSPACE: self._backspace,
            curses.KEY_DC: self._delete,
            10: self._execute_command,  # Enter key
            27: self._handle_escape,    # Escape key
            9: self._tab_complete,      # Tab key
            4: self._ctrl_d,            # Ctrl+D
            3: self._ctrl_c,            # Ctrl+C
            12: self._ctrl_l,           # Ctrl+L
            21: self._ctrl_u,           # Ctrl+U
            11: self._ctrl_k,           # Ctrl+K
            23: self._ctrl_w,           # Ctrl+W
        }
    
    def _init_terminal(self):
        """Initialize terminal state."""
        # Add initial welcome message
        self.output_buffer.append(("status", "ANJ DEV Terminal Interface"))
        self.output_buffer.append(("status", "Type 'help' for available commands"))
        self.output_buffer.append(("status", "Type 'exit' to return to main menu"))
        self.output_buffer.append(("output", ""))
        
        # Get current working directory
        cwd = self.terminal_manager.get_cwd()
        self.output_buffer.append(("prompt", f"{cwd} $ "))
    
    def resize(self, height: int, width: int):
        """Handle terminal resize.
        
        Args:
            height: New height
            width: New width
        """
        self.height = height
        self.width = width
    
    def _history_prev(self):
        """Navigate to previous command in history."""
        if not self.command_history:
            return
            
        if self.history_idx < len(self.command_history) - 1:
            self.history_idx += 1
            self.input_buffer = self.command_history[self.history_idx]
            self.cursor_pos = len(self.input_buffer)
    
    def _history_next(self):
        """Navigate to next command in history."""
        if self.history_idx > 0:
            self.history_idx -= 1
            self.input_buffer = self.command_history[self.history_idx]
            self.cursor_pos = len(self.input_buffer)
        elif self.history_idx == 0:
            self.history_idx = -1
            self.input_buffer = ""
            self.cursor_pos = 0
    
    def _cursor_left(self):
        """Move cursor left."""
        if self.cursor_pos > 0:
            self.cursor_pos -= 1
    
    def _cursor_right(self):
        """Move cursor right."""
        if self.cursor_pos < len(self.input_buffer):
            self.cursor_pos += 1
    
    def _cursor_home(self):
        """Move cursor to start of input."""
        self.cursor_pos = 0
    
    def _cursor_end(self):
        """Move cursor to end of input."""
        self.cursor_pos = len(self.input_buffer)
    
    def _page_up(self):
        """Scroll output up."""
        page_size = self.height - 3
        self.scroll_pos = min(len(self.output_buffer) - 1, self.scroll_pos + page_size)
    
    def _page_down(self):
        """Scroll output down."""
        page_size = self.height - 3
        self.scroll_pos = max(0, self.scroll_pos - page_size)
    
    def _backspace(self):
        """Delete character before cursor."""
        if self.cursor_pos > 0:
            self.input_buffer = self.input_buffer[:self.cursor_pos-1] + self.input_buffer[self.cursor_pos:]
            self.cursor_pos -= 1
    
    def _delete(self):
        """Delete character at cursor."""
        if self.cursor_pos < len(self.input_buffer):
            self.input_buffer = self.input_buffer[:self.cursor_pos] + self.input_buffer[self.cursor_pos+1:]
    
    def _ctrl_c(self):
        """Handle Ctrl+C (interrupt)."""
        if self.running_command:
            self.terminal_manager.interrupt_command()
            self.output_buffer.append(("error", "^C"))
            self.running_command = False
        else:
            self.input_buffer = ""
            self.cursor_pos = 0
            self.output_buffer.append(("output", ""))
            cwd = self.terminal_manager.get_cwd()
            self.output_buffer.append(("prompt", f"{cwd} $ "))
    
    def _ctrl_d(self):
        """Handle Ctrl+D (exit)."""
        if not self.input_buffer:
            self.exit_requested = True
            return False
    
    def _ctrl_l(self):
        """Handle Ctrl+L (clear screen)."""
        self.output_buffer = []
        cwd = self.terminal_manager.get_cwd()
        self.output_buffer.append(("prompt", f"{cwd} $ "))
        self.scroll_pos = 0
    
    def _ctrl_u(self):
        """Handle Ctrl+U (clear to beginning of line)."""
        self.input_buffer = self.input_buffer[self.cursor_pos:]
        self.cursor_pos = 0
    
    def _ctrl_k(self):
        """Handle Ctrl+K (clear to end of line)."""
        self.input_buffer = self.input_buffer[:self.cursor_pos]
    
    def _ctrl_w(self):
        """Handle Ctrl+W (delete word)."""
        if self.cursor_pos > 0:
            # Find start of word
            i = self.cursor_pos - 1
            while i > 0 and self.input_buffer[i-1].isspace():
                i -= 1
            while i > 0 and not self.input_buffer[i-1].isspace():
                i -= 1
                
            # Delete word
            self.input_buffer = self.input_buffer[:i] + self.input_buffer[self.cursor_pos:]
            self.cursor_pos = i
    
    def _handle_escape(self):
        """Handle Escape key."""
        # Clear input buffer
        self.input_buffer = ""
        self.cursor_pos = 0
    
    def _tab_complete(self):
        """Handle Tab key (command/path completion)."""
        if not self.input_buffer:
            return
            
        # Get current word
        parts = self.input_buffer[:self.cursor_pos].split()
        if not parts:
            return
            
        current_word = parts[-1]
        
        # Check if it's a path
        if current_word.startswith('./') or current_word.startswith('/') or current_word.startswith('~/') or '/' in current_word:
            # Path completion
            completions = self.terminal_manager.complete_path(current_word)
        else:
            # Command completion
            completions = self.terminal_manager.complete_command(current_word)
            
        if not completions:
            return
            
        if len(completions) == 1:
            # Single completion - replace current word
            completion = completions[0]
            if len(parts) > 1:
                self.input_buffer = ' '.join(parts[:-1]) + ' ' + completion + self.input_buffer[self.cursor_pos:]
                self.cursor_pos = len(' '.join(parts[:-1]) + ' ' + completion)
            else:
                self.input_buffer = completion + self.input_buffer[self.cursor_pos:]
                self.cursor_pos = len(completion)
        else:
            # Multiple completions - show options
            self.output_buffer.append(("output", ""))
            self.output_buffer.append(("output", "  ".join(completions)))
            self.output_buffer.append(("output", ""))
            cwd = self.terminal_manager.get_cwd()
            self.output_buffer.append(("prompt", f"{cwd} $ {self.input_buffer}"))
    
    def _execute_command(self):
        """Execute current command."""
        if self.running_command:
            # Send input to running command
            self.terminal_manager.send_input(self.input_buffer + '\n')
            self.output_buffer.append(("command", self.input_buffer))
            self.input_buffer = ""
            self.cursor_pos = 0
            return
            
        command = self.input_buffer.strip()
        if not command:
            # Empty command - just add a new prompt
            self.output_buffer.append(("output", ""))
            cwd = self.terminal_manager.get_cwd()
            self.output_buffer.append(("prompt", f"{cwd} $ "))
            return
            
        # Add command to history
        if not self.command_history or self.command_history[0] != command:
            self.command_history.insert(0, command)
            if len(self.command_history) > 100:
                self.command_history.pop()
                
        self.history_idx = -1
        
        # Handle built-in commands
        if command == "exit":
            self.exit_requested = True
            return False
        elif command == "clear" or command == "cls":
            self._ctrl_l()
            self.input_buffer = ""
            self.cursor_pos = 0
            return
        elif command == "help":
            self._show_help()
            self.input_buffer = ""
            self.cursor_pos = 0
            return
            
        # Execute command
        self.output_buffer.append(("command", command))
        self.input_buffer = ""
        self.cursor_pos = 0
        self.running_command = True
        
        # Start command in a separate thread
        threading.Thread(target=self._run_command, args=(command,), daemon=True).start()
    
    def _run_command(self, command: str):
        """Run command and capture output.
        
        Args:
            command: Command to execute
        """
        try:
            for output_type, line in self.terminal_manager.execute_command(command):
                if output_type == "stdout":
                    self.output_buffer.append(("output", line))
                else:
                    self.output_buffer.append(("error", line))
                    
                # Limit buffer size
                if len(self.output_buffer) > self.max_buffer_lines:
                    self.output_buffer = self.output_buffer[-self.max_buffer_lines:]
                    
                # Adjust scroll position if at bottom
                if self.scroll_pos == 0:
                    self.scroll_pos = 0
                    
        except Exception as e:
            self.output_buffer.append(("error", f"Error: {e}"))
            
        finally:
            self.running_command = False
            cwd = self.terminal_manager.get_cwd()
            self.output_buffer.append(("prompt", f"{cwd} $ "))
    
    def _show_help(self):
        """Show help information."""
        help_text = [
            "ANJ DEV Terminal Help",
            "-------------------",
            "Commands:",
            "  exit - Exit terminal",
            "  clear/cls - Clear screen",
            "  help - Show this help",
            "",
            "Keyboard Shortcuts:",
            "  Up/Down - Navigate command history",
            "  Left/Right - Move cursor",
            "  Home/End - Move to start/end of line",
            "  Page Up/Down - Scroll output",
            "  Tab - Command/path completion",
            "  Ctrl+C - Interrupt command",
            "  Ctrl+D - Exit terminal",
            "  Ctrl+L - Clear screen",
            "  Ctrl+U - Clear to beginning of line",
            "  Ctrl+K - Clear to end of line",
            "  Ctrl+W - Delete word",
        ]
        
        for line in help_text:
            self.output_buffer.append(("output", line))
            
        self.output_buffer.append(("output", ""))
        cwd = self.terminal_manager.get_cwd()
        self.output_buffer.append(("prompt", f"{cwd} $ "))
    
    def handle_input(self, key: int) -> bool:
        """Handle keyboard input.
        
        Args:
            key: Key code from getch()
            
        Returns:
            bool: True if terminal should continue, False to exit
        """
        # Check for key in bindings
        if key in self.key_bindings:
            result = self.key_bindings[key]()
            if result is not None:
                return result
        elif 32 <= key <= 126:  # Printable ASCII
            # Insert character at cursor position
            self.input_buffer = self.input_buffer[:self.cursor_pos] + chr(key) + self.input_buffer[self.cursor_pos:]
            self.cursor_pos += 1
            
        return not self.exit_requested
    
    def get_visible_output(self) -> List[Tuple[str, str]]:
        """Get output visible in the current view.
        
        Returns:
            List of (output_type, line) tuples
        """
        max_lines = self.height - 2  # Account for input line and status bar
        
        # Calculate start index based on scroll position
        if self.scroll_pos > 0:
            start_idx = max(0, len(self.output_buffer) - self.scroll_pos - max_lines)
        else:
            start_idx = max(0, len(self.output_buffer) - max_lines)
            
        end_idx = min(start_idx + max_lines, len(self.output_buffer))
        
        return self.output_buffer[start_idx:end_idx]
    
    def draw(self):
        """Draw terminal content."""
        self.stdscr.clear()
        
        # Get visible output
        visible_output = self.get_visible_output()
        
        # Draw output
        for i, (output_type, line) in enumerate(visible_output):
            # Skip empty lines at the beginning
            if i == 0 and not line:
                continue
                
            # Get color for output type
            color = self.colors.get(output_type, self.colors["output"])
            
            # Draw line
            try:
                self.stdscr.addstr(i, 0, line, color)
            except curses.error:
                # Handle lines that are too long
                try:
                    self.stdscr.addstr(i, 0, line[:self.width-1], color)
                except:
                    pass
        
        # Draw input line
        input_y = self.height - 1
        
        # Clear input line
        self.stdscr.move(input_y, 0)
        self.stdscr.clrtoeol()
        
        # Draw prompt
        if self.running_command:
            prompt = "> "
        else:
            prompt = "$ "
            
        self.stdscr.addstr(input_y, 0, prompt, self.colors["prompt"])
        
        # Draw input buffer
        try:
            self.stdscr.addstr(input_y, len(prompt), self.input_buffer, self.colors["command"])
        except curses.error:
            # Handle input that's too long
            visible_start = max(0, self.cursor_pos - (self.width - len(prompt) - 5))
            visible_end = min(len(self.input_buffer), visible_start + (self.width - len(prompt) - 1))
            visible_input = self.input_buffer[visible_start:visible_end]
            
            # Show ellipsis if needed
            if visible_start > 0:
                self.stdscr.addstr(input_y, len(prompt), "...", self.colors["command"])
                self.stdscr.addstr(input_y, len(prompt) + 3, visible_input, self.colors["command"])
                cursor_x = len(prompt) + 3 + (self.cursor_pos - visible_start)
            else:
                self.stdscr.addstr(input_y, len(prompt), visible_input, self.colors["command"])
                cursor_x = len(prompt) + (self.cursor_pos - visible_start)
                
            # Position cursor
            self.stdscr.move(input_y, cursor_x)
            return
            
        # Position cursor
        self.stdscr.move(input_y, len(prompt) + self.cursor_pos)
    
    def run(self) -> bool:
        """Run terminal interface.
        
        Returns:
            bool: True if terminal exited normally, False if error
        """
        try:
            curses.curs_set(1)  # Show cursor
            
            while True:
                # Handle resize if needed
                new_height, new_width = self.stdscr.getmaxyx()
                if new_height != self.height or new_width != self.width:
                    self.resize(new_height, new_width)
                
                # Draw terminal
                self.draw()
                self.stdscr.refresh()
                
                # Get input
                key = self.stdscr.getch()
                
                # Handle input
                if not self.handle_input(key):
                    break
                    
            curses.curs_set(0)  # Hide cursor
            return True
            
        except KeyboardInterrupt:
            return False
        except Exception as e:
            self.output_buffer.append(("error", f"Terminal error: {e}"))
            return False
    
    def cleanup(self):
        """Clean up resources."""
        self.terminal_manager.cleanup()