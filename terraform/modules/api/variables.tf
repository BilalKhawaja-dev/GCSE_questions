# API module variables

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "specifications_bucket_name" {
  description = "Name of the S3 bucket containing specifications"
  type        = string
}

variable "examples_bucket_name" {
  description = "Name of the S3 bucket containing examples"
  type        = string
}

variable "lambda_packages_bucket_name" {
  description = "Name of the S3 bucket containing Lambda deployment packages"
  type        = string
}

variable "bedrock_model_haiku" {
  description = "Bedrock model ID for Claude Haiku"
  type        = string
}

variable "bedrock_model_sonnet" {
  description = "Bedrock model ID for Claude Sonnet"
  type        = string
}

variable "question_bank_bucket_name" {
  description = "Name of the S3 bucket for question bank"
  type        = string
}