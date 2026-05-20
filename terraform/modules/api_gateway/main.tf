resource "google_api_gateway_api" "dashboard_api" {
  provider = google-beta
  api_id   = "${var.project_prefix}-api"
}

resource "google_api_gateway_api_config" "dashboard_api_config" {
  provider      = google-beta
  api           = google_api_gateway_api.dashboard_api.api_id
  api_config_id = "${var.project_prefix}-config"

  openapi_documents {
    document {
      path     = "spec.yaml"
      contents = base64encode(<<EOF
swagger: "2.0"
info:
  title: "NHAI DAS Dashboard API"
  description: "API Gateway for NHAI DAS Dashboard"
  version: "1.0.0"
schemes:
  - "https"
paths:
  /api/v1/defects:
    get:
      summary: "Get all defects"
      operationId: "getDefects"
      x-google-backend:
        address: "${var.dashboard_api_url}"
      responses:
        200:
          description: "A successful response"
EOF
      )
    }
  }
}

resource "google_api_gateway_gateway" "dashboard_gateway" {
  provider   = google-beta
  api_config = google_api_gateway_api_config.dashboard_api_config.id
  gateway_id = "${var.project_prefix}-gateway"
  region     = var.region
}

variable "project_id" {}
variable "region" {}
variable "project_prefix" {}
variable "dashboard_api_url" {
  type        = string
  default     = "https://dashboard-api-863438916962.asia-south1.run.app"
  description = "The target dashboard API Cloud Run service URL backend."
}
