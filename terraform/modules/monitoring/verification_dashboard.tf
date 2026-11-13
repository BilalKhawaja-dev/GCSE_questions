# CloudWatch Dashboards for Question Verification System

# Question Bank Health Dashboard
resource "aws_cloudwatch_dashboard" "question_bank_health" {
  dashboard_name = "${var.project_name}-question-bank-health-${var.environment}"

  dashboard_body = jsonencode({
    widgets = [
      # Header
      {
        type = "text"
        properties = {
          markdown = "# Question Bank Health Dashboard\nMonitor inventory levels, verification quality, and replenishment status"
        }
        x      = 0
        y      = 0
        width  = 24
        height = 1
      },
      
      # Total Verified Questions
      {
        type = "metric"
        properties = {
          metrics = [
            ["GCSE/QuestionVerification", "TotalVerifiedQuestions", { stat = "Average", label = "Total Verified Questions" }]
          ]
          view    = "singleValue"
          region  = var.aws_region
          title   = "Total Verified Questions"
          period  = 300
        }
        x      = 0
        y      = 1
        width  = 6
        height = 3
      },
      
      # Average Pass Rate
      {
        type = "metric"
        properties = {
          metrics = [
            ["GCSE/QuestionVerification", "AveragePassRate", { stat = "Average", label = "Average Pass Rate" }]
          ]
          view    = "singleValue"
          region  = var.aws_region
          title   = "Average Verification Pass Rate"
          period  = 300
          yAxis = {
            left = {
              min = 0
              max = 100
            }
          }
        }
        x      = 6
        y      = 1
        width  = 6
        height = 3
      },
      
      # Average Retrieval Latency
      {
        type = "metric"
        properties = {
          metrics = [
            ["GCSE/QuestionVerification", "AverageRetrievalLatency", { stat = "Average", label = "Avg Latency (ms)" }]
          ]
          view    = "singleValue"
          region  = var.aws_region
          title   = "Average Retrieval Latency"
          period  = 300
        }
        x      = 12
        y      = 1
        width  = 6
        height = 3
      },
      
      # Low Inventory Alerts
      {
        type = "metric"
        properties = {
          metrics = [
            ["GCSE/QuestionVerification", "LowInventoryAlert", { stat = "Sum", label = "Topics Below Threshold" }]
          ]
          view    = "singleValue"
          region  = var.aws_region
          title   = "Low Inventory Alerts"
          period  = 300
        }
        x      = 18
        y      = 1
        width  = 6
        height = 3
      },
      
      # Verified Questions Count Over Time
      {
        type = "metric"
        properties = {
          metrics = [
            ["GCSE/QuestionVerification", "VerifiedQuestionCount", { stat = "Sum", label = "Verified Questions" }]
          ]
          view    = "timeSeries"
          region  = var.aws_region
          title   = "Verified Questions Count Over Time"
          period  = 3600
          stacked = false
        }
        x      = 0
        y      = 4
        width  = 12
        height = 6
      },
      
      # Inventory Levels by Topic
      {
        type = "metric"
        properties = {
          metrics = [
            ["GCSE/QuestionVerification", "InventoryLevel", { stat = "Average" }]
          ]
          view    = "timeSeries"
          region  = var.aws_region
          title   = "Inventory Levels by Topic (%)"
          period  = 3600
          yAxis = {
            left = {
              min = 0
              max = 100
            }
          }
        }
        x      = 12
        y      = 4
        width  = 12
        height = 6
      },
      
      # Replenishment Frequency
      {
        type = "metric"
        properties = {
          metrics = [
            ["GCSE/QuestionVerification", "ReplenishmentExecutionCount", { stat = "Sum", label = "Executions" }],
            [".", "TopicsReplenished", { stat = "Sum", label = "Topics Replenished" }],
            [".", "QuestionsGeneratedInReplenishment", { stat = "Sum", label = "Questions Generated" }]
          ]
          view    = "timeSeries"
          region  = var.aws_region
          title   = "Replenishment Activity"
          period  = 86400
          stacked = false
        }
        x      = 0
        y      = 10
        width  = 24
        height = 6
      }
    ]
  })
}

