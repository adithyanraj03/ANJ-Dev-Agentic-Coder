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
