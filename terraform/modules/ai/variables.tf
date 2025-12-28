# AI module variables

variable "environment" {
  description = "Environment name"
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