#!/usr/bin/env python3
"""
Test script for MCP server with proper OAuth token
This script will help you obtain and test an ID token with the correct scope and response_type
matching the configuration used in useAutoOAuth.ts
"""

import os
import json
import time
import base64
import requests
import webbrowser
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading
import secrets

# Configuration - Update these values
GOOGLE_CLIENT_ID = "730192175971-vh7e9uhhirae35943rpcon93fqp8bhoo.apps.googleusercontent.com"  # Set your Google OAuth Client ID here
MCP_SERVER_URL = "https://looker-explore-assistant-mcp-rchq2jmtba-uc.a.run.app"

# OAuth configuration matching useAutoOAuth.ts
GOOGLE_SCOPES = "openid email profile"
REDIRECT_URI = "http://localhost:8888/callback"
RESPONSE_TYPE = "id_token"

class CallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler for OAuth callback"""
    
    def do_GET(self):
        if self.path.startswith('/callback'):
            # Parse the fragment (everything after #) from the URL
            # Note: The fragment is typically handled by JavaScript, but we'll try to capture it
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            # Send HTML that will extract the token from the URL fragment
            html_response = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>OAuth Callback</title>
            </head>
            <body>
                <h1>Processing OAuth Response...</h1>
                <p id="status">Extracting token...</p>
                <script>
                    // Extract token from URL fragment
                    const fragment = window.location.hash.substring(1);
                    const params = new URLSearchParams(fragment);
                    const idToken = params.get('id_token');
                    const error = params.get('error');
                    
                    if (idToken) {
                        document.getElementById('status').innerHTML = 
                            '<p style="color: green;">✅ ID Token received successfully!</p>' +
                            '<p>Token length: ' + idToken.length + '</p>' +
                            '<p>You can now close this window and check your terminal.</p>';
                        
                        // Send token to Python server via a POST request
                        fetch('/token', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({id_token: idToken})
                        }).catch(e => console.log('Failed to send token to server:', e));
                        
                    } else if (error) {
                        document.getElementById('status').innerHTML = 
                            '<p style="color: red;">❌ OAuth Error: ' + error + '</p>';
                    } else {
                        document.getElementById('status').innerHTML = 
                            '<p style="color: orange;">⚠️ No token found in response</p>';
                    }
                </script>
            </body>
            </html>
            """
            self.wfile.write(html_response.encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        if self.path == '/token':
            # Receive the token from JavaScript
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode())
                token = data.get('id_token')
                if token:
                    # Store the token globally
                    global received_token
                    received_token = token
                    print(f"\n✅ ID Token received! Length: {len(token)}")
                    
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"status": "ok"}')
            except Exception as e:
                print(f"Error processing token: {e}")
                self.send_response(500)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress default HTTP server logging
        pass

def start_callback_server():
    """Start a local HTTP server to handle OAuth callback"""
    global httpd
    server_address = ('localhost', 8888)
    httpd = HTTPServer(server_address, CallbackHandler)
    print(f"🌐 Starting callback server on {REDIRECT_URI}")
    httpd.serve_forever()

def get_oauth_url():
    """Generate OAuth URL matching useAutoOAuth.ts configuration"""
    nonce = secrets.token_urlsafe(16)  # Generate random nonce
    state = secrets.token_urlsafe(16)  # Generate random state for security
    
    params = {
        'client_id': GOOGLE_CLIENT_ID,
        'response_type': RESPONSE_TYPE,
        'scope': GOOGLE_SCOPES,
        'redirect_uri': REDIRECT_URI,
        'nonce': nonce,
        'state': state
    }
    
    base_url = 'https://accounts.google.com/o/oauth2/v2/auth'
    oauth_url = f"{base_url}?{urllib.parse.urlencode(params)}"
    
    print(f"📋 OAuth Parameters:")
    for key, value in params.items():
        print(f"  {key}: {value}")
    
    return oauth_url, nonce, state

def decode_token_payload(token):
    """Decode JWT payload for inspection"""
    try:
        # Split token into parts
        parts = token.split('.')
        if len(parts) != 3:
            print(f"❌ Invalid JWT format: expected 3 parts, got {len(parts)}")
            return None
        
        # Decode payload (second part)
        payload_data = parts[1]
        # Add padding if needed
        payload_data += '=' * (4 - len(payload_data) % 4)
        
        decoded_payload = base64.urlsafe_b64decode(payload_data)
        payload_json = json.loads(decoded_payload)
        
        return payload_json
    except Exception as e:
        print(f"❌ Error decoding token: {e}")
        return None

