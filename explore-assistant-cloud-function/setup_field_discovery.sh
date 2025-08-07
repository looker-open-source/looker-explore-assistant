#!/bin/bash

# Setup script for Field Discovery Vector Search System
# This script sets up the complete vector search system for semantic field discovery

set -e  # Exit on any error

echo "🚀 Setting up Field Discovery Vector Search System..."

# Check required environment variables
required_vars=(
    "PROJECT"
    "BQ_DATASET_ID" 
    "LOOKERSDK_BASE_URL"
    "LOOKERSDK_CLIENT_ID"
    "LOOKERSDK_CLIENT_SECRET"
)

echo "📋 Checking environment variables..."
for var in "${required_vars[@]}"; do
    if [[ -z "${!var}" ]]; then
        echo "❌ Error: $var environment variable is not set"
        echo ""
        case $var in
            "PROJECT")
                echo "   Set your Google Cloud project ID:"
                echo "   export PROJECT=your-project-id"
                ;;
            "BQ_DATASET_ID")
                echo "   Set your BigQuery dataset ID:"
                echo "   export BQ_DATASET_ID=explore_assistant"
                ;;
            "LOOKERSDK_BASE_URL")
                echo "   Set your Looker instance URL:"
                echo "   export LOOKERSDK_BASE_URL=https://your-instance.looker.com"
                ;;
            "LOOKERSDK_CLIENT_ID")
                echo "   Set your Looker API client ID:"
                echo "   export LOOKERSDK_CLIENT_ID=your-client-id"
                ;;
            "LOOKERSDK_CLIENT_SECRET")
                echo "   Set your Looker API client secret:"
                echo "   export LOOKERSDK_CLIENT_SECRET=your-client-secret"
                ;;
        esac
        echo ""
        exit 1
    fi
    echo "✅ $var is set"
done

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Additional dependencies for field discovery
pip install spacy
python -m spacy download en_core_web_sm

echo "🔧 Installing MCP dependencies..."
pip install mcp

echo "📊 Creating BigQuery dataset if it doesn't exist..."
bq mk --dataset --location=US "$PROJECT:$BQ_DATASET_ID" 2>/dev/null || echo "Dataset already exists"

echo "⚡ Setting up vector search system..."
echo "This will:"
echo "  1. Create the text embedding model"
echo "  2. Fetch all Looker explores with 'index' sets"
echo "  3. Create the field values table with embeddings"
echo "  4. Create the vector index for fast search"
echo ""

echo "🔧 Setting up vector search system using Looker explores..."
python vector_table_manager.py --action setup

echo ""
echo "📊 Getting table statistics..."
python vector_table_manager.py --action stats

echo "🧪 Testing MCP server..."
python -c "
import sys
sys.path.append('.')
from field_lookup_mcp import FieldLookupMCPServer
import asyncio

async def test_server():
    server = FieldLookupMCPServer()
    print('✅ MCP server imports successfully')
    
    # Test spaCy
    try:
        import spacy
        nlp = spacy.load('en_core_web_sm')
        doc = nlp('test customer orders')
        print('✅ spaCy is working')
    except Exception as e:
        print(f'❌ spaCy issue: {e}')
        
    # Test BigQuery client
    try:
        from google.cloud import bigquery
        client = bigquery.Client()
        print('✅ BigQuery client initializes')
    except Exception as e:
        print(f'❌ BigQuery issue: {e}')

asyncio.run(test_server())
"

echo ""
echo "🎉 Field Discovery Vector Search System setup complete!"
echo ""
echo "✅ System Features:"
echo "• Automatically indexes all Looker fields from 'index' sets"
echo "• Uses BigQuery ML embeddings for semantic similarity"
echo "• Supports vector search with cosine similarity"
echo "• Provides proper MCP protocol interface"
echo ""
echo "📚 Usage:"
echo "  • Extract terms: Use extract_searchable_terms tool"
echo "  • Search fields: Use semantic_field_search tool" 
echo "  • Discover fields: Use discover_fields_for_query tool"
echo ""
echo "🔄 To update with latest Looker fields:"
echo "  python vector_table_manager.py --action update"
echo ""
echo "📈 To check table statistics:"
echo "  python vector_table_manager.py --action stats"
echo ""
echo "🔗 Integration:"
echo "  • Add field discovery to mcp_server.py LLM flow"
echo "  • Use discovered fields to enhance explore parameter generation"
echo ""
echo "🚀 Start MCP server:"
echo "  python field_lookup_mcp.py"
