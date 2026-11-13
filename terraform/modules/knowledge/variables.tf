# Knowledge module variables

variable "environment" {
  description = "Environment name"
  type        = string
}


variable "region" {
  description = "AWS region"
  type        = string
  default     = "eu-west-2"
}

variable "specifications_bucket_arn" {
  description = "ARN of S3 bucket containing specifications and PDFs"
  type        = string
}

variable "specifications_bucket_name" {
  description = "Name of S3 bucket containing specifications and PDFs"
  type        = string
}
