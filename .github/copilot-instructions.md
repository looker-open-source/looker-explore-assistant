# Looker Explore Assistant - Copilot Instructions

## Architecture Overview

This is a **natural language to Looker query system** with 4 main components:

1. **Frontend Extension** (`explore-assistant-extension/`) - React/TypeScript Looker extension with Redux state management
2. **Backend MCP Server** (`explore-assistant-cloud-function/looker_mcp_server.py`) - Unified Model Context Protocol server with Vertex AI, Looker integration, and semantic field discovery
3. **Vector Search System** (`explore-assistant-cloud-function/vector_table_manager.py`) - BigQuery ML-powered semantic field discovery with dimension value vectorization
4. **Training/Examples** (`explore-assistant-examples/`) - BigQuery tables with golden query examples for LLM training

The system converts natural language → automatic explore selection → structured Looker queries → embedded visualizations.

## New MCP Server Architecture (looker_mcp_server.py)

### Unified MCP Server Features
- **Vertex AI Proxy** - Secure LLM access with service account authentication
- **Automatic Explore Selection** - AI determines best explore from `restricted_explore_keys` using `determine_explore_from_prompt()`
- **Semantic Field Discovery** - Vector-based field search using BigQuery ML embeddings
- **Field Value Lookup** - String-based dimension value search with frequency data
- **Looker Integration** - Direct API access for explore metadata and queries
- **Olympic Query Management** - Bronze/Silver/Golden query promotion workflow
- **Standards-Compliant MCP** - Full Model Context Protocol implementation

### Key Changes from Legacy Architecture
- **No More Explicit explore_key** - System automatically determines best explore from restricted list
- **Integrated Vector Search** - Field discovery built into main MCP server
- **Service Account Authentication** - Eliminates OAuth complexity for backend operations
- **Consolidated Tool Interface** - Single server handles all operations

## Vector Search System with LLM Function Calling

### Intelligent Vector Search Integration
- **LLM-Driven Decision Making** - Vertex AI function calling determines when to use vector search
- **Selective Field Coverage** - Only indexes high-cardinality dimensions marked with 'index' sets in Looker
- **Value-Based Discovery** - Searches actual dimension values (brand names, codes, SKUs) NOT field names
- **Context-Aware Usage** - LLM decides when specific value lookup is needed vs standard field metadata

### Vector Search Capabilities & Limitations
**WHAT IT DOES:**
- Finds fields containing specific product names, brand codes, SKUs, status values, etc.
- Searches actual dimension values from indexed high-cardinality fields only
- Returns field locations where specific values exist with frequency data
- Enables precise filtering on discovered values

**WHAT IT DOESN'T DO:**
- Does NOT provide comprehensive field discovery (only indexed dimensions)
- Does NOT search for business concepts like "revenue" or "profit" (use explore metadata)
- Does NOT replace standard field metadata (complements it for specific values)

### Function Calling Implementation
```python
# LLM has access to these functions via Vertex AI function calling:
function_declarations = [
    {
        "name": "search_semantic_fields", 
        "description": "Find indexed fields containing specific values/codes",
        # Only use for: brand names, SKUs, product codes, status values
    },
    {
        "name": "lookup_field_values",
        "description": "Find specific dimension values in indexed fields", 
        # Only use for: verifying exact codes/names exist before filtering
    }
]

# LLM autonomously decides when to call these based on user query context
```

### Updated Workflow
```python
# 1. LLM analyzes user query: "Show me sales for Nike products"
# 2. LLM recognizes "Nike" as specific value and calls lookup_field_values("Nike")
# 3. System returns: products.brand contains "Nike" with frequency data
# 4. LLM generates query using discovered field location for filtering

# NOT used for general concepts:
# "Show me customer revenue" → uses standard explore metadata, no function calls
```

### Setup Process
```bash
cd explore-assistant-cloud-function
./setup_field_discovery.sh  # Complete automated setup
python vector_table_manager.py --action setup  # Manual setup
python vector_table_manager.py --action stats   # Check system status
```

### Vector Table Schema
```sql
-- field_values_for_vectorization table
CREATE TABLE field_values_for_vectorization (
  model_name STRING,
  explore_name STRING,
  view_name STRING, 
  field_name STRING,
  field_type STRING,       -- 'dimension' or 'measure'
  field_description STRING,
  field_value STRING,      -- Actual dimension values from Looker data
  value_frequency INT64,   -- How often this value appears
  searchable_text STRING,  -- Combined metadata for embedding
  ml_generate_embedding_result ARRAY<FLOAT64>  -- Vector embeddings
)
```

