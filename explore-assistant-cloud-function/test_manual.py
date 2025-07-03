#!/usr/bin/env python3
"""
Quick manual test script for MCP server
Use this if you already have a valid ID token
"""

import json
import requests
import sys

# Configuration
MCP_SERVER_URL = "https://looker-explore-assistant-mcp-rchq2jmtba-uc.a.run.app"

def analyze_token(token):
    """Analyze JWT token structure and content"""
    import base64
    import time
    
    try:
        # Remove Bearer prefix if present
        if token.lower().startswith('bearer '):
            token = token[7:].strip()
            
        parts = token.split('.')
        print(f"🔍 Token Analysis:")
        print(f"  Parts: {len(parts)} (should be 3 for JWT)")
        print(f"  Length: {len(token)}")
        print(f"  First 50 chars: {token[:50]}...")
        print(f"  Last 20 chars: ...{token[-20:]}")
        
        if len(parts) == 3:
            # Decode header
            try:
                header_data = parts[0] + '=' * (4 - len(parts[0]) % 4)
                header = json.loads(base64.urlsafe_b64decode(header_data))
                print(f"  Header: {header}")
            except Exception as e:
                print(f"  Header decode error: {e}")
            
            # Decode payload
            try:
                payload_data = parts[1] + '=' * (4 - len(parts[1]) % 4)
                payload = json.loads(base64.urlsafe_b64decode(payload_data))
                print(f"  Email: {payload.get('email', 'Not found')}")
                print(f"  Audience: {payload.get('aud', 'Not found')}")
                print(f"  Issuer: {payload.get('iss', 'Not found')}")
                print(f"  Subject: {payload.get('sub', 'Not found')}")
                
                # Check expiration
                exp = payload.get('exp')
                if exp:
                    exp_time = time.ctime(exp)
                    now = time.time()
                    expired = exp < now
                    print(f"  Expires: {exp_time} ({'EXPIRED' if expired else 'VALID'})")
                    
                iat = payload.get('iat')
                if iat:
                    print(f"  Issued: {time.ctime(iat)}")
                    
                return payload
                
            except Exception as e:
                print(f"  Payload decode error: {e}")
        
        return None
        
    except Exception as e:
        print(f"  Token analysis error: {e}")
        return None

