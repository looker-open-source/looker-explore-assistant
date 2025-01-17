
resource "google_sql_database_instance" "main" {
  database_version     = "MYSQL_8_0_31"
  deletion_protection  = true
  encryption_key_name  = null
  instance_type        = "CLOUD_SQL_INSTANCE"
  maintenance_version  = "MYSQL_8_0_31.R20241208.01_00"
  master_instance_name = null
  name                 = "beck-test-instance"
  project              = "joon-sandbox"
  region               = "asia-southeast1"
  root_password        = null # sensitive
  settings {
    activation_policy           = "ALWAYS"
    availability_type           = "ZONAL"
    collation                   = null
    connector_enforcement       = "NOT_REQUIRED"
    deletion_protection_enabled = true
    disk_autoresize             = true
    disk_autoresize_limit       = 0
    disk_size                   = 10
    disk_type                   = "PD_SSD"
    edition                     = "ENTERPRISE"
    pricing_plan                = "PER_USE"
    tier                        = "db-custom-2-8192"
    time_zone                   = null
    user_labels                 = {}
    backup_configuration {
      binary_log_enabled             = true
      enabled                        = true
      location                       = "asia"
      point_in_time_recovery_enabled = false
      start_time                     = "05:00"
      transaction_log_retention_days = 7
      backup_retention_settings {
        retained_backups = 7
        retention_unit   = "COUNT"
      }
    }
    insights_config {
      query_insights_enabled  = false
      query_plans_per_minute  = 0
      query_string_length     = 0
      record_application_tags = false
      record_client_address   = false
    }
    ip_configuration {
      allocated_ip_range                            = null
      enable_private_path_for_google_cloud_services = false
      ipv4_enabled                                  = true
      private_network                               = null
      require_ssl                                   = false
      authorized_networks {
        expiration_time = null
        name            = null
        value           = "0.0.0.0/0"
      }
    }
    location_preference {
      follow_gae_application = null
      secondary_zone         = null
      zone                   = "asia-southeast1-c"
    }
    maintenance_window {
      day          = 0
      hour         = 0
      update_track = "canary"
    }
    password_validation_policy {
      complexity                  = "COMPLEXITY_DEFAULT"
      disallow_username_substring = false
      enable_password_policy      = true
      min_length                  = 0
      password_change_interval    = null
      reuse_interval              = 0
    }
  }
  timeouts {
    create = null
    delete = null
    update = null
  }
}


# Create production database
resource "google_sql_database" "production" {
  name     = "production"
  instance = google_sql_database_instance.main.name
}

// Create cloud sql user
resource "google_sql_user" "cloud_sql_user" {
  name     = "cloud_sql_user"
  instance = google_sql_database_instance.main.name
  password = "password"
}