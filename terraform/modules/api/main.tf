# API module - API Gateway + Lambda functions

# Data source for Lambda deployment packages (will be created in task 13.1)
data "aws_s3_object" "lambda_packages" {
  bucket = var.lambda_packages_bucket_name
  key    = "lambda-functions.zip"
}

# IAM role for InterpretLambda
resource "aws_iam_role" "interpret_lambda_role" {
  name = "gcse-interpret-lambda-role-${var.environment}"

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
    Name        = "InterpretLambda Execution Role"
    Environment = var.environment
  }
}

# IAM role for AuthLambda
resource "aws_iam_role" "auth_lambda_role" {
  name = "gcse-auth-lambda-role-${var.environment}"

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
    Name        = "AuthLambda Execution Role"
    Environment = var.environment
  }
}

# IAM role for SessionLambda
resource "aws_iam_role" "session_lambda_role" {
  name = "gcse-session-lambda-role-${var.environment}"

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
    Name        = "SessionLambda Execution Role"
    Environment = var.environment
  }
}

# IAM role for FeedbackLambda
resource "aws_iam_role" "feedback_lambda_role" {
  name = "gcse-feedback-lambda-role-${var.environment}"

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
    Name        = "FeedbackLambda Execution Role"
    Environment = var.environment
  }
}

# IAM role for RefinementLambda
resource "aws_iam_role" "refinement_lambda_role" {
  name = "gcse-refinement-lambda-role-${var.environment}"

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
    Name        = "RefinementLambda Execution Role"
    Environment = var.environment
  }
}

# IAM role for ExportLambda
resource "aws_iam_role" "export_lambda_role" {
  name = "gcse-export-lambda-role-${var.environment}"

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
    Name        = "ExportLambda Execution Role"
    Environment = var.environment
  }
}

# IAM role for TopicCoverageLambda
resource "aws_iam_role" "topic_coverage_lambda_role" {
  name = "gcse-topic-coverage-lambda-role-${var.environment}"

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
    Name        = "TopicCoverageLambda Execution Role"
    Environment = var.environment
  }
}

# IAM role for AsyncWorkerLambda
resource "aws_iam_role" "async_worker_lambda_role" {
  name = "gcse-async-worker-lambda-role-${var.environment}"

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
    Name        = "AsyncWorkerLambda Execution Role"
    Environment = var.environment
  }
}

# Basic Lambda execution policy for InterpretLambda
resource "aws_iam_role_policy_attachment" "interpret_lambda_basic" {
  role       = aws_iam_role.interpret_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Basic Lambda execution policy for AuthLambda
resource "aws_iam_role_policy_attachment" "auth_lambda_basic" {
  role       = aws_iam_role.auth_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# IAM role for GenerateLambda
resource "aws_iam_role" "generate_lambda_role" {
  name = "gcse-generate-lambda-role-${var.environment}"

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
    Name        = "GenerateLambda Execution Role"
    Environment = var.environment
  }
}

# Basic Lambda execution policy for SessionLambda
resource "aws_iam_role_policy_attachment" "session_lambda_basic" {
  role       = aws_iam_role.session_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Basic Lambda execution policy for FeedbackLambda
resource "aws_iam_role_policy_attachment" "feedback_lambda_basic" {
  role       = aws_iam_role.feedback_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Basic Lambda execution policy for RefinementLambda
resource "aws_iam_role_policy_attachment" "refinement_lambda_basic" {
  role       = aws_iam_role.refinement_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Basic Lambda execution policy for ExportLambda
resource "aws_iam_role_policy_attachment" "export_lambda_basic" {
  role       = aws_iam_role.export_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Basic Lambda execution policy for TopicCoverageLambda
resource "aws_iam_role_policy_attachment" "topic_coverage_lambda_basic" {
  role       = aws_iam_role.topic_coverage_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Basic Lambda execution policy for AsyncWorkerLambda
resource "aws_iam_role_policy_attachment" "async_worker_lambda_basic" {
  role       = aws_iam_role.async_worker_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Basic Lambda execution policy for GenerateLambda
resource "aws_iam_role_policy_attachment" "generate_lambda_basic" {
  role       = aws_iam_role.generate_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Bedrock policy for InterpretLambda (Haiku only)
resource "aws_iam_role_policy" "interpret_bedrock_policy" {
  name = "interpret-bedrock-policy"
  role = aws_iam_role.interpret_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = "arn:aws:bedrock:eu-west-2::foundation-model/${var.bedrock_model_haiku}"
      }
    ]
  })
}

# Bedrock policy for GenerateLambda (Haiku for speed)
resource "aws_iam_role_policy" "generate_bedrock_policy" {
  name = "generate-bedrock-policy"
  role = aws_iam_role.generate_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = "arn:aws:bedrock:eu-west-2::foundation-model/${var.bedrock_model_haiku}"
      }
    ]
  })
}

