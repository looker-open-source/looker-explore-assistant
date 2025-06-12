#!/bin/bash

# Script to restart the MCP server with enhanced logging

echo "Stopping any existing MCP server processes..."
pkill -f "python.*mcp_server.py" || echo "No existing processes found"

echo "Starting MCP server with enhanced debugging..."
cd /home/colin/looker-explore-assistant/explore-assistant-cloud-function

# Load environment variables
source .env

# Set debug logging
export LOG_LEVEL="DEBUG"

# Start the server
echo "Starting server on port ${PORT:-8001}..."
python mcp_server.py
