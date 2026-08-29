output "notification_channel_name" {
  description = "Monitoring notification channel resource name."
  value       = google_monitoring_notification_channel.email.name
}

output "dashboard_uptime_check_id" {
  description = "Cloud Monitoring uptime check ID for the dashboard frontend."
  value       = google_monitoring_uptime_check_config.dashboard_uptime.uptime_check_id
}
