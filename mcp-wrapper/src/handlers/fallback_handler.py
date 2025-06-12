import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class FallbackHandler:
    """Handler for maintaining backward compatibility with existing API behavior"""
    
    def __init__(self, settings):
        self.settings = settings
    
    async def handle_direct_request(self, request_data: Dict[str, Any], oauth_token: str) -> Dict[str, Any]:
        """
        Handle direct API requests (non-MCP) to maintain compatibility
        This maintains the current response behavior for requests without MCP context
        """
        try:
            # This would be used if you want to support both MCP and direct HTTP API
            # For now, we'll focus on MCP-only implementation
            logger.info("Direct request handling not implemented - use MCP tools instead")
            
            return {
                "status": "error",
                "message": "Direct API requests not supported. Use MCP tools instead.",
                "suggestion": "Use the 'generate_looker_explore' tool via MCP protocol"
            }
            
        except Exception as e:
            logger.error(f"Error in fallback handler: {e}")
            return {
                "status": "error", 
                "message": f"Fallback handler error: {str(e)}"
            }

    def handle_request(self, request):
        """Legacy method for compatibility"""
        return {
            "status": "error",
            "message": "No handler found for the given request. Use MCP tools instead.",
            "data": None
        }