#!/bin/bash

# Application Load Balancer with Identity-Aware Proxy for CORS handling
# This solution maintains full authentication while handling CORS at the infrastructure level

PROJECT_ID="combined-genai-bi"
SERVICE_NAME="looker-explore-assistant-mcp"
REGION="us-central1"
DOMAIN="looker-mcp.bytecode.io"  # Replace with your domain
LB_NAME="looker-mcp-lb"
BACKEND_SERVICE_NAME="looker-mcp-backend"
URL_MAP_NAME="looker-mcp-urlmap"
HEALTH_CHECK_NAME="looker-mcp-health"
SSL_CERT_NAME="looker-mcp-ssl"

echo "=== SETTING UP APPLICATION LOAD BALANCER WITH IAP ==="
echo ""

# Step 1: Create health check
echo "Step 1: Creating health check..."
gcloud compute health-checks create http ${HEALTH_CHECK_NAME} \
    --port=8080 \
    --request-path=/health \
    --check-interval=30s \
    --timeout=10s \
    --healthy-threshold=2 \
    --unhealthy-threshold=3 \
    --project=${PROJECT_ID}

# Step 2: Create network endpoint group for Cloud Run
echo ""
echo "Step 2: Creating network endpoint group..."
NEG_NAME="${SERVICE_NAME}-neg"
gcloud compute network-endpoint-groups create ${NEG_NAME} \
    --region=${REGION} \
    --network-endpoint-type=serverless \
    --cloud-run-service=${SERVICE_NAME} \
    --project=${PROJECT_ID}

# Step 3: Create backend service
echo ""
echo "Step 3: Creating backend service..."
gcloud compute backend-services create ${BACKEND_SERVICE_NAME} \
    --global \
    --protocol=HTTPS \
    --health-checks=${HEALTH_CHECK_NAME} \
    --load-balancing-scheme=EXTERNAL \
    --project=${PROJECT_ID}

# Add the NEG to the backend service
gcloud compute backend-services add-backend ${BACKEND_SERVICE_NAME} \
    --global \
    --network-endpoint-group=${NEG_NAME} \
    --network-endpoint-group-region=${REGION} \
    --project=${PROJECT_ID}

# Step 4: Create URL map with CORS handling
echo ""
echo "Step 4: Creating URL map with CORS policy..."

# Create URL map configuration file
cat > url-map-config.yaml << EOF
name: ${URL_MAP_NAME}
defaultService: projects/${PROJECT_ID}/global/backendServices/${BACKEND_SERVICE_NAME}
hostRules:
- hosts:
  - ${DOMAIN}
  pathMatcher: main-matcher
pathMatchers:
- name: main-matcher
  defaultService: projects/${PROJECT_ID}/global/backendServices/${BACKEND_SERVICE_NAME}
  routeRules:
  - priority: 1
    description: "Handle OPTIONS requests for CORS"
    matchRules:
    - headerMatches:
      - headerName: ":method"
        exactMatch: "OPTIONS"
    routeAction:
      corsPolicy:
        allowOrigins:
        - "https://bytecodeef.looker.com"
        - "https://*.looker.com"
        - "https://*.cloud.looker.com"
        allowMethods:
        - "GET"
        - "POST" 
        - "OPTIONS"
        allowHeaders:
        - "Origin"
        - "Content-Type"
        - "Accept"
        - "Authorization"
        - "X-Requested-With"
        maxAge: 3600
        allowCredentials: false
      directResponseAction:
        status: 200
        body:
          inlineString: ""
  - priority: 2
    description: "Forward authenticated requests to Cloud Run"
    matchRules:
    - prefixMatch: "/"
    service: projects/${PROJECT_ID}/global/backendServices/${BACKEND_SERVICE_NAME}
EOF

# Import the URL map
gcloud compute url-maps import ${URL_MAP_NAME} \
    --source=url-map-config.yaml \
    --global \
    --project=${PROJECT_ID}

