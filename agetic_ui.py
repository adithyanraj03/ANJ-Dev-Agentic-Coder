#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import time
import threading
import cursor
import curses
import difflib
from typing import Optional, List, Dict, Any
from colorama import init, Fore, Style
from pygments import highlight
from pygments.lexers import get_lexer_for_filename, TextLexer
from pygments.formatters import TerminalFormatter

class AGETICUI:
    """UI handler for AGETIC terminal application."""
    
    def __init__(self):
        """Initialize UI handler."""
        init(autoreset=True)
        self._loading_active = False
        self._loading_thread: Optional[threading.Thread] = None
        self._stdscr = None
        self._using_log_window = False
        
        # Check if log window is being used
        try:
            from log_window import log_queue
            self._using_log_window = True
            self._log_queue = log_queue
        except ImportError:
            pass

        self.symbols = {
            'success': '✓',
            'error': '✗',
            'warning': '!',
            'info': '>',
            'bullet': '•',
            'loading': ['⣷', '⣯', '⣟', '⡿', '⢿', '⣻', '⣽', '⣾']
        }
        self._status_line = ""
        self._last_status_y = 0

    def set_screen(self, stdscr):
        """Set curses screen."""
        # Only set curses screen if not using log window
        if not self._using_log_window:
            self._stdscr = stdscr

    def start_loading(self, message: str = "Processing"):
        """Start loading animation."""
        if self._loading_thread and self._loading_thread.is_alive():
            return

        self._loading_active = True
        self._loading_thread = threading.Thread(
            target=self._animate_loading,
            args=(message,)
        )
        self._loading_thread.daemon = True
        
        if self._stdscr:
            height, width = self._stdscr.getmaxyx()
            self._loading_pos = (height - 4, 2)  # Move up 2 lines from bottom
            self._status_line = message
            self._last_status_y = self._loading_pos[0]
        else:
            cursor.hide()
            
        self._loading_thread.start()

    def stop_loading_animation(self):
        """Stop loading animation."""
        self._loading_active = False
        if self._loading_thread:
            self._loading_thread.join()
            
        if self._stdscr:
            if hasattr(self, '_loading_pos'):
                # Clear loading line and status line
                self._stdscr.move(self._loading_pos[0], 0)
                self._stdscr.clrtoeol()
                self._stdscr.move(self._loading_pos[0] + 1, 0)
                self._stdscr.clrtoeol()
                self._stdscr.refresh()
        else:
            cursor.show()
            sys.stdout.write('\r' + ' ' * 80 + '\r')
            sys.stdout.flush()

    def _animate_loading(self, message: str):
        """Animate loading indicator."""
        frame_idx = 0
        while self._loading_active:
            frame = self.symbols['loading'][frame_idx]
            frame_idx = (frame_idx + 1) % len(self.symbols['loading'])
            
            if self._stdscr:
                if hasattr(self, '_loading_pos'):
                    try:
                        # Clear previous lines
                        self._stdscr.move(self._loading_pos[0], 0)
                        self._stdscr.clrtoeol()
                        self._stdscr.move(self._loading_pos[0] + 1, 0)
                        self._stdscr.clrtoeol()
                        
                        # Draw loading animation
                        self._stdscr.addstr(
                            self._loading_pos[0],
                            self._loading_pos[1],
                            f"{frame} {message}"
                        )
                        
                        # Draw status line below
                        if self._status_line:
                            self._stdscr.addstr(
                                self._loading_pos[0] + 1,
                                self._loading_pos[1],
                                self._status_line
                            )
                            
                        self._stdscr.refresh()
                    except curses.error:
                        pass
            else:
                sys.stdout.write(f'\r{Fore.CYAN}{frame} {message}')
                sys.stdout.flush()
                
            time.sleep(0.1)

    def print_success(self, message: str):
        """Print success message."""
        if self._using_log_window:
            self._log_queue.put({"message": message, "level": "SUCCESS"})
        elif self._stdscr:
            self._print_curses(message, curses.color_pair(2), self.symbols['success'])
        else:
            print(f"{Fore.GREEN}{self.symbols['success']} {message}{Style.RESET_ALL}")

    def print_error(self, message: str):
        """Print error message."""
        if self._using_log_window:
            self._log_queue.put({"message": message, "level": "ERROR"})
        elif self._stdscr:
            self._print_curses(message, curses.color_pair(3), self.symbols['error'])
        else:
            print(f"{Fore.RED}{self.symbols['error']} {message}{Style.RESET_ALL}")

    def print_warning(self, message: str):
        """Print warning message."""
        if self._using_log_window:
            self._log_queue.put({"message": message, "level": "WARNING"})
        elif self._stdscr:
            self._print_curses(message, curses.color_pair(3), self.symbols['warning'])
        else:
            print(f"{Fore.YELLOW}{self.symbols['warning']} {message}{Style.RESET_ALL}")

    def print_info(self, message: str):
        """Print info message."""
        if self._using_log_window:
            self._log_queue.put({"message": message, "level": "INFO"})
        elif self._stdscr:
            self._print_curses(message, curses.color_pair(1), self.symbols['info'])
        else:
            print(f"{Fore.BLUE}{self.symbols['info']} {message}{Style.RESET_ALL}")

    def _print_curses(self, message: str, color_pair: int, symbol: str):
        """Print message using curses."""
        if self._stdscr:
            try:
                height, width = self._stdscr.getmaxyx()
                
                # Store as status line
                self._status_line = f"{symbol} {message}"
                
                # Print at loading position + 1 if loading, otherwise near bottom
                if self._loading_active and hasattr(self, '_loading_pos'):
                    row = self._loading_pos[0] + 1
                else:
                    row = height - 4  # Leave 3 lines at bottom
                    
                self._last_status_y = row
                
                # Clear line first
                self._stdscr.move(row, 0)
                self._stdscr.clrtoeol()
                
                # Print message
                self._stdscr.addstr(row, 2, self._status_line, color_pair)
                self._stdscr.refresh()
                
            except curses.error:
                pass

    def show_provider_status(self, providers: Dict[str, Any]):
        """Display status of LLM providers."""
        if self._stdscr:
            row = 2
            self._stdscr.addstr(row, 2, "LLM Provider Status:", curses.color_pair(1))
            row += 2
            
            for name, info in providers.items():
                status = "Active" if info.get('active', False) else "Inactive"
                color = curses.color_pair(2) if info.get('active', False) else curses.color_pair(3)
                symbol = self.symbols['success'] if info.get('active', False) else self.symbols['error']
                
                self._stdscr.addstr(row, 2, f"{symbol} {name.title()}", color)
                row += 1
                self._stdscr.addstr(row, 4, f"Status: {status}")
                row += 1
                
                if info.get('active', False):
                    if 'url' in info:
                        self._stdscr.addstr(row, 4, f"URL: {info['url']}")
                        row += 1
                    if 'models' in info:
                        self._stdscr.addstr(row, 4, f"Models: {', '.join(info['models'])}")
                        row += 1
                    if 'timeout' in info:
                        self._stdscr.addstr(row, 4, f"Timeout: {info['timeout']}s")
                        row += 1
                row += 1
                
            self._stdscr.refresh()
        else:
            print(f"\n{Fore.CYAN}LLM Provider Status:")
            print(f"{Fore.YELLOW}{'=' * 40}")
            
            for name, info in providers.items():
                status = "Active" if info.get('active', False) else "Inactive"
                color = Fore.GREEN if info.get('active', False) else Fore.RED
                symbol = self.symbols['success'] if info.get('active', False) else self.symbols['error']
                
                print(f"\n{color}{symbol} {name.title()}")
                print(f"{Fore.WHITE}Status: {color}{status}")
                
                if info.get('active', False):
                    if 'url' in info:
                        print(f"{Fore.WHITE}URL: {info['url']}")
                    if 'models' in info:
                        print(f"{Fore.WHITE}Models: {', '.join(info['models'])}")
                    if 'timeout' in info:
                        print(f"{Fore.WHITE}Timeout: {info['timeout']}s")

    def confirm(self, message: str, options: str = "(y/N)", default: bool = False) -> bool:
        """Get user confirmation."""
        if self._stdscr:
            height, width = self._stdscr.getmaxyx()
            # Show prompt above loading/status lines
            prompt_y = height - 3 if self._loading_active else height - 2
            self._stdscr.addstr(prompt_y, 2, f"{message} {options}: ", curses.color_pair(3))
            self._stdscr.refresh()
            response = chr(self._stdscr.getch()).lower()
            return response in ('y', 'yes') if response else default
        else:
            response = input(f"{Fore.YELLOW}{message} {options}: {Style.RESET_ALL}").lower()
            return response in ('y', 'yes') if response else default

    def select_provider(self, providers: Dict[str, Any]) -> Optional[str]:
        """Let user select an LLM provider."""
        print(f"\n{Fore.CYAN}Available Providers:")
        active_providers = {
            name: info for name, info in providers.items()
            if info.get('active', False)
        }
        
        if not active_providers:
            self.print_error("No active providers available")
            return None
            
        for i, (name, info) in enumerate(active_providers.items(), 1):
            print(f"{Fore.WHITE}{i}. {name.title()}")
            
        try:
            choice = int(input(f"\n{Fore.GREEN}Select provider (1-{len(active_providers)}): "))
            if 1 <= choice <= len(active_providers):
                return list(active_providers.keys())[choice - 1]
        except ValueError:
            pass
            
        return None

    def show_help(self):
        """Display help information."""
        print(f"\n{Fore.CYAN}AGETIC DEV Terminal Help:")
        print(f"{Fore.YELLOW}{'=' * 40}\n")
        
        help_items = [
            ("Code Generation", [
                "Enter your code request in natural language",
                "Use clear, specific descriptions",
                "Include language/framework preferences"
            ]),
            ("Provider Settings", [
                "Configure multiple LLM providers",
                "Enable/disable providers",
                "Set API keys and endpoints"
            ]),
            ("History", [
                "View previous code generations",
                "Copy from history",
                "Search past queries"
            ]),
            ("Commands", [
                "!help - Show this help",
                "!providers - Show provider status",
                "!clear - Clear screen",
                "!exit - Exit application"
            ])
        ]
        
        for section, items in help_items:
            print(f"{Fore.GREEN}{section}:")
            for item in items:
                print(f"{Fore.WHITE}{self.symbols['bullet']} {item}")
            print()

    def clear_screen(self):
        """Clear terminal screen."""
        if sys.platform == 'win32':
            os.system('cls')
        else:
            os.system('clear')

    # New methods for code preview and confirmation

    def show_plan(self, files_to_create: List[str], files_to_modify: List[str], description: str):
        """Show the code generation plan."""
        if self._stdscr:
            try:
                height, width = self._stdscr.getmaxyx()
                row = 3
                
                # Show title
                self._stdscr.addstr(row, 2, "Code Generation Plan:", curses.color_pair(1) | curses.A_BOLD)
                row += 2
                
                # Show description with word wrap
                desc_words = description.split()
                current_line = ""
                for word in desc_words:
                    if len(current_line) + len(word) + 1 <= width - 4:
                        current_line += word + " "
                    else:
                        self._stdscr.addstr(row, 2, current_line, curses.color_pair(2))
                        row += 1
                        current_line = word + " "
                if current_line:
                    self._stdscr.addstr(row, 2, current_line, curses.color_pair(2))
                    row += 1
                
                # Add spacing
                row += 1
                
                # Show files to create
                if files_to_create:
                    self._stdscr.addstr(row, 2, "Files to Create:", curses.color_pair(3) | curses.A_BOLD)
                    row += 1
                    for file in files_to_create:
                        self._stdscr.addstr(row, 4, f"{self.symbols['bullet']} {file}", curses.color_pair(2))
                        row += 1
                    row += 1
                
                # Show files to modify
                if files_to_modify:
                    self._stdscr.addstr(row, 2, "Files to Modify:", curses.color_pair(3) | curses.A_BOLD)
                    row += 1
                    for file in files_to_modify:
                        self._stdscr.addstr(row, 4, f"{self.symbols['bullet']} {file}", curses.color_pair(2))
                        row += 1
                
                self._stdscr.refresh()
                
            except curses.error:
                # Fallback to print if curses fails
                print(f"\n{Fore.CYAN}Code Generation Plan:")
                print(f"{Fore.YELLOW}{'=' * 40}\n")
                print(f"{Fore.WHITE}{description}\n")
                if files_to_create:
                    print(f"{Fore.GREEN}Files to Create:")
                    for file in files_to_create:
                        print(f"{Fore.WHITE}{self.symbols['bullet']} {file}")
                    print()
                if files_to_modify:
                    print(f"{Fore.YELLOW}Files to Modify:")
                    for file in files_to_modify:
                        print(f"{Fore.WHITE}{self.symbols['bullet']} {file}")
                    print()
        else:
            # Non-curses mode
            print(f"\n{Fore.CYAN}Code Generation Plan:")
            print(f"{Fore.YELLOW}{'=' * 40}\n")
            print(f"{Fore.WHITE}{description}\n")
            if files_to_create:
                print(f"{Fore.GREEN}Files to Create:")
                for file in files_to_create:
                    print(f"{Fore.WHITE}{self.symbols['bullet']} {file}")
                print()
            if files_to_modify:
                print(f"{Fore.YELLOW}Files to Modify:")
                for file in files_to_modify:
                    print(f"{Fore.WHITE}{self.symbols['bullet']} {file}")
                print()

    def show_code_preview(self, filename: str, content: str, original_content: Optional[str] = None):
        """Show code preview with optional diff."""
        if self._stdscr:
            try:
                height, width = self._stdscr.getmaxyx()
                row = 3
                
                # Show title
                self._stdscr.addstr(row, 2, f"Code Preview: {filename}", curses.color_pair(1) | curses.A_BOLD)
                row += 2
                
                if original_content:
                    # Show diff
                    diff = list(difflib.unified_diff(
                        original_content.splitlines(keepends=True),
                        content.splitlines(keepends=True),
                        fromfile=f"a/{filename}",
                        tofile=f"b/{filename}"
                    ))
                    
                    for line in diff:
                        if row >= height - 4:  # Leave space for prompt
                            break
                            
                        if line.startswith('+'):
                            self._stdscr.addstr(row, 4, line, curses.color_pair(2))  # Green for additions
                        elif line.startswith('-'):
                            self._stdscr.addstr(row, 4, line, curses.color_pair(4))  # Red for deletions
                        else:
                            self._stdscr.addstr(row, 4, line, curses.color_pair(1))  # Normal color
                        row += 1
                else:
                    # Show new content
                    lines = content.splitlines()
                    for i, line in enumerate(lines):
                        if row >= height - 4:  # Leave space for prompt
                            break
                            
                        # Add line numbers
                        self._stdscr.addstr(row, 2, f"{i+1:4d} │ ", curses.color_pair(3))
                        
                        # Handle long lines
                        remaining_width = width - 8  # Account for line number and margin
                        start = 0
                        while start < len(line):
                            if row >= height - 4:
                                break
                            chunk = line[start:start + remaining_width]
                            self._stdscr.addstr(row, 8, chunk, curses.color_pair(1))
                            start += remaining_width
                            row += 1
                            if start < len(line):  # If line continues
                                self._stdscr.addstr(row, 2, "     │ ", curses.color_pair(3))
                                
                self._stdscr.refresh()
                
            except curses.error:
                # Fallback to print mode
                print(f"\n{Fore.CYAN}Preview for {filename}:")
                print(f"{Fore.YELLOW}{'=' * 40}\n")
                
                if original_content:
                    diff = list(difflib.unified_diff(
                        original_content.splitlines(keepends=True),
                        content.splitlines(keepends=True),
                        fromfile=f"a/{filename}",
                        tofile=f"b/{filename}"
                    ))
                    for line in diff:
                        if line.startswith('+'):
                            print(f"{Fore.GREEN}{line}", end='')
                        elif line.startswith('-'):
                            print(f"{Fore.RED}{line}", end='')
                        else:
                            print(f"{Fore.WHITE}{line}", end='')
                else:
                    try:
                        lexer = get_lexer_for_filename(filename)
                    except:
                        lexer = TextLexer()
                    formatter = TerminalFormatter()
                    highlighted = highlight(content, lexer, formatter)
                    print(highlighted)
                print()
        else:
            # Non-curses mode
            print(f"\n{Fore.CYAN}Preview for {filename}:")
            print(f"{Fore.YELLOW}{'=' * 40}\n")
            
            if original_content:
                diff = list(difflib.unified_diff(
                    original_content.splitlines(keepends=True),
                    content.splitlines(keepends=True),
                    fromfile=f"a/{filename}",
                    tofile=f"b/{filename}"
                ))
                for line in diff:
                    if line.startswith('+'):
                        print(f"{Fore.GREEN}{line}", end='')
                    elif line.startswith('-'):
                        print(f"{Fore.RED}{line}", end='')
                    else:
                        print(f"{Fore.WHITE}{line}", end='')
            else:
                try:
                    lexer = get_lexer_for_filename(filename)
                except:
                    lexer = TextLexer()
                formatter = TerminalFormatter()
                highlighted = highlight(content, lexer, formatter)
                print(highlighted)
            print()

    def confirm_changes(self, filename: str) -> str:
        """Get user confirmation for changes with options to edit."""
        if self._stdscr:
            try:
                height, width = self._stdscr.getmaxyx()
                # Show prompt at bottom of screen
                prompt = f"Accept changes to {filename}? (Y)es/(N)o/(E)dit: "
                self._stdscr.move(height - 2, 0)
                self._stdscr.clrtoeol()
                self._stdscr.addstr(height - 2, 2, prompt, curses.color_pair(3))
                self._stdscr.refresh()
                
                while True:
                    choice = chr(self._stdscr.getch()).lower()
                    if choice in ('y', '\n', ' '):  # Allow Enter and Space as Yes
                        return 'accept'
                    elif choice == 'n':
                        return 'reject'
                    elif choice == 'e':
                        return 'edit'
                    else:
                        # Show error message
                        self._stdscr.move(height - 3, 0)
                        self._stdscr.clrtoeol()
                        self._stdscr.addstr(height - 3, 2, "Invalid choice. Please enter Y, N, or E.", 
                                          curses.color_pair(4))
                        self._stdscr.refresh()
                        
            except curses.error:
                # Fallback to regular input
                while True:
                    choice = input(f"{Fore.YELLOW}Accept changes to {filename}? (Y)es/(N)o/(E)dit: {Style.RESET_ALL}").lower()
                    if choice in ('y', 'yes', ''):
                        return 'accept'
                    elif choice in ('n', 'no'):
                        return 'reject'
                    elif choice in ('e', 'edit'):
                        return 'edit'
                    else:
                        print(f"{Fore.RED}Invalid choice. Please enter Y, N, or E.{Style.RESET_ALL}")
        else:
            # Non-curses mode
            while True:
                choice = input(f"{Fore.YELLOW}Accept changes to {filename}? (Y)es/(N)o/(E)dit: {Style.RESET_ALL}").lower()
                if choice in ('y', 'yes', ''):
                    return 'accept'
                elif choice in ('n', 'no'):
                    return 'reject'
                elif choice in ('e', 'edit'):
                    return 'edit'
                else:
                    print(f"{Fore.RED}Invalid choice. Please enter Y, N, or E.{Style.RESET_ALL}")

    def edit_content(self, content: str) -> str:
        """Let user edit content."""
        # Create temporary file
        import tempfile
        import subprocess
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(content)
            temp_path = f.name
            
        # Open in default editor
        editor = os.environ.get('EDITOR', 'notepad' if sys.platform == 'win32' else 'nano')
        subprocess.call([editor, temp_path])
        
        # Read edited content
        with open(temp_path, 'r') as f:
            edited_content = f.read()
            
        # Clean up
        os.unlink(temp_path)
        
        return edited_content
