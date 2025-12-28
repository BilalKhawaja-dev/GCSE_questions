# API module outputs

output "api_gateway_id" {
  description = "API Gateway ID"
  value       = aws_api_gateway_rest_api.gcse_api.id
}

output "api_gateway_name" {
  description = "API Gateway name"
  value       = aws_api_gateway_rest_api.gcse_api.name
}

output "api_gateway_url" {
  description = "API Gateway endpoint URL"
  value       = "https://${aws_api_gateway_rest_api.gcse_api.id}.execute-api.eu-west-2.amazonaws.com/${var.environment}"
}

output "interpret_lambda_name" {
  description = "InterpretLambda function name"
  value       = aws_lambda_function.interpret_lambda.function_name
}

output "generate_lambda_name" {
  description = "GenerateLambda function name"
  value       = aws_lambda_function.generate_lambda.function_name
}

output "interpret_lambda_arn" {
  description = "InterpretLambda function ARN"
  value       = aws_lambda_function.interpret_lambda.arn
}

output "generate_lambda_arn" {
  description = "GenerateLambda function ARN"
  value       = aws_lambda_function.generate_lambda.arn
}