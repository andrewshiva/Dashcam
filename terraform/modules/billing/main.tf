resource "google_project_service" "billing_budgets_api" {
  project            = var.project_id
  service            = "billingbudgets.googleapis.com"
  disable_on_destroy = false
}

resource "google_billing_budget" "budget" {
  count           = var.billing_account_id == "" ? 0 : 1
  billing_account = var.billing_account_id
  display_name    = "NHAI DAS Budget"

  budget_filter {
    projects = ["projects/${var.project_id}"]
  }

  amount {
    specified_amount {
      currency_code = "USD"
      units         = "100"
    }
  }

  threshold_rules {
    threshold_percent = 0.5
  }
  threshold_rules {
    threshold_percent = 0.9
  }
  threshold_rules {
    threshold_percent = 1.0
    spend_basis       = "FORECASTED_SPEND"
  }

  dynamic "all_updates_rule" {
    for_each = length(var.monitoring_notification_channel_names) > 0 ? [1] : []
    content {
      monitoring_notification_channels = var.monitoring_notification_channel_names
      disable_default_iam_recipients   = false
    }
  }

  depends_on = [google_project_service.billing_budgets_api]
}
