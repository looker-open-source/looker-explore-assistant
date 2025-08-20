#!/bin/bash

# Test script for the new consolidated MCP service
# Tests all major tool categories to ensure compatibility

set -e

# Configuration
SERVICE_URL=${1:-"https://looker-explore-assistant-mcp-xxxxxxxxx-uc.a.run.app"}
TOKEN=${2:-""}

if [ -z "$TOKEN" ]; then
    echo "❌ Usage: $0 <SERVICE_URL> <AUTH_TOKEN>"
    echo "Example: $0 https://your-service-url.run.app your-auth-token"
    exit 1
fi

echo "🧪 Testing new consolidated MCP service"
echo "🔗 Service URL: $SERVICE_URL"
echo "🔑 Token: ${TOKEN:0:20}..."
echo ""

# Test function
test_mcp_tool() {
    local tool_name=$1
    local arguments=$2
    local description=$3
    
    echo "🔍 Testing: $description ($tool_name)"
    
    local response=$(curl -s -w "HTTPSTATUS:%{http_code}" -X POST "$SERVICE_URL" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $TOKEN" \
        -d "{\"tool_name\": \"$tool_name\", \"arguments\": $arguments}")
    
    local http_code=$(echo "$response" | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')
    local body=$(echo "$response" | sed -e 's/HTTPSTATUS:.*//g')
    
    if [ "$http_code" -eq 200 ]; then
        echo "  ✅ SUCCESS (HTTP $http_code)"
        echo "  📄 Response: $(echo "$body" | jq -c '.' 2>/dev/null || echo "$body" | head -c 100)..."
    else
        echo "  ❌ FAILED (HTTP $http_code)"
        echo "  📄 Error: $body"
    fi
    echo ""
}

echo "=== LOW SECURITY TOOLS (should work immediately) ==="

# Test basic statistics
test_mcp_tool "get_query_stats" "{}" "Query Statistics"

# Test field search
test_mcp_tool "semantic_field_search" '{"search_terms": ["revenue", "sales"], "limit_per_term": 2}' "Semantic Field Search"

# Test field value lookup
test_mcp_tool "field_value_lookup" '{"search_string": "electronics", "limit": 3}' "Field Value Lookup"

# Test Olympic query fetching
test_mcp_tool "get_queries_by_rank" '{"rank": "bronze", "limit": 5}' "Get Bronze Queries"
test_mcp_tool "get_queries_by_rank" '{"rank": "silver", "limit": 5}' "Get Silver Queries"
test_mcp_tool "get_queries_by_rank" '{"rank": "gold", "limit": 5}' "Get Gold Queries"

# Test promotion history
test_mcp_tool "get_promotion_history" '{"limit": 5}' "Promotion History"

echo "=== FEEDBACK TOOLS ==="

# Test feedback tools (these should work with low security)
test_mcp_tool "get_query_feedback_history" '{"limit": 5}' "Feedback History"

echo "=== MEDIUM SECURITY TOOLS (require developer role) ==="

# Test promotion (requires developer role)
# test_mcp_tool "promote_to_gold" '{"query_id": "test-id", "promoted_by": "test-user"}' "Query Promotion"

echo "=== HIGH SECURITY TOOLS (require user impersonation) ==="

# Test Looker integration (requires user token)
test_mcp_tool "get_explore_fields" '{"model_name": "ecommerce", "explore_name": "order_items"}' "Get Explore Fields"

echo "=== VERTEX AI TOOLS ==="

# Test Vertex AI proxy
test_mcp_tool "vertex_ai_query" '{"prompt": "What is 2+2?", "max_tokens": 50}' "Vertex AI Query"

echo ""
echo "🏁 Testing Complete!"
echo ""
echo "📊 Summary:"
echo "- Low security tools should all pass ✅"
echo "- Medium security tools may require proper roles 🔐"
echo "- High security tools need valid user tokens 🔒"
echo "- Check logs for any authentication issues"
