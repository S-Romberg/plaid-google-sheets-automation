terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  function_name = "plaid-webhook-handler-${var.environment}"
  bucket_name   = "${var.project_id}-function-source-${var.environment}"
  
  # Common labels for all resources
  common_labels = {
    environment = var.environment
    managed_by  = "terraform"
    project     = var.project_id
  }
}

# Enable required APIs
resource "google_project_service" "cloudfunctions" {
  service = "cloudfunctions.googleapis.com"
}

resource "google_project_service" "cloudbuild" {
  service = "cloudbuild.googleapis.com"
}

resource "google_project_service" "secretmanager" {
  service = "secretmanager.googleapis.com"
}

# Create service account for the Cloud Function
resource "google_service_account" "function_account" {
  account_id   = "plaid-webhook-${var.environment}"
  display_name = "Plaid Webhook Handler ${var.environment}"
}

# Grant necessary roles
resource "google_project_iam_member" "secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.function_account.email}"
}

resource "google_project_iam_member" "sheets_editor" {
  project = var.project_id
  role    = "roles/sheets.editor"
  member  = "serviceAccount:${google_service_account.function_account.email}"
}

# Create Cloud Function
resource "google_storage_bucket" "function_bucket" {
  name     = local.bucket_name
  location = var.region
  labels   = local.common_labels

  # Recommended settings for production
  versioning {
    enabled = var.environment == "prod" ? true : false
  }
}

resource "google_storage_bucket_object" "function_source" {
  name   = "function-source-${formatdate("YYYYMMDDhhmmss", timestamp())}.zip"
  bucket = google_storage_bucket.function_bucket.name
  source = "function-source.zip"
}

# Create secrets
resource "google_secret_manager_secret" "plaid_client_id" {
  secret_id = "plaid-client-id-${var.environment}"
  replication {}
}

resource "google_secret_manager_secret_version" "plaid_client_id" {
  secret      = google_secret_manager_secret.plaid_client_id.id
  secret_data = var.plaid_client_id
}

resource "google_secret_manager_secret" "plaid_secret" {
  secret_id = "plaid-secret-${var.environment}"
  replication {}
}

resource "google_secret_manager_secret_version" "plaid_secret" {
  secret      = google_secret_manager_secret.plaid_secret.id
  secret_data = var.plaid_secret
}

resource "google_secret_manager_secret" "spreadsheet_id" {
  secret_id = "spreadsheet-id-${var.environment}"
  replication {}
}

resource "google_secret_manager_secret_version" "spreadsheet_id" {
  secret      = google_secret_manager_secret.spreadsheet_id.id
  secret_data = var.spreadsheet_id
}

# Create secret for Plaid tokens mapping
resource "google_secret_manager_secret" "plaid_tokens" {
  secret_id = "plaid-tokens-${var.environment}"
  replication {}
}

resource "google_secret_manager_secret_version" "plaid_tokens" {
  secret      = google_secret_manager_secret.plaid_tokens.id
  secret_data = var.plaid_tokens
}

resource "google_cloudfunctions2_function" "webhook_function" {
  name        = local.function_name
  location    = var.region
  description = "Handles Plaid webhooks for transaction syncing"
  labels      = local.common_labels

  build_config {
    runtime     = "python310"
    entry_point = "webhook_handler"
    source {
      storage_source {
        bucket = google_storage_bucket.function_bucket.name
        object = google_storage_bucket_object.function_source.name
      }
    }
    environment_variables = {
      PLAID_ENV        = var.plaid_env
      PLAID_CLIENT_ID_SECRET  = google_secret_manager_secret.plaid_client_id.name
      PLAID_SECRET_SECRET     = google_secret_manager_secret.plaid_secret.name
      SPREADSHEET_ID_SECRET   = google_secret_manager_secret.spreadsheet_id.name
      PLAID_TOKENS_SECRET     = google_secret_manager_secret.plaid_tokens.name
    }
  }

  service_config {
    max_instance_count    = var.environment == "prod" ? 3 : 1
    available_memory      = var.environment == "prod" ? "512M" : "256M"
    timeout_seconds       = 60
    service_account_email = google_service_account.function_account.email
  }
}

# Outputs
output "function_url" {
  value       = google_cloudfunctions2_function.webhook_function.service_config[0].uri
  description = "The URL of the deployed Cloud Function"
}

output "function_name" {
  value       = google_cloudfunctions2_function.webhook_function.name
  description = "The name of the deployed Cloud Function"
}

output "service_account_email" {
  value       = google_service_account.function_account.email
  description = "The service account email used by the Cloud Function"
}