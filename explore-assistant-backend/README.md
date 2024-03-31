# Explore Assistant Backend

## Overview

This Terraform configuration establishes a backend for the Looker Explore Assistant on Google Cloud Platform (GCP), facilitating interaction with the Gemini Pro model of Vertex AI. The setup supports two options: a Cloud Function backend and a BigQuery backend, each acting as a proxy/relay for running content through the model.

The Explore Assistant also uses a set of examples to improve the quality of its answers. We store those examples in BigQuery. 

## Prerequisites

- Terraform installed on your machine.
- Access to a GCP account with permission to create and manage resources.
- A GCP project where the resources will be deployed.

## Configuration and Deployment

Start by initiatlizing terraform with:

```bash

cd terraform
terraform init
```

### Cloud Function Backend

First create a file that will contain the LOOKER_AUTH_TOKEN and place it at the root. This will be used my the cloud function locally, as well as the extension framework app.

```bash
openssl rand -base64 32 > .vertex_cf_auth_token

```

To deploy the Cloud Function backend:

```bash
export TF_VAR_project_id=XXX
export TF_VAR_use_bigquery_backend=0
export TF_VAR_use_cloud_function_backend=1
export TF_VAR_looker_auth_token=$(cat ../../.vertex_cf_auth_token)
terraform plan
terraform apply
```

### BigQuery Backend

To deploy the BigQuery backend:

```bash
export TF_VAR_project_id=XXX
export TF_VAR_use_bigquery_backend=1
export TF_VAR_use_cloud_function_backend=0
terraform plan
terraform apply
```

## Deployment Notes

- Changes to the code in `explore-assistant-cloud-function` will result in a zip file with a new hash. This hash is added to the environment variables for the cloud function, and a new hash will trigger the redeployment of the cloud function.

## Resources Created

- Google Cloud Functions or Cloud Run services, based on the selected backend.
- Google BigQuery dataset and table to store the examples
- Google BigQuery connection and gemini pro model, if using the BigQuery backend.
- Necessary IAM roles and permissions for the Looker Explore Assistant to operate.
- Storage buckets for deploying cloud functions or storing data.
- Artifact Registry for storing Docker images, if required.

## Cleaning Up

To remove all resources created by this Terraform configuration, run:

```sh
terraform destroy
```

**Note:** This will delete all resources and data. Ensure you have backups if needed.

## Support

For issues, questions, or contributions, please open an issue in the GitHub repository where this configuration is hosted.
