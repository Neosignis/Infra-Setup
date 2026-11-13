variable "name" { type = string }
variable "suffix" { type = string }

resource "aws_kms_key" "data" {
  description             = "${var.name} model, asset and research encryption"
  enable_key_rotation     = true
  deletion_window_in_days = 30
}
resource "aws_s3_bucket" "data" {
  for_each      = toset(["models", "assets", "research"])
  bucket        = "${var.name}-${each.value}-${var.suffix}"
  force_destroy = false
}
resource "aws_s3_bucket_public_access_block" "data" {
  for_each                = aws_s3_bucket.data
  bucket                  = each.value.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
resource "aws_s3_bucket_versioning" "data" {
  for_each = aws_s3_bucket.data
  bucket   = each.value.id
  versioning_configuration {
    status = "Enabled"
  }
}
resource "aws_s3_bucket_server_side_encryption_configuration" "data" {
  for_each = aws_s3_bucket.data
  bucket   = each.value.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.data.arn
    }
    bucket_key_enabled = true
  }
}
resource "aws_s3_bucket_policy" "data" {
  for_each = aws_s3_bucket.data
  bucket   = each.value.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "DenyInsecureTransport", Effect = "Deny", Principal = "*", Action = "s3:*",
      Resource  = [each.value.arn, "${each.value.arn}/*"],
      Condition = { Bool = { "aws:SecureTransport" = "false" } }
    }]
  })
}
resource "aws_s3_bucket_lifecycle_configuration" "research" {
  bucket = aws_s3_bucket.data["research"].id
  rule {
    id     = "short-lived-consented-research"
    status = "Enabled"
    filter {}
    expiration {
      days = 7
    }
    noncurrent_version_expiration {
      noncurrent_days = 7
    }
    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }
}
output "bucket_names" { value = { for k, v in aws_s3_bucket.data : k => v.id } }
output "bucket_arns" { value = { for k, v in aws_s3_bucket.data : k => v.arn } }
output "kms_key_arn" { value = aws_kms_key.data.arn }
