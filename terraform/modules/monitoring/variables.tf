# Monitoring module variables

variable "project_name" {
  description = "Project name"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-west-2"
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "api_gateway_id" {
  description = "API Gateway ID"
  type        = string
}

variable "api_gateway_name" {
  description = "API Gateway name"
  type        = string
}

variable "interpret_lambda_name" {
  description = "InterpretLambda function name"
  type        = string
}

variable "generate_lambda_name" {
  description = "GenerateLambda function name"
  type        = string
}

variable "auth_lambda_name" {
  description = "AuthLambda function name"
  type        = string
}

variable "feedback_lambda_name" {
  description = "FeedbackLambda function name"
  type        = string
}

variable "refinement_lambda_name" {
  description = "RefinementLambda function name"
  type        = string
}

variable "session_lambda_name" {
  description = "SessionLambda function name"
  type        = string
}

variable "export_lambda_name" {
  description = "ExportLambda function name"
  type        = string
}

variable "topic_coverage_lambda_name" {
  description = "TopicCoverageLambda function name"
  type        = string
}

variable "cost_monitoring_lambda_name" {
  description = "CostMonitoringLambda function name"
  type        = string
  default     = ""
}

variable "specifications_bucket_name" {
  description = "S3 specifications bucket name"
  type        = string
}

variable "examples_bucket_name" {
  description = "S3 examples bucket name"
  type        = string
}

variable "frontend_bucket_name" {
  description = "S3 frontend bucket name"
  type        = string
}

variable "question_bank_bucket_name" {
  description = "S3 question bank bucket name"
  type        = string
}

variable "cloudfront_distribution_id" {
  description = "CloudFront distribution ID"
  type        = string
}

variable "alert_email" {
  description = "Email address for alerts"
  type        = string
}

variable "cost_threshold_daily" {
  description = "Daily cost threshold in USD"
  type        = number
  default     = 1.60 # $1.60/day = ~$48/month (20% buffer over $40 target)
}

variable "cost_threshold_monthly" {
  description = "Monthly cost threshold in USD"
  type        = number
  default     = 48.0 # $48/month (20% buffer over $40 target)
}
# DynamoDB Auto-Scaling Variables
variable "enable_dynamodb_autoscaling" {
  description = "Enable DynamoDB auto-scaling"
  type        = bool
  default     = true
}

variable "dynamodb_min_read_capacity" {
  description = "Minimum read capacity for DynamoDB tables"
  type        = number
  default     = 1
}

variable "dynamodb_max_read_capacity" {
  description = "Maximum read capacity for DynamoDB tables"
  type        = number
  default     = 10
}

variable "dynamodb_min_write_capacity" {
  description = "Minimum write capacity for DynamoDB tables"
  type        = number
  default     = 1
}

variable "dynamodb_max_write_capacity" {
  description = "Maximum write capacity for DynamoDB tables"
  type        = number
  default     = 10
}

variable "dynamodb_target_utilization" {
  description = "Target utilization percentage for DynamoDB auto-scaling"
  type        = number
  default     = 70.0
}