variable "project_id" {
  description = "The ID of the storage project"
  type        = string
}

variable "region" {
  description = "The primary region"
  type        = string
}

variable "env" {
  description = "Environment name"
  type        = string
}

variable "bucket_prefix" {
  description = "Prefix for bucket names"
  type        = string
}
