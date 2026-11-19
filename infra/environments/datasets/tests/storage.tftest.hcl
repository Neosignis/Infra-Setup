mock_provider "aws" {
  mock_data "aws_caller_identity" {
    defaults = { account_id = "324793866495" }
  }
  mock_resource "aws_s3_bucket" {
    defaults = { arn = "arn:aws:s3:::fixture" }
  }
  mock_resource "aws_kms_key" {
    defaults = { arn = "arn:aws:kms:us-east-1:324793866495:key/11111111-1111-1111-1111-111111111111" }
  }
}

variables {
  expected_account_id = "324793866495"
}

override_resource {
  target = aws_s3_bucket.storage["datasets"]
  values = { arn = "arn:aws:s3:::neosignis-datasets-fixture" }
}
override_resource {
  target = aws_s3_bucket.storage["rights"]
  values = { arn = "arn:aws:s3:::neosignis-rights-fixture" }
}
override_resource {
  target = aws_kms_key.storage["datasets"]
  values = { arn = "arn:aws:kms:us-east-1:324793866495:key/11111111-1111-1111-1111-111111111111" }
}
override_resource {
  target = aws_kms_key.storage["rights"]
  values = { arn = "arn:aws:kms:us-east-1:324793866495:key/22222222-2222-2222-2222-222222222222" }
}

run "private_durable_storage" {
  command = apply
  assert {
    condition     = alltrue([for b in aws_s3_bucket_public_access_block.storage : b.block_public_acls && b.block_public_policy && b.ignore_public_acls && b.restrict_public_buckets])
    error_message = "Both dataset and identity/rights buckets must block public access."
  }
  assert {
    condition     = alltrue([for b in aws_s3_bucket_versioning.storage : b.versioning_configuration[0].status == "Enabled"])
    error_message = "Both buckets must preserve object versions."
  }
  assert {
    condition     = alltrue(flatten([for b in aws_s3_bucket_lifecycle_configuration.storage : [for r in b.rule : length(r.expiration) == 0 && length(r.noncurrent_version_expiration) == 0]]))
    error_message = "Completed dataset and rights records must not expire automatically."
  }
  assert {
    condition     = alltrue([for name, b in aws_s3_bucket_server_side_encryption_configuration.storage : one(b.rule).apply_server_side_encryption_by_default[0].sse_algorithm == "aws:kms" && one(b.rule).apply_server_side_encryption_by_default[0].kms_master_key_id == aws_kms_key.storage[name].arn]) && aws_kms_key.storage["datasets"].arn != aws_kms_key.storage["rights"].arn
    error_message = "Datasets and rights must have customer-managed encryption keys."
  }
  assert {
    condition     = alltrue([for b in aws_s3_bucket_policy.storage : jsondecode(b.policy).Statement[0].Condition.Bool["aws:SecureTransport"] == "false"])
    error_message = "Both buckets must reject plaintext transport."
  }
}

run "training_cannot_read_incoming_or_rights" {
  command = apply
  assert {
    condition     = jsondecode(aws_iam_policy.access["trainer"].policy).Statement[0].Resource == ["${aws_s3_bucket.storage["datasets"].arn}/approved/*"] && jsondecode(aws_iam_policy.access["trainer"].policy).Statement[0].Action == ["s3:GetObject", "s3:GetObjectVersion"]
    error_message = "Training policy must be read-only and limited to approved releases."
  }
  assert {
    condition     = jsondecode(aws_iam_policy.access["trainer"].policy).Statement[1].Condition.StringLike["s3:prefix"] == ["approved/*"] && jsondecode(aws_iam_policy.access["trainer"].policy).Statement[2].Resource == [aws_kms_key.storage["datasets"].arn]
    error_message = "Training list/decrypt permissions must stay within the dataset key and approved prefix."
  }
}

run "intake_is_write_only" {
  command = apply
  assert {
    condition     = length(jsondecode(aws_iam_policy.access["intake"].policy).Statement) == 2 && jsondecode(aws_iam_policy.access["intake"].policy).Statement[0].Action == ["s3:PutObject", "s3:AbortMultipartUpload"] && jsondecode(aws_iam_policy.access["intake"].policy).Statement[0].Resource == ["${aws_s3_bucket.storage["datasets"].arn}/incoming/*"]
    error_message = "Intake must not read/list other recordings or write approved releases."
  }
}

run "missing_email_does_not_claim_alerts" {
  command = plan
  assert {
    condition     = length(aws_budgets_budget.collection) == 0 && !output.budget_alerts_configured
    error_message = "No configured email must mean no budget notifications, explicitly."
  }
}

run "alerts_track_usage_before_credits" {
  command = apply
  variables {
    budget_alert_email = "operator@example.com"
  }
  assert {
    condition     = aws_budgets_budget.collection[0].limit_amount == "25" && !aws_budgets_budget.collection[0].cost_types[0].include_credit && length(aws_budgets_budget.collection[0].notification) == 3
    error_message = "Collection budget must track gross usage with three alert thresholds."
  }
}

run "wrong_account_is_rejected" {
  command = plan
  override_data {
    target = data.aws_caller_identity.current
    values = { account_id = "561616501354" }
  }
  expect_failures = [terraform_data.account_guard]
}
