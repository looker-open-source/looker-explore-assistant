"""
Custom exceptions for the Looker Explore Assistant
"""


class TokenLimitExceededException(Exception):
    """Exception raised when Vertex AI response is truncated due to token limits"""
    
    def __init__(self, message="Response truncated due to token limit", current_tokens=None, usage_metadata=None):
        self.message = message
        self.current_tokens = current_tokens
        self.usage_metadata = usage_metadata
        super().__init__(self.message)


class ExploreNotFoundError(Exception):
    """Exception raised when no suitable explore is found for a query"""
    
    def __init__(self, message="No suitable explore found", available_explores=None):
        self.message = message
        self.available_explores = available_explores or []
        super().__init__(self.message)


class VectorSearchError(Exception):
    """Exception raised when vector search operations fail"""
    
    def __init__(self, message="Vector search operation failed", search_type=None):
        self.message = message
        self.search_type = search_type
        super().__init__(self.message)


class LookerAPIError(Exception):
    """Exception raised when Looker API operations fail"""
    
    def __init__(self, message="Looker API operation failed", api_method=None):
        self.message = message
        self.api_method = api_method
        super().__init__(self.message)


class ParameterGenerationError(Exception):
    """Exception raised when explore parameter generation fails"""
    
    def __init__(self, message="Parameter generation failed", explore_key=None):
        self.message = message
        self.explore_key = explore_key
        super().__init__(self.message)