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

# CloudWatch Log Groups for Lambda functions (if not already created)
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
      
      # Lambda Performance Metrics
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
          title   = "Lambda Function Performance"
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
            [".", "ErrorRate", "FunctionName", var.generate_lambda_name]
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

      # Lambda Concurrent Executions
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/Lambda", "ConcurrentExecutions", "FunctionName", var.interpret_lambda_name],
            [".", "ConcurrentExecutions", "FunctionName", var.generate_lambda_name]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "eu-west-2"
          title   = "Lambda Concurrent Executions"
          period  = 300
          stat    = "Maximum"
        }
      },

      # S3 Request Metrics
      {
        type   = "metric"
        x      = 0
        y      = 12
        width  = 8
        height = 6

        properties = {
          metrics = [
            ["AWS/S3", "NumberOfObjects", "BucketName", var.specifications_bucket_name, "StorageType", "AllStorageTypes"],
            [".", "BucketSizeBytes", ".", ".", ".", "."],
            ["AWS/S3", "NumberOfObjects", "BucketName", var.examples_bucket_name, "StorageType", "AllStorageTypes"],
            [".", "BucketSizeBytes", ".", ".", ".", "."],
            ["AWS/S3", "NumberOfObjects", "BucketName", var.frontend_bucket_name, "StorageType", "AllStorageTypes"],
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
        y      = 12
        width  = 8
        height = 6

        properties = {
          metrics = [
            ["AWS/S3", "AllRequests", "BucketName", var.specifications_bucket_name],
            [".", "GetRequests", ".", "."],
            [".", "4xxErrors", ".", "."],
            [".", "5xxErrors", ".", "."],
            ["AWS/S3", "AllRequests", "BucketName", var.examples_bucket_name],
            [".", "GetRequests", ".", "."]
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
        y      = 12
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

      # Bedrock Token Usage (via CloudWatch Logs Insights)
      {
        type   = "log"
        x      = 0
        y      = 18
        width  = 24
        height = 6

        properties = {
          query   = "SOURCE '/aws/lambda/${var.interpret_lambda_name}' | SOURCE '/aws/lambda/${var.generate_lambda_name}' | fields @timestamp, @message | filter @message like /token/ | stats count() by bin(5m)"
          region  = "eu-west-2"
          title   = "Bedrock Token Usage (Logs Insights)"
          view    = "table"
        }
      }
    ]
  })
}

# Cost tracking dashboard using CloudWatch metrics
resource "aws_cloudwatch_dashboard" "cost_dashboard" {
  dashboard_name = "GCSE-Cost-Tracking-${var.environment}"

  dashboard_body = jsonencode({
    widgets = [
      # Estimated Daily Costs
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
            [".", ".", ".", ".", ".", "AmazonCloudFront"]
          ]
          view    = "timeSeries"
          stacked = true
          region  = "us-east-1"  # Billing metrics are in us-east-1
          title   = "Estimated Daily Costs by Service (USD)"
          period  = 86400
          stat    = "Maximum"
        }
      },

      # Total Estimated Charges
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
          title   = "Total Estimated Charges (USD)"
          period  = 86400
          stat    = "Maximum"
        }
      }
    ]
  })
}

# CloudWatch alarms for critical issues
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

# Daily cost alarm
resource "aws_cloudwatch_metric_alarm" "daily_cost_alarm" {
  alarm_name          = "gcse-daily-cost-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "EstimatedCharges"
  namespace           = "AWS/Billing"
  period              = "86400"
  statistic           = "Maximum"
  threshold           = var.cost_threshold_daily
  alarm_description   = "Daily cost exceeded £${var.cost_threshold_daily}"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    Currency = "USD"
  }

  tags = {
    Name        = "Daily Cost Alarm"
    Environment = var.environment
  }
}

# Warning alarms
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