## Key Architectural Patterns

### AI-Driven Explore Selection with Restrictions
- System **automatically determines best explore** from `restricted_explore_keys` list via `determine_explore_from_prompt()`
- No more manual explore_key specification - AI chooses optimal explore for each query
- Explore keys follow format: `"model:explore_name"` (e.g., `"ecommerce:order_items"`)
- Uses golden queries and conversation context for intelligent selection

### Two-Phase Query Processing
```python
# Phase 1: Determine best explore from restricted list
determined_explore_key = determine_explore_from_prompt(
    auth_header=auth_header,
    prompt=prompt,
    golden_queries=golden_queries,
    conversation_context=conversation_context,
    restricted_explore_keys=restricted_explore_keys
)

# Phase 2: Generate parameters for determined explore  
explore_params = generate_explore_params_for_determined_explore(
    prompt, determined_explore_key, field_metadata, conversation_context
)
```

### LLM Function Calling Workflow  
```python
# Phase 1: Determine best explore (with optional function calling)
determined_explore_key = determine_explore_from_prompt(
    auth_header=auth_header,
    prompt=prompt,  # "Show me Nike product sales"
    golden_queries=golden_queries,
    conversation_context=conversation_context,
    restricted_explore_keys=restricted_explore_keys
)
# LLM may call lookup_field_values("Nike") to find which explores contain Nike data

# Phase 2: Generate parameters (with optional function calling)  
explore_params = generate_explore_params_for_determined_explore(
    prompt, determined_explore_key, field_metadata, conversation_context
)
# LLM may call search_semantic_fields(["Nike"]) to find exact field location for filtering
```

### Function Call Decision Logic
- **Use vector search when**: User mentions specific brands, codes, SKUs, product names, status values
- **Don't use when**: User asks for general metrics (revenue, count, average) or business concepts
- **LLM autonomously decides**: Based on query analysis and available explore metadata

### Flask Backend Integration (mcp_server.py)
The Flask-based backend now includes vector search integration with both MCP tools and REST endpoints:

**MCP Tools Available:**
- `search_semantic_fields` - Find indexed fields containing specific values/codes
- `field_value_lookup` - Find specific dimension values in indexed fields  
- `extract_searchable_terms` - Extract searchable terms from natural language

**REST Endpoints:**
- `POST /field-search` - Semantic field search API
- `POST /field-values` - Field value lookup API
- `POST /extract-terms` - Term extraction API
- `GET /health` - Health check (includes new endpoints)

**Integration Pattern:**
```python
# Vector search is integrated into main query processing
# Both determine_explore_from_prompt() and generate_explore_params() 
# can use function calling to access vector search when needed
payload = {
  "prompt": "Show me Nike sales",
  "restricted_explore_keys": ["ecommerce:orders", "products:items"],
  # LLM automatically calls field lookup functions if needed
}
```

### Redux State Structure
```typescript
// Central state in assistantSlice.ts
interface AssistantState {
  currentExploreThread: ExploreThread | null  // Multi-turn conversation
  semanticModels: { [exploreKey: string]: SemanticModel }  // Field metadata
  examples: { exploreEntries, exploreGenerationExamples, ... }  // Training data
  settings: Settings  // OAuth, Vertex AI, BigQuery configs
  oauth: { token, isAuthenticating, hasValidToken }  // Google OAuth state
}
```

## Essential Development Commands

### Backend MCP Server Development
```bash
cd explore-assistant-cloud-function  
pip install -r requirements.txt

# Flask backend with vector search integration
python3 mcp_server.py  # Flask server with MCP tools and REST endpoints
python3 run_local.sh   # Alternative startup script

# Unified MCP server (legacy/alternative)
python3 looker_mcp_server.py  # Direct MCP server

# Vector search system setup
./setup_field_discovery.sh  # Complete automated setup
python vector_table_manager.py --action setup  # Manual setup
python test_semantic_search.py  # Test vector search integration
```

### Frontend Development
```bash
cd explore-assistant-extension
npm install
npm start  # Webpack dev server on https://localhost:8080
npm run build  # Production bundle
```

### BigQuery Vector Search Setup
```bash
# Initialize vector search system
cd explore-assistant-cloud-function
./setup_field_discovery.sh

# Manual setup steps if needed
python vector_table_manager.py --action setup
python vector_table_manager.py --action stats
```

