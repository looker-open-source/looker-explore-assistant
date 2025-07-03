#!/bin/bash

# Script to redeploy your Cloud Run service with improved CORS configuration
# This keeps authentication but ensures CORS headers are properly set

PROJECT_ID="combined-genai-bi"
SERVICE_NAME="looker-explore-assistant-mcp"
REGION="us-central1"

echo "Redeploying Cloud Run service with CORS-optimized configuration..."

# Rebuild and deploy with specific CORS-friendly settings
gcloud run deploy ${SERVICE_NAME} \
    --source=. \
    --platform=managed \
    --region=${REGION} \
    --port=8080 \
    --memory=1Gi \
    --cpu=1 \
    --max-instances=10 \
    --set-env-vars="PROJECT=${PROJECT_ID},REGION=${REGION}" \
    --add-cloudsql-instances="" \
    --execution-environment=gen2 \
    --cpu-boost \
    --session-affinity \
    --project=${PROJECT_ID}

echo ""
echo "Deployment complete!"
echo ""
echo "To test the service:"
echo "1. Check the service logs: gcloud run services logs tail ${SERVICE_NAME} --region=${REGION}"
echo "2. Test direct access: curl -X OPTIONS https://${SERVICE_NAME}-730192175971.${REGION}.run.app/"
echo "3. Test with auth: curl -X POST https://${SERVICE_NAME}-730192175971.${REGION}.run.app/ -H 'Authorization: Bearer YOUR_TOKEN'"
