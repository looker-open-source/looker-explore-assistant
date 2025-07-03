#!/bin/bash

# Deployment script for Cloud Run with CORS support
PROJECT_ID="combined-genai-bi"
SERVICE_NAME="looker-explore-assistant-mcp"
REGION="us-central1"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "Building and deploying Cloud Run service with CORS support..."

# Build the container
echo "Building container image..."
docker build -t ${IMAGE_NAME} .

# Push to Container Registry
echo "Pushing to Container Registry..."
docker push ${IMAGE_NAME}

# Deploy to Cloud Run with specific configuration
echo "Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
    --image=${IMAGE_NAME} \
    --platform=managed \
    --region=${REGION} \
    --allow-unauthenticated \
    --port=8080 \
    --memory=1Gi \
    --cpu=1 \
    --max-instances=10 \
    --set-env-vars="PROJECT=${PROJECT_ID},REGION=${REGION}" \
    --project=${PROJECT_ID}

echo "Getting service URL..."
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --platform=managed \
    --region=${REGION} \
    --format='value(status.url)' \
    --project=${PROJECT_ID})

echo "Service deployed at: ${SERVICE_URL}"

# Create IAM policy for authentication
echo "Setting up IAM policies..."

# Allow unauthenticated access to OPTIONS requests only
# This requires using Cloud Endpoints or Load Balancer for selective auth

echo "Deployment complete!"
echo "Service URL: ${SERVICE_URL}"
echo ""
echo "Next steps:"
echo "1. Configure your frontend to use this URL"
echo "2. Test CORS functionality"
echo "3. Monitor logs for any issues"
