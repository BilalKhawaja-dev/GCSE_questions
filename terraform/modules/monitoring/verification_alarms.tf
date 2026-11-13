# CloudWatch Alarms for Question Verification System

# SNS Topic for Verification Alerts
resource "aws_sns_topic" "verification_alerts" {
  name = "${var.project_name}-verification-alerts-${var.environment}"

  tags = {
    Name        = "${var.project_name}-verification-alerts-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
  }
}

# SNS Topic Subscription (Email)
resource "aws_sns_topic_subscription" "verification_alerts_email" {
  count     = var.alert_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.verification_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# Alarm: Low Inventory (< 20 questions per topic)
resource "aws_cloudwatch_metric_alarm" "low_inventory" {
  alarm_name          = "${var.project_name}-low-inventory-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "LowInventoryAlert"
  namespace           = "GCSE/QuestionVerification"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "Alert when any topic has less than 20 verified questions"
  alarm_actions       = [aws_sns_topic.verification_alerts.arn]
  treat_missing_data  = "notBreaching"

  tags = {
    Name        = "${var.project_name}-low-inventory-${var.environment}"
    Environment = var.environment
    Severity    = "High"
  }
}

# Alarm: Low Verification Pass Rate (< 50%)
resource "aws_cloudwatch_metric_alarm" "low_pass_rate" {
  alarm_name          = "${var.project_name}-low-pass-rate-${var.environment}"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 3
  metric_name         = "AveragePassRate"
  namespace           = "GCSE/QuestionVerification"
  period              = 3600
  statistic           = "Average"
  threshold           = 50
  alarm_description   = "Alert when verification pass rate drops below 50%"
  alarm_actions       = [aws_sns_topic.verification_alerts.arn]
  treat_missing_data  = "notBreaching"

  tags = {
    Name        = "${var.project_name}-low-pass-rate-${var.environment}"
    Environment = var.environment
    Severity    = "High"
  }
}

# Alarm: High Retrieval Latency (> 200ms)
resource "aws_cloudwatch_metric_alarm" "high_retrieval_latency" {
  alarm_name          = "${var.project_name}-high-retrieval-latency-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "RetrievalLatency"
  namespace           = "GCSE/QuestionVerification"
  period              = 300
  statistic           = "Average"
  threshold           = 200
  alarm_description   = "Alert when average retrieval latency exceeds 200ms"
  alarm_actions       = [aws_sns_topic.verification_alerts.arn]
  treat_missing_data  = "notBreaching"

  tags = {
    Name        = "${var.project_name}-high-retrieval-latency-${var.environment}"
    Environment = var.environment
    Severity    = "Medium"
  }
}

# Alarm: High Retrieval Latency P99 (> 500ms)
resource "aws_cloudwatch_metric_alarm" "high_retrieval_latency_p99" {
  alarm_name          = "${var.project_name}-high-retrieval-latency-p99-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "RetrievalLatency"
  namespace           = "GCSE/QuestionVerification"
  period              = 300
  extended_statistic  = "p99"
  threshold           = 500
  alarm_description   = "Alert when P99 retrieval latency exceeds 500ms"
  alarm_actions       = [aws_sns_topic.verification_alerts.arn]
  treat_missing_data  = "notBreaching"

  tags = {
    Name        = "${var.project_name}-high-retrieval-latency-p99-${var.environment}"
    Environment = var.environment
    Severity    = "Medium"
  }
}

# Alarm: Generation Failure Rate (> 20%)
resource "aws_cloudwatch_metric_alarm" "high_generation_failure_rate" {
  alarm_name          = "${var.project_name}-high-generation-failure-${var.environment}"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 2
  metric_name         = "BatchPassRate"
  namespace           = "GCSE/QuestionVerification"
  period              = 3600
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Alert when batch generation pass rate drops below 80% (failure rate > 20%)"
  alarm_actions       = [aws_sns_topic.verification_alerts.arn]
  treat_missing_data  = "notBreaching"

  tags = {
    Name        = "${var.project_name}-high-generation-failure-${var.environment}"
    Environment = var.environment
    Severity    = "High"
  }
}

# Alarm: High User Issue Reports (> 5%)
resource "aws_cloudwatch_metric_alarm" "high_issue_reports" {
  alarm_name          = "${var.project_name}-high-issue-reports-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "FalsePositiveRate"
  namespace           = "GCSE/QuestionVerification"
  period              = 3600
  statistic           = "Average"
  threshold           = 5
  alarm_description   = "Alert when false positive rate (user issue reports) exceeds 5%"
  alarm_actions       = [aws_sns_topic.verification_alerts.arn]
  treat_missing_data  = "notBreaching"

  tags = {
    Name        = "${var.project_name}-high-issue-reports-${var.environment}"
    Environment = var.environment
    Severity    = "Medium"
  }
}

# Alarm: Verification Layer Failure (Deterministic)
resource "aws_cloudwatch_metric_alarm" "deterministic_layer_failure" {
  alarm_name          = "${var.project_name}-deterministic-layer-failure-${var.environment}"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 2
  metric_name         = "VerificationPassRate"
  namespace           = "GCSE/QuestionVerification"
  period              = 3600
  statistic           = "Average"
  threshold           = 90
  alarm_description   = "Alert when deterministic verification layer pass rate drops below 90%"
  alarm_actions       = [aws_sns_topic.verification_alerts.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    Layer = "Deterministic"
  }

  tags = {
    Name        = "${var.project_name}-deterministic-layer-failure-${var.environment}"
    Environment = var.environment
    Severity    = "High"
  }
}

# Alarm: LLM Auditor Low Confidence
resource "aws_cloudwatch_metric_alarm" "llm_low_confidence" {
  alarm_name          = "${var.project_name}-llm-low-confidence-${var.environment}"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 3
  metric_name         = "VerificationConfidence"
  namespace           = "GCSE/QuestionVerification"
  period              = 3600
  statistic           = "Average"
  threshold           = 0.75
  alarm_description   = "Alert when LLM auditor average confidence drops below 0.75"
  alarm_actions       = [aws_sns_topic.verification_alerts.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    Layer = "LLM"
  }

  tags = {
    Name        = "${var.project_name}-llm-low-confidence-${var.environment}"
    Environment = var.environment
    Severity    = "Medium"
  }
}

# Alarm: Replenishment Failure
resource "aws_cloudwatch_metric_alarm" "replenishment_failure" {
  alarm_name          = "${var.project_name}-replenishment-failure-${var.environment}"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ReplenishmentExecutionCount"
  namespace           = "GCSE/QuestionVerification"
  period              = 604800  # 7 days
  statistic           = "Sum"
  threshold           = 1
  alarm_description   = "Alert when replenishment cron job hasn't executed in 7 days"
  alarm_actions       = [aws_sns_topic.verification_alerts.arn]
  treat_missing_data  = "breaching"

  tags = {
    Name        = "${var.project_name}-replenishment-failure-${var.environment}"
    Environment = var.environment
    Severity    = "Critical"
  }
}

# Alarm: High Verification Latency (> 15s)
resource "aws_cloudwatch_metric_alarm" "high_verification_latency" {
  alarm_name          = "${var.project_name}-high-verification-latency-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "VerificationLatency"
  namespace           = "GCSE/QuestionVerification"
  period              = 300
  statistic           = "Average"
  threshold           = 15000  # 15 seconds in milliseconds
  alarm_description   = "Alert when average verification latency exceeds 15 seconds"
  alarm_actions       = [aws_sns_topic.verification_alerts.arn]
  treat_missing_data  = "notBreaching"

  tags = {
    Name        = "${var.project_name}-high-verification-latency-${var.environment}"
    Environment = var.environment
    Severity    = "Medium"
  }
}

# Alarm: No Questions Served (System Down)
resource "aws_cloudwatch_metric_alarm" "no_questions_served" {
  alarm_name          = "${var.project_name}-no-questions-served-${var.environment}"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 2
  metric_name         = "QuestionsServed"
  namespace           = "GCSE/QuestionVerification"
  period              = 3600
  statistic           = "Sum"
  threshold           = 1
  alarm_description   = "Alert when no questions have been served in the last 2 hours (potential system outage)"
  alarm_actions       = [aws_sns_topic.verification_alerts.arn]
  treat_missing_data  = "breaching"

  tags = {
    Name        = "${var.project_name}-no-questions-served-${var.environment}"
    Environment = var.environment
    Severity    = "Critical"
  }
}

# Outputs
output "verification_alerts_topic_arn" {
  description = "ARN of the SNS topic for verification alerts"
  value       = aws_sns_topic.verification_alerts.arn
}

output "alarm_names" {
  description = "List of all verification alarm names"
  value = [
    aws_cloudwatch_metric_alarm.low_inventory.alarm_name,
    aws_cloudwatch_metric_alarm.low_pass_rate.alarm_name,
    aws_cloudwatch_metric_alarm.high_retrieval_latency.alarm_name,
    aws_cloudwatch_metric_alarm.high_retrieval_latency_p99.alarm_name,
    aws_cloudwatch_metric_alarm.high_generation_failure_rate.alarm_name,
    aws_cloudwatch_metric_alarm.high_issue_reports.alarm_name,
    aws_cloudwatch_metric_alarm.deterministic_layer_failure.alarm_name,
    aws_cloudwatch_metric_alarm.llm_low_confidence.alarm_name,
    aws_cloudwatch_metric_alarm.replenishment_failure.alarm_name,
    aws_cloudwatch_metric_alarm.high_verification_latency.alarm_name,
    aws_cloudwatch_metric_alarm.no_questions_served.alarm_name
  ]
}
