#!/bin/bash

# Script to get OAuth token with required scopes for MCP server testing

echo "Getting OAuth token with required scopes for MCP server..."
echo ""

echo "This script will help you get an OAuth token with the required scopes:"
echo "- https://www.googleapis.com/auth/cloud-platform"
echo "- https://www.googleapis.com/auth/userinfo.email"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI is not installed or not in PATH"
    echo "Please install Google Cloud SDK first: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

echo "✅ gcloud CLI found"

# Check if user is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n1 > /dev/null 2>&1; then
    echo ""
    echo "🔐 No active gcloud authentication found. Logging in with required scopes..."
    echo ""
    
    # Login with specific scopes
    gcloud auth login \
        --scopes=https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/userinfo.email \
        --enable-gdrive-access
        
    if [ $? -ne 0 ]; then
        echo "❌ Authentication failed"
        exit 1
    fi
else
    echo "✅ Found active gcloud authentication"
    ACTIVE_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n1)
    echo "   Account: $ACTIVE_ACCOUNT"
fi

echo ""
echo "🎫 Getting access token..."

# Get the access token
TOKEN=$(gcloud auth print-access-token 2>/dev/null)

if [ $? -ne 0 ] || [ -z "$TOKEN" ]; then
    echo "❌ Failed to get access token"
    echo ""
    echo "This might happen if your current authentication doesn't have the required scopes."
    echo "Try running this command to re-authenticate with the correct scopes:"
    echo ""
    echo "gcloud auth login --scopes=https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/userinfo.email"
    echo ""
    exit 1
fi

echo "✅ Access token obtained successfully!"
echo ""
echo "Token preview: ${TOKEN:0:20}..."
echo "Token length: ${#TOKEN} characters"
echo ""

# Validate the token has required scopes
echo "🔍 Validating token scopes..."
VALIDATION_RESPONSE=$(curl -s "https://oauth2.googleapis.com/tokeninfo?access_token=$TOKEN")

if echo "$VALIDATION_RESPONSE" | grep -q "error"; then
    echo "❌ Token validation failed:"
    echo "$VALIDATION_RESPONSE"
    exit 1
fi

# Check if required scopes are present
SCOPES=$(echo "$VALIDATION_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    scopes = data.get('scope', '').split()
    print(' '.join(scopes))
except:
    print('Failed to parse')
")

echo "Token scopes: $SCOPES"

# Check for required scopes
REQUIRED_SCOPES=("https://www.googleapis.com/auth/cloud-platform" "https://www.googleapis.com/auth/userinfo.email")
MISSING_SCOPES=""

for REQUIRED_SCOPE in "${REQUIRED_SCOPES[@]}"; do
    if [[ ! "$SCOPES" == *"$REQUIRED_SCOPE"* ]]; then
        MISSING_SCOPES="$MISSING_SCOPES $REQUIRED_SCOPE"
    fi
done

if [ -n "$MISSING_SCOPES" ]; then
    echo "❌ Token is missing required scopes:$MISSING_SCOPES"
    echo ""
    echo "Please re-authenticate with the correct scopes:"
    echo "gcloud auth login --scopes=https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/userinfo.email"
    exit 1
fi

echo "✅ Token has all required scopes!"
echo ""

# Test the MCP server with this token
echo "🧪 Testing MCP server with this token..."
echo ""

cd "$(dirname "$0")"

if [ -f "test_oauth_flow.py" ]; then
    python3 test_oauth_flow.py "$TOKEN"
else
    echo "OAuth test script not found. You can manually test with:"
    echo ""
    echo "export OAUTH_TOKEN=\"$TOKEN\""
    echo "python3 test_oauth_flow.py \$OAUTH_TOKEN"
    echo ""
    echo "Or copy this token and use it in your tests:"
    echo "$TOKEN"
fi
