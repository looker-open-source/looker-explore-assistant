provider "google" {
  project = var.project_id
}

module "base-project-services" {
  count                       = var.use_bigquery_backend ? 1 : 0
  source                      = "terraform-google-modules/project-factory/google//modules/project_services"
  version                     = "14.2.1"
  disable_services_on_destroy = false

  project_id  = var.project_id
  enable_apis = true

  activate_apis = [
    "serviceusage.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
  ]
}

resource "time_sleep" "wait_after_basic_apis_activate" {
  depends_on      = [module.base-project-services]
  create_duration = "120s"
}

module "bg-backend-project-services" {
  count                       = var.use_bigquery_backend ? 1 : 0
  source                      = "terraform-google-modules/project-factory/google//modules/project_services"
  version                     = "14.2.1"
  disable_services_on_destroy = false

  project_id  = var.project_id
  enable_apis = true

  activate_apis = [
    "aiplatform.googleapis.com",
    "bigquery.googleapis.com",
  ]

  depends_on = [module.base-project-services, time_sleep.wait_after_basic_apis_activate]
}

module "cr-backend-project-services" {
  count                       = var.use_cloud_run_backend ? 1 : 0
  source                      = "terraform-google-modules/project-factory/google//modules/project_services"
  version                     = "14.2.1"
  disable_services_on_destroy = false

  project_id  = var.project_id
  enable_apis = true

  activate_apis = [
    "cloudapis.googleapis.com",
    "cloudbuild.googleapis.com",
    "run.googleapis.com",
    "storage-api.googleapis.com",
    "storage.googleapis.com",
    "compute.googleapis.com",
    "secretmanager.googleapis.com",
  ]

  depends_on = [module.base-project-services, time_sleep.wait_after_basic_apis_activate]
}


resource "time_sleep" "wait_after_apis_activate" {
  depends_on = [
    time_sleep.wait_after_basic_apis_activate,
    module.cr-backend-project-services,
    module.bg-backend-project-services
  ]
  create_duration = "120s"
}

resource "google_bigquery_dataset" "dataset" {
  dataset_id                 = var.dataset_id_name
  friendly_name              = var.dataset_id_name
  description                = "big query dataset for examples"
  location                   = var.deployment_region
  delete_contents_on_destroy = true
  depends_on                 = [time_sleep.wait_after_apis_activate]
}

module "cloud_sql" {
  count                = var.use_cloud_run_backend ? 1 : 0
  source               = "./cloud_sql"
  deployment_region    = var.deployment_region
  project_id           = var.project_id
  root_password        = var.root_password
  user_password        = var.user_password
  cloudSQL_server_name = var.cloudSQL_server_name

  depends_on = [time_sleep.wait_after_apis_activate]
}

module "cloud_run_backend" {
  count                                = var.use_cloud_run_backend ? 1 : 0
  source                               = "./cloud_run"
  project_id                           = var.project_id
  project_number                       = var.project_number
  deployment_region                    = var.deployment_region
  image                                = var.image
  cloud_run_service_name               = var.cloud_run_service_name
  explore-assistant-cr-oauth-client-id = var.explore-assistant-cr-oauth-client-id
  explore-assistant-cr-sa-id           = var.explore-assistant-cr-sa-id
  cloudSQL_server_name                 = var.cloudSQL_server_name

  depends_on = [module.cloud_sql, time_sleep.wait_after_apis_activate]
}

module "bigquery_backend" {
  count             = var.use_bigquery_backend ? 1 : 0
  source            = "./bigquery"
  project_id        = var.project_id
  deployment_region = var.deployment_region
  dataset_id        = var.dataset_id_name
  connection_id     = var.connection_id

  depends_on = [time_sleep.wait_after_apis_activate, google_bigquery_dataset.dataset]
}

output "cloud_run_uri" {
  description = "Cloud Run URI"
  value       = var.use_cloud_run_backend ? module.cloud_run_backend[0].cloud_run_uri : null
}
