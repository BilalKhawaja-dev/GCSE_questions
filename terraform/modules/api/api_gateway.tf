# API Gateway configuration for GCSE Question Generator

# REST API Gateway
resource "aws_api_gateway_rest_api" "gcse_api" {
  name        = "gcse-question-generator-${var.environment}"
  description = "API for GCSE Question Generator - Natural language to exam questions"

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  tags = {
    Name        = "GCSE Question Generator API"
    Environment = var.environment
  }
}

# API Gateway deployment
resource "aws_api_gateway_deployment" "gcse_api_deployment" {
  depends_on = [
    aws_api_gateway_integration.auth_integration,
    aws_api_gateway_integration.interpret_integration,
    aws_api_gateway_integration.generate_integration,
    aws_api_gateway_integration.user_sessions_integration,
    aws_api_gateway_integration.user_session_details_integration,
    aws_api_gateway_integration.user_statistics_integration,
    aws_api_gateway_integration.feedback_integration,
    aws_api_gateway_integration.user_export_integration,
    aws_api_gateway_integration.user_coverage_integration,
    aws_api_gateway_integration.retrieve_questions_integration,
    aws_api_gateway_method.auth_options,
    aws_api_gateway_method.interpret_options,
    aws_api_gateway_method.generate_options,
    aws_api_gateway_method.user_sessions_options,
    aws_api_gateway_method.user_session_details_options,
    aws_api_gateway_method.user_statistics_options,
    aws_api_gateway_method.feedback_options,
    aws_api_gateway_method.user_export_options,
    aws_api_gateway_method.user_coverage_options,
    aws_api_gateway_method.retrieve_questions_options
  ]

  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  stage_name  = var.environment

  # Force redeployment when configuration changes
  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.auth_resource.id,
      aws_api_gateway_resource.interpret_resource.id,
      aws_api_gateway_resource.generate_resource.id,
      aws_api_gateway_resource.user_resource.id,
      aws_api_gateway_resource.user_sessions_resource.id,
      aws_api_gateway_resource.user_session_details_resource.id,
      aws_api_gateway_resource.user_statistics_resource.id,
      aws_api_gateway_resource.user_export_resource.id,
      aws_api_gateway_resource.user_coverage_resource.id,
      aws_api_gateway_resource.feedback_resource.id,
      aws_api_gateway_resource.retrieve_questions_resource.id,
      aws_api_gateway_method.auth_post.id,
      aws_api_gateway_method.interpret_post.id,
      aws_api_gateway_method.generate_post.id,
      aws_api_gateway_method.user_sessions_get.id,
      aws_api_gateway_method.user_session_details_get.id,
      aws_api_gateway_method.user_statistics_get.id,
      aws_api_gateway_method.feedback_post.id,
      aws_api_gateway_method.user_export_post.id,
      aws_api_gateway_method.user_coverage_get.id,
      aws_api_gateway_method.retrieve_questions_post.id,
      aws_api_gateway_integration.auth_integration.id,
      aws_api_gateway_integration.interpret_integration.id,
      aws_api_gateway_integration.generate_integration.id,
      aws_api_gateway_integration.user_sessions_integration.id,
      aws_api_gateway_integration.user_session_details_integration.id,
      aws_api_gateway_integration.user_statistics_integration.id,
      aws_api_gateway_integration.feedback_integration.id,
      aws_api_gateway_integration.user_export_integration.id,
      aws_api_gateway_integration.user_coverage_integration.id,
      aws_api_gateway_integration.retrieve_questions_integration.id,
      aws_api_gateway_authorizer.session_authorizer.id,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Usage plan for rate limiting
resource "aws_api_gateway_usage_plan" "gcse_api_usage_plan" {
  name        = "gcse-api-usage-plan-${var.environment}"
  description = "Usage plan for GCSE Question Generator API"

  api_stages {
    api_id = aws_api_gateway_rest_api.gcse_api.id
    stage  = aws_api_gateway_deployment.gcse_api_deployment.stage_name
  }

  quota_settings {
    limit  = 10000 # 10,000 requests per month
    period = "MONTH"
  }

  throttle_settings {
    rate_limit  = 100 # 100 requests per second
    burst_limit = 200 # 200 burst requests
  }
}

# API key for usage plan
resource "aws_api_gateway_api_key" "gcse_api_key" {
  name        = "gcse-api-key-${var.environment}"
  description = "API key for GCSE Question Generator"
  enabled     = true
}

# Associate API key with usage plan
resource "aws_api_gateway_usage_plan_key" "gcse_api_usage_plan_key" {
  key_id        = aws_api_gateway_api_key.gcse_api_key.id
  key_type      = "API_KEY"
  usage_plan_id = aws_api_gateway_usage_plan.gcse_api_usage_plan.id
}

# /auth resource
resource "aws_api_gateway_resource" "auth_resource" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  parent_id   = aws_api_gateway_rest_api.gcse_api.root_resource_id
  path_part   = "auth"
}

