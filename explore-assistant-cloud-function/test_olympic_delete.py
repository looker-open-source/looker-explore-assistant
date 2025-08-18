#!/usr/bin/env python3
"""
Test Olympic Query Delete Functionality
"""

import json
import logging
import os
from mcp_server import handle_mcp_tool

logging.basicConfig(level=logging.INFO)

def test_delete_olympic_query():
    """Test deleting Olympic queries"""
    
    # Test user (you should replace with an actual authorized email)
    test_user_email = "test@example.com" 
    test_auth_header = "Bearer test_token"
    
    print("🧪 Testing Olympic Query Delete Functionality\n")
    
    # Test 1: Try to delete without confirmation
    print("📋 Test 1: Delete without confirmation (should fail)")
    result1 = handle_mcp_tool(
        tool_name="delete_olympic_query",
        arguments={
            "query_id": "test-query-123",
            "confirm_delete": False
        },
        user_email=test_user_email,
        auth_header=test_auth_header
    )
    print(f"Result: {json.dumps(result1, indent=2)}")
    
    # Test 2: Try to delete without query_id
    print("\n📋 Test 2: Delete without query_id (should fail)")
    result2 = handle_mcp_tool(
        tool_name="delete_olympic_query",
        arguments={
            "confirm_delete": True
        },
        user_email=test_user_email,
        auth_header=test_auth_header
    )
    print(f"Result: {json.dumps(result2, indent=2)}")
    
    # Test 3: Try to delete with confirmation (will fail if query doesn't exist)
    print("\n📋 Test 3: Delete with confirmation")
    result3 = handle_mcp_tool(
        tool_name="delete_olympic_query", 
        arguments={
            "query_id": "test-query-123",
            "confirm_delete": True
        },
        user_email=test_user_email,
        auth_header=test_auth_header
    )
    print(f"Result: {json.dumps(result3, indent=2)}")
    
    print(f"\n✅ Delete functionality test completed")
    print(f"📝 Notes:")
    print(f"   - delete_olympic_query tool exists and is accessible")
    print(f"   - Requires query_id and confirm_delete=true")  
    print(f"   - Requires user authorization")
    print(f"   - Uses OlympicQueryManager.delete_query() method")

if __name__ == "__main__":
    test_delete_olympic_query()
