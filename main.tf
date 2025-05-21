terraform {
  backend "s3" {}
}


provider "aws" {
  region = "us-east-2"
  assume_role {
    role_arn     = var.infra_role_arn
    session_name = "terraform-session"
  }
}

module "spotify_project_data_bucket" {
  source         = "git::https://github.com/amolrairikar/aws-account-infrastructure.git//modules/s3-bucket-private?ref=main"
  bucket_prefix  = "cta-train-analytics-data-lake"
  account_number = var.account_number
  environment    = var.environment
  project        = var.project_name
}

# data "aws_iam_policy_document" "eventbridge_trust_relationship_policy" {
#   statement {
#     actions = ["sts:AssumeRole"]
#     effect  = "Allow"
#     principals {
#       type        = "Service"
#       identifiers = ["scheduler.amazonaws.com"]
#     }
#   }
# }

# data "aws_iam_policy_document" "eventbridge_role_inline_policy_document" {
#   statement {
#     effect    = "Allow"
#     actions   = ["lambda:InvokeFunction"]
#     resources = [module.spotify_get_recently_played_lambda.lambda_arn]
#   }
# }

# module "eventbridge_role" {
#   source                    = "git::https://github.com/amolrairikar/aws-account-infrastructure.git//modules/iam-role?ref=main"
#   role_name                 = "cta-train-analytics-eventbridge-role"
#   trust_relationship_policy = data.aws_iam_policy_document.eventbridge_trust_relationship_policy.json
#   inline_policy             = data.aws_iam_policy_document.eventbridge_role_inline_policy_document.json
#   inline_policy_description = "Policy for EventBridge Scheduler to invoke CTA train analytics project Lambda functions"
#   environment               = var.environment
#   project                   = var.project_name
# }

# module "gtfs_lambda_eventbridge_scheduler" {
#   source               = "git::https://github.com/amolrairikar/aws-account-infrastructure.git//modules/eventbridge-scheduler?ref=main"
#   eventbridge_role_arn = module.eventbridge_role.role_arn
#   lambda_arn           = module.spotify_get_recently_played_lambda.lambda_arn
#   schedule_frequency   = "rate(1 hour)"
#   schedule_timezone   = "America/Chicago"
#   schedule_state       = "ENABLED"
#   environment          = var.environment
#   project              = var.project_name
# }