#!/bin/bash

# Load environment variables from the .env file
# Make sure .env is in the same directory as this script
if [ -f .env ]; then
  # Automatically export all variables defined in .env
  set -a
  source .env
  set +a
else
  echo ".env file not found!"
  exit 1
fi

# Configuration
PROJECT_ID="$PROJECT_NAME"
SERVICE_NAME="$IMAGE_NAME"
REGION="$REGION_NAME"
IMAGE="gcr.io/$PROJECT_ID/$SERVICE_NAME"

# Environment Variables from the .env file (now available due to set -a)
# Example:
# VERTEX_AI_ENDPOINT, VERTEX_CF_AUTH_TOKEN, etc. are now automatically available

# Combine environment variables into a single string for Cloud Run
ENV_VARS="PROJECT=$PROJECT,REGION=$REGION,VERTEX_AI_ENDPOINT=$VERTEX_AI_ENDPOINT,VERTEX_CF_AUTH_TOKEN=$VERTEX_CF_AUTH_TOKEN,VERTEX_BIGQUERY_LOOKER_CONNECTION_NAME=$VERTEX_BIGQUERY_LOOKER_CONNECTION_NAME,BIGQUERY_EXAMPLE_PROMPTS_CONNECTION_NAME=$BIGQUERY_EXAMPLE_PROMPTS_CONNECTION_NAME,BIGQUERY_EXAMPLE_PROMPTS_DATASET_NAME=$BIGQUERY_EXAMPLE_PROMPTS_DATASET_NAME"

# Authenticate with Google Cloud
echo "Authenticating with Google Cloud..."
gcloud auth login
gcloud auth application-default login
gcloud auth application-default set-quota-project "$PROJECT_ID"
gcloud config set project "$PROJECT_ID"

# Build the container image and submit it to Google Container Registry
echo "Building the container image..."
gcloud builds submit --tag "$IMAGE"

# Deploy the container to Cloud Run
echo "Deploying the container to Cloud Run..."
gcloud run deploy "$SERVICE_NAME" \
  --image "$IMAGE" \
  --platform managed \
  --region "$REGION" \
  --set-env-vars "$ENV_VARS" \
  --allow-unauthenticated

# Print the service URL
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format 'value(status.url)')
echo "Service deployed to: $SERVICE_URL"
