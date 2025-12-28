# Output values for GCSE Question Generator infrastructure

output "api_gateway_url" {
  description = "API Gateway endpoint URL"
  value       = module.api.api_gateway_url
}

output "api_gateway_id" {
  description = "API Gateway ID"
  value       = module.api.api_gateway_id
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID"
  value       = module.frontend.cloudfront_distribution_id
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name"
  value       = module.frontend.cloudfront_domain_name
}

output "frontend_bucket_name" {
  description = "S3 bucket name for frontend assets"
  value       = module.frontend.frontend_bucket_name
}

output "specifications_bucket_name" {
  description = "S3 bucket name for specifications"
  value       = module.knowledge.specifications_bucket_name
}

output "examples_bucket_name" {
  description = "S3 bucket name for examples"
  value       = module.knowledge.examples_bucket_name
}

output "lambda_packages_bucket_name" {
  description = "S3 bucket name for Lambda deployment packages"
  value       = module.knowledge.lambda_packages_bucket_name
}

output "interpret_lambda_name" {
  description = "InterpretLambda function name"
  value       = module.api.interpret_lambda_name
}

output "generate_lambda_name" {
  description = "GenerateLambda function name"
  value       = module.api.generate_lambda_name
}

output "monitoring_dashboard_url" {
  description = "CloudWatch dashboard URL"
  value       = module.monitoring.dashboard_url
}