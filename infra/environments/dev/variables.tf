variable "region" {
  type        = string
  description = "Confirm region, residency, latency and GPU availability before apply."
}
variable "name" {
  type    = string
  default = "neosignis-dev"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,19}$", var.name))
    error_message = "Use 3-20 lowercase alphanumeric/hyphen characters, beginning with a letter."
  }
}
variable "enable_runtime" {
  type    = bool
  default = false
}
variable "enable_database" {
  type    = bool
  default = false
}
variable "enable_gpu" {
  type    = bool
  default = false
}
variable "certificate_arn" {
  type    = string
  default = ""
}
variable "api_image" {
  type        = string
  default     = ""
  description = "Immutable ECR image reference with @sha256 digest."
}
variable "worker_image" {
  type    = string
  default = ""
}
variable "gpu_ami_id" {
  type        = string
  default     = ""
  description = "Explicit approved ECS GPU-optimized AMI in selected region."
}
variable "gpu_instance_type" {
  type    = string
  default = "g4dn.xlarge"
}
variable "engine_provider" {
  type        = string
  default     = ""
  description = "Reviewed image-installed module:factory. Empty means unavailable."
}
variable "gpu_max_instances" {
  type    = number
  default = 1
  validation {
    condition     = var.gpu_max_instances >= 1 && var.gpu_max_instances <= 4 && floor(var.gpu_max_instances) == var.gpu_max_instances
    error_message = "Development GPU pool must be bounded to 1-4 whole instances."
  }
}
variable "gpu_desired_tasks" {
  type    = number
  default = 0
  validation {
    condition     = var.gpu_desired_tasks >= 0 && var.gpu_desired_tasks <= var.gpu_max_instances && floor(var.gpu_desired_tasks) == var.gpu_desired_tasks
    error_message = "GPU desired tasks must be a whole number between zero and max instances."
  }
}
variable "allowed_api_cidrs" {
  type        = list(string)
  default     = []
  description = "Development tester public CIDRs. Empty blocks all ALB ingress."
  validation {
    condition     = alltrue([for cidr in var.allowed_api_cidrs : can(cidrnetmask(cidr)) && cidr != "0.0.0.0/0"])
    error_message = "Use explicit IPv4 tester CIDRs; open internet ingress is disallowed in this dev root."
  }
}
variable "callback_urls" {
  type    = list(string)
  default = ["http://localhost:5173/callback"]
}
variable "logout_urls" {
  type    = list(string)
  default = ["http://localhost:5173"]
}
variable "budget_alert_email" {
  type    = string
  default = ""
}
variable "monthly_budget_usd" {
  type    = number
  default = 100
  validation {
    condition     = var.monthly_budget_usd > 0
    error_message = "Budget must be positive; AWS budgets alert rather than enforce a hard cap."
  }
}
