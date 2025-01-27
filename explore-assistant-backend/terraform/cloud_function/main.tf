variable "cloud_run_service_name" {
  type = string
}

variable "deployment_region" {
  type = string
}

variable "project_id" {
  type = string
}

variable "vertex_cf_auth_token" {
  type = string
}

locals {
  source_directory = "../../../explore-assistant-cloud-function"
}

resource "google_service_account" "explore-assistant-sa" {
  account_id   = "explore-assistant-cf-sa"
  display_name = "Looker Explore Assistant Cloud Function SA"
}

resource "google_project_iam_member" "iam_permission_looker_aiplatform" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = format("serviceAccount:%s", google_service_account.explore-assistant-sa.email)
}

resource "google_secret_manager_secret" "vertex_cf_auth_token" {
  project   = var.project_id
  secret_id = "VERTEX_CF_AUTH_TOKEN"
  replication {
    user_managed {
      replicas {
        location = var.deployment_region
      }
    }
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "google_secret_manager_secret_version" "vertex_cf_auth_token_version" {
  secret      = google_secret_manager_secret.vertex_cf_auth_token.name
  secret_data = var.vertex_cf_auth_token
}

resource "google_secret_manager_secret_iam_binding" "vertex_cf_auth_token_accessor" {
  secret_id = google_secret_manager_secret.vertex_cf_auth_token.secret_id
  role      = "roles/secretmanager.secretAccessor"
  members   = [
    "serviceAccount:${google_service_account.explore-assistant-sa.email}",
  ]
}

resource "random_id" "default" {
  byte_length = 8
}
 
resource "google_storage_bucket" "default" {
  name                        = "${random_id.default.hex}-${var.project_id}-gcf-source" # Every bucket name must be globally unique
  location                    = "US"
  uniform_bucket_level_access = true
  depends_on                  = [random_id.default]

  lifecycle {
    create_before_destroy = true
  }
}

data "archive_file" "default" {
  type        = "zip"
  output_path = "/tmp/function-source.zip"
  source  = ../../../explore-assistant-cloud-function
  output_file_mode = "0666"
}

resource "google_storage_bucket_object" "object" {
  name   = "function-source-${data.archive_file.default.output_sha}.zip"  // Add hash to force update
  bucket = google_storage_bucket.default.name
  source = data.archive_file.default.output_path

  lifecycle {
    create_before_destroy = true
  }
}

resource "google_artifact_registry_repository" "default" {
  repository_id = "explore-assistant-repo"
  location      = var.deployment_region
  project       = var.project_id
  format        = "DOCKER"

  lifecycle {
    create_before_destroy = true
  }
}

resource "google_cloudfunctions2_function" "default" {
  name        = var.cloud_run_service_name
  location    = var.deployment_region
  description = "An endpoint for generating Looker queries from natural language using Generative UI"

  build_config {
    runtime           = "python310"
    entry_point       = "cloud_function_entrypoint" // Set the entry point
    docker_repository = google_artifact_registry_repository.default.id
    source {
      storage_source {
        bucket = google_storage_bucket.default.name
        object = google_storage_bucket_object.object.name
      }
    }

    environment_variables = {
      FUNCTIONS_FRAMEWORK = 1
      SOURCE_HASH         = data.archive_file.default.output_sha
      GOOGLE_FUNCTION_SOURCE = "main.py"  // Ensure this line is correct
    }
  }

  service_config {
    max_instance_count               = 10
    min_instance_count               = 1
    available_memory                 = "4Gi"
    timeout_seconds                  = 60
    available_cpu                    = "4"
    max_instance_request_concurrency = 20
    environment_variables = {
      REGION  = var.deployment_region
      PROJECT = var.project_id
    }

    secret_environment_variables {
      key     = "VERTEX_CF_AUTH_TOKEN"
      project_id = var.project_id
      secret  = google_secret_manager_secret.vertex_cf_auth_token.secret_id
      version = "latest"
    }

    all_traffic_on_latest_revision = true
    service_account_email          = google_service_account.explore-assistant-sa.email
  }

  lifecycle {
    create_before_destroy = true
  }
}

### IAM permissions for Cloud Functions Gen2 (requires run invoker as well) for public access

resource "google_cloudfunctions2_function_iam_member" "default" {
  location       = google_cloudfunctions2_function.default.location
  project        = google_cloudfunctions2_function.default.project
  cloud_function = google_cloudfunctions2_function.default.name
  role           = "roles/cloudfunctions.invoker"
  member         = "allUsers"

  lifecycle {
    create_before_destroy = true
  }
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
  location = google_cloudfunctions2_function.default.location
  project  = google_cloudfunctions2_function.default.project
  service  = google_cloudfunctions2_function.default.name

  policy_data = data.google_iam_policy.noauth.policy_data

  lifecycle {
    create_before_destroy = true
  }
}

output "function_uri" {
  value = google_cloudfunctions2_function.default.url
}

output "data" {
  value = google_cloudfunctions2_function.default
}
