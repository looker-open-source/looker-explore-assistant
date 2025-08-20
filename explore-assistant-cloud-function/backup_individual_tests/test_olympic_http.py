#!/usr/bin/env python3
"""
Test Olympic Migration MCP tools via HTTP API
"""

import requests
import json

# Test server endpoint
BASE_URL = "http://localhost:8001"

def test_olympic_migration_via_http():
    """Test Olympic migration tools via HTTP API"""
    
    print("Testing Olympic Migration Tools via HTTP API...")
    
    # Test headers (using placeholder auth for testing)
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer test-token"
    }
    
    # Test 1: Check migration status
    print("\n1. Testing check_migration_status via HTTP...")
    try:
        payload = {
            "tool_name": "check_migration_status",
            "arguments": {},
            "user_email": "test@example.com"
        }
        
        response = requests.post(BASE_URL, json=payload, headers=headers)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Response: {json.dumps(result, indent=2)}")
        else:
            print(f"✗ Error: {response.text}")
    
    except Exception as e:
        print(f"✗ Request failed: {e}")
    
    # Test 2: Get system status
    print("\n2. Testing get_system_status via HTTP...")
    try:
        payload = {
            "tool_name": "get_system_status",
            "arguments": {},
            "user_email": "test@example.com"
        }
        
        response = requests.post(BASE_URL, json=payload, headers=headers)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Response: {json.dumps(result, indent=2)}")
        else:
            print(f"✗ Error: {response.text}")
    
    except Exception as e:
        print(f"✗ Request failed: {e}")
    
    print("\nHTTP API Test Complete!")

if __name__ == "__main__":
    test_olympic_migration_via_http()
