"""
Vertex AI integration module

Provides secure access to Vertex AI APIs with proper token management
and response parsing capabilities.
"""

from .client import (
    call_vertex_ai_api_with_service_account,
    call_vertex_ai_with_retry,
    extract_vertex_response_text
)
from .response_parser import (
    parse_vertex_response,
    extract_function_calls,
    validate_vertex_response
)

__all__ = [
    # Client
    'call_vertex_ai_api_with_service_account',
    'call_vertex_ai_with_retry',
    'extract_vertex_response_text',
    # Response parser
    'parse_vertex_response',
    'extract_function_calls',
    'validate_vertex_response'
]