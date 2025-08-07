#!/bin/bash

# Environment setup script for the new consolidated MCP service
# This script helps set up all required environment variables

echo "🔧 Looker Explore Assistant MCP - Environment Setup"
echo "=================================================="

# Check if environment variables are already set
echo ""
echo "📋 Current Environment Status:"

VARS_TO_CHECK=(
    "PROJECT_ID"
    "REGION" 
    "LOOKERSDK_BASE_URL"
    "LOOKERSDK_CLIENT_ID"
    "LOOKERSDK_CLIENT_SECRET"
)

MISSING_VARS=()
SET_VARS=()

for var in "${VARS_TO_CHECK[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ $var: Not set"
        MISSING_VARS+=("$var")
    else
        case $var in
            "LOOKERSDK_CLIENT_SECRET")
                echo "✅ $var: ***"
                ;;
            "LOOKERSDK_CLIENT_ID")
                echo "✅ $var: ${!var:0:8}..."
                ;;
            *)
                echo "✅ $var: ${!var}"
                ;;
        esac
        SET_VARS+=("$var")
    fi
done

echo ""

if [ ${#MISSING_VARS[@]} -eq 0 ]; then
    echo "🎉 All environment variables are configured!"
    echo ""
    echo "Ready to deploy with:"
    echo "  ./deploy-new-service.sh"
    exit 0
fi

echo "⚠️  Missing ${#MISSING_VARS[@]} required environment variables"
echo ""

# Provide setup instructions for missing variables
echo "📝 Setup Instructions:"
echo "====================="

for var in "${MISSING_VARS[@]}"; do
    echo ""
    case $var in
        "PROJECT_ID")
            echo "🌍 Google Cloud Project ID:"
            echo "   This is your GCP project where the service will be deployed"
            echo "   export PROJECT_ID=\"your-gcp-project-id\""
            echo "   Example: export PROJECT_ID=\"combined-genai-bi\""
            ;;
        "REGION")
            echo "📍 Google Cloud Region:"
            echo "   The GCP region where Cloud Run will be deployed"
            echo "   export REGION=\"us-central1\""
            echo "   Common options: us-central1, us-east1, europe-west1"
            ;;
        "LOOKERSDK_BASE_URL")
            echo "🔗 Looker Instance Base URL:"
            echo "   The base URL of your Looker instance"
            echo "   export LOOKERSDK_BASE_URL=\"https://your-instance.looker.com\""
            echo "   Example: export LOOKERSDK_BASE_URL=\"https://company.looker.com\""
            ;;
        "LOOKERSDK_CLIENT_ID")
            echo "🔑 Looker API Client ID:"
            echo "   Create API credentials in Looker Admin > Users > API3 Keys"
            echo "   export LOOKERSDK_CLIENT_ID=\"your-client-id\""
            ;;
        "LOOKERSDK_CLIENT_SECRET")
            echo "🔐 Looker API Client Secret:"
            echo "   The secret key for your Looker API credentials"
            echo "   export LOOKERSDK_CLIENT_SECRET=\"your-client-secret\""
            ;;
    esac
done

echo ""
echo "💡 Quick Setup (copy and customize):"
echo "===================================="
echo "export PROJECT_ID=\"your-gcp-project-id\""
echo "export REGION=\"us-central1\""
echo "export LOOKERSDK_BASE_URL=\"https://your-instance.looker.com\""
echo "export LOOKERSDK_CLIENT_ID=\"your-client-id\""
echo "export LOOKERSDK_CLIENT_SECRET=\"your-client-secret\""
echo ""
echo "Then run: ./deploy-new-service.sh"

echo ""
echo "📚 Additional Resources:"
echo "========================"
echo "• Looker API Credentials: https://cloud.google.com/looker/docs/api-auth"
echo "• GCP Project Setup: https://cloud.google.com/resource-manager/docs/creating-managing-projects"
echo "• Cloud Run Regions: https://cloud.google.com/run/docs/locations"

echo ""
echo "🔧 After setting variables, run this script again to verify setup"
