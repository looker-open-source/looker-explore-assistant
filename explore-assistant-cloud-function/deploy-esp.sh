#!/bin/bash

# Deploy Cloud Endpoints with ESP for selective authentication
PROJECT_ID="combined-genai-bi"
SERVICE_NAME="looker-explore-assistant-mcp"
REGION="us-central1"

echo "Deploying Cloud Endpoints configuration..."

# Deploy the API configuration
gcloud endpoints services deploy openapi-spec.yaml --project=${PROJECT_ID}

echo "Building ESP-enabled container..."

# Create Dockerfile that combines ESP and our app
cat > Dockerfile.esp << EOF
FROM gcr.io/endpoints-release/endpoints-runtime:2

# Copy our application
COPY . /app
WORKDIR /app

# Install Python dependencies
RUN apt-get update && apt-get install -y python3 python3-pip
RUN pip3 install -r requirements.txt

# Create nginx configuration for ESP
RUN mkdir -p /etc/nginx/conf.d
COPY esp_nginx.conf /etc/nginx/conf.d/default.conf

# Start script
COPY start_esp.sh /start_esp.sh
RUN chmod +x /start_esp.sh

EXPOSE 8080
CMD ["/start_esp.sh"]
EOF

# Create nginx configuration
cat > esp_nginx.conf << EOF
server {
    listen 8080;
    server_name _;
    
    location /healthz {
        return 200 'ok';
        add_header Content-Type text/plain;
    }
    
    location = / {
        if (\$request_method = OPTIONS) {
            add_header Access-Control-Allow-Origin '*';
            add_header Access-Control-Allow-Methods 'GET, POST, OPTIONS';
            add_header Access-Control-Allow-Headers 'Content-Type, Authorization';
            add_header Access-Control-Max-Age 3600;
            add_header Content-Length 0;
            add_header Content-Type text/plain;
            return 204;
        }
        proxy_pass http://127.0.0.1:9000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOF

# Create start script
cat > start_esp.sh << EOF
#!/bin/bash
# Start Python app in background
python3 mcp_server.py &
# Start nginx in foreground
nginx -g "daemon off;"
EOF

echo "Building container with Cloud Build..."
gcloud builds submit --tag gcr.io/${PROJECT_ID}/${SERVICE_NAME}-esp --project=${PROJECT_ID}
            
            location /health {
                proxy_pass http://127.0.0.1:9000;
                proxy_set_header Host \$host;
                proxy_set_header X-Real-IP \$remote_addr;
            }
        }
    }
EOF

# Create a new Dockerfile for ESP
cat > Dockerfile.esp << EOF
FROM gcr.io/endpoints-release/endpoints-runtime:2

# Copy your application
COPY . /app
WORKDIR /app

# Install Python and dependencies
RUN apt-get update && apt-get install -y python3 python3-pip
RUN pip3 install -r requirements.txt

# Copy ESP configuration
COPY esp_config.yaml /etc/nginx/nginx.conf

# Start script
COPY start-esp.sh /start-esp.sh
RUN chmod +x /start-esp.sh

EXPOSE 8080
CMD ["/start-esp.sh"]
EOF

# Create start script for ESP
cat > start-esp.sh << EOF
#!/bin/bash

# Start your Python application on port 9000
python3 mcp_server.py &

# Start ESP on port 8080
/usr/sbin/nginx -g "daemon off;"
EOF

chmod +x start-esp.sh

# Build and deploy the ESP-enabled container
echo "Building ESP-enabled container..."
docker build -f Dockerfile.esp -t gcr.io/${PROJECT_ID}/${SERVICE_NAME}-esp .
docker push gcr.io/${PROJECT_ID}/${SERVICE_NAME}-esp

# Deploy to Cloud Run with ESP
gcloud run deploy ${SERVICE_NAME}-esp \
    --image=gcr.io/${PROJECT_ID}/${SERVICE_NAME}-esp \
    --platform=managed \
    --region=${REGION} \
    --set-env-vars="PROJECT=${PROJECT_ID},REGION=${REGION}" \
    --set-env-vars="ENDPOINTS_SERVICE_NAME=looker-explore-assistant-mcp-730192175971.us-central1.run.app" \
    --port=8080 \
    --memory=2Gi \
    --cpu=1 \
    --max-instances=10 \
    --project=${PROJECT_ID}

echo "ESP deployment complete!"

# Clean up
rm esp_config.yaml Dockerfile.esp start-esp.sh
