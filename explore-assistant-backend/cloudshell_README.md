# Looker Explore Assistant Backend Service

This is an automatic installer of the GCP Cloud Run backend service.
This is intended to be installed in an empty google project. If you are using a project that already has resources in it, see the step-by-step configuration section below.
To begin, please execute:
```
cd explore-assistant-backend/terraform && ./init.sh
```

## Caution
If resources will be deleted or destroyed by Terraform, please abort the process to avoid destroying existing resources. Use the step-by-step configuration section below instead. For more information on the choice of backend, please see [the Backend README.](./README.md)

# Step by Step Configuration

## 1: Set up Environment Variables
Make sure to replace PROJECT_ID and REGION values with actual values. The other values can be left as default.
``` bash
export PROJECT_ID="your-project-id"
export REGION="us-central1"
export DATASET_ID="explore_assistant"
export CLOUD_RUN_SERVICE_NAME="explore-assistant-api"
export VERTEX_CF_AUTH_TOKEN=$(openssl rand -base64 32)
echo $VERTEX_CF_AUTH_TOKEN
```
Please copy the Vertex CF Auth Token that is printed out. This will be used later in the frontend setup.

## 2: Enable Required APIs
(for Both backend types)
``` bash
gcloud services enable serviceusage.googleapis.com \
    cloudresourcemanager.googleapis.com \
    iam.googleapis.com \
    aiplatform.googleapis.com \
    bigquery.googleapis.com \
    cloudapis.googleapis.com \
    cloudbuild.googleapis.com \
    cloudfunctions.googleapis.com \
    run.googleapis.com \
    storage-api.googleapis.com \
    storage.googleapis.com \
    compute.googleapis.com \
    secretmanager.googleapis.com
```

## 3: Create Service Account
(for Both backend types)
```bash 
gcloud iam service-accounts create explore-assistant-cf-sa \
    --display-name "Looker Explore Assistant Cloud Function SA"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member "serviceAccount:explore-assistant-cf-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role "roles/aiplatform.user"
```

## 4: Create Secret in Secret Manager 
(for Cloud Function backend ONLY)
``` bash
echo -n $VERTEX_CF_AUTH_TOKEN | gcloud secrets create VERTEX_CF_AUTH_TOKEN \
    --replication-policy=user-managed \
    --locations=$REGION \
    --data-file=-

gcloud secrets add-iam-policy-binding VERTEX_CF_AUTH_TOKEN \
    --member "serviceAccount:explore-assistant-cf-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role "roles/secretmanager.secretAccessor"
```

## 5: Create Storage Bucket for Cloud Function Source 
(for Cloud Function backend ONLY)
``` bash
BUCKET_NAME="${PROJECT_ID}-gcf-source-$(openssl rand -hex 4)"
gsutil mb -p $PROJECT_ID -l US gs://$BUCKET_NAME/
```

## 6: Upload Cloud Function Source Code
(for Cloud Function backend ONLY)
```bash
cd ./explore-assistant-cloud-function && zip -r ./function-source.zip * && cd ..
gsutil cp function-source.zip gs://$BUCKET_NAME/
```

## 7: Create Artifact Registry Repository
(for Cloud Function backend ONLY)
```bash
gcloud artifacts repositories create explore-assistant-repo \
    --repository-format=docker \
    --location=$REGION \
    --project=$PROJECT_ID \
    --description="Docker repository for Explore Assistant"
```

## 8: Deploy Cloud Function
(for Cloud Function backend ONLY)
```bash
gcloud functions deploy $CLOUD_RUN_SERVICE_NAME \
    --gen2 \
    --region=$REGION \
    --project=$PROJECT_ID \
    --runtime=python310 \
    --entry-point=cloud_function_entrypoint \
    --trigger-http \
    --source=gs://$BUCKET_NAME/function-source.zip \
    --set-env-vars=REGION=$REGION,PROJECT=$PROJECT_ID \
    --set-secrets=VERTEX_CF_AUTH_TOKEN=VERTEX_CF_AUTH_TOKEN:latest \
    --max-instances=10 \
    --memory=4Gi \
    --timeout=60s \
    --service-account=explore-assistant-cf-sa@$PROJECT_ID.iam.gserviceaccount.com
```

## 9: Make Cloud Function Public
(for Cloud Function backend ONLY)
```bash
gcloud functions add-iam-policy-binding $CLOUD_RUN_SERVICE_NAME \
    --region=$REGION \
    --member="allUsers" \
    --role="roles/cloudfunctions.invoker"
gcloud functions describe $CLOUD_RUN_SERVICE_NAME --region=$REGION --format='value(httpsTrigger.url)'
```
The Cloud function url will be printed out and should be copied. This will be used in the frontend installation.

## 10: Create BigQuery Dataset
(for Both backend types)
``` bash
bq --location=$REGION mk --dataset $PROJECT_ID:$DATASET_ID
```

## 11: Create BigQuery Tables
(for Both backend types)
``` bash
bq query --use_legacy_sql=false --location=$REGION \
    "CREATE OR REPLACE TABLE \`${DATASET_ID}.explore_assistant_examples\` (
        explore_id STRING OPTIONS (description = 'Explore id of the explore to pull examples for in a format of -> lookml_model:lookml_explore'),
        examples STRING OPTIONS (description = 'Examples for Explore Assistant training. JSON document with list hashes each with input and output keys.')
    )"

bq query --use_legacy_sql=false --location=$REGION \
    "CREATE OR REPLACE TABLE \`${DATASET_ID}.explore_assistant_refinement_examples\` (
        explore_id STRING OPTIONS (description = 'Explore id of the explore to pull examples for in a format of -> lookml_model:lookml_explore'),
        examples STRING OPTIONS (description = 'Examples for Explore Assistant training. JSON document with list hashes each with input and output keys.')
    )"

bq query --use_legacy_sql=false --location=$REGION \
    "CREATE OR REPLACE TABLE \`${DATASET_ID}.explore_assistant_samples\` (
        explore_id STRING OPTIONS (description = 'Explore id of the explore to pull examples for in a format of -> lookml_model:lookml_explore'),
        samples STRING OPTIONS (description = 'Samples for Explore Assistant Samples displayed in UI. JSON document with listed samples with category, prompt and color keys.')
    )"
```

## 12: Create BigQuery Connection and Model  
(For BigQuery backend install ONLY)
``` bash
gcloud bigquery connections create explore_assistant_llm \
    --project=$PROJECT_ID \
    --location=$REGION \
    --connection-type=CLOUD_RESOURCE

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member "serviceAccount:$(gcloud bigquery connections describe explore_assistant_llm --location=$REGION --format='value(cloudResource.serviceAccountId)')" \
    --role "roles/aiplatform.user"

bq query --use_legacy_sql=false --location=$REGION \
    "CREATE OR REPLACE MODEL \`${DATASET_ID}.explore_assistant_llm\` 
    REMOTE WITH CONNECTION \`$PROJECT_ID.$REGION.explore_assistant_llm\` 
    OPTIONS (endpoint = 'gemini-1.5-flash')"
```