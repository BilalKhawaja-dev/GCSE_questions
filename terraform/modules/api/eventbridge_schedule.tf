# EventBridge Schedule for Question Bank Replenishment
# Triggers replenishment lambda weekly to check inventory and generate questions

resource "aws_cloudwatch_event_rule" "replenishment_schedule" {
  name                = "${var.project_name}-replenishment-schedule"
  description         = "Trigger question bank replenishment weekly"
  schedule_expression = "cron(0 2 ? * SUN *)"  # Every Sunday at 2 AM UTC
  
  tags = {
    Name        = "${var.project_name}-replenishment-schedule"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

resource "aws_cloudwatch_event_target" "replenishment_lambda_target" {
  rule      = aws_cloudwatch_event_rule.replenishment_schedule.name
  target_id = "ReplenishmentLambda"
  arn       = aws_lambda_function.replenishment_lambda.arn
}

resource "aws_lambda_permission" "allow_eventbridge_replenishment" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.replenishment_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.replenishment_schedule.arn
}

# Replenishment Lambda Function
resource "aws_lambda_function" "replenishment_lambda" {
  function_name = "${var.project_name}-replenishment"
  role          = aws_iam_role.replenishment_lambda_role.arn
  handler       = "src.lambda_handlers.replenishment_lambda.handler"
  runtime       = "python3.11"
  timeout       = 300  # 5 minutes
  memory_size   = 512
  
  filename         = var.lambda_package_path
  source_code_hash = filebase64sha256(var.lambda_package_path)
  
  environment {
    variables = {
      VERIFIED_QUESTION_BANK_TABLE      = aws_dynamodb_table.verified_question_bank.name
      QUESTION_BANK_INVENTORY_TABLE     = aws_dynamodb_table.question_bank_inventory.name
      BATCH_GENERATION_LAMBDA           = aws_lambda_function.batch_generation_lambda.function_name
      TARGET_QUESTION_COUNT             = "50"
      LOG_LEVEL                         = "INFO"
    }
  }
  
  tags = {
    Name        = "${var.project_name}-replenishment-lambda"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# IAM Role for Replenishment Lambda
resource "aws_iam_role" "replenishment_lambda_role" {
  name = "${var.project_name}-replenishment-lambda-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
  
  tags = {
    Name        = "${var.project_name}-replenishment-lambda-role"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# IAM Policy for Replenishment Lambda
resource "aws_iam_role_policy" "replenishment_lambda_policy" {
  name = "${var.project_name}-replenishment-lambda-policy"
  role = aws_iam_role.replenishment_lambda_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem"
        ]
        Resource = [
          aws_dynamodb_table.verified_question_bank.arn,
          "${aws_dynamodb_table.verified_question_bank.arn}/index/*",
          aws_dynamodb_table.question_bank_inventory.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = aws_lambda_function.batch_generation_lambda.arn
      }
    ]
  })
}

# Batch Generation Lambda Function
resource "aws_lambda_function" "batch_generation_lambda" {
  function_name = "${var.project_name}-batch-generation"
  role          = aws_iam_role.batch_generation_lambda_role.arn
  handler       = "src.lambda_handlers.batch_generation_lambda.handler"
  runtime       = "python3.11"
  timeout       = 900  # 15 minutes for batch processing
  memory_size   = 1024
  
  filename         = var.lambda_package_path
  source_code_hash = filebase64sha256(var.lambda_package_path)
  
  environment {
    variables = {
      VERIFICATION_QUEUE_URL = aws_sqs_queue.verification_queue.url
      KNOWLEDGE_BASE_ID      = var.knowledge_base_id
      LOG_LEVEL              = "INFO"
    }
  }
  
  tags = {
    Name        = "${var.project_name}-batch-generation-lambda"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# IAM Role for Batch Generation Lambda
resource "aws_iam_role" "batch_generation_lambda_role" {
  name = "${var.project_name}-batch-generation-lambda-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
  
  tags = {
    Name        = "${var.project_name}-batch-generation-lambda-role"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# IAM Policy for Batch Generation Lambda
resource "aws_iam_role_policy" "batch_generation_lambda_policy" {
  name = "${var.project_name}-batch-generation-lambda-policy"
  role = aws_iam_role.batch_generation_lambda_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = aws_sqs_queue.verification_queue.arn
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:Retrieve"
        ]
        Resource = "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:knowledge-base/${var.knowledge_base_id}"
      }
    ]
  })
}

# Verification Lambda Function
resource "aws_lambda_function" "verification_lambda" {
  function_name = "${var.project_name}-verification"
  role          = aws_iam_role.verification_lambda_role.arn
  handler       = "src.lambda_handlers.verification_lambda.handler"
  runtime       = "python3.11"
  timeout       = 300  # 5 minutes per batch
  memory_size   = 2048  # More memory for SymPy and embeddings
  
  filename         = var.lambda_package_path
  source_code_hash = filebase64sha256(var.lambda_package_path)
  
  environment {
    variables = {
      VERIFIED_QUESTION_BANK_TABLE      = aws_dynamodb_table.verified_question_bank.name
      REJECTED_QUESTIONS_TABLE          = aws_dynamodb_table.rejected_questions.name
      QUESTION_BANK_INVENTORY_TABLE     = aws_dynamodb_table.question_bank_inventory.name
      KNOWLEDGE_BASE_ID                 = var.knowledge_base_id
      LOG_LEVEL                         = "INFO"
    }
  }
  
  tags = {
    Name        = "${var.project_name}-verification-lambda"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# SQS Event Source Mapping for Verification Lambda
resource "aws_lambda_event_source_mapping" "verification_queue_trigger" {
  event_source_arn = aws_sqs_queue.verification_queue.arn
  function_name    = aws_lambda_function.verification_lambda.arn
  batch_size       = 10  # Process up to 10 questions at once
  enabled          = true
}

# IAM Role for Verification Lambda
resource "aws_iam_role" "verification_lambda_role" {
  name = "${var.project_name}-verification-lambda-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
  
  tags = {
    Name        = "${var.project_name}-verification-lambda-role"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# IAM Policy for Verification Lambda
resource "aws_iam_role_policy" "verification_lambda_policy" {
  name = "${var.project_name}-verification-lambda-policy"
  role = aws_iam_role.verification_lambda_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = aws_sqs_queue.verification_queue.arn
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem"
        ]
        Resource = [
          aws_dynamodb_table.verified_question_bank.arn,
          "${aws_dynamodb_table.verified_question_bank.arn}/index/*",
          aws_dynamodb_table.rejected_questions.arn,
          aws_dynamodb_table.question_bank_inventory.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:Retrieve"
        ]
        Resource = "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:knowledge-base/${var.knowledge_base_id}"
      }
    ]
  })
}

# Data source for current AWS account
data "aws_caller_identity" "current" {}
