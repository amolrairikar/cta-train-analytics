variable "infra_role_arn" {
  description = "The ARN for the role assumed by the Terraform user"
  type        = string
}

variable "account_number" {
  description = "The AWS account number"
  type        = string
}

variable "email" {
  description = "Developer email to send notifications to"
  type        = string
}

variable "environment" {
  description = "The deployment environment (QA or PROD)"
  type        = string
}

variable "project_name" {
  description = "The name of the project (to be used in tags)"
  type        = string
}

variable "lambda_error_sns_topic_arn" {
  description = "The ARN of the SNS topic to send notifications of Lambda failures"
  type        = string
}