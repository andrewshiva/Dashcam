resource "google_monitoring_dashboard" "system_health" {
  dashboard_json = <<EOF
{
  "displayName": "NHAI DAS System Health",
  "gridLayout": {
    "columns": "2",
    "widgets": [
      {
        "title": "Cloud Run Request Count",
        "xyChart": {
          "dataSets": [
            {
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "resource.type=\"cloud_run_revision\" metric.type=\"run.googleapis.com/request_count\"",
                  "aggregation": {
                    "perSeriesAligner": "ALIGN_RATE"
                  }
                }
              }
            }
          ]
        }
      },
      {
        "title": "Cloud Run Memory Utilization",
        "xyChart": {
          "dataSets": [
            {
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "resource.type=\"cloud_run_revision\" metric.type=\"run.googleapis.com/container/memory/utilizations\"",
                  "aggregation": {
                    "perSeriesAligner": "ALIGN_MEAN"
                  }
                }
              }
            }
          ]
        }
      },
      {
        "title": "Cloud SQL CPU Utilization",
        "xyChart": {
          "dataSets": [
            {
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "resource.type=\"cloudsql_database\" metric.type=\"cloudsql.googleapis.com/database/cpu/utilization\"",
                  "aggregation": {
                    "perSeriesAligner": "ALIGN_MEAN"
                  }
                }
              }
            }
          ]
        }
      },
      {
        "title": "Pub/Sub Undelivered Messages",
        "xyChart": {
          "dataSets": [
            {
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "resource.type=\"pubsub_subscription\" metric.type=\"pubsub.googleapis.com/subscription/num_undelivered_messages\"",
                  "aggregation": {
                    "perSeriesAligner": "ALIGN_MEAN"
                  }
                }
              }
            }
          ]
        }
      }
    ]
  }
}
EOF
}

resource "google_monitoring_notification_channel" "email" {
  display_name = "NHAI Operations Alert Email"
  type         = "email"
  labels = {
    email_address = var.alert_email
  }
}

resource "google_monitoring_alert_policy" "high_error_rate" {
  display_name = "High Error Rate Alert"
  combiner     = "OR"
  conditions {
    display_name = "Cloud Run 5xx Errors"
    condition_threshold {
      filter     = "resource.type=\"cloud_run_revision\" metric.type=\"run.googleapis.com/request_count\" metric.labels.response_code_class=\"5xx\""
      duration   = "60s"
      comparison = "COMPARISON_GT"
      threshold_value = 0.01
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }
  
  notification_channels = [google_monitoring_notification_channel.email.name]
}

resource "google_logging_metric" "pipeline_failures" {
  name        = "nhai_das_pipeline_failures"
  description = "Counts explicit NHAI DAS pipeline failure log entries."
  filter      = "textPayload:\"PIPELINE_FAILURE\" OR jsonPayload.message:\"PIPELINE_FAILURE\""

  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
    unit        = "1"
  }
}

resource "google_monitoring_alert_policy" "pipeline_failure_email" {
  display_name = "NHAI DAS Pipeline Failure"
  combiner     = "OR"

  conditions {
    display_name = "Pipeline failure log entry"

    condition_threshold {
      filter          = "metric.type=\"logging.googleapis.com/user/${google_logging_metric.pipeline_failures.name}\""
      duration        = "60s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0

      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_SUM"
        cross_series_reducer = "REDUCE_SUM"
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.name]
}

resource "google_monitoring_uptime_check_config" "dashboard_uptime" {
  display_name = "Dashboard Frontend Uptime Check"
  timeout      = "10s"
  period       = "60s"

  http_check {
    path = "/"
    port = 443
    use_ssl = true
    validate_ssl = true
  }

  monitored_resource {
    type = "uptime_url"
    labels = {
      project_id = var.project_id
      host       = var.uptime_host
    }
  }
}
