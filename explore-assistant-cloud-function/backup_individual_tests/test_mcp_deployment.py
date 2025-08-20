#!/usr/bin/env python3
"""
Test script for the deployed Looker MCP Server
Tests the area-based facts tools and OAuth integration
"""

import json
import requests
import subprocess
import sys
from typing import Optional

# Configuration - Update these values
MCP_SERVER_URL = "https://mcp-server-rchq2jmtba-uc.a.run.app"
OAUTH_TOKEN = "eyJhbGciOiJSUzI1NiIsImtpZCI6Ijk4ZGM1NWM4YjIwOTM2M2EyNDUxNzc0YmNlNWM0MjcxOGQxM2NiN2QiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2FjY291bnRzLmdvb2dsZS5jb20iLCJhenAiOiI3MzAxOTIxNzU5NzEtdmg3ZTl1aGhpcmFlMzU5NDNycGNvbjkzZnFwOGJob28uYXBwcy5nb29nbGV1c2VyY29udGVudC5jb20iLCJhdWQiOiI3MzAxOTIxNzU5NzEtdmg3ZTl1aGhpcmFlMzU5NDNycGNvbjkzZnFwOGJob28uYXBwcy5nb29nbGV1c2VyY29udGVudC5jb20iLCJzdWIiOiIxMTMzNTUyNDQ1MjI3MzkxMzQ1NjciLCJoZCI6ImJ5dGVjb2RlLmlvIiwiZW1haWwiOiJjb2xpbi5yb3kuZWhyaUBieXRlY29kZS5pbyIsImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJub25jZSI6Imlmc2MxNzlwMHBxbWVoZmhxMngiLCJuYmYiOjE3NTU1NDAyMTcsIm5hbWUiOiJDb2xpbiBSb3ktRWhyaSIsInBpY3R1cmUiOiJodHRwczovL2xoMy5nb29nbGV1c2VyY29udGVudC5jb20vYS9BQ2c4b2NLbmNrUXk3eU9tcVVyREgzYlRFNDZmeFk3OWlZT2I1cEJBakNCd1htdXBBeEI5Uk1ZPXM5Ni1jIiwiZ2l2ZW5fbmFtZSI6IkNvbGluIiwiZmFtaWx5X25hbWUiOiJSb3ktRWhyaSIsImlhdCI6MTc1NTU0MDUxNywiZXhwIjoxNzU1NTQ0MTE3LCJqdGkiOiIyMjdhZDRjYmQxZTI1ZmE1ZDgzNGYyMTkyOWEzZTdmYzg5YTQ3MDllIn0.ljb65piCgxaMI9VQ0nvGnGoz_knRpJbMilCWvUzacXLQB1cM0_1XQtxe_rCoM-A3ETfmVnqRs-xRduBsRCATEkIk8lZ9eepBvA5_m-uCUNDDBPfzjmv0pWbtnE2WeUQ6Y_RqnRczAbtOk7tZTVdv2BnotUhDTljQoA68IS07iQFHZbTXP0RcRe_0n9idLOkI3mWhIYtb689bzIKkM6R309kK91BkvBAjqBzvTvcMVHwthm93dJSAJHD-_Vz6FFOniFpY8MfBxGQSOhs_PRr_q5jC5xa2btjCr8Mma97mR2lQAup0JYtTt2exu61Mx-R9vfg_r38Otg7yjOr6ssDqaQ"  # Paste your Looker OAuth token here for testing

