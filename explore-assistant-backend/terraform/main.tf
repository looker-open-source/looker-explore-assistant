provider "google" {
  project = var.project_id
}

module "project-services" {
  source                      = "terraform-google-modules/project-factory/google//modules/project_services"
  version                     = "14.2.1"
  disable_services_on_destroy = false

  project_id  = var.project_id
  enable_apis = true

  activate_apis = [
    "cloudresourcemanager.googleapis.com", 
    "cloudapis.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudfunctions.googleapis.com",
    "run.googleapis.com",
    "iam.googleapis.com",
    "serviceusage.googleapis.com",
    "storage-api.googleapis.com",
    "storage.googleapis.com",
    "aiplatform.googleapis.com",
    "compute.googleapis.com",
    "secretmanager.googleapis.com",
  ]
}

resource "time_sleep" "wait_after_apis_activate" {
  depends_on      = [module.project-services]
  create_duration = "120s"
}

module "cloud_run_backend" {
  count = var.use_cloud_function_backend ? 1 : 0
  source = "./cloud_function"
  project_id = var.project_id
  deployment_region = var.deployment_region
  cloud_run_service_name = var.cloud_run_service_name

  depends_on = [ time_sleep.wait_after_apis_activate ]
}

module "bigquery_backend" {
  count = var.use_bigquery_backend ? 1 : 0
  source = "./bigquery"
  project_id = var.project_id
  deployment_region = var.deployment_region
  dataset_id = var.dataset_id_name

  depends_on = [ time_sleep.wait_after_apis_activate, google_bigquery_dataset.dataset]
}
