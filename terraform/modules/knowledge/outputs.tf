# Knowledge module outputs

output "specifications_bucket_name" {
  description = "Name of the S3 bucket for specifications"
  value       = aws_s3_bucket.specifications.bucket
}

output "specifications_bucket_arn" {
  description = "ARN of the S3 bucket for specifications"
  value       = aws_s3_bucket.specifications.arn
}

output "examples_bucket_name" {
  description = "Name of the S3 bucket for examples"
  value       = aws_s3_bucket.examples.bucket
}

output "examples_bucket_arn" {
  description = "ARN of the S3 bucket for examples"
  value       = aws_s3_bucket.examples.arn
}

output "lambda_packages_bucket_name" {
  description = "Name of the S3 bucket for Lambda deployment packages"
  value       = aws_s3_bucket.lambda_packages.bucket
}

output "lambda_packages_bucket_arn" {
  description = "ARN of the S3 bucket for Lambda deployment packages"
  value       = aws_s3_bucket.lambda_packages.arn
}

output "question_bank_bucket_name" {
  description = "Name of the S3 bucket for question bank"
  value       = aws_s3_bucket.question_bank.bucket
}

output "question_bank_bucket_arn" {
  description = "ARN of the S3 bucket for question bank"
  value       = aws_s3_bucket.question_bank.arn
}

# Bedrock Knowledge Base outputs are in bedrock_kb.tf
# Removed duplicate output definition

output "knowledge_base_arn" {
  description = "Bedrock Knowledge Base ARN"
  value       = try(aws_bedrockagent_knowledge_base.gcse_kb.arn, "")
}

output "data_source_id" {
  description = "Knowledge Base Data Source ID"
  value       = try(aws_bedrockagent_data_source.s3_source.id, "")
}


output "opensearch_collection_endpoint" {
  description = "OpenSearch Serverless collection endpoint"
  value       = try(aws_opensearchserverless_collection.kb_collection.collection_endpoint, "")
}
