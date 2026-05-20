# Enable required APIs
resource "google_project_service" "eventarc_api" {
  project = var.project_id
  service = "eventarc.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "pubsub_api" {
  project = var.project_id
  service = "pubsub.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "workflows_api" {
  project = var.project_id
  service = "workflows.googleapis.com"
  disable_on_destroy = false
}

data "google_project" "project" {
  project_id = var.project_id
}

resource "google_project_iam_member" "storage_service_agent_pubsub_publisher" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:service-${data.google_project.project.number}@gs-project-accounts.iam.gserviceaccount.com"

  depends_on = [google_project_service.pubsub_api]
}

# Dead Letter Queue (DLQ)
resource "google_pubsub_topic" "dlq" {
  name    = "${var.project_prefix}-dlq"
  project = var.project_id
  depends_on = [google_project_service.pubsub_api]
}

resource "google_pubsub_subscription" "dlq_sub" {
  name    = "${var.project_prefix}-dlq-sub"
  topic   = google_pubsub_topic.dlq.name
  project = var.project_id
}

# Eventarc Trigger for GCS Uploads
# Note: This requires the validation service to be deployed first,
# so we might use a placeholder or assume it's created outside of this module
# For a full IaC deployment, Cloud Run services should be managed by TF.
# We'll comment out the destination service name to prevent apply errors if the service isn't there,
# or we assume standard naming.
resource "google_eventarc_trigger" "gcs_upload" {
  name     = "${var.project_prefix}-gcs-upload"
  project  = var.project_id
  location = var.region
  
  matching_criteria {
    attribute = "type"
    value     = "google.cloud.storage.object.v1.finalized"
  }
  
  matching_criteria {
    attribute = "bucket"
    value     = var.raw_video_bucket
  }

  destination {
    cloud_run_service {
      service = var.validator_service_name
      region  = var.region
    }
  }

  service_account = var.service_account_email
  depends_on      = [google_project_service.eventarc_api, google_project_iam_member.storage_service_agent_pubsub_publisher]
}
