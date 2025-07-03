#!/bin/bash

# Setup Application Load Balancer with CORS support
# This keeps Cloud Run fully authenticated while handling CORS at the ALB level

PROJECT_ID="combined-genai-bi"
SERVICE_NAME="looker-explore-assistant-mcp"
REGION="us-central1"

echo "Setting up Application Load Balancer with CORS policy..."

# Create a global IP address for the load balancer
gcloud compute addresses create ${SERVICE_NAME}-ip --global --project=${PROJECT_ID}

# Get the IP address
IP_ADDRESS=$(gcloud compute addresses describe ${SERVICE_NAME}-ip --global --format="value(address)" --project=${PROJECT_ID})
echo "Reserved IP: $IP_ADDRESS"

# Create a serverless NEG for your Cloud Run service
gcloud compute network-endpoint-groups create ${SERVICE_NAME}-neg \
    --region=${REGION} \
    --network-endpoint-type=serverless \
    --cloud-run-service=${SERVICE_NAME} \
    --project=${PROJECT_ID}

# Create backend service
gcloud compute backend-services create ${SERVICE_NAME}-backend \
    --global \
    --load-balancing-scheme=EXTERNAL_MANAGED \
    --protocol=HTTP \
    --project=${PROJECT_ID}

# Add the NEG to the backend service
gcloud compute backend-services add-backend ${SERVICE_NAME}-backend \
    --global \
    --network-endpoint-group=${SERVICE_NAME}-neg \
    --network-endpoint-group-region=${REGION} \
    --project=${PROJECT_ID}

# Create URL map with CORS policy
cat > url-map-config.yaml << EOF
name: ${SERVICE_NAME}-url-map
defaultService: projects/${PROJECT_ID}/global/backendServices/${SERVICE_NAME}-backend
hostRules:
- hosts:
  - "*"
  pathMatcher: main
pathMatchers:
- name: main
  defaultService: projects/${PROJECT_ID}/global/backendServices/${SERVICE_NAME}-backend
  routeRules:
  - priority: 1
    matchRules:
    - prefixMatch: "/"
    routeAction:
      corsPolicy:
        allowCredentials: true
        allowHeaders:
        - "Content-Type"
        - "Authorization"
        - "Accept"
        - "Origin"
        - "X-Requested-With"
        allowMethods:
        - "GET"
        - "POST"
        - "OPTIONS"
        - "PUT"
        - "DELETE"
        allowOrigins:
        - "*"
        exposeHeaders:
        - "Content-Length"
        - "Date"
        - "Server"
        maxAge: 3600
EOF

gcloud compute url-maps import ${SERVICE_NAME}-url-map \
    --source=url-map-config.yaml \
    --global \
    --project=${PROJECT_ID}

# Create SSL certificate (replace with your domain)
gcloud compute ssl-certificates create ${SERVICE_NAME}-cert \
    --domains=your-domain.com \
    --global \
    --project=${PROJECT_ID}

# Create HTTPS proxy
gcloud compute target-https-proxies create ${SERVICE_NAME}-https-proxy \
    --ssl-certificates=${SERVICE_NAME}-cert \
    --url-map=${SERVICE_NAME}-url-map \
    --global \
    --project=${PROJECT_ID}

# Create forwarding rule
gcloud compute forwarding-rules create ${SERVICE_NAME}-forwarding-rule \
    --address=${SERVICE_NAME}-ip \
    --target-https-proxy=${SERVICE_NAME}-https-proxy \
    --global \
    --ports=443 \
    --project=${PROJECT_ID}

echo "Load balancer setup complete!"
echo "IP Address: $IP_ADDRESS"
echo "Configure your DNS to point to this IP address"
echo "The load balancer will handle CORS while your Cloud Run service remains fully authenticated"

# Clean up temp file
rm url-map-config.yaml
