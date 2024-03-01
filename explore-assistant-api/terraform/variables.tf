variable "project_id" {
  type = string
  default = "YOUR GCP PROJECT"
}

variable "deployment_region" {
  type = string
  default = "GCP DEPLOYMENT REGION"
}

variable "docker_image" {
    type = string
    default = ""
}

variable "cloud_run_service_name" {
    type = string
    default = "explore-assistant-api"
}