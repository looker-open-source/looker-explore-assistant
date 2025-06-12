#!/usr/bin/env python3

import requests
import json
import sys

def test_token_validation_only(oauth_token):
    """Test just the token validation part"""
    print("Testing OAuth token validation only...")
    print(f"Token preview: {oauth_token[:20]}...")
    print()
    
    # Test the token directly with Google's endpoint
    print("1. Testing token with Google's tokeninfo endpoint...")
    try:
        token_info_url = f"https://oauth2.googleapis.com/tokeninfo?access_token={oauth_token}"
        response = requests.get(token_info_url, timeout=10)
        
        print(f"   Status: {response.status_code}")
        
        if response.ok:
            token_info = response.json()
            print("✅ Token is valid with Google")
            print(f"   Email: {token_info.get('email', 'N/A')}")
            print(f"   Scopes: {token_info.get('scope', 'N/A')}")
            print(f"   Expires in: {token_info.get('expires_in', 'N/A')} seconds")
            
            # Check required scopes
            scopes = token_info.get('scope', '').split()
            required_scopes = [
                'https://www.googleapis.com/auth/cloud-platform',
                'https://www.googleapis.com/auth/userinfo.email'
            ]
            
            missing_scopes = []
            for required_scope in required_scopes:
                if required_scope not in scopes:
                    missing_scopes.append(required_scope)
            
            if missing_scopes:
                print(f"❌ Missing required scopes: {missing_scopes}")
                return False
            else:
                print("✅ Token has all required scopes")
        else:
            print(f"❌ Token validation failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error validating token: {e}")
        return False
    
    print()
    
    # Test minimal request to our server
    print("2. Testing minimal request to MCP server...")
    try:
        base_url = "http://localhost:8001"
        
        # Minimal test payload
        test_payload = {
            "test_mode": True,
            "prompt": "test"
        }
        
        headers = {
            "Authorization": f"Bearer {oauth_token}",
            "Content-Type": "application/json"
        }
        
        print("   Sending minimal test request...")
        response = requests.post(f"{base_url}/", json=test_payload, headers=headers, timeout=30)
        
        print(f"   Response status: {response.status_code}")
        print(f"   Response headers: {dict(response.headers)}")
        
        if response.ok:
            print("✅ MCP server accepted the token")
            result = response.json()
            print(f"   Response: {result}")
        else:
            print(f"❌ MCP server rejected request: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error testing MCP server: {e}")
        return False
    
    return True

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_token_only.py <oauth_token>")
        sys.exit(1)
    
    oauth_token = sys.argv[1]
    test_token_validation_only(oauth_token)
