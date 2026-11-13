# Development environment configuration for GCSE Question Generator

environment = "dev"
aws_region  = "eu-west-2"

# Bedrock model configurations
bedrock_model_haiku  = "anthropic.claude-3-haiku-20240307-v1:0"
bedrock_model_sonnet = "anthropic.claude-3-sonnet-20240229-v1:0"

# API configuration
api_rate_limit = 50

# Lower cost thresholds for development (in GBP)
cost_threshold_daily   = 5
cost_threshold_monthly = 20

# Alert configuration
alert_email = "dev@example.com" # Update with actual email