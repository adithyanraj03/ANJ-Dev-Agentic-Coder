#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import json
import time
import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Iterator
from llm_handler import LLMHandler
from dependencies import DependencyManager
from queue_handler import log_queue
from dataclasses import dataclass

@dataclass
class CodePlan:
    """Represents a plan for code generation."""
    description: str
    steps: List[Dict[str, Any]]
    files_to_create: List[str]
    files_to_modify: List[str]
    dependencies: List[str]

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'CodePlan':
        """Create a CodePlan from a dictionary."""
        return CodePlan(
            description=data.get('description', ''),
            steps=data.get('steps', []),
            files_to_create=data.get('files_to_create', []),
            files_to_modify=data.get('files_to_modify', []),
            dependencies=data.get('dependencies', [])
        )

    @staticmethod
    def from_json(json_str: str) -> 'CodePlan':
        """Create a CodePlan from a JSON string."""
        try:
            return CodePlan.from_dict(json.loads(json_str))
        except json.JSONDecodeError:
            # Try to extract JSON from the response
            json_match = re.search(r'```json\n(.*?)\n```', json_str, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group(1))
                    return CodePlan.from_dict(data)
                except json.JSONDecodeError:
                    pass
            
            # Return default if JSON extraction fails
            return CodePlan(
                description="Unable to parse plan",
                steps=[],
                files_to_create=[],
                files_to_modify=[],
                dependencies=[]
            )

