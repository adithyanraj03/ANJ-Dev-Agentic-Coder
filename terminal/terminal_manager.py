#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Terminal manager for executing shell commands."""
import os
import sys
import shlex
import signal
import subprocess
import threading
import queue
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Generator, Union

class TerminalManager:
    """Manages terminal operations and command execution."""
    
    def __init__(self, project_root: Optional[Path] = None):
        """Initialize terminal manager.
        
        Args:
            project_root: Optional project root directory
        """
        self.project_root = project_root or Path.cwd()
        self.current_dir = self.project_root
        self.processes = {}
        self.process_lock = threading.Lock()
        self.next_process_id = 1
        self.active_process = None
        self.active_process_queue = None
        self.environment = os.environ.copy()
        
        # Initialize shell
        self._init_shell()
    
    def _init_shell(self):
        """Initialize shell environment."""
        # Add common paths to PATH if not already present
        paths_to_add = []
        
        if sys.platform == 'win32':
            # Windows paths
            paths_to_add = [
                str(Path.home() / 'AppData' / 'Local' / 'Programs' / 'Python' / 'Python310' / 'Scripts'),
                str(Path.home() / 'AppData' / 'Roaming' / 'npm'),
            ]
        else:
            # Unix paths
            paths_to_add = [
                '/usr/local/bin',
                '/usr/bin',
                str(Path.home() / '.local' / 'bin'),
                str(Path.home() / 'bin'),
                str(Path.home() / '.npm-global' / 'bin'),
            ]
            
        # Add paths if they exist and aren't already in PATH
        current_path = self.environment.get('PATH', '')
        path_parts = current_path.split(os.pathsep)
        
        for path in paths_to_add:
            if os.path.exists(path) and path not in path_parts:
                current_path = path + os.pathsep + current_path
                
        self.environment['PATH'] = current_path
        
        # Set up virtual environment if one exists in project root
        venv_paths = [
            self.project_root / 'venv',
            self.project_root / '.venv',
            self.project_root / 'env',
            self.project_root / '.env',
        ]
        
        for venv_path in venv_paths:
            if self._is_virtual_env(venv_path):
                self._activate_virtual_env(venv_path)
                break
    
    def _is_virtual_env(self, path: Path) -> bool:
        """Check if path is a virtual environment.
        
        Args:
            path: Path to check
            
        Returns:
            bool: True if path is a virtual environment
        """
        if not path.exists():
            return False
            
        # Check for key directories/files that indicate a virtual environment
        if sys.platform == 'win32':
            return (path / 'Scripts' / 'python.exe').exists()
        else:
            return (path / 'bin' / 'python').exists()
    
    def _activate_virtual_env(self, venv_path: Path):
        """Activate virtual environment.
        
        Args:
            venv_path: Path to virtual environment
        """
        if sys.platform == 'win32':
            bin_dir = venv_path / 'Scripts'
        else:
            bin_dir = venv_path / 'bin'
            
        # Update PATH to prioritize the virtual environment
        self.environment['PATH'] = str(bin_dir) + os.pathsep + self.environment['PATH']
        
        # Set VIRTUAL_ENV environment variable
        self.environment['VIRTUAL_ENV'] = str(venv_path)
        
        # Remove PYTHONHOME if it exists
        if 'PYTHONHOME' in self.environment:
            del self.environment['PYTHONHOME']
    
    def get_cwd(self) -> str:
        """Get current working directory.
        
        Returns:
            str: Current working directory
        """
        return str(self.current_dir)
    
    def set_cwd(self, path: Union[str, Path]) -> bool:
        """Set current working directory.
        
        Args:
            path: New working directory
            
        Returns:
            bool: True if directory was changed successfully
        """
        try:
            # Convert to Path object if string
            if isinstance(path, str):
                path = Path(path)
                
            # Resolve path (handle relative paths)
            if not path.is_absolute():
                path = self.current_dir / path
                
            # Check if path exists and is a directory
            if not path.exists() or not path.is_dir():
                return False
                
            # Change directory
            self.current_dir = path.resolve()
            return True
            
        except Exception:
            return False
    
    def execute_command(self, command: str) -> Generator[Tuple[str, str], None, None]:
        """Execute shell command and yield output.
        
        Args:
            command: Command to execute
            
        Yields:
            Tuple[str, str]: Tuples of (output_type, line) where output_type is 'stdout' or 'stderr'
        """
        # Handle cd command specially
        if command.strip().startswith('cd '):
            parts = shlex.split(command)
            if len(parts) > 1:
                path = ' '.join(parts[1:])
                if self.set_cwd(path):
                    yield ('stdout', f"Changed directory to {self.get_cwd()}")
                else:
                    yield ('stderr', f"Directory not found: {path}")
                return
                
        # Handle other built-in commands
        if command.strip() == 'pwd':
            yield ('stdout', self.get_cwd())
            return
            
        # Create process
        try:
            # Create output queue
            output_queue = queue.Queue()
            
            # Start process
            with self.process_lock:
                process_id = self.next_process_id
                self.next_process_id += 1
                
                # Set up process
                if sys.platform == 'win32':
                    # Windows - use shell=True for better command support
                    process = subprocess.Popen(
                        command,
                        shell=True,
                        cwd=str(self.current_dir),
                        env=self.environment,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        stdin=subprocess.PIPE,
                        text=True,
                        bufsize=1,
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                    )
                else:
                    # Unix - use shell=True for better command support
                    process = subprocess.Popen(
                        command,
                        shell=True,
                        cwd=str(self.current_dir),
                        env=self.environment,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        stdin=subprocess.PIPE,
                        text=True,
                        bufsize=1,
                        preexec_fn=os.setsid
                    )
                
                # Store process
                self.processes[process_id] = {
                    'process': process,
                    'command': command,
                    'output_queue': output_queue,
                    'stdout_thread': None,
                    'stderr_thread': None,
                }
                
                # Set as active process
                self.active_process = process
                self.active_process_queue = output_queue
                
            # Start output threads
            stdout_thread = threading.Thread(
                target=self._read_output,
                args=(process.stdout, output_queue, 'stdout'),
                daemon=True
            )
            stderr_thread = threading.Thread(
                target=self._read_output,
                args=(process.stderr, output_queue, 'stderr'),
                daemon=True
            )
            
            stdout_thread.start()
            stderr_thread.start()
            
            # Store threads
            with self.process_lock:
                self.processes[process_id]['stdout_thread'] = stdout_thread
                self.processes[process_id]['stderr_thread'] = stderr_thread
            
            # Yield output
            while True:
                try:
                    output_type, line = output_queue.get(timeout=0.1)
                    if output_type == 'exit':
                        break
                    yield (output_type, line)
                except queue.Empty:
                    # Check if process is still running
                    if process.poll() is not None:
                        # Process has exited
                        break
            
            # Wait for process to complete
            process.wait()
            
            # Get exit code
            exit_code = process.returncode
            if exit_code != 0:
                yield ('stderr', f"Command exited with code {exit_code}")
                
            # Clean up
            with self.process_lock:
                if process_id in self.processes:
                    del self.processes[process_id]
                    
            # Reset active process
            self.active_process = None
            self.active_process_queue = None
            
        except Exception as e:
            yield ('stderr', f"Error executing command: {e}")
    
    def _read_output(self, pipe, output_queue, output_type):
        """Read output from process pipe and put in queue.
        
        Args:
            pipe: Process pipe to read from
            output_queue: Queue to put output in
            output_type: Type of output ('stdout' or 'stderr')
        """
        try:
            for line in iter(pipe.readline, ''):
                if line:
                    output_queue.put((output_type, line.rstrip()))
            pipe.close()
        except (ValueError, IOError):
            pass
        finally:
            output_queue.put(('exit', ''))
    
    def send_input(self, input_str: str):
        """Send input to active process.
        
        Args:
            input_str: Input string to send
        """
        if self.active_process and self.active_process.poll() is None:
            try:
                self.active_process.stdin.write(input_str)
                self.active_process.stdin.flush()
            except (IOError, BrokenPipeError):
                pass
    
    def interrupt_command(self):
        """Interrupt active command."""
        if self.active_process and self.active_process.poll() is None:
            try:
                if sys.platform == 'win32':
                    # Windows - send Ctrl+C signal
                    self.active_process.send_signal(signal.CTRL_C_EVENT)
                else:
                    # Unix - send SIGINT
                    os.killpg(os.getpgid(self.active_process.pid), signal.SIGINT)
            except (ProcessLookupError, OSError):
                pass
    
    def complete_command(self, prefix: str) -> List[str]:
        """Complete command based on prefix.
        
        Args:
            prefix: Command prefix to complete
            
        Returns:
            List[str]: List of possible completions
        """
        completions = []
        
        # Check PATH for executables
        for path_dir in self.environment.get('PATH', '').split(os.pathsep):
            if not path_dir:
                continue
                
            path_dir = Path(path_dir)
            if not path_dir.exists() or not path_dir.is_dir():
                continue
                
            for item in path_dir.iterdir():
                if not item.is_file():
                    continue
                    
                # Check if executable
                if sys.platform == 'win32':
                    # Windows - check extensions
                    if item.suffix.lower() in ('.exe', '.bat', '.cmd', '.ps1') and item.name.lower().startswith(prefix.lower()):
                        completions.append(item.name)
                else:
                    # Unix - check if executable
                    if os.access(item, os.X_OK) and item.name.startswith(prefix):
                        completions.append(item.name)
        
        # Add built-in commands
        builtins = ['cd', 'pwd', 'exit', 'clear', 'cls', 'help']
        for cmd in builtins:
            if cmd.startswith(prefix):
                completions.append(cmd)
                
        return sorted(completions)
    
    def complete_path(self, prefix: str) -> List[str]:
        """Complete path based on prefix.
        
        Args:
            prefix: Path prefix to complete
            
        Returns:
            List[str]: List of possible completions
        """
        completions = []
        
        # Expand ~ to home directory
        if prefix.startswith('~'):
            prefix = str(Path.home()) + prefix[1:]
            
        # Get directory and prefix
        if os.path.isdir(prefix):
            directory = prefix
            file_prefix = ''
        else:
            directory = os.path.dirname(prefix) or '.'
            file_prefix = os.path.basename(prefix)
            
        # Resolve relative paths
        if not os.path.isabs(directory):
            directory = os.path.join(self.get_cwd(), directory)
            
        try:
            # List directory contents
            for item in os.listdir(directory):
                if item.startswith(file_prefix):
                    path = os.path.join(directory, item)
                    if os.path.isdir(path):
                        completions.append(item + '/')
                    else:
                        completions.append(item)
        except (FileNotFoundError, PermissionError):
            pass
            
        return sorted(completions)
    
    def get_running_processes(self) -> List[Dict[str, Any]]:
        """Get list of running processes.
        
        Returns:
            List[Dict[str, Any]]: List of process information dictionaries
        """
        with self.process_lock:
            return [
                {
                    'id': pid,
                    'command': info['command'],
                    'running': info['process'].poll() is None
                }
                for pid, info in self.processes.items()
            ]
    
    def cleanup(self):
        """Clean up resources."""
        # Terminate all processes
        with self.process_lock:
            for process_id, info in list(self.processes.items()):
                process = info['process']
                if process.poll() is None:
                    try:
                        if sys.platform == 'win32':
                            process.terminate()
                        else:
                            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    except (ProcessLookupError, OSError):
                        pass
                        
                # Wait for process to terminate
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    # Force kill if not terminated
                    try:
                        if sys.platform == 'win32':
                            process.kill()
                        else:
                            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                    except (ProcessLookupError, OSError):
                        pass