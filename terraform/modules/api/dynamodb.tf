# DynamoDB tables for user authentication and session management

# KMS key for DynamoDB encryption
resource "aws_kms_key" "dynamodb_key" {
  description             = "KMS key for DynamoDB encryption - GCSE Generator V2"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = {
    Name        = "GCSE DynamoDB Encryption Key"
    Environment = var.environment
    Purpose     = "DynamoDB table encryption"
  }
}

resource "aws_kms_alias" "dynamodb_key_alias" {
  name          = "alias/gcse-dynamodb-${var.environment}"
  target_key_id = aws_kms_key.dynamodb_key.key_id
}

# Users table for authentication
resource "aws_dynamodb_table" "users" {
  name         = "gcse-generator-v2-users-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"

  attribute {
    name = "pk"
    type = "S"
  }

  attribute {
    name = "email"
    type = "S"
  }

  # GSI for email lookup
  global_secondary_index {
    name            = "EmailIndex"
    hash_key        = "email"
    projection_type = "ALL"
  }

  # Enable encryption at rest with customer-managed KMS key
  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.dynamodb_key.arn
  }

  # Enable point-in-time recovery for data protection
  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name        = "GCSE Users Table V2"
    Environment = var.environment
    Purpose     = "User authentication and profile storage"
    Encryption  = "Enabled"
  }
}

# Sessions table for user session management
resource "aws_dynamodb_table" "sessions" {
  name         = "gcse-generator-v2-sessions-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  range_key    = "sk"

  attribute {
    name = "pk"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  attribute {
    name = "user_id"
    type = "S"
  }

  # GSI for user session history queries
  global_secondary_index {
    name            = "UserSessionsIndex"
    hash_key        = "user_id"
    range_key       = "sk"
    projection_type = "ALL"
  }

  # TTL configuration for automatic session cleanup (7 days = 604800 seconds)
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  # Enable encryption at rest with customer-managed KMS key
  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.dynamodb_key.arn
  }

  # Enable point-in-time recovery for data protection
  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name        = "GCSE Sessions Table V2"
    Environment = var.environment
    Purpose     = "User session storage with TTL"
    Encryption  = "Enabled"
  }
}

# TopicCoverage table for tracking user topic coverage statistics
resource "aws_dynamodb_table" "topic_coverage" {
  name         = "gcse-generator-v2-topic-coverage-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  range_key    = "sk"

  attribute {
    name = "pk"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "topic"
    type = "S"
  }

  # GSI for user coverage statistics queries
  global_secondary_index {
    name            = "UserCoverageIndex"
    hash_key        = "user_id"
    range_key       = "sk"
    projection_type = "ALL"
  }

  # GSI for topic popularity queries
  global_secondary_index {
    name            = "TopicPopularityIndex"
    hash_key        = "topic"
    range_key       = "sk"
    projection_type = "ALL"
  }

  # Enable encryption at rest with customer-managed KMS key
  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.dynamodb_key.arn
  }

  # Enable point-in-time recovery for data protection
  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name        = "GCSE Topic Coverage Table V2"
    Environment = var.environment
    Purpose     = "User topic coverage tracking and analytics"
    Encryption  = "Enabled"
  }
}

# QuestionFeedback table for user ratings and feedback
resource "aws_dynamodb_table" "question_feedback" {
  name         = "gcse-generator-v2-question-feedback-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  range_key    = "sk"

  attribute {
    name = "pk"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  attribute {
    name = "question_id"
    type = "S"
  }

  attribute {
    name = "user_id"
    type = "S"
  }

  # GSI for aggregating feedback per question
  global_secondary_index {
    name            = "QuestionFeedbackIndex"
    hash_key        = "question_id"
    range_key       = "sk"
    projection_type = "ALL"
  }

  # GSI for user feedback history
  global_secondary_index {
    name            = "UserFeedbackIndex"
    hash_key        = "user_id"
    range_key       = "sk"
    projection_type = "ALL"
  }

  # Enable encryption at rest with customer-managed KMS key
  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.dynamodb_key.arn
  }

  # Enable point-in-time recovery for data protection
  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name        = "GCSE Question Feedback Table V2"
    Environment = var.environment
    Purpose     = "User feedback collection for AI learning"
    Encryption  = "Enabled"
  }
}

# QualityScores table for question quality metrics
resource "aws_dynamodb_table" "quality_scores" {
  name         = "gcse-generator-v2-quality-scores-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"

  attribute {
    name = "pk"
    type = "S"
  }

  attribute {
    name = "quality_score"
    type = "N"
  }

  # GSI for finding high/low quality questions
  global_secondary_index {
    name            = "QualityScoreIndex"
    hash_key        = "quality_score"
    projection_type = "ALL"
  }

  # Enable encryption at rest with customer-managed KMS key
  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.dynamodb_key.arn
  }

  # Enable point-in-time recovery for data protection
  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name        = "GCSE Quality Scores Table V2"
    Environment = var.environment
    Purpose     = "Question quality metrics for AI learning"
    Encryption  = "Enabled"
  }
}