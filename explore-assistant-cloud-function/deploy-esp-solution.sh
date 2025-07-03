#!/bin/bash

# WORKING SOLUTION: Use Cloud Run with ESPv2 (Extensible Service Proxy v2)
# This is the only way to have selective authentication in Cloud Run

PROJECT_ID="combined-genai-bi"
SERVICE_NAME="looker-explore-assistant-mcp"
REGION="us-central1"
ESP_SERVICE_NAME="${SERVICE_NAME}-esp"

echo "=== CLOUD RUN CORS SOLUTION USING ESP v2 ==="
echo ""

# Step 1: Build and deploy your existing service (keep authenticated)
echo "Step 1: Deploying your main Cloud Run service..."
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

# Get the service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --platform=managed \
    --region=${REGION} \
    --format='value(status.url)' \
    --project=${PROJECT_ID})

echo "Main service deployed at: ${SERVICE_URL}"

# Step 2: Deploy the OpenAPI config to Cloud Endpoints
echo ""
echo "Step 2: Deploying OpenAPI configuration to Cloud Endpoints..."

# Create the OpenAPI spec with the correct backend URL
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
  address: ${SERVICE_URL}
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

# Deploy the API configuration
gcloud endpoints services deploy openapi-esp.yaml --project=${PROJECT_ID}

# Step 3: Deploy ESPv2 as a Cloud Run service
echo ""
echo "Step 3: Deploying ESPv2 proxy service..."

# Get the config ID
CONFIG_ID=\$(gcloud endpoints configs list --service=${ESP_SERVICE_NAME}-730192175971.${REGION}.run.app --format='value(id)' --limit=1 --project=${PROJECT_ID})

gcloud run deploy ${ESP_SERVICE_NAME} \
    --image="gcr.io/endpoints-release/endpoints-runtime-serverless:2" \
    --allow-unauthenticated \
    --platform=managed \
    --region=${REGION} \
    --set-env-vars="ENDPOINTS_SERVICE_NAME=${ESP_SERVICE_NAME}-730192175971.${REGION}.run.app" \
    --set-env-vars="ENDPOINTS_SERVICE_CONFIG_ID=\${CONFIG_ID}" \
    --set-env-vars="ESPv2_ARGS=--cors_preset=basic" \
    --project=${PROJECT_ID}

ESP_URL=\$(gcloud run services describe ${ESP_SERVICE_NAME} \
    --platform=managed \
    --region=${REGION} \
    --format='value(status.url)' \
    --project=${PROJECT_ID})

echo ""
echo "=== DEPLOYMENT COMPLETE ==="
echo ""
echo "Your CORS-enabled endpoint is now available at:"
echo "\${ESP_URL}"
echo ""
echo "Update your Looker extension to use this URL instead of the direct Cloud Run URL."
echo ""
echo "Testing:"
echo "OPTIONS request: curl -X OPTIONS \${ESP_URL}/ -v"
echo "POST request: curl -X POST \${ESP_URL}/ -H 'Authorization: Bearer YOUR_TOKEN' -H 'Content-Type: application/json' -d '{}'"
