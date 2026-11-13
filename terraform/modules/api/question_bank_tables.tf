# DynamoDB tables for question verification and banking system

# Verified Question Bank - Main table for user queries
resource "aws_dynamodb_table" "verified_question_bank" {
  name         = "gcse-generator-v2-verified-questions-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "question_id"

  attribute {
    name = "question_id"
    type = "S"
  }

  attribute {
    name = "topic_grade_paper"
    type = "S"
  }

  attribute {
    name = "difficulty"
    type = "N"
  }

  # GSI for fast queries by topic/grade/paper + difficulty range
  global_secondary_index {
    name            = "TopicGradePaperDifficultyIndex"
    hash_key        = "topic_grade_paper"
    range_key       = "difficulty"
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
    Name        = "GCSE Verified Question Bank V2"
    Environment = var.environment
    Purpose     = "Verified questions for instant retrieval"
    Encryption  = "Enabled"
  }
}

# Rejected Questions - Analysis table for failed verifications
resource "aws_dynamodb_table" "rejected_questions" {
  name         = "gcse-generator-v2-rejected-questions-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "question_id"

  attribute {
    name = "question_id"
    type = "S"
  }

  attribute {
    name = "topic"
    type = "S"
  }

  attribute {
    name = "rejected_at"
    type = "S"
  }

  # GSI for analyzing rejection patterns by topic
  global_secondary_index {
    name            = "TopicRejectionIndex"
    hash_key        = "topic"
    range_key       = "rejected_at"
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
    Name        = "GCSE Rejected Questions V2"
    Environment = var.environment
    Purpose     = "Failed verification analysis"
    Encryption  = "Enabled"
  }
}

# Question Bank Inventory - Monitoring table for replenishment
resource "aws_dynamodb_table" "question_bank_inventory" {
  name         = "gcse-generator-v2-question-inventory-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "topic_grade_paper"

  attribute {
    name = "topic_grade_paper"
    type = "S"
  }

  attribute {
    name = "verified_count"
    type = "N"
  }

  # GSI for finding low-inventory topics
  global_secondary_index {
    name            = "InventoryLevelIndex"
    hash_key        = "verified_count"
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
    Name        = "GCSE Question Bank Inventory V2"
    Environment = var.environment
    Purpose     = "Question bank monitoring and replenishment"
    Encryption  = "Enabled"
  }
}
