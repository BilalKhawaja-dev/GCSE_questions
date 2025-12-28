# GCSE Question Generator - Main Terraform Configuration
# Deploys serverless AI-powered platform for generating GCSE exam questions

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Configure AWS Provider for London region
provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "GCSE-Question-Generator"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# Data source for current AWS account
data "aws_caller_identity" "current" {}

# Data source for current AWS region
data "aws_region" "current" {}

# Frontend module - S3 + CloudFront
module "frontend" {
  source = "./modules/frontend"
  
  environment = var.environment
  domain_name = var.domain_name
}

# API module - API Gateway + Lambda functions
module "api" {
  source = "./modules/api"
  
  environment                   = var.environment
  specifications_bucket_name    = module.knowledge.specifications_bucket_name
  examples_bucket_name          = module.knowledge.examples_bucket_name
  lambda_packages_bucket_name   = module.knowledge.lambda_packages_bucket_name
  bedrock_model_haiku           = var.bedrock_model_haiku
  bedrock_model_sonnet          = var.bedrock_model_sonnet
}

# AI module - Bedrock configurations
module "ai" {
  source = "./modules/ai"
  
  environment           = var.environment
  bedrock_model_haiku   = var.bedrock_model_haiku
  bedrock_model_sonnet  = var.bedrock_model_sonnet
}

# Knowledge module - S3 buckets for specifications and examples
module "knowledge" {
  source = "./modules/knowledge"
  
  environment = var.environment
}

# Monitoring module - CloudWatch dashboards, alarms, SNS
module "monitoring" {
  source = "./modules/monitoring"
  
  environment                  = var.environment
  api_gateway_id              = module.api.api_gateway_id
  api_gateway_name            = module.api.api_gateway_name
  interpret_lambda_name       = module.api.interpret_lambda_name
  generate_lambda_name        = module.api.generate_lambda_name
  specifications_bucket_name  = module.knowledge.specifications_bucket_name
  examples_bucket_name        = module.knowledge.examples_bucket_name
  frontend_bucket_name        = module.frontend.frontend_bucket_name
  cloudfront_distribution_id  = module.frontend.cloudfront_distribution_id
  alert_email                 = var.alert_email
  cost_threshold_daily        = var.cost_threshold_daily
  cost_threshold_monthly      = var.cost_threshold_monthly
}