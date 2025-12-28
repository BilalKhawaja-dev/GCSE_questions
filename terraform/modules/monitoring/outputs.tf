# Monitoring module outputs

output "sns_topic_arn" {
  description = "SNS topic ARN for alerts"
  value       = aws_sns_topic.alerts.arn
}

output "dashboard_url" {
  description = "CloudWatch dashboard URL"
  value       = "https://eu-west-2.console.aws.amazon.com/cloudwatch/home?region=eu-west-2#dashboards:name=${aws_cloudwatch_dashboard.gcse_dashboard.dashboard_name}"
}

output "cost_dashboard_url" {
  description = "CloudWatch cost dashboard URL"
  value       = "https://eu-west-2.console.aws.amazon.com/cloudwatch/home?region=eu-west-2#dashboards:name=${aws_cloudwatch_dashboard.cost_dashboard.dashboard_name}"
}

output "interpret_lambda_log_group" {
  description = "InterpretLambda CloudWatch log group name"
  value       = aws_cloudwatch_log_group.interpret_lambda_logs.name
}

output "generate_lambda_log_group" {
  description = "GenerateLambda CloudWatch log group name"
  value       = aws_cloudwatch_log_group.generate_lambda_logs.name
}