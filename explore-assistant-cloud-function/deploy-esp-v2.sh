#!/bin/bash

# ESP v2 Deployment Script for CORS Solution
# This creates a proxy service that handles CORS while keeping your main service secure

set -e  # Exit on any error

PROJECT_ID="combined-genai-bi"
SERVICE_NAME="looker-explore-assistant-mcp"
ESP_SERVICE_NAME="${SERVICE_NAME}-esp"
REGION="us-central1"

echo "=== ESP v2 CORS SOLUTION DEPLOYMENT ==="
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Main Service: ${SERVICE_NAME}"
echo "ESP Service: ${ESP_SERVICE_NAME}"
echo ""

# Step 1: Get the URL of your existing authenticated service
echo "Step 1: Getting existing service URL..."
BACKEND_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --platform=managed \
    --region=${REGION} \
    --format='value(status.url)' \
    --project=${PROJECT_ID} 2>/dev/null || echo "")

if [[ -z "$BACKEND_URL" ]]; then
    echo "❌ Main service not found. Deploying it first..."
    
    # Deploy the main service (authenticated)
    gcloud run deploy ${SERVICE_NAME} \
        --source=. \
        --platform=managed \
        --region=${REGION} \
        --no-allow-unauthenticated \
        --port=8080 \
        --memory=1Gi \
        --cpu=1 \
        --max-instances=10 \
        --set-env-vars="PROJECT=${PROJECT_ID},REGION=${REGION}" \
        --project=${PROJECT_ID}
    
    BACKEND_URL=$(gcloud run services describe ${SERVICE_NAME} \
        --platform=managed \
        --region=${REGION} \
        --format='value(status.url)' \
        --project=${PROJECT_ID})
fi

echo "✅ Backend service URL: ${BACKEND_URL}"

# Step 2: Create OpenAPI specification for ESP
echo ""
echo "Step 2: Creating OpenAPI specification..."

cat > openapi-esp.yaml << EOF
swagger: '2.0'
info:
  title: Looker Explore Assistant MCP Server
  description: MCP Server with CORS support via ESP
  version: 1.0.0
host: ${ESP_SERVICE_NAME}-730192175971.${REGION}.run.app
schemes:
  - https
produces:
  - application/json
consumes:
  - application/json
x-google-backend:
  address: ${BACKEND_URL}
  protocol: h2
paths:
  /:
    options:
      summary: CORS preflight
      operationId: corsPreflight
      security: []  # No authentication required for OPTIONS
      responses:
        '200':
          description: CORS preflight response
          headers:
            Access-Control-Allow-Origin:
              type: string
            Access-Control-Allow-Methods:
              type: string
            Access-Control-Allow-Headers:
              type: string
    post:
      summary: Process explore assistant request
      operationId: processRequest
      security:
        - google_id_token: []
      parameters:
        - in: body
          name: body
          required: true
          schema:
            type: object
      responses:
        '200':
          description: Successful response
        '401':
          description: Unauthorized
        '500':
          description: Internal server error
  /health:
    get:
      summary: Health check
      operationId: healthCheck
      security:
        - google_id_token: []
      responses:
        '200':
          description: Health status
securityDefinitions:
  google_id_token:
    type: oauth2
    authorizationUrl: ""
    flow: implicit
    x-google-issuer: "https://accounts.google.com"
    x-google-jwks_uri: "https://www.googleapis.com/oauth2/v3/certs"
    x-google-audiences: "${PROJECT_ID}"
EOF

echo "✅ Created OpenAPI specification"

# Step 3: Deploy the API configuration to Cloud Endpoints
echo ""
echo "Step 3: Deploying API configuration to Cloud Endpoints..."

gcloud endpoints services deploy openapi-esp.yaml --project=${PROJECT_ID}

echo "✅ API configuration deployed"

# Step 4: Get the config ID
echo ""
echo "Step 4: Getting ESP configuration..."

CONFIG_ID=$(gcloud endpoints configs list \
    --service=${ESP_SERVICE_NAME}-730192175971.${REGION}.run.app \
    --format='value(id)' \
    --limit=1 \
    --project=${PROJECT_ID})

echo "✅ Config ID: ${CONFIG_ID}"

# Step 5: Deploy ESPv2 as a Cloud Run service
echo ""
echo "Step 5: Deploying ESPv2 proxy service..."

gcloud run deploy ${ESP_SERVICE_NAME} \
    --image="gcr.io/endpoints-release/endpoints-runtime-serverless:2" \
    --allow-unauthenticated \
    --platform=managed \
    --region=${REGION} \
    --set-env-vars="ENDPOINTS_SERVICE_NAME=${ESP_SERVICE_NAME}-730192175971.${REGION}.run.app" \
    --set-env-vars="ENDPOINTS_SERVICE_CONFIG_ID=${CONFIG_ID}" \
    --set-env-vars="ESPv2_ARGS=--cors_preset=basic" \
    --project=${PROJECT_ID}

# Step 6: Get ESP service URL
ESP_URL=$(gcloud run services describe ${ESP_SERVICE_NAME} \
    --platform=managed \
    --region=${REGION} \
    --format='value(status.url)' \
    --project=${PROJECT_ID})

echo ""
echo "=== DEPLOYMENT COMPLETE ==="
echo ""
echo "🎉 Your CORS-enabled endpoint is now available at:"
echo "${ESP_URL}"
echo ""
echo "📋 Next steps:"
echo "1. Update your Looker extension to use this URL: ${ESP_URL}"
echo "2. Test OPTIONS request: curl -X OPTIONS ${ESP_URL}/ -v"
echo "3. Test POST request: curl -X POST ${ESP_URL}/ -H 'Authorization: Bearer YOUR_TOKEN' -H 'Content-Type: application/json' -d '{}'"
echo ""
echo "🔧 Architecture:"
echo "Browser → ESP (${ESP_URL}) → Your Service (${BACKEND_URL})"
echo ""
echo "✅ CORS requests will now work!"
