#!/bin/bash

# Configure existing Application Load Balancer with CORS support
# This updates your existing IAP-enabled load balancer to handle CORS

PROJECT_ID="combined-genai-bi"
BACKEND_SERVICE="exploreassistantmcpbackendservice"
URL_MAP_NAME="lookerbytecodeexploreassistantmcplb"  # Found from discovery

echo "=== Configuring existing Load Balancer with CORS support ==="
echo ""

# First, let's check the current configuration
echo "Step 1: Checking current load balancer configuration..."

# List existing URL maps to find yours
echo "Finding existing URL map..."
gcloud compute url-maps list --project=${PROJECT_ID}

# Get the current URL map configuration
echo ""
echo "Getting current URL map configuration..."
gcloud compute url-maps describe ${URL_MAP_NAME} --project=${PROJECT_ID} || {
    echo "URL map ${URL_MAP_NAME} not found. Let's list all URL maps:"
    gcloud compute url-maps list --project=${PROJECT_ID}
    echo ""
    echo "Please update the URL_MAP_NAME variable in this script with the correct name."
    exit 1
}

# Create a new URL map configuration with CORS support
echo ""
echo "Step 2: Creating URL map configuration with CORS support..."

cat > cors-url-map.yaml << EOF
name: ${URL_MAP_NAME}
description: "Load balancer with CORS support for Explore Assistant MCP"
defaultService: projects/${PROJECT_ID}/global/backendServices/${BACKEND_SERVICE}
hostRules: []
pathMatchers: []
tests: []
# Add CORS policy at the URL map level
defaultRouteAction:
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
EOF

echo "Created CORS-enabled URL map configuration."

# Apply the updated configuration
echo ""
echo "Step 3: Applying CORS configuration to load balancer..."
echo "This will update your existing load balancer to handle CORS at the infrastructure level."
echo ""
read -p "Do you want to apply this CORS configuration? (y/n): " confirm

if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
    echo "Updating URL map with CORS support..."
    gcloud compute url-maps import ${URL_MAP_NAME} \
        --source=cors-url-map.yaml \
        --project=${PROJECT_ID}
    
    if [ $? -eq 0 ]; then
        echo "✅ Successfully updated load balancer with CORS support!"
        echo ""
        echo "Your load balancer will now:"
        echo "- Handle OPTIONS requests at the infrastructure level"
        echo "- Add proper CORS headers to all responses"
        echo "- Maintain IAP authentication for POST requests"
        echo "- Allow unauthenticated OPTIONS requests for CORS preflight"
    else
        echo "❌ Failed to update load balancer configuration"
        exit 1
    fi
else
    echo "Configuration not applied. You can apply it later with:"
    echo "gcloud compute url-maps import ${URL_MAP_NAME} --source=cors-url-map.yaml --project=${PROJECT_ID}"
fi

echo ""
echo "=== Configuration Complete ==="
echo ""
echo "Next steps:"
echo "1. Wait 1-2 minutes for the configuration to propagate"
echo "2. Update your Looker extension to use the load balancer URL instead of direct Cloud Run URL"
echo "3. Test CORS functionality"
echo ""
echo "Load balancer IPs:"
echo "- 34.149.46.123:443"
echo "- 34.160.194.234:443"
echo ""
echo "You can test CORS with:"
echo "curl -X OPTIONS https://34.149.46.123/ -H 'Origin: https://bytecodeef.looker.com' -v"
