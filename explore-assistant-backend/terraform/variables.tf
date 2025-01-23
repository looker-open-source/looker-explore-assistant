
#
# REQUIRED VARIABLES
#

variable "project_id" {
  type        = string
  description = "GCP Project ID"
}

variable "use_cloud_function_backend" {
  type    = bool
  default = false
}

variable "use_bigquery_backend" {
  type    = bool
  default = false
}

variable "use_cloud_run_backend" {
  type    = bool
  default = false
}

#
# VARIABLES WITH DEFAULTS
#

variable "deployment_region" {
  type        = string
  description = "Region to deploy the Cloud Run service. Example: us-central1"
  default     = "us-central1"
}

#
# CLOUD RUN VARIABLES
#

variable "cloud_run_service_name" {
  type        = string
  description = "the name of cloud run service upon deployment"
  default     = "explore-assistant-api"
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
  type        = string
  description = "service account for cloud run to use & make vertexai requests."
}



#
# BIGQUERY VARIABLES
#

variable "dataset_id_name" {
  type    = string
  default = "explore_assistant"
}

variable "connection_id" {
  type    = string
  default = "explore_assistant_llm"
}

