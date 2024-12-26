terraform {
  backend "gcs" {
    bucket = "${TF_VAR_project_id}-terraform-state"
    prefix  = "terraform/state"
  }
}