def test_mcp_server(token):
    """Test the MCP server with the obtained token"""
    print(f"\n🧪 Testing MCP server at: {MCP_SERVER_URL}")
    
    # Test payload matching the format expected by the server
    test_payload = {
        "prompt": "Show me sales data",
        "conversation_id": "test-conversation-123",
        "prompt_history": ["Show me sales data"],
        "thread_messages": [],
        "current_explore": {
            "modelName": "ecommerce",
            "exploreName": "order_items"
        },
        "golden_queries": {
            "exploreSamples": {
                "order_items": {
                    "examples": [
                        {
                            "prompt": "Show me total sales",
                            "explore_params": {
                                "model": "ecommerce",
                                "explore": "order_items",
                                "measures": ["order_items.total_sale_price"],
                                "limit": 100
                            }
                        }
                    ]
                }
            }
        },
        "semantic_models": {},
        "model_name": "ecommerce",
        "test_mode": True
    }
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json'
    }
    
    try:
        print("🚀 Sending request to MCP server...")
        print(f"📤 Request URL: {MCP_SERVER_URL}")
        print(f"📤 Request headers: {headers}")
        print(f"📤 Payload keys: {list(test_payload.keys())}")
        
        response = requests.post(
            MCP_SERVER_URL,
            headers=headers,
            json=test_payload,
            timeout=30
        )
        
        print(f"\n📥 Response received:")
        print(f"  Status Code: {response.status_code}")
        print(f"  Headers: {dict(response.headers)}")
        
        if response.ok:
            try:
                response_json = response.json()
                print(f"  ✅ Success! Response: {json.dumps(response_json, indent=2)}")
                return True
            except json.JSONDecodeError:
                print(f"  ✅ Success! Response (text): {response.text}")
                return True
        else:
            print(f"  ❌ Error: {response.status_code}")
            print(f"  ❌ Response text: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False

def main():
    """Main function to orchestrate OAuth flow and testing"""
    global received_token, httpd
    received_token = None
    
    print("🔐 MCP Server OAuth Test Script")
    print("=" * 50)
    
    # Validate configuration
    if not GOOGLE_CLIENT_ID:
        print("❌ Error: GOOGLE_CLIENT_ID not set!")
        print("Please update the GOOGLE_CLIENT_ID variable in this script.")
        return
    
    print(f"📋 Configuration:")
    print(f"  Google Client ID: {GOOGLE_CLIENT_ID}")
    print(f"  MCP Server URL: {MCP_SERVER_URL}")
    print(f"  Scopes: {GOOGLE_SCOPES}")
    print(f"  Response Type: {RESPONSE_TYPE}")
    print(f"  Redirect URI: {REDIRECT_URI}")
    
    # Generate OAuth URL
    oauth_url, nonce, state = get_oauth_url()
    print(f"\n🔗 OAuth URL generated:")
    print(f"  {oauth_url}")
    
    # Start callback server in a separate thread
    server_thread = threading.Thread(target=start_callback_server, daemon=True)
    server_thread.start()
    
    # Wait a moment for server to start
    time.sleep(1)
    
    print(f"\n🌐 Opening browser for OAuth flow...")
    print(f"If the browser doesn't open automatically, copy and paste this URL:")
    print(f"  {oauth_url}")
    
    # Open browser
    try:
        webbrowser.open(oauth_url)
    except Exception as e:
        print(f"⚠️ Could not open browser automatically: {e}")
    
    # Wait for token
    print(f"\n⏳ Waiting for OAuth callback...")
    print(f"Please complete the OAuth flow in your browser.")
    
    # Wait up to 2 minutes for the token
    timeout = 120
    start_time = time.time()
    
    while received_token is None and (time.time() - start_time) < timeout:
        time.sleep(1)
        
    if received_token is None:
        print(f"❌ Timeout: No token received after {timeout} seconds")
        print(f"Please try again or check your OAuth configuration.")
        return
    
    # Shutdown the callback server
    try:
        httpd.shutdown()
    except:
        pass
    
    # Analyze the token
    print(f"\n🔍 Token Analysis:")
    print(f"  Token length: {len(received_token)}")
    print(f"  Token preview: {received_token[:50]}...{received_token[-20:]}")
    
    payload = decode_token_payload(received_token)
    if payload:
        print(f"  ✅ Token decoded successfully")
        print(f"  Email: {payload.get('email', 'Not found')}")
        print(f"  Audience: {payload.get('aud', 'Not found')}")
        print(f"  Issuer: {payload.get('iss', 'Not found')}")
        print(f"  Expires: {time.ctime(payload.get('exp', 0))}")
        print(f"  Issued: {time.ctime(payload.get('iat', 0))}")
    else:
        print(f"  ❌ Could not decode token")
    
    # Test the MCP server
    success = test_mcp_server(received_token)
    
    if success:
        print(f"\n🎉 Test completed successfully!")
        print(f"Your MCP server is working correctly with OAuth tokens.")
    else:
        print(f"\n❌ Test failed!")
        print(f"Check the server logs for more details.")
    
    print(f"\n📋 Your token for manual testing:")
    print(f"{received_token}")

if __name__ == "__main__":
    main()
