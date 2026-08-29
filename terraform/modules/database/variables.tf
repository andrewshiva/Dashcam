variable "project_id" {
  description = "The ID of the project"
  type        = string
}

variable "region" {
  description = "The primary region"
  type        = string
}

variable "network_id" {
  description = "The ID of the VPC network"
  type        = string
}

variable "db_name" {
  description = "Name of the initial database"
  type        = string
  default     = "nhaidb"
}

variable "db_user" {
  description = "Cloud SQL database user"
  type        = string
  default     = "postgres"
}

variable "db_password" {
  description = "Cloud SQL database password"
  type        = string
  sensitive   = true
}
