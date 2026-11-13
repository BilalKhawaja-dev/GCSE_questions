# Upload endpoint for PDF/content uploads

# /upload resource
resource "aws_api_gateway_resource" "upload_resource" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  parent_id   = aws_api_gateway_rest_api.gcse_api.root_resource_id
  path_part   = "upload"
}

# /upload/presigned resource
resource "aws_api_gateway_resource" "upload_presigned_resource" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  parent_id   = aws_api_gateway_resource.upload_resource.id
  path_part   = "presigned"
}

# POST method for /upload/presigned
resource "aws_api_gateway_method" "upload_presigned_post" {
  rest_api_id   = aws_api_gateway_rest_api.gcse_api.id
  resource_id   = aws_api_gateway_resource.upload_presigned_resource.id
  http_method   = "POST"
  authorization = "NONE"
}

# OPTIONS method for /upload/presigned (CORS)
resource "aws_api_gateway_method" "upload_presigned_options" {
  rest_api_id   = aws_api_gateway_rest_api.gcse_api.id
  resource_id   = aws_api_gateway_resource.upload_presigned_resource.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

# Lambda integration for /upload/presigned
resource "aws_api_gateway_integration" "upload_presigned_integration" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.upload_presigned_resource.id
  http_method = aws_api_gateway_method.upload_presigned_post.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.upload_lambda.invoke_arn
}

# CORS integration for /upload/presigned OPTIONS
resource "aws_api_gateway_integration" "upload_presigned_options_integration" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.upload_presigned_resource.id
  http_method = aws_api_gateway_method.upload_presigned_options.http_method

  type = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

# Method response for /upload/presigned OPTIONS
resource "aws_api_gateway_method_response" "upload_presigned_options_response" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.upload_presigned_resource.id
  http_method = aws_api_gateway_method.upload_presigned_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers"     = true
    "method.response.header.Access-Control-Allow-Methods"     = true
    "method.response.header.Access-Control-Allow-Origin"      = true
    "method.response.header.Access-Control-Allow-Credentials" = true
  }
}

# Integration response for /upload/presigned OPTIONS
resource "aws_api_gateway_integration_response" "upload_presigned_options_integration_response" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.upload_presigned_resource.id
  http_method = aws_api_gateway_method.upload_presigned_options.http_method
  status_code = aws_api_gateway_method_response.upload_presigned_options_response.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers"     = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods"     = "'POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"      = var.environment == "prod" ? "'https://d2ckebo851nz2l.cloudfront.net'" : "'*'"
    "method.response.header.Access-Control-Allow-Credentials" = "'true'"
  }
}

# IAM role for UploadLambda
resource "aws_iam_role" "upload_lambda_role" {
  name = "gcse-upload-lambda-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })

  tags = {
    Name        = "GCSE Upload Lambda Role"
    Environment = var.environment
  }
}

# Attach basic Lambda execution policy
resource "aws_iam_role_policy_attachment" "upload_lambda_basic" {
  role       = aws_iam_role.upload_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# IAM policy for S3 access
resource "aws_iam_role_policy" "upload_lambda_s3_policy" {
  name = "upload-lambda-s3-policy"
  role = aws_iam_role.upload_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${var.specifications_bucket_name}/*",
          "arn:aws:s3:::${var.specifications_bucket_name}",
          "arn:aws:s3:::${var.examples_bucket_name}/*",
          "arn:aws:s3:::${var.examples_bucket_name}"
        ]
      }
    ]
  })
}

# Lambda function for upload
resource "aws_lambda_function" "upload_lambda" {
  filename      = "${path.root}/lambda-package/lambda-functions.zip"
  function_name = "gcse-upload-lambda-${var.environment}"
  role          = aws_iam_role.upload_lambda_role.arn
  handler       = "src.lambda_handlers.upload_lambda.lambda_handler"
  runtime       = "python3.11"
  timeout       = 30
  memory_size   = 512

  environment {
    variables = {
      ENVIRONMENT           = var.environment
      REGION                = var.aws_region
      SPECIFICATIONS_BUCKET = var.specifications_bucket_name
      EXAMPLES_BUCKET       = var.examples_bucket_name
    }
  }

  tags = {
    Name        = "GCSE Upload Lambda"
    Environment = var.environment
  }
}

# Lambda permission for API Gateway to invoke upload lambda
resource "aws_lambda_permission" "upload_lambda_permission" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.upload_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.gcse_api.execution_arn}/*/*"
}
