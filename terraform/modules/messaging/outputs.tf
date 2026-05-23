output "gcs_upload_topic_name" {
  description = "Name of the Pub/Sub topic receiving Cloud Storage upload notifications"
  value       = google_pubsub_topic.gcs_upload_events.name
}

output "gcs_upload_subscription_name" {
  description = "Name of the Pub/Sub push subscription delivering uploads to the validator"
  value       = google_pubsub_subscription.gcs_upload_validator.name
}

output "dlq_topic_name" {
  description = "Name of the Dead Letter Queue topic"
  value       = google_pubsub_topic.dlq.name
}

output "dlq_subscription_name" {
  description = "Name of the Dead Letter Queue subscription"
  value       = google_pubsub_subscription.dlq_sub.name
}
