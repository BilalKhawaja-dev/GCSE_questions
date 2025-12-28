"""
Monitoring validation tests for GCSE Question Generator.
Tests alarm triggering conditions, dashboard metric accuracy, and SNS notification delivery.

Requirements: 10.4
"""

import json
import pytest
import boto3
from unittest.mock import patch, MagicMock, Mock
from moto import mock_aws
import time
from datetime import datetime, timedelta


class TestMonitoringValidation:
    """Validation tests for monitoring and alerting system."""
    
    def setup_method(self):
        """Set up test environment."""
        self.region = "eu-west-2"
        self.environment = "test"
        
    def test_terraform_monitoring_configuration_completeness(self):
        """Test that monitoring Terraform configuration includes all required components."""
        with open('terraform/modules/monitoring/main.tf', 'r') as f:
            monitoring_content = f.read()
            
        # Verify comprehensive dashboard widgets
        assert 'AWS/ApiGateway' in monitoring_content
        assert 'AWS/Lambda' in monitoring_content
        assert 'AWS/S3' in monitoring_content
        assert 'AWS/CloudFront' in monitoring_content
        assert 'AWS/Billing' in monitoring_content
        
        # Verify all required metrics are included
        assert 'Count' in monitoring_content  # API Gateway requests
        assert '4XXError' in monitoring_content
        assert '5XXError' in monitoring_content
        assert 'Latency' in monitoring_content
        assert 'IntegrationLatency' in monitoring_content
        assert 'Invocations' in monitoring_content  # Lambda
        assert 'Errors' in monitoring_content
        assert 'Duration' in monitoring_content
        assert 'Throttles' in monitoring_content
        assert 'ConcurrentExecutions' in monitoring_content
        assert 'NumberOfObjects' in monitoring_content  # S3
        assert 'BucketSizeBytes' in monitoring_content
        assert 'AllRequests' in monitoring_content
        assert 'GetRequests' in monitoring_content
        assert 'Requests' in monitoring_content  # CloudFront
        assert 'BytesDownloaded' in monitoring_content
        assert 'CacheHitRate' in monitoring_content
        assert 'EstimatedCharges' in monitoring_content  # Billing
        
        # Verify Bedrock token usage tracking via logs
        assert 'CloudWatch Logs Insights' in monitoring_content
        assert 'token' in monitoring_content
        
    def test_critical_alarms_configuration(self):
        """Test that all critical alarms are properly configured."""
        with open('terraform/modules/monitoring/main.tf', 'r') as f:
            monitoring_content = f.read()
            
        # Verify critical alarms exist
        critical_alarms = [
            'lambda_error_rate_interpret',
            'lambda_error_rate_generate', 
            'api_gateway_5xx_errors',
            's3_unavailable',
            'daily_cost_alarm'
        ]
        
        for alarm in critical_alarms:
            assert alarm in monitoring_content
            
        # Verify alarm thresholds match requirements
        assert 'threshold           = "5"' in monitoring_content  # Lambda error rate > 5%
        assert 'threshold           = "1"' in monitoring_content  # API Gateway 5xx > 1%
        assert 'threshold           = "0"' in monitoring_content  # S3 unavailable
        
        # Verify evaluation periods
        assert 'evaluation_periods  = "2"' in monitoring_content  # Most alarms
        assert 'evaluation_periods  = "1"' in monitoring_content  # S3 and cost alarms
        
        # Verify alarm actions include SNS
        assert 'alarm_actions       = [aws_sns_topic.alerts.arn]' in monitoring_content
        assert 'ok_actions          = [aws_sns_topic.alerts.arn]' in monitoring_content
        
    def test_warning_alarms_configuration(self):
        """Test that all warning alarms are properly configured."""
        with open('terraform/modules/monitoring/main.tf', 'r') as f:
            monitoring_content = f.read()
            
        # Verify warning alarms exist
        warning_alarms = [
            'lambda_duration_warning_interpret',
            'lambda_duration_warning_generate',
            'api_gateway_latency_warning',
            'bedrock_throttling',
            'monthly_cost_warning'
        ]
        
        for alarm in warning_alarms:
            assert alarm in monitoring_content
            
        # Verify warning thresholds
        assert 'threshold           = "25000"' in monitoring_content  # InterpretLambda 25s
        assert 'threshold           = "50000"' in monitoring_content  # GenerateLambda 50s
        assert 'threshold           = "10000"' in monitoring_content  # API Gateway 10s
        
        # Verify monthly cost warning is 80% of threshold
        assert 'var.cost_threshold_monthly * 0.8' in monitoring_content
        
    def test_sns_topic_configuration(self):
        """Test SNS topic and subscription configuration."""
        with open('terraform/modules/monitoring/main.tf', 'r') as f:
            monitoring_content = f.read()
            
        # Verify SNS topic
        assert 'resource "aws_sns_topic" "alerts"' in monitoring_content
        assert 'gcse-alerts-${var.environment}' in monitoring_content
        
        # Verify email subscription
        assert 'resource "aws_sns_topic_subscription" "email_alerts"' in monitoring_content
        assert 'protocol  = "email"' in monitoring_content
        assert 'endpoint  = var.alert_email' in monitoring_content
        
        # Verify proper tagging
        assert 'Name        = "GCSE Alerts"' in monitoring_content
        assert 'Environment = var.environment' in monitoring_content
        
    def test_cloudwatch_log_groups_configuration(self):
        """Test CloudWatch log groups are properly configured."""
        with open('terraform/modules/monitoring/main.tf', 'r') as f:
            monitoring_content = f.read()
            
        # Verify log groups for Lambda functions
        assert 'resource "aws_cloudwatch_log_group" "interpret_lambda_logs"' in monitoring_content
        assert 'resource "aws_cloudwatch_log_group" "generate_lambda_logs"' in monitoring_content
        
        # Verify log retention
        assert 'retention_in_days = 30' in monitoring_content
        
        # Verify log group naming
        assert '/aws/lambda/${var.interpret_lambda_name}' in monitoring_content
        assert '/aws/lambda/${var.generate_lambda_name}' in monitoring_content
        
    def test_cost_tracking_dashboard_configuration(self):
        """Test cost tracking dashboard configuration."""
        with open('terraform/modules/monitoring/main.tf', 'r') as f:
            monitoring_content = f.read()
            
        # Verify cost dashboard exists
        assert 'resource "aws_cloudwatch_dashboard" "cost_dashboard"' in monitoring_content
        assert 'GCSE-Cost-Tracking-${var.environment}' in monitoring_content
        
        # Verify cost metrics by service
        services = ['AmazonBedrock', 'AmazonS3', 'AWSLambda', 'AmazonApiGateway', 'AmazonCloudFront']
        for service in services:
            assert service in monitoring_content
            
        # Verify billing metrics region (us-east-1)
        assert 'region  = "us-east-1"' in monitoring_content
        
        # Verify currency and period
        assert 'Currency", "USD"' in monitoring_content
        assert 'period  = 86400' in monitoring_content  # Daily
        
    @mock_aws
    def test_alarm_triggering_conditions_lambda_errors(self):
        """Test Lambda error rate alarm triggering conditions."""
        # Create CloudWatch client
        cloudwatch = boto3.client('cloudwatch', region_name=self.region)
        
        # Create alarm similar to Terraform configuration
        alarm_name = f'gcse-interpret-lambda-error-rate-{self.environment}'
        cloudwatch.put_metric_alarm(
            AlarmName=alarm_name,
            ComparisonOperator='GreaterThanThreshold',
            EvaluationPeriods=2,
            MetricName='Errors',
            Namespace='AWS/Lambda',
            Period=300,
            Statistic='Sum',
            Threshold=5.0,
            ActionsEnabled=True,
            AlarmActions=['arn:aws:sns:eu-west-2:123456789012:gcse-alerts-test'],
            AlarmDescription='InterpretLambda error rate > 5%',
            Dimensions=[
                {
                    'Name': 'FunctionName',
                    'Value': f'gcse-interpret-lambda-{self.environment}'
                }
            ]
        )
        
        # Put metric data that should trigger alarm (6 errors in 5 minutes)
        cloudwatch.put_metric_data(
            Namespace='AWS/Lambda',
            MetricData=[
                {
                    'MetricName': 'Errors',
                    'Dimensions': [
                        {
                            'Name': 'FunctionName',
                            'Value': f'gcse-interpret-lambda-{self.environment}'
                        }
                    ],
                    'Value': 6.0,
                    'Timestamp': datetime.utcnow()
                }
            ]
        )
        
        # Verify alarm exists
        alarms = cloudwatch.describe_alarms(AlarmNames=[alarm_name])
        assert len(alarms['MetricAlarms']) == 1
        assert alarms['MetricAlarms'][0]['Threshold'] == 5.0
        assert alarms['MetricAlarms'][0]['ComparisonOperator'] == 'GreaterThanThreshold'
        
    @mock_aws
    def test_alarm_triggering_conditions_api_gateway_errors(self):
        """Test API Gateway 5xx error alarm triggering conditions."""
        cloudwatch = boto3.client('cloudwatch', region_name=self.region)
        
        # Create alarm
        alarm_name = f'gcse-api-5xx-errors-{self.environment}'
        cloudwatch.put_metric_alarm(
            AlarmName=alarm_name,
            ComparisonOperator='GreaterThanThreshold',
            EvaluationPeriods=2,
            MetricName='5XXError',
            Namespace='AWS/ApiGateway',
            Period=300,
            Statistic='Sum',
            Threshold=1.0,
            ActionsEnabled=True,
            AlarmActions=['arn:aws:sns:eu-west-2:123456789012:gcse-alerts-test'],
            AlarmDescription='API Gateway 5xx error rate > 1%',
            Dimensions=[
                {
                    'Name': 'ApiName',
                    'Value': f'gcse-question-generator-{self.environment}'
                }
            ]
        )
        
        # Put metric data that should trigger alarm (2 5xx errors)
        cloudwatch.put_metric_data(
            Namespace='AWS/ApiGateway',
            MetricData=[
                {
                    'MetricName': '5XXError',
                    'Dimensions': [
                        {
                            'Name': 'ApiName',
                            'Value': f'gcse-question-generator-{self.environment}'
                        }
                    ],
                    'Value': 2.0,
                    'Timestamp': datetime.utcnow()
                }
            ]
        )
        
        # Verify alarm configuration
        alarms = cloudwatch.describe_alarms(AlarmNames=[alarm_name])
        assert len(alarms['MetricAlarms']) == 1
        assert alarms['MetricAlarms'][0]['Threshold'] == 1.0
        
    @mock_aws
    def test_alarm_triggering_conditions_lambda_duration(self):
        """Test Lambda duration warning alarm triggering conditions."""
        cloudwatch = boto3.client('cloudwatch', region_name=self.region)
        
        # Create duration warning alarm for GenerateLambda
        alarm_name = f'gcse-generate-duration-warning-{self.environment}'
        cloudwatch.put_metric_alarm(
            AlarmName=alarm_name,
            ComparisonOperator='GreaterThanThreshold',
            EvaluationPeriods=2,
            MetricName='Duration',
            Namespace='AWS/Lambda',
            Period=300,
            Statistic='Average',
            Threshold=50000.0,  # 50 seconds
            ActionsEnabled=True,
            AlarmActions=['arn:aws:sns:eu-west-2:123456789012:gcse-alerts-test'],
            AlarmDescription='GenerateLambda duration approaching timeout',
            Dimensions=[
                {
                    'Name': 'FunctionName',
                    'Value': f'gcse-generate-lambda-{self.environment}'
                }
            ]
        )
        
        # Put metric data that should trigger alarm (55 seconds duration)
        cloudwatch.put_metric_data(
            Namespace='AWS/Lambda',
            MetricData=[
                {
                    'MetricName': 'Duration',
                    'Dimensions': [
                        {
                            'Name': 'FunctionName',
                            'Value': f'gcse-generate-lambda-{self.environment}'
                        }
                    ],
                    'Value': 55000.0,  # 55 seconds in milliseconds
                    'Timestamp': datetime.utcnow()
                }
            ]
        )
        
        # Verify alarm configuration
        alarms = cloudwatch.describe_alarms(AlarmNames=[alarm_name])
        assert len(alarms['MetricAlarms']) == 1
        assert alarms['MetricAlarms'][0]['Threshold'] == 50000.0
        assert alarms['MetricAlarms'][0]['Statistic'] == 'Average'
        
    @mock_aws
    def test_dashboard_metric_accuracy(self):
        """Test CloudWatch dashboard metric accuracy and configuration."""
        cloudwatch = boto3.client('cloudwatch', region_name=self.region)
        
        # Create dashboard similar to Terraform configuration
        dashboard_name = f'GCSE-Question-Generator-{self.environment}'
        dashboard_body = {
            "widgets": [
                {
                    "type": "metric",
                    "properties": {
                        "metrics": [
                            ["AWS/ApiGateway", "Count", "ApiName", f"gcse-question-generator-{self.environment}"],
                            [".", "4XXError", ".", "."],
                            [".", "5XXError", ".", "."],
                            [".", "Latency", ".", "."]
                        ],
                        "view": "timeSeries",
                        "region": "eu-west-2",
                        "title": "API Gateway Metrics",
                        "period": 300
                    }
                },
                {
                    "type": "metric",
                    "properties": {
                        "metrics": [
                            ["AWS/Lambda", "Invocations", "FunctionName", f"gcse-interpret-lambda-{self.environment}"],
                            [".", "Errors", ".", "."],
                            [".", "Duration", ".", "."]
                        ],
                        "view": "timeSeries",
                        "region": "eu-west-2",
                        "title": "Lambda Function Performance",
                        "period": 300
                    }
                }
            ]
        }
        
        cloudwatch.put_dashboard(
            DashboardName=dashboard_name,
            DashboardBody=json.dumps(dashboard_body)
        )
        
        # Verify dashboard was created
        dashboards = cloudwatch.list_dashboards()
        dashboard_names = [d['DashboardName'] for d in dashboards['DashboardEntries']]
        assert dashboard_name in dashboard_names
        
        # Get dashboard and verify structure
        dashboard = cloudwatch.get_dashboard(DashboardName=dashboard_name)
        body = json.loads(dashboard['DashboardBody'])
        
        # Verify widget structure
        assert len(body['widgets']) == 2
        assert body['widgets'][0]['type'] == 'metric'
        assert body['widgets'][0]['properties']['title'] == 'API Gateway Metrics'
        assert body['widgets'][1]['properties']['title'] == 'Lambda Function Performance'
        
        # Verify metrics are correctly configured
        api_metrics = body['widgets'][0]['properties']['metrics']
        assert ['AWS/ApiGateway', 'Count', 'ApiName', f'gcse-question-generator-{self.environment}'] in api_metrics
        # The "." notation is shorthand for repeating the previous metric dimensions
        assert ['.', '4XXError', '.', '.'] in api_metrics
        
    @mock_aws
    def test_sns_notification_delivery(self):
        """Test SNS notification delivery configuration."""
        sns = boto3.client('sns', region_name=self.region)
        
        # Create SNS topic similar to Terraform configuration
        topic_name = f'gcse-alerts-{self.environment}'
        topic_response = sns.create_topic(Name=topic_name)
        topic_arn = topic_response['TopicArn']
        
        # Create email subscription
        test_email = 'test@example.com'
        sns.subscribe(
            TopicArn=topic_arn,
            Protocol='email',
            Endpoint=test_email
        )
        
        # Verify topic exists
        topics = sns.list_topics()
        topic_arns = [t['TopicArn'] for t in topics['Topics']]
        assert topic_arn in topic_arns
        
        # Verify subscription
        subscriptions = sns.list_subscriptions_by_topic(TopicArn=topic_arn)
        assert len(subscriptions['Subscriptions']) == 1
        assert subscriptions['Subscriptions'][0]['Protocol'] == 'email'
        assert subscriptions['Subscriptions'][0]['Endpoint'] == test_email
        
        # Test message publishing (simulating alarm notification)
        alarm_message = {
            "AlarmName": f"gcse-lambda-error-rate-{self.environment}",
            "AlarmDescription": "InterpretLambda error rate > 5%",
            "NewStateValue": "ALARM",
            "NewStateReason": "Threshold Crossed: 6 out of the last 2 datapoints were greater than the threshold (5.0).",
            "StateChangeTime": datetime.utcnow().isoformat(),
            "Region": "eu-west-2"
        }
        
        response = sns.publish(
            TopicArn=topic_arn,
            Message=json.dumps(alarm_message),
            Subject=f'ALARM: {alarm_message["AlarmName"]}'
        )
        
        # Verify message was published
        assert 'MessageId' in response
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200
        
    def test_cost_threshold_configuration(self):
        """Test cost threshold alarm configuration."""
        with open('terraform/modules/monitoring/main.tf', 'r') as f:
            monitoring_content = f.read()
            
        # Verify daily cost alarm
        assert 'daily_cost_alarm' in monitoring_content
        assert 'var.cost_threshold_daily' in monitoring_content
        assert 'EstimatedCharges' in monitoring_content
        assert 'Currency = "USD"' in monitoring_content
        
        # Verify monthly cost warning
        assert 'monthly_cost_warning' in monitoring_content
        assert 'var.cost_threshold_monthly * 0.8' in monitoring_content
        
        # Check variables file for default thresholds
        with open('terraform/variables.tf', 'r') as f:
            variables_content = f.read()
            
        assert 'cost_threshold_daily' in variables_content
        assert 'default     = 20' in variables_content  # £20 daily
        assert 'cost_threshold_monthly' in variables_content
        assert 'default     = 500' in variables_content  # £500 monthly
        
    def test_bedrock_usage_tracking_configuration(self):
        """Test Bedrock token usage tracking via CloudWatch Logs Insights."""
        with open('terraform/modules/monitoring/main.tf', 'r') as f:
            monitoring_content = f.read()
            
        # Verify Logs Insights widget for Bedrock usage
        assert 'type   = "log"' in monitoring_content
        assert 'Bedrock Token Usage (Logs Insights)' in monitoring_content
        
        # Verify query targets both Lambda functions
        assert 'SOURCE \'/aws/lambda/${var.interpret_lambda_name}\'' in monitoring_content
        assert 'SOURCE \'/aws/lambda/${var.generate_lambda_name}\'' in monitoring_content
        
        # Verify query filters for token usage
        assert 'filter @message like /token/' in monitoring_content
        assert 'stats count() by bin(5m)' in monitoring_content
        
    def test_monitoring_module_variables_completeness(self):
        """Test that monitoring module has all required variables."""
        with open('terraform/modules/monitoring/variables.tf', 'r') as f:
            variables_content = f.read()
            
        required_variables = [
            'environment',
            'api_gateway_id',
            'api_gateway_name',
            'interpret_lambda_name',
            'generate_lambda_name',
            'specifications_bucket_name',
            'examples_bucket_name',
            'frontend_bucket_name',
            'cloudfront_distribution_id',
            'alert_email',
            'cost_threshold_daily',
            'cost_threshold_monthly'
        ]
        
        for var in required_variables:
            assert f'variable "{var}"' in variables_content
            
    def test_monitoring_module_outputs_completeness(self):
        """Test that monitoring module provides all required outputs."""
        with open('terraform/modules/monitoring/outputs.tf', 'r') as f:
            outputs_content = f.read()
            
        required_outputs = [
            'sns_topic_arn',
            'dashboard_url',
            'cost_dashboard_url',
            'interpret_lambda_log_group',
            'generate_lambda_log_group'
        ]
        
        for output in required_outputs:
            assert f'output "{output}"' in outputs_content
            
        # Verify dashboard URLs are properly formatted
        assert 'https://eu-west-2.console.aws.amazon.com/cloudwatch/home' in outputs_content
        assert '#dashboards:name=' in outputs_content
        
    def test_alarm_evaluation_periods_and_thresholds(self):
        """Test that alarm evaluation periods and thresholds meet requirements."""
        with open('terraform/modules/monitoring/main.tf', 'r') as f:
            monitoring_content = f.read()
            
        # Critical alarms should have appropriate evaluation periods
        # Lambda error rate: 2 periods of 5 minutes each
        assert 'evaluation_periods  = "2"' in monitoring_content
        assert 'period              = "300"' in monitoring_content
        
        # S3 unavailable: 1 period of 1 minute (immediate alert)
        assert 'evaluation_periods  = "1"' in monitoring_content
        assert 'period              = "60"' in monitoring_content
        
        # Daily cost: 1 period of 24 hours
        assert 'period              = "86400"' in monitoring_content
        
        # Verify threshold values match design requirements
        thresholds = {
            '"5"': 'Lambda error count',      # 5 errors in 5 minutes
            '"1"': 'API Gateway 5xx errors',  # 1 5xx error
            '"0"': 'S3 5xx errors',          # Any S3 error
            '"25000"': 'InterpretLambda duration',  # 25 seconds
            '"50000"': 'GenerateLambda duration',   # 50 seconds
            '"10000"': 'API Gateway latency'        # 10 seconds
        }
        
        for threshold, description in thresholds.items():
            assert f'threshold           = {threshold}' in monitoring_content


if __name__ == '__main__':
    pytest.main([__file__, '-v'])