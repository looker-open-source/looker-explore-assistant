#!/bin/bash

# Solution: Deploy Cloud Run with proper CORS configuration via service YAML
# This bypasses the authentication requirement for OPTIONS requests specifically

PROJECT_ID="combined-genai-bi"
SERVICE_NAME="looker-explore-assistant-mcp"
REGION="us-central1"

echo "Creating Cloud Run service configuration with CORS support..."

# Create a service.yaml file that configures Cloud Run to handle CORS properly
cat > service.yaml << 'EOF'
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: looker-explore-assistant-mcp
  annotations:
    run.googleapis.com/ingress: all
    run.googleapis.com/execution-environment: gen2
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/maxScale: '10'
        run.googleapis.com/startup-cpu-boost: 'true'
        # Key annotation: Allow specific HTTP methods without authentication
        run.googleapis.com/cors-allow-origin: "*"
        run.googleapis.com/cors-allow-methods: "POST, OPTIONS, GET"
        run.googleapis.com/cors-allow-headers: "Content-Type, Authorization"
    spec:
      containerConcurrency: 100
      timeoutSeconds: 3600
      containers:
      - image: us-central1-docker.pkg.dev/combined-genai-bi/looker-explore-assistant-mcp/looker-explore-assistant-mcp:latest
        ports:
        - name: http1
          containerPort: 8080
        env:
        - name: PROJECT
          value: "combined-genai-bi"
        - name: REGION
          value: "us-central1"
        resources:
          limits:
            cpu: 1000m
            memory: 1Gi
        startupProbe:
          timeoutSeconds: 240
          periodSeconds: 240
          failureThreshold: 1
          tcpSocket:
            port: 8080
EOF

echo "Deploying Cloud Run service with CORS configuration..."
gcloud run services replace service.yaml --region=${REGION} --project=${PROJECT_ID}

# If the above doesn't work due to authentication requirements, 
# we'll need to use a different approach with IAM conditions

echo ""
echo "If the above deployment fails due to authentication requirements,"
echo "we'll need to create a conditional IAM policy..."

# Create IAM policy that allows unauthenticated access only for OPTIONS requests
cat > cors-policy.yaml << 'EOF'
bindings:
- members:
  - allUsers
  role: roles/run.invoker
  condition:
    title: "Allow OPTIONS for CORS"
    description: "Allow unauthenticated OPTIONS requests for CORS preflight"
    expression: |
      request.method == "OPTIONS"
EOF

echo ""
echo "To apply the conditional IAM policy (if needed):"
echo "gcloud run services set-iam-policy ${SERVICE_NAME} cors-policy.yaml --region=${REGION} --project=${PROJECT_ID}"
echo ""
echo "Service should now be available at:"
echo "https://${SERVICE_NAME}-730192175971.${REGION}.run.app"