# /interpret resource
resource "aws_api_gateway_resource" "interpret_resource" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  parent_id   = aws_api_gateway_rest_api.gcse_api.root_resource_id
  path_part   = "interpret"
}

# /generate resource
resource "aws_api_gateway_resource" "generate_resource" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  parent_id   = aws_api_gateway_rest_api.gcse_api.root_resource_id
  path_part   = "generate"
}

# /user resource
resource "aws_api_gateway_resource" "user_resource" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  parent_id   = aws_api_gateway_rest_api.gcse_api.root_resource_id
  path_part   = "user"
}

# /user/sessions resource
resource "aws_api_gateway_resource" "user_sessions_resource" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  parent_id   = aws_api_gateway_resource.user_resource.id
  path_part   = "sessions"
}

# /user/sessions/{session_id} resource
resource "aws_api_gateway_resource" "user_session_details_resource" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  parent_id   = aws_api_gateway_resource.user_sessions_resource.id
  path_part   = "{session_id}"
}

# /user/statistics resource
resource "aws_api_gateway_resource" "user_statistics_resource" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  parent_id   = aws_api_gateway_resource.user_resource.id
  path_part   = "statistics"
}

# /user/export resource
resource "aws_api_gateway_resource" "user_export_resource" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  parent_id   = aws_api_gateway_resource.user_resource.id
  path_part   = "export"
}

# /user/coverage resource
resource "aws_api_gateway_resource" "user_coverage_resource" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  parent_id   = aws_api_gateway_resource.user_resource.id
  path_part   = "coverage"
}

# /user/suggestions resource
resource "aws_api_gateway_resource" "user_suggestions_resource" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  parent_id   = aws_api_gateway_resource.user_resource.id
  path_part   = "suggestions"
}

# /feedback resource
resource "aws_api_gateway_resource" "feedback_resource" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  parent_id   = aws_api_gateway_rest_api.gcse_api.root_resource_id
  path_part   = "feedback"
}

# POST method for /auth
resource "aws_api_gateway_method" "auth_post" {
  rest_api_id   = aws_api_gateway_rest_api.gcse_api.id
  resource_id   = aws_api_gateway_resource.auth_resource.id
  http_method   = "POST"
  authorization = "NONE"

  request_validator_id = aws_api_gateway_request_validator.request_validator.id

  request_models = {
    "application/json" = aws_api_gateway_model.auth_request_model.name
  }
}

# Lambda authorizer for authentication
resource "aws_api_gateway_authorizer" "session_authorizer" {
  name                   = "session-authorizer-${var.environment}"
  rest_api_id            = aws_api_gateway_rest_api.gcse_api.id
  authorizer_uri         = aws_lambda_function.auth_lambda.invoke_arn
  authorizer_credentials = aws_iam_role.api_gateway_authorizer_role.arn
  type                   = "REQUEST"
  identity_source        = "method.request.header.Authorization"

  # Cache authorizer results for 5 minutes
  authorizer_result_ttl_in_seconds = 300
}

# IAM role for API Gateway authorizer
resource "aws_iam_role" "api_gateway_authorizer_role" {
  name = "api-gateway-authorizer-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "apigateway.amazonaws.com"
        }
      }
    ]
  })
}

# IAM policy for API Gateway authorizer
resource "aws_iam_role_policy" "api_gateway_authorizer_policy" {
  name = "api-gateway-authorizer-policy-${var.environment}"
  role = aws_iam_role.api_gateway_authorizer_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = aws_lambda_function.auth_lambda.arn
      }
    ]
  })
}

# POST method for /interpret (now requires authentication)
resource "aws_api_gateway_method" "interpret_post" {
  rest_api_id   = aws_api_gateway_rest_api.gcse_api.id
  resource_id   = aws_api_gateway_resource.interpret_resource.id
  http_method   = "POST"
  authorization = "CUSTOM"
  authorizer_id = aws_api_gateway_authorizer.session_authorizer.id

  request_validator_id = aws_api_gateway_request_validator.request_validator.id

  request_models = {
    "application/json" = aws_api_gateway_model.interpret_request_model.name
  }
}

# POST method for /generate (now requires authentication)
resource "aws_api_gateway_method" "generate_post" {
  rest_api_id   = aws_api_gateway_rest_api.gcse_api.id
  resource_id   = aws_api_gateway_resource.generate_resource.id
  http_method   = "POST"
  authorization = "CUSTOM"
  authorizer_id = aws_api_gateway_authorizer.session_authorizer.id

  request_validator_id = aws_api_gateway_request_validator.request_validator.id

  request_models = {
    "application/json" = aws_api_gateway_model.generate_request_model.name
  }
}

# GET method for /user/sessions (no authorizer - Lambda handles auth)
resource "aws_api_gateway_method" "user_sessions_get" {
  rest_api_id   = aws_api_gateway_rest_api.gcse_api.id
  resource_id   = aws_api_gateway_resource.user_sessions_resource.id
  http_method   = "GET"
  authorization = "NONE"
}

