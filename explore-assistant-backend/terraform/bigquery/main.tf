variable "deployment_region" {
    type = string
}

variable "project_id" {
    type = string
}

variable "dataset_id_name" {
    type = string
}

resource "google_bigquery_connection" "connection" {
  connection_id = "looker-llm-connection"
  project       = var.project_id
  location      = var.deployment_region
  cloud_resource {}
}

resource "google_service_account" "looker_llm_service_account" {
  account_id   = "looker-llm-sa"
  display_name = "Looker LLM SA"
}

resource "google_project_iam_member" "iam_permission_looker_bq" {
  project    = var.project_id
  role       = "roles/editor"
  member     = format("serviceAccount:%s", google_service_account.looker_llm_service_account.email)
}

resource "google_project_iam_member" "iam_permission_looker_aiplatform" {
  project    = var.project_id
  role       = "roles/aiplatform.user"
  member     = format("serviceAccount:%s", google_service_account.looker_llm_service_account.email)
}

# IAM for connection to be able to execute vertex ai queries through BQ
resource "google_project_iam_member" "bigquery_connection_remote_model" {
  project    = var.project_id
  role       = "roles/aiplatform.user"
  member     = format("serviceAccount:%s", google_bigquery_connection.connection.cloud_resource[0].service_account_id)
}


resource "google_project_iam_member" "iam_service_account_act_as" {
  project    = var.project_id
  role       = "roles/iam.serviceAccountUser"
  member     = format("serviceAccount:%s", google_service_account.looker_llm_service_account.email)
}

# IAM permission as Editor
resource "google_project_iam_member" "iam_looker_service_usage" {
  project    = var.project_id
  role       = "roles/serviceusage.serviceUsageConsumer"
  member     = format("serviceAccount:%s", google_service_account.looker_llm_service_account.email)
}

# IAM permission as Editor
resource "google_project_iam_member" "iam_looker_bq_consumer" {
  project    = var.project_id
  role       = "roles/bigquery.connectionUser"
  member     = format("serviceAccount:%s", google_service_account.looker_llm_service_account.email)
}

resource "google_bigquery_dataset" "dataset" {
  dataset_id    = var.dataset_id_name
  friendly_name = var.dataset_id_name
  description   = "bq llm dataset for remote vertex ai model"
  location      = var.deployment_region
}


resource "google_bigquery_job" "create_bq_model_llm" {
  job_id = "create_looker_llm_model-${formatdate("YYYYMMDDhhmmss", timestamp())}"
  query {
    query              = <<EOF
CREATE OR REPLACE MODEL `${google_bigquery_dataset.dataset.dataset_id}.llm_model` 
REMOTE WITH CONNECTION `${google_bigquery_connection.connection.name}` 
OPTIONS (endpoint = 'gemini-pro')
EOF  
    create_disposition = ""
    write_disposition  = ""
    allow_large_results = false
    flatten_results = false
    maximum_billing_tier = 0
    schema_update_options = [ ]
    use_legacy_sql = false
  }

  location = var.deployment_region
}