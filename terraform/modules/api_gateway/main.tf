resource "google_project_service" "api_gateway" {
  project            = var.project_id
  service            = "apigateway.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "service_management" {
  project            = var.project_id
  service            = "servicemanagement.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "service_control" {
  project            = var.project_id
  service            = "servicecontrol.googleapis.com"
  disable_on_destroy = false
}

data "google_project" "project" {
  project_id = var.project_id
}

resource "google_project_iam_member" "gateway_run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-apigateway.iam.gserviceaccount.com"

  depends_on = [google_project_service.api_gateway]
}

resource "google_api_gateway_api" "dashboard_api" {
  provider = google-beta
  project  = var.project_id
  api_id   = "${var.project_prefix}-api"

  depends_on = [
    google_project_service.api_gateway,
    google_project_service.service_management,
    google_project_service.service_control,
  ]
}

resource "google_api_gateway_api_config" "dashboard_api_config" {
  provider             = google-beta
  project              = var.project_id
  api                  = google_api_gateway_api.dashboard_api.api_id
  api_config_id_prefix = "${var.project_prefix}-config-"

  openapi_documents {
    document {
      path = "spec.yaml"
      contents = base64encode(<<EOF
swagger: "2.0"
info:
  title: "NHAI DAS Dashboard API"
  description: "API Gateway for NHAI DAS Dashboard API"
  version: "1.0.0"
schemes:
  - "https"
consumes:
  - "application/json"
produces:
  - "application/json"
securityDefinitions:
  api_key:
    type: "apiKey"
    name: "x-api-key"
    in: "header"
x-google-management:
  metrics:
    - name: "dashboard-read-requests"
      displayName: "Dashboard read requests"
      valueType: INT64
      metricKind: DELTA
    - name: "dashboard-write-requests"
      displayName: "Dashboard write requests"
      valueType: INT64
      metricKind: DELTA
  quota:
    limits:
      - name: "dashboard-read-minute-limit"
        metric: "dashboard-read-requests"
        unit: "1/min/{project}"
        values:
          STANDARD: ${var.read_quota_per_minute}
      - name: "dashboard-write-minute-limit"
        metric: "dashboard-write-requests"
        unit: "1/min/{project}"
        values:
          STANDARD: ${var.write_quota_per_minute}
paths:
  /api/v1/defects:
    get:
      summary: "Get all defects"
      operationId: "getDefects"
      security:
        - api_key: []
      x-google-quota:
        metricCosts:
          dashboard-read-requests: 1
      x-google-backend:
        address: "${var.dashboard_api_url}"
      responses:
        200:
          description: "A successful response"
  /api/v1/defects/{defect_id}/image:
    get:
      summary: "Get defect evidence image"
      operationId: "getDefectImage"
      security:
        - api_key: []
      parameters:
        - name: "defect_id"
          in: "path"
          required: true
          type: "string"
      x-google-quota:
        metricCosts:
          dashboard-read-requests: 1
      x-google-backend:
        address: "${var.dashboard_api_url}"
      produces:
        - "image/jpeg"
      responses:
        200:
          description: "JPEG evidence image"
  /api/v1/upload:
    post:
      summary: "Upload video through the API"
      operationId: "uploadVideo"
      security:
        - api_key: []
      x-google-quota:
        metricCosts:
          dashboard-write-requests: 1
      x-google-backend:
        address: "${var.dashboard_api_url}"
      responses:
        200:
          description: "Upload accepted"
  /api/v1/generate-upload-url:
    post:
      summary: "Generate a direct GCS upload URL"
      operationId: "generateUploadUrl"
      security:
        - api_key: []
      x-google-quota:
        metricCosts:
          dashboard-write-requests: 1
      x-google-backend:
        address: "${var.dashboard_api_url}"
      responses:
        200:
          description: "Signed upload URL generated"
  /api/v1/confirm-upload:
    post:
      summary: "Confirm direct GCS upload"
      operationId: "confirmUpload"
      security:
        - api_key: []
      x-google-quota:
        metricCosts:
          dashboard-write-requests: 1
      x-google-backend:
        address: "${var.dashboard_api_url}"
      responses:
        200:
          description: "Upload confirmed"
  /api/v1/pipeline-status/{execution_id}:
    get:
      summary: "Get pipeline status"
      operationId: "getPipelineStatus"
      security:
        - api_key: []
      parameters:
        - name: "execution_id"
          in: "path"
          required: true
          type: "string"
      x-google-quota:
        metricCosts:
          dashboard-read-requests: 1
      x-google-backend:
        address: "${var.dashboard_api_url}"
      responses:
        200:
          description: "Pipeline status"
  /health:
    get:
      summary: "Health check"
      operationId: "healthCheck"
      security: []
      x-google-backend:
        address: "${var.dashboard_api_url}"
      responses:
        200:
          description: "Healthy"
EOF
      )
    }
  }

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [
    google_project_iam_member.gateway_run_invoker,
  ]
}

resource "google_api_gateway_gateway" "dashboard_gateway" {
  provider   = google-beta
  project    = var.project_id
  api_config = google_api_gateway_api_config.dashboard_api_config.id
  gateway_id = "${var.project_prefix}-gateway"
  region     = var.region
}
