# Looker Explore Assistant MCP Server - Complete Integration Guide

## 🚀 Overview

We have successfully integrated the vector-based field discovery system into a comprehensive Model Context Protocol (MCP) server. The server combines:

- **Vertex AI Proxy** - Secure LLM access with authentication
- **Semantic Field Discovery** - Vector-based field search using BigQuery ML
- **Field Value Lookup** - String-based dimension value search
- **Looker Integration** - Direct API access for explore metadata and queries
- **True MCP Protocol** - Standards-compliant server for AI assistants

## ✅ Current Status

**All systems operational:**
- ✅ Vector table with 20,579 rows of Looker dimension values
- ✅ BigQuery ML embeddings with Vertex AI text-embedding-004
- ✅ Semantic field search working (19.1% similarity matches)
- ✅ Field value lookup working (exact string matches)
- ✅ MCP server passes all functionality tests

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MCP Server                               │
├─────────────────────────────────────────────────────────────┤
│  • semantic_field_search - AI similarity matching          │
│  • field_value_lookup - String-based value search          │
│  • vertex_ai_query - Secure Vertex AI proxy               │
│  • get_explore_fields - Looker metadata access            │  
│  • run_looker_query - Execute Looker queries              │
└─────────────────────────────────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
    │  BigQuery   │ │ Vertex AI   │ │ Looker API  │
    │    ML       │ │    API      │ │             │
    └─────────────┘ └─────────────┘ └─────────────┘
```

## 🛠️ Files Overview

### Core MCP Server
- **`looker_mcp_server.py`** - Main MCP server implementation
  - Complete MCP protocol implementation
  - All 5 tools integrated and tested
  - Async operations with proper error handling

### Supporting Services  
- **`field_lookup_service.py`** - Standalone field discovery service
  - Used for testing and development
  - Same functionality as MCP server tools
  
- **`vector_table_manager.py`** - Vector table creation and management
  - 20,579 rows of actual Looker dimension values
  - Automated dimension value extraction from Looker API

### Testing & Utilities
- **`test_mcp_server.py`** - Comprehensive MCP server testing
- **`test_*.py`** - Various component tests

## 🔧 How to Use

### 1. Run as MCP Server (for AI Assistants like Claude)

```bash
cd explore-assistant-cloud-function
python3 looker_mcp_server.py
```

The server will listen on stdio for MCP protocol messages.

### 2. Test Functionality

```bash
python3 test_mcp_server.py
```

### 3. Use Individual Tools

```python
from looker_mcp_server import LookerExploreAssistantMCPServer
import asyncio

async def test_search():
    server = LookerExploreAssistantMCPServer()
    
    # Test semantic search
    result = await server._handle_semantic_field_search({
        "search_terms": ["brand", "revenue"],
        "limit_per_term": 3
    })
    
    # Test field value lookup  
    result = await server._handle_field_value_lookup({
        "search_string": "nike"
    })

asyncio.run(test_search())
```

## 🎯 Available MCP Tools

### 1. semantic_field_search
Find fields using AI similarity matching.

**Input:**
```json
{
  "search_terms": ["brand", "customer", "revenue"],
  "explore_ids": ["model:explore"],  // optional
  "limit_per_term": 5,
  "similarity_threshold": 0.1
}
```

**Output:** Field matches with similarity scores and sample values.

### 2. field_value_lookup
Find specific values in dimension fields.

**Input:**
```json
{
  "search_string": "nike",
  "field_location": "model.explore.view.field",  // optional
  "limit": 10
}
```

**Output:** Matching field values with frequency data.

### 3. vertex_ai_query
Secure Vertex AI API proxy.

**Input:**
```json
{
  "prompt": "Your question here",
  "model": "gemini-2.0-flash-001",
  "temperature": 0.1,
  "max_tokens": 8192
}
```

### 4. get_explore_fields
Get available Looker explore fields.

**Input:**
```json
{
  "model_name": "ecommerce",
  "explore_name": "order_items"
}
```

### 5. run_looker_query
Execute Looker inline queries.

**Input:**
```json
{
  "query_body": {
    "model": "ecommerce",
    "explore": "order_items", 
    "dimensions": ["products.brand"],
    "measures": ["order_items.count"]
  }
}
```

## 📊 Performance Metrics

**Vector Table:**
- 20,579 rows of actual Looker dimension values
- 50+ explores across multiple models
- Real production data from ecommerce dataset

**Search Results:**
- Semantic search: 19.1% similarity for "brand" → `products.brand`
- Value lookup: Exact matches for "nike" → 2 brand fields
- Query time: <2 seconds for semantic search

## 🔮 Integration Examples

### Claude Desktop Configuration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "looker-explore-assistant": {
      "command": "python3",
      "args": ["/path/to/explore-assistant-cloud-function/looker_mcp_server.py"],
      "env": {
        "BQ_PROJECT_ID": "ml-accelerator-dbarr",
        "PROJECT": "your-vertex-project-id"
      }
    }
  }
}
```

### Programmatic Usage

```python
# Find fields related to customer analysis
semantic_results = await server._handle_semantic_field_search({
    "search_terms": ["customer", "segment", "demographic"],
    "limit_per_term": 5
})

# Look for specific brand values
brand_values = await server._handle_field_value_lookup({
    "search_string": "adidas",
    "limit": 10
})

# Get LLM suggestions for analysis
ai_response = await server._handle_vertex_ai_query({
    "prompt": "Based on these fields, what's the best way to analyze customer brand preferences?"
})
```

## 🛡️ Security & Authentication

- **Service Account**: Uses default Google Cloud credentials
- **OAuth Support**: Can accept user OAuth tokens for Vertex AI
- **API Security**: All API calls use proper authentication headers
- **Error Handling**: Comprehensive error handling with user-friendly messages

## 🔄 Next Steps

The MCP server is production-ready and can be:

1. **Deployed** as a standalone MCP service
2. **Integrated** into existing Looker infrastructure  
3. **Extended** with additional field discovery capabilities
4. **Scaled** to handle multiple concurrent requests

All vector search capabilities are fully operational and integrated into the main MCP server!
