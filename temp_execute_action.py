    def _execute_action(self, action: Dict[str, Any], stdscr=None) -> Dict[str, Any]:
        """Execute a single action and return the result."""
        action_type = action.get("type")
        
        # Import logging functions if available
        try:
            from agent_utils import log_action_start, log_action_end
            log_action_start(f"Execute action: {action_type}")
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
            # New action types
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
                
            # Log action result if logging functions are available
            try:
                from agent_utils import log_action_end
                success = result.get("success", False) if result else False
                log_action_end(f"Execute action: {action_type}", success)
            except ImportError:
                pass
                
            return result
        except Exception as e:
            logging.error(f"Error executing action {action_type}: {e}")
            try:
                from agent_utils import log_action_end
                log_action_end(f"Execute action: {action_type}", False, {"error": str(e)})
            except ImportError:
                pass
                
            return {
                "success": False,
                "type": action_type or "unknown",
                "message": f"Error executing action: {e}"
            }
