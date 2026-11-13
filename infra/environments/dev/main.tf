locals {
  suffix = "${data.aws_caller_identity.current.account_id}-${var.region}"
}

resource "terraform_data" "configuration" {
  lifecycle {
    precondition {
      condition     = !var.enable_runtime || (var.certificate_arn != "" && can(regex("@sha256:[a-f0-9]{64}$", var.api_image)) && length(var.allowed_api_cidrs) > 0)
      error_message = "Runtime requires a regional ACM certificate, digest-pinned API image and tester CIDRs."
    }
    precondition {
      condition     = !var.enable_gpu || (var.enable_runtime && var.gpu_ami_id != "" && can(regex("@sha256:[a-f0-9]{64}$", var.worker_image)))
      error_message = "GPU requires runtime, a reviewed GPU AMI and digest-pinned worker image."
    }
  }
}

module "network" {
  source            = "../../modules/network"
  name              = var.name
  region            = var.region
  azs               = slice(data.aws_availability_zones.available.names, 0, 2)
  enable_egress     = var.enable_runtime
  allowed_api_cidrs = var.allowed_api_cidrs
}
module "storage" {
  source = "../../modules/storage"
  name   = var.name
  suffix = local.suffix
}
module "registry" {
  source = "../../modules/registry"
  name   = var.name
}
module "identity" {
  source        = "../../modules/identity"
  name          = "${var.name}-${data.aws_caller_identity.current.account_id}"
  callback_urls = var.callback_urls
  logout_urls   = var.logout_urls
  region        = var.region
}

resource "aws_ecs_cluster" "engine" {
  name = var.name
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}
module "api" {
  count             = var.enable_runtime ? 1 : 0
  source            = "../../modules/api"
  name              = var.name
  region            = var.region
  cluster_arn       = aws_ecs_cluster.engine.arn
  vpc_id            = module.network.vpc_id
  public_subnets    = module.network.public_subnets
  private_subnets   = module.network.private_subnets
  alb_sg            = module.network.alb_sg
  api_sg            = module.network.api_sg
  certificate_arn   = var.certificate_arn
  image             = var.api_image
  cognito_issuer    = module.identity.issuer
  cognito_client_id = module.identity.client_id
  inference_url     = "http://engine.${var.name}.internal:8001"
  depends_on        = [terraform_data.configuration, module.network]
}
module "database" {
  count           = var.enable_database ? 1 : 0
  source          = "../../modules/database"
  name            = var.name
  private_subnets = module.network.private_subnets
  database_sg     = module.network.database_sg
  kms_key_arn     = module.storage.kms_key_arn
}
module "gpu" {
  count             = var.enable_gpu ? 1 : 0
  source            = "../../modules/gpu"
  name              = var.name
  region            = var.region
  vpc_id            = module.network.vpc_id
  cluster_name      = aws_ecs_cluster.engine.name
  cluster_arn       = aws_ecs_cluster.engine.arn
  private_subnets   = module.network.private_subnets
  worker_sg         = module.network.worker_sg
  image             = var.worker_image
  ami_id            = var.gpu_ami_id
  instance_type     = var.gpu_instance_type
  engine_provider   = var.engine_provider
  max_instances     = var.gpu_max_instances
  desired_tasks     = var.gpu_desired_tasks
  model_bucket_arn  = module.storage.bucket_arns["models"]
  assets_bucket_arn = module.storage.bucket_arns["assets"]
  kms_key_arn       = module.storage.kms_key_arn
  depends_on        = [terraform_data.configuration, module.network]
}

resource "aws_budgets_budget" "development" {
  count        = var.budget_alert_email != "" ? 1 : 0
  name         = "${var.name}-monthly"
  budget_type  = "COST"
  limit_amount = tostring(var.monthly_budget_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.budget_alert_email]
  }
}
