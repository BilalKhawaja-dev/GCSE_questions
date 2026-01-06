# Security monitoring and alerting configuration

# CloudWatch Log Group for audit logs
resource "aws_cloudwatch_log_group" "audit_logs" {
  name              = "/aws/lambda/gcse-audit-logs-${var.environment}"
  retention_in_days = 2557  # 7 years for compliance (closest valid value)
  
  tags = {
    Name        = "GCSE Audit Logs"
    Environment = var.environment
    Purpose     = "Security audit and compliance logging"
  }
}

# CloudWatch Log Group for security events
resource "aws_cloudwatch_log_group" "security_events" {
  name              = "/aws/lambda/gcse-security-events-${var.environment}"
  retention_in_days = 365  # 1 year for security events
  
  tags = {
    Name        = "GCSE Security Events"
    Environment = var.environment
    Purpose     = "Security event monitoring and alerting"
  }
}

# SNS topic for security alerts
resource "aws_sns_topic" "security_alerts" {
  name = "gcse-security-alerts-${var.environment}"
  
  tags = {
    Name        = "GCSE Security Alerts"
    Environment = var.environment
    Purpose     = "Security incident notifications"
  }
}

# SNS topic for audit notifications
resource "aws_sns_topic" "audit_notifications" {
  name = "gcse-audit-notifications-${var.environment}"
  
  tags = {
    Name        = "GCSE Audit Notifications"
    Environment = var.environment
    Purpose     = "Audit event notifications"
  }
}

# CloudWatch metric filter for authentication failures
resource "aws_cloudwatch_log_metric_filter" "auth_failures" {
  name           = "gcse-auth-failures-${var.environment}"
  log_group_name = aws_cloudwatch_log_group.security_events.name
  pattern        = "[timestamp, level=\"WARNING\", message=\"Authentication failure\", ...]"

  metric_transformation {
    name      = "AuthenticationFailures"
    namespace = "GCSE/Security"
    value     = "1"
    
    default_value = 0
  }
}

# CloudWatch metric filter for brute force attempts
resource "aws_cloudwatch_log_metric_filter" "brute_force_attempts" {
  name           = "gcse-brute-force-${var.environment}"
  log_group_name = aws_cloudwatch_log_group.security_events.name
  pattern        = "[timestamp, level, message, alert_type=\"brute_force_suspected\"]"

  metric_transformation {
    name      = "BruteForceAttempts"
    namespace = "GCSE/Security"
    value     = "1"
    
    default_value = 0
  }
}

# CloudWatch metric filter for security violations
resource "aws_cloudwatch_log_metric_filter" "security_violations" {
  name           = "gcse-security-violations-${var.environment}"
  log_group_name = aws_cloudwatch_log_group.security_events.name
  pattern        = "[timestamp, level, message, event_type=\"security_violation\"]"

  metric_transformation {
    name      = "SecurityViolations"
    namespace = "GCSE/Security"
    value     = "1"
    
    default_value = 0
  }
}

# CloudWatch metric filter for rate limit exceeded
resource "aws_cloudwatch_log_metric_filter" "rate_limit_exceeded" {
  name           = "gcse-rate-limit-exceeded-${var.environment}"
  log_group_name = aws_cloudwatch_log_group.security_events.name
  pattern        = "[timestamp, level, message, event_type=\"rate_limit_exceeded\"]"

  metric_transformation {
    name      = "RateLimitExceeded"
    namespace = "GCSE/Security"
    value     = "1"
    
    default_value = 0
  }
}

# CloudWatch metric filter for suspicious activity
resource "aws_cloudwatch_log_metric_filter" "suspicious_activity" {
  name           = "gcse-suspicious-activity-${var.environment}"
  log_group_name = aws_cloudwatch_log_group.security_events.name
  pattern        = "[timestamp, level, message, security_alert=\"true\"]"

  metric_transformation {
    name      = "SuspiciousActivity"
    namespace = "GCSE/Security"
    value     = "1"
    
    default_value = 0
  }
}

# CloudWatch alarm for multiple authentication failures
resource "aws_cloudwatch_metric_alarm" "auth_failure_alarm" {
  alarm_name          = "gcse-auth-failures-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "AuthenticationFailures"
  namespace           = "GCSE/Security"
  period              = "300"  # 5 minutes
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "This metric monitors authentication failures"
  alarm_actions       = [aws_sns_topic.security_alerts.arn]
  ok_actions          = [aws_sns_topic.security_alerts.arn]
  
  treat_missing_data = "notBreaching"
  
  tags = {
    Name        = "GCSE Auth Failure Alarm"
    Environment = var.environment
    Severity    = "High"
  }
}

# CloudWatch alarm for brute force attempts
resource "aws_cloudwatch_metric_alarm" "brute_force_alarm" {
  alarm_name          = "gcse-brute-force-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "BruteForceAttempts"
  namespace           = "GCSE/Security"
  period              = "300"  # 5 minutes
  statistic           = "Sum"
  threshold           = "1"
  alarm_description   = "This metric monitors brute force attempts"
  alarm_actions       = [aws_sns_topic.security_alerts.arn]
  
  treat_missing_data = "notBreaching"
  
  tags = {
    Name        = "GCSE Brute Force Alarm"
    Environment = var.environment
    Severity    = "Critical"
  }
}

# CloudWatch alarm for security violations
resource "aws_cloudwatch_metric_alarm" "security_violation_alarm" {
  alarm_name          = "gcse-security-violations-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "SecurityViolations"
  namespace           = "GCSE/Security"
  period              = "300"  # 5 minutes
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "This metric monitors security violations"
  alarm_actions       = [aws_sns_topic.security_alerts.arn]
  
  treat_missing_data = "notBreaching"
  
  tags = {
    Name        = "GCSE Security Violation Alarm"
    Environment = var.environment
    Severity    = "Critical"
  }
}

