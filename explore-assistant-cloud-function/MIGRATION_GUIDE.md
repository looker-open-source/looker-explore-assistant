# Service Migration Guide: Old vs New

## Services Comparison

### **Old Service** (explore-assistant-service)
- **File**: `mcp_server.py`
- **Architecture**: Flask + MCP tool handler (hybrid)
- **Query Management**: Separate bronze/silver/golden tables
- **Endpoints**: `/admin/promote`, `/admin/queries/*`, `/admin/promotion-history`
- **Status**: 🔄 To be deprecated

### **New Service** (looker-explore-assistant-mcp)  
- **File**: `looker_mcp_server.py`
- **Architecture**: Pure MCP + Flask HTTP adapter
- **Query Management**: Olympic single table design
- **Tools**: Unified MCP tool interface
- **Status**: ✅ Production ready

---

## Frontend Migration Steps

### **Phase 1: Test New Service**
1. Deploy new service alongside old service
2. Test with existing frontend (no changes needed)
3. Verify all functionality works

### **Phase 2: Environment Variable Switch**
```typescript
// In frontend settings, update Cloud Run URL:
// OLD: https://explore-assistant-service-xxx.run.app
// NEW: https://looker-explore-assistant-mcp-xxx.run.app
```

### **Phase 3: Tool Mapping Verification**
The frontend tools should map correctly:

| Frontend Tool Call | Old Service | New Service | Status |
|-------------------|-------------|-------------|---------|
| `submit_positive_feedback` | ✅ | ✅ | Compatible |
| `submit_negative_feedback` | ✅ | ✅ | Compatible |  
| `request_response_improvement` | ✅ | ✅ | Compatible |
| `submit_query_feedback` | ✅ | ✅ | Compatible |
| `get_query_feedback_history` | ✅ | ✅ | Compatible |
| `get_query_stats` | ✅ | ✅ | Compatible |
| `get_queries_by_rank` | `get_queries_for_promotion` | ✅ | **Updated** |
| `promote_to_gold` | `promote_query` | ✅ | **Updated** |
| `get_promotion_history` | ✅ | ✅ | Compatible |

### **Phase 4: Gradual Migration**
1. **A/B Testing**: Route percentage of traffic to new service
2. **Monitor**: Check logs, errors, performance
3. **Validate**: Ensure feature parity
4. **Rollout**: Increase traffic to new service

### **Phase 5: Cleanup**
1. Route 100% traffic to new service
2. Remove old service deployment
3. Delete deprecated files (`mcp_server.py`, `mcp_wrapper/`)

---

## Benefits of New Service

### **Technical Improvements**
✅ **Single Table Design**: Olympic queries system  
✅ **Pure MCP Architecture**: Cleaner tool interface  
✅ **Better Security**: Granular authentication levels  
✅ **Semantic Search**: Vector-based field discovery  
✅ **User Impersonation**: Proper Looker user context  

### **Operational Benefits**  
✅ **Simplified Deployment**: One service, one codebase  
✅ **Better Testing**: Comprehensive tool coverage  
✅ **Future Proof**: MCP standard compliance  
✅ **Easier Maintenance**: No duplicate logic  

---

## Testing Checklist

### **Pre-Deployment**
- [ ] Dockerfile builds successfully
- [ ] All required files included  
- [ ] Environment variables configured
- [ ] Dependencies installed correctly

### **Post-Deployment**
- [ ] Service starts without errors
- [ ] Health check endpoint responds
- [ ] Low security tools work (no auth needed)
- [ ] Medium security tools validate roles
- [ ] High security tools require user tokens
- [ ] Frontend can connect successfully

### **Functional Testing**
- [ ] Query promotion workflow
- [ ] Feedback submission and retrieval  
- [ ] Semantic field search
- [ ] Vertex AI proxy functionality
- [ ] Olympic query management
- [ ] Error handling and logging

### **Performance Testing**
- [ ] Response times acceptable
- [ ] Memory usage within limits
- [ ] Concurrent request handling
- [ ] BigQuery query optimization

---

## Rollback Plan

If issues arise, rollback is simple:

1. **Immediate**: Update frontend Cloud Run URL back to old service
2. **Database**: Olympic queries table remains intact
3. **Monitoring**: Check old service logs for any missed features
4. **Fix Forward**: Address issues in new service and redeploy

The beauty of this approach is **zero downtime** - both services can run simultaneously during migration.

---

## Success Metrics

### **Functional Success**
- [ ] All frontend features work identically
- [ ] Query promotion system functional  
- [ ] Feedback system operational
- [ ] No increase in error rates

### **Performance Success**
- [ ] Response times ≤ old service
- [ ] Memory usage optimized
- [ ] BigQuery costs not increased
- [ ] User satisfaction maintained

### **Security Success**
- [ ] Authentication works correctly
- [ ] User impersonation functional
- [ ] Role validation working
- [ ] No security regressions
