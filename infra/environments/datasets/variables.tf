variable "expected_account_id" {
  type        = string
  description = "Refuse to operate in another account. Confirm with STS before initializing the backend."
  validation {
    condition     = can(regex("^[0-9]{12}$", var.expected_account_id))
    error_message = "Supply the confirmed twelve-digit AWS account ID without hyphens."
  }
}

variable "region" {
  type    = string
  default = "us-east-1"
}

variable "budget_alert_email" {
  type        = string
  default     = ""
  description = "No budget or email notifications are created until an address is supplied."
  validation {
    condition     = var.budget_alert_email == "" || can(regex("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", var.budget_alert_email))
    error_message = "Supply an email address or leave empty while preparing the plan."
  }
}

variable "monthly_budget_usd" {
  type        = number
  default     = 25
  description = "Draft monthly alert threshold, not a hard spending cap."
  validation {
    condition     = var.monthly_budget_usd > 0
    error_message = "The monthly budget must be positive."
  }
}
