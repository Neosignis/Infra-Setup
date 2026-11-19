output "bucket_names" {
  value = local.buckets
}
output "kms_key_arns" {
  value = { for name, key in aws_kms_key.storage : name => key.arn }
}
output "access_policy_arns" {
  value = { for name, policy in aws_iam_policy.access : name => policy.arn }
}
output "budget_alerts_configured" {
  value = var.budget_alert_email != ""
}
output "access_requires_role_attachment" {
  value = true
}
