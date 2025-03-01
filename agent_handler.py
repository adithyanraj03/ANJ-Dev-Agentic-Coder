import json
import re
import logging
import os
import subprocess
import webbrowser
import glob
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

class AgentHandler:
    """
    Agent handler for autonomous coding capabilities.
    Provides functionality to create, edit, read files and run commands.
    Also includes codebase exploration and context-awareness capabilities.
    """
    
    def __init__(self, llm_handler, project_path):
        """Initialize the agent handler with an LLM handler."""
        self.llm = llm_handler
        self.project_path = Path(project_path) if project_path else Path.cwd()
        self.history = []
        self.context = {}  # Stores relevant context about the codebase
        self.memory = {}  # Stores long-term memory for the agent
        
        # Initialize display mode
        self.using_log_window = False
        self.force_log_mode = os.environ.get('FORCE_LOG_MODE', '').lower() == 'true'
        
        # Only use log window if explicitly forced
        if self.force_log_mode:
            try:
                from log_window import log_queue
                self.using_log_window = True
            except ImportError:
                pass
        
        # Initialize planner with proper display settings
        from agent_planner import AgentPlanner
        self.planner = AgentPlanner(self)
        
        # Ensure planner has consistent display mode
        if hasattr(self.planner, 'using_log_window'):
            self.planner.using_log_window = self.using_log_window
            
        # Initialize memory directory
        self._initialize_memory()
    
    def _initialize_memory(self):
        """Initialize memory directory for context persistence."""
        memory_dir = self.project_path / '.memory'
        memory_dir.mkdir(exist_ok=True)
        
        # Load existing memory if available
        memory_file = memory_dir / 'agent_memory.json'
        if memory_file.exists():
            try:
                with open(memory_file, 'r', encoding='utf-8') as f:
                    self.memory = json.load(f)
            except json.JSONDecodeError:
                self.memory = {"files": {}, "project_structure": {}, "dependencies": []}
        else:
            self.memory = {"files": {}, "project_structure": {}, "dependencies": []}
    
    def _save_memory(self):
        """Save agent memory to disk."""
        memory_dir = self.project_path / '.memory'
        memory_file = memory_dir / 'agent_memory.json'
        try:
            with open(memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.memory, f, indent=2)
        except Exception as e:
            logging.error(f"Failed to save agent memory: {e}")
    
    def explore_codebase(self, query: str = None) -> Dict[str, Any]:
        """
        Explore the codebase to understand its structure and relevant files.
        Uses query to focus exploration on relevant parts.
        """
        logging.info("Exploring codebase...")
        result = {"files": [], "structure": {}, "relevant_context": {}}
        
        # Search for project configuration files
        config_files = self._find_files(["*.json", "*.toml", "*.yaml", "*.yml", "requirements.txt", "package.json"])
        for file in config_files:
            if self._should_include_file(file):
                content = self._read_file_content(file)
                if content:
                    rel_path = os.path.relpath(file, self.project_path)
                    result["files"].append(rel_path)
                    result["relevant_context"][rel_path] = content
        
        # If query is provided, search for relevant files based on query
        if query:
            keywords = self._extract_keywords(query)
            relevant_files = []
            
            # Search Python files for relevant keywords
            for keyword in keywords:
                found_files = self._grep_codebase(keyword)
                relevant_files.extend(found_files)
            
            # Remove duplicates and limit to most relevant files
            relevant_files = list(set(relevant_files))[:15]  # Limit to 15 most relevant files
            
            # Read content of relevant files
            for file in relevant_files:
                if self._should_include_file(file):
                    content = self._read_file_content(file)
                    if content:
                        rel_path = os.path.relpath(file, self.project_path)
                        result["files"].append(rel_path)
                        result["relevant_context"][rel_path] = content
        
        # Get overall project structure (directories and files count)
        project_structure = self._get_project_structure()
        result["structure"] = project_structure
        
        # Update agent memory with new context
        self.memory["project_structure"] = project_structure
        for file_path, content in result["relevant_context"].items():
            self.memory["files"][file_path] = {"last_content": content, "last_updated": os.path.getmtime(os.path.join(self.project_path, file_path))}
        
        self._save_memory()
        return result
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract important keywords from a query."""
        # Remove common stop words
        stop_words = ['a', 'an', 'the', 'in', 'on', 'at', 'to', 'for', 'with', 'by', 'about', 'like', 'that', 'this']
        words = query.lower().split()
        keywords = [word for word in words if word not in stop_words and len(word) > 3]
        
        # Try to extract code-related specific terms
        code_patterns = [
            r'\b[A-Za-z]+\.[A-Za-z]+\b',  # Method calls like file.open
            r'\b[A-Za-z_]+\([^\)]*\)',    # Function calls
            r'import\s+[A-Za-z_]+',       # Import statements
            r'from\s+[A-Za-z_\.]+',       # From import statements
            r'class\s+[A-Za-z_]+',        # Class definitions
            r'def\s+[A-Za-z_]+'           # Function definitions
        ]
        
        for pattern in code_patterns:
            matches = re.findall(pattern, query)
            keywords.extend(matches)
        
        return list(set(keywords))
    
    def _find_files(self, patterns: List[str]) -> List[str]:
        """Find files matching the given patterns."""
        found_files = []
        for pattern in patterns:
            pattern_path = os.path.join(self.project_path, "**", pattern)
            found_files.extend(glob.glob(pattern_path, recursive=True))
        return found_files
    
    def _grep_codebase(self, pattern: str) -> List[str]:
        """Search codebase for files containing the pattern."""
        result = []
        extensions = ['.py', '.js', '.jsx', '.ts', '.tsx', '.html', '.css', '.json']
        
        for ext in extensions:
            for root, _, files in os.walk(self.project_path):
                for file in files:
                    if file.endswith(ext):
                        file_path = os.path.join(root, file)
                        if self._file_contains(file_path, pattern):
                            result.append(file_path)
        
        return result
    
    def _file_contains(self, file_path: str, pattern: str) -> bool:
        """Check if file contains the specified pattern."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                return pattern.lower() in content.lower()
        except Exception:
            return False
    
    def _read_file_content(self, file_path: str) -> Optional[str]:
        """Read content of a file safely."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            logging.warning(f"Failed to read {file_path}: {e}")
            return None
    
    def _should_include_file(self, file_path: str) -> bool:
        """Determine if file should be included in context."""
        # Skip common non-relevant files
        exclusions = [
            '__pycache__', 
            '.git', 
            '.github',
            '.vscode',
            'node_modules',
            'venv',
            '.env',
            'build',
            'dist',
            '.idea'
        ]
        
        # Skip files that are too large (>1MB)
        try:
            if os.path.getsize(file_path) > 1024 * 1024:
                return False
        except OSError:
            return False
            
        for exclusion in exclusions:
            if exclusion in file_path:
                return False
                
        return True
    
    def _get_project_structure(self) -> Dict[str, Any]:
        """Get overall structure of the project."""
        structure = {}
        
        for root, dirs, files in os.walk(self.project_path):
            # Skip hidden directories and excluded paths
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules', 'venv']]
            
            rel_path = os.path.relpath(root, self.project_path)
            if rel_path == ".":
                rel_path = "root"
                
            file_types = {}
            for file in files:
                ext = os.path.splitext(file)[1]
                if ext:
                    file_types[ext] = file_types.get(ext, 0) + 1
                    
            structure[rel_path] = {
                "file_count": len(files),
                "file_types": file_types
            }
            
        return structure
    
    def execute_request(self, request: str, stdscr=None) -> List[Dict[str, Any]]:
        """
        Execute a user request and return the actions performed.
        This is the main entry point for the agent functionality.
        """
        # First, explore codebase to gather context for informed decisions
        if any(keyword in request.lower() for keyword in ['create', 'modify', 'update', 'implement', 'write', 'code', 'fix']):
            # Only explore for code-related requests
            self.explore_codebase(request)
        
        # Check if this is a code modification request that should use the planner
        if any(keyword in request.lower() for keyword in ['create', 'modify', 'update', 'implement', 'write', 'code']):
            try:
                # Update planner's screen if needed
                if self.planner:
                    self.planner.set_screen(None if self.using_log_window else stdscr)
                
                # Execute plan
                result = self.planner.execute_plan_with_preview(request)
                
                # Convert planner result to agent result format
                if result["success"]:
                    results = [{
                        "type": "code_update",
                        "success": True,
                        "message": result["message"],
                        "files": result["files_changed"]
                    }]
                    
                    # Add a run action if there's a main Python file
                    py_files = [f for f in result["files_changed"] if f.endswith('.py')]
                    if py_files:
                        main_file = min(py_files, key=len)  # Choose shortest name as likely main file
                        results.append({
                            "type": "run_command",
                            "success": True,
                            "message": f"Would you like to run {main_file.split('/')[-1]}?",
                            "command": f"python {main_file}"
                        })
                    
                    return results
                else:
                    return [{
                        "type": "code_update",
                        "success": False,
                        "message": result["message"]
                    }]
                    
            except ImportError:
                # Fall back to standard approach if planner not available
                pass
                
            except Exception as e:
                logging.error(f"Error in planner execution: {e}")
                return [{
                    "type": "code_update",
                    "success": False,
                    "message": f"Error: {str(e)}"
                }]
        
        # Create LLM prompt with enhanced context
        prompt = self._create_agent_prompt(request)
        
        # Get response from LLM
        response = self.llm.execute_query(prompt, stdscr)
        
        if not response:
            logging.error("No response from LLM for agent request")
            return [{"type": "error", "success": False, "message": "No response from AI model"}]
            
        # Parse the response to extract actions
        actions = self._parse_actions(response)
        
        if not actions:
            logging.warning("No actions extracted from response")
            # Return a default action with the response content
            return [{
                "type": "info",
                "success": True,
                "message": "AI provided information but no specific actions",
                "content": response
            }]
        
        # Execute the actions
        results = []
        for action in actions:
            result = self._execute_action(action, stdscr)
            results.append(result)
            
        # Log the request and results in history
        self.history.append({
            "request": request,
            "response": response,
            "actions": actions,
            "results": results
        })
        
        return results
    
    def _create_agent_prompt(self, request: str) -> str:
        """Create a prompt for the agent with enhanced context."""
        # Start with base prompt
        prompt = f"""
        You are an autonomous AI coding assistant who can help create, modify, and analyze code.
        You have permission to explore the codebase, analyze files, and make changes with the user's approval.
        
        The user has requested: "{request}"
        
        Here is some information about the project structure:
        """
        
        # Add project structure information if available
        if "project_structure" in self.memory and self.memory["project_structure"]:
            structure_info = "\nProject structure summary:\n"
            for directory, info in self.memory["project_structure"].items():
                file_info = ""
                if "file_types" in info and info["file_types"]:
                    file_types = [f"{count} {ext} files" for ext, count in info["file_types"].items()]
                    file_info = ", ".join(file_types)
                
                structure_info += f"- {directory}: {info.get('file_count', 0)} files ({file_info})\n"
            
            prompt += structure_info
        
        # Add relevant files based on the request
        if "files" in self.memory:
            relevant_files = []
            keywords = self._extract_keywords(request)
            
            for file_path in self.memory["files"]:
                # Check if file is relevant to the current request
                is_relevant = any(keyword.lower() in file_path.lower() for keyword in keywords)
                if is_relevant:
                    relevant_files.append(file_path)
            
            # Limit to 5 most relevant files to avoid too long context
            if relevant_files:
                prompt += "\nHere are some relevant files that might be helpful:\n"
                for file_path in relevant_files[:5]:
                    prompt += f"- {file_path}\n"
        
        # Add action instructions
        prompt += """
        Please respond with a JSON object containing a list of actions to take.
        Each action should have a 'type' field and appropriate parameters.
        
        Valid action types:
        - create_file: Creates a new file (params: path, content)
        - read_file: Reads an existing file (params: path)
        - edit_file: Modifies an existing file (params: path, changes or content)
        - run_command: Runs a shell command (params: command)
        - browse_url: Opens a URL in browser (params: url)
        - search_web: Searches the web for information (params: query)
        - analyze_code: Analyzes code for improvements (params: path)
        
        First determine what files you need to read to understand the codebase better.
        Then decide what changes to make based on the user's request.
        Finally, propose any commands that should be run to test your changes.
        
        Example response format:
        {
            "actions": [
                {
                    "type": "read_file",
                    "path": "some_file.py"
                },
                {
                    "type": "create_file",
                    "path": "new_file.py",
                    "content": "print('Hello, world!')"
                },
                {
                    "type": "run_command",
                    "command": "python new_file.py"
                }
            ]
        }
        """
        
        return prompt
        
    def process_request(self, request: str, stdscr=None) -> Dict[str, Any]:
        """Process a user request and return results."""
        results = self.execute_request(request, stdscr)
        return {
            "success": True,
            "actions_performed": len(results),
            "results": results
        }
        
    def _parse_actions(self, response: str) -> List[Dict[str, Any]]:
        """Parse actions from the LLM response."""
        actions = []
        
        # Try to parse as JSON
        try:
            # Try direct parsing
            data = json.loads(response)
            if "actions" in data and isinstance(data["actions"], list):
                return data["actions"]
        except json.JSONDecodeError:
            # If direct parsing fails, try to extract JSON from the response
            json_match = re.search(r'```json\n(.*?)\n```', response, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group(1))
                    if "actions" in data and isinstance(data["actions"], list):
                        return data["actions"]
                except json.JSONDecodeError:
                    pass
                    
            # Try to find any JSON object in the response
            json_pattern = r'({[\s\S]*?})'
            matches = re.findall(json_pattern, response)
            for match in matches:
                try:
                    data = json.loads(match)
                    if "actions" in data and isinstance(data["actions"], list):
                        return data["actions"]
                    elif "type" in data and data.get("type") in ["create_file", "read_file", "edit_file", "run_command"]:
                        return [data]
                except json.JSONDecodeError:
                    continue
        
        # If no structured actions found, try to infer actions from the text
        if "create" in response.lower() and "file" in response.lower():
            # Look for code blocks
            code_blocks = re.findall(r'```(?:\w+)?\s*([\s\S]*?)```', response)
            if code_blocks:
                # Look for filenames
                filename_match = re.search(r'(?:create|write|save).*?(?:file|code).*?[\'"`]([^\'"`]+)[\'"`]', response, re.IGNORECASE)
                filename = "generated_code.py"
                if filename_match:
                    filename = filename_match.group(1)
                
                # Add action to create file
                actions.append({
                    "type": "create_file",
                    "path": filename,
                    "content": code_blocks[0]
                })
        
        return actions
    
    def _create_file(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new file with the given content."""
        path = action.get("path")
        content = action.get("content", "")
        
        # Ensure path is relative to project directory
        file_path = self.project_path / path
        
        try:
            # Create parent directories if they don't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write content to file
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
                
            # Update memory with new file
            rel_path = os.path.relpath(file_path, self.project_path)
            self.memory["files"][rel_path] = {
                "last_content": content,
                "last_updated": os.path.getmtime(file_path)
            }
            self._save_memory()
                
            return {
                "success": True,
                "action": "create_file",
                "path": str(file_path),
                "message": f"File created: {path}"
            }
        except Exception as e:
            return {
                "success": False,
                "action": "create_file",
                "error": str(e)
            }
    
    def _read_file(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Read the content of a file."""
        path = action.get("path")
        file_path = self.project_path / path
        
        try:
            if not file_path.exists():
                return {
                    "success": False,
                    "action": "read_file",
                    "error": f"File not found: {path}"
                }
                
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Update memory with file content
            rel_path = os.path.relpath(file_path, self.project_path)
            self.memory["files"][rel_path] = {
                "last_content": content,
                "last_updated": os.path.getmtime(file_path)
            }
            self._save_memory()
                
            return {
                "success": True,
                "action": "read_file",
                "path": str(file_path),
                "content": content
            }
        except Exception as e:
            return {
                "success": False,
                "action": "read_file",
                "error": str(e)
            }
    
    def _edit_file(self, action: Dict[str, Any], stdscr=None) -> Dict[str, Any]:
        """Edit an existing file with changes."""
        path = action.get("path")
        content = action.get("content")
        changes = action.get("changes")
        file_path = self.project_path / path
        
        try:
            if not file_path.exists():
                return {
                    "success": False,
                    "action": "edit_file",
                    "error": f"File not found: {path}"
                }
            
            # Read current content
            with open(file_path, "r", encoding="utf-8") as f:
                current_content = f.read()
            
            # Apply changes
            if content is not None:
                new_content = content
            elif changes is not None:
                # Let LLM apply changes
                edit_prompt = f"""
                Current content of {path}:
                ```
                {current_content}
                ```
                Apply these changes:
                {changes}
                Return ONLY the complete updated file content.
                """
                new_content = self.llm.execute_query(edit_prompt, stdscr)
                code_match = re.search(r'```(?:\w+)?\s*([\s\S]*?)```', new_content)
                if code_match:
                    new_content = code_match.group(1)
            else:
                return {
                    "success": False,
                    "action": "edit_file",
                    "error": "No content or changes provided"
                }
            
            # Write new content
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
                
            # Update memory with new content
            rel_path = os.path.relpath(file_path, self.project_path)
            self.memory["files"][rel_path] = {
                "last_content": new_content,
                "last_updated": os.path.getmtime(file_path)
            }
            self._save_memory()
                
            return {
                "success": True,
                "action": "edit_file",
                "path": str(file_path),
                "message": f"File edited: {path}"
            }
        except Exception as e:
            return {
                "success": False,
                "action": "edit_file",
                "error": str(e)
            }
    
    def _run_command(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Run a shell command."""
        command = action.get("command")
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(self.project_path),
                capture_output=True,
                text=True
            )
            
            return {
                "success": result.returncode == 0,
                "action": "run_command",
                "command": command,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        except Exception as e:
            return {
                "success": False,
                "action": "run_command",
                "command": command,
                "error": str(e)
            }
    
    def _browse_url(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Open URL in browser."""
        url = action.get("url", "")
        
        if not url:
            return {
                "success": False,
                "action": "browse_url",
                "message": "No URL provided"
            }
            
        try:
            if not (url.startswith("http://") or url.startswith("https://")):
                url = "https://" + url
            webbrowser.open(url)
            return {
                "success": True,
                "action": "browse_url",
                "url": url,
                "message": f"Opened URL: {url}"
            }
        except Exception as e:
            return {
                "success": False,
                "action": "browse_url",
                "error": str(e)
            }
    
    def _search_web(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Web search."""
        query = action.get("query", "")
        
        if not query:
            return {
                "success": False,
                "action": "search_web",
                "message": "No search query provided"
            }
            
        try:
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            webbrowser.open(search_url)
            return {
                "success": True,
                "action": "search_web",
                "query": query,
                "message": f"Searched for: {query}"
            }
        except Exception as e:
            return {
                "success": False,
                "action": "search_web",
                "error": str(e)
            }
    
    def _analyze_code(self, action: Dict[str, Any], stdscr=None) -> Dict[str, Any]:
        """Analyze code using LLM."""
        path = action.get("path")
        file_path = self.project_path / path
        
        try:
            if not file_path.exists():
                return {
                    "success": False,
                    "action": "analyze_code",
                    "message": f"File not found: {path}"
                }
                
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            analysis_prompt = f"""
            Analyze this code for improvements:
            ```
            {content}
            ```
            Focus on:
            1. Potential bugs
            2. Performance issues 
            3. Code organization
            4. Best practices
            5. Security concerns
            
            Provide specific recommendations.
            """
            
            analysis = self.llm.execute_query(analysis_prompt, stdscr)
            
            return {
                "success": True,
                "action": "analyze_code",
                "path": str(file_path),
                "message": f"Code analysis for {path}",
                "analysis": analysis
            }
        except Exception as e:
            return {
                "success": False,
                "action": "analyze_code",
                "error": str(e)
            }

    def _list_directory(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """List files in a directory."""
        from agent_utils import get_directory_structure, log_detailed
        
        path = action.get("path", ".")
        max_depth = action.get("max_depth", 2)
        
        # Ensure path is relative to project directory
        dir_path = self.project_path / path
        
        try:
            if not dir_path.exists() or not dir_path.is_dir():
                return {
                    "success": False,
                    "action": "list_directory",
                    "error": f"Directory not found: {path}"
                }
                
            structure = get_directory_structure(str(dir_path), max_depth)
            log_detailed(f"Listed directory structure for {path}", "DEBUG")
                
            return {
                "success": True,
                "action": "list_directory",
                "path": str(dir_path),
                "structure": structure,
                "message": f"Listed directory: {path}"
            }
        except Exception as e:
            logging.error(f"Error listing directory {path}: {e}")
            return {
                "success": False,
                "action": "list_directory",
                "error": str(e)
            }
    def _find_files_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Find files matching a pattern."""
        from agent_utils import find_files, log_detailed
        
        pattern = action.get("pattern", "*")
        path = action.get("path", ".")
        
        # Ensure path is relative to project directory
        base_path = self.project_path / path
        
        try:
            if not base_path.exists() or not base_path.is_dir():
                return {
                    "success": False,
                    "action": "find_files",
                    "error": f"Directory not found: {path}"
                }
                
            files = find_files(str(base_path), pattern)
            
            # Make paths relative to the project
            rel_files = [os.path.relpath(f, str(self.project_path)) for f in files]
            log_detailed(f"Found {len(files)} files matching pattern {pattern}", "DEBUG", {"count": len(files), "pattern": pattern})
                
            return {
                "success": True,
                "action": "find_files",
                "path": str(base_path),
                "pattern": pattern,
                "files": rel_files,
                "message": f"Found {len(files)} files matching '{pattern}' in {path}"
            }
        except Exception as e:
            logging.error(f"Error finding files with pattern {pattern}: {e}")
            return {
                "success": False,
                "action": "find_files",
                "error": str(e)
            }
    def _search_code_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Search for a pattern in code files."""
        from agent_utils import search_code, log_detailed
        
        pattern = action.get("pattern", "")
        path = action.get("path", ".")
        
        if not pattern:
            return {
                "success": False,
                "action": "search_code",
                "error": "No search pattern provided"
            }
            
        # Ensure path is relative to project directory
        base_path = self.project_path / path
        
        try:
            if not base_path.exists() or not base_path.is_dir():
                return {
                    "success": False,
                    "action": "search_code",
                    "error": f"Directory not found: {path}"
                }
                
            results = search_code(str(base_path), pattern)
            log_detailed(f"Searched code for pattern '{pattern}'", "DEBUG", {"matches_in_files": len(results)})
                
            return {
                "success": True,
                "action": "search_code",
                "path": str(base_path),
                "pattern": pattern,
                "results": results,
                "message": f"Found matches in {len(results)} files for pattern '{pattern}'"
            }
        except Exception as e:
            logging.error(f"Error searching code for pattern {pattern}: {e}")
            return {
                "success": False,
                "action": "search_code",
                "error": str(e)
            }
    def _explore_codebase_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Explore the codebase to build context."""
        query = action.get("query", "")
        
        try:
            # Use the existing explore_codebase method
            result = self.explore_codebase(query)
            
            # Format the response for LLM consumption
            return {
                "success": True,
                "action": "explore_codebase",
                "query": query,
                "files_found": len(result.get("files", [])),
                "structure": result.get("structure", {}),
                "message": f"Explored codebase with {len(result.get('files', []))} relevant files"
            }
        except Exception as e:
            logging.error(f"Error exploring codebase: {e}")
            return {
                "success": False,
                "action": "explore_codebase",
                "error": str(e)
            }
    def _execute_action(self, action: Dict[str, Any], stdscr=None) -> Dict[str, Any]:
        """Execute a single action and return the result."""
        action_type = action.get("type")
        
        # Import logging functions if available
        try:
            from agent_utils import log_action_start, log_action_end, log_detailed
            log_action_start(f"Execute action: {action_type}")
            log_detailed(f"Action details: {json.dumps(action, indent=2)}", "DEBUG")
        except ImportError:
            pass
        
        result = None
        try:
            if action_type == "create_file":
                result = self._create_file(action)
            elif action_type == "read_file":
                result = self._read_file(action)
            elif action_type == "edit_file":
                result = self._edit_file(action, stdscr)
            elif action_type == "run_command":
                result = self._run_command(action)
            elif action_type == "browse_url":
                result = self._browse_url(action)
            elif action_type == "search_web":
                result = self._search_web(action)
            elif action_type == "analyze_code":
                result = self._analyze_code(action, stdscr)
            elif action_type == "list_directory":
                result = self._list_directory(action)
            elif action_type == "find_files":
                result = self._find_files_action(action)
            elif action_type == "search_code":
                result = self._search_code_action(action)
            elif action_type == "explore_codebase":
                result = self._explore_codebase_action(action)
            else:
                result = {
                    "success": False,
                    "type": action_type,
                    "message": f"Unknown action type: {action_type}"
                }
                
            # Log detailed result information
            try:
                from agent_utils import log_detailed
                success = result.get("success", False) if result else False
                log_detailed(
                    f"Action result: {json.dumps(result, indent=2)}", 
                    "DEBUG" if success else "ERROR"
                )
                log_action_end(f"Execute action: {action_type}", success)
            except ImportError:
                pass
                
            return result
        except Exception as e:
            error_msg = f"Error executing action {action_type}: {e}"
            logging.error(error_msg)
            try:
                from agent_utils import log_action_end, log_detailed
                log_detailed(error_msg, "ERROR", {"error": str(e), "traceback": traceback.format_exc()})
                log_action_end(f"Execute action: {action_type}", False, {"error": str(e)})
            except ImportError:
                pass
                
            return {
                "success": False,
                "type": action_type or "unknown",
                "message": f"Error executing action: {e}"
            }

# Factory function
_agent_instance = None

def get_agent(llm_handler, project_path: Optional[str] = None):
    """Get the singleton agent instance."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = AgentHandler(llm_handler, project_path)
    return _agent_instance
