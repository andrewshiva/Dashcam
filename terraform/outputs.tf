output "api_gateway_url" {
  description = "Default API Gateway HTTPS URL."
  value       = module.api_gateway.gateway_url
}

output "gcs_upload_subscription_name" {
  description = "Pub/Sub subscription delivering GCS upload events to the validator."
  value       = module.messaging.gcs_upload_subscription_name
}

output "dlq_subscription_name" {
  description = "Pub/Sub DLQ subscription for failed upload event deliveries."
  value       = module.messaging.dlq_subscription_name
}

output "dashboard_uptime_check_id" {
  description = "Cloud Monitoring uptime check ID for the dashboard frontend."
  value       = module.observability.dashboard_uptime_check_id
}

output "dashboard_admin_password_secret_name" {
  description = "Secret Manager secret name for the dashboard administrator password."
  value       = module.security.dashboard_admin_password_secret_name
}

output "dashboard_ro_password_secret_name" {
  description = "Secret Manager secret name for the dashboard RO user password."
  value       = module.security.dashboard_ro_password_secret_name
}

output "cloud_build_app_deploy_trigger_name" {
  description = "Cloud Build app deploy trigger name, when enabled."
  value       = module.cicd.app_deploy_trigger_name
}

output "cloud_build_terraform_validate_trigger_name" {
  description = "Cloud Build Terraform validation trigger name, when enabled."
  value       = module.cicd.terraform_validate_trigger_name
}
