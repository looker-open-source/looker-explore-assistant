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

## env_var. Refer to ./.env
REGION_NAME="$REGION_NAME"
PROJECT_ID="$PROJECT_NAME"
IMAGE_NAME="$IMAGE_NAME"

## hard coded
REPO_NAME="looker-explore-assistant"
REPOSITORY_REGION="$REGION_NAME-docker.pkg.dev"
TAG="latest"
IMAGE="$REPOSITORY_REGION/$PROJECT_ID/$REPO_NAME/$IMAGE_NAME:$TAG"

echo "Building Docker image..."
docker build -t $IMAGE .

# echo "Testing Docker image locally..."
# docker run -p 8080:8080 gcr.io/$PROJECT_ID/$IMAGE_NAME:$TAG

echo "Pushing Docker image to GCR..."
gcloud auth configure-docker $REPOSITORY_REGION

# Check if repository exists first
REPO_EXISTS=$(gcloud artifacts repositories list --project=$PROJECT_ID --filter="name:$REPO_NAME" --format="get(name)")

if [ -z "$REPO_EXISTS" ]; then
    echo "Creating new repository $REPO_NAME..."
    gcloud artifacts repositories create $REPO_NAME --repository-format=docker \
        --location=$REGION_NAME --description="Looker explore assistant repository" \
        --project=$PROJECT_ID
else
    echo "Repository $REPO_NAME already exists, skipping creation..."
fi

docker push $IMAGE

cat <<EOF
=================================================
Image pushed to Artifact Registry.

To deploy the image with terraform, please copy the following variables to variables.tfvars file:
=================================================


image="$IMAGE"
use_cloud_run_backend=true


EOF