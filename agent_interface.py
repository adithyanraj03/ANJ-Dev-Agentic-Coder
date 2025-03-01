import curses
from typing import Dict, Any, List, Optional
import json
import time
import os

# Try to import log queue, but have a fallback mechanism
try:
    from queue_handler import log_queue
    HAS_LOG_QUEUE = True
except ImportError:
    HAS_LOG_QUEUE = False
    import logging
    logging.basicConfig(level=logging.INFO)

class AgentInterface:
    """User interface for interacting with the autonomous coding agent."""
    
    def __init__(self, agent_handler, stdscr=None):
        """Initialize the agent interface."""
        self.agent = agent_handler
        self.stdscr = None  # Initialize to None
        self.history = []
        self.session_window = None
        
        # Initialize display mode based on environment
        force_log_mode = os.environ.get('FORCE_LOG_MODE', '').lower() == 'true'
        self.using_log_window = False
        
        # Only use log window if explicitly forced
        if force_log_mode:
            try:
                from log_window import log_queue
                self.using_log_window = True
                if hasattr(self.agent, 'planner'):
                    self.agent.planner.using_log_window = True
            except ImportError:
                pass
        else:
            # Prefer interactive session window
            self.set_screen(stdscr)
            if not self.using_log_window and self.stdscr:
                try:
                    from editors.session_window import SessionWindow
                    self.session_window = SessionWindow(self.stdscr)
                except ImportError:
                    pass
        
    def _wrap_text(self, text: str, width: int) -> List[str]:
        """Helper method to wrap text to fit the screen."""
        if not text:
            return []
            
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            # Check if adding this word would exceed the width
            if current_length + len(word) + (1 if current_length > 0 else 0) <= width:
                current_line.append(word)
                current_length += len(word) + (1 if current_length > 0 else 0)
            else:
                # Line is full, start a new one
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
                current_length = len(word)
        
        # Add the last line if there's anything left
        if current_line:
            lines.append(' '.join(current_line))
            
        return lines
        
    def set_screen(self, stdscr):
        """Set the curses screen."""
        # Always set our own screen first
        self.stdscr = None if getattr(self, 'using_log_window', False) else stdscr
        
        # Ensure planner has proper display settings before setting screen
        if hasattr(self.agent, 'planner') and self.agent.planner is not None:
            # First ensure planner has using_log_window set
            if not hasattr(self.agent.planner, 'using_log_window'):
                self.agent.planner.using_log_window = getattr(self, 'using_log_window', False)
            
            # Now safely try to set the screen
            if hasattr(self.agent.planner, 'set_screen'):
                try:
                    screen_to_use = None if self.agent.planner.using_log_window else stdscr
                    self.agent.planner.set_screen(screen_to_use)
                except (AttributeError, TypeError) as e:
                    logging.warning(f"Could not set planner screen: {str(e)}")
        
    def draw_header(self, title="ANJ Dev Agent"):
        """Draw the interface header with ANJ DEV logo."""
        if not self.stdscr:
            return
        
        try:
            height, width = self.stdscr.getmaxyx()
            
            # Always preserve the ANJ DEV logo in the header
            try:
                if hasattr(curses, 'color_pair'):
                    color = curses.color_pair(1)
                    self.stdscr.addstr(0, 0, "╔═════ ANJ DEV ════╗", color | curses.A_BOLD)
                    self.stdscr.addstr(1, 0, "╚══by Adithyanraj══╝", color)
                else:
                    self.stdscr.addstr(0, 0, "╔═════ ANJ DEV ════╗", curses.A_BOLD)
                    self.stdscr.addstr(1, 0, "╚══by Adithyanraj══╝")
            except (curses.error, TypeError):
                # If color fails, try without it
                try:
                    self.stdscr.addstr(0, 0, "╔═════ ANJ DEV ════╗")
                    self.stdscr.addstr(1, 0, "╚══by Adithyanraj══╝")
                except curses.error:
                    pass
            
            # Add title if provided, but ensure it doesn't overlap with the logo
            if title and title != "ANJ Dev":
                try:
                    # Calculate position to avoid logo overlap
                    logo_width = 20  # Width of the ANJ DEV logo box
                    title_pos = max(logo_width + 2, (width - len(title) - 2) // 2)
                    if hasattr(curses, 'color_pair'):
                        self.stdscr.addstr(0, title_pos, f" {title} ", curses.color_pair(1) | curses.A_BOLD)
                    else:
                        self.stdscr.addstr(0, title_pos, f" {title} ", curses.A_BOLD)
                except curses.error:
                    pass
                    
        except (curses.error, TypeError, AttributeError) as e:
            print(f"Header drawing error: {str(e)}")
        
    def get_input(self, prompt: str, y: int, x: int) -> str:
        """Get input with proper cursor positioning."""
        if not self.stdscr:
            try:
                return input(f"{prompt}: ")
            except (KeyboardInterrupt, EOFError):
                return ""

        try:
            height, width = self.stdscr.getmaxyx()
            y = min(y, height - 3)  # Leave space at bottom
            x = min(x, width - len(prompt) - 3)
            
            self.stdscr.addstr(y, x, f"{prompt}: ")
            self.stdscr.refresh()
            
            # Position cursor after prompt
            input_x = x + len(prompt) + 2
            self.stdscr.move(y, input_x)
            
            # Only try to use curses functions if they're available
            if hasattr(curses, 'echo') and hasattr(curses, 'curs_set'):
                curses.echo()
                curses.curs_set(1)
            
            # Get input with better sizing
            max_len = width - input_x - 2
            value = self.stdscr.getstr(y, input_x, max_len)
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
    
    def display_action_result(self, result: Dict[str, Any], row: int = 3) -> int:
        """Display the result of an action and return the next row position."""
        if not self.stdscr:
            print(json.dumps(result, indent=2))
            return row

        height, width = 24, 80  # Default size if getmaxyx fails
        try:
            height, width = self.stdscr.getmaxyx()
        except (curses.error, AttributeError):
            pass

        try:
            # Show action info
            action_type = result.get('type', result.get('action', 'unknown'))
            success = result.get('success', False)
            message = result.get('message', '')
            
            # Format action type with proper capitalization
            action_display = ' '.join(word.capitalize() for word in action_type.split('_'))
            
            # Display action header with status color
            try:
                color = curses.color_pair(2) if success else curses.color_pair(4)
                self.stdscr.addstr(row, 2, f"{action_display}: ", color | curses.A_BOLD)
                row += 1
                
                # Display message
                if message:
                    self.stdscr.addstr(row, 4, str(message), color)
                    row += 2
                else:
                    row += 1
            except (curses.error, TypeError):
                # If display fails, try without color and formatting
                try:
                    self.stdscr.addstr(row, 2, f"{action_display}: {message}")
                    row += 2
                except curses.error:
                    return row
        except (curses.error, TypeError, AttributeError) as e:
            print(f"Display error: {str(e)}")
            return row
        
        # Display specific content based on action type
        try:
            if 'content' in result:
                content = result['content']
                lines = content.split('\n')
                for line in lines[:min(10, len(lines))]:  # Limit to 10 lines
                    if row >= height - 3:
                        break
                    try:
                        self.stdscr.addstr(row, 4, line[:width-8], curses.color_pair(1))
                        row += 1
                    except curses.error:
                        pass
                    
                if len(lines) > 10:
                    try:
                        self.stdscr.addstr(row, 4, "... (content truncated)", curses.color_pair(3))
                        row += 1
                    except curses.error:
                        pass
            
            # For analysis results
            if 'analysis' in result:
                analysis = result['analysis']
                lines = analysis.split('\n')
                for line in lines[:min(10, len(lines))]:  # Limit to 10 lines
                    if row >= height - 3:
                        break
                    try:
                        self.stdscr.addstr(row, 4, line[:width-8], curses.color_pair(1))
                        row += 1
                    except curses.error:
                        pass
                    
                if len(lines) > 10:
                    try:
                        self.stdscr.addstr(row, 4, "... (analysis truncated)", curses.color_pair(3))
                        row += 1
                    except curses.error:
                        pass
            
            # For command results
            if 'stdout' in result:
                stdout = result['stdout']
                if stdout:
                    try:
                        self.stdscr.addstr(row, 4, "Command output:", curses.color_pair(2))
                        row += 1
                    except curses.error:
                        pass
                    
                    lines = stdout.split('\n')
                    for line in lines[:min(5, len(lines))]:  # Limit to 5 lines
                        if row >= height - 3:
                            break
                        try:
                            self.stdscr.addstr(row, 6, line[:width-10], curses.color_pair(1))
                            row += 1
                        except curses.error:
                            pass
                        
                    if len(lines) > 5:
                        try:
                            self.stdscr.addstr(row, 6, "... (output truncated)", curses.color_pair(3))
                            row += 1
                        except curses.error:
                            pass
            
            # For errors
            if 'error' in result:
                try:
                    self.stdscr.addstr(row, 4, f"Error: {result['error']}", curses.color_pair(4))
                    row += 1
                except curses.error:
                    pass
        except (curses.error, TypeError, AttributeError) as e:
            print(f"Display error in content section: {str(e)}")
        
        return row + 1  # Return the next row to use

    def run_session(self):
        """Run an interactive session with the agent."""
        if not self.session_window and not self.using_log_window:
            print("Error: No screen available")
            return
            
        while True:
            try:
                # Clear screen and get user input
                if self.session_window:
                    self.session_window.clear()
                    self.session_window._draw_header("ANJ Dev Agent")
                    request = self.session_window.get_input("Enter your request (or 'exit' to quit)")
                else:
                    request = input("Enter your request (or 'exit' to quit): ")
                
                if not request or request.lower() in ('exit', 'quit'):
                    break
                
                # Start loading animation
                if self.session_window:
                    self.session_window.start_loading("Processing request...")
                
                try:
                    # Execute request and get results
                    results = self.agent.execute_request(request, self.stdscr)
                    
                    # Stop loading animation
                    if self.session_window:
                        self.session_window.stop_loading()
                    
                    # Handle interactive session UI
                    success = True
                    for result in results:
                        if self.session_window:
                            action_type = result.get('type', result.get('action', 'unknown'))
                            
                            if action_type == 'code_update':
                                # Show changes
                                if 'files' in result:
                                    for file in result['files']:
                                        try:
                                            with open(file, 'r') as f:
                                                content = f.read()
                                                self.session_window.show_preview(
                                                    os.path.basename(file),
                                                    content,
                                                    is_new=True
                                                )
                                        except Exception as e:
                                            self.session_window.show_error(str(e))
                                            success = False
                                            
                            elif action_type == 'run_command':
                                # Show command output
                                cmd_success = result.get('success', False)
                                output = result.get('stdout', '') or result.get('message', '')
                                if output:
                                    self.session_window.clear()
                                    self.session_window._draw_header("Command Output")
                                    self.session_window._draw_footer("Press any key to continue...")
                                    # Format output with line numbers and colors
                                    lines = output.splitlines()
                                    for i, line in enumerate(lines):
                                        try:
                                            # Line numbers
                                            self.stdscr.addstr(2 + i, 2, f"{i+1:4d} │ ", curses.color_pair(1))
                                            # Command output with appropriate color
                                            color = curses.color_pair(2) if cmd_success else curses.color_pair(4)
                                            self.stdscr.addstr(2 + i, 8, line, color)
                                        except curses.error:
                                            break
                                    self.stdscr.refresh()
                                    self.stdscr.getch()
                            
                            elif action_type == 'error':
                                self.session_window.show_error(result.get('message', 'Unknown error'))
                                success = False
                        else:
                            print(f"\nResult: {result.get('message', str(result))}")
                    
                    # Add to history
                    self.history.append({
                        'request': request,
                        'results': results,
                        'success': success
                    })
                    
                except Exception as e:
                    if self.session_window:
                        self.session_window.show_error(str(e))
                    else:
                        print(f"\nError: {e}")
                    
                    # Wait for user acknowledgment
                    if self.session_window:
                        self.stdscr.getch()
                    else:
                        input("\nPress Enter to continue...")
                
            except (curses.error, TypeError, AttributeError) as e:
                print(f"\nDisplay error: {e}")
                try:
                    input("Press Enter to continue...")
                except (KeyboardInterrupt, EOFError):
                    break

    def _execute_command(self, command: str) -> None:
        """Execute a shell command and display its output."""
        self.session_window.start_loading(f"Running: {command}")
        
        try:
            import subprocess
            proc = subprocess.run(
                command, 
                shell=True, 
                cwd=str(self.agent.project_path),
                capture_output=True,
                text=True
            )
            
            self.session_window.stop_loading()
            self.session_window.clear()
            self.session_window._draw_header("Command Output")
            self.session_window._draw_footer("Press any key to continue...")
            
            if proc.returncode == 0:
                self.stdscr.addstr(2, 2, "Command executed successfully:", curses.color_pair(2))
            else:
                self.stdscr.addstr(2, 2, "Command failed:", curses.color_pair(4))
            
            output = proc.stdout or proc.stderr or "No output"
            lines = output.split('\n')
            for i, line in enumerate(lines[:20]):
                try:
                    self.stdscr.addstr(4 + i, 4, line, curses.color_pair(1))
                except curses.error:
                    break
                    
            if len(lines) > 20:
                try:
                    self.stdscr.addstr(4 + 20, 4, "... (output truncated)", curses.color_pair(3))
                except curses.error:
                    pass
                    
            self.stdscr.refresh()
            self.stdscr.getch()
            
        except Exception as cmd_err:
            self.session_window.stop_loading()
            self.session_window.show_error(f"Error running command: {cmd_err}")
            self.stdscr.getch()

    def run_one_request(self, request: str) -> List[Dict[str, Any]]:
        """Run a single request and return the results with enhanced agent capabilities."""
        # Using log window setting is checked in __init__
        if self.using_log_window:
            # Log mode - use logging without curses
            if HAS_LOG_QUEUE:
                log_queue.put({"message": f"Processing request: {request}", "level": "INFO"})
            else:
                print(f"\nProcessing request: {request}")
            
        elif self.session_window:
            # Use session window for display
            self.session_window.clear()
            self.session_window._draw_header("ANJ Dev Agent")
            self.session_window._draw_footer("Processing request...")
            
            # Show a more informative message about the agent's processing steps
            self.session_window.start_loading("Analyzing codebase and thinking about implementation...")
        else:
            # Basic print mode
            print(f"\nProcessing request: {request}")
        
        results = []
        try:
            # Ensure the agent's planner is properly initialized
            if hasattr(self.agent, 'planner') and self.agent.planner is not None:
                # Ensure planner has using_log_window set correctly
                if not hasattr(self.agent.planner, 'using_log_window'):
                    self.agent.planner.using_log_window = self.using_log_window
                # Set screen with proper mode
                if hasattr(self.agent.planner, 'set_screen'):
                    try:
                        screen_to_use = None if self.agent.planner.using_log_window else self.stdscr
                        self.agent.planner.set_screen(screen_to_use)
                    except (AttributeError, TypeError) as e:
                        logging.warning(f"Could not set planner screen: {str(e)}")
            
            # First try to explore the codebase if agent has this capability
            if hasattr(self.agent, 'explore_codebase'):
                try:
                    # Update the loading message to inform the user
                    if self.session_window:
                        self.session_window.stop_loading()
                        self.session_window.start_loading("Exploring codebase to understand project structure...")
                    
                    # Explore codebase
                    self.agent.explore_codebase(request)
                    
                    # Update the loading message again
                    if self.session_window:
                        self.session_window.stop_loading()
                        self.session_window.start_loading("Creating plan for implementation...")
                except Exception as e:
                    logging.warning(f"Error during codebase exploration: {e}")
                    # Continue without exploration
            
            # Execute the user's request
            results = self.agent.execute_request(request, self.stdscr)
            
            # Display results based on mode
            if self.session_window:
                try:
                    self.session_window.stop_loading()
                    
                    for result in results:
                        action_type = result.get('type', result.get('action', 'unknown'))
                        
                        if action_type == 'error':
                            self.session_window.show_error(result.get('message', 'Unknown error'))
                        
                        elif action_type == 'info':
                            self.session_window.clear()
                            self.session_window._draw_header("Information")
                            self.session_window._draw_footer("Press any key to continue...")
                            # Use better text wrapping for messages
                            message = result.get('message', '')
                            height, width = self.stdscr.getmaxyx()
                            wrapped_lines = self._wrap_text(message, width-6)
                            
                            for i, line in enumerate(wrapped_lines):
                                try:
                                    self.stdscr.addstr(2+i, 2, line, curses.color_pair(1))
                                except curses.error:
                                    break
                            self.stdscr.refresh()
                            self.stdscr.getch()
                            
                        elif action_type == 'code_update':
                            # For code updates, show a summary of changes
                            files_changed = result.get('files', [])
                            if files_changed:
                                self.session_window.clear()
                                self.session_window._draw_header("Code Changes")
                                self.session_window._draw_footer("Press any key to continue...")
                                
                                self.stdscr.addstr(2, 2, "Changes applied to the following files:", curses.color_pair(1))
                                for i, file_path in enumerate(files_changed, 1):
                                    try:
                                        # Show filename with color
                                        self.stdscr.addstr(3 + i, 4, f"{i}. {os.path.basename(file_path)}", curses.color_pair(2))
                                        # Show file path in a different color
                                        self.stdscr.addstr(3 + i, 4 + len(f"{i}. {os.path.basename(file_path)}"), 
                                                       f" ({os.path.dirname(file_path)})", curses.color_pair(3))
                                    except curses.error:
                                        break
                                
                                self.stdscr.refresh()
                                self.stdscr.getch()
                                
                        elif action_type == 'run_command':
                            # For run commands, offer to execute them
                            command = result.get('command', '')
                            message = result.get('message', f"Run command: {command}")
                            
                            self.session_window.clear()
                            self.session_window._draw_header("Run Command")
                            self.session_window._draw_footer("Press Y to run, N to skip, E to edit command...")
                            
                            self.stdscr.addstr(2, 2, message, curses.color_pair(2))
                            self.stdscr.addstr(4, 2, f"Command: {command}", curses.color_pair(1))
                            self.stdscr.refresh()
                            
                            # Show command execution menu
                            key = self.stdscr.getch()
                            action = chr(key).lower()
                            
                            if action == 'y':
                                # Run the command as-is
                                self._execute_command(command)
                            elif action == 'e':
                                # Edit the command
                                self.session_window.clear()
                                self.session_window._draw_header("Edit Command")
                                edited_command = self.get_input("Edit command", 2, 2)
                                
                                if edited_command:
                                    # Run the edited command
                                    self._execute_command(edited_command)
                
                except (curses.error, TypeError, AttributeError) as ui_error:
                    # Fallback to basic print mode if curses fails
                    logging.error(f"UI error: {ui_error}")
                    for result in results:
                        print(f"\nResult: {result.get('message', str(result))}")
            
            elif self.using_log_window:
                # Log results through the log window
                for result in results:
                    level = "SUCCESS" if result.get('success', False) else "ERROR"
                    message = result.get('message', str(result))
                    log_queue.put({"message": message, "level": level})
            
            else:
                # Basic print mode
                for result in results:
                    print(f"\nResult: {result.get('message', str(result))}")
            
            # Add the request and results to history
            self.history.append({
                'request': request,
                'results': results
            })
            
            # Save agent memory if supported
            if hasattr(self.agent, '_save_memory'):
                try:
                    self.agent._save_memory()
                except Exception as e:
                    logging.warning(f"Error saving agent memory: {e}")
            
            return results
            
        except Exception as e:
            error = {"type": "error", "success": False, "message": str(e)}
            
            if self.stdscr and not self.using_log_window:
                # Show error with ANJ DEV logo preserved
                self.stdscr.clear()
                self.draw_header("Error")
                self.stdscr.addstr(3, 2, f"Error: {e}", curses.color_pair(4) | curses.A_BOLD)
                self.stdscr.refresh()
                self.stdscr.getch()
            elif self.using_log_window:
                log_queue.put({"message": f"Error: {str(e)}", "level": "ERROR"})
            else:
                print(f"\nError: {str(e)}")
            
            return [error]