# CloudWatch alarm for rate limiting
resource "aws_cloudwatch_metric_alarm" "rate_limit_alarm" {
  alarm_name          = "gcse-rate-limit-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "RateLimitExceeded"
  namespace           = "GCSE/Security"
  period              = "300"  # 5 minutes
  statistic           = "Sum"
  threshold           = "50"
  alarm_description   = "This metric monitors rate limit violations"
  alarm_actions       = [aws_sns_topic.security_alerts.arn]
  
  treat_missing_data = "notBreaching"
  
  tags = {
    Name        = "GCSE Rate Limit Alarm"
    Environment = var.environment
    Severity    = "Medium"
  }
}

# CloudWatch alarm for suspicious activity
resource "aws_cloudwatch_metric_alarm" "suspicious_activity_alarm" {
  alarm_name          = "gcse-suspicious-activity-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "SuspiciousActivity"
  namespace           = "GCSE/Security"
  period              = "300"  # 5 minutes
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "This metric monitors suspicious activity patterns"
  alarm_actions       = [aws_sns_topic.security_alerts.arn]
  
  treat_missing_data = "notBreaching"
  
  tags = {
    Name        = "GCSE Suspicious Activity Alarm"
    Environment = var.environment
    Severity    = "High"
  }
}

# CloudWatch dashboard for security monitoring
resource "aws_cloudwatch_dashboard" "security_dashboard" {
  dashboard_name = "GCSE-Security-Dashboard-${var.environment}"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["GCSE/Security", "AuthenticationFailures"],
            [".", "BruteForceAttempts"],
            [".", "SecurityViolations"],
            [".", "RateLimitExceeded"],
            [".", "SuspiciousActivity"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "us-east-1"
          title   = "Security Events Overview"
          period  = 300
        }
      },
      {
        type   = "log"
        x      = 0
        y      = 6
        width  = 24
        height = 6

        properties = {
          query   = "SOURCE '${aws_cloudwatch_log_group.security_events.name}' | fields @timestamp, @message | filter @message like /security_alert/ | sort @timestamp desc | limit 100"
          region  = "us-east-1"
          title   = "Recent Security Alerts"
        }
      },
      {
        type   = "log"
        x      = 0
        y      = 12
        width  = 24
        height = 6

        properties = {
          query   = "SOURCE '${aws_cloudwatch_log_group.audit_logs.name}' | fields @timestamp, @message | filter @message like /Authentication failure/ | sort @timestamp desc | limit 50"
          region  = "us-east-1"
          title   = "Recent Authentication Failures"
        }
      }
    ]
  })
}

# EventBridge rule for security event processing
resource "aws_cloudwatch_event_rule" "security_event_rule" {
  name        = "gcse-security-events-${var.environment}"
  description = "Process security events for automated response"

  event_pattern = jsonencode({
    source      = ["aws.logs"]
    detail-type = ["CloudWatch Logs Subscription Filter"]
    detail = {
      logGroup = [aws_cloudwatch_log_group.security_events.name]
    }
  })

  tags = {
    Name        = "GCSE Security Event Rule"
    Environment = var.environment
  }
}

# Lambda function for automated security response (placeholder)
resource "aws_lambda_function" "security_response" {
  filename         = "security_response.zip"
  function_name    = "gcse-security-response-${var.environment}"
  role            = aws_iam_role.security_response_role.arn
  handler         = "index.handler"
  runtime         = "python3.9"
  timeout         = 60

  # Placeholder code - would be implemented for automated responses
  source_code_hash = data.archive_file.security_response_zip.output_base64sha256

  environment {
    variables = {
      ENVIRONMENT = var.environment
      SNS_TOPIC_ARN = aws_sns_topic.security_alerts.arn
    }
  }

  tags = {
    Name        = "GCSE Security Response"
    Environment = var.environment
    Purpose     = "Automated security incident response"
  }
}

# Create placeholder zip file for security response lambda
data "archive_file" "security_response_zip" {
  type        = "zip"
  output_path = "security_response.zip"
  
  source {
    content = <<EOF
import json
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    """Automated security response handler."""
    logger.info(f"Security event received: {json.dumps(event)}")
    
    # Placeholder for automated security responses:
    # - Block suspicious IPs
    # - Disable compromised accounts
    # - Escalate critical incidents
    # - Generate incident reports
    
    return {
        'statusCode': 200,
        'body': json.dumps('Security event processed')
    }
EOF
    filename = "index.py"
  }
}

# IAM role for security response lambda
resource "aws_iam_role" "security_response_role" {
  name = "gcse-security-response-role-${var.environment}"

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
    Name        = "GCSE Security Response Role"
    Environment = var.environment
  }
}

# IAM policy for security response lambda
resource "aws_iam_role_policy" "security_response_policy" {
  name = "gcse-security-response-policy-${var.environment}"
  role = aws_iam_role.security_response_role.id

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
          "sns:Publish"
        ]
        Resource = aws_sns_topic.security_alerts.arn
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:Query",
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem"
        ]
        Resource = "arn:aws:dynamodb:*:*:table/gcse-*"
      }
    ]
  })
}

# EventBridge target for security response lambda
resource "aws_cloudwatch_event_target" "security_response_target" {
  rule      = aws_cloudwatch_event_rule.security_event_rule.name
  target_id = "SecurityResponseTarget"
  arn       = aws_lambda_function.security_response.arn
}

# Lambda permission for EventBridge
resource "aws_lambda_permission" "security_response_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.security_response.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.security_event_rule.arn
}