"""
Vector Search Client

High-level client for vector search operations, providing a unified interface
for semantic field discovery and field value lookup.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple, Callable

from vector_search.field_lookup import FieldLookupService
from vector_search.enhanced_integration import EnhancedVectorIntegration
from core.models import VectorSearchResult, FieldMatch
from core.exceptions import VectorSearchError

logger = logging.getLogger(__name__)


class VectorSearchClient:
    """
    High-level client for vector search operations
    
    Provides a unified interface for semantic field discovery, field value lookup,
    and enhanced query processing with vector search integration.
    """
    
    def __init__(self):
        self.field_service = FieldLookupService()
        self.enhanced_service = EnhancedVectorIntegration()
    
    async def search_fields_semantically(self, query: str, explore_filter: Optional[List[str]] = None, 
                                       limit: int = 10) -> VectorSearchResult:
        """
        Search for fields using semantic similarity
        
        Args:
            query: Natural language query or search term
            explore_filter: Optional list of explore IDs to filter by
            limit: Maximum number of results
            
        Returns:
            VectorSearchResult with matching fields
        """
        try:
            import time
            start_time = time.time()
            
            # Extract entities from query for more targeted search
            search_terms = self.enhanced_service._extract_entities_regex_fallback(query)
            if not search_terms:
                search_terms = [query]  # Use the whole query as fallback
            
            # Perform semantic search
            field_matches = await self.field_service.search_semantic_fields(
                search_terms=search_terms,
                explore_ids=explore_filter,
                limit_per_term=max(1, limit // len(search_terms))
            )
            
            processing_time = time.time() - start_time
            
            return VectorSearchResult(
                query=query,
                matches=field_matches,
                search_type="semantic",
                total_results=len(field_matches),
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Semantic field search failed: {e}")
            raise VectorSearchError(f"Semantic field search failed: {e}", search_type="semantic")
    
    async def lookup_field_values(self, search_value: str, field_filter: Optional[str] = None, 
                                 limit: int = 10) -> List[Dict[str, Any]]:
        """
        Look up specific values in database fields
        
        Args:
            search_value: Value to search for
            field_filter: Optional field location to restrict search to
            limit: Maximum number of results
            
        Returns:
            List of matching field values with metadata
        """
        try:
            return await self.field_service.lookup_field_values(
                search_string=search_value,
                field_location=field_filter,
                limit=limit
            )
            
        except Exception as e:
            logger.error(f"Field value lookup failed: {e}")
            raise VectorSearchError(f"Field value lookup failed: {e}", search_type="field_values")
    
    async def enhance_query_for_parameters(self, query: str, vertex_ai_func: Callable) -> Tuple[str, str, Dict[str, List]]:
        """
        Enhance a query with vector search for better parameter generation
        
        Args:
            query: User's natural language query
            vertex_ai_func: Function to call Vertex AI for entity extraction
            
        Returns:
            Tuple of (parameter_context, explore_context, search_results)
        """
        try:
            return await self.enhanced_service.enhance_query_with_vector_search(query, vertex_ai_func)
            
        except Exception as e:
            logger.error(f"Query enhancement failed: {e}")
            # Return empty contexts on failure
            return "", "", {}
    
    async def get_search_statistics(self, explore_filter: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get statistics about the vector search system
        
        Args:
            explore_filter: Optional list of explore IDs to filter statistics
            
        Returns:
            Dictionary containing search system statistics
        """
        try:
            stats = await self.field_service.get_field_statistics(explore_ids=explore_filter)
            
            # Add system health indicators
            system_health = {
                "status": "healthy" if stats.get("total_fields", 0) > 0 else "no_data",
                "coverage": {
                    "fields": stats.get("total_fields", 0),
                    "explores": stats.get("total_explores", 0),
                    "models": stats.get("total_models", 0),
                    "field_values": stats.get("total_field_values", 0)
                },
                "recommendations": self._generate_health_recommendations(stats)
            }
            
            return {
                "statistics": stats,
                "health": system_health,
                "filter_applied": explore_filter is not None
            }
            
        except Exception as e:
            logger.error(f"Failed to get search statistics: {e}")
            return {
                "statistics": {},
                "health": {"status": "error", "error": str(e)},
                "filter_applied": False
            }
    
    async def search_comprehensive(self, query: str, explore_filter: Optional[List[str]] = None, 
                                  include_values: bool = True) -> Dict[str, Any]:
        """
        Perform comprehensive search including both field matching and value lookup
        
        Args:
            query: Search query
            explore_filter: Optional explore filter
            include_values: Whether to include field value search
            
        Returns:
            Comprehensive search results
        """
        try:
            # Perform semantic field search
            field_results = await self.search_fields_semantically(query, explore_filter, limit=10)
            
            results = {
                "query": query,
                "field_matches": field_results,
                "value_matches": [],
                "summary": {
                    "total_field_matches": field_results.total_results,
                    "total_value_matches": 0,
                    "processing_time": field_results.processing_time
                }
            }
            
            # Optionally perform field value search
            if include_values:
                try:
                    import time
                    value_start = time.time()
                    
                    value_matches = await self.lookup_field_values(query, limit=10)
                    
                    results["value_matches"] = value_matches
                    results["summary"]["total_value_matches"] = len(value_matches)
                    results["summary"]["processing_time"] += (time.time() - value_start)
                    
                except Exception as e:
                    logger.warning(f"Value search failed, continuing with field results only: {e}")
            
            return results
            
        except Exception as e:
            logger.error(f"Comprehensive search failed: {e}")
            raise VectorSearchError(f"Comprehensive search failed: {e}", search_type="comprehensive")
    
    def _generate_health_recommendations(self, stats: Dict[str, Any]) -> List[str]:
        """Generate health recommendations based on statistics"""
        recommendations = []
        
        total_fields = stats.get("total_fields", 0)
        total_explores = stats.get("total_explores", 0)
        total_values = stats.get("total_field_values", 0)
        
        if total_fields == 0:
            recommendations.append("Vector search system needs initialization - no fields indexed")
        elif total_fields < 50:
            recommendations.append("Consider indexing more fields for better coverage")
        
        if total_explores < 3:
            recommendations.append("Add more explores to improve search scope")
        
        if total_values < 1000:
            recommendations.append("Field value coverage is low - consider indexing more dimension values")
        
        if not recommendations:
            recommendations.append("Vector search system is well-configured and healthy")
        
        return recommendations