#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import json
import sys
import curses
import subprocess
import tkinter as tk
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("agent_debug.log"),
        logging.StreamHandler()
    ]
)

# Log startup
logging.info("Starting ANJ DEV Terminal")

from tkinter import filedialog
import atexit
import difflib
from typing import Dict, Any, Optional
from pathlib import Path
from colorama import init, Fore, Style
import pyfiglet
import time
from datetime import datetime
from rich.console import Console
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.text import Text
from rich.style import Style as RichStyle

# Import original components
from agetic_ui import AGETICUI
from code_generator import CodeGenerator, CodePlan
from llm_handler import LLMHandler
from provider_settings import ProviderSettings
from project_manager import ProjectManager
from log_window import LogWindow
from queue_handler import log_queue

# Import new enhanced components
from feature_integration import FeatureIntegration
from components import ComponentRegistry
from agent_handler import get_agent, AgentHandler
from agent_interface import AgentInterface  # Add this import

def clear_terminal():
    """Clear current terminal."""
    os.system('cls' if os.name == 'nt' else 'clear')

def select_folder() -> Optional[str]:
    """Open folder selection dialog."""
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    folder_path = filedialog.askdirectory(
        title="Select Project Folder",
        mustexist=True
    )
    root.destroy()
    return folder_path if folder_path else None

def launch_new_terminal():
    """Launch the application in a new terminal."""
    script_path = os.path.abspath(__file__)
    cwd = os.getcwd()
    
    if sys.platform == 'win32':
        # For Windows, use start cmd with /k to keep window open
        command = f'start cmd /k "cd /d {cwd} && python {script_path} --new-instance"'
        os.system(command)
    else:
        # For Unix-like systems
        subprocess.Popen([
            'gnome-terminal', '--working-directory', cwd,
            '--', 'python3', script_path, '--new-instance'
        ])
    
    # Clear current terminal and exit
    clear_terminal()
    print("ANJ Dev terminal launched in a new window.")
    sys.exit(0)