# GET method for /user/sessions/{session_id} (no authorizer - Lambda handles auth)
resource "aws_api_gateway_method" "user_session_details_get" {
  rest_api_id   = aws_api_gateway_rest_api.gcse_api.id
  resource_id   = aws_api_gateway_resource.user_session_details_resource.id
  http_method   = "GET"
  authorization = "NONE"
}

# GET method for /user/statistics (requires authentication)
resource "aws_api_gateway_method" "user_statistics_get" {
  rest_api_id   = aws_api_gateway_rest_api.gcse_api.id
  resource_id   = aws_api_gateway_resource.user_statistics_resource.id
  http_method   = "GET"
  authorization = "NONE"
}

# POST method for /feedback (requires authentication)
resource "aws_api_gateway_method" "feedback_post" {
  rest_api_id   = aws_api_gateway_rest_api.gcse_api.id
  resource_id   = aws_api_gateway_resource.feedback_resource.id
  http_method   = "POST"
  authorization = "CUSTOM"
  authorizer_id = aws_api_gateway_authorizer.session_authorizer.id

  request_validator_id = aws_api_gateway_request_validator.request_validator.id

  request_models = {
    "application/json" = aws_api_gateway_model.feedback_request_model.name
  }
}

# POST method for /user/export (requires authentication)
resource "aws_api_gateway_method" "user_export_post" {
  rest_api_id   = aws_api_gateway_rest_api.gcse_api.id
  resource_id   = aws_api_gateway_resource.user_export_resource.id
  http_method   = "POST"
  authorization = "CUSTOM"
  authorizer_id = aws_api_gateway_authorizer.session_authorizer.id

  request_validator_id = aws_api_gateway_request_validator.request_validator.id

  request_models = {
    "application/json" = aws_api_gateway_model.export_request_model.name
  }
}

# GET method for /user/coverage (requires authentication)
resource "aws_api_gateway_method" "user_coverage_get" {
  rest_api_id   = aws_api_gateway_rest_api.gcse_api.id
  resource_id   = aws_api_gateway_resource.user_coverage_resource.id
  http_method   = "GET"
  authorization = "NONE"
}

# GET method for /user/suggestions (requires authentication)
resource "aws_api_gateway_method" "user_suggestions_get" {
  rest_api_id   = aws_api_gateway_rest_api.gcse_api.id
  resource_id   = aws_api_gateway_resource.user_suggestions_resource.id
  http_method   = "GET"
  authorization = "NONE"
}

# OPTIONS method for /auth (CORS)
resource "aws_api_gateway_method" "auth_options" {
  rest_api_id   = aws_api_gateway_rest_api.gcse_api.id
  resource_id   = aws_api_gateway_resource.auth_resource.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

# OPTIONS method for /interpret (CORS)
resource "aws_api_gateway_method" "interpret_options" {
  rest_api_id   = aws_api_gateway_rest_api.gcse_api.id
  resource_id   = aws_api_gateway_resource.interpret_resource.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

# OPTIONS method for /generate (CORS)
resource "aws_api_gateway_method" "generate_options" {
  rest_api_id   = aws_api_gateway_rest_api.gcse_api.id
  resource_id   = aws_api_gateway_resource.generate_resource.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

# OPTIONS method for /user/sessions (CORS)
resource "aws_api_gateway_method" "user_sessions_options" {
  rest_api_id   = aws_api_gateway_rest_api.gcse_api.id
  resource_id   = aws_api_gateway_resource.user_sessions_resource.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

# OPTIONS method for /user/sessions/{session_id} (CORS)
resource "aws_api_gateway_method" "user_session_details_options" {
  rest_api_id   = aws_api_gateway_rest_api.gcse_api.id
  resource_id   = aws_api_gateway_resource.user_session_details_resource.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

# OPTIONS method for /user/statistics (CORS)
resource "aws_api_gateway_method" "user_statistics_options" {
  rest_api_id   = aws_api_gateway_rest_api.gcse_api.id
  resource_id   = aws_api_gateway_resource.user_statistics_resource.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

# OPTIONS method for /feedback (CORS)
resource "aws_api_gateway_method" "feedback_options" {
  rest_api_id   = aws_api_gateway_rest_api.gcse_api.id
  resource_id   = aws_api_gateway_resource.feedback_resource.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

# OPTIONS method for /user/export (CORS)
resource "aws_api_gateway_method" "user_export_options" {
  rest_api_id   = aws_api_gateway_rest_api.gcse_api.id
  resource_id   = aws_api_gateway_resource.user_export_resource.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

# OPTIONS method for /user/coverage (CORS)
resource "aws_api_gateway_method" "user_coverage_options" {
  rest_api_id   = aws_api_gateway_rest_api.gcse_api.id
  resource_id   = aws_api_gateway_resource.user_coverage_resource.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

# Lambda integration for /auth
resource "aws_api_gateway_integration" "auth_integration" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.auth_resource.id
  http_method = aws_api_gateway_method.auth_post.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.auth_lambda.invoke_arn
}

# Lambda integration for /interpret
resource "aws_api_gateway_integration" "interpret_integration" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.interpret_resource.id
  http_method = aws_api_gateway_method.interpret_post.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.interpret_lambda.invoke_arn
}

# Lambda integration for /generate
resource "aws_api_gateway_integration" "generate_integration" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.generate_resource.id
  http_method = aws_api_gateway_method.generate_post.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.generate_lambda.invoke_arn
}

# Lambda integration for /user/sessions
resource "aws_api_gateway_integration" "user_sessions_integration" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.user_sessions_resource.id
  http_method = aws_api_gateway_method.user_sessions_get.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.session_lambda.invoke_arn
}

# Lambda integration for /user/sessions/{session_id}
resource "aws_api_gateway_integration" "user_session_details_integration" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.user_session_details_resource.id
  http_method = aws_api_gateway_method.user_session_details_get.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.session_lambda.invoke_arn
}

# Lambda integration for /user/statistics
resource "aws_api_gateway_integration" "user_statistics_integration" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.user_statistics_resource.id
  http_method = aws_api_gateway_method.user_statistics_get.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.session_lambda.invoke_arn
}

# Lambda integration for /feedback
resource "aws_api_gateway_integration" "feedback_integration" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.feedback_resource.id
  http_method = aws_api_gateway_method.feedback_post.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.feedback_lambda.invoke_arn
}

# Lambda integration for /user/export
resource "aws_api_gateway_integration" "user_export_integration" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.user_export_resource.id
  http_method = aws_api_gateway_method.user_export_post.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.export_lambda.invoke_arn
}

# Lambda integration for /user/coverage
resource "aws_api_gateway_integration" "user_coverage_integration" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.user_coverage_resource.id
  http_method = aws_api_gateway_method.user_coverage_get.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.topic_coverage_lambda.invoke_arn
}

