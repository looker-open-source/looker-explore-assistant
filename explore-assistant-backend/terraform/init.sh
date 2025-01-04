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

# Check if an argument was provided
if [ -z "$1" ]; then
  echo "Error: No option provided."
  show_help
  exit 1
fi

# Check if TF_VAR_project_id is set
if [ -z "$TF_VAR_project_id" ]; then
  echo "Error: TF_VAR_project_id environment variable is not set."
  exit 1
fi

# Process the provided argument
case "$1" in
  remote)
    cp backends/backend-gcs.tf backend.tf
    gsutil mb -p $TF_VAR_project_id gs://${TF_VAR_project_id}-terraform-state/

    echo "Initializing Terraform with remote GCS backend..."
    terraform init -backend-config="bucket=${TF_VAR_project_id}-terraform-state"
    ;;
  local)
    echo "Initializing Terraform with local backend..."
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
