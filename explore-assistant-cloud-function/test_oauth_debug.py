#!/usr/bin/env python3
"""
Debug test script for MCP server OAuth
This will test step by step what the server is doing with the token
"""

import json
import requests
import base64
import time
import sys

# Configuration
MCP_SERVER_URL = "https://looker-explore-assistant-mcp-rchq2jmtba-uc.a.run.app"

def test_token_extraction_locally(token):
    """Test the same token extraction logic as the server"""
    print("🔍 Testing token extraction locally (mimicking server logic)...")
    
    try:
        # Remove 'Bearer ' prefix if present
        if token.lower().startswith('bearer '):
            token = token[7:]
        
        # Remove any whitespace
        token = token.strip()
        
        # Split JWT into parts
        token_parts = token.split('.')
        if len(token_parts) != 3:
            print(f"❌ Invalid JWT format: expected 3 parts, got {len(token_parts)}")
            return None
        
        print(f"✅ JWT has correct format: 3 parts")
        
        # Decode the payload (second part) to extract email
        payload_data = token_parts[1]
        # Add padding if needed for base64 decoding
        payload_data += '=' * (4 - len(payload_data) % 4)
        
        try:
            payload_json = base64.urlsafe_b64decode(payload_data).decode('utf-8')
            payload = json.loads(payload_json)
            
            email = payload.get('email')
            if email:
                print(f"✅ Extracted email: {email}")
                print(f"✅ Token extraction should work on server")
                return email
            else:
                print("❌ No email found in token payload")
                return None
                
        except Exception as e:
            print(f"❌ Failed to decode JWT payload: {e}")
            return None
        
    except Exception as e:
        print(f"❌ Error extracting email from token: {e}")
        return None

def test_minimal_request(token):
    """Test with the most minimal request possible"""
    print("\n🧪 Testing with minimal request...")
    
    # Clean the token 
    clean_token = token
    if token.lower().startswith('bearer '):
        clean_token = token[7:].strip()
    
    minimal_payload = {
        "test_mode": True
    }
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {clean_token}',
        'Accept': 'application/json'
    }
    
    try:
        print(f"Sending minimal test request...")
        response = requests.post(
            MCP_SERVER_URL,
            headers=headers,
            json=minimal_payload,
            timeout=30
        )
        
        print(f"Status: {response.status_code}")
        
        if response.ok:
            try:
                data = response.json()
                print(f"✅ Success: {json.dumps(data, indent=2)}")
                return True
            except:
                print(f"✅ Success (text): {response.text}")
                return True
        else:
            print(f"❌ Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False

def test_with_different_auth_formats(base_token):
    """Test different ways of sending the auth header"""
    print("\n🔄 Testing different Authorization header formats...")
    
    test_formats = [
        ("Bearer + token", f"Bearer {base_token}"),
        ("bearer + token (lowercase)", f"bearer {base_token}"),
        ("BEARER + token (uppercase)", f"BEARER {base_token}"),
        ("Just token", base_token),
    ]
    
    minimal_payload = {"test_mode": True}
    
    for format_name, auth_value in test_formats:
        print(f"\n🧪 Testing format: {format_name}")
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': auth_value,
            'Accept': 'application/json'
        }
        
        try:
            response = requests.post(
                MCP_SERVER_URL,
                headers=headers,
                json=minimal_payload,
                timeout=10
            )
            
            print(f"  Status: {response.status_code}")
            if response.ok:
                print(f"  ✅ SUCCESS with {format_name}")
                return auth_value
            else:
                print(f"  ❌ Failed: {response.text}")
                
        except Exception as e:
            print(f"  ❌ Request failed: {e}")
    
    return None

def test_token_with_curl(token):
    """Generate curl command for manual testing"""
    print(f"\n🌐 Curl command for manual testing:")
    print(f"curl -X POST '{MCP_SERVER_URL}' \\")
    print(f"  -H 'Content-Type: application/json' \\")
    print(f"  -H 'Authorization: Bearer {token}' \\")
    print(f"  -d '{{\"test_mode\": true}}' \\")
    print(f"  -v")