def get_identity_token() -> Optional[str]:
    """Get Google Cloud identity token for authentication"""
    try:
        result = subprocess.run(
            ["gcloud", "auth", "print-identity-token"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error getting identity token: {e}")
        return None

def test_mcp_server_health(identity_token: str) -> bool:
    """Test if the MCP server is running and accessible"""
    try:
        headers = {"Authorization": f"Bearer {identity_token}"}
        response = requests.get(f"{MCP_SERVER_URL}/health", headers=headers, timeout=10)
        
        print(f"Health check status: {response.status_code}")
        if response.status_code == 200:
            print("✅ MCP Server is running and accessible")
            return True
        else:
            print(f"❌ Health check failed: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def test_mcp_list_tools(identity_token: str) -> dict:
    """Test listing available MCP tools"""
    try:
        headers = {
            "Authorization": f"Bearer {identity_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }
        
        response = requests.post(MCP_SERVER_URL, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if "result" in result:
                tools = result["result"]["tools"]
                print(f"✅ Found {len(tools)} tools:")
                
                # Look for area-based facts tools
                facts_tools = [tool for tool in tools if tool["name"].endswith("_facts")]
                for tool in facts_tools:
                    print(f"  📊 {tool['name']}: {tool['description']}")
                
                return {"success": True, "tools": tools, "facts_tools": facts_tools}
            else:
                print(f"❌ Unexpected response format: {result}")
                return {"success": False, "error": "Unexpected response format"}
        else:
            print(f"❌ Tools list failed: {response.status_code} - {response.text}")
            return {"success": False, "error": f"HTTP {response.status_code}"}
            
    except Exception as e:
        print(f"❌ Error listing tools: {e}")
        return {"success": False, "error": str(e)}

def test_area_facts_tool(identity_token: str, tool_name: str, topic: str, oauth_token: str) -> dict:
    """Test calling an area-based facts tool"""
    if not oauth_token:
        return {"success": False, "error": "OAuth token required for facts tools"}
    
    try:
        headers = {
            "Authorization": f"Bearer {identity_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": {
                    "user_question": topic,
                    "oauth_token": oauth_token
                }
            }
        }
        
        print(f"🔍 Testing {tool_name} with topic: '{topic}'")
        response = requests.post(MCP_SERVER_URL, json=payload, headers=headers, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            if "result" in result:
                content = result["result"]["content"][0]["text"]
                facts_data = json.loads(content)
                
                print(f"✅ Facts query successful!")
                print(f"   Area: {facts_data.get('area', 'Unknown')}")
                print(f"   Explore used: {facts_data.get('explore_used', 'Unknown')}")
                print(f"   Row count: {facts_data.get('row_count', 0)}")
                
                if "error" in facts_data:
                    print(f"   ⚠️  Error in response: {facts_data['error']}")
                
                return {"success": True, "data": facts_data}
            else:
                print(f"❌ Unexpected response format: {result}")
                return {"success": False, "error": "Unexpected response format"}
        else:
            print(f"❌ Facts tool call failed: {response.status_code} - {response.text}")
            return {"success": False, "error": f"HTTP {response.status_code}"}
            
    except Exception as e:
        print(f"❌ Error calling facts tool: {e}")
        return {"success": False, "error": str(e)}

def main():
    print("🚀 Testing Looker MCP Server Deployment")
    print("=" * 50)
    
    # Get authentication token
    print("1. Getting authentication token...")
    identity_token = get_identity_token()
    if not identity_token:
        print("❌ Could not get identity token. Make sure you're authenticated with gcloud.")
        sys.exit(1)
    
    # Test server health
    print("\n2. Testing server health...")
    if not test_mcp_server_health(identity_token):
        print("❌ Server health check failed. Check deployment and permissions.")
        sys.exit(1)
    
    # List available tools
    print("\n3. Listing available tools...")
    tools_result = test_mcp_list_tools(identity_token)
    if not tools_result["success"]:
        print("❌ Could not list tools. Check server logs.")
        sys.exit(1)
    
    facts_tools = tools_result.get("facts_tools", [])
    if not facts_tools:
        print("⚠️  No area-based facts tools found. Check areas table in BigQuery.")
        print("   Run the SQL commands in DEPLOY_AND_TEST_MCP_SERVER.md to create sample data.")
        return
    
    # Test a facts tool (if OAuth token provided)
    print("\n4. Testing area-based facts tool...")
    if OAUTH_TOKEN:
        first_tool = facts_tools[0]["name"]
        test_result = test_area_facts_tool(
            identity_token, 
            first_tool, 
            "What are the current trends?", 
            OAUTH_TOKEN
        )
        
        if test_result["success"]:
            print("✅ End-to-end test successful!")
        else:
            print(f"❌ Facts tool test failed: {test_result.get('error', 'Unknown error')}")
    else:
        print("⚠️  OAuth token not provided. Skipping facts tool test.")
        print("   To test facts tools, add your Looker OAuth token to OAUTH_TOKEN variable.")
    
    print("\n" + "=" * 50)
    print("🎉 MCP Server deployment test completed!")
    print(f"   Server URL: {MCP_SERVER_URL}")
    print(f"   Available facts tools: {len(facts_tools)}")

if __name__ == "__main__":
    main()