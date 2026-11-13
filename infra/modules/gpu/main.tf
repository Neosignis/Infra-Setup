variable "name" { type = string }
variable "region" { type = string }
variable "vpc_id" { type = string }
variable "cluster_name" { type = string }
variable "cluster_arn" { type = string }
variable "private_subnets" { type = list(string) }
variable "worker_sg" { type = string }
variable "image" { type = string }
variable "ami_id" { type = string }
variable "instance_type" { type = string }
variable "max_instances" { type = number }
variable "desired_tasks" { type = number }
variable "model_bucket_arn" { type = string }
variable "assets_bucket_arn" { type = string }
variable "kms_key_arn" { type = string }
variable "engine_provider" {
  type    = string
  default = ""
}

resource "aws_iam_role" "host" {
  name = "${var.name}-gpu-host"
  assume_role_policy = jsonencode({
    Version = "2012-10-17", Statement = [{
      Effect = "Allow", Principal = { Service = "ec2.amazonaws.com" }, Action = "sts:AssumeRole"
    }]
  })
}
resource "aws_iam_role_policy_attachment" "ecs_host" {
  role       = aws_iam_role.host.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role"
}
resource "aws_iam_role_policy_attachment" "ssm_host" {
  role       = aws_iam_role.host.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}
resource "aws_iam_instance_profile" "host" {
  name = "${var.name}-gpu"
  role = aws_iam_role.host.name
}
resource "aws_launch_template" "gpu" {
  name_prefix            = "${var.name}-gpu-"
  image_id               = var.ami_id
  instance_type          = var.instance_type
  vpc_security_group_ids = [var.worker_sg]
  iam_instance_profile {
    name = aws_iam_instance_profile.host.name
  }
  metadata_options {
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
    http_endpoint               = "enabled"
  }
  block_device_mappings {
    device_name = "/dev/xvda"
    ebs {
      encrypted             = true
      volume_type           = "gp3"
      volume_size           = 100
      delete_on_termination = true
    }
  }
  user_data = base64encode(<<-EOT
    #!/bin/bash
    set -eu
    echo 'ECS_CLUSTER=${var.cluster_name}' >> /etc/ecs/ecs.config
    echo 'ECS_ENABLE_GPU_SUPPORT=true' >> /etc/ecs/ecs.config
    echo 'ECS_AWSVPC_BLOCK_IMDS=true' >> /etc/ecs/ecs.config
  EOT
  )
  tag_specifications {
    resource_type = "instance"
    tags          = { Name = "${var.name}-gpu", AmazonECSManaged = "true" }
  }
}
resource "aws_autoscaling_group" "gpu" {
  name                = "${var.name}-gpu"
  min_size            = 0
  max_size            = var.max_instances
  desired_capacity    = 0
  vpc_zone_identifier = var.private_subnets
  launch_template {
    id      = aws_launch_template.gpu.id
    version = aws_launch_template.gpu.latest_version
  }
  tag {
    key                 = "AmazonECSManaged"
    value               = "true"
    propagate_at_launch = true
  }
  lifecycle {
    ignore_changes = [desired_capacity]
  }
}
resource "aws_ecs_capacity_provider" "gpu" {
  name = "${var.name}-gpu"
  auto_scaling_group_provider {
    auto_scaling_group_arn         = aws_autoscaling_group.gpu.arn
    managed_termination_protection = "DISABLED"
    managed_scaling {
      status                    = "ENABLED"
      target_capacity           = 100
      minimum_scaling_step_size = 1
      maximum_scaling_step_size = 1
      instance_warmup_period    = 120
    }
  }
}
resource "aws_ecs_cluster_capacity_providers" "engine" {
  cluster_name       = var.cluster_name
  capacity_providers = ["FARGATE", aws_ecs_capacity_provider.gpu.name]
  default_capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight            = 1
  }
}
resource "aws_cloudwatch_log_group" "worker" {
  name              = "/neosignis/${var.name}/worker"
  retention_in_days = 14
}
resource "aws_iam_role" "execution" {
  name = "${var.name}-worker-execution"
  assume_role_policy = jsonencode({
    Version = "2012-10-17", Statement = [{
      Effect = "Allow", Principal = { Service = "ecs-tasks.amazonaws.com" }, Action = "sts:AssumeRole"
    }]
  })
}
resource "aws_iam_role_policy_attachment" "execution" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}
resource "aws_iam_role" "worker" {
  name               = "${var.name}-worker-app"
  assume_role_policy = aws_iam_role.execution.assume_role_policy
}
resource "aws_iam_role_policy" "read_approved_artifacts" {
  name = "read-approved-artifacts"
  role = aws_iam_role.worker.id
  policy = jsonencode({
    Version = "2012-10-17", Statement = [
      { Effect = "Allow", Action = ["s3:GetObject"], Resource = ["${var.model_bucket_arn}/approved/*", "${var.assets_bucket_arn}/approved/*"] },
      { Effect = "Allow", Action = ["kms:Decrypt"], Resource = var.kms_key_arn, Condition = { StringEquals = { "kms:ViaService" = "s3.${var.region}.amazonaws.com" } } }
    ]
  })
}
resource "aws_service_discovery_private_dns_namespace" "engine" {
  name = "${var.name}.internal"
  vpc  = var.vpc_id
}
resource "aws_service_discovery_service" "engine" {
  name = "engine"
  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.engine.id
    dns_records {
      ttl  = 10
      type = "A"
    }
    routing_policy = "MULTIVALUE"
  }
  health_check_custom_config {}
}
resource "aws_ecs_task_definition" "worker" {
  family                   = "${var.name}-worker"
  requires_compatibilities = ["EC2"]
  network_mode             = "awsvpc"
  cpu                      = "2048"
  memory                   = "4096"
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.worker.arn
  container_definitions = jsonencode([{
    name                   = "worker", image = var.image, essential = true, user = "10001",
    readonlyRootFilesystem = true,
    command                = ["python", "-m", "uvicorn", "neosignis.worker:app", "--host", "0.0.0.0", "--port", "8001", "--no-access-log"],
    environment            = [{ name = "ENGINE_PROVIDER", value = var.engine_provider }],
    portMappings           = [{ containerPort = 8001, protocol = "tcp" }],
    resourceRequirements   = [{ type = "GPU", value = "1" }],
    linuxParameters        = { capabilities = { drop = ["ALL"] } },
    logConfiguration = {
      logDriver = "awslogs", options = {
        awslogs-group  = aws_cloudwatch_log_group.worker.name,
        awslogs-region = var.region, awslogs-stream-prefix = "worker"
      }
    },
    healthCheck = {
      command  = ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8001/healthz', timeout=2)"],
      interval = 30, timeout = 5, retries = 3, startPeriod = 60
    }
  }])
}
resource "aws_ecs_service" "worker" {
  name            = "${var.name}-worker"
  cluster         = var.cluster_arn
  task_definition = aws_ecs_task_definition.worker.arn
  desired_count   = var.desired_tasks
  capacity_provider_strategy {
    capacity_provider = aws_ecs_capacity_provider.gpu.name
    weight            = 1
  }
  network_configuration {
    subnets          = var.private_subnets
    security_groups  = [var.worker_sg]
    assign_public_ip = false
  }
  service_registries {
    registry_arn = aws_service_discovery_service.engine.arn
  }
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
  depends_on = [aws_ecs_cluster_capacity_providers.engine, aws_iam_role_policy_attachment.execution, aws_iam_role_policy.read_approved_artifacts]
}
output "service_name" { value = aws_ecs_service.worker.name }
