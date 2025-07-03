#!/bin/bash

# Script to configure Cloud Load Balancer with CORS handling
# Run this script to set up the load balancer configuration

PROJECT_ID="combined-genai-bi"
SERVICE_NAME="looker-explore-assistant-mcp"
REGION="us-central1"

echo "Setting up Cloud Load Balancer with CORS support..."

# Create a separate backend service for OPTIONS requests (no auth required)
gcloud compute backend-services create ${SERVICE_NAME}-options-backend \
    --global \
    --protocol=HTTP \
    --health-checks=http-basic-check \
    --project=${PROJECT_ID}

# Create the main backend service (with auth required)
gcloud compute backend-services create ${SERVICE_NAME}-main-backend \
    --global \
    --protocol=HTTP \
    --health-checks=http-basic-check \
    --project=${PROJECT_ID}

# Add your Cloud Run service as a backend to both services
NEG_NAME="${SERVICE_NAME}-neg"
gcloud compute network-endpoint-groups create ${NEG_NAME} \
    --region=${REGION} \
    --network-endpoint-type=serverless \
    --cloud-run-service=${SERVICE_NAME} \
    --project=${PROJECT_ID}

# Add the NEG to both backend services
gcloud compute backend-services add-backend ${SERVICE_NAME}-options-backend \
    --global \
    --network-endpoint-group=${NEG_NAME} \
    --network-endpoint-group-region=${REGION} \
    --project=${PROJECT_ID}

gcloud compute backend-services add-backend ${SERVICE_NAME}-main-backend \
    --global \
    --network-endpoint-group=${NEG_NAME} \
    --network-endpoint-group-region=${REGION} \
    --project=${PROJECT_ID}

# Create URL map with path matcher for OPTIONS requests
gcloud compute url-maps create ${SERVICE_NAME}-url-map \
    --default-service=${SERVICE_NAME}-main-backend \
    --project=${PROJECT_ID}

# Add path matcher for OPTIONS requests
gcloud compute url-maps add-path-matcher ${SERVICE_NAME}-url-map \
    --path-matcher-name=options-matcher \
    --default-service=${SERVICE_NAME}-options-backend \
    --path-rules="/*=looker-explore-assistant-mcp-options-backend" \
    --project=${PROJECT_ID}

echo "Load balancer configuration created. You'll need to:"
echo "1. Configure IAM policies to allow unauthenticated access to the options backend"
echo "2. Set up the appropriate routing rules based on HTTP method"
echo "3. Configure SSL certificates and frontend"
