variable "project_id" {
  description = "The ID of the networking project"
  type        = string
}

variable "region" {
  description = "The primary region"
  type        = string
}

variable "network_name" {
  description = "The name of the shared VPC network"
  type        = string
  default     = "nhai-das-shared-vpc"
}

variable "connector_name" {
  description = "The name of the Serverless VPC Access connector"
  type        = string
  default     = "nhai-das-vpc-connector"
}
