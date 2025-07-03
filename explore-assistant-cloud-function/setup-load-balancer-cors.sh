#!/bin/bash

# Solution: Application Load Balancer with CORS policy
# This handles CORS at the load balancer level without requiring unauthenticated services

PROJECT_ID="combined-genai-bi"
SERVICE_NAME="looker-explore-assistant-mcp"
REGION="us-central1"
LOAD_BALANCER_NAME="${SERVICE_NAME}-lb"

echo "=== SETTING UP APPLICATION LOAD BALANCER WITH CORS ==="
echo ""

# Step 1: Create a serverless network endpoint group for your Cloud Run service
echo "Step 1: Creating serverless NEG for Cloud Run service..."
gcloud compute network-endpoint-groups create ${SERVICE_NAME}-neg \
    --region=${REGION} \
    --network-endpoint-type=serverless \
    --cloud-run-service=${SERVICE_NAME} \
    --project=${PROJECT_ID}

# Step 2: Create backend service with your Cloud Run NEG
echo "Step 2: Creating backend service..."
gcloud compute backend-services create ${SERVICE_NAME}-backend \
    --global \
    --project=${PROJECT_ID}

# Add the NEG to the backend service
gcloud compute backend-services add-backend ${SERVICE_NAME}-backend \
    --global \
    --network-endpoint-group=${SERVICE_NAME}-neg \
    --network-endpoint-group-region=${REGION} \
    --project=${PROJECT_ID}

# Step 3: Create URL map with CORS policy
echo "Step 3: Creating URL map with CORS configuration..."
cat > url-map.yaml << EOF
defaultService: projects/${PROJECT_ID}/global/backendServices/${SERVICE_NAME}-backend
name: ${LOAD_BALANCER_NAME}
hostRules:
- hosts:
  - "*"
  pathMatcher: main
pathMatchers:
- name: main
  defaultService: projects/${PROJECT_ID}/global/backendServices/${SERVICE_NAME}-backend
  routeRules:
  - priority: 1
    matchRules:
    - headerMatches:
      - headerName: ":method"
        exactMatch: "OPTIONS"
    routeAction:
      corsPolicy:
        allowOrigins:
        - "*"
        allowMethods:
        - "GET"
        - "POST"
        - "OPTIONS"
        allowHeaders:
        - "Content-Type"
        - "Authorization"
        - "X-Requested-With"
        maxAge: 3600
        allowCredentials: false
      # For OPTIONS requests, return empty response with CORS headers
      directResponseAction:
        status: 200
        body: ""
  - priority: 2
    matchRules:
    - pathTemplateMatch: "/**"
    service: projects/${PROJECT_ID}/global/backendServices/${SERVICE_NAME}-backend
EOF

gcloud compute url-maps import ${LOAD_BALANCER_NAME} \
    --source=url-map.yaml \
    --global \
    --project=${PROJECT_ID}

# Step 4: Create SSL certificate (using Google-managed)
echo "Step 4: Creating SSL certificate..."
# You'll need to specify your domain here
read -p "Enter your domain (e.g., your-domain.com): " DOMAIN
gcloud compute ssl-certificates create ${SERVICE_NAME}-ssl-cert \
    --domains=${DOMAIN} \
    --global \
    --project=${PROJECT_ID}

# Step 5: Create HTTPS target proxy
echo "Step 5: Creating HTTPS target proxy..."
gcloud compute target-https-proxies create ${SERVICE_NAME}-https-proxy \
    --url-map=${LOAD_BALANCER_NAME} \
    --ssl-certificates=${SERVICE_NAME}-ssl-cert \
    --global \
    --project=${PROJECT_ID}

# Step 6: Create global forwarding rule
echo "Step 6: Creating global forwarding rule..."
gcloud compute forwarding-rules create ${SERVICE_NAME}-https-rule \
    --global \
    --target-https-proxy=${SERVICE_NAME}-https-proxy \
    --ports=443 \
    --project=${PROJECT_ID}

# Get the load balancer IP
LB_IP=$(gcloud compute forwarding-rules describe ${SERVICE_NAME}-https-rule \
    --global \
    --format='value(IPAddress)' \
    --project=${PROJECT_ID})

echo ""
echo "=== LOAD BALANCER SETUP COMPLETE ==="
echo ""
echo "Load Balancer IP: ${LB_IP}"
echo "Your service will be available at: https://${DOMAIN}"
echo ""
echo "Next steps:"
echo "1. Point your domain ${DOMAIN} to the IP ${LB_IP}"
echo "2. Wait for SSL certificate to provision (10-60 minutes)"
echo "3. Update your Looker extension to use https://${DOMAIN}"
echo ""
echo "How it works:"
echo "- OPTIONS requests get CORS headers from the load balancer directly"
echo "- POST requests are forwarded to your authenticated Cloud Run service"
echo "- No unauthenticated Cloud Run services required!"
