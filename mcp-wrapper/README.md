# Looker Explore Assistant MCP Wrapper

This is a Model Context Protocol (MCP) wrapper for the Looker Explore Assistant API. It allows AI assistants like Claude Desktop to interact with your Looker data through natural language queries.

## What is MCP?

The Model Context Protocol (MCP) is a standardized way for AI assistants to access external tools and resources. This wrapper converts your existing Looker Explore Assistant API into MCP-compatible tools.

## Features

- **🔧 MCP Tools**: 
  - `generate_looker_explore`: Convert natural language to Looker explore parameters
  - `test_looker_connection`: Test API connectivity and authentication

- **📚 MCP Resources**:
  - OAuth setup guide
  - Usage examples and documentation

- **🔐 Authentication**: Uses OAuth tokens for secure access to Google Cloud/Vertex AI

## Setup

### 1. Install Dependencies

```bash
cd mcp-wrapper
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the `.env` file and update settings if needed:

```bash
# The default configuration should work with your existing Cloud Run service
cat .env
```

### 3. Get OAuth Token

You'll need a Google Cloud OAuth token with these scopes:
- `https://www.googleapis.com/auth/cloud-platform`
- `https://www.googleapis.com/auth/userinfo.email`

```bash
# Option 1: Using gcloud (easiest)
gcloud auth print-access-token

# Option 2: With specific scopes
gcloud auth login --scopes=https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/userinfo.email
gcloud auth print-access-token
```

## Running the Server

### Method 1: Direct Test (Recommended for testing)

```bash
./test_mcp_server.py
```

This will:
- Start the MCP server
- Test all available tools and resources
- Guide you through testing with your OAuth token

### Method 2: Run Server Directly

```bash
./run_server.sh
```

This starts the MCP server listening on stdio. You'll need an MCP client to interact with it.

### Method 3: Manual Setup

```bash
cd src
python server.py
```

## Usage Examples

### Using with Claude Desktop

Add to your Claude Desktop MCP configuration:

```json
{
  "mcpServers": {
    "looker-explore-assistant": {
      "command": "python",
      "args": ["/path/to/mcp-wrapper/src/server.py"],
      "env": {
        "LOOKER_API_URL": "https://your-cloud-run-url"
      }
    }
  }
}
```

### Tool Usage

#### Generate Looker Explore
```json
{
  "tool": "generate_looker_explore",
  "arguments": {
    "prompt": "Show me total sales by product category for this year",
    "oauth_token": "your_oauth_token",
    "explore_key": "order_items"
  }
}
```

#### Test Connection
```json
{
  "tool": "test_looker_connection", 
  "arguments": {
    "oauth_token": "your_oauth_token"
  }
}
```

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   AI Assistant  │    │   MCP Wrapper   │    │  Looker API     │
│   (Claude)      │◄──►│   (This Repo)   │◄──►│  (Cloud Run)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

The MCP wrapper:
1. Receives MCP tool calls from AI assistants
2. Converts them to API calls to your existing Looker service
3. Returns formatted responses back through MCP

## Testing

### Run All Tests
```bash
cd mcp-wrapper
python -m pytest tests/
```

### Test Individual Components
```bash
# Test the MCP server
python test_mcp_server.py

# Test against your original API directly
cd ../explore-assistant-cloud-function
python test_oauth_flow.py
```

## Troubleshooting

### Common Issues

1. **"ModuleNotFoundError"**: Make sure you're in the virtual environment and have installed dependencies
2. **"OAuth token invalid"**: Check that your token has both required scopes
3. **"Connection refused"**: Verify your Cloud Run service is running at the configured URL

### Debug Mode

Set `LOG_LEVEL=DEBUG` in `.env` for detailed logging:

```bash
LOG_LEVEL=DEBUG python test_mcp_server.py
```

### Verify Original API

Test your original API still works:
```bash
cd ../explore-assistant-cloud-function
python test_oauth_flow.py
```

## Development

### Project Structure
```
mcp-wrapper/
├── src/
│   ├── server.py              # Main MCP server
│   ├── handlers/
│   │   ├── mcp_handler.py     # MCP tool implementations  
│   │   └── fallback_handler.py
│   ├── config/
│   │   └── settings.py        # Configuration
│   └── utils/
│       ├── request_parser.py
│       └── response_formatter.py
├── test_mcp_server.py         # Test script
├── run_server.sh             # Server runner
└── requirements.txt
```

### Adding New Tools

1. Add tool definition in `MCPHandler.list_tools()`
2. Implement handler in `MCPHandler.call_tool()`
3. Add tests in `test_mcp_server.py`

## Contributing

This wrapper maintains backward compatibility with your existing API while adding MCP functionality. Changes should not break existing integrations.

## License

Same as the original Looker Explore Assistant project.