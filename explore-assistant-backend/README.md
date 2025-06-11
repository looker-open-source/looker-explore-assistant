# Explore Assistant Backend

## Overview

The Looker Explore Assistant backend no longer requires Terraform or Cloud Functions. The only setup required is creating the necessary BigQuery tables and configuring OAuth in GCP. This simplifies the installation process and removes the need for additional backend services.

## Prerequisites

- Access to a GCP account with permission to create and manage resources.
- A GCP project where the resources will be deployed.
- A Looker connection to BigQuery.

## Configuration and Deployment

### 1: Enable Required APIs
```bash
gcloud services enable serviceusage.googleapis.com \
    cloudresourcemanager.googleapis.com \
    iam.googleapis.com \
    aiplatform.googleapis.com \
    bigquery.googleapis.com \
    cloudapis.googleapis.com \
    storage.googleapis.com \
    compute.googleapis.com \
    secretmanager.googleapis.com
```

### 2: Create BigQuery Dataset and Tables
```bash
bq --location=us-central1 mk --dataset $PROJECT_ID:explore_assistant

bq query --use_legacy_sql=false --location=us-central1 \
    "CREATE OR REPLACE TABLE \`explore_assistant.golden_queries\` (
        explore_id STRING OPTIONS (description = 'Explore id of the explore to pull examples for in a format of -> lookml_model:lookml_explore'),
        input STRING OPTIONS (description = 'Natural language input question for the example'),
        output STRING OPTIONS (description = 'Looker query URL parameters as output for the example')
    )"

bq query --use_legacy_sql=false --location=us-central1 \
    "CREATE OR REPLACE TABLE \`explore_assistant.explore_assistant_samples\` (
        explore_id STRING OPTIONS (description = 'Explore id of the explore to pull examples for in a format of -> lookml_model:lookml_explore'),
        samples STRING OPTIONS (description = 'Samples for Explore Assistant Samples displayed in UI. JSON document with listed samples with category, prompt and color keys.')
    )"

bq query --use_legacy_sql=false --location=us-central1 \
    "CREATE OR REPLACE TABLE \`explore_assistant.explore_assistant_refinement_examples\` (
        explore_id STRING OPTIONS (description = 'Explore id of the explore to pull examples for in a format of -> lookml_model:lookml_explore'),
        examples STRING OPTIONS (description = 'Examples for Explore Assistant training. JSON document with list hashes each with input and output keys.')
    )"
```

### 3: Configure OAuth Consent and App in GCP
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Navigate to **APIs & Services** > **OAuth consent screen**.
3. Configure the consent screen with the required details.
4. Create an OAuth 2.0 Client ID under **Credentials**.
5. Note the Client ID and Secret for use in the Looker Explore Assistant.

### 4: Connect Looker to BigQuery
Follow the [Looker documentation](https://cloud.google.com/looker/docs/db-config-google-bigquery) to set up a BigQuery connection in Looker. Ensure the connection has access to the `explore_assistant` dataset.

## Cleaning Up

To remove all resources created, delete the BigQuery dataset and any associated OAuth credentials in GCP.

## Support

For issues, questions, or contributions, please open an issue in the GitHub repository where this configuration is hosted.
