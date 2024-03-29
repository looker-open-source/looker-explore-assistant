
variable "cloud_run_service_name" {
    type = string
}

variable "deployment_region" {
    type = string
}

variable "project_id" {
    type = string
}

variable "docker_image" {
    type = string
}

resource "google_cloud_run_v2_service" "default" {
  name     = var.cloud_run_service_name
  location = var.deployment_region
  ingress = "INGRESS_TRAFFIC_ALL"

  template {
    scaling {
        max_instance_count = 20
        min_instance_count = 1
    }
    timeout = "300s"
    max_instance_request_concurrency = 200

    containers {
        image = var.docker_image

        env {
            name  = "project"
            value = var.project_id
        }
        env {
            name  = "region"
            value = var.deployment_region
        }

        resources {
            limits = {
                cpu = 2
                memory = "2000Mi"
            }
        }
    }
  }
}

# Return service URL
output "url" {
  value = "${google_cloud_run_v2_service.default.uri}"
}