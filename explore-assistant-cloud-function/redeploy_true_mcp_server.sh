#!/bin/bash

# Redeploy Script for True MCP Server with IAM Authentication (Cloud Run)
# This script builds and redeploys the MCP server with project-level IAM required for invocation.
# Only users/service accounts with the Cloud Run Invoker role can access the service.

set -e  # Exit on any error

# Configuration variables - update as needed
PROJECT_ID="combined-genai-bi"  # Replace with your GCP project ID
REGION="us-central1"            # Replace with your preferred region
SERVICE_NAME="mcp-server"       # Unique service name for the true MCP server
IMAGE_NAME="mcp-server"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}Starting redeploy of True MCP Server (IAM protected)${NC}"

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

gcloud builds submit --config cloudbuild.mcp_server.yaml --substitutions=_FULL_IMAGE_NAME=$FULL_IMAGE_NAME .
# Deploy to Cloud Run with IAM authentication required
echo -e "${YELLOW}Deploying to Cloud Run with IAM authentication required...${NC}"
gcloud run deploy $SERVICE_NAME \
    --image $FULL_IMAGE_NAME \
    --region $REGION \
    --platform managed \
    --no-allow-unauthenticated \
    --quiet

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format='value(status.url)')

echo -e "${GREEN}Deploy completed! Service URL: $SERVICE_URL${NC}"
echo -e "${YELLOW}This service REQUIRES IAM authentication. Only users/service accounts with the 'Cloud Run Invoker' role can access it.${NC}"
echo -e "${YELLOW}To grant access, run:${NC}"
echo -e "  gcloud run services add-iam-policy-binding $SERVICE_NAME \\"
echo -e "    --region $REGION --member='user:YOUR_USER@YOUR_DOMAIN.com' --role='roles/run.invoker'"

echo -e "${YELLOW}Health check requires an authenticated token. See Cloud Run docs for curl with ID token.${NC}"
echo -e "${GREEN}Redeploy script completed!${NC}"
