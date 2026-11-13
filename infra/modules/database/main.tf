variable "name" { type = string }
variable "private_subnets" { type = list(string) }
variable "database_sg" { type = string }
variable "kms_key_arn" { type = string }

resource "aws_db_subnet_group" "main" {
  name       = var.name
  subnet_ids = var.private_subnets
}
resource "terraform_data" "snapshot_suffix" {}
resource "aws_db_parameter_group" "postgres" {
  name_prefix = "${var.name}-"
  family      = "postgres16"
  parameter {
    name  = "rds.force_ssl"
    value = "1"
  }
}
resource "aws_db_instance" "postgres" {
  identifier                      = var.name
  engine                          = "postgres"
  engine_version                  = "16"
  instance_class                  = "db.t4g.micro"
  allocated_storage               = 20
  max_allocated_storage           = 50
  storage_type                    = "gp3"
  storage_encrypted               = true
  kms_key_id                      = var.kms_key_arn
  db_name                         = "neosignis"
  username                        = "neosignis_admin"
  manage_master_user_password     = true
  db_subnet_group_name            = aws_db_subnet_group.main.name
  parameter_group_name            = aws_db_parameter_group.postgres.name
  vpc_security_group_ids          = [var.database_sg]
  publicly_accessible             = false
  multi_az                        = false
  backup_retention_period         = 7
  deletion_protection             = true
  skip_final_snapshot             = false
  final_snapshot_identifier       = "${var.name}-final-${terraform_data.snapshot_suffix.id}"
  auto_minor_version_upgrade      = true
  copy_tags_to_snapshot           = true
  enabled_cloudwatch_logs_exports = ["postgresql"]
}
output "endpoint" { value = aws_db_instance.postgres.address }
output "master_secret_arn" {
  value     = aws_db_instance.postgres.master_user_secret[0].secret_arn
  sensitive = true
}