class CodeGenerator:
    """Handles code generation and organization."""
    
    def __init__(self, config: Dict[str, Any], ui=None, project_manager=None):
        """Initialize code generator."""
        self.config = config
        self.ui = ui
        self.project = project_manager
        self.llm = LLMHandler(config)
        self.dep_manager = DependencyManager()
        self.base_requirements = self.dep_manager.load_base_requirements()
        self.current_plan = None
        self._log("Code generator initialized", "INFO")

    def _log(self, message: str, level: str = 'INFO'):
        """Log message to both UI and log window."""
        if self.ui:
            if level == 'ERROR':
                self.ui.print_error(message)
            elif level == 'WARNING':
                self.ui.print_warning(message)
            elif level == 'SUCCESS':
                self.ui.print_success(message)
            else:
                self.ui.print_info(message)
        log_queue.put({"message": message, "level": level})

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from response text."""
        try:
            # Look for JSON between ```json and ``` markers
            start_marker = "```json"
            end_marker = "```"
            
            start_idx = text.find(start_marker)
            if start_idx != -1:
                start_idx += len(start_marker)
                end_idx = text.find(end_marker, start_idx)
                if (end_idx != -1):
                    json_str = text[start_idx:end_idx].strip()
                    self._log(f"Raw response:\n{json_str}", "DEBUG")
                    return json.loads(json_str)
                    
            # Try finding raw JSON
            start_idx = text.find('{')
            if start_idx != -1:
                end_idx = text.rfind('}') + 1
                if end_idx > start_idx:
                    json_str = text[start_idx:end_idx]
                    self._log(f"Raw response:\n{json_str}", "DEBUG")
                    return json.loads(json_str)
                    
        except json.JSONDecodeError as e:
            self._log(f"JSON parsing error: {e}", "ERROR")
            self._log(f"Response text:\n{text}", "DEBUG")
        except Exception as e:
            self._log(f"Error extracting JSON: {e}", "ERROR")
            
        return None

    def create_plan(self, query: str) -> Optional[CodePlan]:
        """Create a plan for code generation based on the query."""
        logging.info(f"Creating plan for query: {query}")
        
        prompt = self._create_plan_prompt(query)
        response = self.llm.execute_query(prompt)
        
        if not response:
            logging.error("Empty response from LLM")
            return None
        
        # Try to extract the plan using multiple methods
        try:
            # First, try to parse as JSON
            plan_data = self._extract_plan_data(response)
            
            if not plan_data:
                logging.error("Failed to extract JSON from response")
                return None
                
            description = plan_data.get('description', '')
            files_to_create = plan_data.get('files', {}).get('create', [])
            files_to_modify = plan_data.get('files', {}).get('modify', [])
            dependencies = plan_data.get('dependencies', [])
            steps = plan_data.get('steps', [])
            
            # Validate plan
            if not description or not steps:
                logging.error("Invalid plan: missing description or steps")
                return None
            
            plan = CodePlan(
                description=description,
                files_to_create=files_to_create,
                files_to_modify=files_to_modify,
                dependencies=dependencies,
                steps=steps
            )
            
            return plan
            
        except Exception as e:
            logging.error(f"Plan creation failed: {e}")
            return None

    def _extract_plan_data(self, response: str) -> Dict[str, Any]:
        """Extract plan data from the LLM response."""
        # Try to parse as JSON first
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # Try to extract just the JSON part
        json_match = re.search(r'```json\n(.*?)\n```', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try to extract with special handling for triple-quoted strings
        try:
            # Extract description
            desc_match = re.search(r'"description"\s*:\s*"([^"]+)"', response)
            description = desc_match.group(1) if desc_match else "Code generation plan"
            
            # Extract files to create
            files_create = []
            files_create_match = re.search(r'"create"\s*:\s*\[(.*?)\]', response, re.DOTALL)
            if files_create_match:
                files_create = re.findall(r'"([^"]+)"', files_create_match.group(1))
            
            # Extract files to modify
            files_modify = []
            files_modify_match = re.search(r'"modify"\s*:\s*\[(.*?)\]', response, re.DOTALL)
            if files_modify_match:
                files_modify = re.findall(r'"([^"]+)"', files_modify_match.group(1))
            
            # Extract dependencies
            dependencies = []
            dependencies_match = re.search(r'"dependencies"\s*:\s*\[(.*?)\]', response, re.DOTALL)
            if dependencies_match:
                dependencies = re.findall(r'"([^"]+)"', dependencies_match.group(1))
            
            # Extract steps
            steps = []
            steps_match = re.search(r'"steps"\s*:\s*\[(.*?)\]', response, re.DOTALL)
            if steps_match:
                steps_content = steps_match.group(1)
                step_objects = []
                
                # Find all step objects
                step_regex = r'{([^{}]*(?:{[^{}]*}[^{}]*)*?)}'
                for step_match in re.finditer(step_regex, steps_content):
                    step_text = step_match.group(1)
                    
                    # Extract step properties
                    desc_match = re.search(r'"description"\s*:\s*"([^"]+)"', step_text)
                    action_match = re.search(r'"action"\s*:\s*"([^"]+)"', step_text)
                    file_match = re.search(r'"file"\s*:\s*"([^"]+)"', step_text)
                    content_match = re.search(r'"content"\s*:\s*"""([\s\S]*?)"""', step_text)
                    
                    # Create step object
                    step = {}
                    if desc_match:
                        step['description'] = desc_match.group(1)
                    if action_match:
                        step['action'] = action_match.group(1)
                    if file_match:
                        step['file'] = file_match.group(1)
                    if content_match:
                        step['content'] = content_match.group(1)
                    
                    if step:
                        steps.append(step)
            
            return {
                'description': description,
                'files': {
                    'create': files_create,
                    'modify': files_modify
                },
                'dependencies': dependencies,
                'steps': steps
            }
            
        except Exception as e:
            logging.error(f"Error extracting plan data: {e}")
            return {}

    def _create_plan_prompt(self, query: str) -> str:
        """Create prompt for plan generation."""
        # Get project context if available
        context = ""
        if self.project:
            context = self.project.get_context_history()
            
        return (
            "Create a detailed implementation plan for the following code request. "
            "Break down the implementation into small, manageable steps.\n\n"
            f"Query: {query}\n\n"
            f"Project Context:\n{context}\n\n"
            "Respond with a JSON object containing:\n"
            "{\n"
            '  "description": "Brief description of the implementation plan",\n'
            '  "files": {\n'
            '    "create": ["list of files to create with .py extension"],\n'
            '    "modify": ["list of files to modify"]\n'
            "  },\n"
            '  "dependencies": ["list of required dependencies"],\n'
            '  "steps": [\n'
            "    {\n"
            '      "description": "step description",\n'
            '      "action": "create/modify/delete",\n'
            '      "file": "filename.py",\n'
            '      "content": "implementation details"\n'
            "    }\n"
            "  ],\n"
            '  "tests": ["list of tests to implement"]\n'
            "}\n\n"
            "For Python files, include proper file extensions (.py). "
            "Break down the implementation into small, focused files. "
            "Include clear docstrings and type hints."
        )

    def _create_step_prompt(self, step: Dict[str, Any]) -> str:
        """Create a prompt for a single step."""
        if step['action'] == 'create':
            return f"""
            You are helping to create code. Your task is to create a file named '{step['file']}' with the following description:
            
            {step['description']}
            
            Please generate the complete content for this file. Be thorough and include all necessary code.
            Return ONLY the code without any explanations.
            """
        else:  # modify
            current_content = self._project_manager.read_file(step['file'])
            return f"""
            You are helping to modify code. Your task is to modify the file '{step['file']}' according to the following description:
            
            {step['description']}
            
            Current content of the file:
            ```
            {current_content}
            ```
            
            Please provide the complete updated content for this file. Be thorough and include all necessary code.
            Return ONLY the updated code without any explanations.
            """
    
    def _format_code_output(self, response: str) -> str:
        """Format the code output from the LLM response."""
        # Try to extract code blocks
        code_blocks = re.findall(r'```(?:\w+)?\s*([\s\S]*?)```', response)
        if code_blocks:
            # Return the first code block
            return code_blocks[0]
        
        # If no code blocks found, strip any markdown/text formatting that might be present
        lines = response.split('\n')
        clean_lines = []
        for line in lines:
            # Skip common explanation lines from LLMs
            if line.startswith('#') and any(x in line.lower() for x in ['here', 'explanation', 'code', 'file']):
                continue
            if line.startswith('Here is') or line.startswith('This is') or line.startswith('Now let'):
                continue
            clean_lines.append(line)
        
        return '\n'.join(clean_lines)
    
    def generate_code_step(self, step: Dict[str, Any]) -> str:
        """Generate code for a single step with error handling."""
        try:
            prompt = self._create_step_prompt(step)
            raw_response = self.llm.execute_query(prompt)
            
            if not raw_response:
                logging.error(f"Empty response for step: {step['description']}")
                return ""
            
            formatted_code = self._format_code_output(raw_response)
            return formatted_code
        
        except Exception as e:
            logging.error(f"Error generating code for step: {e}")
            return ""
    
    def generate_code_step_stream(self, step: Dict[str, Any]) -> Iterator[str]:
        """Generate code for a single step with streaming output."""
        try:
            prompt = self._create_step_prompt(step)
            buffer = ""
            
            for chunk in self.llm.execute_query_stream(prompt):
                buffer += chunk
                yield chunk
                
            # Clean up the final result - not needed during streaming
            # but useful for the final buffer value
            return self._format_code_output(buffer)
            
        except Exception as e:
            logging.error(f"Error streaming code for step: {e}")
            return ""

    def generate_code(
        self,
        query: str,
        context: Optional[str] = None,
        subfolder: Optional[str] = None
    ) -> Tuple[Dict[str, str], List[str]]:
        """Generate code based on query."""
        if self.ui:
            self.ui.start_loading("Creating plan")
            
        try:
            # Stage 1: Create and display plan
            self._log(f"Starting code generation for: {query}")
            plan = self.create_plan(query)
            if not plan:
                raise ValueError("Failed to create plan")
                
            if self.ui:
                self.ui.show_plan(
                    plan.files_to_create,
                    plan.files_to_modify,
                    plan.description
                )
                
                if not self.ui.confirm("Proceed with this plan?"):
                    self._log("Plan rejected by user", "WARNING")
                    return {}, []
            
            # Stage 2: Execute plan with previews
            code_blocks = {}
            total_steps = len(plan.steps)
            for idx, step in enumerate(plan.steps, 1):
                step_msg = f"Step {idx}/{total_steps}: {step['description']}"
                self._log(step_msg)
                if self.ui:
                    self.ui.start_loading(step_msg)
                    
                # Generate code for this step
                response = self.llm.execute_query(
                    self._create_step_prompt(step, context)
                )
                
                if not response:
                    continue
                    
                # Extract code blocks
                blocks = self.llm._extract_code_blocks(response)
                
                # Preview and confirm each file
                for filename, content in blocks.items():
                    # Get original content if modifying
                    original_content = None
                    if step['action'] == 'modify' and self.project:
                        filepath = Path(self.project.current_project) / filename
                        if filepath.exists():
                            original_content = filepath.read_text()
                            
                    # Show preview
                    if self.ui:
                        self.ui.show_code_preview(filename, content, original_content)
                        choice = self.ui.confirm_changes(filename)
                        
                        if choice == 'reject':
                            self._log(f"Changes to {filename} rejected", "WARNING")
                            continue
                        elif choice == 'edit':
                            content = self.ui.edit_content(content)
                            # Show preview of edited content
                            self.ui.show_code_preview(filename, content, original_content)
                            if not self.ui.confirm(f"Save edited {filename}?"):
                                self._log(f"Changes to {filename} cancelled", "WARNING")
                                continue
                                
                    code_blocks[filename] = content
                    
                    # Update project status
                    if self.project:
                        self.project.update_file_status(
                            filename,
                            step['action'],
                            content
                        )
                        self._log(f"Generated {filename}", "SUCCESS")
                            
            # Extract dependencies
            all_dependencies = self.dep_manager.merge_requirements(
                self.base_requirements,
                plan.dependencies
            )
            
            self._log("Code generation completed", "SUCCESS")
            return code_blocks, all_dependencies
            
        except Exception as e:
            error_msg = f"Code generation failed: {e}"
            self._log(error_msg, "ERROR")
            raise
        finally:
            if self.ui:
                self.ui.stop_loading_animation()

    def save_code(
        self,
        code_blocks: Dict[str, str],
        base_path: Path,
        allow_overwrite: bool = False
    ) -> List[Path]:
        """Save generated code to files."""
        if self.ui:
            self.ui.start_loading("Saving code files")
            
        try:
            saved_files = []
            base_path.mkdir(parents=True, exist_ok=True)
            test_path = base_path / 'tests'
            test_path.mkdir(exist_ok=True)
            
            self._log(f"Saving files to {base_path}")
            
            for filename, content in code_blocks.items():
                # Determine file path
                if filename.startswith('test_'):
                    file_path = test_path / filename
                else:
                    file_path = base_path / filename
                    
                # Create backup if modifying
                if file_path.exists():
                    if self.project:
                        backup_path = self.project.create_backup(str(file_path))
                        if backup_path:
                            self._log(f"Created backup: {backup_path}", "INFO")
                    if not allow_overwrite:
                        if not self.ui or not self.ui.confirm(f"Overwrite {filename}?"):
                            self._log(f"Skipped {filename} (not overwritten)", "WARNING")
                            continue
                        
                # Save file
                file_path.parent.mkdir(parents=True, exist_ok=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                    
                saved_files.append(file_path)
                self._log(f"Saved: {file_path}", "SUCCESS")
                    
            return saved_files
            
        except Exception as e:
            error_msg = f"Failed to save code: {e}"
            self._log(error_msg, "ERROR")
            raise
        finally:
            if self.ui:
                self.ui.stop_loading_animation()