# Verification Quality Dashboard
resource "aws_cloudwatch_dashboard" "verification_quality" {
  dashboard_name = "${var.project_name}-verification-quality-${var.environment}"

  dashboard_body = jsonencode({
    widgets = [
      # Header
      {
        type = "text"
        properties = {
          markdown = "# Verification Quality Dashboard\nMonitor verification layer performance, pass rates, and failure reasons"
        }
        x      = 0
        y      = 0
        width  = 24
        height = 1
      },
      
      # Pass Rate by Layer (Pie Chart)
      {
        type = "metric"
        properties = {
          metrics = [
            ["GCSE/QuestionVerification", "VerificationPassRate", { stat = "Average", label = "Deterministic" }, { dimensions = { Layer = "Deterministic" } }],
            ["...", { dimensions = { Layer = "SymPy" } }],
            ["...", { dimensions = { Layer = "LLM" } }],
            ["...", { dimensions = { Layer = "KB" } }],
            ["...", { dimensions = { Layer = "Dedupe" } }]
          ]
          view    = "pie"
          region  = var.aws_region
          title   = "Pass Rate by Verification Layer"
          period  = 3600
        }
        x      = 0
        y      = 1
        width  = 12
        height = 6
      },
      
      # Verification Count by Result
      {
        type = "metric"
        properties = {
          metrics = [
            ["GCSE/QuestionVerification", "VerificationCount", { stat = "Sum" }]
          ]
          view    = "bar"
          region  = var.aws_region
          title   = "Verification Results (Pass/Fail)"
          period  = 3600
        }
        x      = 12
        y      = 1
        width  = 12
        height = 6
      },
      
      # Verification Latency by Layer
      {
        type = "metric"
        properties = {
          metrics = [
            ["GCSE/QuestionVerification", "VerificationLatency", { stat = "Average", label = "Deterministic" }, { dimensions = { Layer = "Deterministic" } }],
            ["...", { dimensions = { Layer = "SymPy" } }],
            ["...", { dimensions = { Layer = "LLM" } }],
            ["...", { dimensions = { Layer = "KB" } }],
            ["...", { dimensions = { Layer = "Dedupe" } }]
          ]
          view    = "timeSeries"
          region  = var.aws_region
          title   = "Verification Latency by Layer (ms)"
          period  = 300
          stacked = false
        }
        x      = 0
        y      = 7
        width  = 12
        height = 6
      },
      
      # Verification Confidence Scores
      {
        type = "metric"
        properties = {
          metrics = [
            ["GCSE/QuestionVerification", "VerificationConfidence", { stat = "Average" }]
          ]
          view    = "timeSeries"
          region  = var.aws_region
          title   = "Verification Confidence Scores"
          period  = 300
          yAxis = {
            left = {
              min = 0
              max = 1
            }
          }
        }
        x      = 12
        y      = 7
        width  = 12
        height = 6
      },
      
      # Failure Reasons Breakdown
      {
        type = "metric"
        properties = {
          metrics = [
            ["GCSE/QuestionVerification", "VerificationFailureCount", { stat = "Sum" }]
          ]
          view    = "bar"
          region  = var.aws_region
          title   = "Failure Reasons Breakdown"
          period  = 3600
        }
        x      = 0
        y      = 13
        width  = 12
        height = 6
      },
      
      # Batch Pass Rate
      {
        type = "metric"
        properties = {
          metrics = [
            ["GCSE/QuestionVerification", "BatchPassRate", { stat = "Average" }]
          ]
          view    = "timeSeries"
          region  = var.aws_region
          title   = "Batch Generation Pass Rate (%)"
          period  = 3600
          yAxis = {
            left = {
              min = 0
              max = 100
            }
          }
        }
        x      = 12
        y      = 13
        width  = 12
        height = 6
      }
    ]
  })
}

