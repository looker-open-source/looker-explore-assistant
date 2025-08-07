#!/bin/bash

# Environment Variables Check for Field Discovery Vector Search System

echo "🔍 Checking Field Discovery Environment Variables..."
echo ""

# Required environment variables
required_vars=(
    "PROJECT"
    "BQ_DATASET_ID" 
    "LOOKERSDK_BASE_URL"
    "LOOKERSDK_CLIENT_ID"
    "LOOKERSDK_CLIENT_SECRET"
)

all_set=true

for var in "${required_vars[@]}"; do
    if [[ -z "${!var}" ]]; then
        echo "❌ $var: NOT SET"
        all_set=false
        
        case $var in
            "PROJECT")
                echo "   💡 Set with: export PROJECT=your-google-cloud-project-id"
                ;;
            "BQ_DATASET_ID")
                echo "   💡 Set with: export BQ_DATASET_ID=explore_assistant"
                ;;
            "LOOKERSDK_BASE_URL")
                echo "   💡 Set with: export LOOKERSDK_BASE_URL=https://your-instance.looker.com"
                ;;
            "LOOKERSDK_CLIENT_ID")
                echo "   💡 Set with: export LOOKERSDK_CLIENT_ID=your-looker-api-client-id"
                echo "   📚 Get from: Looker Admin > API > API Keys"
                ;;
            "LOOKERSDK_CLIENT_SECRET")
                echo "   💡 Set with: export LOOKERSDK_CLIENT_SECRET=your-looker-api-client-secret"
                echo "   📚 Get from: Looker Admin > API > API Keys"
                ;;
        esac
        echo ""
    else
        echo "✅ $var: ${!var}"
    fi
done

echo ""
if [ "$all_set" = true ]; then
    echo "🎉 All environment variables are set!"
    echo "✅ Ready to run: ./setup_field_discovery.sh"
else
    echo "⚠️  Please set the missing environment variables above."
    echo "📖 For Looker API credentials, see: https://cloud.google.com/looker/docs/api-auth"
fi
