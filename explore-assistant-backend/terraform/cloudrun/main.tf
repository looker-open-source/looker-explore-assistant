variable "cloud_run_service_name" {
  type = string
}

variable "deployment_region" {
  type = string
}

variable "project_id" {
  type = string
}

resource "google_service_account" "explore_assistant_sa" {
  account_id   = "explore-assistant-cr-sa"
  display_name = "Looker Explore Assistant Cloud Run SA"
}

resource "google_project_iam_member" "iam_permission_looker_aiplatform" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = format("serviceAccount:%s", google_service_account.explore_assistant_sa.email)
}

resource "google_secret_manager_secret" "vertex_cr_auth_token" {
  project   = var.project_id
  secret_id = "VERTEX_CR_AUTH_TOKEN"
  replication {
    user_managed {
      replicas {
        location = var.deployment_region
      }
    }
  }
}

locals {
  auth_token_file_path    = "${path.module}/../../../.vertex_cr_auth_token"
  auth_token_file_exists  = fileexists(local.auth_token_file_path)
  auth_token_file_content = local.auth_token_file_exists ? file(local.auth_token_file_path) : ""
}

resource "google_secret_manager_secret_version" "vertex_cr_auth_token_version" {
  count       = local.auth_token_file_exists ? 1 : 0
  secret      = google_secret_manager_secret.vertex_cr_auth_token.name
  secret_data = local.auth_token_file_content
}

resource "google_secret_manager_secret_iam_binding" "vertex_cr_auth_token_accessor" {
  secret_id = google_secret_manager_secret.vertex_cr_auth_token.secret_id
  role      = "roles/secretmanager.secretAccessor"
  members   = [
    "serviceAccount:${google_service_account.explore_assistant_sa.email}",
  ]
}

resource "google_artifact_registry_repository" "default" {
  repository_id = "explore-assistant-repo"
  location      = var.deployment_region
  project       = var.project_id
  format        = "DOCKER"
}

resource "random_id" "default" {
  byte_length = 8
}

data "archive_file" "default" {
  type        = "zip"
  output_path = "/tmp/service-source.zip"
  source_dir  = "../../explore-assistant-cloud-run/" # Path to the Cloud Run service source code
}

resource "google_storage_bucket" "default" {
  name                        = "${random_id.default.hex}-${var.project_id}-cr-source"
  location                    = "US"
  uniform_bucket_level_access = true
}

resource "google_storage_bucket_object" "object" {
  name   = "service-source.zip"
  bucket = google_storage_bucket.default.name
  source = data.archive_file.default.output_path
}

resource "google_cloud_run_service" "default" {
  name     = var.cloud_run_service_name
  location = var.deployment_region
  project  = var.project_id

  template {
    spec {
      containers {
        image = "gcr.io/${var.project_id}/explore-assistant:latest" # Replace with your image tag
        resources {
          limits = {
            memory = "4Gi"
            cpu    = "1000m"
          }
        }
        env {
          name  = "REGION"
          value = var.deployment_region
        }
        env {
          name  = "PROJECT"
          value = var.project_id
        }
        secret_env {
          name = "VERTEX_CR_AUTH_TOKEN"
          secret_key_ref {
            name = google_secret_manager_secret.vertex_cr_auth_token.secret_id
            key  = "latest"
          }
        }
      }
    }

    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale" = "1"
        "autoscaling.knative.dev/maxScale" = "10"
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [google_artifact_registry_repository.default]
}

### IAM permissions for Cloud Run (public access)
data "google_iam_policy" "noauth" {
  binding {
    role = "roles/run.invoker"
    members = [
      "allUsers",
    ]
  }
}

resource "google_cloud_run_service_iam_policy" "noauth" {
  location = google_cloud_run_service.default.location
  project  = google_cloud_run_service.default.project
  service  = google_cloud_run_service.default.name

  policy_data = data.google_iam_policy.noauth.policy_data
}

output "cloud_run_uri" {
  value = google_cloud_run_service.default.status[0].url
}

output "cloud_run_data" {
  value = google_cloud_run_service.default
}
