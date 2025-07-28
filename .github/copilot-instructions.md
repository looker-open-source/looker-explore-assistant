# Looker Explore Assistant - Copilot Instructions

## Architecture Overview

This is a **natural language to Looker query system** with 3 main components:

1. **Frontend Extension** (`explore-assistant-extension/`) - React/TypeScript Looker extension with Redux state management
2. **Backend Cloud Function** (`explore-assistant-cloud-function/`) - Python Flask API that proxies to Vertex AI
3. **Training/Examples** (`explore-assistant-examples/`) - BigQuery tables with golden query examples for LLM training

The system converts natural language → Looker explore parameters → embedded visualizations.

## Key Architectural Patterns

### AI-Driven Explore Selection
- The service **always determines the best explore** for each request via `determine_explore_from_prompt()`
- Explore keys follow format: `"model:explore_name"` (e.g., `"ecommerce:order_items"`)
- Golden queries stored in BigQuery drive explore selection and parameter generation

### Two-Phase LLM Processing
```python
# Phase 1: Synthesize conversation context
synthesized_query = synthesize_conversation_context(prompt, conversation_context)

# Phase 2: Generate explore parameters from clear query  
explore_params = generate_explore_params_from_query(synthesized_query, explore_key)
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

### Frontend Development
```bash
cd explore-assistant-extension
npm install
npm start  # Webpack dev server on https://localhost:8080
npm run build  # Production bundle
```

### Backend Local Testing
```bash
cd explore-assistant-cloud-function  
pip install -r requirements.txt
python3 run_local.sh  # Flask server on localhost:8001
```
#### use python3 vs python for local dev.

### BigQuery Setup
```bash
# Required tables for golden queries and examples
bq mk --dataset $PROJECT_ID:explore_assistant
# See explore-assistant-backend/README.md for table schemas
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

### State Management
- Use Redux Toolkit with typed selectors
- Persist conversation history in localStorage via redux-persist
- Load semantic models and examples on app initialization

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

## Files That Define Core Patterns

- `explore-assistant-cloud-function/mcp_server.py` - Main AI processing logic
- `explore-assistant-extension/src/slices/assistantSlice.ts` - State structure
- `explore-assistant-extension/src/hooks/useSendVertexMessage.ts` - AI API calls
- `explore-assistant-extension/src/hooks/useOAuth2Token.ts` - Authentication flow
- `explore-assistant-extension/manifest.lkml` - Looker extension configuration

## Model Context Protocol (MCP)
- `mcp-wrapper/` provides MCP interface for AI assistants like Claude
- Wraps existing Cloud Run API for external AI agent access
- Use for integrating with desktop AI assistants outside Looker
