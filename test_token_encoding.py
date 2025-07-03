#!/usr/bin/env python3
"""
Test script to verify JWT token validation logic
"""

import jwt
import json
import base64
import logging

logging.basicConfig(level=logging.INFO)

def test_jwt_validation(token):
    """Test the same JWT validation logic as the backend"""
    print(f"\n=== Testing JWT Token ===")
    print(f"Token length: {len(token)}")
    print(f"Token preview: {token[:50]}...")
    
    # Remove Bearer prefix if present
    if token.lower().startswith('bearer '):
        token = token[7:]
    
    token = token.strip()
    
    # Check for encoding issues
    if '\\x' in token:
        print("ERROR: Token contains \\x sequences - likely double-encoded")
        return False
        
    if '\x' in token:
        print("ERROR: Token contains null bytes")
        return False
    
    # Validate JWT structure
    token_parts = token.split('.')
    print(f"Token parts: {len(token_parts)} (should be 3)")
    
    if len(token_parts) != 3:
        print(f"ERROR: Invalid JWT format - expected 3 parts, got {len(token_parts)}")
        return False
    
    # Validate each part
    valid_jwt_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_=')
    for i, part in enumerate(token_parts):
        if not part:
            print(f"ERROR: Part {i+1} is empty")
            return False
        
        invalid_chars = set(part) - valid_jwt_chars
        if invalid_chars:
            print(f"ERROR: Part {i+1} contains invalid characters: {invalid_chars}")
            return False
        
        print(f"Part {i+1} length: {len(part)} - valid")
    
    # Try to decode header
    try:
        header_data = token_parts[0]
        # Add padding if needed
        header_data += '=' * (4 - len(header_data) % 4)
        header_json = base64.urlsafe_b64decode(header_data).decode('utf-8')
        header = json.loads(header_json)
        
        print(f"JWT header: {header}")
        
        if 'alg' not in header:
            print("ERROR: JWT header missing 'alg' field")
            return False
    except Exception as e:
        print(f"ERROR: Failed to decode JWT header: {e}")
        return False
    
    print("Token format validation: PASSED")
    return True

# Test with a sample JWT (you can replace this with an actual token for testing)
sample_jwt = "eyJhbGciOiJSUzI1NiIsImtpZCI6IjE2NzAyNzI2M2I4OWMzYzk4ZjE2YTgzMjkzMmE3MjU0OWNiMjBjODAiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJhY2NvdW50cy5nb29nbGUuY29tIiwiYXpwIjoiNTI5MTY1Nzg5NzkwLXNvYW5lNGZrNzNzdGFiaWVkN3NwdjBzbWQ3cmRmZGhkLmFwcHMuZ29vZ2xldXNlcmNvbnRlbnQuY29tIiwiYXVkIjoiNTI5MTY1Nzg5NzkwLXNvYW5lNGZrNzNzdGFiaWVkN3NwdjBzbWQ3cmRmZGhkLmFwcHMuZ29vZ2xldXNlcmNvbnRlbnQuY29tIiwic3ViIjoiMTE0Mzk0OTEyMTA3NDM3NDY2NzY1IiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiZW1haWxfdmVyaWZpZWQiOnRydWUsIm5vbmNlIjoiOGUzYWNlMzljOGM1YjE0OSIsIm5hbWUiOiJUZXN0IFVzZXIiLCJwaWN0dXJlIjoiaHR0cHM6Ly9saDMuZ29vZ2xldXNlcmNvbnRlbnQuY29tL2EtL0FPaDE0R2h4eWg0TWtKUkdxcXE1SUZxZGhTUUtyNXhGZWNNQUZLblpjUUxGMkE9czk2LWMiLCJnaXZlbl9uYW1lIjoiVGVzdCIsImZhbWlseV9uYW1lIjoiVXNlciIsImxvY2FsZSI6ImVuIiwiaWF0IjoxNjM5NTg0OTQwLCJleHAiOjE2Mzk1ODg1NDB9.sample_signature_here"

print("Testing JWT validation logic...")
test_jwt_validation(sample_jwt)

# Test with some problematic tokens
print("\n" + "="*50)
print("Testing problematic tokens...")

# Test with double-encoded token (common issue)
problematic_token = "Bearer%20eyJhbGciOiJSUzI1NiIs..."
print(f"\nTesting URL-encoded token: {test_jwt_validation(problematic_token)}")

# Test with token containing \\x sequences
corrupted_token = "eyJhbGciOiJSUzI1\\x20NiIs..."
print(f"\nTesting corrupted token: {test_jwt_validation(corrupted_token)}")

print("\n=== Test Complete ===")
