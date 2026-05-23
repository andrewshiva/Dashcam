# Enable required APIs
resource "google_project_service" "eventarc_api" {
  project            = var.project_id
  service            = "eventarc.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "pubsub_api" {
  project            = var.project_id
  service            = "pubsub.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "workflows_api" {
  project            = var.project_id
  service            = "workflows.googleapis.com"
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

# Pub/Sub ingestion topic fed by Cloud Storage notifications.
resource "google_pubsub_topic" "gcs_upload_events" {
  name    = "${var.project_prefix}-gcs-upload-events"
  project = var.project_id

  depends_on = [google_project_service.pubsub_api]
}

# Dead Letter Queue (DLQ) for raw upload events that cannot be delivered.
resource "google_pubsub_topic" "dlq" {
  name    = "${var.project_prefix}-dlq"
  project = var.project_id

  depends_on = [google_project_service.pubsub_api]
}

resource "google_pubsub_subscription" "dlq_sub" {
  name    = "${var.project_prefix}-dlq-sub"
  topic   = google_pubsub_topic.dlq.id
  project = var.project_id
}

resource "google_pubsub_topic_iam_member" "pubsub_service_agent_dlq_publisher" {
  project = var.project_id
  topic   = google_pubsub_topic.dlq.name
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

resource "google_project_iam_member" "pubsub_service_agent_token_creator" {
  project = var.project_id
  role    = "roles/iam.serviceAccountTokenCreator"
  member  = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

resource "google_pubsub_subscription" "gcs_upload_validator" {
  name    = "${var.project_prefix}-gcs-upload-validator-sub"
  topic   = google_pubsub_topic.gcs_upload_events.id
  project = var.project_id

  ack_deadline_seconds = var.validator_ack_deadline_seconds

  push_config {
    push_endpoint = var.validator_push_endpoint

    oidc_token {
      service_account_email = var.service_account_email
      audience              = var.validator_push_endpoint
    }
  }

  retry_policy {
    minimum_backoff = var.validator_retry_minimum_backoff
    maximum_backoff = var.validator_retry_maximum_backoff
  }

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dlq.id
    max_delivery_attempts = var.dlq_max_delivery_attempts
  }

  depends_on = [
    google_project_iam_member.pubsub_service_agent_token_creator,
    google_pubsub_topic_iam_member.pubsub_service_agent_dlq_publisher,
  ]
}

resource "google_pubsub_subscription_iam_member" "pubsub_service_agent_source_subscriber" {
  project      = var.project_id
  subscription = google_pubsub_subscription.gcs_upload_validator.name
  role         = "roles/pubsub.subscriber"
  member       = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

resource "google_storage_notification" "raw_video_finalize" {
  bucket         = var.raw_video_bucket
  topic          = google_pubsub_topic.gcs_upload_events.id
  payload_format = "JSON_API_V1"
  event_types    = ["OBJECT_FINALIZE"]

  depends_on = [google_project_iam_member.storage_service_agent_pubsub_publisher]
}
