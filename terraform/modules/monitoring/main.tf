# Monitoring module - CloudWatch dashboards, alarms, and SNS notifications

# SNS topic for alerts
resource "aws_sns_topic" "alerts" {
  name = "gcse-alerts-${var.environment}"
  
  tags = {
    Name        = "GCSE Alerts"
    Environment = var.environment
  }
}

# SNS topic subscription for email alerts
resource "aws_sns_topic_subscription" "email_alerts" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# CloudWatch Log Groups for all Lambda functions
resource "aws_cloudwatch_log_group" "interpret_lambda_logs" {
  name              = "/aws/lambda/${var.interpret_lambda_name}"
  retention_in_days = 30

  tags = {
    Name        = "InterpretLambda Logs"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "generate_lambda_logs" {
  name              = "/aws/lambda/${var.generate_lambda_name}"
  retention_in_days = 30

  tags = {
    Name        = "GenerateLambda Logs"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "auth_lambda_logs" {
  name              = "/aws/lambda/${var.auth_lambda_name}"
  retention_in_days = 30

  tags = {
    Name        = "AuthLambda Logs"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "feedback_lambda_logs" {
  name              = "/aws/lambda/${var.feedback_lambda_name}"
  retention_in_days = 30

  tags = {
    Name        = "FeedbackLambda Logs"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "refinement_lambda_logs" {
  name              = "/aws/lambda/${var.refinement_lambda_name}"
  retention_in_days = 30

  tags = {
    Name        = "RefinementLambda Logs"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "session_lambda_logs" {
  name              = "/aws/lambda/${var.session_lambda_name}"
  retention_in_days = 30

  tags = {
    Name        = "SessionLambda Logs"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "export_lambda_logs" {
  name              = "/aws/lambda/${var.export_lambda_name}"
  retention_in_days = 30

  tags = {
    Name        = "ExportLambda Logs"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "topic_coverage_lambda_logs" {
  name              = "/aws/lambda/${var.topic_coverage_lambda_name}"
  retention_in_days = 30

  tags = {
    Name        = "TopicCoverageLambda Logs"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "cost_monitoring_lambda_logs" {
  count             = var.cost_monitoring_lambda_name != "" ? 1 : 0
  name              = "/aws/lambda/${var.cost_monitoring_lambda_name}"
  retention_in_days = 30

  tags = {
    Name        = "CostMonitoringLambda Logs"
    Environment = var.environment
  }
}

# CloudWatch dashboard with comprehensive metrics
resource "aws_cloudwatch_dashboard" "gcse_dashboard" {
  dashboard_name = "GCSE-Question-Generator-${var.environment}"

  dashboard_body = jsonencode({
    widgets = [
      # API Gateway Metrics
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/ApiGateway", "Count", "ApiName", var.api_gateway_name],
            [".", "4XXError", ".", "."],
            [".", "5XXError", ".", "."],
            [".", "Latency", ".", "."],
            [".", "IntegrationLatency", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "eu-west-2"
          title   = "API Gateway Metrics"
          period  = 300
          stat    = "Average"
          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },
      
      # Lambda Performance Metrics - Core Functions
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/Lambda", "Invocations", "FunctionName", var.interpret_lambda_name],
            [".", "Errors", ".", "."],
            [".", "Duration", ".", "."],
            [".", "Throttles", ".", "."],
            ["AWS/Lambda", "Invocations", "FunctionName", var.generate_lambda_name],
            [".", "Errors", ".", "."],
            [".", "Duration", ".", "."],
            [".", "Throttles", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "eu-west-2"
          title   = "Core Lambda Functions Performance"
          period  = 300
          stat    = "Average"
        }
      },

      # Lambda Performance Metrics - User Management Functions
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/Lambda", "Invocations", "FunctionName", var.auth_lambda_name],
            [".", "Errors", ".", "."],
            [".", "Duration", ".", "."],
            ["AWS/Lambda", "Invocations", "FunctionName", var.session_lambda_name],
            [".", "Errors", ".", "."],
            [".", "Duration", ".", "."],
            ["AWS/Lambda", "Invocations", "FunctionName", var.feedback_lambda_name],
            [".", "Errors", ".", "."],
            [".", "Duration", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "eu-west-2"
          title   = "User Management Lambda Functions"
          period  = 300
          stat    = "Average"
        }
      },

      # Lambda Performance Metrics - Additional Functions
      {
        type   = "metric"
        x      = 0
        y      = 12
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/Lambda", "Invocations", "FunctionName", var.export_lambda_name],
            [".", "Errors", ".", "."],
            [".", "Duration", ".", "."],
            ["AWS/Lambda", "Invocations", "FunctionName", var.topic_coverage_lambda_name],
            [".", "Errors", ".", "."],
            [".", "Duration", ".", "."],
            ["AWS/Lambda", "Invocations", "FunctionName", var.refinement_lambda_name],
            [".", "Errors", ".", "."],
            [".", "Duration", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "eu-west-2"
          title   = "Additional Lambda Functions"
          period  = 300
          stat    = "Average"
        }
      },

      # Lambda Error Rates
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/Lambda", "ErrorRate", "FunctionName", var.interpret_lambda_name],
            [".", "ErrorRate", "FunctionName", var.generate_lambda_name],
            [".", "ErrorRate", "FunctionName", var.auth_lambda_name],
            [".", "ErrorRate", "FunctionName", var.feedback_lambda_name]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "eu-west-2"
          title   = "Lambda Error Rates (%)"
          period  = 300
          stat    = "Average"
          yAxis = {
            left = {
              min = 0
              max = 100
            }
          }
        }
      },

      # Custom Metrics - Question Generation Success Rates
      {
        type   = "metric"
        x      = 12
        y      = 12
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["GCSE/QuestionGeneration", "SuccessRate", "Function", "GenerateLambda"],
            [".", "QuestionsGenerated", ".", "."],
            [".", "AverageQuality", ".", "."],
            ["GCSE/QuestionGeneration", "SuccessRate", "Function", "InterpretLambda"],
            [".", "QueriesParsed", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "eu-west-2"
          title   = "Question Generation Success Metrics"
          period  = 300
          stat    = "Average"
        }
      },

      # Lambda Concurrent Executions
      {
        type   = "metric"
        x      = 0
        y      = 18
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/Lambda", "ConcurrentExecutions", "FunctionName", var.interpret_lambda_name],
            [".", "ConcurrentExecutions", "FunctionName", var.generate_lambda_name],
            [".", "ConcurrentExecutions", "FunctionName", var.auth_lambda_name],
            [".", "ConcurrentExecutions", "FunctionName", var.feedback_lambda_name]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "eu-west-2"
          title   = "Lambda Concurrent Executions"
          period  = 300
          stat    = "Maximum"
        }
      },

      # DynamoDB Metrics
      {
        type   = "metric"
        x      = 12
        y      = 18
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", "${var.environment}-users"],
            [".", "ConsumedWriteCapacityUnits", ".", "."],
            ["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", "${var.environment}-sessions"],
            [".", "ConsumedWriteCapacityUnits", ".", "."],
            ["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", "${var.environment}-question-feedback"],
            [".", "ConsumedWriteCapacityUnits", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "eu-west-2"
          title   = "DynamoDB Capacity Usage"
          period  = 300
          stat    = "Sum"
        }
      },

      # S3 Request Metrics
      {
        type   = "metric"
        x      = 0
        y      = 24
        width  = 8
        height = 6

        properties = {
          metrics = [
            ["AWS/S3", "NumberOfObjects", "BucketName", var.specifications_bucket_name, "StorageType", "AllStorageTypes"],
            [".", "BucketSizeBytes", ".", ".", ".", "."],
            ["AWS/S3", "NumberOfObjects", "BucketName", var.examples_bucket_name, "StorageType", "AllStorageTypes"],
            [".", "BucketSizeBytes", ".", ".", ".", "."],
            ["AWS/S3", "NumberOfObjects", "BucketName", var.frontend_bucket_name, "StorageType", "AllStorageTypes"],
            [".", "BucketSizeBytes", ".", ".", ".", "."],
            ["AWS/S3", "NumberOfObjects", "BucketName", var.question_bank_bucket_name, "StorageType", "AllStorageTypes"],
            [".", "BucketSizeBytes", ".", ".", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "eu-west-2"
          title   = "S3 Storage Metrics"
          period  = 86400
          stat    = "Average"
        }
      },

      # S3 Request Performance
      {
        type   = "metric"
        x      = 8
        y      = 24
        width  = 8
        height = 6

        properties = {
          metrics = [
            ["AWS/S3", "AllRequests", "BucketName", var.specifications_bucket_name],
            [".", "GetRequests", ".", "."],
            [".", "4xxErrors", ".", "."],
            [".", "5xxErrors", ".", "."],
            ["AWS/S3", "AllRequests", "BucketName", var.examples_bucket_name],
            [".", "GetRequests", ".", "."],
            ["AWS/S3", "AllRequests", "BucketName", var.question_bank_bucket_name],
            [".", "PutRequests", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "eu-west-2"
          title   = "S3 Request Performance"
          period  = 300
          stat    = "Sum"
        }
      },

      # CloudFront Metrics
      {
        type   = "metric"
        x      = 16
        y      = 24
        width  = 8
        height = 6

        properties = {
          metrics = [
            ["AWS/CloudFront", "Requests", "DistributionId", var.cloudfront_distribution_id],
            [".", "BytesDownloaded", ".", "."],
            [".", "4xxErrorRate", ".", "."],
            [".", "5xxErrorRate", ".", "."],
            [".", "CacheHitRate", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "us-east-1"  # CloudFront metrics are in us-east-1
          title   = "CloudFront Performance"
          period  = 300
          stat    = "Average"
        }
      },

      # Bedrock Token Usage and Performance
      {
        type   = "log"
        x      = 0
        y      = 30
        width  = 12
        height = 6

        properties = {
          query   = "SOURCE '/aws/lambda/${var.interpret_lambda_name}' | SOURCE '/aws/lambda/${var.generate_lambda_name}' | SOURCE '/aws/lambda/${var.refinement_lambda_name}' | fields @timestamp, @message | filter @message like /bedrock/ or @message like /token/ | stats count() by bin(5m)"
          region  = "eu-west-2"
          title   = "Bedrock API Usage (Logs Insights)"
          view    = "table"
        }
      },

      # X-Ray Tracing Metrics
      {
        type   = "metric"
        x      = 12
        y      = 30
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/X-Ray", "TracesReceived"],
            [".", "TracesProcessed"],
            [".", "ResponseTime", "ServiceName", "gcse-question-generator"],
            [".", "ErrorRate", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "eu-west-2"
          title   = "X-Ray Distributed Tracing"
          period  = 300
          stat    = "Average"
        }
      },

      # Custom Business Metrics
      {
        type   = "metric"
        x      = 0
        y      = 36
        width  = 24
        height = 6

        properties = {
          metrics = [
            ["GCSE/UserActivity", "ActiveUsers", "Period", "Daily"],
            [".", "QuestionsGenerated", ".", "."],
            [".", "SessionsCreated", ".", "."],
            ["GCSE/Quality", "AverageRating", "Component", "Questions"],
            [".", "FeedbackCount", ".", "."],
            ["GCSE/Performance", "ResponseTime", "Endpoint", "Generate"],
            [".", "ResponseTime", "Endpoint", "Interpret"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "eu-west-2"
          title   = "Business and Performance Metrics"
          period  = 300
          stat    = "Average"
        }
      }
    ]
  })
}

# Enhanced cost tracking dashboard with Bedrock focus
resource "aws_cloudwatch_dashboard" "cost_dashboard" {
  dashboard_name = "GCSE-Cost-Tracking-${var.environment}"

  dashboard_body = jsonencode({
    widgets = [
      # Estimated Daily Costs by Service
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/Billing", "EstimatedCharges", "Currency", "USD", "ServiceName", "AmazonBedrock"],
            [".", ".", ".", ".", ".", "AmazonS3"],
            [".", ".", ".", ".", ".", "AWSLambda"],
            [".", ".", ".", ".", ".", "AmazonApiGateway"],
            [".", ".", ".", ".", ".", "AmazonCloudFront"],
            [".", ".", ".", ".", ".", "AmazonDynamoDB"]
          ]
          view    = "timeSeries"
          stacked = true
          region  = "us-east-1"  # Billing metrics are in us-east-1
          title   = "Estimated Daily Costs by Service (USD)"
          period  = 86400
          stat    = "Maximum"
        }
      },

      # Total Estimated Charges with Threshold
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/Billing", "EstimatedCharges", "Currency", "USD"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "us-east-1"
          title   = "Total Estimated Charges (USD) - Target: $40/month"
          period  = 86400
          stat    = "Maximum"
          annotations = {
            horizontal = [
              {
                label = "Daily Target ($1.33)"
                value = 1.33
              },
              {
                label = "Warning ($1.60)"
                value = 1.60
              }
            ]
          }
        }
      },

      # Bedrock Usage Breakdown
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["GCSE/Bedrock", "TokensUsed", "Model", "Claude-Haiku"],
            [".", "TokensUsed", "Model", "Claude-Sonnet"],
            [".", "RequestCount", "Model", "Claude-Haiku"],
            [".", "RequestCount", "Model", "Claude-Sonnet"],
            [".", "EstimatedCost", "Model", "Claude-Haiku"],
            [".", "EstimatedCost", "Model", "Claude-Sonnet"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "eu-west-2"
          title   = "Bedrock Usage and Cost Breakdown"
          period  = 3600
          stat    = "Sum"
        }
      },

      # DynamoDB Cost Tracking
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", "${var.environment}-users"],
            [".", "ConsumedWriteCapacityUnits", ".", "."],
            ["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", "${var.environment}-sessions"],
            [".", "ConsumedWriteCapacityUnits", ".", "."],
            ["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", "${var.environment}-question-feedback"],
            [".", "ConsumedWriteCapacityUnits", ".", "."]
          ]
          view    = "timeSeries"
          stacked = true
          region  = "eu-west-2"
          title   = "DynamoDB Capacity Usage (Cost Impact)"
          period  = 3600
          stat    = "Sum"
        }
      },

      # Cost Efficiency Metrics
      {
        type   = "metric"
        x      = 0
        y      = 12
        width  = 24
        height = 6

        properties = {
          metrics = [
            ["GCSE/CostEfficiency", "CostPerQuestion", "Service", "Total"],
            [".", "CostPerUser", ".", "."],
            [".", "CostPerSession", ".", "."],
            ["GCSE/Usage", "QuestionsPerDollar"],
            [".", "UsersPerDollar"],
            [".", "SessionsPerDollar"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "eu-west-2"
          title   = "Cost Efficiency Metrics"
          period  = 86400
          stat    = "Average"
        }
      }
    ]
  })
}

# CloudWatch alarms for all Lambda functions
resource "aws_cloudwatch_metric_alarm" "lambda_error_rate_interpret" {
  alarm_name          = "gcse-interpret-lambda-error-rate-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "InterpretLambda error rate > 5%"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = var.interpret_lambda_name
  }

  tags = {
    Name        = "InterpretLambda Error Rate Alarm"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_metric_alarm" "lambda_error_rate_generate" {
  alarm_name          = "gcse-generate-lambda-error-rate-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "GenerateLambda error rate > 5%"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = var.generate_lambda_name
  }

  tags = {
    Name        = "GenerateLambda Error Rate Alarm"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_metric_alarm" "lambda_error_rate_auth" {
  alarm_name          = "gcse-auth-lambda-error-rate-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "3"
  alarm_description   = "AuthLambda error rate > 3%"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = var.auth_lambda_name
  }

  tags = {
    Name        = "AuthLambda Error Rate Alarm"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_metric_alarm" "lambda_error_rate_feedback" {
  alarm_name          = "gcse-feedback-lambda-error-rate-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "3"
  alarm_description   = "FeedbackLambda error rate > 3%"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = var.feedback_lambda_name
  }

  tags = {
    Name        = "FeedbackLambda Error Rate Alarm"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_metric_alarm" "lambda_error_rate_refinement" {
  alarm_name          = "gcse-refinement-lambda-error-rate-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "RefinementLambda failed execution"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = var.refinement_lambda_name
  }

  tags = {
    Name        = "RefinementLambda Error Alarm"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_metric_alarm" "api_gateway_5xx_errors" {
  alarm_name          = "gcse-api-5xx-errors-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "5XXError"
  namespace           = "AWS/ApiGateway"
  period              = "300"
  statistic           = "Sum"
  threshold           = "1"
  alarm_description   = "API Gateway 5xx error rate > 1%"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]

  dimensions = {
    ApiName = var.api_gateway_name
  }

  tags = {
    Name        = "API Gateway 5xx Errors"
    Environment = var.environment
  }
}

# S3 unavailable alarm
resource "aws_cloudwatch_metric_alarm" "s3_unavailable" {
  alarm_name          = "gcse-s3-unavailable-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "5xxErrors"
  namespace           = "AWS/S3"
  period              = "60"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "S3 service unavailable"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]

  dimensions = {
    BucketName = var.specifications_bucket_name
  }

  tags = {
    Name        = "S3 Unavailable Alarm"
    Environment = var.environment
  }
}

# Enhanced cost monitoring alarms
resource "aws_cloudwatch_metric_alarm" "daily_cost_alarm" {
  alarm_name          = "gcse-daily-cost-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "EstimatedCharges"
  namespace           = "AWS/Billing"
  period              = "86400"
  statistic           = "Maximum"
  threshold           = var.cost_threshold_daily
  alarm_description   = "Daily cost exceeded $${var.cost_threshold_daily} (£${var.cost_threshold_daily * 0.8})"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    Currency = "USD"
  }

  tags = {
    Name        = "Daily Cost Alarm"
    Environment = var.environment
  }
}

# Bedrock-specific cost alarm
resource "aws_cloudwatch_metric_alarm" "bedrock_daily_cost_alarm" {
  alarm_name          = "gcse-bedrock-daily-cost-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "EstimatedCharges"
  namespace           = "AWS/Billing"
  period              = "86400"
  statistic           = "Maximum"
  threshold           = 0.75  # $0.75 per day for Bedrock (£18/month target)
  alarm_description   = "Bedrock daily cost exceeded $0.75"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    Currency    = "USD"
    ServiceName = "AmazonBedrock"
  }

  tags = {
    Name        = "Bedrock Daily Cost Alarm"
    Environment = var.environment
  }
}

# DynamoDB cost alarm
resource "aws_cloudwatch_metric_alarm" "dynamodb_daily_cost_alarm" {
  alarm_name          = "gcse-dynamodb-daily-cost-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "EstimatedCharges"
  namespace           = "AWS/Billing"
  period              = "86400"
  statistic           = "Maximum"
  threshold           = 0.50  # $0.50 per day for DynamoDB
  alarm_description   = "DynamoDB daily cost exceeded $0.50"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    Currency    = "USD"
    ServiceName = "AmazonDynamoDB"
  }

  tags = {
    Name        = "DynamoDB Daily Cost Alarm"
    Environment = var.environment
  }
}

# Performance monitoring alarms
resource "aws_cloudwatch_metric_alarm" "lambda_duration_warning_interpret" {
  alarm_name          = "gcse-interpret-duration-warning-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Average"
  threshold           = "25000"  # 25 seconds (approaching 30s timeout)
  alarm_description   = "InterpretLambda duration approaching timeout"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = var.interpret_lambda_name
  }

  tags = {
    Name        = "InterpretLambda Duration Warning"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_metric_alarm" "lambda_duration_warning_generate" {
  alarm_name          = "gcse-generate-duration-warning-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Average"
  threshold           = "50000"  # 50 seconds (approaching 60s timeout)
  alarm_description   = "GenerateLambda duration approaching timeout"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = var.generate_lambda_name
  }

  tags = {
    Name        = "GenerateLambda Duration Warning"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_metric_alarm" "lambda_duration_warning_auth" {
  alarm_name          = "gcse-auth-duration-warning-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Average"
  threshold           = "5000"  # 5 seconds for auth operations
  alarm_description   = "AuthLambda duration > 5 seconds"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = var.auth_lambda_name
  }

  tags = {
    Name        = "AuthLambda Duration Warning"
    Environment = var.environment
  }
}

# Question generation success rate alarm
resource "aws_cloudwatch_metric_alarm" "question_generation_success_rate" {
  alarm_name          = "gcse-question-success-rate-${var.environment}"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "SuccessRate"
  namespace           = "GCSE/QuestionGeneration"
  period              = "300"
  statistic           = "Average"
  threshold           = "90"  # 90% success rate
  alarm_description   = "Question generation success rate < 90%"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    Function = "GenerateLambda"
  }

  tags = {
    Name        = "Question Generation Success Rate"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_metric_alarm" "api_gateway_latency_warning" {
  alarm_name          = "gcse-api-latency-warning-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Latency"
  namespace           = "AWS/ApiGateway"
  period              = "300"
  statistic           = "Average"
  threshold           = "10000"  # 10 seconds
  alarm_description   = "API Gateway latency > 10 seconds"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    ApiName = var.api_gateway_name
  }

  tags = {
    Name        = "API Gateway Latency Warning"
    Environment = var.environment
  }
}

# Bedrock throttling alarm
resource "aws_cloudwatch_metric_alarm" "bedrock_throttling" {
  alarm_name          = "gcse-bedrock-throttling-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "Throttles"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "Bedrock throttling detected"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = var.generate_lambda_name
  }

  tags = {
    Name        = "Bedrock Throttling Warning"
    Environment = var.environment
  }
}

# Monthly cost warning alarm
resource "aws_cloudwatch_metric_alarm" "monthly_cost_warning" {
  alarm_name          = "gcse-monthly-cost-warning-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "EstimatedCharges"
  namespace           = "AWS/Billing"
  period              = "86400"
  statistic           = "Maximum"
  threshold           = var.cost_threshold_monthly * 0.8  # 80% of monthly threshold
  alarm_description   = "Monthly cost approaching limit (80% of £${var.cost_threshold_monthly})"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    Currency = "USD"
  }

  tags = {
    Name        = "Monthly Cost Warning"
    Environment = var.environment
  }
}

# DynamoDB Auto-Scaling Configuration
resource "aws_appautoscaling_target" "users_table_read" {
  count              = var.enable_dynamodb_autoscaling ? 1 : 0
  max_capacity       = var.dynamodb_max_read_capacity
  min_capacity       = var.dynamodb_min_read_capacity
  resource_id        = "table/gcse-generator-v2-users-${var.environment}"
  scalable_dimension = "dynamodb:table:ReadCapacityUnits"
  service_namespace  = "dynamodb"

  tags = {
    Name        = "Users Table Read Scaling"
    Environment = var.environment
  }
}

resource "aws_appautoscaling_target" "users_table_write" {
  count              = var.enable_dynamodb_autoscaling ? 1 : 0
  max_capacity       = var.dynamodb_max_write_capacity
  min_capacity       = var.dynamodb_min_write_capacity
  resource_id        = "table/gcse-generator-v2-users-${var.environment}"
  scalable_dimension = "dynamodb:table:WriteCapacityUnits"
  service_namespace  = "dynamodb"

  tags = {
    Name        = "Users Table Write Scaling"
    Environment = var.environment
  }
}

resource "aws_appautoscaling_target" "sessions_table_read" {
  count              = var.enable_dynamodb_autoscaling ? 1 : 0
  max_capacity       = var.dynamodb_max_read_capacity * 2  # Sessions table needs more capacity
  min_capacity       = var.dynamodb_min_read_capacity
  resource_id        = "table/gcse-generator-v2-sessions-${var.environment}"
  scalable_dimension = "dynamodb:table:ReadCapacityUnits"
  service_namespace  = "dynamodb"

  tags = {
    Name        = "Sessions Table Read Scaling"
    Environment = var.environment
  }
}

resource "aws_appautoscaling_target" "sessions_table_write" {
  count              = var.enable_dynamodb_autoscaling ? 1 : 0
  max_capacity       = var.dynamodb_max_write_capacity * 2  # Sessions table needs more capacity
  min_capacity       = var.dynamodb_min_write_capacity
  resource_id        = "table/gcse-generator-v2-sessions-${var.environment}"
  scalable_dimension = "dynamodb:table:WriteCapacityUnits"
  service_namespace  = "dynamodb"

  tags = {
    Name        = "Sessions Table Write Scaling"
    Environment = var.environment
  }
}

resource "aws_appautoscaling_target" "feedback_table_read" {
  count              = var.enable_dynamodb_autoscaling ? 1 : 0
  max_capacity       = var.dynamodb_max_read_capacity
  min_capacity       = var.dynamodb_min_read_capacity
  resource_id        = "table/gcse-generator-v2-question-feedback-${var.environment}"
  scalable_dimension = "dynamodb:table:ReadCapacityUnits"
  service_namespace  = "dynamodb"

  tags = {
    Name        = "Feedback Table Read Scaling"
    Environment = var.environment
  }
}

resource "aws_appautoscaling_target" "feedback_table_write" {
  count              = var.enable_dynamodb_autoscaling ? 1 : 0
  max_capacity       = var.dynamodb_max_write_capacity
  min_capacity       = var.dynamodb_min_write_capacity
  resource_id        = "table/gcse-generator-v2-question-feedback-${var.environment}"
  scalable_dimension = "dynamodb:table:WriteCapacityUnits"
  service_namespace  = "dynamodb"

  tags = {
    Name        = "Feedback Table Write Scaling"
    Environment = var.environment
  }
}

# Auto-Scaling Policies
resource "aws_appautoscaling_policy" "users_table_read_policy" {
  count              = var.enable_dynamodb_autoscaling ? 1 : 0
  name               = "DynamoDBReadCapacityUtilization:${aws_appautoscaling_target.users_table_read[0].resource_id}"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.users_table_read[0].resource_id
  scalable_dimension = aws_appautoscaling_target.users_table_read[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.users_table_read[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "DynamoDBReadCapacityUtilization"
    }
    target_value       = var.dynamodb_target_utilization
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

resource "aws_appautoscaling_policy" "users_table_write_policy" {
  count              = var.enable_dynamodb_autoscaling ? 1 : 0
  name               = "DynamoDBWriteCapacityUtilization:${aws_appautoscaling_target.users_table_write[0].resource_id}"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.users_table_write[0].resource_id
  scalable_dimension = aws_appautoscaling_target.users_table_write[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.users_table_write[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "DynamoDBWriteCapacityUtilization"
    }
    target_value       = var.dynamodb_target_utilization
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

resource "aws_appautoscaling_policy" "sessions_table_read_policy" {
  count              = var.enable_dynamodb_autoscaling ? 1 : 0
  name               = "DynamoDBReadCapacityUtilization:${aws_appautoscaling_target.sessions_table_read[0].resource_id}"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.sessions_table_read[0].resource_id
  scalable_dimension = aws_appautoscaling_target.sessions_table_read[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.sessions_table_read[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "DynamoDBReadCapacityUtilization"
    }
    target_value       = var.dynamodb_target_utilization
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

resource "aws_appautoscaling_policy" "sessions_table_write_policy" {
  count              = var.enable_dynamodb_autoscaling ? 1 : 0
  name               = "DynamoDBWriteCapacityUtilization:${aws_appautoscaling_target.sessions_table_write[0].resource_id}"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.sessions_table_write[0].resource_id
  scalable_dimension = aws_appautoscaling_target.sessions_table_write[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.sessions_table_write[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "DynamoDBWriteCapacityUtilization"
    }
    target_value       = var.dynamodb_target_utilization
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

resource "aws_appautoscaling_policy" "feedback_table_read_policy" {
  count              = var.enable_dynamodb_autoscaling ? 1 : 0
  name               = "DynamoDBReadCapacityUtilization:${aws_appautoscaling_target.feedback_table_read[0].resource_id}"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.feedback_table_read[0].resource_id
  scalable_dimension = aws_appautoscaling_target.feedback_table_read[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.feedback_table_read[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "DynamoDBReadCapacityUtilization"
    }
    target_value       = var.dynamodb_target_utilization
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

resource "aws_appautoscaling_policy" "feedback_table_write_policy" {
  count              = var.enable_dynamodb_autoscaling ? 1 : 0
  name               = "DynamoDBWriteCapacityUtilization:${aws_appautoscaling_target.feedback_table_write[0].resource_id}"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.feedback_table_write[0].resource_id
  scalable_dimension = aws_appautoscaling_target.feedback_table_write[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.feedback_table_write[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "DynamoDBWriteCapacityUtilization"
    }
    target_value       = var.dynamodb_target_utilization
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

# Auto-Scaling Monitoring Alarms
resource "aws_cloudwatch_metric_alarm" "dynamodb_scaling_alarm" {
  count               = var.enable_dynamodb_autoscaling ? 1 : 0
  alarm_name          = "gcse-dynamodb-scaling-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ConsumedReadCapacityUnits"
  namespace           = "AWS/DynamoDB"
  period              = "300"
  statistic           = "Sum"
  threshold           = var.dynamodb_max_read_capacity * 0.8  # 80% of max capacity
  alarm_description   = "DynamoDB scaling approaching maximum capacity"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    TableName = "${var.environment}-sessions"
  }

  tags = {
    Name        = "DynamoDB Scaling Alarm"
    Environment = var.environment
  }
}

# Additional V2 Monitoring Alarms

# Topic Coverage Lambda Error Alarm
resource "aws_cloudwatch_metric_alarm" "lambda_error_rate_topic_coverage" {
  alarm_name          = "gcse-topic-coverage-lambda-error-rate-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "3"
  alarm_description   = "TopicCoverageLambda error rate > 3%"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = var.topic_coverage_lambda_name
  }

  tags = {
    Name        = "TopicCoverageLambda Error Rate Alarm"
    Environment = var.environment
  }
}

# Export Lambda Error Alarm
resource "aws_cloudwatch_metric_alarm" "lambda_error_rate_export" {
  alarm_name          = "gcse-export-lambda-error-rate-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "3"
  alarm_description   = "ExportLambda error rate > 3%"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = var.export_lambda_name
  }

  tags = {
    Name        = "ExportLambda Error Rate Alarm"
    Environment = var.environment
  }
}

# Session Lambda Error Alarm
resource "aws_cloudwatch_metric_alarm" "lambda_error_rate_session" {
  alarm_name          = "gcse-session-lambda-error-rate-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "3"
  alarm_description   = "SessionLambda error rate > 3%"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = var.session_lambda_name
  }

  tags = {
    Name        = "SessionLambda Error Rate Alarm"
    Environment = var.environment
  }
}

# User Registration Rate Alarm (detect unusual activity)
resource "aws_cloudwatch_metric_alarm" "user_registration_spike" {
  alarm_name          = "gcse-user-registration-spike-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "Invocations"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "50"  # More than 50 registrations in 5 minutes
  alarm_description   = "Unusual user registration activity detected"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = var.auth_lambda_name
  }

  tags = {
    Name        = "User Registration Spike Alarm"
    Environment = var.environment
  }
}

# Question Generation Quality Alarm
resource "aws_cloudwatch_metric_alarm" "question_quality_degradation" {
  alarm_name          = "gcse-question-quality-degradation-${var.environment}"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "3"
  metric_name         = "AverageQuality"
  namespace           = "GCSE/Quality"
  period              = "900"  # 15 minutes
  statistic           = "Average"
  threshold           = "0.7"  # Quality score below 70%
  alarm_description   = "Question quality has degraded below acceptable threshold"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    Component = "Questions"
  }

  tags = {
    Name        = "Question Quality Degradation Alarm"
    Environment = var.environment
  }
}

# DynamoDB Throttling Alarm
resource "aws_cloudwatch_metric_alarm" "dynamodb_throttling" {
  alarm_name          = "gcse-dynamodb-throttling-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "ThrottledRequests"
  namespace           = "AWS/DynamoDB"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "DynamoDB requests are being throttled"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    TableName = "${var.environment}-sessions"
  }

  tags = {
    Name        = "DynamoDB Throttling Alarm"
    Environment = var.environment
  }
}

# API Gateway 4xx Error Rate Alarm
resource "aws_cloudwatch_metric_alarm" "api_gateway_4xx_errors" {
  alarm_name          = "gcse-api-4xx-errors-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "4XXError"
  namespace           = "AWS/ApiGateway"
  period              = "300"
  statistic           = "Sum"
  threshold           = "20"  # More than 20 4xx errors in 5 minutes
  alarm_description   = "High rate of API Gateway 4xx errors"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    ApiName = var.api_gateway_name
  }

  tags = {
    Name        = "API Gateway 4xx Errors"
    Environment = var.environment
  }
}

# Lambda Cold Start Alarm
resource "aws_cloudwatch_metric_alarm" "lambda_cold_starts" {
  alarm_name          = "gcse-lambda-cold-starts-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Maximum"
  threshold           = "15000"  # 15 seconds indicates cold starts
  alarm_description   = "High Lambda cold start times detected"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = var.generate_lambda_name
  }

  tags = {
    Name        = "Lambda Cold Start Alarm"
    Environment = var.environment
  }
}