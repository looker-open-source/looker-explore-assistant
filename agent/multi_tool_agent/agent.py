from google.adk.agents import Agent
import requests
import os
import json
from typing import Optional, Dict, List, Any

MCP_SERVER_URL = "https://mcp-server-rchq2jmtba-uc.a.run.app"

def _call_mcp(tool_name: str, arguments: dict) -> dict:
    """Internal helper to call the MCP server with the given tool_name and arguments."""
    url = MCP_SERVER_URL
    payload = {"tool_name": tool_name, "arguments": arguments}
    headers = {"Content-Type": "application/json"}
    try:
        import google.auth.transport.requests as greq
        import google.auth
        creds, _ = google.auth.default()
        auth_req = greq.Request()
        creds.refresh(auth_req)
        id_token = creds.id_token
        if id_token:
            headers["Authorization"] = f"Bearer {id_token}"
    except Exception:
        pass
    response = requests.post(url, json=payload, headers=headers)
    try:
        return response.json()
    except Exception:
        return {"error": f"Non-JSON response: {response.text}"}

def _get_auth_headers() -> dict:
    """Get authentication headers for MCP server requests."""
    headers = {"Content-Type": "application/json"}
    try:
        import google.auth.transport.requests as greq
        import google.auth
        creds, _ = google.auth.default()
        auth_req = greq.Request()
        creds.refresh(auth_req)
        id_token = creds.id_token
        if id_token:
            headers["Authorization"] = f"Bearer {id_token}"
    except Exception:
        pass
    return headers

def _discover_mcp_tools() -> List[Dict[str, Any]]:
    """Discover available tools from the MCP server using the MCP protocol."""
    try:
        headers = _get_auth_headers()
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }
        
        response = requests.post(MCP_SERVER_URL, json=payload, headers=headers)
        if response.status_code == 200:
            result = response.json()
            if "result" in result and "tools" in result["result"]:
                return result["result"]["tools"]
            else:
                print(f"Unexpected MCP response format: {result}")
                return []
        else:
            print(f"MCP tools discovery failed: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        print(f"Error discovering MCP tools: {e}")
        return []

def _create_dynamic_tool_wrapper(tool_name: str, tool_description: str, input_schema: Dict[str, Any]):
    """Create a dynamic tool wrapper function for a discovered MCP tool."""
    
    # Extract required and optional parameters from the schema
    properties = input_schema.get("properties", {})
    required_params = input_schema.get("required", [])
    
    # For facts tools, create a more explicit wrapper
    if tool_name.endswith("_facts"):
        def facts_tool_wrapper(user_question: str, oauth_token: Optional[str] = None):
            """Wrapper for facts tools that explicitly requires user_question parameter."""
            tool_args = {
                "user_question": user_question
            }
            if oauth_token:
                tool_args["oauth_token"] = oauth_token
            return _call_mcp(tool_name, tool_args)
        
        facts_tool_wrapper.__name__ = tool_name
        facts_tool_wrapper.__doc__ = f"{tool_description}\n\nParameters:\n- user_question (str): The user's exact question\n- oauth_token (str, optional): Looker OAuth token"
        return facts_tool_wrapper
    
    # Generic wrapper for other tools
    def tool_wrapper(*args, **kwargs):
        # Build arguments dict from the provided parameters
        tool_args = {}
        
        # Handle positional arguments (map to required parameters in order)
        for i, arg in enumerate(args):
            if i < len(required_params):
                tool_args[required_params[i]] = arg
        
        # Handle keyword arguments
        for key, value in kwargs.items():
            tool_args[key] = value
        
        # Call the MCP server
        return _call_mcp(tool_name, tool_args)
    
    # Set function metadata
    tool_wrapper.__name__ = tool_name
    tool_wrapper.__doc__ = tool_description
    
    return tool_wrapper

def _create_all_dynamic_tools() -> List[callable]:
    """Discover and create dynamic tool wrappers for all MCP server tools."""
    discovered_tools = _discover_mcp_tools()
    dynamic_tools = []
    
    print(f"Discovered {len(discovered_tools)} tools from MCP server:")
    
    for tool_info in discovered_tools:
        tool_name = tool_info.get("name", "unknown_tool")
        tool_description = tool_info.get("description", f"MCP tool: {tool_name}")
        input_schema = tool_info.get("inputSchema", {})
        
        print(f"  - {tool_name}: {tool_description}")
        
        # Create dynamic wrapper
        wrapper_func = _create_dynamic_tool_wrapper(tool_name, tool_description, input_schema)
        dynamic_tools.append(wrapper_func)
    
    return dynamic_tools

# Create dynamic tools by discovering them from the MCP server
print("🔍 Discovering tools from MCP server...")
dynamic_tools = _create_all_dynamic_tools()

# Build dynamic tool names for instructions
if dynamic_tools:
    tool_names = [tool.__name__ for tool in dynamic_tools]
    tools_list = ", ".join(tool_names)
    description = f"Agent to answer questions using the Looker MCP server with {len(dynamic_tools)} dynamically discovered tools including vector search, explore parameter generation, query execution, feedback capabilities, and area-based facts tools."
    instruction = f"I can answer your questions about Looker data using the MCP server. Available tools: {tools_list}."
else:
    # Fallback if discovery fails
    print("⚠️  Tool discovery failed, using fallback mode")
    description = "Agent to answer questions using the Looker MCP server (tool discovery failed)"
    instruction = "I can answer your questions about Looker data, but tool discovery failed. Please check MCP server connection."

# Register dynamically discovered tools with the agent
root_agent = Agent(
    name="looker_mcp_agent",
    model="gemini-2.5-flash",
    description=description,
    instruction=instruction,
    tools=dynamic_tools if dynamic_tools else []
)