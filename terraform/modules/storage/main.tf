# Enable required APIs
resource "google_project_service" "storage_api" {
  project = var.project_id
  service = "storage.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "bigquery_api" {
  project = var.project_id
  service = "bigquery.googleapis.com"
  disable_on_destroy = false
}

# GCS Buckets
resource "google_storage_bucket" "raw_video" {
  name          = "${var.bucket_prefix}-raw-video"
  project       = var.project_id
  location      = "ASIA" # Dual-region IN is typically ASIA or IN
  force_destroy = true
  uniform_bucket_level_access = true

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }
}

resource "google_storage_bucket" "validated_video" {
  name          = "${var.bucket_prefix}-validated-video"
  project       = var.project_id
  location      = "ASIA"
  force_destroy = true
  uniform_bucket_level_access = true
}

resource "google_storage_bucket" "processed_metadata" {
  name          = "${var.bucket_prefix}-processed"
  project       = var.project_id
  location      = var.region
  force_destroy = true
  uniform_bucket_level_access = true
}

resource "google_storage_bucket" "quarantine" {
  name          = "${var.bucket_prefix}-quarantine"
  project       = var.project_id
  location      = var.region
  force_destroy = true
  uniform_bucket_level_access = true
}

# BigQuery Dataset
resource "google_bigquery_dataset" "analytics" {
  dataset_id                  = "nhai_analytics_${var.env}"
  project                     = var.project_id
  location                    = var.region
  description                 = "Dataset for NHAI dashcam analytics and reports"
  delete_contents_on_destroy  = true
}
