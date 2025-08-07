# MCP Server Consolidation Plan

## Goal: Consolidate mcp_server.py functionality into looker_mcp_server.py

### Phase 1: Audit and Merge Missing Tools
1. **Missing Feedback Tools**: Add explicit feedback tools to looker_mcp_server.py
   - submit_positive_feedback
   - submit_negative_feedback  
   - request_response_improvement
   - get_query_feedback_history
   - get_query_stats

2. **Missing Promotion Tools**: Verify Olympic tools cover all promotion needs
   - get_queries_for_promotion → get_queries_by_rank
   - promote_query → promote_to_gold  
   - get_promotion_history → query_statistics

### Phase 2: Update Frontend Integration
1. **Update useFeedback.ts**: Point to looker_mcp_server MCP tools
2. **Update useQueryPromotion.ts**: Use Olympic Query Management tools
3. **Remove Flask endpoint dependencies**: Eliminate /admin/* route usage

### Phase 3: Deploy and Test
1. **Deploy looker_mcp_server.py**: As primary Cloud Run service
2. **Test MCP Tools**: Verify all frontend functionality works
3. **Monitor Performance**: Ensure no regression in functionality

### Phase 4: Cleanup
1. **Deprecate mcp_server.py**: Remove Flask routes and hybrid design
2. **Update Documentation**: Point to single MCP server
3. **Remove Redundant Code**: Clean up duplicate functionality

## Migration Commands

### Deploy Primary MCP Server
```bash
cd explore-assistant-cloud-function
# Update Cloud Run to use looker_mcp_server.py as main
gcloud run deploy explore-assistant-service \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars MAIN_SERVER=looker_mcp_server
```

### Test MCP Tools
```bash
# Test promotion tools
curl -X POST https://your-service-url \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"tool_name": "get_gold_queries", "arguments": {"limit": 10}}'

# Test feedback tools
curl -X POST https://your-service-url \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"tool_name": "submit_positive_feedback", "arguments": {"query_id": "test"}}'
```

## Benefits of Consolidation

### Technical Benefits
- **Single Source of Truth**: One server, one architecture
- **Reduced Maintenance**: No duplicate logic to maintain
- **Better Performance**: Single table design vs multiple tables
- **Cleaner APIs**: Pure MCP tools vs mixed Flask/MCP

### Operational Benefits  
- **Simplified Deployment**: One service to deploy and monitor
- **Unified Logging**: All operations in one place
- **Easier Testing**: Single test suite vs multiple
- **Better Documentation**: One API to document

## Risk Mitigation

### Backwards Compatibility
- Keep Flask endpoints temporarily during migration
- Gradual frontend migration with feature flags
- Comprehensive testing before full cutover

### Rollback Plan
- Keep mcp_server.py available as backup
- Environment variable to switch between servers
- Quick deployment rollback if issues arise

## Success Criteria

1. ✅ All frontend functionality works with consolidated server
2. ✅ Query promotion system fully functional
3. ✅ Feedback system operational
4. ✅ Semantic search and field discovery working
5. ✅ Performance equals or exceeds current system
6. ✅ No data loss during migration