# DynamoDB access policy for AuthLambda
resource "aws_iam_role_policy" "auth_dynamodb_policy" {
  name = "auth-dynamodb-policy"
  role = aws_iam_role.auth_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          aws_dynamodb_table.users.arn,
          "${aws_dynamodb_table.users.arn}/index/*",
          aws_dynamodb_table.sessions.arn,
          "${aws_dynamodb_table.sessions.arn}/index/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey"
        ]
        Resource = aws_kms_key.dynamodb_key.arn
      }
    ]
  })
}

# DynamoDB access policy for SessionLambda (read-only sessions and users for auth)
resource "aws_iam_role_policy" "session_dynamodb_policy" {
  name = "session-dynamodb-policy"
  role = aws_iam_role.session_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:Query"
        ]
        Resource = [
          aws_dynamodb_table.sessions.arn,
          "${aws_dynamodb_table.sessions.arn}/index/*",
          aws_dynamodb_table.users.arn,
          "${aws_dynamodb_table.users.arn}/index/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey"
        ]
        Resource = aws_kms_key.dynamodb_key.arn
      }
    ]
  })
}

# DynamoDB access policy for GenerateLambda (for session storage)
resource "aws_iam_role_policy" "generate_dynamodb_policy" {
  name = "generate-dynamodb-policy"
  role = aws_iam_role.generate_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:GetItem",
          "dynamodb:Query"
        ]
        Resource = [
          aws_dynamodb_table.sessions.arn,
          "${aws_dynamodb_table.sessions.arn}/index/*",
          aws_dynamodb_table.topic_coverage.arn,
          "${aws_dynamodb_table.topic_coverage.arn}/index/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:Encrypt",
          "kms:DescribeKey"
        ]
        Resource = aws_kms_key.dynamodb_key.arn
      }
    ]
  })
}

# SQS access policy for GenerateLambda (to send messages)
resource "aws_iam_role_policy" "generate_sqs_policy" {
  name = "generate-sqs-policy"
  role = aws_iam_role.generate_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:GetQueueUrl"
        ]
        Resource = aws_sqs_queue.async_generation_queue.arn
      }
    ]
  })
}

# DynamoDB access policy for FeedbackLambda
resource "aws_iam_role_policy" "feedback_dynamodb_policy" {
  name = "feedback-dynamodb-policy"
  role = aws_iam_role.feedback_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:Query",
          "dynamodb:GetItem"
        ]
        Resource = [
          aws_dynamodb_table.question_feedback.arn,
          "${aws_dynamodb_table.question_feedback.arn}/index/*",
          aws_dynamodb_table.quality_scores.arn,
          "${aws_dynamodb_table.quality_scores.arn}/index/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:Encrypt",
          "kms:DescribeKey"
        ]
        Resource = aws_kms_key.dynamodb_key.arn
      }
    ]
  })
}

# Bedrock policy for RefinementLambda (Sonnet only)
resource "aws_iam_role_policy" "refinement_bedrock_policy" {
  name = "refinement-bedrock-policy"
  role = aws_iam_role.refinement_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = "arn:aws:bedrock:eu-west-2::foundation-model/${var.bedrock_model_sonnet}"
      }
    ]
  })
}

# DynamoDB access policy for RefinementLambda
resource "aws_iam_role_policy" "refinement_dynamodb_policy" {
  name = "refinement-dynamodb-policy"
  role = aws_iam_role.refinement_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:Scan",
          "dynamodb:Query",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem"
        ]
        Resource = [
          aws_dynamodb_table.question_feedback.arn,
          "${aws_dynamodb_table.question_feedback.arn}/index/*",
          aws_dynamodb_table.quality_scores.arn,
          "${aws_dynamodb_table.quality_scores.arn}/index/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:Encrypt",
          "kms:DescribeKey"
        ]
        Resource = aws_kms_key.dynamodb_key.arn
      }
    ]
  })
}

