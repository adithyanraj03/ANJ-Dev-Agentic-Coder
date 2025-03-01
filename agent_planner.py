#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import difflib
import re
import json
import curses
import os
import time
import logging
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path

# Import the utility function for plan parsing
try:
    from agent_utils import parse_plan_response, sanitize_plan
except ImportError:
    # Define fallback versions if the import fails
    def parse_plan_response(response: str) -> Dict[str, Any]:
        """Fallback parser if agent_utils is not available."""
        try:
            return json.loads(response)
        except:
            return {"description": "", "files": {"create": [], "modify": []}, "steps": []}

    def sanitize_plan(plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback sanitizer if agent_utils is not available."""
        return plan_data

class AgentPlanner:
    """
    Handles the planning and preview steps for the autonomous coding agent.
    Provides a structured interface for showing planned changes and getting user approval.
    """
    
    def __init__(self, agent_handler, stdscr=None):
        """Initialize the agent planner with an agent handler."""
        # Initialize display mode first
        self.using_log_window = getattr(agent_handler, 'using_log_window', False)
        self.stdscr = None
        self.session_window = None
        
        # Set other properties
        self.agent = agent_handler
        self.llm = agent_handler.llm
        self.project_path = agent_handler.project_path

        # Check if we should use stdscr
        try:
            from log_window import log_queue
            self.using_log_window = True
            # Always None in log window mode
            self.stdscr = None
        except ImportError:
            # Set up curses mode if screen provided
            if stdscr is not None:
                self.set_screen(stdscr)
        
    def set_screen(self, stdscr):
        """Set the curses screen."""
        if getattr(self, 'using_log_window', False):
            self.stdscr = None  # Always None in log window mode
        else:
            self.stdscr = stdscr  # Use provided screen in curses mode
            # Initialize session window if using curses
            if self.stdscr:
                from editors.session_window import SessionWindow
                self.session_window = SessionWindow(self.stdscr)
    
    def create_plan(self, request: str) -> Dict[str, Any]:
        """Create a detailed plan based on the user request with codebase awareness."""
        if self.session_window:
            self.session_window.clear()
            self.session_window._draw_header("Planning")
            self.session_window.start_loading("Creating implementation plan...")
        elif self.using_log_window:
            logging.info("Creating implementation plan...")
        
        # First explore the codebase if agent has this capability
        project_context = ""
        relevant_files = []
        if hasattr(self.agent, 'explore_codebase'):
            try:
                exploration_results = self.agent.explore_codebase(request)
                
                # Build context from exploration
                if 'structure' in exploration_results and exploration_results['structure']:
                    project_context += "Project structure summary:\n"
                    for directory, info in exploration_results['structure'].items():
                        if directory != "root":  # Skip root directory to save space
                            continue
                        file_types = []
                        if 'file_types' in info and info['file_types']:
                            for ext, count in info['file_types'].items():
                                file_types.append(f"{count} {ext} files")
                        project_context += f"- Directory contains: {', '.join(file_types)}\n"
                
                # Add relevant files information
                if 'files' in exploration_results and exploration_results['files']:
                    project_context += "\nRelevant files that might be useful:\n"
                    # Limit to 10 most relevant files
                    for file_path in exploration_results['files'][:10]:
                        project_context += f"- {file_path}\n"
                        relevant_files.append(file_path)
                        
                # Add file contents for very relevant files (up to 5)
                if 'relevant_context' in exploration_results and exploration_results['relevant_context']:
                    project_context += "\nContents of key files:\n"
                    count = 0
                    for file_path, content in exploration_results['relevant_context'].items():
                        if count >= 3:  # Limit to 3 files to avoid context bloat
                            break
                        # Check if this file seems particularly relevant to the request
                        keywords = self._extract_keywords(request)
                        matches = sum(1 for kw in keywords if kw.lower() in content.lower())
                        if matches > 1:  # Only include if multiple keywords match
                            # Truncate content if too long
                            if len(content) > 500:
                                content = content[:500] + "\n... (truncated)"
                            project_context += f"\nFile: {file_path}\n```\n{content}\n```\n"
                            count += 1
                
            except Exception as e:
                logging.error(f"Error exploring codebase: {e}")
                # Continue without exploration context
        
        # Create a prompt for planning with enhanced context awareness
        prompt = f"""
        You are an AI coding assistant creating a detailed implementation plan.
        The user has requested: "{request}"
        
        {project_context}
        
        Create a structured plan with specific files to create or modify.
        Your plan should include:
        1. A brief description of what will be done
        2. Files to create (marked with "+")
        3. Files to modify (marked with "*")
        
        Based on the codebase exploration, try to:
        - Identify existing files that should be modified rather than creating new ones
        - Maintain consistent coding style with the rest of the project
        - Reuse existing patterns, functions, and classes when appropriate
        - Consider dependencies and imports that may be needed
        
        Respond with a JSON object containing:
        {{
            "description": "Brief description of implementation",
            "files": {{
                "create": ["file1.py", "file2.py"],
                "modify": ["existing.py"]
            }},
            "steps": [
                {{
                    "description": "Step 1: What will be done",
                    "file": "file1.py",
                    "action": "create",
                    "overview": "Brief description of changes"
                }},
                ...
            ]
        }}
        
        Every file mentioned in the steps must be included in either the create or modify lists.
        Make the plan concrete and specific to the request.
        """
        
        # Get response from LLM
        response = self.llm.execute_query(prompt, self.stdscr)
        
        # Parse the response
        plan_data = parse_plan_response(response)
        
        # Add any relevant existing files we found that might have been missed
        if hasattr(self.agent, 'memory') and 'files' in self.agent.memory:
            if 'files' not in plan_data:
                plan_data['files'] = {}
            if 'modify' not in plan_data['files']:
                plan_data['files']['modify'] = []
                
            existing_files_to_check = set(relevant_files) - set(plan_data['files'].get('modify', []))
            for file_path in existing_files_to_check:
                # Check if file exists and seems relevant but was missed
                if file_path in self.agent.memory['files'] and self._is_relevant_to_request(file_path, request):
                    # Suggest this file for modification
                    plan_data['files']['modify'].append(file_path)
        
        # Stop loading animation if using session window
        if self.session_window:
            self.session_window.stop_loading()
        
        return plan_data
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text for relevance checking."""
        # Simple keyword extraction - remove common words and keep significant terms
        common_words = {'a', 'an', 'the', 'and', 'or', 'but', 'is', 'are', 'was', 'were', 
                        'in', 'on', 'at', 'to', 'for', 'with', 'by', 'about', 'as',
                        'of', 'that', 'this', 'these', 'those', 'be', 'have', 'has', 'had',
                        'do', 'does', 'did', 'can', 'could', 'will', 'would', 'should'}
        
        words = re.findall(r'\b\w+\b', text.lower())
        keywords = [word for word in words if word not in common_words and len(word) > 3]
        
        # Add any code-related patterns
        code_patterns = [
            (r'\b[A-Za-z]+\.[A-Za-z]+\b', 'method'),  # Method calls like file.open
            (r'\b[A-Za-z_]+\([^\)]*\)', 'function'),   # Function calls
            (r'import\s+[A-Za-z_]+', 'import'),        # Import statements
            (r'from\s+[A-Za-z_\.]+', 'from'),          # From import statements
            (r'class\s+[A-Za-z_]+', 'class'),          # Class definitions
            (r'def\s+[A-Za-z_]+', 'function')          # Function definitions
        ]
        
        for pattern, kind in code_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                keywords.append(match)
        
        return list(set(keywords))
    
    def _is_relevant_to_request(self, file_path: str, request: str) -> bool:
        """Check if a file is relevant to the current request."""
        keywords = self._extract_keywords(request)
        
        # Check filename relevance
        basename = os.path.basename(file_path)
        filename_score = sum(1 for kw in keywords if kw.lower() in basename.lower())
        
        # If filename directly matches keywords, consider it relevant
        if filename_score >= 2:
            return True
            
        # Check file content if available in memory
        if hasattr(self.agent, 'memory') and 'files' in self.agent.memory and file_path in self.agent.memory['files']:
            file_info = self.agent.memory['files'][file_path]
            if 'last_content' in file_info:
                content = file_info['last_content']
                content_score = sum(1 for kw in keywords if kw.lower() in content.lower())
                if content_score >= 3:  # Higher threshold for content match
                    return True
        
        return False
    
    def display_plan(self, plan: Dict[str, Any]) -> bool:
        """Display the plan and ask for user confirmation."""
        if self.using_log_window:
            # Log mode - output plan details and auto-accept
            logging.info("[Step 1: Planning]")
            logging.info(f"Description: {plan.get('description', '')}")
            logging.info("Files to modify:")
            for file in plan.get('files', {}).get('create', []):
                logging.info(f"+ {file}")
            for file in plan.get('files', {}).get('modify', []):
                logging.info(f"* {file}")
            if plan.get('steps'):
                logging.info("Implementation steps:")
                for i, step in enumerate(plan.get('steps', [])):
                    step_desc = step.get('description', f'Step {i+1}')
                    file_info = f" ({step['file']})" if 'file' in step else ""
                    logging.info(f"{i+1}. {step_desc}{file_info}")
            return True  # Auto-accept in log window mode
        
        elif self.session_window:
            # Format plan description with steps
            desc = plan.get('description', 'Implementation plan') + "\n\n"
            if plan.get('steps'):
                desc += "Implementation steps:\n"
                for i, step in enumerate(plan.get('steps', [])):
                    step_desc = step.get('description', f'Step {i+1}')
                    file_info = f" ({step['file']})" if 'file' in step else ""
                    desc += f"{i+1}. {step_desc}{file_info}\n"
            
            # Show plan using session window
            result = self.session_window.show_plan(
                "Planning",
                desc,
                {
                    'create': plan.get('files', {}).get('create', []),
                    'modify': plan.get('files', {}).get('modify', [])
                }
            )
            return result is True
        
        else:
            # Console fallback
            print("\n[Step 1: Planning]")
            print(f"Description: {plan.get('description', '')}")
            print("Files to modify:")
            for file in plan.get('files', {}).get('create', []):
                print(f"+ {file}")
            for file in plan.get('files', {}).get('modify', []):
                print(f"* {file}")
            try:
                return input("Accept plan? [Y/n/e(dit)] ").lower() not in ('n', 'no')
            except (KeyboardInterrupt, EOFError):
                print("\nAssuming Yes...")
                return True
    
    def generate_and_preview(self, plan: Dict[str, Any], request: str) -> Dict[str, Any]:
        """Generate code based on plan and show previews for user confirmation."""
        results = {}
        
        for step_idx, step in enumerate(plan.get('steps', [])):
            if not step.get('file'):
                continue
            
            file_action = step.get('action', 'update')
            file_name = step.get('file')
            
            if self.session_window:
                self.session_window.start_loading(
                    f"Step {step_idx+1}: {'Creating' if file_action == 'create' else 'Modifying'} {file_name}"
                )
            elif self.using_log_window:
                logging.info(f"Step {step_idx+1}: {'Creating' if file_action == 'create' else 'Modifying'} {file_name}")
                if 'description' in step:
                    logging.info(f"Description: {step['description']}")
            
            # Generate code for this file
            prompt = self._build_file_prompt(step, request, plan)
            response = self.llm.execute_query(prompt, self.stdscr)
            code = self._extract_code_from_response(response)
            
            if self.session_window:
                self.session_window.stop_loading()
            
            # Read original file if it exists
            file_path = self.project_path / step.get('file')
            original_content = None
            if file_path.exists():
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        original_content = f.read()
                except:
                    pass
            
            # Show preview/diff and get confirmation
            accepted = False
            if self.session_window:
                if original_content:
                    accepted = self.session_window.show_diff(file_name, original_content, code)
                else:
                    accepted = self.session_window.show_preview(file_name, code, is_new=True)
            else:
                # Use fallback preview
                accepted = self._fallback_preview(file_name, code, original_content, file_action)
            
            if accepted:
                results[step.get('file')] = code
        
        return results
    
    def _build_file_prompt(self, step: Dict[str, Any], request: str, plan: Dict[str, Any]) -> str:
        """Build a prompt for file creation/modification with enhanced context awareness."""
        file_name = step.get('file', '')
        action = step.get('action', 'modify')
        description = step.get('description', '')
        
        # Check if file exists
        file_path = self.project_path / file_name
        existing_content = ""
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    existing_content = f.read()
            except:
                pass
        
        # Get additional context from other relevant files
        additional_context = ""
        
        # Check if agent has memory of files
        if hasattr(self.agent, 'memory') and 'files' in self.agent.memory:
            # Find related files based on naming or imports
            related_files = []
            base_name = os.path.splitext(os.path.basename(file_name))[0]
            
            for stored_file, file_info in self.agent.memory['files'].items():
                # Skip the current file
                if stored_file == file_name:
                    continue
                    
                # Check if this file might be related (by name or content)
                stored_base = os.path.splitext(os.path.basename(stored_file))[0]
                
                # Name-based relationship
                if base_name in stored_base or stored_base in base_name:
                    related_files.append(stored_file)
                    continue
                    
                # Or if it's imported/referenced in the content
                if 'last_content' in file_info and existing_content:
                    import_pattern = f"import.*{base_name}"
                    from_pattern = f"from.*{base_name}"
                    if (re.search(import_pattern, file_info['last_content'], re.IGNORECASE) or 
                        re.search(from_pattern, file_info['last_content'], re.IGNORECASE) or
                        base_name in file_info['last_content']):
                        related_files.append(stored_file)
            
            # Add context from up to 3 related files
            if related_files:
                additional_context += "\nHere are related files that may provide context:\n"
                for i, rel_file in enumerate(related_files[:3]):
                    rel_content = self.agent.memory['files'][rel_file].get('last_content', '')
                    if len(rel_content) > 300:  # Limit context to prevent overflow
                        rel_content = rel_content[:300] + "\n... (truncated)"
                    additional_context += f"\nFile: {rel_file}\n```\n{rel_content}\n```\n"
        
        # Determine file type hints
        file_ext = Path(file_name).suffix.lower()
        language_hint = ""
        
        if file_ext in ['.py', '.pyw']:
            language_hint = "Python code should follow PEP 8 style guidelines with proper docstrings."
        elif file_ext in ['.js', '.jsx']:
            language_hint = "JavaScript code should follow modern ES6+ syntax and best practices."
        elif file_ext in ['.ts', '.tsx']:
            language_hint = "TypeScript code should use strong typing and modern TypeScript features."
        elif file_ext in ['.html', '.htm']:
            language_hint = "HTML should be semantic and accessible."
        elif file_ext in ['.css']:
            language_hint = "CSS should be well-organized and maintainable."
        
        # Build prompt based on action
        if action == 'create' or not existing_content:
            return f"""
            Create a new file named '{file_name}' to implement the following:
            
            User request: {request}
            Description: {description}
            Plan overview: {plan.get('description', '')}
            {language_hint}
            
            {additional_context}
            
            Provide the complete code for this file. Be thorough and include all necessary
            functions, classes, imports, and documentation. The code should be production-ready.
            
            Return ONLY the code with no additional text or explanations.
            """
        else:
            return f"""
            Modify the file '{file_name}' according to the following:
            
            User request: {request}
            Description: {description}
            
            Current file content:
            ```
            {existing_content}
            ```
            
            {additional_context}
            
            {language_hint}
            
            Return the COMPLETE updated file content, not just the changes.
            The code should be production-ready with necessary imports, functions, and documentation.
            
            Return ONLY the code with no additional text or explanations.
            """
    
    def _extract_code_from_response(self, response: str) -> str:
        """Extract code content from LLM response."""
        # Look for markdown code blocks
        code_blocks = re.findall(r'```(?:\w+)?\s*([\s\S]*?)```', response)
        if code_blocks:
            return code_blocks[0].strip()
        
        # If no code blocks, try to clean up the response
        lines = response.split('\n')
        cleaned_lines = []
        skip_line = False
        
        for line in lines:
            # Skip explanations that might be in the response
            if re.match(r'^(Here\'s|This is|Below is|I\'ll|Let me|Now)', line.strip()):
                skip_line = True
                continue
            if skip_line and not line.strip():
                skip_line = False
                continue
            if skip_line:
                continue
            # Keep code lines
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines).strip()
    
    def _fallback_preview(self, file_name: str, new_content: str, original_content: Optional[str], action: str) -> bool:
        """Show file preview/diff in console mode."""
        print(f"\n[Step 2: {'Preview' if action == 'create' else 'Changes'}]")
        print(f"{file_name}:")
        
        if action == 'create' or not original_content:
            print("```python")
            print(new_content)
            print("```")
        else:
            # Show unified diff
            diff = list(difflib.unified_diff(
                original_content.splitlines(),
                new_content.splitlines(),
                fromfile='Original',
                tofile='Modified',
                lineterm=''
            ))
            for line in diff:
                print(line)
        
        try:
            return input("Accept changes? [Y/n/e(dit)] ").lower() not in ('n', 'no')
        except (KeyboardInterrupt, EOFError):
            print("\nAssuming Yes...")
            return True
    
    def execute_plan_with_preview(self, request: str) -> Dict[str, Any]:
        """Execute the full planning and preview workflow."""
        def stop_all_loading():
            # Ensure all loading animations are stopped
            if hasattr(self, 'session_window') and self.session_window:
                self.session_window.is_loading = False
                self.session_window.stop_loading()

        try:
            # Create and show plan with proper cleanup
            plan = None
            try:
                plan = self.create_plan(request)
            finally:
                stop_all_loading()

            if not plan:
                return {
                    "success": False,
                    "message": "Failed to create plan",
                    "files_changed": []
                }
            
            # Get plan approval
            if not self.display_plan(plan):
                return {
                    "success": False,
                    "message": "Plan rejected by user",
                    "files_changed": []
                }
            
            # Generate and preview changes
            file_changes = self.generate_and_preview(plan, request)
            
            # Apply approved changes
            applied_files = []
            for file_name, content in file_changes.items():
                file_path = self.project_path / file_name
                file_path.parent.mkdir(parents=True, exist_ok=True)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                applied_files.append(str(file_path))
                
                # Update agent memory if it exists
                if hasattr(self.agent, 'memory') and hasattr(self.agent, '_save_memory'):
                    rel_path = os.path.relpath(file_path, self.project_path)
                    self.agent.memory["files"][rel_path] = {
                        "last_content": content,
                        "last_updated": os.path.getmtime(file_path)
                    }
                    self.agent._save_memory()
            
            # Generate next steps suggestions
            next_steps = []
            
            # Web project steps
            if any(f.endswith(('.html', '.js', '.css', '.tsx', '.jsx')) for f in applied_files):
                if any(f.endswith('package.json') for f in applied_files):
                    next_steps.append({
                        "type": "run_command",
                        "command": "npm install",
                        "message": "Install npm dependencies"
                    })
                
                if any(f.endswith('index.html') for f in applied_files):
                    next_steps.append({
                        "type": "info",
                        "message": "Consider running a local server to view your web application"
                    })
            
            # Python project steps
            if any(f.endswith('.py') for f in applied_files):
                main_files = [f for f in applied_files if f.endswith(('main.py', 'app.py'))]
                if main_files:
                    next_steps.append({
                        "type": "run_command",
                        "command": f"python {os.path.basename(main_files[0])}",
                        "message": f"Run the main application file: {os.path.basename(main_files[0])}"
                    })
            
            return {
                "success": True,
                "message": f"Successfully applied changes to {len(applied_files)} files",
                "files_changed": applied_files,
                "plan": plan,
                "next_steps": next_steps
            }
            
        except Exception as e:
            error_msg = str(e)
            if self.session_window:
                self.session_window.show_error(error_msg)
            elif self.using_log_window:
                logging.error(f"Error in execute_plan_with_preview: {error_msg}")
            else:
                print(f"Error: {error_msg}")
            
            return {
                "success": False,
                "message": f"Error executing plan: {error_msg}",
                "files_changed": []
            }