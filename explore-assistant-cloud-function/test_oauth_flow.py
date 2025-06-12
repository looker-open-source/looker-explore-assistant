#!/usr/bin/env python3

import requests
import json
import sys
import os

def test_oauth_flow(oauth_token=None):
    """Test the MCP server with OAuth authentication"""
    base_url = "https://looker-explore-assistant-mcp-rchq2jmtba-uc.a.run.app"
        
    print("Testing MCP Server with OAuth Token...")
    print(f"Base URL: {base_url}")
    print()
    
    # Test 1: Health check
    print("1. Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            print("✅ Health check passed")
            health_data = response.json()
            print(f"   Service: {health_data.get('service')}")
            print(f"   Project: {health_data.get('project')}")
            print(f"   Model: {health_data.get('model')}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False
    
    print()
    
    # Get OAuth token
    if not oauth_token:
        oauth_token = input("Enter your OAuth token (or press Enter to skip OAuth test): ").strip()
    
    if not oauth_token:
        print("⚠️  No OAuth token provided. Testing with fake token...")
        oauth_token = "fake_token_for_test"
        test_mode = True
    else:
        print("🔑 Using provided OAuth token for real API test...")
        test_mode = False
    
    # Test 2: Main endpoint with OAuth
    print("2. Testing main endpoint with OAuth...")
    try:
        # Sample golden queries for testing
        sample_golden_queries = {
            "order_items": [
                {
                    "input": "Show me total sales by product category",
                    "output": "fields=products.category,order_items.total_sale_price&sorts=order_items.total_sale_price desc"
                },
                {
                    "input": "What are the top selling products this year?",
                    "output": "fields=products.name,order_items.total_sale_price&filters={\"order_items.created_date\":\"this year\"}&sorts=order_items.total_sale_price desc&limit=10"
                }
            ],
            "users": [
                {
                    "input": "How many users signed up each month?",
                    "output": "fields=users.created_month,users.count&sorts=users.created_month desc"
                }
            ]
        }
        
        # Sample semantic models
        sample_semantic_models = {
            "order_items": {
                "dimensions": [
                    {"name": "products.category", "type": "string", "label": "Product Category"},
                    {"name": "order_items.created_date", "type": "date", "label": "Order Date"}
                ],
                "measures": [
                    {"name": "order_items.total_sale_price", "type": "number", "label": "Total Sales"},
                    {"name": "order_items.count", "type": "number", "label": "Number of Orders"}
                ]
            },
            "users": {
                "dimensions": [
                    {"name": "users.created_month", "type": "date", "label": "Created Month"},
                    {"name": "users.country", "type": "string", "label": "Country"}
                ],
                "measures": [
                    {"name": "users.count", "type": "number", "label": "Number of Users"}
                ]
            }
        }
        
        test_payload = {
            "prompt": "Show me total sales by product category for this year",
            "conversation_id": "test_oauth_123",
            "current_explore": {},
            "golden_queries": sample_golden_queries,
            "semantic_models": sample_semantic_models,
            "model_name": "gemini-2.0-flash-001",
            "test_mode": test_mode
        }
        
        headers = {
            "Authorization": f"Bearer {oauth_token}",
            "Content-Type": "application/json"
        }
        
        print(f"   Sending request with payload keys: {list(test_payload.keys())}")
        print(f"   Using {'test mode' if test_mode else 'real OAuth token'}")
        
        # Debug: Print first few characters of token
        token_preview = oauth_token[:20] + "..." if len(oauth_token) > 20 else oauth_token
        print(f"   Token preview: {token_preview}")
        
        response = requests.post(f"{base_url}/", json=test_payload, headers=headers, timeout=60)
        
        print(f"   Response status: {response.status_code}")
        print(f"   Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("✅ OAuth endpoint test passed")
            result_data = response.json()
            print(f"   Response type: {result_data.get('message_type', 'unknown')}")
            
            if test_mode:
                print(f"   Status: {result_data.get('status')}")
                print(f"   Message: {result_data.get('message')}")
            else:
                # Real API response
                if 'explore_params' in result_data:
                    explore_params = result_data['explore_params']
                    print(f"   Generated fields: {explore_params.get('fields', [])}")
                    print(f"   Generated filters: {explore_params.get('filters', {})}")
                    print(f"   Explore key: {result_data.get('explore_key', 'N/A')}")
                
                if 'summary' in result_data:
                    print(f"   Summary: {result_data['summary']}")
                
                if 'error' in result_data:
                    print(f"   Note: {result_data['error']}")
                else:
                    print("   🎉 Real OAuth token validated successfully!")
                    print("   Your token has the correct scopes and permissions.")
                    
        elif response.status_code == 401:
            print(f"❌ OAuth authentication failed: {response.status_code}")
            print("   This usually means:")
            print("   - Token is expired or invalid")
            print("   - Token doesn't have required scopes")
            print("   - Token validation endpoint is not working")
            print(f"   Response: {response.text}")
            return False
        else:
            print(f"❌ OAuth test failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out (60s). The server might be processing or having issues.")
        return False
    except Exception as e:
        print(f"❌ OAuth test error: {e}")
        return False
    
    print()
    print("🎉 OAuth flow test completed!")
    print()
    print("Next steps:")
    print("1. If using real OAuth token, verify your token has the required scopes:")
    print("   - https://www.googleapis.com/auth/cloud-platform")
    print("   - email scope for user identification")
    print("2. Make sure your GCP project has Vertex AI API enabled")
    print("3. Verify the PROJECT environment variable matches your GCP project")
    
    return True

def get_oauth_token_instructions():
    """Print instructions for getting an OAuth token"""
    print("=" * 60)
    print("HOW TO GET AN OAUTH TOKEN FOR TESTING")
    print("=" * 60)
    print()
    print("Option 1: Using gcloud CLI (easiest)")
    print("1. Run: gcloud auth application-default print-access-token")
    print("   This should include both cloud-platform and email scopes")
    print()
    print("Option 2: Using gcloud with user credentials (recommended)")
    print("1. Run: gcloud auth login --enable-gdrive-access")
    print("2. Run: gcloud auth print-access-token")
    print()
    print("Option 3: Using OAuth Playground")
    print("1. Go to: https://developers.google.com/oauthplayground/")
    print("2. In 'Step 1', add these scopes:")
    print("   - https://www.googleapis.com/auth/cloud-platform")
    print("   - https://www.googleapis.com/auth/userinfo.email")
    print("3. Click 'Authorize APIs'")
    print("4. Complete the authorization flow")
    print("5. In 'Step 2', click 'Exchange authorization code for tokens'")
    print("6. Copy the 'Access token' from the response")
    print()
    print("Option 4: Manual gcloud with specific scopes")
    print("1. Run: gcloud auth login --scopes=https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/userinfo.email")
    print("2. Run: gcloud auth print-access-token")
    print()
    print("Required scopes:")
    print("- https://www.googleapis.com/auth/cloud-platform (for Vertex AI)")
    print("- https://www.googleapis.com/auth/userinfo.email (for user identification)")
    print()
    print("Note: The token must have BOTH scopes to work properly!")
    print()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--help" or sys.argv[1] == "-h":
            get_oauth_token_instructions()
            sys.exit(0)
        else:
            # Use token from command line argument
            oauth_token = sys.argv[1]
            test_oauth_flow(oauth_token)
    else:
        # Interactive mode
        print("OAuth Flow Tester for MCP Server")
        print("Type --help for instructions on getting an OAuth token")
        print()
        test_oauth_flow()
