#!/usr/bin/env python3

import requests
import json

# Test the local MCP server
def test_mcp_server():
    base_url = "http://localhost:8001"
    
    print("Testing MCP Server...")
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
    
    # Test 2: Test mode (no actual Vertex AI call)
    print("2. Testing main endpoint in test mode...")
    try:
        test_payload = {
            "prompt": "test prompt",
            "conversation_id": "test_123",
            "current_explore": {},
            "golden_queries": {},
            "semantic_models": {},
            "model_name": "test_model",
            "test_mode": True
        }
        
        headers = {
            "Authorization": "Bearer fake_token_for_test",
            "Content-Type": "application/json"
        }
        
        response = requests.post(f"{base_url}/", json=test_payload, headers=headers)
        
        if response.status_code == 200:
            print("✅ Test mode endpoint passed")
            test_data = response.json()
            print(f"   Status: {test_data.get('status')}")
            print(f"   Message: {test_data.get('message')}")
        else:
            print(f"❌ Test mode failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Test mode error: {e}")
        return False
    
    print()
    print("🎉 All tests passed! The MCP server is ready for use.")
    print()
    print("Next steps:")
    print("1. Set your Cloud Run service URL in the extension to: http://localhost:8001")
    print("2. Make sure you have valid OAuth tokens in your extension")
    print("3. Set the PROJECT environment variable to your GCP project ID")
    
    return True

if __name__ == "__main__":
    test_mcp_server()
