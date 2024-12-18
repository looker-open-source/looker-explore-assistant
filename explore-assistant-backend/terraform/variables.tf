
#
# REQUIRED VARIABLES
#

variable "project_id" {
  type = string
  description = "GCP Project ID"
}

variable "use_cloud_function_backend" {
  type = bool
  default = false
}

variable "use_bigquery_backend" {
  type = bool
  default = false
}

variable "use_cloud_run_backend" {
  type = bool
  default = false
}

#
# VARIABLES WITH DEFAULTS
#

variable "deployment_region" {
  type = string
  description = "Region to deploy the Cloud Run service. Example: us-central1"
  default = "us-central1"
}

#
# CLOUD RUN VARIABLES
#

variable "cloud_run_service_name" {
    type = string
    description = "the name of cloud run service upon deployment"
    default = "explore-assistant-api"
}

variable "image_name" {
  description = "The name of the Docker image for Cloud Run. defaults to same name of service."
  type        = string
}

variable "image_tag" {
  description = "image tag to deploy; defaults to latest."
  type        = string
  default     = "latest"
}

#
# BIGQUERY VARIABLES
#

variable "dataset_id_name" {
    type = string
    default = "explore_assistant"
}

variable "connection_id" {
    type = string
    default = "explore_assistant_llm"
}