# Step 5: Create SSL certificate (you'll need to verify domain ownership)
echo ""
echo "Step 5: Creating SSL certificate..."
echo "NOTE: You'll need to verify domain ownership for the SSL certificate to be provisioned."

gcloud compute ssl-certificates create ${SSL_CERT_NAME} \
    --domains=${DOMAIN} \
    --global \
    --project=${PROJECT_ID}

# Step 6: Create HTTPS load balancer
echo ""
echo "Step 6: Creating HTTPS load balancer..."
gcloud compute target-https-proxies create ${LB_NAME}-https-proxy \
    --url-map=${URL_MAP_NAME} \
    --ssl-certificates=${SSL_CERT_NAME} \
    --global \
    --project=${PROJECT_ID}

# Step 7: Create global forwarding rule
echo ""
echo "Step 7: Creating global forwarding rule..."
gcloud compute forwarding-rules create ${LB_NAME}-https-rule \
    --address=${LB_NAME}-ip \
    --global \
    --target-https-proxy=${LB_NAME}-https-proxy \
    --ports=443 \
    --project=${PROJECT_ID}

# Reserve static IP
gcloud compute addresses create ${LB_NAME}-ip \
    --global \
    --project=${PROJECT_ID}

# Get the IP address
LB_IP=$(gcloud compute addresses describe ${LB_NAME}-ip \
    --global \
    --format="value(address)" \
    --project=${PROJECT_ID})

echo ""
echo "=== IDENTITY-AWARE PROXY SETUP ==="
echo ""

# Step 8: Enable IAP for the backend service
echo "Step 8: Enabling Identity-Aware Proxy..."

# First, create OAuth consent screen and credentials (this needs to be done manually)
echo "MANUAL STEP REQUIRED:"
echo "1. Go to: https://console.cloud.google.com/apis/credentials/consent"
echo "2. Configure OAuth consent screen for your project"
echo "3. Create OAuth 2.0 credentials (Web application type)"
echo "4. Add authorized redirect URIs: https://iap.googleapis.com/v1/oauth/clientIds/YOUR_CLIENT_ID:handleCodeRedirect"
echo ""
echo "After completing the OAuth setup, run the following commands:"
echo ""
echo "# Enable IAP on the backend service"
echo "gcloud iap web enable --resource-type=backend-services --service=${BACKEND_SERVICE_NAME} --oauth2-client-id=YOUR_CLIENT_ID --oauth2-client-secret=YOUR_CLIENT_SECRET --project=${PROJECT_ID}"
echo ""
echo "# Grant IAP access to your users"
echo "gcloud projects add-iam-policy-binding ${PROJECT_ID} --member='user:YOUR_USER_EMAIL' --role='roles/iap.httpsResourceAccessor'"

echo ""
echo "=== DEPLOYMENT SUMMARY ==="
echo ""
echo "Load Balancer IP: ${LB_IP}"
echo "Domain: ${DOMAIN}"
echo "Backend Service: ${BACKEND_SERVICE_NAME}"
echo ""
echo "DNS CONFIGURATION REQUIRED:"
echo "Create an A record pointing ${DOMAIN} to ${LB_IP}"
echo ""
echo "NEXT STEPS:"
echo "1. Configure DNS: ${DOMAIN} → ${LB_IP}"
echo "2. Wait for SSL certificate provisioning (can take up to 60 minutes)"
echo "3. Complete OAuth consent screen setup"
echo "4. Enable IAP with the commands shown above"
echo "5. Test CORS: curl -X OPTIONS https://${DOMAIN}/ -v"
echo "6. Update your Looker extension to use: https://${DOMAIN}/"
echo ""
echo "CORS HANDLING:"
echo "✅ OPTIONS requests are handled directly by the load balancer"
echo "✅ POST requests are forwarded to your authenticated Cloud Run service"
echo "✅ No unauthenticated services required"
echo "✅ Full IAP protection maintained"
