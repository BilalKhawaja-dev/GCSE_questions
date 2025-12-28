"""
Integration tests for GCSE Question Generator infrastructure.
Tests infrastructure configuration, policies, and component integration.

Requirements: 19.2
"""

import json
import pytest
import boto3
from unittest.mock import patch, MagicMock
import os


class TestInfrastructureIntegration:
    """Integration tests for infrastructure components."""
    
    def setup_method(self):
        """Set up test environment."""
        self.region = "eu-west-2"
        self.environment = "test"
        
    def test_terraform_configuration_structure(self):
        """Test that Terraform configuration files have correct structure."""
        # Test main.tf exists and has required modules
        with open('terraform/main.tf', 'r') as f:
            main_tf_content = f.read()
            
        # Verify required modules are defined
        assert 'module "frontend"' in main_tf_content
        assert 'module "api"' in main_tf_content
        assert 'module "ai"' in main_tf_content
        assert 'module "knowledge"' in main_tf_content
        assert 'module "monitoring"' in main_tf_content
        
        # Verify provider configuration
        assert 'provider "aws"' in main_tf_content
        assert 'region = var.aws_region' in main_tf_content
        
    def test_backend_configuration(self):
        """Test Terraform backend configuration."""
        with open('terraform/backend.tf', 'r') as f:
            backend_content = f.read()
            
        # Verify S3 backend configuration
        assert 'backend "s3"' in backend_content
        assert 'bucket         = "gcse-terraform-state-' in backend_content  # Allow for random suffix
        assert 'key            = "prod/terraform.tfstate"' in backend_content
        assert 'region         = "eu-west-2"' in backend_content
        assert 'encrypt        = true' in backend_content
        assert 'dynamodb_table = "terraform-locks"' in backend_content
        
    def test_s3_bucket_configuration(self):
        """Test S3 bucket configuration in knowledge module."""
        with open('terraform/modules/knowledge/main.tf', 'r') as f:
            knowledge_content = f.read()
            
        # Verify specifications bucket
        assert 'resource "aws_s3_bucket" "specifications"' in knowledge_content
        assert 'gcse-specifications-' in knowledge_content
        
        # Verify examples bucket
        assert 'resource "aws_s3_bucket" "examples"' in knowledge_content
        assert 'gcse-examples-' in knowledge_content
        
        # Verify versioning is enabled
        assert 'aws_s3_bucket_versioning' in knowledge_content
        assert 'status = "Enabled"' in knowledge_content
        
        # Verify encryption configuration
        assert 'aws_s3_bucket_server_side_encryption_configuration' in knowledge_content
        assert 'sse_algorithm = "AES256"' in knowledge_content
        
        # Verify public access is blocked
        assert 'aws_s3_bucket_public_access_block' in knowledge_content
        assert 'block_public_acls       = true' in knowledge_content
        
        # Verify lifecycle policies
        assert 'aws_s3_bucket_lifecycle_configuration' in knowledge_content
        assert 'noncurrent_days = 90' in knowledge_content  # 90-day retention
        
    def test_lambda_function_configuration(self):
        """Test Lambda function configuration in API module."""
        with open('terraform/modules/api/main.tf', 'r') as f:
            api_content = f.read()
            
        # Verify InterpretLambda function
        assert 'resource "aws_lambda_function" "interpret_lambda"' in api_content
        assert 'runtime      = "python3.11"' in api_content
        assert 'timeout      = 30' in api_content
        assert 'memory_size  = 512' in api_content
        
        # Verify GenerateLambda function
        assert 'resource "aws_lambda_function" "generate_lambda"' in api_content
        assert 'timeout      = 60' in api_content
        assert 'memory_size  = 1024' in api_content
        
        # Verify IAM roles
        assert 'resource "aws_iam_role" "interpret_lambda_role"' in api_content
        assert 'resource "aws_iam_role" "generate_lambda_role"' in api_content
        
        # Verify Bedrock permissions
        assert 'bedrock:InvokeModel' in api_content
        assert 'var.bedrock_model_haiku' in api_content
        assert 'var.bedrock_model_sonnet' in api_content
        
        # Verify S3 permissions for GenerateLambda
        assert 's3:GetObject' in api_content
        
    def test_api_gateway_configuration(self):
        """Test API Gateway configuration."""
        with open('terraform/modules/api/api_gateway.tf', 'r') as f:
            api_gateway_content = f.read()
            
        # Verify REST API
        assert 'resource "aws_api_gateway_rest_api" "gcse_api"' in api_gateway_content
        assert 'gcse-question-generator-' in api_gateway_content
        
        # Verify endpoints
        assert 'path_part   = "interpret"' in api_gateway_content
        assert 'path_part   = "generate"' in api_gateway_content
        
        # Verify HTTP methods
        assert 'http_method   = "POST"' in api_gateway_content
        assert 'http_method   = "OPTIONS"' in api_gateway_content
        
        # Verify CORS configuration
        assert 'Access-Control-Allow-Origin' in api_gateway_content
        assert 'Access-Control-Allow-Methods' in api_gateway_content
        assert 'Access-Control-Allow-Headers' in api_gateway_content
        
        # Verify request validation
        assert 'aws_api_gateway_request_validator' in api_gateway_content
        assert 'validate_request_body       = true' in api_gateway_content
        
        # Verify Lambda integrations
        assert 'type                   = "AWS_PROXY"' in api_gateway_content
        assert 'integration_http_method = "POST"' in api_gateway_content
        
    def test_cloudfront_distribution_configuration(self):
        """Test CloudFront distribution configuration."""
        with open('terraform/modules/frontend/main.tf', 'r') as f:
            frontend_content = f.read()
            
        # Verify CloudFront distribution
        assert 'resource "aws_cloudfront_distribution" "frontend_distribution"' in frontend_content
        
        # Verify HTTPS-only configuration
        assert 'viewer_protocol_policy = "redirect-to-https"' in frontend_content
        
        # Verify compression
        assert 'compress               = true' in frontend_content
        
        # Verify caching policies
        assert 'default_ttl = 3600' in frontend_content  # 1 hour
        assert 'max_ttl     = 86400' in frontend_content     # 24 hours
        
        # Verify Origin Access Control
        assert 'aws_cloudfront_origin_access_control' in frontend_content
        assert 'signing_behavior                  = "always"' in frontend_content
        
        # Verify price class for cost optimization
        assert 'price_class = "PriceClass_100"' in frontend_content
        
        # Verify custom error pages for SPA
        assert 'custom_error_response' in frontend_content
        assert 'error_code         = 404' in frontend_content
        assert 'response_page_path = "/index.html"' in frontend_content
        
    def test_monitoring_configuration(self):
        """Test monitoring and alerting configuration."""
        with open('terraform/modules/monitoring/main.tf', 'r') as f:
            monitoring_content = f.read()
            
        # Verify SNS topic for alerts
        assert 'resource "aws_sns_topic" "alerts"' in monitoring_content
        assert 'resource "aws_sns_topic_subscription" "email_alerts"' in monitoring_content
        
        # Verify CloudWatch dashboard
        assert 'resource "aws_cloudwatch_dashboard" "gcse_dashboard"' in monitoring_content
        assert 'AWS/ApiGateway' in monitoring_content
        assert 'AWS/Lambda' in monitoring_content
        
        # Verify critical alarms
        assert 'aws_cloudwatch_metric_alarm' in monitoring_content
        assert 'lambda_error_rate' in monitoring_content
        assert 'api_gateway_5xx_errors' in monitoring_content
        
        # Verify alarm thresholds
        assert 'threshold           = "5"' in monitoring_content  # Lambda error threshold
        assert 'threshold           = "1"' in monitoring_content  # API Gateway 5xx threshold
        
    def test_request_validation_schemas(self):
        """Test API Gateway request validation schemas."""
        with open('terraform/modules/api/api_gateway.tf', 'r') as f:
            api_gateway_content = f.read()
            
        # Verify interpret request schema
        assert 'InterpretRequest' in api_gateway_content
        assert 'maxLength = 500' in api_gateway_content  # Query length limit
        
        # Verify generate request schema
        assert 'GenerateRequest' in api_gateway_content
        assert '"Foundation", "Higher"' in api_gateway_content  # Tier enum
        assert 'maximum = 50' in api_gateway_content  # Count limit
        
    def test_environment_configuration(self):
        """Test environment-specific configuration files."""
        # Test production environment
        with open('terraform/environments/prod.tfvars', 'r') as f:
            prod_config = f.read()
            
        assert 'environment = "prod"' in prod_config
        assert 'aws_region  = "eu-west-2"' in prod_config
        assert 'api_rate_limit = 100' in prod_config
        assert 'cost_threshold_daily   = 20' in prod_config
        
        # Test development environment
        with open('terraform/environments/dev.tfvars', 'r') as f:
            dev_config = f.read()
            
        assert 'environment = "dev"' in dev_config
        assert 'api_rate_limit = 50' in dev_config
        assert 'cost_threshold_daily   = 5' in dev_config
        
    def test_security_configuration(self):
        """Test security configurations across modules."""
        # Test IAM least-privilege policies
        with open('terraform/modules/api/main.tf', 'r') as f:
            api_content = f.read()
            
        # Verify scoped Bedrock permissions
        assert 'arn:aws:bedrock:eu-west-2::foundation-model/' in api_content
        
        # Verify S3 bucket policies block public access
        with open('terraform/modules/knowledge/main.tf', 'r') as f:
            knowledge_content = f.read()
            
        assert 'block_public_acls       = true' in knowledge_content
        assert 'block_public_policy     = true' in knowledge_content
        assert 'ignore_public_acls      = true' in knowledge_content
        assert 'restrict_public_buckets = true' in knowledge_content
        
        # Verify CloudFront OAC security
        with open('terraform/modules/frontend/main.tf', 'r') as f:
            frontend_content = f.read()
            
        assert 'origin_access_control_origin_type = "s3"' in frontend_content
        assert 'signing_protocol                  = "sigv4"' in frontend_content
        
    def test_cost_optimization_features(self):
        """Test cost optimization configurations."""
        # Verify CloudFront price class
        with open('terraform/modules/frontend/main.tf', 'r') as f:
            frontend_content = f.read()
            
        assert 'price_class = "PriceClass_100"' in frontend_content
        
        # Verify S3 lifecycle policies
        with open('terraform/modules/knowledge/main.tf', 'r') as f:
            knowledge_content = f.read()
            
        assert 'noncurrent_days = 90' in knowledge_content
        assert 'days_after_initiation = 7' in knowledge_content
        
        # Verify Lambda memory allocation
        with open('terraform/modules/api/main.tf', 'r') as f:
            api_content = f.read()
            
        assert 'memory_size  = 512' in api_content   # InterpretLambda
        assert 'memory_size  = 1024' in api_content  # GenerateLambda
        
    def test_regional_deployment_configuration(self):
        """Test that all resources are configured for eu-west-2 region."""
        # Check main configuration
        with open('terraform/main.tf', 'r') as f:
            main_content = f.read()
            
        assert 'region = var.aws_region' in main_content
        
        # Check variables default
        with open('terraform/variables.tf', 'r') as f:
            variables_content = f.read()
            
        assert 'default     = "eu-west-2"' in variables_content
        
        # Check environment configs
        with open('terraform/environments/prod.tfvars', 'r') as f:
            prod_content = f.read()
            
        assert 'aws_region  = "eu-west-2"' in prod_content


if __name__ == '__main__':
    pytest.main([__file__, '-v'])