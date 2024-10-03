
resource "google_service_account" "explore-assistant-bq-sa" {
  account_id   = "explore-assistant-bq-sa"
  display_name = "Looker Explore Assistant BigQuery SA"
}

resource "google_project_iam_member" "iam_permission_bq_data_editor" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = format("serviceAccount:%s", google_service_account.explore-assistant-bq-sa.email)
}

resource "google_project_iam_member" "iam_permission_bq_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = format("serviceAccount:%s", google_service_account.explore-assistant-bq-sa.email)
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

resource "google_bigquery_job" "create_explore_assistant_examples_table" {
  job_id = "create_explore_assistant_examples_table-${formatdate("YYYYMMDDhhmmss", timestamp())}"
  query {
    query              = <<EOF
    CREATE OR REPLACE TABLE `${google_bigquery_dataset.dataset.dataset_id}.trusted_dashboards` (
        explore_id STRING OPTIONS (description = 'Explore id of the explore to pull examples for in a format of -> lookml_model:lookml_explore'),
        lookml STRING OPTIONS (description = 'LookML dashboard copy for authoritative dashboard(s) based on the given explore_id.')
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

resource "google_bigquery_job" "create_explore_assistant_samples_table" {
  job_id = "create_explore_assistant_samples_table-${formatdate("YYYYMMDDhhmmss", timestamp())}"
  query {
    query = <<EOF
    CREATE OR REPLACE TABLE `${google_bigquery_dataset.dataset.dataset_id}.explore_assistant_samples` (
        explore_id STRING OPTIONS (description = 'Explore id of the explore to pull examples for in a format of -> lookml_model:lookml_explore'),
        samples STRING OPTIONS (description = 'Samples for Explore Assistant Samples displayed in UI. JSON document with listed samples with category, prompt and color keys.')
    )
  EOF
    create_disposition  = ""
    write_disposition   = ""
    allow_large_results = false
    flatten_results     = false
    maximum_billing_tier = 0
    schema_update_options = []
    use_legacy_sql      = false
  }

  location   = var.deployment_region
  depends_on = [time_sleep.wait_after_apis_activate]

  lifecycle {
    ignore_changes = [query, job_id]
  }
}
