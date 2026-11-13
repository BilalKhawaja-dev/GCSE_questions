# SQS queue for question verification pipeline

# Dead Letter Queue for failed verifications
resource "aws_sqs_queue" "verification_dlq" {
  name                      = "gcse-verification-dlq-${var.environment}"
  message_retention_seconds = 1209600 # 14 days

  # Enable encryption at rest
  sqs_managed_sse_enabled = true

  tags = {
    Name        = "GCSE Verification DLQ V2"
    Environment = var.environment
    Purpose     = "Dead letter queue for failed verifications"
  }
}

# Main verification queue
resource "aws_sqs_queue" "verification_queue" {
  name                       = "gcse-verification-queue-${var.environment}"
  visibility_timeout_seconds = 360   # 6 minutes (Lambda timeout is 5 minutes)
  message_retention_seconds  = 86400 # 24 hours
  receive_wait_time_seconds  = 20    # Long polling

  # Enable encryption at rest
  sqs_managed_sse_enabled = true

  # Configure dead letter queue
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.verification_dlq.arn
    maxReceiveCount     = 3 # Retry up to 3 times before sending to DLQ
  })

  tags = {
    Name        = "GCSE Verification Queue V2"
    Environment = var.environment
    Purpose     = "Question verification processing queue"
  }
}

# IAM policy for Lambda to access verification queue
resource "aws_iam_policy" "verification_queue_policy" {
  name        = "gcse-verification-queue-policy-${var.environment}"
  description = "Policy for Lambda functions to access verification queue"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:GetQueueUrl"
        ]
        Resource = [
          aws_sqs_queue.verification_queue.arn,
          aws_sqs_queue.verification_dlq.arn
        ]
      }
    ]
  })

  tags = {
    Name        = "GCSE Verification Queue Policy V2"
    Environment = var.environment
  }
}

# Output queue URLs for Lambda configuration
output "verification_queue_url" {
  description = "URL of the verification queue"
  value       = aws_sqs_queue.verification_queue.url
}

output "verification_queue_arn" {
  description = "ARN of the verification queue"
  value       = aws_sqs_queue.verification_queue.arn
}

output "verification_dlq_url" {
  description = "URL of the verification dead letter queue"
  value       = aws_sqs_queue.verification_dlq.url
}

output "verification_dlq_arn" {
  description = "ARN of the verification dead letter queue"
  value       = aws_sqs_queue.verification_dlq.arn
}

output "verification_queue_policy_arn" {
  description = "ARN of the verification queue IAM policy"
  value       = aws_iam_policy.verification_queue_policy.arn
}
