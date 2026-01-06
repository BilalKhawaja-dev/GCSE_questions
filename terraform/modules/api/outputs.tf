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

output "feedback_lambda_name" {
  description = "FeedbackLambda function name"
  value       = aws_lambda_function.feedback_lambda.function_name
}

output "feedback_lambda_arn" {
  description = "FeedbackLambda function ARN"
  value       = aws_lambda_function.feedback_lambda.arn
}

output "refinement_lambda_name" {
  description = "RefinementLambda function name"
  value       = aws_lambda_function.refinement_lambda.function_name
}

output "refinement_lambda_arn" {
  description = "RefinementLambda function ARN"
  value       = aws_lambda_function.refinement_lambda.arn
}

output "auth_lambda_name" {
  description = "AuthLambda function name"
  value       = aws_lambda_function.auth_lambda.function_name
}

output "auth_lambda_arn" {
  description = "AuthLambda function ARN"
  value       = aws_lambda_function.auth_lambda.arn
}

output "session_lambda_name" {
  description = "SessionLambda function name"
  value       = aws_lambda_function.session_lambda.function_name
}

output "session_lambda_arn" {
  description = "SessionLambda function ARN"
  value       = aws_lambda_function.session_lambda.arn
}

output "export_lambda_name" {
  description = "ExportLambda function name"
  value       = aws_lambda_function.export_lambda.function_name
}

output "export_lambda_arn" {
  description = "ExportLambda function ARN"
  value       = aws_lambda_function.export_lambda.arn
}

output "topic_coverage_lambda_name" {
  description = "TopicCoverageLambda function name"
  value       = aws_lambda_function.topic_coverage_lambda.function_name
}

output "topic_coverage_lambda_arn" {
  description = "TopicCoverageLambda function ARN"
  value       = aws_lambda_function.topic_coverage_lambda.arn
}

# DynamoDB table outputs
output "users_table_name" {
  description = "Users DynamoDB table name"
  value       = aws_dynamodb_table.users.name
}

output "sessions_table_name" {
  description = "Sessions DynamoDB table name"
  value       = aws_dynamodb_table.sessions.name
}

output "topic_coverage_table_name" {
  description = "TopicCoverage DynamoDB table name"
  value       = aws_dynamodb_table.topic_coverage.name
}

output "users_table_arn" {
  description = "Users DynamoDB table ARN"
  value       = aws_dynamodb_table.users.arn
}

output "sessions_table_arn" {
  description = "Sessions DynamoDB table ARN"
  value       = aws_dynamodb_table.sessions.arn
}

output "topic_coverage_table_arn" {
  description = "TopicCoverage DynamoDB table ARN"
  value       = aws_dynamodb_table.topic_coverage.arn
}

output "question_feedback_table_name" {
  description = "QuestionFeedback DynamoDB table name"
  value       = aws_dynamodb_table.question_feedback.name
}

output "quality_scores_table_name" {
  description = "QualityScores DynamoDB table name"
  value       = aws_dynamodb_table.quality_scores.name
}

output "question_feedback_table_arn" {
  description = "QuestionFeedback DynamoDB table ARN"
  value       = aws_dynamodb_table.question_feedback.arn
}

output "quality_scores_table_arn" {
  description = "QualityScores DynamoDB table ARN"
  value       = aws_dynamodb_table.quality_scores.arn
}

# EventBridge and error handling outputs
output "refinement_schedule_rule_name" {
  description = "EventBridge rule name for RefinementLambda schedule"
  value       = aws_cloudwatch_event_rule.refinement_schedule.name
}

output "refinement_schedule_rule_arn" {
  description = "EventBridge rule ARN for RefinementLambda schedule"
  value       = aws_cloudwatch_event_rule.refinement_schedule.arn
}

output "refinement_dlq_name" {
  description = "Dead Letter Queue name for RefinementLambda"
  value       = aws_sqs_queue.refinement_dlq.name
}

output "refinement_dlq_arn" {
  description = "Dead Letter Queue ARN for RefinementLambda"
  value       = aws_sqs_queue.refinement_dlq.arn
}

# KMS key outputs
output "dynamodb_kms_key_arn" {
  description = "ARN of the KMS key used for DynamoDB encryption"
  value       = aws_kms_key.dynamodb_key.arn
}

output "dynamodb_kms_key_id" {
  description = "ID of the KMS key used for DynamoDB encryption"
  value       = aws_kms_key.dynamodb_key.key_id
}