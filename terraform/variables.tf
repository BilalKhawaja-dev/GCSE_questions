# Input variables for GCSE Question Generator infrastructure

variable "aws_region" {
  description = "AWS region for deployment (London for data residency)"
  type        = string
  default     = "eu-west-2"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "domain_name" {
  description = "Domain name for the frontend (optional)"
  type        = string
  default     = ""
}

variable "bedrock_model_haiku" {
  description = "Bedrock model ID for Claude Haiku (interpretation)"
  type        = string
  default     = "anthropic.claude-3-haiku-20240307-v1:0"
}

variable "bedrock_model_sonnet" {
  description = "Bedrock model ID for Claude Sonnet (generation)"
  type        = string
  default     = "anthropic.claude-3-sonnet-20240229-v1:0"
}

variable "alert_email" {
  description = "Email address for CloudWatch alerts"
  type        = string
}

variable "api_rate_limit" {
  description = "API rate limit per user per hour"
  type        = number
  default     = 100
}

variable "cost_threshold_daily" {
  description = "Daily cost threshold in GBP for alerts"
  type        = number
  default     = 20
}

variable "cost_threshold_monthly" {
  description = "Monthly cost threshold in GBP for alerts"
  type        = number
  default     = 500
}