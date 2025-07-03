#!/bin/bash

# Solution 2: Cloud Function as CORS proxy
# Cloud Functions can handle CORS more easily than Cloud Run

PROJECT_ID="combined-genai-bi"
SERVICE_NAME="looker-explore-assistant-mcp"
REGION="us-central1"
FUNCTION_NAME="${SERVICE_NAME}-cors-proxy"

echo "=== SETTING UP CLOUD FUNCTION CORS PROXY ==="
echo ""

# Get your Cloud Run service URL
CLOUD_RUN_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --platform=managed \
    --region=${REGION} \
    --format='value(status.url)' \
    --project=${PROJECT_ID})

echo "Cloud Run service URL: ${CLOUD_RUN_URL}"

# Create the Cloud Function code
mkdir -p cors-proxy-function
cd cors-proxy-function

# Create main.py for the Cloud Function
cat > main.py << EOF
import functions_framework
import requests
import json
from flask import jsonify

@functions_framework.http
def cors_proxy(request):
    """CORS proxy for Cloud Run service"""
    
    # Set CORS headers for all responses
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With',
        'Access-Control-Max-Age': '3600'
    }
    
    # Handle preflight OPTIONS requests
    if request.method == 'OPTIONS':
        return ('', 200, headers)
    
    # Forward other requests to Cloud Run service
    try:
        # Get authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'Authorization header required'}), 401, headers
        
        # Prepare headers for Cloud Run request
        forward_headers = {
            'Content-Type': 'application/json',
            'Authorization': auth_header
        }
        
        # Get request data
        if request.method == 'POST':
            request_data = request.get_json()
            
            # Forward to Cloud Run service
            response = requests.post(
                '${CLOUD_RUN_URL}',
                headers=forward_headers,
                json=request_data,
                timeout=30
            )
            
            if response.ok:
                return response.json(), 200, headers
            else:
                return jsonify({'error': f'Cloud Run error: {response.status_code}'}), response.status_code, headers
        
        elif request.method == 'GET':
            response = requests.get(
                '${CLOUD_RUN_URL}/health',
                headers=forward_headers,
                timeout=30
            )
            
            if response.ok:
                return response.json(), 200, headers
            else:
                return jsonify({'error': f'Cloud Run error: {response.status_code}'}), response.status_code, headers
    
    except Exception as e:
        return jsonify({'error': f'Proxy error: {str(e)}'}), 500, headers
EOF

# Create requirements.txt
cat > requirements.txt << EOF
functions-framework==3.*
requests==2.*
flask==2.*
EOF

echo "Step 1: Deploying Cloud Function CORS proxy..."
gcloud functions deploy ${FUNCTION_NAME} \
    --gen2 \
    --runtime=python311 \
    --region=${REGION} \
    --source=. \
    --entry-point=cors_proxy \
    --trigger-http \
    --allow-unauthenticated \
    --memory=256MB \
    --timeout=60s \
    --project=${PROJECT_ID}

# Get the function URL
FUNCTION_URL=$(gcloud functions describe ${FUNCTION_NAME} \
    --region=${REGION} \
    --format='value(serviceConfig.uri)' \
    --project=${PROJECT_ID})

cd ..
rm -rf cors-proxy-function

echo ""
echo "=== CLOUD FUNCTION CORS PROXY SETUP COMPLETE ==="
echo ""
echo "Function URL: ${FUNCTION_URL}"
echo ""
echo "Update your Looker extension to use this URL instead of the direct Cloud Run URL."
echo ""
echo "How it works:"
echo "- Cloud Function handles CORS headers for all requests"
echo "- OPTIONS requests are handled directly by the function"
echo "- POST requests are forwarded to your authenticated Cloud Run service"
echo "- Cloud Function can be unauthenticated (simpler than Cloud Run)"
echo ""
echo "Test with:"
echo "curl -X OPTIONS ${FUNCTION_URL} -v"
