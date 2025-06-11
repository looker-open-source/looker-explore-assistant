# Looker Explore Assistant Backend Service

This document outlines the steps required to set up the Looker Explore Assistant backend. The backend no longer requires Terraform or Cloud Functions. Instead, the only setup required is creating the necessary BigQuery tables and configuring OAuth in GCP.

## Step-by-Step Configuration

### 1: Set up Environment Variables
Make sure to replace PROJECT_ID and REGION values with actual values.
```bash
export PROJECT_ID="your-project-id"
export REGION="us-central1"
export DATASET_ID="explore_assistant"
gcloud config set project $PROJECT_ID
```

### 2: Enable Required APIs
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

### 3: Create BigQuery Dataset and Tables
```bash
bq --location=$REGION mk --dataset $PROJECT_ID:$DATASET_ID

bq query --use_legacy_sql=false --location=$REGION \
    "CREATE OR REPLACE TABLE \`${DATASET_ID}.golden_queries\` (
        explore_id STRING OPTIONS (description = 'Explore id of the explore to pull examples for in a format of -> lookml_model:lookml_explore'),
        input STRING OPTIONS (description = 'Natural language input question for the example'),
        output STRING OPTIONS (description = 'Looker query URL parameters as output for the example')
    )"

bq query --use_legacy_sql=false --location=$REGION \
    "CREATE OR REPLACE TABLE \`${DATASET_ID}.explore_assistant_samples\` (
        explore_id STRING OPTIONS (description = 'Explore id of the explore to pull examples for in a format of -> lookml_model:lookml_explore'),
        samples STRING OPTIONS (description = 'Samples for Explore Assistant Samples displayed in UI. JSON document with listed samples with category, prompt and color keys.')
    )"

bq query --use_legacy_sql=false --location=$REGION \
    "CREATE OR REPLACE TABLE \`${DATASET_ID}.explore_assistant_refinement_examples\` (
        explore_id STRING OPTIONS (description = 'Explore id of the explore to pull examples for in a format of -> lookml_model:lookml_explore'),
        examples STRING OPTIONS (description = 'Examples for Explore Assistant training. JSON document with list hashes each with input and output keys.')
    )"
```

### 4: Configure OAuth Consent and App in GCP
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Navigate to **APIs & Services** > **OAuth consent screen**.
3. Configure the consent screen with the required details.
4. Create an OAuth 2.0 Client ID under **Credentials**.
5. Note the Client ID and Secret for use in the Looker Explore Assistant.

### 5: Connect Looker to BigQuery
Follow the [Looker documentation](https://cloud.google.com/looker/docs/db-config-google-bigquery) to set up a BigQuery connection in Looker. Ensure the connection has access to the `explore_assistant` dataset.