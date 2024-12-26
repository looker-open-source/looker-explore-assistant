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

  # Set the project ID as the default and application-default project ID
  gcloud config set project $TF_VAR_project_id
  # if gcloud auth application-default set-quota-project $TF_VAR_project_id; then
  #   echo "Application-default project set to $TF_VAR_project_id"
  else
    echo "Failed to set application-default project. Please ensure you have application-default credentials set up."
  fi
}

# Function to create Cloud Function key
create_cf_key() {
  VERTEX_CF_AUTH_TOKEN=$(openssl rand -base64 32)
  echo "Generated Cloud Function Key: $VERTEX_CF_AUTH_TOKEN"
  export TF_VAR_vertex_cf_auth_token=$VERTEX_CF_AUTH_TOKEN
}

# Function to refresh application-default credentials
refresh_application_default_credentials() {
  gcloud auth application-default login
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

# Refresh application-default credentials
refresh_application_default_credentials

# Process the provided argument
case "$1" in
  remote)
    # Set default use_cloud_function_backend to true
    export TF_VAR_use_cloud_function_backend=true
    cp backends/backend-gcs.tf backend.tf
    gsutil mb -p $TF_VAR_project_id gs://${TF_VAR_project_id}-terraform-state/

    echo "Initializing Terraform with remote GCS backend..."
    terraform init -backend-config="bucket=${TF_VAR_project_id}-terraform-state"
    ;;
  local)
    echo "Initializing Terraform with local backend..."
    export TF_VAR_use_cloud_function_backend=false
    export TF_VAR_use_bigquery_backend=true
    terraform init
    ;;
  help)
    show_help
    ;;
  *)
    echo "Error: Invalid option '$1'."
    show_help
    exit 1
    ;;
esac

# Apply Terraform configuration
terraform apply -auto-approve