## Critical Integration Points

### OAuth Flow
- Frontend uses `useOAuth2Token()` hook for Google OAuth
- Token passed as `Bearer` header to backend for Vertex AI access
- Extension context stores OAuth client configuration

### Vertex AI Integration
- Backend calls Vertex AI API directly using service account credentials
- Frontend can optionally call Vertex AI directly with user OAuth token
- All prompts include Looker field metadata and golden query examples

### Looker Extension Framework
```typescript
// manifest.lkml requirements
core_api_methods: ["lookml_model_explore", "run_inline_query", ...]
external_api_urls: ["https://us-central1-aiplatform.googleapis.com", ...]
oauth2_urls: ["https://accounts.google.com/o/oauth2/v2/auth"]
```

## Project-Specific Conventions

### Error Handling Pattern
```typescript
// Use ErrorBoundary with react-error-boundary
const { showBoundary } = useErrorHandler()
try {
  await apiCall()
} catch (error) {
  showBoundary(error)  // Triggers global error UI
}
```

### LLM Prompt Structure
Always include:
1. Looker field metadata (dimensions/measures with descriptions)
2. Golden query examples for the specific explore
3. Current date for timeframe queries
4. Conversation context synthesis

**Field Naming**: Use `explore_id` (not `explore_key`) throughout BigQuery operations and queries.

### State Management
- Use Redux Toolkit with typed selectors
- Persist conversation history in localStorage via redux-persist
- Load semantic models and examples on app initialization

## MCP Server Tools and Capabilities

### Core MCP Tools Available
```typescript
// Available tools in looker_mcp_server.py
interface MCPTools {
  // Vertex AI Integration
  vertex_ai_query: (prompt, model, temperature) => VertexResponse
  
  // Semantic Field Discovery  
  semantic_field_search: (search_terms[], explore_ids?, limit_per_term) => FieldMatch[]
  field_value_lookup: (search_string, field_location?, limit) => FieldValue[]
  extract_searchable_terms: (query_text) => string[]
  
  // Core Explore Assistant
  generate_explore_params: (prompt, restricted_explore_keys[], conversation_context?) => ExploreParams
  get_explore_fields: (model_name, explore_name) => ExploreFields
  run_looker_query: (query_body, result_format?) => QueryResult
  
  // Olympic Query Management
  add_bronze_query: (explore_id, input, output, link, user_email) => BronzeQuery
  promote_query: (query_id, source_table, target_rank, promoted_by) => PromotionResult
  get_golden_queries: (explore_id?) => GoldenQuery[]
}
```

### Field Discovery System
```python
# Semantic field search workflow
terms = extract_searchable_terms("Show me customer lifetime value")
# Returns: ["customer", "lifetime", "value"]

field_matches = semantic_field_search(
    search_terms=terms,
    explore_ids=["ecommerce:customers"],
    limit_per_term=5
)
# Returns: FieldMatch objects with similarity scores and sample values

value_matches = field_value_lookup(
    search_string="premium",
    field_location="products.brand"
)
# Returns: Specific dimension values containing "premium"
```

### Vector Search Implementation
- **BigQuery ML Embeddings** - Uses Vertex AI `text-embedding-004` model
- **COSINE Distance Search** - Semantic similarity matching with configurable thresholds  
- **Field Value Indexing** - Actual Looker dimension values from 'index' sets
- **Frequency-Based Ranking** - Values ranked by occurrence frequency in data

## BigQuery Table Architecture (Simplified Management)

### Three-Tier Query Progression System
- **Bronze Queries** → **Silver Queries** → **Golden Queries**
- **Disposable Staging Strategy**: Bronze/Silver tables drop and recreate on schema mismatch
- **Data Preservation**: Golden table only adds missing columns, never drops data

### Standardized Field Schema
All tables use consistent field names with `explore_id` (not `explore_key`):

```python
# Core fields that migrate through all tables
CORE_FIELDS = ["id", "explore_id", "input", "output", "link", "promoted_by", "promoted_at"]

# Bronze-specific fields (don't migrate)
BRONZE_FIELDS = ["user_email", "query_run_count"]

# Silver-specific fields (don't migrate) 
SILVER_FIELDS = ["user_id", "feedback_type", "conversation_history"]
```

