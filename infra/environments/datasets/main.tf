locals {
  buckets = {
    datasets = "neosignis-datasets-${var.expected_account_id}-${var.region}"
    rights   = "neosignis-rights-${var.expected_account_id}-${var.region}"
  }
}

resource "terraform_data" "account_guard" {
  lifecycle {
    precondition {
      condition     = data.aws_caller_identity.current.account_id == var.expected_account_id
      error_message = "The signed-in AWS account is not the confirmed Neosignis account."
    }
  }
}

resource "aws_kms_key" "storage" {
  for_each                = local.buckets
  description             = "Neosignis ${each.key} storage; separate dataset and identity/permission keys"
  enable_key_rotation     = true
  deletion_window_in_days = 30
  lifecycle {
    prevent_destroy = true
  }
  depends_on = [terraform_data.account_guard]
}

resource "aws_s3_bucket" "storage" {
  for_each      = local.buckets
  bucket        = each.value
  force_destroy = false
  lifecycle {
    prevent_destroy = true
  }
  depends_on = [terraform_data.account_guard]
}

resource "aws_s3_bucket_public_access_block" "storage" {
  for_each                = local.buckets
  bucket                  = aws_s3_bucket.storage[each.key].id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "storage" {
  for_each = local.buckets
  bucket   = aws_s3_bucket.storage[each.key].id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_versioning" "storage" {
  for_each = local.buckets
  bucket   = aws_s3_bucket.storage[each.key].id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "storage" {
  for_each = local.buckets
  bucket   = aws_s3_bucket.storage[each.key].id
  rule {
    bucket_key_enabled = true
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.storage[each.key].arn
    }
  }
}

resource "aws_s3_bucket_policy" "storage" {
  for_each = local.buckets
  bucket   = aws_s3_bucket.storage[each.key].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyInsecureTransport", Effect = "Deny", Principal = "*", Action = "s3:*",
        Resource  = [aws_s3_bucket.storage[each.key].arn, "${aws_s3_bucket.storage[each.key].arn}/*"],
        Condition = { Bool = { "aws:SecureTransport" = "false" } }
      },
      {
        Sid      = "DenyEncryptionOverride", Effect = "Deny", Principal = "*", Action = "s3:PutObject",
        Resource = "${aws_s3_bucket.storage[each.key].arn}/*",
        Condition = {
          Null            = { "s3:x-amz-server-side-encryption" = "false" },
          StringNotEquals = { "s3:x-amz-server-side-encryption" = "aws:kms" }
        }
      },
      {
        Sid      = "DenyDifferentKey", Effect = "Deny", Principal = "*", Action = "s3:PutObject",
        Resource = "${aws_s3_bucket.storage[each.key].arn}/*",
        Condition = {
          Null            = { "s3:x-amz-server-side-encryption-aws-kms-key-id" = "false" },
          StringNotEquals = { "s3:x-amz-server-side-encryption-aws-kms-key-id" = aws_kms_key.storage[each.key].arn }
        }
      }
    ]
  })
}

# Retain completed objects and their versions. This only clears abandoned uploads.
# Retention/withdrawal decisions require an explicit, reviewed deletion workflow.
resource "aws_s3_bucket_lifecycle_configuration" "storage" {
  for_each = local.buckets
  bucket   = aws_s3_bucket.storage[each.key].id
  rule {
    id     = "abort-incomplete-uploads-only"
    status = "Enabled"
    filter {}
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# Policies are deliberately unattached. Trust and attachment require verified
# operator identities; creating a policy alone grants nobody access.
locals {
  access = {
    intake   = { bucket = "datasets", prefixes = ["incoming/*"], actions = ["s3:PutObject", "s3:AbortMultipartUpload"], kms = ["kms:GenerateDataKey", "kms:Decrypt"] }
    reviewer = { bucket = "datasets", prefixes = ["incoming/*", "review/*", "approved/*"], actions = ["s3:GetObject", "s3:GetObjectVersion", "s3:PutObject"], kms = ["kms:GenerateDataKey", "kms:Decrypt"] }
    trainer  = { bucket = "datasets", prefixes = ["approved/*"], actions = ["s3:GetObject", "s3:GetObjectVersion"], kms = ["kms:Decrypt"] }
    rights   = { bucket = "rights", prefixes = ["records/*"], actions = ["s3:GetObject", "s3:GetObjectVersion", "s3:PutObject"], kms = ["kms:GenerateDataKey", "kms:Decrypt"] }
  }
}

resource "aws_iam_policy" "access" {
  for_each = local.access
  name     = "neosignis-datasets-${each.key}-${var.region}"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat(
      [{ Effect = "Allow", Action = each.value.actions, Resource = [for prefix in each.value.prefixes : "${aws_s3_bucket.storage[each.value.bucket].arn}/${prefix}"] }],
      each.key == "intake" ? [] : [{
        Effect    = "Allow", Action = ["s3:ListBucket"], Resource = [aws_s3_bucket.storage[each.value.bucket].arn],
        Condition = { StringLike = { "s3:prefix" = each.value.prefixes } }
      }],
      [{
        Effect = "Allow", Action = each.value.kms, Resource = [aws_kms_key.storage[each.value.bucket].arn],
        Condition = {
          StringEquals = {
            "kms:ViaService"                   = "s3.${var.region}.amazonaws.com",
            "kms:EncryptionContext:aws:s3:arn" = aws_s3_bucket.storage[each.value.bucket].arn
          }
        }
      }]
    )
  })
}

resource "aws_budgets_budget" "collection" {
  count        = var.budget_alert_email == "" ? 0 : 1
  account_id   = var.expected_account_id
  name         = "neosignis-account-monthly-collection"
  budget_type  = "COST"
  limit_amount = tostring(var.monthly_budget_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"
  cost_types {
    include_credit = false
    include_refund = false
  }
  dynamic "notification" {
    for_each = toset([50, 80, 100])
    content {
      comparison_operator        = "GREATER_THAN"
      threshold                  = notification.value
      threshold_type             = "PERCENTAGE"
      notification_type          = "ACTUAL"
      subscriber_email_addresses = [var.budget_alert_email]
    }
  }
  depends_on = [terraform_data.account_guard]
}