# Lambda integration for /user/suggestions
resource "aws_api_gateway_integration" "user_suggestions_integration" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.user_suggestions_resource.id
  http_method = aws_api_gateway_method.user_suggestions_get.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.topic_coverage_lambda.invoke_arn
}

# OPTIONS method for /user/suggestions (CORS)
resource "aws_api_gateway_method" "user_suggestions_options" {
  rest_api_id   = aws_api_gateway_rest_api.gcse_api.id
  resource_id   = aws_api_gateway_resource.user_suggestions_resource.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

# CORS integration for /user/suggestions OPTIONS
resource "aws_api_gateway_integration" "user_suggestions_options_integration" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.user_suggestions_resource.id
  http_method = aws_api_gateway_method.user_suggestions_options.http_method

  type = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

# Method response for /user/suggestions OPTIONS
resource "aws_api_gateway_method_response" "user_suggestions_options_response" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.user_suggestions_resource.id
  http_method = aws_api_gateway_method.user_suggestions_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers"     = true
    "method.response.header.Access-Control-Allow-Methods"     = true
    "method.response.header.Access-Control-Allow-Origin"      = true
    "method.response.header.Access-Control-Allow-Credentials" = true
  }
}

# Integration response for /user/suggestions OPTIONS
resource "aws_api_gateway_integration_response" "user_suggestions_options_integration_response" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.user_suggestions_resource.id
  http_method = aws_api_gateway_method.user_suggestions_options.http_method
  status_code = aws_api_gateway_method_response.user_suggestions_options_response.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers"     = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Session-Token'"
    "method.response.header.Access-Control-Allow-Methods"     = "'GET,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"      = var.environment == "prod" ? "'https://d2ckebo851nz2l.cloudfront.net'" : "'http://localhost:3000,https://localhost:3000'"
    "method.response.header.Access-Control-Allow-Credentials" = "'true'"
  }
}

# CORS integration for /auth OPTIONS
resource "aws_api_gateway_integration" "auth_options_integration" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.auth_resource.id
  http_method = aws_api_gateway_method.auth_options.http_method

  type = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

# CORS integration for /interpret OPTIONS
resource "aws_api_gateway_integration" "interpret_options_integration" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.interpret_resource.id
  http_method = aws_api_gateway_method.interpret_options.http_method

  type = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

# CORS integration for /generate OPTIONS
resource "aws_api_gateway_integration" "generate_options_integration" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.generate_resource.id
  http_method = aws_api_gateway_method.generate_options.http_method

  type = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

# CORS integration for /user/sessions OPTIONS
resource "aws_api_gateway_integration" "user_sessions_options_integration" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.user_sessions_resource.id
  http_method = aws_api_gateway_method.user_sessions_options.http_method

  type = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

