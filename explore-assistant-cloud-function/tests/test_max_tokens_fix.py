#!/usr/bin/env python3
"""
Test for MAX_TOKENS retry fix
"""

import sys
import os
import logging
from unittest.mock import patch, MagicMock

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO)

try:
    from mcp_server import (
        call_vertex_ai_with_retry,
        TokenLimitExceededException,
        extract_vertex_response_text
    )
except ImportError as e:
    print(f"❌ Error importing modules: {e}")
    sys.exit(1)

def test_max_tokens_retry():
    """Test that MAX_TOKENS finish reason triggers retry with higher limits"""
    print("🧪 Testing MAX_TOKENS retry mechanism...")
    
    # Mock response that will trigger MAX_TOKENS on first attempt, success on second
    def mock_api_call(request_body):
        max_tokens = request_body.get('generationConfig', {}).get('maxOutputTokens', 2048)
        
        if max_tokens <= 2048:
            # First call - return truncated response
            return {
                "candidates": [
                    {
                        "content": {
                            "parts": [{"text": "This response was truncated"}]
                        },
                        "finishReason": "MAX_TOKENS"
                    }
                ],
                "usageMetadata": {
                    "candidatesTokenCount": 2048,
                    "promptTokenCount": 1000
                }
            }
        else:
            # Retry with higher limits - return complete response
            return {
                "candidates": [
                    {
                        "content": {
                            "parts": [{"text": "This is the complete response with higher token limits"}]
                        },
                        "finishReason": "STOP"
                    }
                ],
                "usageMetadata": {
                    "candidatesTokenCount": 3000,
                    "promptTokenCount": 1000
                }
            }
    
    # Test the retry mechanism
    test_request = {
        "contents": [{"role": "user", "parts": [{"text": "Test prompt"}]}],
        "generationConfig": {
            "maxOutputTokens": 2048,
            "temperature": 0.1
        }
    }
    
    with patch('mcp_server.call_vertex_ai_api_with_service_account', side_effect=mock_api_call):
        result = call_vertex_ai_with_retry(test_request, "test_max_tokens_retry", process_response=True)
        
        if result and 'processed_response' in result:
            response_text = result['processed_response']
            print(f"✅ Success! Got complete response: '{response_text}'")
            
            # Verify the response is the complete one, not truncated
            if "complete response with higher token limits" in response_text:
                print("✅ Retry mechanism working correctly - got complete response!")
                return True
            else:
                print(f"❌ Got unexpected response: {response_text}")
                return False
        else:
            print(f"❌ Failed to get processed response: {result}")
            return False

def test_max_tokens_exception():
    """Test that TokenLimitExceededException is raised correctly"""
    print("\n🧪 Testing TokenLimitExceededException...")
    
    test_response = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": "Truncated response"}]
                },
                "finishReason": "MAX_TOKENS"
            }
        ],
        "usageMetadata": {
            "candidatesTokenCount": 2048
        }
    }
    
    try:
        result = extract_vertex_response_text(test_response)
        print("❌ Expected TokenLimitExceededException but got result:", result)
        return False
    except TokenLimitExceededException as e:
        print(f"✅ TokenLimitExceededException raised correctly: {e.message}")
        print(f"✅ Token info: {e.current_tokens} tokens")
        return True
    except Exception as e:
        print(f"❌ Unexpected exception: {e}")
        return False

if __name__ == '__main__':
    print("🚀 Testing MAX_TOKENS retry fix...")
    
    # Test 1: Exception is raised correctly
    success1 = test_max_tokens_exception()
    
    # Test 2: Retry mechanism works
    success2 = test_max_tokens_retry()
    
    if success1 and success2:
        print("\n🎉 All tests passed! MAX_TOKENS retry fix is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed.")
        sys.exit(1)
