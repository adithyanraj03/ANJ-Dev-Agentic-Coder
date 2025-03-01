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