# CORS integration for /user/sessions/{session_id} OPTIONS
resource "aws_api_gateway_integration" "user_session_details_options_integration" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.user_session_details_resource.id
  http_method = aws_api_gateway_method.user_session_details_options.http_method

  type = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

# CORS integration for /user/statistics OPTIONS
resource "aws_api_gateway_integration" "user_statistics_options_integration" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.user_statistics_resource.id
  http_method = aws_api_gateway_method.user_statistics_options.http_method

  type = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

# CORS integration for /feedback OPTIONS
resource "aws_api_gateway_integration" "feedback_options_integration" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.feedback_resource.id
  http_method = aws_api_gateway_method.feedback_options.http_method

  type = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

# CORS integration for /user/export OPTIONS
resource "aws_api_gateway_integration" "user_export_options_integration" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.user_export_resource.id
  http_method = aws_api_gateway_method.user_export_options.http_method

  type = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

# CORS integration for /user/coverage OPTIONS
resource "aws_api_gateway_integration" "user_coverage_options_integration" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.user_coverage_resource.id
  http_method = aws_api_gateway_method.user_coverage_options.http_method

  type = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

# Method responses for CORS
resource "aws_api_gateway_method_response" "auth_options_response" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.auth_resource.id
  http_method = aws_api_gateway_method.auth_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers"     = true
    "method.response.header.Access-Control-Allow-Methods"     = true
    "method.response.header.Access-Control-Allow-Origin"      = true
    "method.response.header.Access-Control-Allow-Credentials" = true
  }
}

resource "aws_api_gateway_method_response" "interpret_options_response" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.interpret_resource.id
  http_method = aws_api_gateway_method.interpret_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers"     = true
    "method.response.header.Access-Control-Allow-Methods"     = true
    "method.response.header.Access-Control-Allow-Origin"      = true
    "method.response.header.Access-Control-Allow-Credentials" = true
  }
}

resource "aws_api_gateway_method_response" "generate_options_response" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.generate_resource.id
  http_method = aws_api_gateway_method.generate_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers"     = true
    "method.response.header.Access-Control-Allow-Methods"     = true
    "method.response.header.Access-Control-Allow-Origin"      = true
    "method.response.header.Access-Control-Allow-Credentials" = true
  }
}

# Integration responses for CORS
resource "aws_api_gateway_integration_response" "auth_options_integration_response" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.auth_resource.id
  http_method = aws_api_gateway_method.auth_options.http_method
  status_code = aws_api_gateway_method_response.auth_options_response.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers"     = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Session-Token'"
    "method.response.header.Access-Control-Allow-Methods"     = "'POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"      = var.environment == "prod" ? "'https://d2ckebo851nz2l.cloudfront.net'" : "'http://localhost:3000,https://localhost:3000'"
    "method.response.header.Access-Control-Allow-Credentials" = "'true'"
  }
}

resource "aws_api_gateway_integration_response" "interpret_options_integration_response" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.interpret_resource.id
  http_method = aws_api_gateway_method.interpret_options.http_method
  status_code = aws_api_gateway_method_response.interpret_options_response.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers"     = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Session-Token'"
    "method.response.header.Access-Control-Allow-Methods"     = "'POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"      = var.environment == "prod" ? "'https://d2ckebo851nz2l.cloudfront.net'" : "'http://localhost:3000,https://localhost:3000'"
    "method.response.header.Access-Control-Allow-Credentials" = "'true'"
  }
}

resource "aws_api_gateway_integration_response" "generate_options_integration_response" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.generate_resource.id
  http_method = aws_api_gateway_method.generate_options.http_method
  status_code = aws_api_gateway_method_response.generate_options_response.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers"     = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Session-Token'"
    "method.response.header.Access-Control-Allow-Methods"     = "'POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"      = var.environment == "prod" ? "'https://d2ckebo851nz2l.cloudfront.net'" : "'http://localhost:3000,https://localhost:3000'"
    "method.response.header.Access-Control-Allow-Credentials" = "'true'"
  }
}

# Method responses for session endpoints CORS
resource "aws_api_gateway_method_response" "user_sessions_options_response" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.user_sessions_resource.id
  http_method = aws_api_gateway_method.user_sessions_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers"     = true
    "method.response.header.Access-Control-Allow-Methods"     = true
    "method.response.header.Access-Control-Allow-Origin"      = true
    "method.response.header.Access-Control-Allow-Credentials" = true
  }
}

resource "aws_api_gateway_method_response" "user_session_details_options_response" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.user_session_details_resource.id
  http_method = aws_api_gateway_method.user_session_details_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers"     = true
    "method.response.header.Access-Control-Allow-Methods"     = true
    "method.response.header.Access-Control-Allow-Origin"      = true
    "method.response.header.Access-Control-Allow-Credentials" = true
  }
}

