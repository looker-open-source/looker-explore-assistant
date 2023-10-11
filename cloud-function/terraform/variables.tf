variable "project_id" {
  type = string
  default = "looker-private-demo"
}

variable "deployment_region" {
  type = list(string)
  default = ["us-central1"]
}