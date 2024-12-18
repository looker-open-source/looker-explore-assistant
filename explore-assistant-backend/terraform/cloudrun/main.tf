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

variable "image_name" {
  description = "The name of the Docker image for Cloud Run"
  type        = string
}

variable "image_tag" {
  description = "image tag to deploy; defaults to latest."
  type        = string
  default     = "latest"
}



resource "google_service_account" "explore_assistant_sa" {
  # account_id   = "explore-assistant-cf-sa-kendev"  # FOR LOCAL DEV
  account_id   = "explore-assistant-cf-sa"

  display_name = "Looker Explore Assistant Cloud Run SA"
}

resource "google_project_iam_member" "iam_permission_looker_aiplatform" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = format("serviceAccount:%s", google_service_account.explore_assistant_sa.email)
}

# resource "google_project_iam_member" "cloud_run_sa_act_as" {
#   project = var.project_id
#   role    = "roles/iam.serviceAccountUser"
#   member  = format("serviceAccount:%s", google_service_account.explore_assistant_sa.email)
# }


resource "google_secret_manager_secret" "vertex_cf_auth_token" {
  project   = var.project_id
  # secret_id = "VERTEX_CF_AUTH_TOKEN-kendev" # # FOR LOCAL DEV
  secret_id = "VERTEX_CF_AUTH_TOKEN" 
  replication {
    user_managed {
      replicas {
        location = var.deployment_region
      }
    }
  }
}

locals {
  auth_token_file_path    = "${path.module}/../../../.vertex_cf_auth_token"
  auth_token_file_exists  = fileexists(local.auth_token_file_path)
  auth_token_file_content = local.auth_token_file_exists ? file(local.auth_token_file_path) : ""
}

resource "google_secret_manager_secret_version" "vertex_cf_auth_token_version" {
  count       = local.auth_token_file_exists ? 1 : 0
  secret      = google_secret_manager_secret.vertex_cf_auth_token.name
  secret_data = local.auth_token_file_content
}

resource "google_secret_manager_secret_iam_binding" "vertex_cf_auth_token_accessor" {
  secret_id = google_secret_manager_secret.vertex_cf_auth_token.secret_id
  role      = "roles/secretmanager.secretAccessor"
  members = [
    "serviceAccount:${google_service_account.explore_assistant_sa.email}",
  ]
}


resource "google_cloud_run_service" "default" {
  name     = var.cloud_run_service_name
  location = var.deployment_region
  project  = var.project_id

  template {
    spec {
      containers {
        image = "gcr.io/${var.project_id}/${var.image_name}:${var.image_tag}"
        resources {
          limits = {
            memory = "4Gi"
            cpu    = "1000m"
          }
        }
        env {
          name = "VERTEX_CF_AUTH_TOKEN" # The name of the environment variable in the container
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.vertex_cf_auth_token.secret_id
              key  = "latest" # Fetches the latest version of the secret
            }
          }
        }
      }
    }

    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale" = "0"
        "autoscaling.knative.dev/maxScale" = "10"
      }
    }
  }



  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [google_secret_manager_secret.vertex_cf_auth_token]

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