# S3 access policy for RefinementLambda
resource "aws_iam_role_policy" "refinement_s3_policy" {
  name = "refinement-s3-policy"
  role = aws_iam_role.refinement_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ]
        Resource = [
          "arn:aws:s3:::${var.question_bank_bucket_name}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${var.question_bank_bucket_name}"
        ]
      }
    ]
  })
}

# DynamoDB access policy for ExportLambda
resource "aws_iam_role_policy" "export_dynamodb_policy" {
  name = "export-dynamodb-policy"
  role = aws_iam_role.export_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:Query"
        ]
        Resource = [
          aws_dynamodb_table.sessions.arn,
          "${aws_dynamodb_table.sessions.arn}/index/*",
          aws_dynamodb_table.users.arn,
          "${aws_dynamodb_table.users.arn}/index/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey"
        ]
        Resource = aws_kms_key.dynamodb_key.arn
      }
    ]
  })
}

# DynamoDB access policy for TopicCoverageLambda
resource "aws_iam_role_policy" "topic_coverage_dynamodb_policy" {
  name = "topic-coverage-dynamodb-policy"
  role = aws_iam_role.topic_coverage_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:Query",
          "dynamodb:UpdateItem"
        ]
        Resource = [
          aws_dynamodb_table.topic_coverage.arn,
          "${aws_dynamodb_table.topic_coverage.arn}/index/*",
          aws_dynamodb_table.users.arn,
          "${aws_dynamodb_table.users.arn}/index/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:Encrypt",
          "kms:DescribeKey"
        ]
        Resource = aws_kms_key.dynamodb_key.arn
      }
    ]
  })
}

# Bedrock policy for AsyncWorkerLambda (Haiku for speed)
resource "aws_iam_role_policy" "async_worker_bedrock_policy" {
  name = "async-worker-bedrock-policy"
  role = aws_iam_role.async_worker_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = "arn:aws:bedrock:eu-west-2::foundation-model/${var.bedrock_model_haiku}"
      }
    ]
  })
}

# DynamoDB access policy for AsyncWorkerLambda
resource "aws_iam_role_policy" "async_worker_dynamodb_policy" {
  name = "async-worker-dynamodb-policy"
  role = aws_iam_role.async_worker_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:GetItem",
          "dynamodb:Query"
        ]
        Resource = [
          aws_dynamodb_table.sessions.arn,
          "${aws_dynamodb_table.sessions.arn}/index/*",
          aws_dynamodb_table.topic_coverage.arn,
          "${aws_dynamodb_table.topic_coverage.arn}/index/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:Encrypt",
          "kms:DescribeKey"
        ]
        Resource = aws_kms_key.dynamodb_key.arn
      }
    ]
  })
}

# SQS access policy for AsyncWorkerLambda (to receive and delete messages)
resource "aws_iam_role_policy" "async_worker_sqs_policy" {
  name = "async-worker-sqs-policy"
  role = aws_iam_role.async_worker_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = aws_sqs_queue.async_generation_queue.arn
      }
    ]
  })
}

# S3 access policy for AsyncWorkerLambda
resource "aws_iam_role_policy" "async_worker_s3_policy" {
  name = "async-worker-s3-policy"
  role = aws_iam_role.async_worker_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject"
        ]
        Resource = [
          "arn:aws:s3:::${var.specifications_bucket_name}/*",
          "arn:aws:s3:::${var.examples_bucket_name}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${var.specifications_bucket_name}",
          "arn:aws:s3:::${var.examples_bucket_name}"
        ]
      }
    ]
  })
}

# S3 access policy for InterpretLambda
resource "aws_iam_role_policy" "interpret_s3_policy" {
  name = "interpret-s3-policy"
  role = aws_iam_role.interpret_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject"
        ]
        Resource = [
          "arn:aws:s3:::${var.specifications_bucket_name}/*",
          "arn:aws:s3:::${var.examples_bucket_name}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${var.specifications_bucket_name}",
          "arn:aws:s3:::${var.examples_bucket_name}"
        ]
      }
    ]
  })
}

# Lambda self-invoke policy for GenerateLambda (for async processing)
resource "aws_iam_role_policy" "generate_lambda_self_invoke_policy" {
  name = "generate-lambda-self-invoke-policy"
  role = aws_iam_role.generate_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = aws_lambda_function.generate_lambda.arn
      }
    ]
  })
}

