variable "name" { type = string }
resource "aws_ecr_repository" "images" {
  for_each             = toset(["api", "worker"])
  name                 = "${var.name}/${each.value}"
  image_tag_mutability = "IMMUTABLE"
  force_delete         = false
  image_scanning_configuration {
    scan_on_push = true
  }
  encryption_configuration {
    encryption_type = "AES256"
  }
}
output "urls" { value = { for k, v in aws_ecr_repository.images : k => v.repository_url } }
output "arns" { value = { for k, v in aws_ecr_repository.images : k => v.arn } }
