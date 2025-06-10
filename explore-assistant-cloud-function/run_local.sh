#!/bin/bash

# Local MCP Server Deployment Script for Looker Explore Assistant

echo "Setting up local MCP server for testing..."

# Set environment variables for local development
export PROJECT="${PROJECT:-your-gcp-project-id}"
export REGION="${REGION:-us-central1}"
export VERTEX_MODEL="${VERTEX_MODEL:-gemini-2.0-flash-001}"
export PORT="${PORT:-8001}"

# Check if environment variables are set
if [ "$PROJECT" = "your-gcp-project-id" ]; then
    echo "ERROR: Please set the PROJECT environment variable to your GCP project ID"
    echo "Example: export PROJECT=my-gcp-project-123"
    exit 1
fi

echo "Configuration:"
echo "  - Project: $PROJECT"
echo "  - Region: $REGION"
echo "  - Vertex Model: $VERTEX_MODEL"
echo "  - Port: $PORT"
echo ""

# Install dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

echo ""
echo "Starting MCP server locally..."
echo "The server will be available at: http://localhost:$PORT"
echo ""
echo "Available endpoints:"
echo "  - POST http://localhost:$PORT/"
echo "  - GET  http://localhost:$PORT/health"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the server
python mcp_server.py
