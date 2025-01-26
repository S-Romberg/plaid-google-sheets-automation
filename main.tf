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
  account_id   = "plaid-webhook-handler"
  display_name = "Plaid Webhook Handler"
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
  name     = "${var.project_id}-function-source"
  location = var.region
}

resource "google_storage_bucket_object" "function_source" {
  name   = "function-source.zip"
  bucket = google_storage_bucket.function_bucket.name
  source = "function-source.zip"  # You'll need to create this zip file
}

resource "google_cloudfunctions2_function" "webhook_function" {
  name        = "plaid-webhook-handler"
  location    = var.region
  description = "Handles Plaid webhooks for transaction syncing"

  build_config {
    runtime     = "python310"
    entry_point = "webhook_handler"
    source {
      storage_source {
        bucket = google_storage_bucket.function_bucket.name
        object = google_storage_bucket_object.function_source.name
      }
    }
  }

  service_config {
    max_instance_count = 1
    available_memory   = "256M"
    timeout_seconds    = 60
    service_account_email = google_service_account.function_account.email
  }
}

# Output the function URL
output "function_url" {
  value = google_cloudfunctions2_function.webhook_function.service_config[0].uri
}