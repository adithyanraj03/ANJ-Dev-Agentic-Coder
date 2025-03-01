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
