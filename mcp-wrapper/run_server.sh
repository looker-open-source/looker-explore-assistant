#!/bin/bash

# Run the MCP server
cd "$(dirname "$0")"

echo "🚀 Starting Looker MCP Server..."
echo "📁 Working directory: $(pwd)"
echo "🐍 Python path: $(which python3)"
echo

# Check if virtual environment should be created
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📋 Installing dependencies..."
pip install -r requirements.txt

echo
echo "🎯 Starting MCP server..."
echo "ℹ️  The server will listen on stdio for MCP protocol messages"
echo "ℹ️  Use an MCP client or the test script to interact with it"
echo

# Run the server
cd src
python server.py
