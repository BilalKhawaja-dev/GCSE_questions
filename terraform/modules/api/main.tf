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

# Basic Lambda execution policy for InterpretLambda
resource "aws_iam_role_policy_attachment" "interpret_lambda_basic" {
  role       = aws_iam_role.interpret_lambda_role.name
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

# Bedrock policy for GenerateLambda (Sonnet only)
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
        Resource = "arn:aws:bedrock:eu-west-2::foundation-model/${var.bedrock_model_sonnet}"
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
  role         = aws_iam_role.interpret_lambda_role.arn
  handler      = "src.lambda_handlers.interpret_lambda.lambda_handler"
  runtime      = "python3.11"
  timeout      = 30
  memory_size  = 512

  s3_bucket = data.aws_s3_object.lambda_packages.bucket
  s3_key    = data.aws_s3_object.lambda_packages.key

  environment {
    variables = {
      BEDROCK_MODEL_ID = var.bedrock_model_haiku
      REGION           = "eu-west-2"
      ENVIRONMENT      = var.environment
    }
  }

  tags = {
    Name        = "GCSE InterpretLambda"
    Environment = var.environment
    Purpose     = "Query interpretation using Claude Haiku"
  }
}

# GenerateLambda function
resource "aws_lambda_function" "generate_lambda" {
  function_name = "gcse-generate-lambda-${var.environment}"
  role         = aws_iam_role.generate_lambda_role.arn
  handler      = "src.lambda_handlers.generate_lambda.lambda_handler"
  runtime      = "python3.11"
  timeout      = 60
  memory_size  = 1024

  s3_bucket = data.aws_s3_object.lambda_packages.bucket
  s3_key    = data.aws_s3_object.lambda_packages.key

  environment {
    variables = {
      BEDROCK_MODEL_ID         = var.bedrock_model_sonnet
      SPECIFICATIONS_BUCKET    = var.specifications_bucket_name
      EXAMPLES_BUCKET         = var.examples_bucket_name
      REGION                  = "eu-west-2"
      ENVIRONMENT             = var.environment
    }
  }

  tags = {
    Name        = "GCSE GenerateLambda"
    Environment = var.environment
    Purpose     = "Question generation using Claude Sonnet"
  }
}

# CloudWatch log groups for Lambda functions
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