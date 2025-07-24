#!/bin/bash

# Script to update environment variables for the deployed Cloud Run service
# Use this script after initial deployment to set your actual configuration values

set -e  # Exit on any error

# Configuration variables - Modify these to match your deployment
PROJECT_ID="combined-genai-bi"  # Replace with your GCP project ID
REGION="us-central1"  # Replace with your region (should match deployment)
SERVICE_NAME="looker-explore-assistant-mcp"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Updating environment variables for Cloud Run service: $SERVICE_NAME${NC}"

# Validate project ID is set
if [ "$PROJECT_ID" = "YOUR_PROJECT_ID" ]; then
    echo -e "${RED}Error: Please set your PROJECT_ID in the script before running.${NC}"
    exit 1
fi

# Function to update environment variable
update_env_var() {
    local var_name=$1
    local var_value=$2
    local description=$3
    
    if [ -z "$var_value" ] || [ "$var_value" = "PLACEHOLDER_"* ]; then
        echo -e "${YELLOW}Skipping $var_name - no value provided${NC}"
        return
    fi
    
    echo -e "${YELLOW}Updating $var_name ($description)...${NC}"
    gcloud run services update $SERVICE_NAME \
        --region=$REGION \
        --set-env-vars "$var_name=$var_value" \
        --quiet
}

# Prompt for each environment variable
echo ""
echo -e "${YELLOW}Please provide the following environment variable values:${NC}"
echo "Press Enter to skip any variable you don't want to update."
echo ""

# MCP Shared Secret
read -p "MCP_SHARED_SECRET (secure secret for MCP authentication): " MCP_SHARED_SECRET
update_env_var "MCP_SHARED_SECRET" "$MCP_SHARED_SECRET" "MCP authentication secret"

# Looker API credentials
read -p "LOOKER_API_CLIENT_ID (your Looker API client ID): " LOOKER_API_CLIENT_ID
update_env_var "LOOKER_API_CLIENT_ID" "$LOOKER_API_CLIENT_ID" "Looker API client ID"
update_env_var "LOOKERSDK_CLIENT_ID" "$LOOKER_API_CLIENT_ID" "Looker SDK client ID (same as API client ID)"

read -s -p "LOOKER_API_CLIENT_SECRET (your Looker API client secret): " LOOKER_API_CLIENT_SECRET
echo ""
update_env_var "LOOKER_API_CLIENT_SECRET" "$LOOKER_API_CLIENT_SECRET" "Looker API client secret"
update_env_var "LOOKERSDK_CLIENT_SECRET" "$LOOKER_API_CLIENT_SECRET" "Looker SDK client secret (same as API client secret)"

read -p "LOOKER_BASE_URL (your Looker instance URL, e.g., https://your-instance.looker.com): " LOOKER_BASE_URL
update_env_var "LOOKER_BASE_URL" "$LOOKER_BASE_URL" "Looker base URL"

# Vertex AI Model (optional override)
read -p "VERTEX_MODEL (optional, default is gemini-2.0-flash-001): " VERTEX_MODEL
if [ -n "$VERTEX_MODEL" ]; then
    update_env_var "VERTEX_MODEL" "$VERTEX_MODEL" "Vertex AI model name"
fi

# SSL verification setting
echo ""
echo -e "${YELLOW}SSL Verification Settings:${NC}"
echo "1. true (recommended for production)"
echo "2. false (for development/testing only)"
read -p "Select SSL verification setting [1-2, default: 1]: " SSL_CHOICE

case $SSL_CHOICE in
    2)
        update_env_var "LOOKERSDK_VERIFY_SSL" "false" "SSL verification disabled"
        ;;
    *)
        update_env_var "LOOKERSDK_VERIFY_SSL" "true" "SSL verification enabled"
        ;;
esac

echo ""
echo -e "${GREEN}Environment variables update completed!${NC}"

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format='value(status.url)')

echo ""
echo -e "${GREEN}Service URL: $SERVICE_URL${NC}"
echo ""
echo -e "${YELLOW}Testing the updated service...${NC}"

# Test health endpoint
if curl -f "$SERVICE_URL/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Health check passed!${NC}"
else
    echo -e "${RED}✗ Health check failed. The service may be restarting or there may be configuration issues.${NC}"
    echo "Check the logs with: gcloud run logs read $SERVICE_NAME --region=$REGION"
fi

echo ""
echo -e "${YELLOW}Additional commands:${NC}"
echo "View logs: gcloud run logs read $SERVICE_NAME --region=$REGION --follow"
echo "View service details: gcloud run services describe $SERVICE_NAME --region=$REGION"
echo "Update single env var: gcloud run services update $SERVICE_NAME --region=$REGION --set-env-vars KEY=VALUE"

echo -e "${GREEN}Configuration update completed!${NC}"