# S3 access policy for GenerateLambda
resource "aws_iam_role_policy" "generate_s3_policy" {
  name = "generate-s3-policy"
  role = aws_iam_role.generate_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject"
        ]
        Resource = [
          "arn:aws:s3:::${var.specifications_bucket_name}/*",
          "arn:aws:s3:::${var.examples_bucket_name}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${var.specifications_bucket_name}",
          "arn:aws:s3:::${var.examples_bucket_name}"
        ]
      }
    ]
  })
}

# InterpretLambda function
resource "aws_lambda_function" "interpret_lambda" {
  function_name = "gcse-interpret-lambda-${var.environment}"
  role          = aws_iam_role.interpret_lambda_role.arn
  handler       = "src.lambda_handlers.interpret_lambda.lambda_handler"
  runtime       = "python3.11"
  timeout       = 30
  memory_size   = 512

  s3_bucket = data.aws_s3_object.lambda_packages.bucket
  s3_key    = data.aws_s3_object.lambda_packages.key

  environment {
    variables = {
      BEDROCK_MODEL_ID      = var.bedrock_model_haiku
      SPECIFICATIONS_BUCKET = var.specifications_bucket_name
      EXAMPLES_BUCKET       = var.examples_bucket_name
      REGION                = "eu-west-2"
      ENVIRONMENT           = var.environment
    }
  }

  tags = {
    Name        = "GCSE InterpretLambda"
    Environment = var.environment
    Purpose     = "Query interpretation using Claude Haiku"
  }
}

# AuthLambda function
resource "aws_lambda_function" "auth_lambda" {
  function_name = "gcse-auth-lambda-${var.environment}"
  role          = aws_iam_role.auth_lambda_role.arn
  handler       = "src.lambda_handlers.auth_lambda.lambda_handler"
  runtime       = "python3.11"
  timeout       = 30
  memory_size   = 512

  s3_bucket = data.aws_s3_object.lambda_packages.bucket
  s3_key    = data.aws_s3_object.lambda_packages.key

  environment {
    variables = {
      USERS_TABLE_NAME    = aws_dynamodb_table.users.name
      SESSIONS_TABLE_NAME = aws_dynamodb_table.sessions.name
      REGION              = "eu-west-2"
      ENVIRONMENT         = var.environment
    }
  }

  tags = {
    Name        = "GCSE AuthLambda"
    Environment = var.environment
    Purpose     = "User authentication and session management"
  }
}

# SessionLambda function
resource "aws_lambda_function" "session_lambda" {
  function_name = "gcse-session-lambda-${var.environment}"
  role          = aws_iam_role.session_lambda_role.arn
  handler       = "src.lambda_handlers.session_lambda.lambda_handler"
  runtime       = "python3.11"
  timeout       = 30
  memory_size   = 512

  s3_bucket = data.aws_s3_object.lambda_packages.bucket
  s3_key    = data.aws_s3_object.lambda_packages.key

  environment {
    variables = {
      SESSIONS_TABLE_NAME = aws_dynamodb_table.sessions.name
      USERS_TABLE_NAME    = aws_dynamodb_table.users.name
      REGION              = "eu-west-2"
      ENVIRONMENT         = var.environment
    }
  }

  tags = {
    Name        = "GCSE SessionLambda"
    Environment = var.environment
    Purpose     = "Session history and management"
  }
}

# GenerateLambda function
resource "aws_lambda_function" "generate_lambda" {
  function_name = "gcse-generate-lambda-${var.environment}"
  role          = aws_iam_role.generate_lambda_role.arn
  handler       = "src.lambda_handlers.generate_lambda.lambda_handler"
  runtime       = "python3.11"
  timeout       = 300 # Increased to 5 minutes for large question sets
  memory_size   = 1024

  s3_bucket = data.aws_s3_object.lambda_packages.bucket
  s3_key    = data.aws_s3_object.lambda_packages.key

  environment {
    variables = {
      BEDROCK_MODEL_ID          = var.bedrock_model_haiku
      SPECIFICATIONS_BUCKET     = var.specifications_bucket_name
      EXAMPLES_BUCKET           = var.examples_bucket_name
      SESSIONS_TABLE_NAME       = aws_dynamodb_table.sessions.name
      TOPIC_COVERAGE_TABLE_NAME = aws_dynamodb_table.topic_coverage.name
      ASYNC_QUEUE_URL           = aws_sqs_queue.async_generation_queue.url
      REGION                    = "eu-west-2"
      ENVIRONMENT               = var.environment
    }
  }

  tags = {
    Name        = "GCSE GenerateLambda"
    Environment = var.environment
    Purpose     = "Question generation using Claude Sonnet"
  }
}

