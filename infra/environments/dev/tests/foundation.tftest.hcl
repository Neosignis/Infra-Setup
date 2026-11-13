mock_provider "aws" {
  mock_data "aws_caller_identity" {
    defaults = {
      account_id = "123456789012"
      arn        = "arn:aws:iam::123456789012:user/test"
    }
  }
  mock_data "aws_availability_zones" {
    defaults = {
      names = ["eu-west-1a", "eu-west-1b"]
    }
  }
  mock_resource "aws_kms_key" {
    defaults = { arn = "arn:aws:kms:eu-west-1:123456789012:key/11111111-1111-1111-1111-111111111111" }
  }
  mock_resource "aws_iam_role" {
    defaults = { arn = "arn:aws:iam::123456789012:role/fixture" }
  }
  mock_resource "aws_ecs_cluster" {
    defaults = { arn = "arn:aws:ecs:eu-west-1:123456789012:cluster/fixture" }
  }
  mock_resource "aws_s3_bucket" {
    defaults = { arn = "arn:aws:s3:::fixture" }
  }
  mock_resource "aws_lb" {
    defaults = { arn = "arn:aws:elasticloadbalancing:eu-west-1:123456789012:loadbalancer/app/fixture/1234567890123456" }
  }
  mock_resource "aws_lb_target_group" {
    defaults = { arn = "arn:aws:elasticloadbalancing:eu-west-1:123456789012:targetgroup/fixture/1234567890123456" }
  }
  mock_resource "aws_autoscaling_group" {
    defaults = { arn = "arn:aws:autoscaling:eu-west-1:123456789012:autoScalingGroup:11111111-1111-1111-1111-111111111111:autoScalingGroupName/fixture" }
  }
  mock_resource "aws_launch_template" {
    defaults = { latest_version = 1 }
  }
  mock_resource "aws_ecs_task_definition" {
    defaults = { arn = "arn:aws:ecs:eu-west-1:123456789012:task-definition/fixture:1" }
  }
  mock_resource "aws_service_discovery_service" {
    defaults = { arn = "arn:aws:servicediscovery:eu-west-1:123456789012:service/srv-fixture" }
  }
}

variables {
  region = "eu-west-1"
}

run "foundation_has_no_running_compute" {
  command = plan
  assert {
    condition     = length(module.api) == 0 && length(module.database) == 0 && length(module.gpu) == 0
    error_message = "Default development plan must not create API, RDS or GPU runtime."
  }
}

run "runtime_requires_concrete_release" {
  command = plan
  variables {
    enable_runtime = true
  }
  expect_failures = [terraform_data.configuration]
}

run "gpu_requires_runtime_and_pinned_artifacts" {
  command = plan
  variables {
    enable_gpu = true
  }
  expect_failures = [terraform_data.configuration]
}

run "optional_runtime_database_and_gpu_plan" {
  command = plan
  variables {
    enable_runtime    = true
    enable_database   = true
    enable_gpu        = true
    certificate_arn   = "arn:aws:acm:eu-west-1:123456789012:certificate/11111111-1111-1111-1111-111111111111"
    api_image         = "123456789012.dkr.ecr.eu-west-1.amazonaws.com/neosignis-dev/api@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    worker_image      = "123456789012.dkr.ecr.eu-west-1.amazonaws.com/neosignis-dev/worker@sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    gpu_ami_id        = "ami-0123456789abcdef0"
    allowed_api_cidrs = ["192.0.2.1/32"]
  }
  assert {
    condition     = length(module.api) == 1 && length(module.database) == 1 && length(module.gpu) == 1
    error_message = "All explicitly enabled optional modules should plan with concrete inputs."
  }
}
