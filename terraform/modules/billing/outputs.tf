output "budget_name" {
  description = "Billing budget resource name, when a billing account is configured."
  value       = length(google_billing_budget.budget) > 0 ? google_billing_budget.budget[0].name : null
}
