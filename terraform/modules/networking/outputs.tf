output "network_id" {
  value       = google_compute_network.shared_vpc.id
  description = "The ID of the shared VPC network"
}

output "network_name" {
  value       = google_compute_network.shared_vpc.name
  description = "The name of the shared VPC network"
}

output "vpc_connector_name" {
  value       = google_vpc_access_connector.serverless.name
  description = "The name of the Serverless VPC Access connector"
}