### Table Management Functions
```python
# Disposable tables - drop/recreate on schema mismatch
ensure_bronze_queries_table_exists()  # Bronze staging
ensure_silver_queries_table_exists()  # Silver feedback staging

# Preserve data - only add missing core fields
ensure_golden_queries_table_exists()  # Golden training data

# Promotion only uses core fields
promote_query_atomic(query_id, source_table, "golden", promoted_by)
```

### Query Promotion Workflow
1. **Bronze**: Raw query patterns with run counts
2. **Silver**: User feedback with conversation history
3. **Golden**: Core training data (7 fields only)
4. **Promotion**: Atomic operation with audit logging

### Key Benefits of Simplified Architecture
- **No Migration Complexity**: Bronze/Silver recreated fresh vs complex schema migrations
- **HTTP 500 Prevention**: Promotion only inserts fields that exist in golden table
- **Enhanced Context**: Silver queries store full conversation history
- **Data Safety**: Golden table data always preserved during schema updates

## Common Debugging Workflows

### OAuth Issues
```typescript
// Check OAuth state in browser console
console.log(store.getState().assistant.oauth)
// Verify token validity in Network tab
```

### Vertex AI Connectivity
```bash
# Test backend directly
curl -X POST http://localhost:8001 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"test_mode": true}'
```

### BigQuery Permissions
- Service account needs `BigQuery User` role
- Connection must have `aiplatform.user` for BQML queries
- Check `explore_assistant` dataset access

### Vector Search Debugging
```bash
# Test vector search system
cd explore-assistant-cloud-function
python test_semantic_search.py
python test_vector_search.py

# Check vector table status
python vector_table_manager.py --action stats

# Test Flask integration with vector search
curl -X POST http://localhost:8001/field-values \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"search_string": "nike", "limit": 5}'

# Test MCP tool integration
curl -X POST http://localhost:8001 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "field_value_lookup", 
    "arguments": {"search_string": "nike", "limit": 3}
  }'
```

**Common Vector Search Issues:**
- **No Results**: Check if fields are indexed with 'index' sets in Looker
- **Function Not Called**: LLM may not recognize need for specific value lookup
- **Low Similarity**: Adjust similarity threshold in function calls
- **Missing Values**: Vector table may need refresh from Looker data
```bash
# Test vector search system
cd explore-assistant-cloud-function
python test_semantic_search.py
python test_vector_search.py

# Check vector table status
python vector_table_manager.py --action stats
```

## Files That Define Core Patterns

- `explore-assistant-cloud-function/looker_mcp_server.py` - Main AI processing logic and MCP server
- `explore-assistant-cloud-function/vector_table_manager.py` - Vector search system management
- `explore-assistant-cloud-function/field_lookup_mcp.py` - Field discovery service implementation
- `explore-assistant-extension/src/slices/assistantSlice.ts` - State structure
- `explore-assistant-extension/src/hooks/useSendVertexMessage.ts` - AI API calls
- `explore-assistant-extension/src/hooks/useOAuth2Token.ts` - Authentication flow
- `explore-assistant-extension/manifest.lkml` - Looker extension configuration

## Model Context Protocol (MCP)
- `looker_mcp_server.py` is the primary MCP server with all functionality
- Deprecates older `mcp_server.py` in favor of unified architecture
- Use for integrating with desktop AI assistants outside Looker

## Recent Architectural Updates

### Vector Search Function Calling Integration
- **Vertex AI Function Calling** - LLM autonomously decides when to use vector search via function declarations
- **Intelligent Value Discovery** - LLM calls `search_semantic_fields` and `lookup_field_values` when user queries mention specific codes/values
- **Flask Backend Integration** - `mcp_server.py` now includes vector search as both MCP tools and REST endpoints
- **Scoped Field Discovery** - Vector search limited to indexed high-cardinality dimensions only

### MCP Server Consolidation
- **Single Server Architecture** - `looker_mcp_server.py` now contains all functionality
- **Integrated Explore Selection** - `determine_explore_from_prompt()` moved into main server
- **No Explicit explore_key Required** - System automatically determines best explore from restricted list
- **Vector Search Integration** - Field discovery built directly into MCP tools

### Frontend Integration Updates
- **MCP Tool Format** - Updated hooks to use `{tool_name: 'generate_explore_params', arguments: {...}}`
- **Automatic Explore Selection** - Frontend passes `restricted_explore_keys` array instead of single `explore_key`
- **Enhanced Error Handling** - Better error boundaries and user feedback for MCP operations
