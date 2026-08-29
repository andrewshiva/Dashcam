locals {
  create_github_triggers = var.enable_cloud_build_triggers && trimspace(var.github_owner) != "" && trimspace(var.github_repo) != ""
}

resource "google_project_service" "cloudbuild_api" {
  project            = var.project_id
  service            = "cloudbuild.googleapis.com"
  disable_on_destroy = false
}

resource "google_cloudbuild_trigger" "app_deploy" {
  count       = local.create_github_triggers ? 1 : 0
  project     = var.project_id
  name        = "${var.project_prefix}-app-deploy"
  description = "Build, test, and deploy NHAI DAS services."
  filename    = "cloudbuild.yaml"

  github {
    owner = var.github_owner
    name  = var.github_repo
    push {
      branch = var.branch_regex
    }
  }

  included_files = [
    "cloudbuild.yaml",
    "services/**",
    "scripts/**",
    "training/*.yaml",
    "training/README.md",
  ]

  ignored_files = [
    "training/datasets/**",
    "training/external/**",
    "training/runs/**",
  ]

  depends_on = [google_project_service.cloudbuild_api]
}

resource "google_cloudbuild_trigger" "terraform_validate" {
  count       = local.create_github_triggers ? 1 : 0
  project     = var.project_id
  name        = "${var.project_prefix}-terraform-validate"
  description = "Validate Terraform formatting and configuration."
  filename    = "cloudbuild-terraform.yaml"

  github {
    owner = var.github_owner
    name  = var.github_repo
    push {
      branch = var.branch_regex
    }
  }

  included_files = [
    "cloudbuild-terraform.yaml",
    "terraform/**",
  ]

  depends_on = [google_project_service.cloudbuild_api]
}