def test_with_token(token):
    """Test MCP server with provided token"""
    
    defaultToken = "eyJhbGciOiJSUzI1NiIsImtpZCI6Ijg4MjUwM2E1ZmQ1NmU5ZjczNGRmYmE1YzUwZDdiZjQ4ZGIyODRhZTkiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2FjY291bnRzLmdvb2dsZS5jb20iLCJhenAiOiI3MzAxOTIxNzU5NzEtdmg3ZTl1aGhpcmFlMzU5NDNycGNvbjkzZnFwOGJob28uYXBwcy5nb29nbGV1c2VyY29udGVudC5jb20iLCJhdWQiOiI3MzAxOTIxNzU5NzEtdmg3ZTl1aGhpcmFlMzU5NDNycGNvbjkzZnFwOGJob28uYXBwcy5nb29nbGV1c2VyY29udGVudC5jb20iLCJzdWIiOiIxMTMzNTUyNDQ1MjI3MzkxMzQ1NjciLCJoZCI6ImJ5dGVjb2RlLmlvIiwiZW1haWwiOiJjb2xpbi5yb3kuZWhyaUBieXRlY29kZS5pbyIsImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJub25jZSI6InJxbHY4d2QyeG4iLCJuYmYiOjE3NTE1NTc4NDIsIm5hbWUiOiJDb2xpbiBSb3ktRWhyaSIsInBpY3R1cmUiOiJodHRwczovL2xoMy5nb29nbGV1c2VyY29udGVudC5jb20vYS9BQ2c4b2NLbmNrUXk3eU9tcVVyREgzYlRFNDZmeFk3OWlZT2I1cEJBakNCd1htdXBBeEI5Uk1ZPXM5Ni1jIiwiZ2l2ZW5fbmFtZSI6IkNvbGluIiwiZmFtaWx5X25hbWUiOiJSb3ktRWhyaSIsImlhdCI6MTc1MTU1ODE0MiwiZXhwIjoxNzUxNTYxNzQyLCJqdGkiOiJmNzQ2ZjAyMDE2OGU5NGQyY2ZlZGM1NzFjYzNmM2UyZjc0Mjg5Yjg1In0.Q8ktQojnPRu5Kowz8gtD6e991z82SArHdd58Xpr1CUygoicUt7W0hKcH_K6a2mfNhXYcd555heyBprBlzYFR0HVTYgqjs5TTb6v-kHlB96rHPGMg55N1Jch3mWFfRLGQRAWLTcJJ5QEkSbFNgezP9m049JoUauEpc5Jpckv-xYhUkuFc2rDp8m8s8QM_c_jXcx4gE_ON1YTFtCJkcq8ghX4KlHoCgF4ldRQDzR-CaHeqL4P8_ulK5FpnbYaRK6si-9CNwlNlZNmH0hbimmOzZjvvahE4ssV_F3MGgdJ9CcDA5_S8Oo8b6RdMQrTy-l_dw8pvkYEP-M61m4GLyxg1SQ"
    # Use default token if "default" is passed
    if token.lower() == 'default':
        token = defaultToken
        print("🔄 Using default token from script")
    
    # Analyze the token first
    payload = analyze_token(token)

    # Health check first
    print("🏥 Testing health endpoint...")
    try:
        health_response = requests.get(f"{MCP_SERVER_URL}/health", timeout=10)
        print(f"Health check: {health_response.status_code}")
        if health_response.ok:
            print(f"Health response: {health_response.json()}")
        else:
            print(f"Health error: {health_response.text}")
    except Exception as e:
        print(f"Health check failed: {e}")
    
    # Test main endpoint
    print(f"\n🧪 Testing main endpoint with token...")
    
    test_payload = {
        "prompt": "Show me total sales by region",
        "conversation_id": "test-123",
        "prompt_history": ["Show me total sales by region"],
        "thread_messages": [],
        "current_explore": {
            "modelName": "ecommerce", 
            "exploreName": "order_items"
        },
        "golden_queries": {
            "exploreSamples": {
                "order_items": {
                    "examples": []
                }
            }
        },
        "semantic_models": {},
        "model_name": "ecommerce",
        "test_mode": True
    }
    
    # Clean the token (remove Bearer prefix if present)
    clean_token = token
    if token.lower().startswith('bearer '):
        clean_token = token[7:].strip()
        print("🧹 Removed 'Bearer ' prefix from token")
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {clean_token}',
        'Accept': 'application/json'
    }
    
    try:
        print(f"Sending POST request to {MCP_SERVER_URL}")
        response = requests.post(
            MCP_SERVER_URL,
            headers=headers,
            json=test_payload,
            timeout=30
        )
        
        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        if response.ok:
            try:
                data = response.json()
                print(f"✅ Success: {json.dumps(data, indent=2)}")
            except:
                print(f"✅ Success (text): {response.text}")
        else:
            print(f"❌ Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

def main():
    if len(sys.argv) == 1:
        # No arguments, use default token
        print("No token provided, using default token")
        test_with_token("default")
    elif len(sys.argv) == 2:
        token = sys.argv[1]
        if token.lower() == 'default':
            print("Using default token from script")
        else:
            print(f"Testing with provided token (length: {len(token)})")
        test_with_token(token)
    else:
        print("Usage: python test_manual.py [ID_TOKEN|default]")
        print("Examples:")
        print("  python test_manual.py default")
        print("  python test_manual.py eyJhbGciOiJSUzI1NiIs...")
        print("  python test_manual.py  # uses default token")
        sys.exit(1)

if __name__ == "__main__":
    main()