resource "aws_api_gateway_method_response" "user_statistics_options_response" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.user_statistics_resource.id
  http_method = aws_api_gateway_method.user_statistics_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers"     = true
    "method.response.header.Access-Control-Allow-Methods"     = true
    "method.response.header.Access-Control-Allow-Origin"      = true
    "method.response.header.Access-Control-Allow-Credentials" = true
  }
}

resource "aws_api_gateway_method_response" "feedback_options_response" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.feedback_resource.id
  http_method = aws_api_gateway_method.feedback_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers"     = true
    "method.response.header.Access-Control-Allow-Methods"     = true
    "method.response.header.Access-Control-Allow-Origin"      = true
    "method.response.header.Access-Control-Allow-Credentials" = true
  }
}

resource "aws_api_gateway_method_response" "user_export_options_response" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.user_export_resource.id
  http_method = aws_api_gateway_method.user_export_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers"     = true
    "method.response.header.Access-Control-Allow-Methods"     = true
    "method.response.header.Access-Control-Allow-Origin"      = true
    "method.response.header.Access-Control-Allow-Credentials" = true
  }
}

resource "aws_api_gateway_method_response" "user_coverage_options_response" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.user_coverage_resource.id
  http_method = aws_api_gateway_method.user_coverage_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers"     = true
    "method.response.header.Access-Control-Allow-Methods"     = true
    "method.response.header.Access-Control-Allow-Origin"      = true
    "method.response.header.Access-Control-Allow-Credentials" = true
  }
}

# Integration responses for session endpoints CORS
resource "aws_api_gateway_integration_response" "user_sessions_options_integration_response" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.user_sessions_resource.id
  http_method = aws_api_gateway_method.user_sessions_options.http_method
  status_code = aws_api_gateway_method_response.user_sessions_options_response.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers"     = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Session-Token'"
    "method.response.header.Access-Control-Allow-Methods"     = "'GET,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"      = var.environment == "prod" ? "'https://d2ckebo851nz2l.cloudfront.net'" : "'http://localhost:3000,https://localhost:3000'"
    "method.response.header.Access-Control-Allow-Credentials" = "'true'"
  }
}

resource "aws_api_gateway_integration_response" "user_session_details_options_integration_response" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.user_session_details_resource.id
  http_method = aws_api_gateway_method.user_session_details_options.http_method
  status_code = aws_api_gateway_method_response.user_session_details_options_response.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers"     = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Session-Token'"
    "method.response.header.Access-Control-Allow-Methods"     = "'GET,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"      = var.environment == "prod" ? "'https://d2ckebo851nz2l.cloudfront.net'" : "'http://localhost:3000,https://localhost:3000'"
    "method.response.header.Access-Control-Allow-Credentials" = "'true'"
  }
}

resource "aws_api_gateway_integration_response" "user_statistics_options_integration_response" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.user_statistics_resource.id
  http_method = aws_api_gateway_method.user_statistics_options.http_method
  status_code = aws_api_gateway_method_response.user_statistics_options_response.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers"     = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Session-Token'"
    "method.response.header.Access-Control-Allow-Methods"     = "'GET,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"      = var.environment == "prod" ? "'https://d2ckebo851nz2l.cloudfront.net'" : "'http://localhost:3000,https://localhost:3000'"
    "method.response.header.Access-Control-Allow-Credentials" = "'true'"
  }
}

resource "aws_api_gateway_integration_response" "feedback_options_integration_response" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.feedback_resource.id
  http_method = aws_api_gateway_method.feedback_options.http_method
  status_code = aws_api_gateway_method_response.feedback_options_response.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers"     = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Session-Token'"
    "method.response.header.Access-Control-Allow-Methods"     = "'POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"      = var.environment == "prod" ? "'https://d2ckebo851nz2l.cloudfront.net'" : "'http://localhost:3000,https://localhost:3000'"
    "method.response.header.Access-Control-Allow-Credentials" = "'true'"
  }
}

resource "aws_api_gateway_integration_response" "user_export_options_integration_response" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.user_export_resource.id
  http_method = aws_api_gateway_method.user_export_options.http_method
  status_code = aws_api_gateway_method_response.user_export_options_response.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers"     = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Session-Token'"
    "method.response.header.Access-Control-Allow-Methods"     = "'POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"      = var.environment == "prod" ? "'https://d2ckebo851nz2l.cloudfront.net'" : "'http://localhost:3000,https://localhost:3000'"
    "method.response.header.Access-Control-Allow-Credentials" = "'true'"
  }
}

resource "aws_api_gateway_integration_response" "user_coverage_options_integration_response" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.user_coverage_resource.id
  http_method = aws_api_gateway_method.user_coverage_options.http_method
  status_code = aws_api_gateway_method_response.user_coverage_options_response.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers"     = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Session-Token'"
    "method.response.header.Access-Control-Allow-Methods"     = "'GET,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"      = var.environment == "prod" ? "'https://d2ckebo851nz2l.cloudfront.net'" : "'http://localhost:3000,https://localhost:3000'"
    "method.response.header.Access-Control-Allow-Credentials" = "'true'"
  }
}

