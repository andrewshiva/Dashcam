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
