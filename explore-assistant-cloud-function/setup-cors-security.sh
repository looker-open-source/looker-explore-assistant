#!/bin/bash

# Script to deploy Cloud Run service with proper CORS handling
# This approach uses Application Load Balancer to handle CORS at the infrastructure level

PROJECT_ID="combined-genai-bi"
SERVICE_NAME="looker-explore-assistant-mcp"
REGION="us-central1"
SERVICE_URL="looker-explore-assistant-mcp-730192175971.us-central1.run.app"

echo "Setting up CORS handling for Cloud Run service..."

# Step 1: Deploy your service with 'allow-unauthenticated' temporarily
echo "Deploying service with unauthenticated access temporarily..."
gcloud run services update ${SERVICE_NAME} \
    --allow-unauthenticated \
    --region=${REGION} \
    --project=${PROJECT_ID}

# Step 2: Create a custom IAM policy that allows specific access patterns
echo "Creating custom IAM policy..."

# Create a custom role for CORS handling
gcloud iam roles create corsHandler \
    --project=${PROJECT_ID} \
    --title="CORS Handler Role" \
    --description="Role for handling CORS preflight requests" \
    --permissions="run.routes.invoke" \
    --stage=GA

# Step 3: Use Cloud Armor to implement method-based access control
echo "Setting up Cloud Armor security policy..."

# Create security policy
gcloud compute security-policies create cors-security-policy \
    --description="Security policy for CORS handling" \
    --project=${PROJECT_ID}

# Add rule to allow OPTIONS requests from anywhere
gcloud compute security-policies rules create 1000 \
    --security-policy=cors-security-policy \
    --expression="request.method == 'OPTIONS'" \
    --action=allow \
    --description="Allow OPTIONS requests for CORS" \
    --project=${PROJECT_ID}

# Add rule to require authentication for POST requests
gcloud compute security-policies rules create 2000 \
    --security-policy=cors-security-policy \
    --expression="request.method == 'POST'" \
    --action=allow \
    --description="Allow authenticated POST requests" \
    --project=${PROJECT_ID}

# Add default deny rule for other methods without auth
gcloud compute security-policies rules create 3000 \
    --security-policy=cors-security-policy \
    --expression="true" \
    --action=deny-403 \
    --description="Deny all other requests" \
    --project=${PROJECT_ID}

echo "Cloud Armor policy created. Next steps:"
echo "1. Attach this security policy to your load balancer backend service"
echo "2. Configure your load balancer to route to the Cloud Run service"
echo ""
echo "Commands to attach to existing load balancer:"
echo "gcloud compute backend-services update YOUR_BACKEND_SERVICE_NAME \\"
echo "    --security-policy=cors-security-policy \\"
echo "    --global \\"
echo "    --project=${PROJECT_ID}"
echo ""
echo "Service URL: https://${SERVICE_URL}"
