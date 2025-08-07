#!/bin/bash

# Deploy new consolidated MCP service to Cloud Run
# This creates a separate service alongside the existing one

set -e

# Configuration
PROJECT_ID=${PROJECT_ID:-"combined-genai-bi"}
REGION=${REGION:-"us-central1"}
NEW_SERVICE_NAME="looker-explore-assistant-mcp"
OLD_SERVICE_NAME="explore-assistant-service"

echo "🚀 Deploying new consolidated MCP service: $NEW_SERVICE_NAME"
echo "📍 Project: $PROJECT_ID"
echo "🌍 Region: $REGION"

# Validate required environment variables
echo ""
echo "🔍 Validating environment variables..."

MISSING_VARS=()

if [ -z "$LOOKERSDK_BASE_URL" ]; then
    MISSING_VARS+=("LOOKERSDK_BASE_URL")
fi

if [ -z "$LOOKERSDK_CLIENT_ID" ]; then
    MISSING_VARS+=("LOOKERSDK_CLIENT_ID") 
fi

if [ -z "$LOOKERSDK_CLIENT_SECRET" ]; then
    MISSING_VARS+=("LOOKERSDK_CLIENT_SECRET")
fi

if [ ${#MISSING_VARS[@]} -ne 0 ]; then
    echo "❌ Missing required environment variables:"
    for var in "${MISSING_VARS[@]}"; do
        echo "   - $var"
    done
    echo ""
    echo "💡 Please set the missing variables:"
    echo "   export LOOKERSDK_BASE_URL=https://your-instance.looker.com"
    echo "   export LOOKERSDK_CLIENT_ID=your-client-id"
    echo "   export LOOKERSDK_CLIENT_SECRET=your-client-secret"
    echo ""
    exit 1
fi

echo "✅ All required environment variables are set"
echo "   LOOKERSDK_BASE_URL: $LOOKERSDK_BASE_URL"
echo "   LOOKERSDK_CLIENT_ID: ${LOOKERSDK_CLIENT_ID:0:8}..."
echo "   LOOKERSDK_CLIENT_SECRET: ***"
echo ""

# Build and deploy the new service
gcloud run deploy $NEW_SERVICE_NAME \
  --source . \
  --platform managed \
  --region $REGION \
  --project $PROJECT_ID \
  --allow-unauthenticated \
  --port 8080 \
  --memory 2Gi \
  --cpu 2 \
  --concurrency 80 \
  --max-instances 10 \
  --timeout 900s \
  --set-env-vars PROJECT=$PROJECT_ID,REGION=$REGION \
  --set-env-vars BQ_PROJECT_ID=$PROJECT_ID \
  --set-env-vars BQ_DATASET_ID=explore_assistant \
  --set-env-vars VERTEX_MODEL=gemini-2.0-flash-001 \
  --set-env-vars LOOKERSDK_BASE_URL=$LOOKERSDK_BASE_URL \
  --set-env-vars LOOKERSDK_CLIENT_ID=$LOOKERSDK_CLIENT_ID \
  --set-env-vars LOOKERSDK_CLIENT_SECRET=$LOOKERSDK_CLIENT_SECRET \
  --tag mcp-consolidated

# Get the new service URL
NEW_SERVICE_URL=$(gcloud run services describe $NEW_SERVICE_NAME \
  --region $REGION \
  --project $PROJECT_ID \
  --format 'value(status.url)')

echo "✅ New service deployed successfully!"
echo "🔗 New Service URL: $NEW_SERVICE_URL"
echo ""
echo "� Configured Environment Variables:"
echo "   • GCP Project: $PROJECT_ID"
echo "   • GCP Region: $REGION"
echo "   • BigQuery Dataset: explore_assistant"
echo "   • Vertex AI Model: gemini-2.0-flash-001"
echo "   • Looker SDK Base URL: $LOOKERSDK_BASE_URL"
echo "   • Looker SDK Client ID: ${LOOKERSDK_CLIENT_ID:0:8}..."
echo ""
echo "�📋 Next Steps:"
echo "1. Test the new service with existing frontend"
echo "2. Update frontend settings to point to new URL"
echo "3. Verify all MCP tools work correctly (including Looker integration)"
echo "4. Test Looker SDK functionality"
echo "5. Gradually migrate traffic"
echo "5. Deprecate old service: $OLD_SERVICE_NAME"
echo ""
echo "🧪 Test the new service:"
echo "curl -X POST $NEW_SERVICE_URL \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -H 'Authorization: Bearer \$TOKEN' \\"
echo "  -d '{\"tool_name\": \"get_query_stats\", \"arguments\": {}}'"
