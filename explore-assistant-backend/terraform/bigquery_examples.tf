

resource "google_bigquery_dataset" "dataset" {
  dataset_id    = var.dataset_id_name
  friendly_name = var.dataset_id_name
  description   = "bq llm dataset for remote vertex ai model"
  location      = var.deployment_region
}

resource "google_service_account" "looker_llm_service_account" {
  account_id   = "looker-explore-assistant-sa"
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

resource "google_bigquery_job" "create_explore_assistant_examples_table" {
  job_id = "create_explore_assistant_examples_table-${formatdate("YYYYMMDDhhmmss", timestamp())}"
  query {
    query              = <<EOF
    CREATE OR REPLACE TABLE `${google_bigquery_dataset.dataset.dataset_id}.explore_assistant_examples` (
        explore_id STRING OPTIONS (description = 'Explore id of the explore to pull examples for in a format of -> lookml_model:lookml_explore'),
        examples STRING OPTIONS (description = 'Examples for Explore Assistant training. JSON document with list hashes each with input and output keys.')
    )
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
  depends_on = [ time_sleep.wait_after_apis_activate]

  lifecycle {
    ignore_changes  = [query, job_id]
  }
}


resource "google_bigquery_job" "create_explore_assistant_refinement_examples_table" {
  job_id = "create_explore_assistant_refinement_examples_table-${formatdate("YYYYMMDDhhmmss", timestamp())}"
  query {
    query              = <<EOF
    CREATE OR REPLACE TABLE `${google_bigquery_dataset.dataset.dataset_id}.explore_assistant_refinement_examples` (
        explore_id STRING OPTIONS (description = 'Explore id of the explore to pull examples for in a format of -> lookml_model:lookml_explore'),
        examples STRING OPTIONS (description = 'Examples for Explore Assistant training. JSON document with list hashes each with input and output keys.')
    )
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
  depends_on = [ time_sleep.wait_after_apis_activate]
  lifecycle {
    ignore_changes  = [query, job_id]
  }
}
