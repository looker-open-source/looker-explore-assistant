"""
Vector search module for semantic field discovery

Provides vector search capabilities for finding relevant database fields
and values using semantic similarity.
"""

from .client import VectorSearchClient
from .field_lookup import FieldLookupService
from .enhanced_integration import EnhancedVectorIntegration
from .mcp_tools import register_vector_search_tools

__all__ = [
    'VectorSearchClient',
    'FieldLookupService', 
    'EnhancedVectorIntegration',
    'register_vector_search_tools'
]