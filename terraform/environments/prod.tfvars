# Production environment configuration for GCSE Question Generator

environment = "prod"
aws_region  = "eu-west-2"

# Bedrock model configurations
bedrock_model_haiku  = "anthropic.claude-3-haiku-20240307-v1:0"
bedrock_model_sonnet = "anthropic.claude-3-sonnet-20240229-v1:0"

# API configuration
api_rate_limit = 100

# Cost thresholds (in GBP)
cost_threshold_daily   = 20
cost_threshold_monthly = 50

# Alert configuration
alert_email = "bilalkwj@example.com" # Update with actual email

# Disable auto-scaling temporarily to fix deployment
enable_dynamodb_autoscaling = false

# Optional domain name for custom domain
# domain_name = "gcse-questions.example.com"