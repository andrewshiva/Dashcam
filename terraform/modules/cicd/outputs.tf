output "app_deploy_trigger_name" {
  description = "Cloud Build app deploy trigger name, when enabled."
  value       = length(google_cloudbuild_trigger.app_deploy) > 0 ? google_cloudbuild_trigger.app_deploy[0].name : null
}

output "terraform_validate_trigger_name" {
  description = "Cloud Build Terraform validation trigger name, when enabled."
  value       = length(google_cloudbuild_trigger.terraform_validate) > 0 ? google_cloudbuild_trigger.terraform_validate[0].name : null
}
