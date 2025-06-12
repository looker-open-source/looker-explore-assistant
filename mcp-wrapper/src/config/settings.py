# File: /mcp-wrapper/mcp-wrapper/src/config/settings.py

# Configuration settings for the MCP wrapper application

import os
from typing import Optional
from pydantic import BaseSettings, Field

class Settings(BaseSettings):
    """Configuration settings for the MCP wrapper"""
    
    # Target API settings
    looker_api_url: str = Field(
        default="https://looker-explore-assistant-mcp-rchq2jmtba-uc.a.run.app",
        env="LOOKER_API_URL"
    )
    
    # Timeout settings
    request_timeout: int = Field(default=60, env="REQUEST_TIMEOUT")
    
    # OAuth settings (for forwarding to the real service)
    oauth_token: Optional[str] = Field(default=None, env="OAUTH_TOKEN")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Development settings
    debug_mode: bool = Field(default=False, env="DEBUG_MODE")
    test_mode: bool = Field(default=False, env="TEST_MODE")
    
    class Config:
        env_file = ".env"
        case_sensitive = False

    @staticmethod
    def init_app(app):
        pass  # Placeholder for any app initialization logic if needed

# Example of how to use the Settings class
# settings = Settings()
# print(settings.looker_api_url)