#!/bin/bash

# Function to display help
show_help() {
  echo "Usage: $0 [option]"
  echo ""
  echo "Options:"
  echo "  remote     Initialize Terraform with remote GCS backend"
  echo "  local      Initialize Terraform with local backend"
  echo "  help       Display this help message"
  echo ""
  echo "Examples:"
  echo "  $0 remote    # Initialize with remote GCS backend"
  echo "  $0 local     # Initialize with local backend"
}

# Function to prompt for environment variables if not set
prompt_for_env_vars() {
  if [ -z "$TF_VAR_project_id" ]; then
    read -p "Enter your GCP project ID: " TF_VAR_project_id
    export TF_VAR_project_id
  fi

  if [ -z "$TF_VAR_region" ]; then
    read -p "Enter your GCP region (e.g., us-central1): " TF_VAR_region
    export TF_VAR_region
  fi

  # Set the entered project ID as the default
  gcloud config set project $TF_VAR_project_id  
}

# Function to create Cloud Function key
create_cf_key() {
  VERTEX_CF_AUTH_TOKEN=$(openssl rand -base64 32)
  echo "Generated Cloud Function Key: $VERTEX_CF_AUTH_TOKEN"
  export TF_VAR_vertex_cf_auth_token=$VERTEX_CF_AUTH_TOKEN
}

# Check if an argument was provided
if [ -z "$1" ]; then
  echo "No option provided. Defaulting to 'remote' backend."
  set -- "remote"
fi

# Create Cloud Function key
create_cf_key

# Prompt for environment variables if not set
prompt_for_env_vars

# Set default use_cloud_function_backend to true
export TF_VAR_use_cloud_function_backend=true
cp backends/backend-gcs.tf backend.tf
sed -i "s/project-id/$TF_VAR_project_id/" backend.tf

# Check if the GCS bucket already exists
BUCKET_NAME="${TF_VAR_project_id}-terraform-state"
if gsutil ls -b gs://$BUCKET_NAME/ &>/dev/null; then
  echo "GCS bucket already exists. Reusing the existing bucket."
else
  echo "GCS bucket does not exist. Creating a new bucket..."
  if gsutil mb -p $TF_VAR_project_id gs://$BUCKET_NAME/; then
    echo "GCS bucket created successfully."
  else
    echo "Failed to create GCS bucket. Please check your permissions and try again."
    exit 1
  fi
fi

echo "Initializing Terraform with remote GCS backend..."
terraform init 

# Apply Terraform configuration
terraform apply
