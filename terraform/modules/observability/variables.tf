variable "project_id" {}
variable "region" {}

variable "alert_email" {
  type        = string
  description = "Email address for monitoring notifications"
}

variable "uptime_host" {
  type        = string
  default     = "dashboard-frontend-863438916962.asia-south1.run.app"
  description = "The target hostname for the frontend dashboard monitoring."
}
