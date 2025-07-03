#!/bin/bash

# Simple solution: Deploy with unauthenticated access and handle auth in application
PROJECT_ID="combined-genai-bi"
SERVICE_NAME="looker-explore-assistant-mcp"
REGION="us-central1"

echo "Updating Cloud Run service to allow unauthenticated access..."

# The key insight: Your application already handles authentication via OAuth tokens
# So we can allow unauthenticated access at the Cloud Run level
# and rely on your application to validate the Bearer tokens

gcloud run services update ${SERVICE_NAME} \
    --allow-unauthenticated \
    --region=${REGION} \
    --project=${PROJECT_ID}

echo "Service updated to allow unauthenticated access."
echo "Your application will handle authentication via Bearer tokens."
echo ""
echo "Test CORS preflight with:"
echo "curl -X OPTIONS https://looker-explore-assistant-mcp-730192175971.us-central1.run.app/ \\"
echo "  -H 'Origin: https://your-frontend-domain.com' \\"
echo "  -H 'Access-Control-Request-Method: POST' \\"
echo "  -H 'Access-Control-Request-Headers: Content-Type,Authorization' \\"
echo "  -v"
echo ""
echo "Test authenticated POST with:"
echo "curl -X POST https://looker-explore-assistant-mcp-730192175971.us-central1.run.app/ \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -H 'Authorization: Bearer YOUR_OAUTH_TOKEN' \\"
echo "  -d '{\"test\": true}' \\"
echo "  -v"