# FeedbackLambda function
resource "aws_lambda_function" "feedback_lambda" {
  function_name = "gcse-feedback-lambda-${var.environment}"
  role          = aws_iam_role.feedback_lambda_role.arn
  handler       = "src.lambda_handlers.feedback_lambda.handler"
  runtime       = "python3.11"
  timeout       = 30
  memory_size   = 512

  s3_bucket = data.aws_s3_object.lambda_packages.bucket
  s3_key    = data.aws_s3_object.lambda_packages.key

  environment {
    variables = {
      QUESTION_FEEDBACK_TABLE = aws_dynamodb_table.question_feedback.name
      QUALITY_SCORES_TABLE    = aws_dynamodb_table.quality_scores.name
      REGION                  = "eu-west-2"
      ENVIRONMENT             = var.environment
    }
  }

  tags = {
    Name        = "GCSE FeedbackLambda"
    Environment = var.environment
    Purpose     = "User feedback collection for AI learning"
  }
}

# RefinementLambda function
resource "aws_lambda_function" "refinement_lambda" {
  function_name = "gcse-refinement-lambda-${var.environment}"
  role          = aws_iam_role.refinement_lambda_role.arn
  handler       = "src.lambda_handlers.refinement_lambda.handler"
  runtime       = "python3.11"
  timeout       = 900 # 15 minutes for processing multiple questions
  memory_size   = 1024

  s3_bucket = data.aws_s3_object.lambda_packages.bucket
  s3_key    = data.aws_s3_object.lambda_packages.key

  environment {
    variables = {
      QUESTION_FEEDBACK_TABLE = aws_dynamodb_table.question_feedback.name
      QUALITY_SCORES_TABLE    = aws_dynamodb_table.quality_scores.name
      QUESTION_BANK_BUCKET    = var.question_bank_bucket_name
      BEDROCK_MODEL_ID        = var.bedrock_model_sonnet
      REGION                  = "eu-west-2"
      ENVIRONMENT             = var.environment
    }
  }

  tags = {
    Name        = "GCSE RefinementLambda"
    Environment = var.environment
    Purpose     = "AI learning and question improvement"
  }
}

# ExportLambda function
resource "aws_lambda_function" "export_lambda" {
  function_name = "gcse-export-lambda-${var.environment}"
  role          = aws_iam_role.export_lambda_role.arn
  handler       = "src.lambda_handlers.export_lambda.handler"
  runtime       = "python3.11"
  timeout       = 300 # 5 minutes for PDF generation
  memory_size   = 512

  s3_bucket = data.aws_s3_object.lambda_packages.bucket
  s3_key    = data.aws_s3_object.lambda_packages.key

  environment {
    variables = {
      SESSIONS_TABLE_NAME = aws_dynamodb_table.sessions.name
      USERS_TABLE_NAME    = aws_dynamodb_table.users.name
      REGION              = "eu-west-2"
      ENVIRONMENT         = var.environment
    }
  }

  tags = {
    Name        = "GCSE ExportLambda"
    Environment = var.environment
    Purpose     = "PDF export functionality"
  }
}

# TopicCoverageLambda function
resource "aws_lambda_function" "topic_coverage_lambda" {
  function_name = "gcse-topic-coverage-lambda-${var.environment}"
  role          = aws_iam_role.topic_coverage_lambda_role.arn
  handler       = "src.lambda_handlers.topic_coverage_lambda.lambda_handler"
  runtime       = "python3.11"
  timeout       = 30
  memory_size   = 512

  s3_bucket = data.aws_s3_object.lambda_packages.bucket
  s3_key    = data.aws_s3_object.lambda_packages.key

  environment {
    variables = {
      TOPIC_COVERAGE_TABLE_NAME = aws_dynamodb_table.topic_coverage.name
      USERS_TABLE_NAME          = aws_dynamodb_table.users.name
      ENVIRONMENT               = var.environment
    }
  }

  tags = {
    Name        = "GCSE TopicCoverageLambda"
    Environment = var.environment
    Purpose     = "Topic coverage tracking and analytics"
  }
}

