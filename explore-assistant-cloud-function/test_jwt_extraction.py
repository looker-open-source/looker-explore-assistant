#!/usr/bin/env python3
"""Test JWT user extraction functionality"""

import os
import sys
import json
import base64

# Add the current directory to Python path so we can import modules
sys.path.append('.')

from mcp_server import extract_user_info_from_token

def test_jwt_extraction():
    """Test JWT user extraction with sample tokens"""
    
    print("Testing JWT user extraction functionality...")
    
    # Create a test JWT payload
    test_payload = {
        "sub": "1234567890",
        "email": "test.user@example.com", 
        "name": "Test User",
        "given_name": "Test",
        "family_name": "User",
        "iat": 1516239022
    }
    
    # Create a mock JWT structure (header.payload.signature)
    import base64
    import json
    
    # Header (we'll use a simple one)
    header = {"alg": "RS256", "typ": "JWT"}
    header_encoded = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
    
    # Payload
    payload_encoded = base64.urlsafe_b64encode(json.dumps(test_payload).encode()).decode().rstrip('=')
    
    # Signature (dummy)
    signature = "dummy_signature"
    
    # Combine into JWT
    test_jwt = f"{header_encoded}.{payload_encoded}.{signature}"
    test_bearer_token = f"Bearer {test_jwt}"
    
    print(f"Test JWT: {test_jwt[:50]}...")
    print(f"Test payload: {test_payload}")
    
    # Test extraction
    print(f"\nTesting user info extraction...")
    user_info = extract_user_info_from_token(test_bearer_token)
    
    print(f"\nExtracted user info:")
    print(f"  Email: {user_info.get('email')}")
    print(f"  User ID: {user_info.get('user_id')}")
    print(f"  Name: {user_info.get('name')}")
    
    # Verify results
    if user_info.get('email') == test_payload['email']:
        print(f"✅ Email extraction successful")
    else:
        print(f"❌ Email extraction failed: expected {test_payload['email']}, got {user_info.get('email')}")
    
    if user_info.get('user_id') == test_payload['sub']:
        print(f"✅ User ID extraction successful")
    else:
        print(f"❌ User ID extraction failed: expected {test_payload['sub']}, got {user_info.get('user_id')}")
    
    if user_info.get('name') == test_payload['name']:
        print(f"✅ Name extraction successful")
    else:
        print(f"❌ Name extraction failed: expected {test_payload['name']}, got {user_info.get('name')}")

    # Test with invalid tokens
    print(f"\n--- Testing error cases ---")
    
    # Test with empty token
    result = extract_user_info_from_token("")
    print(f"Empty token result: {result}")
    
    # Test with malformed token
    result = extract_user_info_from_token("Bearer invalid.token")
    print(f"Malformed token result: {result}")
    
    # Test without Bearer prefix
    result = extract_user_info_from_token(test_jwt)
    print(f"No Bearer prefix result: {result}")

if __name__ == "__main__":
    test_jwt_extraction()
