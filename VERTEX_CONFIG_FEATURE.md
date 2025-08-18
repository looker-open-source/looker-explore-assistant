# Vertex AI Generation Configuration Feature

## Summary
Added frontend configuration options for Vertex AI generation parameters (temperature, topP, topK) that users can adjust through the Settings dialog. These parameters are only applied to explore parameter generation, not explore selection, as requested.

## Changes Made

### Frontend Changes

#### 1. Redux State (assistantSlice.ts)
Added three new settings to the initial state:
- `vertex_temperature`: Controls randomness (0.0-2.0, default: 0.1)
- `vertex_top_p`: Controls nucleus sampling (0.0-1.0, default: 0.5)  
- `vertex_top_k`: Limits token choices (1-40, default: 20)

#### 2. Settings UI (Settings.tsx)
- Added the new settings to `persistableSettings` array so they're saved to extension context
- Added them to `relevantSettings` filter so they appear in the Settings dialog
- Users can now configure these values through the UI

#### 3. API Communication (useSendCloudRunMessage.ts)
- Extract the configuration values from Redux state
- Parse them to appropriate numeric types with fallback defaults
- Include them in the payload sent to Cloud Run service
- Added them to the dependency array and console logging

### Backend Changes (mcp_server.py)

#### 1. Request Processing (process_explore_assistant_request)
- Extract vertex config parameters from request data
- Validate parameter ranges to ensure they're within acceptable bounds:
  - Temperature: 0.0-2.0 (clamped)
  - TopP: 0.0-1.0 (clamped)
  - TopK: 1-40 (clamped)
- Create `generation_config` dictionary to pass to functions

#### 2. Function Updates
- Updated `generate_explore_params()` to accept optional `generation_config` parameter
- Updated `generate_explore_params_from_query()` to use the configurable values instead of hardcoded ones
- Only the explore parameter generation uses these custom configs - explore selection continues to use hardcoded conservative values

#### 3. Logging Enhancement
- Added generation config values to the logging output for debugging
- Shows: `Temp: X.X | TopP: X.X | TopK: XX` in the request logs

## Configuration Scope

**Applied To:**
- Explore parameter generation (the main LLM call that creates the actual Looker query)

**NOT Applied To:**
- Explore selection (uses conservative hardcoded values: temp=0.1, topP=0.4, topK=20)
- Conversation context synthesis (uses hardcoded values: temp=0.1, topP=0.5, topK=20)

This ensures that the most critical decision (which explore to use) remains conservative and deterministic, while allowing users to adjust creativity for the parameter generation step.

## Default Values
- **Temperature**: 0.1 (focused and deterministic)
- **TopP**: 0.5 (moderate nucleus sampling)
- **TopK**: 20 (moderate token choice limitation)

## Validation
- All parameters are validated and clamped to safe ranges
- Invalid values are automatically corrected to nearest valid value
- Frontend parsing includes fallback defaults for missing/invalid values

## Testing
- All existing tests continue to pass
- Frontend builds successfully without TypeScript errors
- Manual verification shows config parameters are properly extracted and applied
- Log output confirms custom values are being used instead of defaults

## Usage
Users can now:
1. Open Settings dialog in the Explore Assistant
2. Configure Temperature, Top P, and Top K values
3. Click "Test & Save" to persist the settings
4. See the custom values applied in subsequent query generations (visible in logs)

The feature provides fine-grained control over the AI's creativity and determinism for explore parameter generation while maintaining reliability for explore selection.
