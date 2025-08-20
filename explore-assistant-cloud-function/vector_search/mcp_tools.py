"""
Vector Search MCP Tools

Provides MCP tool registration and handlers for vector search operations.
"""

import logging
from typing import Dict, Any, List, Callable
from google.cloud import bigquery

from vector_search.field_lookup import FieldLookupService
from vector_search.enhanced_integration import EnhancedVectorIntegration
from core.exceptions import VectorSearchError

logger = logging.getLogger(__name__)


def register_vector_search_tools(tools_dict: Dict[str, Callable], bq_client: bigquery.Client, project_id: str) -> None:
    """
    Register vector search MCP tools
    
    Args:
        tools_dict: Dictionary to register tools in
        bq_client: BigQuery client
        project_id: GCP project ID
    """
    
    # Create service instances
    field_service = FieldLookupService()
    enhanced_service = EnhancedVectorIntegration()
    
    # Define tool handlers
    async def search_semantic_fields(search_terms: List[str], explore_ids: List[str] = None, limit_per_term: int = 5) -> Dict[str, Any]:
        """Search for semantically similar fields"""
        try:
            matches = await field_service.search_semantic_fields(
                search_terms=search_terms,
                explore_ids=explore_ids,
                limit_per_term=limit_per_term
            )
            
            return {
                "search_terms": search_terms,
                "total_matches": len(matches),
                "matches": [
                    {
                        "field_location": match.field_location,
                        "field_name": match.field_name,
                        "similarity": match.similarity_score,
                        "description": match.description,
                        "field_type": match.field_type
                    }
                    for match in matches
                ]
            }
            
        except VectorSearchError as e:
            logger.error(f"Semantic field search failed: {e}")
            return {"error": str(e), "search_type": e.search_type}
        except Exception as e:
            logger.error(f"Unexpected error in semantic field search: {e}")
            return {"error": f"Semantic field search failed: {e}"}
    
    async def lookup_field_values(search_string: str, field_location: str = None, limit: int = 10) -> Dict[str, Any]:
        """Look up field values by string matching"""
        try:
            matches = await field_service.lookup_field_values(
                search_string=search_string,
                field_location=field_location,
                limit=limit
            )
            
            return {
                "search_string": search_string,
                "field_location": field_location,
                "total_matches": len(matches),
                "matches": matches
            }
            
        except VectorSearchError as e:
            logger.error(f"Field value lookup failed: {e}")
            return {"error": str(e), "search_type": e.search_type}
        except Exception as e:
            logger.error(f"Unexpected error in field value lookup: {e}")
            return {"error": f"Field value lookup failed: {e}"}
    
    async def get_field_statistics(explore_ids: List[str] = None) -> Dict[str, Any]:
        """Get statistics about indexed fields"""
        try:
            stats = await field_service.get_field_statistics(explore_ids=explore_ids)
            return {
                "explore_filter": explore_ids,
                "statistics": stats
            }
        except Exception as e:
            logger.error(f"Failed to get field statistics: {e}")
            return {"error": f"Failed to get field statistics: {e}"}
    
    async def check_vector_search_status(arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Check vector search system status"""
        try:
            # Check if vector tables exist and get basic stats
            stats = await field_service.get_field_statistics()
            
            return {
                "system_status": "operational" if stats else "not_configured",
                "statistics": stats,
                "recommendations": _get_system_recommendations(stats)
            }
            
        except Exception as e:
            logger.error(f"Vector search status check failed: {e}")
            return {
                "system_status": "error",
                "error": str(e),
                "recommendations": ["Check BigQuery configuration and permissions"]
            }
    
    def _get_system_recommendations(stats: Dict[str, Any]) -> List[str]:
        """Generate system recommendations based on statistics"""
        recommendations = []
        
        if not stats:
            recommendations.append("Vector search system needs to be initialized")
            return recommendations
        
        total_fields = stats.get("total_fields", 0)
        total_explores = stats.get("total_explores", 0)
        
        if total_fields < 100:
            recommendations.append("Consider indexing more fields for better search coverage")
        
        if total_explores < 5:
            recommendations.append("Consider adding more explores to the vector search index")
        
        if not recommendations:
            recommendations.append("Vector search system is well-configured")
        
        return recommendations
    
    # Register tools in the tools dictionary
    tools_dict.update({
        "search_semantic_fields": search_semantic_fields,
        "lookup_field_values": lookup_field_values,
        "get_field_statistics": get_field_statistics,
        "check_vector_search_status": check_vector_search_status,
    })
    
    logger.info(f"Registered {len(tools_dict)} vector search MCP tools")


# Tool metadata for MCP server registration
VECTOR_SEARCH_TOOLS_METADATA = [
    {
        "name": "search_semantic_fields",
        "description": "Search for database fields using semantic similarity",
        "parameters": {
            "type": "object",
            "properties": {
                "search_terms": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Terms to search for semantically"
                },
                "explore_ids": {
                    "type": "array", 
                    "items": {"type": "string"},
                    "description": "Optional explore IDs to filter by"
                },
                "limit_per_term": {
                    "type": "integer",
                    "description": "Maximum results per search term",
                    "default": 5
                }
            },
            "required": ["search_terms"]
        }
    },
    {
        "name": "lookup_field_values",
        "description": "Look up specific values in database fields",
        "parameters": {
            "type": "object",
            "properties": {
                "search_string": {
                    "type": "string",
                    "description": "String to search for in field values"
                },
                "field_location": {
                    "type": "string",
                    "description": "Optional specific field to search in"
                },
                "limit": {
                    "type": "integer", 
                    "description": "Maximum number of results",
                    "default": 10
                }
            },
            "required": ["search_string"]
        }
    },
    {
        "name": "get_field_statistics",
        "description": "Get statistics about indexed fields and explores",
        "parameters": {
            "type": "object",
            "properties": {
                "explore_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional explore IDs to filter statistics"
                }
            }
        }
    },
    {
        "name": "check_vector_search_status", 
        "description": "Check the status and health of the vector search system",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
]