# User Experience Dashboard
resource "aws_cloudwatch_dashboard" "user_experience" {
  dashboard_name = "${var.project_name}-user-experience-${var.environment}"

  dashboard_body = jsonencode({
    widgets = [
      # Header
      {
        type = "text"
        properties = {
          markdown = "# User Experience Dashboard\nMonitor retrieval performance, user feedback, and question quality"
        }
        x      = 0
        y      = 0
        width  = 24
        height = 1
      },
      
      # Retrieval Latency
      {
        type = "metric"
        properties = {
          metrics = [
            ["GCSE/QuestionVerification", "RetrievalLatency", { stat = "Average", label = "Avg Latency" }],
            ["...", { stat = "p99", label = "P99 Latency" }]
          ]
          view    = "timeSeries"
          region  = var.aws_region
          title   = "Retrieval Latency (ms)"
          period  = 300
          stacked = false
          annotations = {
            horizontal = [
              {
                value = 100
                label = "Target (100ms)"
                color = "#2ca02c"
              },
              {
                value = 200
                label = "Alert Threshold (200ms)"
                color = "#d62728"
              }
            ]
          }
        }
        x      = 0
        y      = 1
        width  = 12
        height = 6
      },
      
      # Questions Served Per Hour
      {
        type = "metric"
        properties = {
          metrics = [
            ["GCSE/QuestionVerification", "QuestionsServed", { stat = "Sum", label = "Questions Served" }]
          ]
          view    = "timeSeries"
          region  = var.aws_region
          title   = "Questions Served Per Hour"
          period  = 3600
          stacked = false
        }
        x      = 12
        y      = 1
        width  = 12
        height = 6
      },
      
      # User Feedback Scores
      {
        type = "metric"
        properties = {
          metrics = [
            ["GCSE/QuestionVerification", "UserFeedbackCount", { stat = "Sum", label = "Helpful" }, { dimensions = { Helpful = "Yes" } }],
            ["...", { label = "Not Helpful" }, { dimensions = { Helpful = "No" } }]
          ]
          view    = "singleValue"
          region  = var.aws_region
          title   = "User Feedback"
          period  = 3600
        }
        x      = 0
        y      = 7
        width  = 8
        height = 4
      },
      
      # User Difficulty Ratings
      {
        type = "metric"
        properties = {
          metrics = [
            ["GCSE/QuestionVerification", "UserDifficultyRating", { stat = "Average", label = "Avg Difficulty Rating" }]
          ]
          view    = "singleValue"
          region  = var.aws_region
          title   = "Average Difficulty Rating"
          period  = 3600
        }
        x      = 8
        y      = 7
        width  = 8
        height = 4
      },
      
      # Issue Reports
      {
        type = "metric"
        properties = {
          metrics = [
            ["GCSE/QuestionVerification", "IssueReportCount", { stat = "Sum", label = "Issues Reported" }]
          ]
          view    = "singleValue"
          region  = var.aws_region
          title   = "Issues Reported"
          period  = 3600
        }
        x      = 16
        y      = 7
        width  = 8
        height = 4
      },
      
      # False Positive Rate
      {
        type = "metric"
        properties = {
          metrics = [
            ["GCSE/QuestionVerification", "FalsePositiveRate", { stat = "Average" }]
          ]
          view    = "timeSeries"
          region  = var.aws_region
          title   = "False Positive Rate (%)"
          period  = 3600
          yAxis = {
            left = {
              min = 0
              max = 10
            }
          }
          annotations = {
            horizontal = [
              {
                value = 5
                label = "Alert Threshold (5%)"
                color = "#d62728"
              }
            ]
          }
        }
        x      = 0
        y      = 11
        width  = 12
        height = 6
      },
      
      # High Latency Alerts
      {
        type = "metric"
        properties = {
          metrics = [
            ["GCSE/QuestionVerification", "HighLatencyAlert", { stat = "Sum" }]
          ]
          view    = "timeSeries"
          region  = var.aws_region
          title   = "High Latency Alerts"
          period  = 300
        }
        x      = 12
        y      = 11
        width  = 12
        height = 6
      }
    ]
  })
}

# Outputs
output "question_bank_health_dashboard_name" {
  description = "Name of the Question Bank Health dashboard"
  value       = aws_cloudwatch_dashboard.question_bank_health.dashboard_name
}

output "verification_quality_dashboard_name" {
  description = "Name of the Verification Quality dashboard"
  value       = aws_cloudwatch_dashboard.verification_quality.dashboard_name
}

output "user_experience_dashboard_name" {
  description = "Name of the User Experience dashboard"
  value       = aws_cloudwatch_dashboard.user_experience.dashboard_name
}
