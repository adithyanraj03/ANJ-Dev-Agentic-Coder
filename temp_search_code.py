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
