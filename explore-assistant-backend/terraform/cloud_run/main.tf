variable "cloud_run_service_name" {
  type        = string
  description = "the name of cloud run service upon deployment"
  default     = "explore-assistant-api"
}

variable "deployment_region" {
  type        = string
  description = "Region to deploy the Cloud Run service. Example: us-central1"
  default     = "us-southeast1"
}

variable "project_id" {
  type = string
}

variable "project_number" {
  type = number
}

variable "looker_client_id" {
  type = string
}

variable "looker_client_secret" {
  type = string
}

variable "looker_api_url" {
  type = string
}
variable "image" {
  description = "The full path to image on your Google artifacts repo"
  type        = string
}

variable "explore-assistant-cr-oauth-client-id" {
  type        = string
  description = "GCP Client ID for cloud run to perform oauth verifications."
}

variable "explore-assistant-cr-sa-id" {
  type = string
  description = "service account for cloud run to use & make vertexai requests."
}

variable "cloudSQL_server_name" {
  type = string
  description = "prefix the cloud run use to source cloud sql secrets for db connection"
}

resource "google_service_account" "explore_assistant_sa" {
  account_id   = var.explore-assistant-cr-sa-id
  display_name = "Looker Explore Assistant Cloud Run SA"
}

resource "google_project_iam_member" "iam_permission_looker_aiplatform" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = format("serviceAccount:%s", google_service_account.explore_assistant_sa.email)
}
resource "google_project_iam_member" "iam_permission_bq_user" {
  project = var.project_id
  role    = "roles/bigquery.user"
  member  = format("serviceAccount:%s", google_service_account.explore_assistant_sa.email)
}
resource "google_project_iam_member" "iam_permission_bq_data_editor" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = format("serviceAccount:%s", google_service_account.explore_assistant_sa.email)
}
resource "google_project_iam_member" "default" {
  project = var.project_id
  role      = "roles/secretmanager.secretAccessor"
  member  = format("serviceAccount:%s", google_service_account.explore_assistant_sa.email)
}

resource "google_cloud_run_v2_service" "default" {
  name     = var.cloud_run_service_name
  location = var.deployment_region
  project  = var.project_id

  template {
    annotations = {
        "autoscaling.knative.dev/minScale" = "0"
        "autoscaling.knative.dev/maxScale" = "10"
      }
    containers {
      image = "${var.image}"
      resources {
        limits = {
          memory = "4Gi"
          cpu    = "1000m"
        }
      }
      env {
        name = "admin_token"
        value_source {
          secret_key_ref {
            secret  = "projects/${var.project_number}/secrets/looker-explore-assistant-admin-token"
            version = "latest"
          }
        }
      }
      env {
        name = "CLOUD_SQL_HOST"
        value_source {
          secret_key_ref {
            secret  = format("projects/${var.project_number}/secrets/looker-genai-cloud-sql-host-%s",var.cloudSQL_server_name)
            version = "latest"
          }
        }
      }
      env {
        name = "CLOUD_SQL_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = format("projects/${var.project_number}/secrets/looker-genai-cloud-sql-password-%s",var.cloudSQL_server_name)
            version = "latest"
          }
        }
      }
      env {
        name = "CLOUD_SQL_DATABASE"
        value_source {
          secret_key_ref {
            secret  = format("projects/${var.project_number}/secrets/looker-genai-cloud-sql-database-%s",var.cloudSQL_server_name)
            version = "latest"
          }
        }
      }
      env {
        name = "CLOUD_SQL_USER"
        value_source {
          secret_key_ref {
            secret  = format("projects/${var.project_number}/secrets/looker-genai-cloud-sql-user-%s",var.cloudSQL_server_name)
            version = "latest"
          }
        }
      }
      ports {
        container_port = 8080
      }
      env {
        name  = "OAUTH_CLIENT_ID"
        value = var.explore-assistant-cr-oauth-client-id
      }
      env {
        name  = "REGION_NAME"
        value = var.deployment_region
      }
      env {
        name  = "PROJECT_NAME"
        value = var.project_id
      }
      env {
        name  = "LOOKER_CLIENT_ID"
        value = var.looker_client_id
      }
      env {
        name  = "LOOKER_CLIENT_SECRET"
        value = var.looker_client_secret
      }
      env {
        name  = "LOOKER_API_URL"
        value = var.looker_api_url
      }
    }
    service_account = google_service_account.explore_assistant_sa.email
  }
  traffic {
    percent         = 100
    type = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
  }
  depends_on = [ google_service_account.explore_assistant_sa ]
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
  location = google_cloud_run_v2_service.default.location
  project  = google_cloud_run_v2_service.default.project
  service  = google_cloud_run_v2_service.default.name

  policy_data = data.google_iam_policy.noauth.policy_data
}

output "cloud_run_uri" {
  value = google_cloud_run_v2_service.default.uri
}

output "cloud_run_data" {
  value = google_cloud_run_v2_service.default
}
