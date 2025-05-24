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

# S3 bucket for entire project
module "cta_train_analytics_project_data_bucket" {
  source         = "git::https://github.com/amolrairikar/aws-account-infrastructure.git//modules/s3-bucket-private?ref=main"
  bucket_prefix  = "cta-train-analytics-data-lake"
  account_number = var.account_number
  environment    = var.environment
  project        = var.project_name
}

# Trust + inline policy documents, role definition, and scheduler definition for EventBridge triggered GTFS fetch Lambda
data "aws_iam_policy_document" "eventbridge_trust_relationship_policy" {
  statement {
    actions = ["sts:AssumeRole"]
    effect  = "Allow"
    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "eventbridge_role_inline_policy_document" {
  statement {
    effect    = "Allow"
    actions   = ["lambda:InvokeFunction"]
    resources = [module.get_gtfs_data_lambda.lambda_arn]
  }
}

module "eventbridge_role" {
  source                    = "git::https://github.com/amolrairikar/aws-account-infrastructure.git//modules/iam-role?ref=main"
  role_name                 = "cta-train-analytics-eventbridge-role"
  trust_relationship_policy = data.aws_iam_policy_document.eventbridge_trust_relationship_policy.json
  inline_policy             = data.aws_iam_policy_document.eventbridge_role_inline_policy_document.json
  inline_policy_description = "Policy for EventBridge Scheduler to invoke CTA train analytics project Lambda functions"
  environment               = var.environment
  project                   = var.project_name
}

module "gtfs_lambda_eventbridge_scheduler" {
  source               = "git::https://github.com/amolrairikar/aws-account-infrastructure.git//modules/eventbridge-scheduler?ref=main"
  eventbridge_role_arn = module.eventbridge_role.role_arn
  lambda_arn           = module.get_gtfs_data_lambda.lambda_arn
  schedule_frequency   = "cron(1 0 * * 0 *)"  # Every week on Sunday at 12:01 AM
  schedule_timezone   = "America/Chicago"
  schedule_state       = "ENABLED"
  environment          = var.environment
  project              = var.project_name
}

# Generic trust relationship policy for all Lambdas
data "aws_iam_policy_document" "lambda_trust_relationship_policy" {
  statement {
    actions = ["sts:AssumeRole"]
    effect  = "Allow"
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

# Lambda execution policy, execution role, and function definition for GTFS fetch Lambda
data "aws_iam_policy_document" "lambda_get_get_gtfs_data_execution_role_inline_policy_document" {
  statement {
    effect    = "Allow"
    actions = [
      "s3:PutObject"
    ]
    resources = [
      "arn:aws:s3:::${module.cta_train_analytics_project_data_bucket.bucket_id}"
    ]
  }
  statement {
    effect    = "Allow"
    actions = [
      "sns:Publish"
    ]
    resources = [
      var.lambda_error_sns_topic_arn
    ]
  }
  statement {
    effect    = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = [
      "*"
    ]
  }
}

module "lambda_get_gtfs_data_played_role" {
  source                    = "git::https://github.com/amolrairikar/aws-account-infrastructure.git//modules/iam-role?ref=main"
  role_name                 = "get-gtfs-data-lambda-execution-role"
  trust_relationship_policy = data.aws_iam_policy_document.lambda_trust_relationship_policy.json
  inline_policy             = data.aws_iam_policy_document.lambda_get_get_gtfs_data_execution_role_inline_policy_document.json
  inline_policy_description = "Inline policy for get-gtfs-data Lambda function execution role"
  environment               = var.environment
  project                   = var.project_name
}

module "get_gtfs_data_lambda" {
  source                         = "git::https://github.com/amolrairikar/aws-account-infrastructure.git//modules/lambda?ref=main"
  environment                    = var.environment
  project                        = var.project_name
  lambda_name                    = "get-gtfs-data-lambda"
  lambda_description             = "Lambda function to fetch GTFS data from CTA"
  lambda_filename                = "get_gtfs_data.zip"
  lambda_handler                 = "main.lambda_handler"
  lambda_memory_size             = "256"
  lambda_runtime                 = "python3.12"
  lambda_execution_role_arn      = module.lambda_get_gtfs_data_played_role.role_arn
  sns_topic_arn                  = var.lambda_error_sns_topic_arn
    lambda_environment_variables = {
      S3_BUCKET = module.cta_train_analytics_project_data_bucket.bucket_id
  }
}