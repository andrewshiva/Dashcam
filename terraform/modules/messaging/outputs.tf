output "dlq_topic_name" {
  description = "Name of the Dead Letter Queue topic"
  value       = google_pubsub_topic.dlq.name
}

output "eventarc_trigger_name" {
  description = "Name of the Eventarc trigger"
  value       = google_eventarc_trigger.gcs_upload.name
}
