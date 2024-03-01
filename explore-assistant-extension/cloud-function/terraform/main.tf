/*

MIT License

Copyright (c) 2023 Looker Data Sciences, Inc.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

*/

/**
 * This Terraform configuration file sets up a Google Cloud Function for the Looker Explore Assistant.
 * It provisions the necessary resources such as project services, service accounts, IAM permissions,
 * storage bucket, and deploys the Cloud Function with the specified runtime and configuration.
 * The Cloud Function acts as an endpoint for generating Looker queries from natural language using Generative UI.
 * It also includes IAM permissions for Cloud Functions Gen2 to allow public access.
 */
 
provider "google" {
  project = var.project_id
}

module "project-services" {
  source                      = "terraform-google-modules/project-factory/google//modules/project_services"
  version                     = "14.2.1"
  disable_services_on_destroy = false

  project_id  = var.project_id
  enable_apis = true

  activate_apis = [
    "cloudresourcemanager.googleapis.com", 
    "cloudapis.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudfunctions.googleapis.com",
    "run.googleapis.com",
    "iam.googleapis.com",
    "serviceusage.googleapis.com",
    "storage-api.googleapis.com",
    "storage.googleapis.com",
    "aiplatform.googleapis.com",
    "compute.googleapis.com"
  ]
}

resource "time_sleep" "wait_after_apis_activate" {
  depends_on      = [module.project-services]
  create_duration = "20s"
}

resource "google_service_account" "looker_llm_service_account" {
  account_id   = "explore-assistant-sa"
  display_name = "Looker Explore Assistant SA"
  depends_on = [ time_sleep.wait_after_apis_activate ]
}
# TODO: Remove Editor and apply right permissions
resource "google_project_iam_member" "iam_permission_looker_bq" {
  project = var.project_id
  role    = "roles/editor"
  member  = format("serviceAccount:%s", google_service_account.looker_llm_service_account.email)
  depends_on = [ time_sleep.wait_after_apis_activate ]
}

resource "google_project_iam_member" "iam_permission_looker_aiplatform" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = format("serviceAccount:%s", google_service_account.looker_llm_service_account.email)
  depends_on = [ time_sleep.wait_after_apis_activate ]
}

resource "google_project_iam_member" "iam_service_account_act_as" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = format("serviceAccount:%s", google_service_account.looker_llm_service_account.email)
  depends_on = [ time_sleep.wait_after_apis_activate ]
}

# IAM permission as Editor
resource "google_project_iam_member" "iam_looker_service_usage" {  
  project = var.project_id
  role    = "roles/serviceusage.serviceUsageConsumer"
  member  = format("serviceAccount:%s", google_service_account.looker_llm_service_account.email)
  depends_on = [ time_sleep.wait_after_apis_activate ]
}

resource "random_id" "default" {
  byte_length = 8
}

resource "google_storage_bucket" "default" {
  name                        = "${random_id.default.hex}-gcf-source" # Every bucket name must be globally unique
  location                    = "US"
  uniform_bucket_level_access = true
  depends_on                  = [random_id.default, time_sleep.wait_after_apis_activate]
}

data "archive_file" "default" {
  type        = "zip"
  output_path = "/tmp/function-source.zip"
  source_dir  = "../src/"
}
resource "google_storage_bucket_object" "object" {
  name   = "function-source.zip"
  bucket = google_storage_bucket.default.name
  source = data.archive_file.default.output_path # Add path to the zipped function source code
}

resource "google_cloudfunctions2_function" "default" {
  for_each    = toset(var.deployment_region)

  name        = "explore-assistant-endpoint-prod"
  location    = each.value
  description = "An endpoint for generating Looker queries from natural language using Generative UI"

  build_config {
    runtime     = "python310"
    entry_point = "gen_looker_query" # Set the entry point
    source {
      storage_source {
        bucket = google_storage_bucket.default.name
        object = google_storage_bucket_object.object.name
      }
    }
  }

  service_config {
    max_instance_count = 10
    min_instance_count = 1
    available_memory   = "4Gi"
    timeout_seconds    = 60
    available_cpu      = "4"
    max_instance_request_concurrency = 20
    environment_variables = {
        REGION = each.value
        PROJECT = var.project_id
    }
    all_traffic_on_latest_revision = true
    service_account_email = google_service_account.looker_llm_service_account.email
  }
}

### IAM permissions for Cloud Functions Gen2 (requires run invoker as well) for public access

resource "google_cloudfunctions2_function_iam_member" "default" {
  for_each = toset(var.deployment_region)

  location = google_cloudfunctions2_function.default[each.key].location
  project  = google_cloudfunctions2_function.default[each.key].project
  cloud_function  = google_cloudfunctions2_function.default[each.key].name
  role     = "roles/cloudfunctions.invoker"
  member   = "allUsers"

  depends_on = [google_cloudfunctions2_function.default]
}

data "google_iam_policy" "noauth" {
  binding {
    role = "roles/run.invoker"
    members = [
      "allUsers",
    ]
  }
}

resource "google_cloud_run_service_iam_policy" "noauth" {
  for_each = toset(var.deployment_region)

  location    = google_cloudfunctions2_function.default[each.key].location
  project     = google_cloudfunctions2_function.default[each.key].project
  service     = google_cloudfunctions2_function.default[each.key].name

  policy_data = data.google_iam_policy.noauth.policy_data

  depends_on = [google_cloudfunctions2_function.default]
}

output "function_uri" {
  value = values(google_cloudfunctions2_function.default).*.url
}

output "data" {
  value = values(google_cloudfunctions2_function.default)
} 