# Request validator
resource "aws_api_gateway_request_validator" "request_validator" {
  name                        = "request-validator-${var.environment}"
  rest_api_id                 = aws_api_gateway_rest_api.gcse_api.id
  validate_request_body       = true
  validate_request_parameters = true
}

# Request models for validation
resource "aws_api_gateway_model" "auth_request_model" {
  rest_api_id  = aws_api_gateway_rest_api.gcse_api.id
  name         = "AuthRequest"
  content_type = "application/json"

  schema = jsonencode({
    "$schema" = "http://json-schema.org/draft-04/schema#"
    title     = "Auth Request Schema"
    type      = "object"
    properties = {
      action = {
        type = "string"
        enum = ["register", "login", "validate"]
      }
      username = {
        type      = "string"
        minLength = 3
        maxLength = 50
      }
      password = {
        type      = "string"
        minLength = 8
        maxLength = 128
      }
      email = {
        type   = "string"
        format = "email"
      }
      school = {
        type      = "string"
        maxLength = 100
      }
      subject_specialization = {
        type      = "string"
        maxLength = 50
      }
      session_token = {
        type = "string"
      }
    }
    required = ["action"]
  })
}

resource "aws_api_gateway_model" "interpret_request_model" {
  rest_api_id  = aws_api_gateway_rest_api.gcse_api.id
  name         = "InterpretRequest"
  content_type = "application/json"

  schema = jsonencode({
    "$schema" = "http://json-schema.org/draft-04/schema#"
    title     = "Interpret Request Schema"
    type      = "object"
    properties = {
      query = {
        type      = "string"
        minLength = 1
        maxLength = 500
      }
      count = {
        type    = "integer"
        minimum = 1
        maximum = 100
      }
      tier = {
        type = "string"
        enum = ["foundation", "higher"]
      }
      topic = {
        type = "string"
      }
    }
    required = ["query"]
  })
}

resource "aws_api_gateway_model" "generate_request_model" {
  rest_api_id  = aws_api_gateway_rest_api.gcse_api.id
  name         = "GenerateRequest"
  content_type = "application/json"

  schema = jsonencode({
    "$schema" = "http://json-schema.org/draft-04/schema#"
    title     = "Generate Request Schema"
    type      = "object"
    properties = {
      topic = {
        type      = "string"
        minLength = 1
      }
      tier = {
        type = "string"
        enum = ["Foundation", "Higher", "foundation", "higher"]
      }
      count = {
        type    = "integer"
        minimum = 1
        maximum = 100
      }
      specification_version = {
        type    = "string"
        default = "latest"
      }
      subtopic = {
        type = "string"
      }
      difficulty_min = {
        type    = "integer"
        minimum = 1
        maximum = 10
      }
      difficulty_max = {
        type    = "integer"
        minimum = 1
        maximum = 10
      }
    }
    required = ["topic", "tier", "count"]
  })
}

resource "aws_api_gateway_model" "feedback_request_model" {
  rest_api_id  = aws_api_gateway_rest_api.gcse_api.id
  name         = "FeedbackRequest"
  content_type = "application/json"

  schema = jsonencode({
    "$schema" = "http://json-schema.org/draft-04/schema#"
    title     = "Feedback Request Schema"
    type      = "object"
    properties = {
      question_id = {
        type      = "string"
        minLength = 1
      }
      helpful = {
        type = "boolean"
      }
      difficulty_rating = {
        type    = "integer"
        minimum = 1
        maximum = 10
      }
      comments = {
        type      = "string"
        maxLength = 500
      }
    }
    required = ["question_id", "helpful"]
  })
}

resource "aws_api_gateway_model" "export_request_model" {
  rest_api_id  = aws_api_gateway_rest_api.gcse_api.id
  name         = "ExportRequest"
  content_type = "application/json"

  schema = jsonencode({
    "$schema" = "http://json-schema.org/draft-04/schema#"
    title     = "Export Request Schema"
    type      = "object"
    properties = {
      session_id = {
        type      = "string"
        minLength = 1
      }
      format = {
        type    = "string"
        enum    = ["pdf"]
        default = "pdf"
      }
    }
    required = ["session_id"]
  })
}

# Lambda permissions for API Gateway
resource "aws_lambda_permission" "auth_lambda_permission" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.auth_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.gcse_api.execution_arn}/*/*"
}

resource "aws_lambda_permission" "auth_lambda_authorizer_permission" {
  statement_id  = "AllowExecutionFromAPIGatewayAuthorizer"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.auth_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.gcse_api.execution_arn}/authorizers/${aws_api_gateway_authorizer.session_authorizer.id}"
}

resource "aws_lambda_permission" "interpret_lambda_permission" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.interpret_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.gcse_api.execution_arn}/*/*"
}

