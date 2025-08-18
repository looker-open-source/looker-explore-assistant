# Vector Search Notification System

## Overview

The vector search notification system provides users with transparency about when and how the AI system uses semantic field discovery to enhance query processing. This helps users understand why certain results are particularly accurate or comprehensive.

## How It Works

### Backend Integration

1. **Function Call Tracking**: The system tracks when Vertex AI calls vector search functions:
   - `search_semantic_fields`: Finds fields containing specific values/codes
   - `lookup_field_values`: Verifies specific dimension values exist

2. **Usage Metadata**: Each function call is recorded with:
   ```python
   vector_search_used.append({
       "function": function_name,
       "args": function_args,
       "phase": "explore_selection" | "parameter_generation"
   })
   ```

3. **User-Friendly Summary**: Raw usage data is converted to user-friendly messages:
   ```python
   {
       "total_vector_searches": 2,
       "user_messages": [
           "Searched for specific values: nike, adidas",
           "Verified existence of: Nike"
       ]
   }
   ```

### Frontend Display

The notifications appear as purple info boxes above explore results:

```
🔍 Smart Data Discovery Used
  🔎 Searched for specific values: nike, adidas
  🔎 Verified existence of: Nike
  (2 smart searches performed)
```

## When Vector Search is Used

### Common Scenarios

1. **Brand/Product Queries**: "Show me Nike product sales"
2. **Specific Codes**: "Filter by status code 'SHIPPED'"
3. **SKU Lookups**: "Find products with SKU containing 'ABC123'"
4. **Regional Codes**: "Show data for region 'CA'"

### When It's NOT Used

1. **General Metrics**: "Show me total revenue"
2. **Standard Aggregations**: "Count of customers"
3. **Time-based Queries**: "Sales by month"

## Implementation Details

### Response Structure

```typescript
interface ExploreMessage {
  // ... existing fields
  vectorSearchUsed?: VectorSearchUsage[]
  vectorSearchSummary?: VectorSearchSummaryInfo
}

interface VectorSearchSummaryInfo {
  total_vector_searches: number
  user_messages: string[]
  detailed_usage: VectorSearchUsage[]
}
```

### Backend Functions Modified

1. **`determine_explore_from_prompt()`** - Tracks explore selection usage
2. **`generate_explore_params_from_query()`** - Tracks parameter generation usage
3. **`generate_vector_search_summary()`** - Creates user-friendly messages

### Frontend Components Updated

1. **`ExploreMessage.tsx`** - Displays vector search notifications
2. **`MessageThread.tsx`** - Passes vector search data to components
3. **`assistantSlice.ts`** - Includes vector search in message types

## Testing

### Manual Testing

1. **Test with Brand Query**:
   ```
   "Show me sales for Nike products by month"
   ```
   Should trigger vector search for "Nike"

2. **Test with Code Query**:
   ```
   "Filter orders by status 'COMPLETED'"
   ```
   Should trigger lookup for "COMPLETED" status values

3. **Test with General Query**:
   ```
   "Show me total revenue"
   ```
   Should NOT trigger vector search

### Automated Testing

```bash
cd explore-assistant-cloud-function
python test_vector_search_notification.py
```

## Logging and Debugging

Vector search usage is logged at multiple levels:

```python
# Function call detection
logging.info(f"🔧 Model requested function call: {function_name} with args: {function_args}")

# Usage tracking
logging.info(f"🔍 Vector search used during parameter generation: {vector_search_used}")

# User notification
logging.info(f"🔍 Vector search was used - user should be notified: {user_messages}")
```

## Benefits for Users

1. **Transparency**: Users understand when AI uses advanced features
2. **Trust**: Clear indication of enhanced data discovery
3. **Context**: Helps explain why certain results are particularly accurate
4. **Learning**: Users learn what types of queries benefit from vector search

## Customization

### Changing Notification Style

Modify the CSS classes in `ExploreMessage.tsx`:

```tsx
<div className="mb-3 p-3 bg-purple-50 border-l-4 border-purple-400 text-purple-800 text-sm rounded">
```

### Adding More Details

Extend the `generate_vector_search_summary()` function to include:
- Field locations discovered
- Similarity scores
- Number of matching values found

### Disabling Notifications

Set environment variable:
```bash
DISABLE_VECTOR_SEARCH_NOTIFICATIONS=true
```

## Troubleshooting

### No Notifications Appearing

1. Check that vector search is actually being used (logs should show function calls)
2. Verify frontend types match backend response structure
3. Ensure MessageThread passes vectorSearchSummary prop

### Notifications Show But No Vector Search

This indicates a tracking bug - the system is marking usage without actual function calls.

### Performance Impact

Vector search notifications add minimal overhead:
- ~100 bytes per response for metadata
- One additional function call for summary generation
- No impact on LLM processing time
