# API module variables

variable "project_name" {
  description = "Project name"
  type        = string
}

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

variable "region" {
  description = "AWS region"
  type        = string
  default     = "eu-west-2"
}

variable "knowledge_bucket_name" {
  description = "Name of the S3 bucket for knowledge base content"
  type        = string
  default     = ""
}

variable "lambda_package_path" {
  description = "Path to Lambda deployment package"
  type        = string
  default     = "../lambda-package/placeholder.py.zip"
}

variable "knowledge_base_id" {
  description = "Bedrock Knowledge Base ID"
  type        = string
  default     = ""
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-west-2"
}