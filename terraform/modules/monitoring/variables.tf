# Monitoring module variables

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

variable "cloudfront_distribution_id" {
  description = "CloudFront distribution ID"
  type        = string
}

variable "alert_email" {
  description = "Email address for alerts"
  type        = string
}

variable "cost_threshold_daily" {
  description = "Daily cost threshold in GBP"
  type        = number
  default     = 20
}

variable "cost_threshold_monthly" {
  description = "Monthly cost threshold in GBP"
  type        = number
  default     = 500
}