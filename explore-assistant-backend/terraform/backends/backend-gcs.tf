terraform {
  backend "gcs" {
    bucket = "project-id-terraform-state"
    prefix  = "terraform/state"
  }
}
