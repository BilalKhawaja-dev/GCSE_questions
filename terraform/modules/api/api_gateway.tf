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
    aws_api_gateway_integration.interpret_integration,
    aws_api_gateway_integration.generate_integration,
    aws_api_gateway_method.interpret_options,
    aws_api_gateway_method.generate_options
  ]

  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  stage_name  = var.environment

  # Force redeployment when configuration changes
  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.interpret_resource.id,
      aws_api_gateway_resource.generate_resource.id,
      aws_api_gateway_method.interpret_post.id,
      aws_api_gateway_method.generate_post.id,
      aws_api_gateway_integration.interpret_integration.id,
      aws_api_gateway_integration.generate_integration.id,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }
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

# POST method for /interpret
resource "aws_api_gateway_method" "interpret_post" {
  rest_api_id   = aws_api_gateway_rest_api.gcse_api.id
  resource_id   = aws_api_gateway_resource.interpret_resource.id
  http_method   = "POST"
  authorization = "NONE"

  request_validator_id = aws_api_gateway_request_validator.request_validator.id
  
  request_models = {
    "application/json" = aws_api_gateway_model.interpret_request_model.name
  }
}

# POST method for /generate
resource "aws_api_gateway_method" "generate_post" {
  rest_api_id   = aws_api_gateway_rest_api.gcse_api.id
  resource_id   = aws_api_gateway_resource.generate_resource.id
  http_method   = "POST"
  authorization = "NONE"

  request_validator_id = aws_api_gateway_request_validator.request_validator.id
  
  request_models = {
    "application/json" = aws_api_gateway_model.generate_request_model.name
  }
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

# Lambda integration for /interpret
resource "aws_api_gateway_integration" "interpret_integration" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.interpret_resource.id
  http_method = aws_api_gateway_method.interpret_post.http_method

  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.interpret_lambda.invoke_arn
}

# Lambda integration for /generate
resource "aws_api_gateway_integration" "generate_integration" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.generate_resource.id
  http_method = aws_api_gateway_method.generate_post.http_method

  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.generate_lambda.invoke_arn
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

# Method responses for CORS
resource "aws_api_gateway_method_response" "interpret_options_response" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.interpret_resource.id
  http_method = aws_api_gateway_method.interpret_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_method_response" "generate_options_response" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.generate_resource.id
  http_method = aws_api_gateway_method.generate_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

# Integration responses for CORS
resource "aws_api_gateway_integration_response" "interpret_options_integration_response" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.interpret_resource.id
  http_method = aws_api_gateway_method.interpret_options.http_method
  status_code = aws_api_gateway_method_response.interpret_options_response.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

resource "aws_api_gateway_integration_response" "generate_options_integration_response" {
  rest_api_id = aws_api_gateway_rest_api.gcse_api.id
  resource_id = aws_api_gateway_resource.generate_resource.id
  http_method = aws_api_gateway_method.generate_options.http_method
  status_code = aws_api_gateway_method_response.generate_options_response.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
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
        type = "string"
        minLength = 1
      }
      tier = {
        type = "string"
        enum = ["Foundation", "Higher"]
      }
      count = {
        type    = "integer"
        minimum = 1
        maximum = 50
      }
      specification_version = {
        type    = "string"
        default = "latest"
      }
    }
    required = ["topic", "tier", "count"]
  })
}

# Lambda permissions for API Gateway
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