def init_colors():
    """Initialize color pairs."""
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_CYAN, -1)
    curses.init_pair(2, curses.COLOR_GREEN, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    curses.init_pair(4, curses.COLOR_RED, -1)

def draw_mini_logo(stdscr=None):
    """Draw mini ANJ DEV logo."""
    if not stdscr:
        print("\n╔═════ ANJ DEV ════╗")
        print("╚══by Adithyanraj══╝\n")
        return
        
    try:
        # Only try to use curses colors if curses is properly initialized
        if curses.has_colors() and hasattr(curses, 'color_pair'):
            color = curses.color_pair(1)
            stdscr.addstr(0, 0, "╔═════ ANJ DEV ════╗", color | curses.A_BOLD)
            stdscr.addstr(1, 0, "╚══by Adithyanraj══╝", color)
        else:
            stdscr.addstr(0, 0, "╔═════ ANJ DEV ════╗", curses.A_BOLD)
            stdscr.addstr(1, 0, "╚══by Adithyanraj══╝")
    except (curses.error, AttributeError, TypeError):
        # Handle curses.error, NoneType attribute error, and type errors
        print("\n╔═════ ANJ DEV ════╗")
        print("╚══by Adithyanraj══╝\n")

class Menu:
    """Menu handler with support for both curses and console modes."""
    
    def __init__(self, stdscr):
        """Initialize menu."""
        self.stdscr = stdscr
        self.current_option = 0
        self.options = [
            "New Session",
            "Resume Session",
            "View Project Files", 
            "Provider Settings",
            "Toggle Log Window",
            "Exit"
        ]
        
        # Enable keypad mode for arrow keys if using curses
        if stdscr:
            try:
                stdscr.keypad(1)
            except:
                pass
        
    def show(self) -> int:
        """Display menu and handle navigation."""
        if not self.stdscr:
            # Console mode
            print("\nANJ DEV Terminal")
            print("=" * 30)
            print("\nMain Menu:")
            for idx, option in enumerate(self.options):
                print(f"{idx + 1}. {option}")
            
            while True:
                try:
                    choice = input("\nEnter your choice (1-6): ").strip()
                    if choice.isdigit() and 1 <= int(choice) <= len(self.options):
                        return int(choice) - 1
                    print("Invalid choice, please try again")
                except (KeyboardInterrupt, EOFError):
                    return len(self.options) - 1  # Return Exit option
                except:
                    print("Invalid input, please try again")
            
        # Curses mode
        while True:
            try:
                height, width = self.stdscr.getmaxyx()
                self.stdscr.clear()
                
                # Draw mini logo at the top
                draw_mini_logo(self.stdscr)
                
                # Draw title
                title = "Main Menu"
                x = max(0, (width - len(title)) // 2)
                self.stdscr.addstr(4, x, title, curses.color_pair(1) | curses.A_BOLD)
                
                # Draw options
                for idx, option in enumerate(self.options):
                    x = max(0, (width - len(option)) // 2)
                    y = min(height - 3, 7 + idx * 2)  # Leave space at bottom
                    
                    if idx == self.current_option:
                        # Show arrow and highlight
                        if x >= 3:  # Only show arrow if there's space
                            self.stdscr.addstr(y, x - 3, "→", curses.color_pair(2) | curses.A_BOLD)
                        self.stdscr.addstr(y, x, option, curses.color_pair(2) | curses.A_BOLD)
                    else:
                        self.stdscr.addstr(y, x, option)
                        
                self.stdscr.refresh()
                
                # Handle input
                key = self.stdscr.getch()
                
                if key == curses.KEY_UP and self.current_option > 0:
                    self.current_option -= 1
                elif key == curses.KEY_DOWN and self.current_option < len(self.options) - 1:
                    self.current_option += 1
                elif key in (10, ord('\n'), ord(' ')):  # Enter key or space
                    return self.current_option
                elif key in (27, ord('q')):  # ESC or 'q'
                    return len(self.options) - 1  # Return Exit option
                    
            except curses.error:
                continue

class ANJTerminal:
    """ANJ Dev Terminal Application."""
    
    def __init__(self):
        """Initialize terminal application."""
        init(autoreset=True)
        self.config = self._load_config()
        self.ui = AGETICUI()
        self.settings = ProviderSettings('config.json')
        self.project = ProjectManager()
        self.log_window = LogWindow()
        
        # Initialize rich console
        self.console = Console()
        
        # Initialize IO for file operations
        self.io = self
        
        # Initialize handlers lazily
        self._llm = None
        self._generator = None
        
        # Initialize component registry and feature integration
        self._components = None
        self._features = None
        
        # Session state
        self.current_session = None
        self.session_context = []
        self.session_files = set()
        
    def save_session_context(self):
        """Save current session context to file."""
        if not self.current_session or not self.project.current_project:
            return
            
        context_file = Path(self.project.current_project) / '.memory' / f'session_{self.current_session}.json'
        context_data = {
            'timestamp': datetime.now().isoformat(),
            'context': self.session_context,
            'files': list(self.session_files)
        }
        
        with open(context_file, 'w', encoding='utf-8') as f:
            json.dump(context_data, f, indent=2)
            
    def load_session_context(self, session_id: str) -> bool:
        """Load session context from file."""
        if not self.project.current_project:
            return False
            
        context_file = Path(self.project.current_project) / '.memory' / f'session_{session_id}.json'
        if not context_file.exists():
            return False
            
        try:
            with open(context_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.session_context = data.get('context', [])
                self.session_files = set(data.get('files', []))
                self.current_session = session_id
                return True
        except:
            return False
            
    def start_new_session(self):
        """Start a new coding session."""
        self.current_session = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.session_context = []
        self.session_files = set()
        
    def read_text(self, filepath: str) -> Optional[str]:
        """Read text from file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            return None
            
    def write_text(self, filepath: str, content: str):
        """Write text to file."""
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            print(f"Error writing {filepath}: {e}")
        
    @property
    def llm(self):
        """Lazy initialization of LLM handler."""
        if self._llm is None:
            self._llm = LLMHandler(self.config)
        return self._llm
        
    @property
    def generator(self):
        """Lazy initialization of code generator."""
        if self._generator is None:
            self._generator = CodeGenerator(
                self.config,
                self.ui,
                self.project
            )
        return self._generator
        
    @property
    def components(self):
        """Lazy initialization of component registry."""
        if self._components is None:
            project_path = Path(self.project.current_project) if self.project.current_project else Path.cwd()
            self._components = ComponentRegistry(project_path, self.llm)
        return self._components
        
    @property
    def features(self):
        """Lazy initialization of feature integration."""
        if self._features is None:
            self._features = FeatureIntegration(self.components, self.config)
        return self._features

    @property
    def agent(self):
        """Lazy initialization of agent handler."""
        if self.project.current_project:
            return get_agent(self.llm, self.project.current_project)
        return None
        
    @property
    def agent_interface(self):
        """Lazy initialization of agent interface."""
        if self.agent:
            return AgentInterface(self.agent)
        return None

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print("Config file not found. Creating default config...")
            return self._create_default_config()

    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration."""
        config = {
            "llm_providers": {
                "local": {
                    "url": "http://localhost:1234/v1",
                    "active": False,
                    "models": ["codellama-7b-instruct"],
                    "timeout": 30
                },
                "vscode": {
                    "active": False,
                    "extension_id": "GitHub.copilot",
                    "timeout": 10
                },
                "gemini": {
                    "active": False,
                    "api_key": "",
                    "model": "gemini-pro",
                    "timeout": 30
                }
            }
        }
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        return config

    def show_banner(self, stdscr):
        """Display animated banner."""
        try:
            height, width = stdscr.getmaxyx()
            banner = pyfiglet.figlet_format("ANJ DEV", font="slant")
            lines = banner.split('\n')
            
            # Add author line
            lines.append("")
            lines.append("by Adithyanraj")
            
            # Calculate starting positions
            start_y = max(0, (height - len(lines)) // 2)
            
            # Animate each line
            for idx, line in enumerate(lines):
                if line.strip():  # Skip empty lines
                    start_x = max(0, (width - len(line)) // 2)
                    for i in range(min(len(line), width - start_x)):
                        stdscr.addstr(
                            min(start_y + idx, height - 1),
                            start_x + i,
                            line[i],
                            curses.color_pair(1) | curses.A_BOLD
                        )
                        stdscr.refresh()
                        time.sleep(0.01)
            
            subtitle = "AI-Generated Enhanced Terminal Interface for Coding"
            subtitle_x = max(0, (width - len(subtitle)) // 2)
            subtitle_y = min(start_y + len(lines), height - 1)
            stdscr.addstr(subtitle_y, subtitle_x, subtitle,
                         curses.color_pair(2))
            stdscr.refresh()
            time.sleep(1)
            
        except curses.error:
            pass

    def show_code_block(self, content: str, filename: str = None):
        """Display code block with syntax highlighting."""
        # Detect language from file extension
        language = "text"
        if filename:
            ext = Path(filename).suffix.lower()
            if ext in {'.py', '.pyw'}:
                language = 'python'
            elif ext in {'.js', '.jsx', '.ts', '.tsx'}:
                language = 'javascript'
            elif ext in {'.html', '.htm'}:
                language = 'html'
            elif ext in {'.css'}:
                language = 'css'
            elif ext in {'.json'}:
                language = 'json'
            elif ext in {'.md', '.markdown'}:
                language = 'markdown'
            elif ext in {'.yml', '.yaml'}:
                language = 'yaml'
            elif ext in {'.sh', '.bash'}:
                language = 'bash'
            elif ext in {'.sql'}:
                language = 'sql'
            elif ext in {'.xml'}:
                language = 'xml'
            elif ext in {'.php'}:
                language = 'php'
            elif ext in {'.rb'}:
                language = 'ruby'
            elif ext in {'.go'}:
                language = 'go'
            elif ext in {'.java'}:
                language = 'java'
            elif ext in {'.cpp', '.hpp', '.cc', '.hh', '.c', '.h'}:
                language = 'cpp'
                
        markdown = f"```{language}\n{content}\n```"
        self.console.print(Markdown(markdown))
        
    def show_diff(self, original: str, updated: str, filename: str):
        """Display diff between original and updated content."""
        diff = list(difflib.unified_diff(
            original.splitlines(keepends=True),
            updated.splitlines(keepends=True),
            fromfile=f"{filename} original",
            tofile=f"{filename} updated"
        ))
        
        # Format diff with colors
        formatted_diff = []
        for line in diff[2:]:  # Skip diff header
            if line.startswith('+'):
                formatted_diff.append(Text(line, style="green"))
            elif line.startswith('-'):
                formatted_diff.append(Text(line, style="yellow"))
            else:
                formatted_diff.append(Text(line))
                
        self.console.print(*formatted_diff)
        
    def get_input(self, stdscr, prompt: str, y: int, x: int) -> str:
        """Get input with proper cursor positioning."""
        if not stdscr:
            try:
                return input(f"{prompt}: ")
            except (KeyboardInterrupt, EOFError):
                return ""

        try:
            height, width = stdscr.getmaxyx()
            y = min(y, height - 3)  # Leave space at bottom
            x = min(x, width - len(prompt) - 3)
            
            stdscr.addstr(y, x, f"{prompt}: ")
            stdscr.refresh()
            
            # Position cursor after prompt
            input_x = x + len(prompt) + 2
            stdscr.move(y, input_x)
            
            # Only try to use curses functions if they're available
            if hasattr(curses, 'echo') and hasattr(curses, 'curs_set'):
                curses.echo()
                curses.curs_set(1)
            
            # Get input with better sizing
            max_len = width - input_x - 2
            value = stdscr.getstr(y, input_x, max_len)
            if value is not None:
                value = value.decode('utf-8')
            else:
                value = ""
            
            # Reset curses settings if available
            if hasattr(curses, 'echo') and hasattr(curses, 'curs_set'):
                curses.noecho()
                curses.curs_set(0)
                
            return value
            
        except (curses.error, TypeError, AttributeError):
            try:
                # Fallback to regular input if curses fails
                return input(f"{prompt}: ")
            except (KeyboardInterrupt, EOFError):
                return ""

    def initialize_project_folder(self, stdscr) -> bool:
        """Initialize or load project folder."""
        try:
            # Temporarily exit curses to show folder dialog
            curses.endwin()
            folder_path = select_folder()
            curses.doupdate()
            
            if not folder_path:
                return False
                
            # Check for existing project
            has_memory, config = self.project.check_memory(folder_path)
            
            if has_memory:
                if config:
                    # Load existing project
                    self.project.load_project(folder_path)
                    return True
                else:
                    # Memory exists but is corrupted
                    stdscr.addstr(2, 2, "Project memory is corrupted. Initialize as new? (y/N): ")
                    stdscr.refresh()
                    choice = chr(stdscr.getch()).lower()
                    if choice != 'y':
                        return False
                        
            # Ask about subfolder
            stdscr.addstr(4, 2, "Create in subfolder? (y/N): ")
            stdscr.refresh()
            create_subfolder = chr(stdscr.getch()).lower() == 'y'
            
            # Initialize project
            success, path = self.project.initialize_project(folder_path, create_subfolder)
            return success
            
        except curses.error:
            return False

    def _handle_code_request(self, stdscr, query: str) -> bool:
        """Handle a code generation request. Returns True if should continue session."""
        # Show loading message
        height, width = stdscr.getmaxyx()
        stdscr.move(height-2, 0)
        stdscr.clrtoeol()
        stdscr.addstr(height-2, 2, "Creating plan...", curses.color_pair(2))
        stdscr.refresh()

        # Create plan first
        plan = self.generator.create_plan(query)
        if not plan:
            raise ValueError("Failed to create plan")

        # Clear screen and show plan
        stdscr.clear()
        draw_mini_logo(stdscr)

        # Show description
        row = 3
        desc_lines = [plan.description[i:i+width-4] for i in range(0, len(plan.description), width-4)]
        for line in desc_lines:
            stdscr.addstr(row, 2, line, curses.color_pair(1))
            row += 1

        # Show steps
        row += 1
        for idx, step in enumerate(plan.steps, 1):
            step_desc = f"Step {idx}/{len(plan.steps)}: {step['description']}"
            desc_lines = [step_desc[i:i+width-6] for i in range(0, len(step_desc), width-6)]
            for line in desc_lines:
                stdscr.addstr(row, 2, line, curses.color_pair(2))
                row += 1

        # Show files section
        row += 1
        if plan.files_to_create:
            stdscr.addstr(row, 2, "Files to create:", curses.color_pair(3))
            row += 1
            for file in plan.files_to_create:
                stdscr.addstr(row, 4, file)
                row += 1

        if plan.files_to_modify:
            row += 1
            stdscr.addstr(row, 2, "Files to modify:", curses.color_pair(3))
            row += 1
            for file in plan.files_to_modify:
                stdscr.addstr(row, 4, file)
                row += 1

        if plan.dependencies:
            row += 1
            stdscr.addstr(row, 2, "Dependencies:", curses.color_pair(3))
            row += 1
            stdscr.addstr(row, 4, ", ".join(plan.dependencies))
            row += 1

        # Ask for confirmation
        stdscr.move(height-2, 0)
        stdscr.clrtoeol()
        stdscr.addstr(height-2, 2, "Proceed with this plan? (y/N): ", curses.color_pair(2))
        stdscr.refresh()

        # Get confirmation
        choice = chr(stdscr.getch()).lower()
        if choice != 'y':
            return True

        # Execute plan step by step with progress
        total_steps = len(plan.steps)
        for idx, step in enumerate(plan.steps, 1):
            # Show progress
            progress = idx * 100 // total_steps
            progress_bar = "█" * (progress // 5) + "░" * (20 - progress // 5)
            progress_text = f"Progress: [{progress_bar}] {progress}%"
            
            # Show current step
            stdscr.clear()
            draw_mini_logo(stdscr)
            
            # Show progress bar at top
            row = 3
            stdscr.addstr(row, 2, progress_text, curses.color_pair(2))
            row += 2
            
            # Show step info
            step_info = f"Step {idx}/{len(plan.steps)}: {step['description']}"
            for line in [step_info[i:i+width-4] for i in range(0, len(step_info), width-4)]:
                stdscr.addstr(row, 2, line, curses.color_pair(2))
                row += 1
            
            # Show file being modified/created
            row += 1
            if step['action'] == 'create':
                stdscr.addstr(row, 2, f"Creating new file: {step['file']}", curses.color_pair(2))
            else:
                stdscr.addstr(row, 2, f"Modifying file: {step['file']}", curses.color_pair(3))
            row += 2
            
            # Stay in curses mode for generation
            stdscr.clear()
            draw_mini_logo(stdscr)
            
            # Show progress and step info
            row = 3
            stdscr.addstr(row, 2, progress_text, curses.color_pair(2))
            row += 2
            stdscr.addstr(row, 2, f"Step {idx}/{len(plan.steps)}: {step['description']}", curses.color_pair(2))
            row += 2
            stdscr.addstr(row, 2, "Generating code...", curses.color_pair(3))
            row += 2
            
            # Generate code with streaming output
            response = ""
            code_buffer = []
            current_line = ""
            
            for chunk in self.generator.llm.execute_query_stream(
                self.generator._create_step_prompt(step)
            ):
                response += chunk
                current_line += chunk
                
                # Update buffer with new content
                if '\n' in current_line:
                    lines = current_line.split('\n')
                    code_buffer.extend(lines[:-1])
                    current_line = lines[-1]
                
                # Format and display code
                code = "\n".join(code_buffer)
                if current_line:
                    code += current_line
                    
                # Clear code area once
                for i in range(row, height-3):
                    stdscr.move(i, 0)
                    stdscr.clrtoeol()
                
                # Display code with proper formatting
                display_row = row
                for line in code.split('\n'):
                    if display_row >= height-3:
                        break
                        
                    # Handle long lines
                    pos = 0
                    indent = 4
                    while pos < len(line):
                        # Calculate space for this line
                        available = width - indent - 1
                        
                        # Get chunk that fits
                        chunk = line[pos:pos + available]
                        if pos + available < len(line):
                            # Find last space to break at
                            last_space = chunk.rfind(' ')
                            if last_space != -1:
                                chunk = chunk[:last_space]
                                pos += last_space + 1
                            else:
                                pos += available
                        else:
                            pos = len(line)
                            
                        # Display chunk
                        try:
                            stdscr.addstr(display_row, indent, chunk, curses.color_pair(1))
                        except curses.error:
                            pass
                            
                        display_row += 1
                        indent = 8  # Indent continuation lines
                
                stdscr.refresh()
                time.sleep(0.005)  # Faster animation delay
            
            if not response:
                continue
                
            # Extract and save code blocks
            blocks = self.generator.llm._extract_code_blocks(response)
            
            for filename, content in blocks.items():
                # Save file and add to project tracking
                filepath = Path(self.project.current_project) / filename
                filepath.parent.mkdir(parents=True, exist_ok=True)
                self.io.write_text(str(filepath), content)
                
                # Add file to project tracking
                self.project.add_file(str(filepath))
                
                # Show the saved file
                stdscr.clear()
                draw_mini_logo(stdscr)
                
                # Show file info
                row = 3
                stdscr.addstr(row, 2, f"File saved: {filename}", curses.color_pair(2))
                row += 2
                
                # Show content
                content_lines = content.split('\n')
                for line in content_lines:
                    if row >= height-3:  # Leave space at bottom
                        break
                    stdscr.addstr(row, 4, line, curses.color_pair(1))
                    row += 1
                    
                # Update status in curses
                stdscr.move(height-2, 0)
                stdscr.clrtoeol()
                stdscr.addstr(height-2, 2, f"Applied changes to {filename}", curses.color_pair(2))
                stdscr.refresh()
                stdscr.getch()
                    
        # Show completion summary
        stdscr.clear()
        draw_mini_logo(stdscr)
        row = 3
        stdscr.addstr(row, 2, "Plan completed successfully!", curses.color_pair(2))
        row += 2
        stdscr.addstr(row, 2, "Summary:", curses.color_pair(1))
        row += 1
        if plan.files_to_create:
            stdscr.addstr(row, 4, f"Created {len(plan.files_to_create)} files", curses.color_pair(2))
            row += 1
        if plan.files_to_modify:
            stdscr.addstr(row, 4, f"Modified {len(plan.files_to_modify)} files", curses.color_pair(3))
            row += 1
        if plan.dependencies:
            stdscr.addstr(row, 4, f"Added {len(plan.dependencies)} dependencies", curses.color_pair(1))
            row += 1
        stdscr.refresh()
        
        # Ask if user wants to continue with another request
        row += 2
        stdscr.addstr(row, 2, "Would you like to make another request? (y/N): ", curses.color_pair(2))
        stdscr.refresh()
        
        if chr(stdscr.getch()).lower() == 'y':
            # Save current context before continuing
            self.save_session_context()
            return True
        else:
            # Save final context before returning to menu
            self.save_session_context()
            return False

    def _handle_file_management(self, stdscr):
        """Handle file management operations."""
        # Initialize components if needed
        if self.components:
            self.components.set_screen(stdscr)
            
        # Show file management menu
        stdscr.clear()
        draw_mini_logo(stdscr)
        
        height, width = stdscr.getmaxyx()
        row = 3
        
        # Show options
        options = [
            "Edit File",
            "View File",
            "Compare Files",
            "Browse Files",
            "Back"
        ]
        
        # Display options
        stdscr.addstr(row, 2, "File Management:", curses.color_pair(1) | curses.A_BOLD)
        row += 2
        
        for idx, option in enumerate(options):
            stdscr.addstr(row, 4, f"{idx+1}. {option}", curses.color_pair(2))
            row += 1
        
        row += 1
        stdscr.addstr(row, 2, "Enter your choice (1-5): ", curses.color_pair(1))
        stdscr.refresh()
        
        # Get choice
        choice = stdscr.getch()
        if choice in range(ord('1'), ord('6')):
            choice = int(chr(choice))
        else:
            return
        
        if choice == 1:  # Edit File
            # Use file browser to select file
            file_browser = self.components.get_editor('browser')
            if file_browser:
                file_browser.run()
                selected_file = file_browser.selected_file
                if selected_file:
                    # Open file in text editor
                    text_editor = self.components.get_editor('text', selected_file)
                    if text_editor:
                        text_editor.run()
        
        elif choice == 2:  # View File
            # Use file browser to select file
            file_browser = self.components.get_editor('browser')
            if file_browser:
                file_browser.run()
                selected_file = file_browser.selected_file
                if selected_file:
                    # Open file in viewer
                    file_viewer = self.components.get_editor('view', selected_file)
                    if file_viewer:
                        file_viewer.run()
        
        elif choice == 3:  # Compare Files
            # Use file browser to select first file
            file_browser = self.components.get_editor('browser')
            if file_browser:
                stdscr.clear()
                draw_mini_logo(stdscr)
                stdscr.addstr(3, 2, "Select first file:", curses.color_pair(1))
                stdscr.refresh()
                
                file_browser.run()
                first_file = file_browser.selected_file
                
                if first_file:
                    # Select second file
                    stdscr.clear()
                    draw_mini_logo(stdscr)
                    stdscr.addstr(3, 2, "Select second file:", curses.color_pair(1))
                    stdscr.refresh()
                    
                    file_browser.run()
                    second_file = file_browser.selected_file
                    
                    if second_file:
                        # Open file diff
                        file_diff = self.components.get_editor('diff')
                        if file_diff:
                            file_diff.set_files(first_file, second_file)
                            file_diff.run()
        
        elif choice == 4:  # Browse Files
            file_browser = self.components.get_editor('browser')
            if file_browser:
                file_browser.run()
    
    def _handle_terminal(self, stdscr):
        """Handle terminal operations."""
        # Initialize components if needed
        if self.components:
            self.components.set_screen(stdscr)
            
        # Show terminal menu
        stdscr.clear()
        draw_mini_logo(stdscr)
        
        height, width = stdscr.getmaxyx()
        row = 3
        
        # Show options
        options = [
            "Open Terminal",
            "Execute Command",
            "Back"
        ]
        
        # Display options
        stdscr.addstr(row, 2, "Terminal:", curses.color_pair(1) | curses.A_BOLD)
        row += 2
        
        for idx, option in enumerate(options):
            stdscr.addstr(row, 4, f"{idx+1}. {option}", curses.color_pair(2))
            row += 1
        
        row += 1
        stdscr.addstr(row, 2, "Enter your choice (1-3): ", curses.color_pair(1))
        stdscr.refresh()
        
        # Get choice
        choice = stdscr.getch()
        if choice in range(ord('1'), ord('4')):
            choice = int(chr(choice))
        else:
            return
        
        if choice == 1:  # Open Terminal
            terminal = self.components.get_terminal_interface()
            if terminal:
                terminal.run()
        
        elif choice == 2:  # Execute Command
            # Get command
            stdscr.clear()
            draw_mini_logo(stdscr)
            command = self.get_input(stdscr, "Enter command to execute", 3, 0)
            if command:
                # Execute command
                terminal_manager = self.components.get_terminal_manager()
                if terminal_manager:
                    result = terminal_manager.execute_command(command)
                    
                    # Show result
                    stdscr.clear()
                    draw_mini_logo(stdscr)
                    row = 3
                    stdscr.addstr(row, 2, "Command output:", curses.color_pair(1))
                    row += 2
                    
                    # Display output
                    for line in result.split('\n'):
                        if row >= height - 3:
                            break
                        stdscr.addstr(row, 4, line, curses.color_pair(2))
                        row += 1
                    
                    # Wait for key press
                    stdscr.move(height-2, 0)
                    stdscr.clrtoeol()
                    stdscr.addstr(height-2, 2, "Press any key to continue...", curses.color_pair(1))
                    stdscr.refresh()
                    stdscr.getch()
    
    def _handle_testing(self, stdscr):
        """Handle testing operations."""
        # Initialize components if needed
        if self.components:
            self.components.set_screen(stdscr)
            
        # Show testing menu
        stdscr.clear()
        draw_mini_logo(stdscr)
        
        height, width = stdscr.getmaxyx()
        row = 3
        
        # Show options
        options = [
            "Generate Tests",
            "Run Tests",
            "View Coverage",
            "Back"
        ]
        
        # Display options
        stdscr.addstr(row, 2, "Testing:", curses.color_pair(1) | curses.A_BOLD)
        row += 2
        
        for idx, option in enumerate(options):
            stdscr.addstr(row, 4, f"{idx+1}. {option}", curses.color_pair(2))
            row += 1
        
        row += 1
        stdscr.addstr(row, 2, "Enter your choice (1-4): ", curses.color_pair(1))
        stdscr.refresh()
        
        # Get choice
        choice = stdscr.getch()
        if choice in range(ord('1'), ord('5')):
            choice = int(chr(choice))
        else:
            return
        
        if choice == 1:  # Generate Tests
            # Use file browser to select file
            file_browser = self.components.get_editor('browser')
            if file_browser:
                file_browser.run()
                selected_file = file_browser.selected_file
                if selected_file:
                    # Generate tests
                    self.components.run_tests(selected_file)
        
        elif choice == 2:  # Run Tests
            # Run all tests
            self.components.run_tests()
        
        elif choice == 3:  # View Coverage
            test_manager = self.components.get_test_manager()
            if test_manager:
                test_manager.show_coverage(stdscr)
    
    def _handle_code_refactoring(self, stdscr):
        """Handle code refactoring operations."""
        # Initialize components if needed
        if self.components:
            self.components.set_screen(stdscr)
            
        # Show code refactoring menu
        stdscr.clear()
        draw_mini_logo(stdscr)
        
        height, width = stdscr.getmaxyx()
        row = 3
        
        # Show options
        options = [
            "Analyze Code",
            "Refactor Code",
            "Explain Code",
            "Back"
        ]
        
        # Display options
        stdscr.addstr(row, 2, "Code Refactoring:", curses.color_pair(1) | curses.A_BOLD)
        row += 2
        
        for idx, option in enumerate(options):
            stdscr.addstr(row, 4, f"{idx+1}. {option}", curses.color_pair(2))
            row += 1
        
        row += 1
        stdscr.addstr(row, 2, "Enter your choice (1-4): ", curses.color_pair(1))
        stdscr.refresh()
        
        # Get choice
        choice = stdscr.getch()
        if choice in range(ord('1'), ord('5')):
            choice = int(chr(choice))
        else:
            return
        
        if choice == 1:  # Analyze Code
            # Use file browser to select file
            file_browser = self.components.get_editor('browser')
            if file_browser:
                file_browser.run()
                selected_file = file_browser.selected_file
                if selected_file and self.features:
                    self.features.analyze_code(selected_file, stdscr)
        
        elif choice == 2:  # Refactor Code
            # Use file browser to select file
            file_browser = self.components.get_editor('browser')
            if file_browser:
                file_browser.run()
                selected_file = file_browser.selected_file
                if selected_file and self.features:
                    self.features.refactor_code(selected_file, stdscr)
        
        elif choice == 3:  # Explain Code
            # Use file browser to select file
            file_browser = self.components.get_editor('browser')
            if file_browser:
                file_browser.run()
                selected_file = file_browser.selected_file
                if selected_file and self.features:
                    self.features.explain_code(selected_file, stdscr)
    
    def _handle_project_management(self, stdscr):
        """Handle project management operations."""
        # Initialize components if needed
        if self.components:
            self.components.set_screen(stdscr)
            
        # Show project management menu
        stdscr.clear()
        draw_mini_logo(stdscr)
        
        height, width = stdscr.getmaxyx()
        row = 3
        
        # Show options
        options = [
            "Manage Dependencies",
            "Project Statistics",
            "Generate Documentation",
            "Back"
        ]
        
        # Display options
        stdscr.addstr(row, 2, "Project Management:", curses.color_pair(1) | curses.A_BOLD)
        row += 2
        
        for idx, option in enumerate(options):
            stdscr.addstr(row, 4, f"{idx+1}. {option}", curses.color_pair(2))
            row += 1
        
        row += 1
        stdscr.addstr(row, 2, "Enter your choice (1-4): ", curses.color_pair(1))
        stdscr.refresh()
        
        # Get choice
        choice = stdscr.getch()
        if choice in range(ord('1'), ord('5')):
            choice = int(chr(choice))
        else:
            return
        
        if choice == 1:  # Manage Dependencies
            # Show dependency management menu
            stdscr.clear()
            draw_mini_logo(stdscr)
            
            row = 3
            dep_options = [
                "Install Dependencies",
                "Add Dependency",
                "Remove Dependency",
                "Update Dependencies",
                "Back"
            ]
            
            # Display options
            stdscr.addstr(row, 2, "Dependency Management:", curses.color_pair(1) | curses.A_BOLD)
            row += 2
            
            for idx, option in enumerate(dep_options):
                stdscr.addstr(row, 4, f"{idx+1}. {option}", curses.color_pair(2))
                row += 1
            
            row += 1
            stdscr.addstr(row, 2, "Enter your choice (1-5): ", curses.color_pair(1))
            stdscr.refresh()
            
            # Get choice
            dep_choice = stdscr.getch()
            if dep_choice in range(ord('1'), ord('6')):
                dep_choice = int(chr(dep_choice))
            else:
                return
            
            if dep_choice == 1:  # Install Dependencies
                self.components.manage_dependencies('install')
            
            elif dep_choice == 2:  # Add Dependency
                # Get dependency name
                stdscr.clear()
                draw_mini_logo(stdscr)
                dependency = self.get_input(stdscr, "Enter dependency name", 3, 0)
                if dependency:
                    self.components.manage_dependencies('add', dependency)
            
            elif dep_choice == 3:  # Remove Dependency
                # Get dependency name
                stdscr.clear()
                draw_mini_logo(stdscr)
                dependency = self.get_input(stdscr, "Enter dependency name", 3, 0)
                if dependency:
                    self.components.manage_dependencies('remove', dependency)
            
            elif dep_choice == 4:  # Update Dependencies
                self.components.manage_dependencies('update')
        
        elif choice == 2:  # Project Statistics
            if self.features:
                self.features.show_project_statistics(stdscr)
        
        elif choice == 3:  # Generate Documentation
            if self.features:
                self.features.generate_documentation(stdscr)
    
    def _process_agent_request(self, stdscr, query: str) -> bool:
        """Process a code generation request using the autonomous agent.
        
        Args:
            stdscr: Curses window for display
            query: User's code request
            
        Returns:
            bool: True if should continue, False to exit
        """
        try:
            # Check if agent is available
            if not self.agent:
                stdscr.clear()
                draw_mini_logo(stdscr)
                stdscr.addstr(3, 2, "Error: No project selected", curses.color_pair(4) | curses.A_BOLD)
                stdscr.refresh()
                stdscr.getch()
                return True

            # Use the agent interface for better UX
            interface = self.agent_interface
            if interface:
                interface.set_screen(stdscr)
                interface.run_one_request(query)
                return True
            
            # If interface isn't available, fall back to direct execution
            # Show thinking message
            stdscr.clear()
            draw_mini_logo(stdscr)
            stdscr.addstr(3, 2, "Thinking about your request...", curses.color_pair(2))
            stdscr.refresh()
            
            # Execute the request using the agent
            results = self.agent.execute_request(query)
            
            # Show results
            for i, result in enumerate(results):
                stdscr.clear()
                draw_mini_logo(stdscr)
                
                # Show action info
                row = 3
                action_type = result.get('type', result.get('action', 'unknown'))
                success = result.get('success', False)
                message = result.get('message', '')
                
                # Format action type with proper capitalization
                action_display = ' '.join(word.capitalize() for word in action_type.split('_'))
                
                # Display action header with status color
                color = curses.color_pair(2) if success else curses.color_pair(4)
                stdscr.addstr(row, 2, f"Action {i+1}/{len(results)}: {action_display}", 
                             color | curses.A_BOLD)
                row += 1
                
                # Display message
                stdscr.addstr(row, 2, message, color)
                row += 2
                
                # Display specific content based on action type
                if 'content' in result:
                    height, width = stdscr.getmaxyx()
                    content = result.get('content', '')
                    lines = content.split('\n')
                    for line in lines[:min(10, len(lines))]:  # Limit to 10 lines
                        if row >= height - 3:
                            break
                        stdscr.addstr(row, 4, line[:width-8], curses.color_pair(1))
                        row += 1
                
                stdscr.refresh()
                stdscr.getch()
            
            return True
            
        except Exception as e:
            # Show error
            stdscr.clear()
            draw_mini_logo(stdscr)
            stdscr.addstr(3, 2, f"Error: {e}", curses.color_pair(4) | curses.A_BOLD)
            stdscr.refresh()
            stdscr.getch()
            return True

    def _run_session_loop(self, stdscr, initial_query: str):
        """Run a continuous session loop starting with the given query.
        
        Args:
            stdscr: The curses window to use for display
            initial_query: The first code request to process
            
        The loop continues until either:
        - The user enters an empty query
        - The user chooses not to continue after a request
        - An error occurs during request handling
        """
        # Initialize components with the screen
        if self.components:
            self.components.set_screen(stdscr)
        
        query = initial_query
        while True:
            try:
                # Process the query using the agent
                if not self._process_agent_request(stdscr, query):
                    break
                
                # Get next request based on mode
                if stdscr:
                    try:
                        stdscr.clear()
                        draw_mini_logo(stdscr)
                        query = self.get_input(stdscr, "Enter your request (or 'exit' to return to main menu)", 3, 0)
                    except curses.error:
                        query = ""
                else:
                    draw_mini_logo()
                    query = input("Enter your request (or 'exit' to return to main menu): ")
                
                if not query:
                    break
                    
                if query.lower() in ('exit', 'quit', 'back', 'return'):
                    break
                    
            except Exception as e:
                # Show error based on mode
                if stdscr:
                    try:
                        height, width = stdscr.getmaxyx()
                        stdscr.move(height-2, 0)
                        stdscr.clrtoeol()
                        stdscr.addstr(height-2, 2, f"Error: {e}", curses.color_pair(3))
                        stdscr.refresh()
                        stdscr.getch()
                    except curses.error:
                        print(f"Error: {e}")
                else:
                    print(f"Error: {e}")
                continue

    def run(self, stdscr):
        """Run the terminal application."""
        try:
            # Determine if we should use log window from config
            use_log_window = False
            try:
                with open('config.json', 'r') as f:
                    config = json.load(f)
                    use_log_window = config.get('use_log_window', False)
            except (FileNotFoundError, json.JSONDecodeError, TypeError):
                print("Warning: Could not load config.json, using default settings")
            except Exception as e:
                print(f"Warning: Unexpected error reading config: {e}")

            if use_log_window:
                # Log window mode - don't use curses
                stdscr = None
                self.log_window.start()
            else:
                # Curses mode - initialize curses screen
                try:
                    init_colors()
                    curses.curs_set(0)
                    self.show_banner(stdscr)
                except curses.error as e:
                    print(f"Curses error during initialization: {e}")
                    return

            # Initialize project
            try:
                if not self.initialize_project_folder(stdscr):
                    if stdscr:
                        stdscr.addstr(2, 2, "Failed to initialize project. Press any key to exit...")
                        stdscr.refresh()
                        stdscr.getch()
                    else:
                        print("Failed to initialize project")
                    return
            except curses.error:
                print("Error: Screen too small for project initialization")
                return
            except Exception as e:
                print(f"Error initializing project: {e}")
                return

            # Set up UI and components with correct display mode
            self.ui.set_screen(None if use_log_window else stdscr)
            if self.components:
                self.components.set_screen(None if use_log_window else stdscr)

            # Create appropriate menu
# Create appropriate menu
            menu = Menu(None if use_log_window else stdscr)
            
            while True:
                try:
                    choice = menu.show()
                    
                    # Only perform curses operations if not in log window mode
                    if stdscr:
                        try:
                            stdscr.clear()
                            draw_mini_logo(stdscr)  # Keep mini logo visible
                        except curses.error:
                            print("Error: Screen too small for menu display")
                            continue
                    else:
                        draw_mini_logo()  # Print mode logo
                    
                    # Handle menu choice
                    if choice == 0:  # New Session
                        try:
                            self.start_new_session()
                            if stdscr:
                                # Clear screen for aider-like interface
                                stdscr.clear()
                                # Draw just the logo at top
                                draw_mini_logo(stdscr)
                            else:
                                draw_mini_logo()
                            
                            # Get input based on mode
                            if stdscr:
                                query = self.get_input(stdscr, "Enter your code request", 3, 0)
                            else:
                                query = input("Enter your code request: ")
                            if not query:
                                continue
                                
                            self._run_session_loop(stdscr, query)
                        except Exception as e:
                            if stdscr:
                                try:
                                    stdscr.addstr(2, 2, f"Error in new session: {e}")
                                    stdscr.refresh()
                                    stdscr.getch()
                                except curses.error:
                                    print(f"Error: {e}")
                            else:
                                print(f"Error: {e}")
                            continue

                    elif choice == 1:  # Resume Session
                        # List available sessions
                        memory_dir = Path(self.project.current_project) / '.memory'
                        sessions = []
                        if memory_dir.exists():
                            for f in memory_dir.glob('session_*.json'):
                                session_id = f.stem.replace('session_', '')
                                try:
                                    with open(f, 'r') as sf:
                                        data = json.load(sf)
                                        timestamp = datetime.fromisoformat(data['timestamp'])
                                        sessions.append((session_id, timestamp))
                                except Exception:
                                    continue
                        
                        if not sessions:
                            if stdscr:
                                stdscr.addstr(4, 2, "No previous sessions found", curses.color_pair(3))
                            else:
                                print("No previous sessions found")
                        else:
                            # Sort sessions by timestamp, newest first
                            sessions.sort(key=lambda x: x[1], reverse=True)
                            
                            row = 4
                            if stdscr:
                                stdscr.addstr(row, 2, "Available sessions:", curses.color_pair(2))
                                row += 2
                                
                                for session_id, timestamp in sessions:
                                    stdscr.addstr(row, 4, f"{session_id} ({timestamp.strftime('%Y-%m-%d %H:%M:%S')})", 
                                                curses.color_pair(1))
                                    row += 1
                                
                                row += 1
                                session_id = self.get_input(stdscr, "Enter session ID to resume", row, 2)
                                if session_id and self.load_session_context(session_id):
                                    stdscr.addstr(row + 2, 2, f"Resumed session {session_id}", curses.color_pair(2))
                                    
                                    # Start session loop
                                    stdscr.clear()
                                    draw_mini_logo(stdscr)
                                    query = self.get_input(stdscr, "Enter your code request", 3, 0)
                                    if query:
                                        self._run_session_loop(stdscr, query)
                                else:
                                    stdscr.addstr(row + 2, 2, "Failed to resume session", curses.color_pair(3))
                            else:
                                # Print mode handling for session list
                                print("Available sessions:")
                                for session_id, timestamp in sessions:
                                    print(f"  {session_id} ({timestamp.strftime('%Y-%m-%d %H:%M:%S')})")
                                
                                session_id = input("Enter session ID to resume: ")
                                if session_id and self.load_session_context(session_id):
                                    print(f"Resumed session {session_id}")
                                    query = input("Enter your code request: ")
                                    if query:
                                        self._run_session_loop(None, query)
                                else:
                                    print("Failed to resume session")
                    
                    elif choice == 2:  # View Project Files
                        files = self.project.get_project_files()
                        if not files:
                            if stdscr:
                                stdscr.addstr(4, 2, "No files in project", curses.color_pair(3))
                            else:
                                print("No files in project")
                        else:
                            if stdscr:
                                row = 4
                                for file_info in files:
                                    stdscr.addstr(
                                        row, 2,
                                        f"[{file_info['status']}] {file_info['path']}",
                                        curses.color_pair(1)
                                    )
                                    row += 1
                            else:
                                print("Project files:")
                                for file_info in files:
                                    print(f"[{file_info['status']}] {file_info['path']}")
                                
                    elif choice == 3:  # Provider Settings
                        self.settings.show_settings_ui(stdscr)
                        self.config = self._load_config()
                        # Reset handlers to reload config
                        self._llm = None
                        self._generator = None
                        
                    elif choice == 4:  # Toggle Log Window
                        if not self.log_window.running:
                            self.log_window.start()
                            if stdscr:
                                stdscr.addstr(4, 2, "Log window opened", curses.color_pair(2))
                            else:
                                print("Log window opened")
                        else:
                            self.log_window.stop()
                            if stdscr:
                                stdscr.addstr(4, 2, "Log window closed", curses.color_pair(2))
                            else:
                                print("Log window closed")
                            
                    elif choice == 5:  # Exit
                        if self.log_window.running:
                            self.log_window.stop()
                        if stdscr:
                            stdscr.addstr(4, 2, "Goodbye!", curses.color_pair(2))
                            stdscr.refresh()
                        else:
                            print("Goodbye!")
                        time.sleep(1)
                        break
                        
                    # Handle "press any key" based on mode
                    if stdscr:
                        try:
                            height, width = stdscr.getmaxyx()
                            stdscr.addstr(height-2, 2, "Press any key to continue...")
                            stdscr.refresh()
                            stdscr.getch()
                        except curses.error:
                            continue
                    else:
                        input("\nPress Enter to continue...")
                
                except KeyboardInterrupt:
                    if self.log_window.running:
                        self.log_window.stop()
                    break
                except Exception as e:
                    if stdscr:
                        try:
                            stdscr.clear()
                            stdscr.addstr(1, 2, f"Error: {str(e)}", curses.color_pair(3))
                            stdscr.refresh()
                            stdscr.getch()
                        except curses.error:
                            print(f"Error: {str(e)}")
                    else:
                        print(f"Error: {str(e)}")

        except Exception as e:
            # Added exception handling for the outer try block
            if stdscr:
                try:
                    stdscr.clear()
                    stdscr.addstr(0, 0, f"Fatal error: {str(e)}")
                    stdscr.refresh()
                    stdscr.getch()
                except curses.error:
                    print(f"Fatal error: {str(e)}")
            else:
                print(f"Fatal error: {str(e)}")
        finally:
            # Clean up resources
            if hasattr(self, 'log_window') and getattr(self.log_window, 'running', False):
                self.log_window.stop()

def main():
    """Main entry point."""
    try:
        # Check if we should launch in new window
        if len(sys.argv) < 2 or sys.argv[1] != '--new-instance':
            launch_new_terminal()
        else:
            terminal = ANJTerminal()
            curses.wrapper(terminal.run)
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
