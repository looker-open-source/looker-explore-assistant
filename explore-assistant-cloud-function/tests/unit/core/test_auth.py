"""
Unit tests for core.auth module
"""

import pytest
from unittest.mock import patch

from core.auth import (
    extract_user_info_from_token,
    extract_user_email_from_token,
    get_response_headers
)


class TestGetResponseHeaders:
    """Test CORS response headers"""
    
    def test_returns_correct_headers(self):
        headers = get_response_headers()
        
        assert headers["Access-Control-Allow-Origin"] == "*"
        assert headers["Access-Control-Allow-Methods"] == "POST, OPTIONS, GET"
        assert "Content-Type" in headers["Access-Control-Allow-Headers"]
        assert "Authorization" in headers["Access-Control-Allow-Headers"]


class TestExtractUserInfoFromToken:
    """Test JWT token parsing"""
    
    def test_valid_jwt_token(self, sample_jwt_token):
        user_info = extract_user_info_from_token(sample_jwt_token)
        
        assert user_info["email"] == "test@example.com"
        assert user_info["user_id"] == "user123"
        assert user_info["name"] == "Test User"
    
    def test_token_with_bearer_prefix(self, sample_jwt_token):
        bearer_token = f"Bearer {sample_jwt_token}"
        user_info = extract_user_info_from_token(bearer_token)
        
        assert user_info["email"] == "test@example.com"
        assert user_info["user_id"] == "user123"
    
    def test_invalid_token_none(self):
        user_info = extract_user_info_from_token(None)
        
        assert user_info["email"] is None
        assert user_info["user_id"] is None
        assert user_info["name"] is None
    
    def test_invalid_token_empty_string(self):
        user_info = extract_user_info_from_token("")
        
        assert user_info["email"] is None
        assert user_info["user_id"] is None
        assert user_info["name"] is None
    
    def test_invalid_token_wrong_format(self):
        user_info = extract_user_info_from_token("invalid.token")
        
        assert user_info["email"] is None
        assert user_info["user_id"] is None
        assert user_info["name"] is None
    
    def test_token_with_whitespace(self, sample_jwt_token):
        user_info = extract_user_info_from_token(f"  Bearer  {sample_jwt_token}  ")
        
        assert user_info["email"] == "test@example.com"
        assert user_info["user_id"] == "user123"
    
    @patch('core.auth.logging')
    def test_logging_on_invalid_token(self, mock_logging):
        extract_user_info_from_token("invalid")
        
        mock_logging.error.assert_called()


class TestExtractUserEmailFromToken:
    """Test email extraction wrapper"""
    
    def test_returns_email_from_valid_token(self, sample_jwt_token):
        email = extract_user_email_from_token(sample_jwt_token)
        
        assert email == "test@example.com"
    
    def test_returns_none_for_invalid_token(self):
        email = extract_user_email_from_token("invalid")
        
        assert email is None