def main():
    # Default token from your script
    default_token = "eyJhbGciOiJSUzI1NiIsImtpZCI6Ijg4MjUwM2E1ZmQ1NmU5ZjczNGRmYmE1YzUwZDdiZjQ4ZGIyODRhZTkiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2FjY291bnRzLmdvb2dsZS5jb20iLCJhenAiOiI3MzAxOTIxNzU5NzEtdmg3ZTl1aGhpcmFlMzU5NDNycGNvbjkzZnFwOGJob28uYXBwcy5nb29nbGV1c2VyY29udGVudC5jb20iLCJhdWQiOiI3MzAxOTIxNzU5NzEtdmg3ZTl1aGhpcmFlMzU5NDNycGNvbjkzZnFwOGJob28uYXBwcy5nb29nbGV1c2VyY29udGVudC5jb20iLCJzdWIiOiIxMTMzNTUyNDQ1MjI3MzkxMzQ1NjciLCJoZCI6ImJ5dGVjb2RlLmlvIiwiZW1haWwiOiJjb2xpbi5yb3kuZWhyaUBieXRlY29kZS5pbyIsImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJub25jZSI6IjNsdTl1aDVpYjIyIiwibmJmIjoxNzUxNTU0NzQ3LCJuYW1lIjoiQ29saW4gUm95LUVocmkiLCJwaWN0dXJlIjoiaHR0cHM6Ly9saDMuZ29vZ2xldXNlcmNvbnRlbnQuY29tL2EvQUNnOG9jS25ja1F5N3lPbXFVckRIM2JENTQ2ZnhZNzlpWU9iNXBCQWpDQndYbXVwQXhCOVJNWT1zOTYtYyIsImdpdmVuX25hbWUiOiJDb2xpbiIsImZhbWlseV9uYW1lIjoiUm95LUVocmkiLCJpYXQiOjE3NTE1NTUwNDcsImV4cCI6MTc1MTU1ODY0NywianRpIjoiM2I0M2IyM2VlZDhiZWMzNjcxY2ZjZmRjYWE0NjNjMTI0MTZlYjkzOSJ9.LEc_lNzI0oI86SdL5Ss6gIj-rESeB-7P6mhj0BbG4z-uE1WvN6j1E9t7hKLQDQUy_StHPljT35iTXAWy_i7MsH25wg-Aq8_WOc1llZEiM_JioigBXHyeFaXO6XXd3mi6TaVZldkNybRkU4sRAkeEuqNQbTA3yBVxdXUc871rxed73xJlw6e4YRBaK1hA3gm6EXj0Eeo2eJsH85NpFLcO1sxHJ8Im0LKnR6YjLYbcxz6eqf5cID7CqMaqngJRIcB53oZArGEQ2b6Tr9CCRNLQoCBUjtZpA19TakzuIdyWxImaAuf2qZr4gDSKNJmh3cQjtCtPjzBSPQ5OTR0eD7XTlA"
    
    if len(sys.argv) > 1:
        token = sys.argv[1]
        if token.lower() == 'default':
            token = default_token
    else:
        token = default_token
        print("Using default token")
    
    print("🔐 MCP Server OAuth Debug Test")
    print("=" * 50)
    
    # Step 1: Test token extraction locally
    extracted_email = test_token_extraction_locally(token)
    
    if not extracted_email:
        print("❌ Token extraction failed locally - server will also fail")
        return
    
    # Step 2: Test minimal request
    success = test_minimal_request(token)
    
    if success:
        print("✅ Test successful! Your token works with the server.")
        return
    
    # Step 3: Try different auth header formats
    print("❌ Basic test failed, trying different formats...")
    working_format = test_with_different_auth_formats(token)
    
    if working_format:
        print(f"✅ Found working format: {working_format}")
    else:
        print("❌ No working format found")
        
        # Step 4: Generate curl command for manual testing
        test_token_with_curl(token)
        
        print("\n💡 Troubleshooting suggestions:")
        print("1. Check if your token has expired")
        print("2. Verify the server is expecting exactly this OAuth client ID")
        print("3. Check server logs for more detailed error messages")
        print("4. Try the curl command above manually")

if __name__ == "__main__":
    main()
