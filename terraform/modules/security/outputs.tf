output "cloud_run_sa_email" {
  description = "Service account email for Cloud Run workload identity"
  value       = google_service_account.cloud_run_sa.email
}

output "db_password_secret_id" {
  description = "Secret ID for the database password"
  value       = google_secret_manager_secret.db_password.id
}

output "db_password_secret_name" {
  description = "Secret name for Cloud Run --set-secrets"
  value       = google_secret_manager_secret.db_password.secret_id
}

output "db_password" {
  description = "Generated database password"
  value       = random_password.db_password.result
  sensitive   = true
}

output "dashboard_admin_password_secret_name" {
  description = "Secret name for the dashboard administrator password"
  value       = google_secret_manager_secret.dashboard_admin_password.secret_id
}

output "dashboard_ro_password_secret_name" {
  description = "Secret name for the dashboard RO user password"
  value       = google_secret_manager_secret.dashboard_ro_password.secret_id
}
