#!/usr/bin/env python3

import asyncio
import json
import sys
import os

# Add src to path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp import ClientSession
from mcp.types import TextContent


async def test_mcp_server():
    """Test the MCP server functionality"""
    
    print("🚀 Testing Looker MCP Server...")
    print()
    
    # Server parameters
    server_params = StdioServerParameters(
        command="python",
        args=[os.path.join(os.path.dirname(__file__), "src", "server.py")]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            
            # Initialize the session
            await session.initialize()
            
            print("✅ MCP Server initialized successfully")
            print()
            
            # Test 1: List available tools
            print("📋 Listing available tools...")
            tools = await session.list_tools()
            
            for tool in tools.tools:
                print(f"  • {tool.name}: {tool.description}")
            print()
            
            # Test 2: List available resources  
            print("📚 Listing available resources...")
            resources = await session.list_resources()
            
            for resource in resources.resources:
                print(f"  • {resource.name}: {resource.description}")
            print()
            
            # Test 3: Read a resource
            if resources.resources:
                print("📖 Reading OAuth setup guide...")
                content = await session.read_resource("looker://help/oauth-setup")
                print("Content preview:")
                print(content[:200] + "..." if len(content) > 200 else content)
                print()
            
            # Test 4: Test connection (requires OAuth token)
            oauth_token = input("Enter OAuth token to test connection (or press Enter to skip): ").strip()
            
            if oauth_token:
                print("🔌 Testing connection to Looker API...")
                
                try:
                    result = await session.call_tool(
                        "test_looker_connection",
                        {"oauth_token": oauth_token}
                    )
                    
                    for content in result.content:
                        if isinstance(content, TextContent):
                            print(content.text)
                    print()
                    
                    # Test 5: Generate explore (if connection works)
                    print("🔍 Testing explore generation...")
                    explore_result = await session.call_tool(
                        "generate_looker_explore",
                        {
                            "prompt": "Show me total sales by product category",
                            "oauth_token": oauth_token
                        }
                    )
                    
                    for content in explore_result.content:
                        if isinstance(content, TextContent):
                            print(content.text)
                    
                except Exception as e:
                    print(f"❌ Error during tool testing: {e}")
            
            else:
                print("⚠️  Skipping connection and explore tests (no OAuth token provided)")
                print()
                print("To get an OAuth token, run:")
                print("  gcloud auth print-access-token")
                print("  (Make sure you have the required scopes)")


async def main():
    """Main test function"""
    try:
        await test_mcp_server()
        print("🎉 MCP Server test completed!")
        
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
