#!/bin/bash

# Deploy Cloud Function as CORS proxy
PROJECT_ID="combined-genai-bi"
FUNCTION_NAME="looker-cors-proxy"
REGION="us-central1"

echo "Creating Cloud Function CORS proxy..."

# Create the function directory
mkdir -p cors-proxy-function
cd cors-proxy-function

# Create package.json
cat > package.json << EOF
{
  "name": "looker-cors-proxy",
  "version": "1.0.0",
  "dependencies": {
    "@google-cloud/functions-framework": "^3.0.0",
    "node-fetch": "^2.6.7"
  }
}
EOF

# Create the Cloud Function
cat > index.js << EOF
const functions = require('@google-cloud/functions-framework');
const fetch = require('node-fetch');

const TARGET_URL = 'https://looker-explore-assistant-mcp-730192175971.us-central1.run.app';

functions.http('corsProxy', async (req, res) => {
  // Set CORS headers for all requests
  res.set('Access-Control-Allow-Origin', '*');
  res.set('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.set('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  res.set('Access-Control-Max-Age', '3600');

  // Handle preflight OPTIONS request
  if (req.method === 'OPTIONS') {
    res.status(200).send('');
    return;
  }

  try {
    // Forward the request to your Cloud Run service
    const headers = {
      'Content-Type': 'application/json',
    };

    // Forward Authorization header if present
    if (req.headers.authorization) {
      headers['Authorization'] = req.headers.authorization;
    }

    const response = await fetch(TARGET_URL + req.path, {
      method: req.method,
      headers: headers,
      body: req.method !== 'GET' ? JSON.stringify(req.body) : undefined
    });

    const data = await response.json();
    res.status(response.status).json(data);

  } catch (error) {
    console.error('Proxy error:', error);
    res.status(500).json({ error: 'Proxy error: ' + error.message });
  }
});
EOF

# Deploy the function
gcloud functions deploy ${FUNCTION_NAME} \
    --gen2 \
    --runtime=nodejs18 \
    --region=${REGION} \
    --source=. \
    --entry-point=corsProxy \
    --trigger-http \
    --allow-unauthenticated \
    --project=${PROJECT_ID}

echo "Cloud Function deployed!"
echo "Use this URL in your frontend: https://${REGION}-${PROJECT_ID}.cloudfunctions.net/${FUNCTION_NAME}"

cd ..
rm -rf cors-proxy-function
