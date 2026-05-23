variable "project_id" {
  type        = string
  description = "GCP project ID."
}

variable "project_prefix" {
  type        = string
  description = "Prefix for CI/CD resources."
}

variable "enable_cloud_build_triggers" {
  type        = bool
  description = "Create GitHub-backed Cloud Build triggers when repository details are provided."
  default     = false
}

variable "github_owner" {
  type        = string
  description = "GitHub organization or user that owns the repository."
  default     = ""
}

variable "github_repo" {
  type        = string
  description = "GitHub repository name."
  default     = ""
}

variable "branch_regex" {
  type        = string
  description = "Branch regex for Cloud Build trigger push events."
  default     = "^main$"
}