resource "aws_lambda_permission" "generate_lambda_permission" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.generate_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.gcse_api.execution_arn}/*/*"
}

# Lambda permissions for SessionLambda
resource "aws_lambda_permission" "session_lambda_permission" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.session_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.gcse_api.execution_arn}/*/*"
}

# Lambda permissions for FeedbackLambda
resource "aws_lambda_permission" "feedback_lambda_permission" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.feedback_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.gcse_api.execution_arn}/*/*"
}

# Lambda permissions for ExportLambda
resource "aws_lambda_permission" "export_lambda_permission" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.export_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.gcse_api.execution_arn}/*/*"
}

# Lambda permissions for TopicCoverageLambda
resource "aws_lambda_permission" "topic_coverage_lambda_permission" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.topic_coverage_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.gcse_api.execution_arn}/*/*"
}

# /retrieve-questions resource
resource "aws_api_gateway_resource" "retrieve_questions_resource" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  parent_id   = aws_api_gateway_rest_api.gcse_api.root_resource_id
  path_part   = "retrieve-questions"
}

# POST method for /retrieve-questions (requires authentication)
resource "aws_api_gateway_method" "retrieve_questions_post" {
  rest_api_id   = aws_api_gateway_rest_api.gcse_api.id
  resource_id   = aws_api_gateway_resource.retrieve_questions_resource.id
  http_method   = "POST"
  authorization = "CUSTOM"
  authorizer_id = aws_api_gateway_authorizer.session_authorizer.id

  request_validator_id = aws_api_gateway_request_validator.request_validator.id

  request_models = {
    "application/json" = aws_api_gateway_model.retrieve_request_model.name
  }
}

# OPTIONS method for /retrieve-questions (CORS)
resource "aws_api_gateway_method" "retrieve_questions_options" {
  rest_api_id   = aws_api_gateway_rest_api.gcse_api.id
  resource_id   = aws_api_gateway_resource.retrieve_questions_resource.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

# Lambda integration for /retrieve-questions
resource "aws_api_gateway_integration" "retrieve_questions_integration" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.retrieve_questions_resource.id
  http_method = aws_api_gateway_method.retrieve_questions_post.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.retrieval_lambda.invoke_arn
}

# CORS integration for /retrieve-questions OPTIONS
resource "aws_api_gateway_integration" "retrieve_questions_options_integration" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.retrieve_questions_resource.id
  http_method = aws_api_gateway_method.retrieve_questions_options.http_method

  type = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

# Method response for /retrieve-questions OPTIONS
resource "aws_api_gateway_method_response" "retrieve_questions_options_response" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.retrieve_questions_resource.id
  http_method = aws_api_gateway_method.retrieve_questions_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers"     = true
    "method.response.header.Access-Control-Allow-Methods"     = true
    "method.response.header.Access-Control-Allow-Origin"      = true
    "method.response.header.Access-Control-Allow-Credentials" = true
  }
}

# Integration response for /retrieve-questions OPTIONS
resource "aws_api_gateway_integration_response" "retrieve_questions_options_integration_response" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.retrieve_questions_resource.id
  http_method = aws_api_gateway_method.retrieve_questions_options.http_method
  status_code = aws_api_gateway_method_response.retrieve_questions_options_response.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers"     = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Session-Token'"
    "method.response.header.Access-Control-Allow-Methods"     = "'POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"      = var.environment == "prod" ? "'https://d2ckebo851nz2l.cloudfront.net'" : "'http://localhost:3000,https://localhost:3000'"
    "method.response.header.Access-Control-Allow-Credentials" = "'true'"
  }
}

# Request model for retrieve-questions
resource "aws_api_gateway_model" "retrieve_request_model" {
  rest_api_id  = aws_api_gateway_rest_api.gcse_api.id
  name         = "RetrieveRequest"
  content_type = "application/json"

  schema = jsonencode({
    "$schema" = "http://json-schema.org/draft-04/schema#"
    title     = "Retrieve Request Schema"
    type      = "object"
    properties = {
      topic = {
        type      = "string"
        minLength = 1
      }
      grade = {
        type = "string"
        enum = ["foundation", "higher"]
      }
      paper_type = {
        type = "string"
        enum = ["P1", "P2", "P3"]
      }
      difficulty_min = {
        type    = "integer"
        minimum = 1
        maximum = 10
        default = 1
      }
      difficulty_max = {
        type    = "integer"
        minimum = 1
        maximum = 10
        default = 10
      }
      exclude_question_ids = {
        type = "array"
        items = {
          type = "string"
        }
        default = []
      }
      count = {
        type    = "integer"
        minimum = 1
        maximum = 20
        default = 5
      }
    }
    required = ["topic", "grade", "paper_type"]
  })
}

# Lambda permission for retrieval lambda
resource "aws_lambda_permission" "retrieval_lambda_permission" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.retrieval_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.gcse_api.execution_arn}/*/*"
}
