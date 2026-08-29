output "api_id" {
  description = "API Gateway API ID."
  value       = google_api_gateway_api.dashboard_api.api_id
}

output "gateway_id" {
  description = "API Gateway gateway ID."
  value       = google_api_gateway_gateway.dashboard_gateway.gateway_id
}

output "gateway_default_hostname" {
  description = "Default hostname assigned to the API Gateway."
  value       = google_api_gateway_gateway.dashboard_gateway.default_hostname
}

output "gateway_url" {
  description = "Default HTTPS URL for the API Gateway."
  value       = "https://${google_api_gateway_gateway.dashboard_gateway.default_hostname}"
}
