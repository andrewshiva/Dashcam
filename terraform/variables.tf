variable "project_id" {
  description = "The ID of the GCP project to deploy resources into"
  type        = string
}

variable "region" {
  description = "The primary region for resources"
  type        = string
  default     = "asia-south1"
}

variable "zone" {
  description = "The primary zone for resources"
  type        = string
  default     = "asia-south1-a"
}

variable "env" {
  description = "Environment (dev, uat, prod)"
  type        = string
  default     = "dev"
}

variable "billing_account_id" {
  description = "The ID of the billing account"
  type        = string
  default     = ""
}

variable "alert_email" {
  description = "Email address for Cloud Monitoring alerts"
  type        = string
  default     = "andrewshiva886@gmail.com"
}

variable "validator_push_endpoint" {
  description = "HTTPS endpoint for the video-validator Cloud Run service Pub/Sub push subscription"
  type        = string
  default     = "https://video-validator-863438916962.asia-south1.run.app/"
}

variable "dashboard_api_url" {
  description = "HTTPS URL for the dashboard-api Cloud Run service used by API Gateway."
  type        = string
  default     = "https://dashboard-api-863438916962.asia-south1.run.app"
}

variable "dashboard_frontend_host" {
  description = "Hostname for the dashboard frontend uptime check."
  type        = string
  default     = "dashboard-frontend-863438916962.asia-south1.run.app"
}

variable "api_gateway_read_quota_per_minute" {
  description = "API Gateway read quota per project per minute."
  type        = number
  default     = 120
}

variable "api_gateway_write_quota_per_minute" {
  description = "API Gateway write quota per project per minute."
  type        = number
  default     = 30
}

variable "enable_cloud_build_triggers" {
  description = "Create GitHub-backed Cloud Build triggers when github_owner and github_repo are also provided."
  type        = bool
  default     = false
}

variable "github_owner" {
  description = "GitHub organization or user that owns this repository for Cloud Build triggers."
  type        = string
  default     = ""
}

variable "github_repo" {
  description = "GitHub repository name for Cloud Build triggers."
  type        = string
  default     = ""
}

variable "cloud_build_branch_regex" {
  description = "Branch regex for Cloud Build trigger push events."
  type        = string
  default     = "^main$"
}
