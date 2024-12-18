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
IMAGE_NAME="$IMAGE_NAME"
IMAGE="gcr.io/$PROJECT_ID/$IMAGE_NAME"
TAG=$(git rev-parse --short HEAD)


echo "Building Docker image..."
docker build -t $IMAGE:$TAG .

# echo "Testing Docker image locally..."
# docker run -p 8080:8080 gcr.io/$PROJECT_ID/$IMAGE_NAME:$TAG

echo "Pushing Docker image to GCR..."
gcloud auth configure-docker
docker push gcr.io/$PROJECT_ID/$IMAGE_NAME:$TAG