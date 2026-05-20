variable "project_id" {
  type        = string
  description = "The GCP project ID"
}

variable "project_prefix" {
  type        = string
  description = "Prefix for resources"
}

variable "region" {
  type        = string
  description = "GCP region"
}

variable "raw_video_bucket" {
  type        = string
  description = "Bucket name for raw video uploads"
}

variable "service_account_email" {
  type        = string
  description = "Service account email for Eventarc trigger"
}

variable "validator_service_name" {
  type        = string
  description = "Cloud Run service name for the video validator"
  default     = "video-validator"
}
