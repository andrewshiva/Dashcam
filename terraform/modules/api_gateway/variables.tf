variable "project_id" {
  type        = string
  description = "GCP project ID."
}

variable "region" {
  type        = string
  description = "GCP region for the API Gateway."
}

variable "project_prefix" {
  type        = string
  description = "Prefix for API Gateway resources."
}

variable "dashboard_api_url" {
  type        = string
  default     = "https://dashboard-api-863438916962.asia-south1.run.app"
  description = "Target dashboard API Cloud Run service URL backend."
}

variable "read_quota_per_minute" {
  type        = number
  description = "API Gateway read quota per project per minute."
  default     = 120
}

variable "write_quota_per_minute" {
  type        = number
  description = "API Gateway write quota per project per minute."
  default     = 30
}
