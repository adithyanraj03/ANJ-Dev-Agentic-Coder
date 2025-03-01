import re
import json
import logging
import os
import glob
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set

def sanitize_plan(plan_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize and validate plan data to ensure consistency between files and steps.
    This helps prevent issues where the plan contains mismatches that could cause the agent to get stuck.
    """
    if not isinstance(plan_data, dict):
        plan_data = {"description": "Generic plan", "files": {"create": [], "modify": []}, "steps": []}
        return plan_data
    
    # Ensure basic structure exists
    if "files" not in plan_data:
        plan_data["files"] = {"create": [], "modify": []}
    elif not isinstance(plan_data["files"], dict):
        plan_data["files"] = {"create": [], "modify": []}
    
    if "create" not in plan_data["files"]:
        plan_data["files"]["create"] = []
    if "modify" not in plan_data["files"]:
        plan_data["files"]["modify"] = []
    
    if "steps" not in plan_data:
        plan_data["steps"] = []
    
    # Track files mentioned in steps
    files_in_steps = set()
    
    # Ensure each step has required fields and fix inconsistencies
    for step in plan_data["steps"]:
        if not isinstance(step, dict):
            continue
            
        # Ensure step has a description
        if "description" not in step:
            step["description"] = "Implementation step"
        
        # Handle file field
        if "file" not in step:
            # Try to extract file from description
            file_match = re.search(r'[\'"`]([\w\.]+)[\'"`]', step.get("description", ""))
            if file_match:
                step["file"] = file_match.group(1)
            else:
                step["file"] = "code.py"  # Default placeholder
        
        # Keep track of files referenced in steps
        files_in_steps.add(step["file"])
        
        # Handle action field
        if "action" not in step:
            # Check if it's in the create list
            if step["file"] in plan_data["files"]["create"]:
                step["action"] = "create"
            elif step["file"] in plan_data["files"]["modify"]:
                step["action"] = "modify"
            else:
                # Default based on file extension
                if "." not in step["file"] or step["description"].lower().startswith("creat"):
                    step["action"] = "create"
                else:
                    step["action"] = "modify"
    
    # Ensure files lists include all files from steps
    for step in plan_data["steps"]:
        file_name = step.get("file", "")
        action = step.get("action", "")
        
        if action == "create" and file_name not in plan_data["files"]["create"]:
            plan_data["files"]["create"].append(file_name)
        elif action == "modify" and file_name not in plan_data["files"]["modify"]:
            plan_data["files"]["modify"].append(file_name)
    
    return plan_data

def parse_plan_response(response: str) -> Dict[str, Any]:
    """
    Parse an LLM response into a valid plan structure, ensuring consistency.
    
    Args:
        response: Raw LLM response text
        
    Returns:
        Dict containing the parsed and sanitized plan
    """
    # Try to parse as JSON directly
    try:
        plan_data = json.loads(response)
        return sanitize_plan(plan_data)
    except json.JSONDecodeError:
        pass
    
    # Try to extract JSON from markdown
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', response, re.DOTALL)
    if json_match:
        try:
            plan_data = json.loads(json_match.group(1))
            return sanitize_plan(plan_data)
        except json.JSONDecodeError:
            pass
    
    # Try to extract non-JSON structure
    try:
        # Extract description
        desc_match = re.search(r'(?:Plan|Implementation):\s*(.+?)(?:\n|$)', response, re.IGNORECASE)
        description = desc_match.group(1).strip() if desc_match else "Implementation plan"
        
        # Extract files to create/modify
        files_create = []
        files_modify = []
        
        create_matches = re.findall(r'(?:Create|Add).*?[\'"`]([^\'"`]+)[\'"`]', response, re.IGNORECASE)
        files_create.extend(create_matches)
        
        modify_matches = re.findall(r'(?:Modify|Update|Edit).*?[\'"`]([^\'"`]+)[\'"`]', response, re.IGNORECASE)
        files_modify.extend(modify_matches)
        
        # Extract steps
        steps = []
        step_matches = re.finditer(r'(?:Step|Action)\s*\d+:?\s*(.+?)(?=(?:Step|Action)\s*\d+:?|\Z)', response, re.DOTALL | re.IGNORECASE)
        
        for i, match in enumerate(step_matches):
            step_text = match.group(1).strip()
            first_line = step_text.split('\n')[0].strip()
            
            # Try to identify the file and action
            file_match = re.search(r'(?:in|for|file|create|modify)\s+[\'"`]?([a-zA-Z0-9_\-\.]+)[\'"`]?', step_text, re.IGNORECASE)
            
            file_name = ""
            if file_match:
                file_name = file_match.group(1)
                
                # Check if file already exists in either list
                if file_name not in files_create and file_name not in files_modify:
                    if "create" in step_text.lower():
                        files_create.append(file_name)
                    else:
                        files_modify.append(file_name)
            
            action = "create" if "create" in step_text.lower() else "modify"
            
            steps.append({
                "description": first_line,
                "file": file_name,
                "action": action,
                "overview": step_text
            })
        
        plan_data = {
            "description": description,
            "files": {
                "create": files_create,
                "modify": files_modify
            },
            "steps": steps
        }
        
        return sanitize_plan(plan_data)
    except Exception as e:
        logging.error(f"Error parsing plan response: {e}")
        return {
            "description": "Failed to parse plan",
            "files": {"create": [], "modify": []},
            "steps": []
        }

# New file and directory utility functions for enhanced agent capabilities
def find_files(base_path: str, pattern: str) -> List[str]:
    """Find files matching a pattern in the given directory and its subdirectories."""
    matches = []
    try:
        matches = glob.glob(os.path.join(base_path, "**", pattern), recursive=True)
        # Filter out directories and non-existent files
        matches = [f for f in matches if os.path.isfile(f)]
    except Exception as e:
        logging.error(f"Error finding files with pattern {pattern}: {e}")
    
    # Log raw results for debugging
    logging.debug(f"Raw find results for pattern '{pattern}': {matches}")
    return matches

def search_code(base_path: str, pattern: str) -> Dict[str, List[Dict[str, Any]]]:
    """Search for a pattern in code files and return matches with context."""
    results = {}
    
    # Extensions to search
    extensions = ['.py', '.js', '.jsx', '.ts', '.tsx', '.html', '.css', '.json']
    
    # Log the start of search operation
    logging.info(f"Searching codebase for pattern: '{pattern}'")
    
    # Find all matching files
    for ext in extensions:
        files = find_files(base_path, f"*{ext}")
        for file_path in files:
            # Skip large files and common exclusions
            if os.path.getsize(file_path) > 1024 * 1024:  # Skip files > 1MB
                continue
                
            # Skip system directories
            if any(dir_name in file_path for dir_name in ['__pycache__', 'node_modules', '.git', 'venv']):
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                # Search for pattern (case-insensitive)
                if pattern.lower() in content.lower():
                    # Compile the matches with context
                    lines = content.split('\n')
                    matches = []
                    
                    for i, line in enumerate(lines):
                        if pattern.lower() in line.lower():
                            # Add context (lines before and after)
                            context_start = max(0, i - 2)
                            context_end = min(len(lines), i + 3)
                            
                            context_lines = []
                            for ctx_idx in range(context_start, context_end):
                                context_lines.append({
                                    'line_number': ctx_idx + 1,
                                    'content': lines[ctx_idx],
                                    'is_match': ctx_idx == i
                                })
                            
                            matches.append({
                                'line_number': i + 1,
                                'match_line': line,
                                'context_lines': context_lines
                            })
                    
                    # Only include if we actually found matches
                    if matches:
                        # Get relative path for display
                        rel_path = os.path.relpath(file_path, base_path)
                        results[rel_path] = matches
                        logging.debug(f"Found {len(matches)} matches in {rel_path}")
            except Exception as e:
                # Log the error for debugging
                logging.error(f"Error searching file {file_path}: {e}")
                continue
    
    # Log summary of search results
    logging.info(f"Search complete. Found matches in {len(results)} files.")
    return results

def get_directory_structure(path: str, max_depth: int = 3) -> Dict[str, Any]:
    """Get the structure of a directory up to a certain depth."""
    result = {
        'name': os.path.basename(path) or path,
        'path': path,
        'type': 'dir',
        'children': []
    }
    
    if max_depth <= 0:
        return result
    
    try:
        entries = os.listdir(path)
        
        # Process directories first, then files
        dirs = []
        files = []
        
        for entry in entries:
            full_path = os.path.join(path, entry)
            
            # Skip system files and directories
            if entry.startswith('.') or entry in ['__pycache__', 'node_modules', 'venv']:
                continue
            
            if os.path.isdir(full_path):
                dirs.append(entry)
            else:
                files.append(entry)
        
        # Add directories
        for dir_name in sorted(dirs):
            full_path = os.path.join(path, dir_name)
            child = get_directory_structure(full_path, max_depth - 1)
            result['children'].append(child)
        
        # Add files
        for file_name in sorted(files):
            full_path = os.path.join(path, file_name)
            # Skip large files
            if os.path.getsize(full_path) > 1024 * 1024:  # Skip files > 1MB
                continue
                
            result['children'].append({
                'name': file_name,
                'path': full_path,
                'type': 'file',
                'ext': os.path.splitext(file_name)[1]
            })
    
    except Exception as e:
        # Log the error for debugging
        logging.error(f"Error getting directory structure for {path}: {e}")
    
    return result

def get_file_preview(file_path: str, max_lines: int = 50) -> str:
    """Get a preview of a file's contents."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            
        # If the file is smaller than max_lines, return all of it
        if len(lines) <= max_lines:
            return ''.join(lines)
        
        # Otherwise, return the first and last sections
        first_section = ''.join(lines[:max_lines//2])
        last_section = ''.join(lines[-max_lines//2:])
        
        return first_section + f"\n\n... [file truncated, showing {max_lines} of {len(lines)} lines] ...\n\n" + last_section
    except Exception as e:
        logging.error(f"Error reading file {file_path}: {e}")
        return f"Error reading file: {str(e)}"
        
def get_file_info(file_path: str) -> Dict[str, Any]:
    """Get information about a file."""
    try:
        stat = os.stat(file_path)
        
        return {
            'path': file_path,
            'name': os.path.basename(file_path),
            'size': stat.st_size,
            'modified': stat.st_mtime,
            'extension': os.path.splitext(file_path)[1],
            'exists': True
        }
    except Exception as e:
        logging.error(f"Error getting file info for {file_path}: {e}")
        return {
            'path': file_path,
            'error': str(e),
            'exists': False
        }

def backup_file(file_path: str) -> Optional[str]:
    """Create a backup of a file before modifying it."""
    try:
        if not os.path.exists(file_path):
            return None
            
        backup_path = f"{file_path}.bak"
        shutil.copy2(file_path, backup_path)
        logging.info(f"Created backup of {file_path} at {backup_path}")
        return backup_path
    except Exception as e:
        logging.error(f"Error creating backup of {file_path}: {e}")
        return None

def wrap_text(text: str, width: int = 80) -> List[str]:
    """Wrap text to a specified width for better display."""
    if not text:
        return []
        
    lines = []
    current_line = []
    current_length = 0
    
    # Split by words
    words = text.split()
    
    for word in words:
        # Check if adding this word would exceed the width
        if current_length + len(word) + (1 if current_length > 0 else 0) <= width:
            # Add word to current line
            current_line.append(word)
            current_length += len(word) + (1 if current_length > 0 else 0)
        else:
            # Current line is full, start a new one
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
            current_length = len(word)
    
    # Add any remaining line
    if current_line:
        lines.append(' '.join(current_line))
    
    return lines

# Enhanced logging functions for detailed tracing
def log_detailed(message: str, level: str = "INFO", data: Any = None):
    """Log a detailed message with optional data."""
    log_func = getattr(logging, level.lower(), logging.info)
    
    # Log the main message
    log_func(message)
    
    # If data is provided, log it too
    if data is not None:
        if isinstance(data, dict) or isinstance(data, list):
            try:
                formatted_data = json.dumps(data, indent=2)
                for line in formatted_data.split('\n'):
                    log_func(f"  {line}")
            except Exception:
                log_func(f"  Raw data: {data}")
        else:
            log_func(f"  {data}")

def log_action_start(action: str, details: str = "", level: str = "INFO"):
    """Log the start of an action for better tracing."""
    log_detailed(f"=== START: {action} ===", level)
    if details:
        logging.info(f"Details: {details}")

def log_action_end(action: str, success: bool = True, result: Any = None, level: str = "INFO"):
    """Log the end of an action with result information."""
    status = "SUCCESS" if success else "FAILURE"
    log_detailed(f"=== END: {action} ({status}) ===", level, result)