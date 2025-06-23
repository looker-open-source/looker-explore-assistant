#!/bin/bash

# Google Cloud Run Deployment Script for Looker Explore Assistant MCP Server
# This script deploys the MCP server to Google Cloud Run

set -e  # Exit on any error

# Configuration variables - Modify these before running
PROJECT_ID="combined-genai-bi"  # Replace with your GCP project ID
REGION="us-central1"  # Replace with your preferred region
SERVICE_NAME="looker-explore-assistant-mcp"
IMAGE_NAME="looker-explore-assistant-mcp"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting deployment of Looker Explore Assistant MCP Server to Google Cloud Run${NC}"

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if required tools are installed
echo -e "${YELLOW}Checking prerequisites...${NC}"
if ! command_exists gcloud; then
    echo -e "${RED}Error: gcloud CLI is not installed. Please install it first.${NC}"
    exit 1
fi

if ! command_exists docker; then
    echo -e "${RED}Error: Docker is not installed. Please install it first.${NC}"
    exit 1
fi

# Check if user is authenticated with gcloud
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo -e "${RED}Error: Not authenticated with gcloud. Please run 'gcloud auth login' first.${NC}"
    exit 1
fi

# Validate project ID is set
if [ "$PROJECT_ID" = "YOUR_PROJECT_ID" ]; then
    echo -e "${RED}Error: Please set your PROJECT_ID in the script before running.${NC}"
    exit 1
fi

# Set the project
echo -e "${YELLOW}Setting GCP project to $PROJECT_ID...${NC}"
gcloud config set project $PROJECT_ID

# Enable required APIs
echo -e "${YELLOW}Enabling required Google Cloud APIs...${NC}"
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable artifactregistry.googleapis.com

# Create Artifact Registry repository (if it doesn't exist)
echo -e "${YELLOW}Creating Artifact Registry repository...${NC}"
gcloud artifacts repositories create $SERVICE_NAME \
    --repository-format=docker \
    --location=$REGION \
    --description="Docker repository for Looker Explore Assistant MCP Server" \
    --quiet || echo "Repository may already exist"

# Configure Docker to use gcloud as a credential helper
echo -e "${YELLOW}Configuring Docker authentication...${NC}"
gcloud auth configure-docker $REGION-docker.pkg.dev

# Build the container image using Cloud Build
echo -e "${YELLOW}Building container image...${NC}"
FULL_IMAGE_NAME="$REGION-docker.pkg.dev/$PROJECT_ID/$SERVICE_NAME/$IMAGE_NAME"

gcloud builds submit --tag $FULL_IMAGE_NAME .

# Deploy to Cloud Run
echo -e "${YELLOW}Deploying to Cloud Run...${NC}"
gcloud run deploy $SERVICE_NAME \
    --image $FULL_IMAGE_NAME \
    --region $REGION \
    --platform managed \
    --allow-unauthenticated \
    --port 8080 \
    --memory 1Gi \
    --cpu 1 \
    --timeout 3600 \
    --concurrency 100 \
    --min-instances 0 \
    --max-instances 10 \
    --set-env-vars "PROJECT=$PROJECT_ID" \
    --set-env-vars "REGION=$REGION" \
    --set-env-vars "VERTEX_MODEL=gemini-2.0-flash-001" \
    --set-env-vars "LOG_LEVEL=INFO" \
    --set-env-vars "FLASK_ENV=production" \
    --set-env-vars "MCP_SHARED_SECRET=PLACEHOLDER_REPLACE_WITH_SECURE_SECRET" \
    --set-env-vars "LOOKER_API_CLIENT_ID=PLACEHOLDER_YOUR_LOOKER_CLIENT_ID" \
    --set-env-vars "LOOKER_API_CLIENT_SECRET=PLACEHOLDER_YOUR_LOOKER_CLIENT_SECRET" \
    --set-env-vars "LOOKER_BASE_URL=PLACEHOLDER_YOUR_LOOKER_BASE_URL" \
    --set-env-vars "LOOKERSDK_CLIENT_ID=PLACEHOLDER_YOUR_LOOKER_CLIENT_ID" \
    --set-env-vars "LOOKERSDK_CLIENT_SECRET=PLACEHOLDER_YOUR_LOOKER_CLIENT_SECRET" \
    --set-env-vars "LOOKERSDK_VERIFY_SSL=true" \
    --quiet

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format='value(status.url)')

echo -e "${GREEN}Deployment completed successfully!${NC}"
echo -e "${GREEN}Service URL: $SERVICE_URL${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Update the environment variables with your actual values:"
echo "   gcloud run services update $SERVICE_NAME --region=$REGION --set-env-vars KEY=VALUE"
echo ""
echo "2. Required environment variables to update:"
echo "   - MCP_SHARED_SECRET: Replace with a secure secret"
echo "   - LOOKER_API_CLIENT_ID: Your Looker API client ID"
echo "   - LOOKER_API_CLIENT_SECRET: Your Looker API client secret"
echo "   - LOOKER_BASE_URL: Your Looker instance URL"
echo "   - LOOKERSDK_CLIENT_ID: Same as LOOKER_API_CLIENT_ID"
echo "   - LOOKERSDK_CLIENT_SECRET: Same as LOOKER_API_CLIENT_SECRET"
echo ""
echo "3. Test the deployment:"
echo "   curl $SERVICE_URL/health"
echo ""
echo -e "${YELLOW}Security Note:${NC}"
echo "The service is currently deployed with --allow-unauthenticated."
echo "For production, consider using IAM authentication instead."

# Optional: Test the health endpoint
echo -e "${YELLOW}Testing health endpoint...${NC}"
if curl -f "$SERVICE_URL/health" > /dev/null 2>&1; then
    echo -e "${GREEN}Health check passed!${NC}"
else
    echo -e "${YELLOW}Health check failed or service is still starting up.${NC}"
    echo "You can test manually with: curl $SERVICE_URL/health"
fi

echo -e "${GREEN}Deployment script completed!${NC}"
