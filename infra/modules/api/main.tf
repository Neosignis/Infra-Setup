variable "name" { type = string }
variable "region" { type = string }
variable "cluster_arn" { type = string }
variable "vpc_id" { type = string }
variable "public_subnets" { type = list(string) }
variable "private_subnets" { type = list(string) }
variable "alb_sg" { type = string }
variable "api_sg" { type = string }
variable "certificate_arn" { type = string }
variable "image" { type = string }
variable "cognito_issuer" { type = string }
variable "cognito_client_id" { type = string }
variable "inference_url" { type = string }

resource "aws_cloudwatch_log_group" "api" {
  name              = "/neosignis/${var.name}/api"
  retention_in_days = 14
}
resource "aws_iam_role" "execution" {
  name = "${var.name}-api-execution"
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
resource "aws_iam_role" "app" {
  name               = "${var.name}-api-app"
  assume_role_policy = aws_iam_role.execution.assume_role_policy
}
resource "aws_lb" "api" {
  name                       = "${var.name}-api"
  load_balancer_type         = "application"
  internal                   = false
  security_groups            = [var.alb_sg]
  subnets                    = var.public_subnets
  drop_invalid_header_fields = true
  idle_timeout               = 30
}
resource "aws_lb_target_group" "api" {
  name        = "${var.name}-api"
  port        = 8000
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = var.vpc_id
  health_check {
    # Process health must not restart the API because a model is unavailable.
    path                = "/healthz"
    matcher             = "200"
    interval            = 30
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }
}
resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.api.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.certificate_arn
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}
resource "aws_ecs_task_definition" "api" {
  family                   = "${var.name}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.app.arn
  container_definitions = jsonencode([{
    name                   = "api", image = var.image, essential = true, user = "10001",
    readonlyRootFilesystem = true,
    portMappings           = [{ containerPort = 8000, protocol = "tcp" }],
    environment = [
      { name = "APP_ENV", value = "cloud" },
      { name = "AUTH_MODE", value = "cognito" },
      { name = "COGNITO_ISSUER", value = var.cognito_issuer },
      { name = "COGNITO_CLIENT_ID", value = var.cognito_client_id },
      { name = "INFERENCE_URL", value = var.inference_url }
    ],
    linuxParameters = { capabilities = { drop = ["ALL"] } },
    logConfiguration = {
      logDriver = "awslogs", options = {
        awslogs-group  = aws_cloudwatch_log_group.api.name,
        awslogs-region = var.region, awslogs-stream-prefix = "api"
      }
    }
  }])
}
resource "aws_ecs_service" "api" {
  name                   = "${var.name}-api"
  cluster                = var.cluster_arn
  task_definition        = aws_ecs_task_definition.api.arn
  desired_count          = 1
  launch_type            = "FARGATE"
  enable_execute_command = false
  network_configuration {
    subnets          = var.private_subnets
    security_groups  = [var.api_sg]
    assign_public_ip = false
  }
  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8000
  }
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
  depends_on = [aws_lb_listener.https, aws_iam_role_policy_attachment.execution]
}
resource "aws_cloudwatch_metric_alarm" "unhealthy" {
  alarm_name          = "${var.name}-api-unhealthy"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "UnHealthyHostCount"
  namespace           = "AWS/ApplicationELB"
  period              = 60
  statistic           = "Maximum"
  threshold           = 0
  treat_missing_data  = "notBreaching"
  dimensions = {
    LoadBalancer = aws_lb.api.arn_suffix
    TargetGroup  = aws_lb_target_group.api.arn_suffix
  }
  # Route alarm_actions to an agreed owner before shared use.
}
output "alb_dns" { value = aws_lb.api.dns_name }