# AsyncWorkerLambda function for processing SQS messages
resource "aws_lambda_function" "async_worker_lambda" {
  function_name = "gcse-async-worker-lambda-${var.environment}"
  role          = aws_iam_role.async_worker_lambda_role.arn
  handler       = "src.lambda_handlers.async_worker_lambda.lambda_handler"
  runtime       = "python3.11"
  timeout       = 300 # 5 minutes for question generation
  memory_size   = 1024

  s3_bucket = data.aws_s3_object.lambda_packages.bucket
  s3_key    = data.aws_s3_object.lambda_packages.key

  environment {
    variables = {
      BEDROCK_MODEL_ID          = var.bedrock_model_haiku
      SPECIFICATIONS_BUCKET     = var.specifications_bucket_name
      EXAMPLES_BUCKET           = var.examples_bucket_name
      SESSIONS_TABLE_NAME       = aws_dynamodb_table.sessions.name
      TOPIC_COVERAGE_TABLE_NAME = aws_dynamodb_table.topic_coverage.name
      REGION                    = "eu-west-2"
      ENVIRONMENT               = var.environment
    }
  }

  tags = {
    Name        = "GCSE AsyncWorkerLambda"
    Environment = var.environment
    Purpose     = "Background worker for async question generation"
  }
}

# SQS Event Source Mapping for AsyncWorkerLambda
resource "aws_lambda_event_source_mapping" "async_worker_sqs_trigger" {
  event_source_arn = aws_sqs_queue.async_generation_queue.arn
  function_name    = aws_lambda_function.async_worker_lambda.arn
  batch_size       = 1 # Process one job at a time
  enabled          = true

  scaling_config {
    maximum_concurrency = 5 # Allow up to 5 concurrent workers
  }
}

