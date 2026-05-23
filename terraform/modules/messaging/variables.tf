variable "project_id" {
  type        = string
  description = "The GCP project ID"
}

variable "project_prefix" {
  type        = string
  description = "Prefix for resources"
}

variable "raw_video_bucket" {
  type        = string
  description = "Bucket name for raw video uploads"
}

variable "service_account_email" {
  type        = string
  description = "Service account email used for authenticated Pub/Sub push delivery"
}

variable "validator_push_endpoint" {
  type        = string
  description = "HTTPS endpoint for the video-validator Cloud Run service Pub/Sub push subscription"
}

variable "validator_ack_deadline_seconds" {
  type        = number
  description = "Pub/Sub ack deadline for validator push deliveries"
  default     = 60
}

variable "validator_retry_minimum_backoff" {
  type        = string
  description = "Minimum retry backoff for validator push delivery failures"
  default     = "10s"
}

variable "validator_retry_maximum_backoff" {
  type        = string
  description = "Maximum retry backoff for validator push delivery failures"
  default     = "600s"
}

variable "dlq_max_delivery_attempts" {
  type        = number
  description = "Maximum validator delivery attempts before Pub/Sub forwards the event to the DLQ"
  default     = 5

  validation {
    condition     = var.dlq_max_delivery_attempts >= 5 && var.dlq_max_delivery_attempts <= 100
    error_message = "dlq_max_delivery_attempts must be between 5 and 100."
  }
}
