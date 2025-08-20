"""
Core module for Looker Explore Assistant

This module contains foundational components used throughout the application:
- Authentication and user management
- Configuration and environment settings
- Custom exceptions
- Data models and schemas
"""

from .auth import (
    extract_user_info_from_token,
    extract_user_email_from_token,
    get_response_headers
)
from .config import (
    get_max_tokens_for_model,
    get_model_generation_defaults,
    update_token_warning_thresholds,
    MODEL_LIMITS,
    PROJECT,
    REGION,
    VERTEX_MODEL
)
from .exceptions import (
    TokenLimitExceededException,
    ExploreNotFoundError,
    VectorSearchError
)
from .models import (
    FieldMatch,
    VertexResponse
)
from .system_status import (
    SystemStatusService
)
from .olympic_service import (
    OlympicOperationsService,
    QueryRank
)

__all__ = [
    # Auth
    'extract_user_info_from_token',
    'extract_user_email_from_token', 
    'get_response_headers',
    # Config
    'get_max_tokens_for_model',
    'get_model_generation_defaults',
    'update_token_warning_thresholds',
    'MODEL_LIMITS',
    'PROJECT',
    'REGION', 
    'VERTEX_MODEL',
    # Exceptions
    'TokenLimitExceededException',
    'ExploreNotFoundError',
    'VectorSearchError',
    # Models
    'FieldMatch',
    'VertexResponse',
    # System Status
    'SystemStatusService',
    # Olympic Operations
    'OlympicOperationsService',
    'QueryRank'
]