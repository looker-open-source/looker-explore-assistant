#!/bin/bash

# Test script to verify the frontend hooks send the correct MCP format
# This helps ensure the "Missing tool_name parameter" error is resolved

echo "🧪 Testing Frontend MCP Integration"
echo "=================================="

# Check if the required files have been updated correctly
echo "1. Checking useSendCloudRunMessage.ts for MCP format..."
if grep -q "tool_name: 'generate_explore_parameters'" explore-assistant-extension/src/hooks/useSendCloudRunMessage.ts; then
    echo "✅ useSendCloudRunMessage.ts uses correct MCP format"
else
    echo "❌ useSendCloudRunMessage.ts missing MCP format"
    exit 1
fi

echo ""
echo "2. Checking useGenerateBronzeQueries.ts for MCP format..."
if grep -q "tool_name: 'generate_bronze_queries'" explore-assistant-extension/src/hooks/useGenerateBronzeQueries.ts; then
    echo "✅ useGenerateBronzeQueries.ts uses correct MCP format"
else
    echo "❌ useGenerateBronzeQueries.ts missing MCP format"
    exit 1
fi

echo ""
echo "3. Checking useFeedback.ts for MCP format..."
if grep -q "tool_name:" explore-assistant-extension/src/hooks/useFeedback.ts; then
    echo "✅ useFeedback.ts uses correct MCP format"
else
    echo "❌ useFeedback.ts missing MCP format"
    exit 1
fi

echo ""
echo "4. Checking useQueryPromotion.ts for MCP format..."
if grep -q "tool_name:" explore-assistant-extension/src/hooks/useQueryPromotion.ts; then
    echo "✅ useQueryPromotion.ts uses correct MCP format"
else
    echo "❌ useQueryPromotion.ts missing MCP format"
    exit 1
fi

echo ""
echo "🎉 All frontend hooks are properly configured for MCP format!"
echo ""
echo "📋 Expected request format:"
echo "{"
echo '  "tool_name": "generate_explore_parameters",'
echo '  "arguments": {'
echo '    "prompt": "...",'
echo '    "conversation_id": "...",'
echo '    "...: "..."'
echo "  }"
echo "}"
echo ""
echo "🚀 This should resolve the 'Missing tool_name parameter' error."
