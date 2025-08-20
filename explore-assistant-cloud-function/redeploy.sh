#!/bin/bash

# Quick Redeploy Script for Looker Explore Assistant MCP Server
# This script rebuilds and redeploys the service without modifying environment variables

set -e  # Exit on any error

# Configuration variables - should match your existing deployment
PROJECT_ID="explore-assistant-cf-mis"  # Updated for new GCP project
REGION="us-central1"  # Replace with your preferred region
SERVICE_NAME="ea-demo-backend"  # New unique service name
IMAGE_NAME="ea-demo-backend"  # Match image name to service for clarity

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting quick redeploy of Looker Explore Assistant MCP Server${NC}"

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

# Set the project
echo -e "${YELLOW}Setting GCP project to $PROJECT_ID...${NC}"
gcloud config set project $PROJECT_ID

# Configure Docker to use gcloud as a credential helper
echo -e "${YELLOW}Configuring Docker authentication...${NC}"
gcloud auth configure-docker $REGION-docker.pkg.dev

# Build the container image using Cloud Build
echo -e "${YELLOW}Building updated container image...${NC}"
FULL_IMAGE_NAME="$REGION-docker.pkg.dev/$PROJECT_ID/$SERVICE_NAME/$IMAGE_NAME"

gcloud builds submit --tag $FULL_IMAGE_NAME .

# Deploy to Cloud Run (preserving existing environment variables)
echo -e "${YELLOW}Redeploying to Cloud Run with new image...${NC}"
gcloud run deploy $SERVICE_NAME \
    --image $FULL_IMAGE_NAME \
    --region $REGION \
    --platform managed \
    --quiet

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format='value(status.url)')

echo -e "${GREEN}Redeploy completed successfully!${NC}"
echo -e "${GREEN}Service URL: $SERVICE_URL${NC}"
echo ""

# Optional: Test the health endpoint
echo -e "${YELLOW}Testing health endpoint...${NC}"
if curl -f "$SERVICE_URL/health" > /dev/null 2>&1; then
    echo -e "${GREEN}Health check passed!${NC}"
else
    echo -e "${YELLOW}Health check failed or service is still starting up.${NC}"
    echo "You can test manually with: curl $SERVICE_URL/health"
fi

echo -e "${GREEN}Redeploy script completed!${NC}"
