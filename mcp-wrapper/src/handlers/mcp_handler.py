import json
import logging
from typing import Any, Dict, List

import aiohttp
from mcp import types

logger = logging.getLogger(__name__)


class MCPHandler:
    def __init__(self, settings):
        self.settings = settings
        
    async def list_tools(self) -> List[types.Tool]:
        """List available MCP tools"""
        return [
            types.Tool(
                name="generate_looker_explore",
                description="Generate Looker explore parameters from natural language query",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "Natural language query to convert to Looker explore parameters"
                        },
                        "explore_key": {
                            "type": "string", 
                            "description": "Optional: specific explore to use (e.g., 'order_items', 'users')"
                        },
                        "oauth_token": {
                            "type": "string",
                            "description": "OAuth token for authentication with Google Cloud/Vertex AI"
                        },
                        "golden_queries": {
                            "type": "object",
                            "description": "Optional: golden query examples for context"
                        },
                        "semantic_models": {
                            "type": "object", 
                            "description": "Optional: semantic model definitions"
                        }
                    },
                    "required": ["prompt", "oauth_token"]
                }
            ),
            types.Tool(
                name="test_looker_connection",
                description="Test connection to the Looker Explore Assistant API",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "oauth_token": {
                            "type": "string",
                            "description": "OAuth token for authentication"
                        }
                    },
                    "required": ["oauth_token"]
                }
            )
        ]
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Handle MCP tool calls"""
        logger.info(f"Calling tool: {name}")
        
        if name == "generate_looker_explore":
            return await self._generate_looker_explore(arguments)
        elif name == "test_looker_connection":
            return await self._test_looker_connection(arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")
    
    async def _generate_looker_explore(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Generate Looker explore parameters using the existing API"""
        try:
            prompt = arguments.get("prompt", "")
            oauth_token = arguments.get("oauth_token", "")
            explore_key = arguments.get("explore_key")
            golden_queries = arguments.get("golden_queries", {})
            semantic_models = arguments.get("semantic_models", {})
            
            if not prompt:
                return [types.TextContent(
                    type="text",
                    text="Error: 'prompt' parameter is required"
                )]
            
            if not oauth_token:
                return [types.TextContent(
                    type="text", 
                    text="Error: 'oauth_token' parameter is required for authentication"
                )]
            
            # Build request payload for the existing API
            payload = {
                "prompt": prompt,
                "conversation_id": f"mcp_tool_{hash(prompt)}",
                "current_explore": {"exploreKey": explore_key} if explore_key else {},
                "golden_queries": golden_queries,
                "semantic_models": semantic_models,
                "model_name": "gemini-2.0-flash-001",
                "test_mode": False
            }
            
            headers = {
                "Authorization": f"Bearer {oauth_token}",
                "Content-Type": "application/json"
            }
            
            # Call the existing API
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.settings.looker_api_url}/",
                    json=payload,
                    headers=headers,
                    timeout=self.settings.request_timeout
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        
                        # Format the response nicely
                        formatted_result = self._format_explore_result(result)
                        
                        return [types.TextContent(
                            type="text",
                            text=formatted_result
                        )]
                    else:
                        error_text = await response.text()
                        logger.error(f"API call failed: {response.status} - {error_text}")
                        
                        return [types.TextContent(
                            type="text",
                            text=f"Error: API call failed with status {response.status}\n{error_text}"
                        )]
                        
        except Exception as e:
            logger.error(f"Error in _generate_looker_explore: {e}")
            return [types.TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )]
    
    async def _test_looker_connection(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Test connection to the Looker API"""
        try:
            oauth_token = arguments.get("oauth_token", "")
            
            if not oauth_token:
                return [types.TextContent(
                    type="text",
                    text="Error: 'oauth_token' parameter is required"
                )]
            
            # Build test request
            payload = {
                "prompt": "test connection",
                "test_mode": True
            }
            
            headers = {
                "Authorization": f"Bearer {oauth_token}",
                "Content-Type": "application/json"
            }
            
            # Test health endpoint first
            async with aiohttp.ClientSession() as session:
                # Health check
                async with session.get(f"{self.settings.looker_api_url}/health") as response:
                    if response.status == 200:
                        health_data = await response.json()
                        
                        # Test main endpoint
                        async with session.post(
                            f"{self.settings.looker_api_url}/",
                            json=payload,
                            headers=headers,
                            timeout=self.settings.request_timeout
                        ) as main_response:
                            
                            if main_response.status == 200:
                                test_result = await main_response.json()
                                
                                return [types.TextContent(
                                    type="text",
                                    text=f"✅ Connection successful!\n\n"
                                         f"Health Status: {health_data.get('status', 'unknown')}\n"
                                         f"Service: {health_data.get('service', 'unknown')}\n"
                                         f"Project: {health_data.get('project', 'unknown')}\n"
                                         f"Model: {health_data.get('model', 'unknown')}\n"
                                         f"Test Response: {test_result.get('message', 'unknown')}"
                                )]
                            else:
                                error_text = await main_response.text()
                                return [types.TextContent(
                                    type="text",
                                    text=f"❌ Main endpoint failed: {main_response.status}\n{error_text}"
                                )]
                    else:
                        return [types.TextContent(
                            type="text",
                            text=f"❌ Health check failed: {response.status}"
                        )]
                        
        except Exception as e:
            logger.error(f"Error in _test_looker_connection: {e}")
            return [types.TextContent(
                type="text",
                text=f"❌ Connection test failed: {str(e)}"
            )]
    
    def _format_explore_result(self, result: Dict[str, Any]) -> str:
        """Format the explore result for display"""
        if "error" in result:
            return f"❌ Error: {result['error']}"
        
        formatted = "🎉 Looker Explore Generated Successfully!\n\n"
        
        if "explore_key" in result:
            formatted += f"📊 Explore: {result['explore_key']}\n\n"
        
        if "summary" in result:
            formatted += f"📝 Summary: {result['summary']}\n\n"
        
        if "explore_params" in result:
            params = result["explore_params"]
            formatted += "⚙️ Generated Parameters:\n"
            
            if "fields" in params and params["fields"]:
                formatted += f"  • Fields: {', '.join(params['fields'])}\n"
            
            if "filters" in params and params["filters"]:
                filters_str = ", ".join([f"{k}={v}" for k, v in params["filters"].items()])
                formatted += f"  • Filters: {filters_str}\n"
            
            if "sorts" in params and params["sorts"]:
                formatted += f"  • Sorts: {', '.join(params['sorts'])}\n"
            
            if "limit" in params:
                formatted += f"  • Limit: {params['limit']}\n"
        
        formatted += f"\n📋 Full Response:\n```json\n{json.dumps(result, indent=2)}\n```"
        
        return formatted

    async def list_resources(self) -> List[types.Resource]:
        """List available MCP resources"""
        return [
            types.Resource(
                uri="looker://help/oauth-setup",
                name="OAuth Setup Guide",
                description="Instructions for setting up OAuth token for Looker API access",
                mimeType="text/markdown"
            ),
            types.Resource(
                uri="looker://help/examples",
                name="Usage Examples", 
                description="Examples of how to use the Looker Explore Assistant",
                mimeType="text/markdown"
            )
        ]
    
    async def read_resource(self, uri: str) -> str:
        """Read resource content"""
        if uri == "looker://help/oauth-setup":
            return self._get_oauth_setup_guide()
        elif uri == "looker://help/examples":
            return self._get_usage_examples()
        else:
            raise ValueError(f"Unknown resource: {uri}")
    
    def _get_oauth_setup_guide(self) -> str:
        """Return OAuth setup instructions"""
        return """# OAuth Setup Guide for Looker Explore Assistant

## Getting an OAuth Token

You need a Google Cloud OAuth token with the following scopes:
- `https://www.googleapis.com/auth/cloud-platform` (for Vertex AI)
- `https://www.googleapis.com/auth/userinfo.email` (for user identification)

## Methods to Get Token:

### Option 1: Using gcloud CLI (easiest)
```bash
gcloud auth application-default print-access-token
```

### Option 2: Using gcloud with user credentials 
```bash
gcloud auth login --enable-gdrive-access
gcloud auth print-access-token
```

### Option 3: Using OAuth Playground
1. Go to: https://developers.google.com/oauthplayground/
2. Add the required scopes listed above
3. Complete the authorization flow
4. Copy the access token

## Important Notes:
- The token must have BOTH required scopes
- Tokens expire and need to be refreshed
- Make sure your GCP project has Vertex AI API enabled
"""

    def _get_usage_examples(self) -> str:
        """Return usage examples"""
        return """# Usage Examples for Looker Explore Assistant

## Example 1: Basic Query
```json
{
  "prompt": "Show me total sales by product category",
  "oauth_token": "your_oauth_token_here"
}
```

## Example 2: With Specific Explore
```json
{
  "prompt": "What are the top selling products this year?",
  "explore_key": "order_items",
  "oauth_token": "your_oauth_token_here"
}
```

## Example 3: With Context Data
```json
{
  "prompt": "How many users signed up each month?",
  "oauth_token": "your_oauth_token_here",
  "golden_queries": {
    "users": [
      {
        "input": "Monthly user signups",
        "output": "fields=users.created_month,users.count&sorts=users.created_month desc"
      }
    ]
  },
  "semantic_models": {
    "users": {
      "dimensions": [
        {"name": "users.created_month", "type": "date", "label": "Created Month"}
      ],
      "measures": [
        {"name": "users.count", "type": "number", "label": "Number of Users"}
      ]
    }
  }
}
```

## Testing Connection
Use the `test_looker_connection` tool to verify your setup:
```json
{
  "oauth_token": "your_oauth_token_here"
}
```
"""