# CloudWatch log groups for Lambda functions
resource "aws_cloudwatch_log_group" "auth_lambda_logs" {
  name              = "/aws/lambda/${aws_lambda_function.auth_lambda.function_name}"
  retention_in_days = 30

  tags = {
    Name        = "AuthLambda Logs"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "session_lambda_logs" {
  name              = "/aws/lambda/${aws_lambda_function.session_lambda.function_name}"
  retention_in_days = 30

  tags = {
    Name        = "SessionLambda Logs"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "interpret_lambda_logs" {
  name              = "/aws/lambda/${aws_lambda_function.interpret_lambda.function_name}"
  retention_in_days = 30

  tags = {
    Name        = "InterpretLambda Logs"
    Environment = var.environment
  }
}
resource "aws_cloudwatch_log_group" "generate_lambda_logs" {
  name              = "/aws/lambda/${aws_lambda_function.generate_lambda.function_name}"
  retention_in_days = 30

  tags = {
    Name        = "GenerateLambda Logs"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "feedback_lambda_logs" {
  name              = "/aws/lambda/${aws_lambda_function.feedback_lambda.function_name}"
  retention_in_days = 30

  tags = {
    Name        = "FeedbackLambda Logs"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "refinement_lambda_logs" {
  name              = "/aws/lambda/${aws_lambda_function.refinement_lambda.function_name}"
  retention_in_days = 30

  tags = {
    Name        = "RefinementLambda Logs"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "export_lambda_logs" {
  name              = "/aws/lambda/${aws_lambda_function.export_lambda.function_name}"
  retention_in_days = 30

  tags = {
    Name        = "ExportLambda Logs"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "topic_coverage_lambda_logs" {
  name              = "/aws/lambda/${aws_lambda_function.topic_coverage_lambda.function_name}"
  retention_in_days = 30

  tags = {
    Name        = "TopicCoverageLambda Logs"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "async_worker_lambda_logs" {
  name              = "/aws/lambda/${aws_lambda_function.async_worker_lambda.function_name}"
  retention_in_days = 30

  tags = {
    Name        = "AsyncWorkerLambda Logs"
    Environment = var.environment
  }
}

# EventBridge rule for RefinementLambda (weekly schedule)
resource "aws_cloudwatch_event_rule" "refinement_schedule" {
  name                = "gcse-refinement-schedule-${var.environment}"
  description         = "Weekly trigger for RefinementLambda - Sundays at 2 AM"
  schedule_expression = "cron(0 2 ? * SUN *)"

  tags = {
    Name        = "RefinementLambda Schedule"
    Environment = var.environment
    Purpose     = "AI learning and question improvement"
  }
}

# EventBridge target for RefinementLambda
resource "aws_cloudwatch_event_target" "refinement_lambda_target" {
  rule      = aws_cloudwatch_event_rule.refinement_schedule.name
  target_id = "RefinementLambdaTarget"
  arn       = aws_lambda_function.refinement_lambda.arn

  input = jsonencode({
    source      = "eventbridge.scheduled"
    detail_type = "Scheduled Event"
    detail = {
      trigger_type = "weekly_refinement"
      schedule     = "cron(0 2 ? * SUN *)"
    }
  })
}

# Lambda permission for EventBridge to invoke RefinementLambda
resource "aws_lambda_permission" "allow_eventbridge_refinement" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.refinement_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.refinement_schedule.arn
}

# SQS Queue for async question generation
resource "aws_sqs_queue" "async_generation_queue" {
  name                       = "gcse-async-generation-queue-${var.environment}"
  visibility_timeout_seconds = 900  # 15 minutes (3x Lambda timeout)
  message_retention_seconds  = 3600 # 1 hour
  receive_wait_time_seconds  = 20   # Long polling

  tags = {
    Name        = "Async Generation Queue"
    Environment = var.environment
    Purpose     = "Queue for large question generation requests"
  }
}

# Dead Letter Queue for async generation failures
resource "aws_sqs_queue" "async_generation_dlq" {
  name                      = "gcse-async-generation-dlq-${var.environment}"
  message_retention_seconds = 1209600 # 14 days

  tags = {
    Name        = "Async Generation DLQ"
    Environment = var.environment
    Purpose     = "Error handling for failed async generation"
  }
}

# Dead Letter Queue for RefinementLambda error handling
resource "aws_sqs_queue" "refinement_dlq" {
  name                      = "gcse-refinement-dlq-${var.environment}"
  message_retention_seconds = 1209600 # 14 days

  tags = {
    Name        = "RefinementLambda DLQ"
    Environment = var.environment
    Purpose     = "Error handling for failed refinement operations"
  }
}

# Update RefinementLambda with DLQ configuration
resource "aws_lambda_function_event_invoke_config" "refinement_lambda_config" {
  function_name = aws_lambda_function.refinement_lambda.function_name

  destination_config {
    on_failure {
      destination = aws_sqs_queue.refinement_dlq.arn
    }
  }

  maximum_retry_attempts = 2
}

# IAM policy for RefinementLambda to send messages to DLQ
resource "aws_iam_role_policy" "refinement_dlq_policy" {
  name = "refinement-dlq-policy"
  role = aws_iam_role.refinement_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage"
        ]
        Resource = aws_sqs_queue.refinement_dlq.arn
      }
    ]
  })
}

# RetrievalLambda function
resource "aws_lambda_function" "retrieval_lambda" {
  function_name = "gcse-retrieval-lambda-${var.environment}"
  role          = aws_iam_role.retrieval_lambda_role.arn
  handler       = "src.lambda_handlers.retrieval_lambda.handler"
  runtime       = "python3.11"
  timeout       = 10 # Fast retrieval - 10 seconds max
  memory_size   = 512

  s3_bucket = data.aws_s3_object.lambda_packages.bucket
  s3_key    = data.aws_s3_object.lambda_packages.key

  environment {
    variables = {
      VERIFIED_QUESTIONS_TABLE = aws_dynamodb_table.verified_question_bank.name
      REGION                   = "eu-west-2"
      ENVIRONMENT              = var.environment
    }
  }

  tags = {
    Name        = "GCSE RetrievalLambda"
    Environment = var.environment
    Purpose     = "Fast question retrieval from verified bank"
  }
}

# IAM role for RetrievalLambda
resource "aws_iam_role" "retrieval_lambda_role" {
  name = "gcse-retrieval-lambda-role-${var.environment}"

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
    Name        = "GCSE RetrievalLambda Role"
    Environment = var.environment
  }
}

# IAM policy for RetrievalLambda
resource "aws_iam_role_policy" "retrieval_lambda_policy" {
  name = "gcse-retrieval-lambda-policy-${var.environment}"
  role = aws_iam_role.retrieval_lambda_role.id

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
          "dynamodb:GetItem",
          "dynamodb:UpdateItem"
        ]
        Resource = [
          aws_dynamodb_table.verified_question_bank.arn,
          "${aws_dynamodb_table.verified_question_bank.arn}/index/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
      }
    ]
  })
}

# Attach basic execution role
resource "aws_iam_role_policy_attachment" "retrieval_lambda_basic_execution" {
  role       = aws_iam_role.retrieval_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}
