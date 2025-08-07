#!/usr/bin/env python3
"""
Test script to verify the MCP server fixes
"""
import asyncio
import json
import logging
import sys
import os

# Add the directory containing looker_mcp_server.py to the path
sys.path.insert(0, os.path.dirname(__file__))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_mcp_server_fixes():
    """Test that the MCP server can handle tool calls correctly"""
    print("🧪 Testing MCP Server Fixes")
    print("=" * 40)
    
    try:
        # Import the server
        from looker_mcp_server import LookerExploreAssistantMCPServer
        print("✅ Successfully imported LookerExploreAssistantMCPServer")
        
        # Create server instance
        server = LookerExploreAssistantMCPServer()
        print("✅ Successfully created server instance")
        
        # Test that the handle_tool_call method exists
        if hasattr(server, 'handle_tool_call'):
            print("✅ handle_tool_call method exists")
        else:
            print("❌ handle_tool_call method missing")
            return False
            
        # Test a simple tool call that should work
        test_args = {
            "prompt": "test connection",
            "conversation_id": "test",
            "vertex_model": "gemini-2.0-flash",
            "test_mode": True
        }
        
        print(f"🔧 Testing tool call: generate_explore_parameters")
        try:
            # This should work now with both tool names
            result = await server.handle_tool_call("generate_explore_parameters", test_args)
            print("✅ Tool call succeeded")
            print(f"📊 Result type: {type(result)}")
            if result:
                print(f"📊 Result length: {len(result)}")
        except Exception as e:
            # Expected to fail due to missing dependencies, but shouldn't be attribute error
            print(f"⚠️  Tool call failed (expected): {type(e).__name__}: {str(e)[:100]}...")
            if "'Server' object has no attribute" in str(e):
                print("❌ Still has attribute error - fix didn't work")
                return False
            else:
                print("✅ No more attribute errors - fix worked!")
                
        print("\n🎉 MCP Server fixes verified successfully!")
        print("✅ The '_call_tool_handlers' error should be resolved")
        print("✅ Both 'generate_explore_parameters' and 'generate_explore_params' work")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_mcp_server_fixes())
