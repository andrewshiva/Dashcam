variable "billing_account_id" {
  description = "The ID of the billing account to associate with the budget."
  type        = string
}

variable "project_id" {
  description = "The ID of the project."
  type        = string
}

variable "monitoring_notification_channel_names" {
  description = "Monitoring notification channels that should receive budget updates."
  type        = list(string)
  default     = []
}
