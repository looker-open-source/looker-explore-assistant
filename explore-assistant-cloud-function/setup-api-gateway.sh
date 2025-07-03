#!/bin/bash

# Solution 3: API Gateway with CORS support
# Most enterprise-ready solution with fine-grained control

PROJECT_ID="combined-genai-bi"
SERVICE_NAME="looker-explore-assistant-mcp"
REGION="us-central1"
API_ID="${SERVICE_NAME}-api"
GATEWAY_ID="${SERVICE_NAME}-gateway"

echo "=== SETTING UP API GATEWAY WITH CORS ==="
echo ""

# Get your Cloud Run service URL
CLOUD_RUN_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --platform=managed \
    --region=${REGION} \
    --format='value(status.url)' \
    --project=${PROJECT_ID})

echo "Cloud Run service URL: ${CLOUD_RUN_URL}"

# Create OpenAPI spec for API Gateway
cat > api-gateway-spec.yaml << EOF
swagger: '2.0'
info:
  title: Looker Explore Assistant API
  description: API Gateway proxy for Looker Explore Assistant
  version: 1.0.0
schemes:
  - https
produces:
  - application/json
consumes:
  - application/json

# CORS configuration
x-google-management:
  metrics:
    - name: "requests"
      displayName: "Requests"
      valueType: INT64
      metricKind: CUMULATIVE
  quota:
    limits:
      - name: "requests-per-minute"
        metric: "requests"
        unit: "1/min"
        values:
          STANDARD: 1000

paths:
  /:
    options:
      summary: CORS preflight
      operationId: corsPreflightRoot
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
      x-google-backend:
        address: ${CLOUD_RUN_URL}
        protocol: h2
        path_translation: APPEND_PATH_TO_ADDRESS
      # Override to handle CORS directly
      x-google-backend:
        disable_auth: true
      responses:
        default:
          description: CORS response
          headers:
            Access-Control-Allow-Origin:
              description: CORS header
              type: string
              default: "*"
            Access-Control-Allow-Methods:
              description: CORS header
              type: string
              default: "GET, POST, OPTIONS"
            Access-Control-Allow-Headers:
              description: CORS header
              type: string
              default: "Content-Type, Authorization"
            Access-Control-Max-Age:
              description: CORS header
              type: string
              default: "3600"
      
    post:
      summary: Process explore assistant request
      operationId: processRequest
      parameters:
        - in: body
          name: body
          required: true
          schema:
            type: object
      security:
        - google_id_token: []
      responses:
        '200':
          description: Successful response
        '401':
          description: Unauthorized
        '500':
          description: Internal server error
      x-google-backend:
        address: ${CLOUD_RUN_URL}
        protocol: h2
        path_translation: APPEND_PATH_TO_ADDRESS

  /health:
    get:
      summary: Health check
      operationId: healthCheck
      security:
        - google_id_token: []
      responses:
        '200':
          description: Health status
      x-google-backend:
        address: ${CLOUD_RUN_URL}/health
        protocol: h2

securityDefinitions:
  google_id_token:
    type: oauth2
    authorizationUrl: ""
    flow: implicit
    x-google-issuer: "https://accounts.google.com"
    x-google-jwks_uri: "https://www.googleapis.com/oauth2/v3/certs"
    x-google-audiences: "${PROJECT_ID}"
EOF

echo "Step 1: Creating API Gateway configuration..."
gcloud api-gateway api-configs create ${API_ID}-config \
    --api=${API_ID} \
    --openapi-spec=api-gateway-spec.yaml \
    --project=${PROJECT_ID}

echo "Step 2: Creating API Gateway..."
gcloud api-gateway gateways create ${GATEWAY_ID} \
    --api=${API_ID} \
    --api-config=${API_ID}-config \
    --location=${REGION} \
    --project=${PROJECT_ID}

# Get the gateway URL
GATEWAY_URL=$(gcloud api-gateway gateways describe ${GATEWAY_ID} \
    --location=${REGION} \
    --format='value(defaultHostname)' \
    --project=${PROJECT_ID})

echo ""
echo "=== API GATEWAY SETUP COMPLETE ==="
echo ""
echo "Gateway URL: https://${GATEWAY_URL}"
echo ""
echo "Update your Looker extension to use this URL."
echo ""
echo "How it works:"
echo "- API Gateway handles CORS at the infrastructure level"
echo "- OPTIONS requests get CORS headers without authentication"
echo "- POST requests are forwarded to your authenticated Cloud Run service"
echo "- Enterprise-grade with monitoring, quotas, and security policies"
echo ""
echo "Test with:"
echo "curl -X OPTIONS https://${GATEWAY_URL}/ -v"
