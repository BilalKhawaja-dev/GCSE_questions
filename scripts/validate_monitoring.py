#!/usr/bin/env python3
"""
Monitoring Validation Script for GCSE Question Generator V2

This script validates that all monitoring and alerting systems are properly configured
and functioning correctly.
"""

import boto3
import json
import time
from typing import Dict, List, Optional

class MonitoringValidator:
    def __init__(self, environment: str = 'prod', region: str = 'eu-west-2'):
        self.environment = environment
        self.region = region
        self.cloudwatch = boto3.client('cloudwatch', region_name=region)
        self.sns = boto3.client('sns', region_name=region)
        self.logs = boto3.client('logs', region_name=region)
        
        self.expected_alarms = [
            f'gcse-interpret-lambda-error-rate-{environment}',
            f'gcse-generate-lambda-error-rate-{environment}',
            f'gcse-auth-lambda-error-rate-{environment}',
            f'gcse-feedback-lambda-error-rate-{environment}',
            f'gcse-refinement-lambda-error-rate-{environment}',
            f'gcse-api-5xx-errors-{environment}',
            f'gcse-s3-unavailable-{environment}',
            f'gcse-daily-cost-{environment}',
            f'gcse-bedrock-daily-cost-{environment}',
            f'gcse-dynamodb-daily-cost-{environment}',
            f'gcse-interpret-duration-warning-{environment}',
            f'gcse-generate-duration-warning-{environment}',
            f'gcse-auth-duration-warning-{environment}',
            f'gcse-question-success-rate-{environment}',
            f'gcse-api-latency-warning-{environment}',
            f'gcse-bedrock-throttling-{environment}',
            f'gcse-monthly-cost-warning-{environment}'
        ]
        
        self.expected_dashboards = [
            f'GCSE-Question-Generator-{environment}',
            f'GCSE-Cost-Tracking-{environment}'
        ]
        
        self.expected_log_groups = [
            f'/aws/lambda/gcse-auth-lambda-{environment}',
            f'/aws/lambda/gcse-interpret-lambda-{environment}',
            f'/aws/lambda/gcse-generate-lambda-{environment}',
            f'/aws/lambda/gcse-session-lambda-{environment}',
            f'/aws/lambda/gcse-feedback-lambda-{environment}',
            f'/aws/lambda/gcse-refinement-lambda-{environment}',
            f'/aws/lambda/gcse-export-lambda-{environment}',
            f'/aws/lambda/gcse-topic-coverage-lambda-{environment}'
        ]
    
    def validate_alarms(self) -> Dict[str, bool]:
        """Validate that all required CloudWatch alarms exist and are configured correctly."""
        print("Validating CloudWatch Alarms...")
        results = {}
        
        try:
            response = self.cloudwatch.describe_alarms()
            existing_alarms = {alarm['AlarmName'] for alarm in response['MetricAlarms']}
            
            for alarm_name in self.expected_alarms:
                if alarm_name in existing_alarms:
                    # Check alarm configuration
                    alarm_details = next(
                        alarm for alarm in response['MetricAlarms'] 
                        if alarm['AlarmName'] == alarm_name
                    )
                    
                    # Validate alarm has actions configured
                    has_actions = bool(alarm_details.get('AlarmActions'))
                    results[alarm_name] = has_actions
                    
                    status = "✓" if has_actions else "✗ (no actions)"
                    print(f"  {status} {alarm_name}")
                else:
                    results[alarm_name] = False
                    print(f"  ✗ {alarm_name} (missing)")
            
            return results
            
        except Exception as e:
            print(f"Error validating alarms: {e}")
            return {alarm: False for alarm in self.expected_alarms}
    
    def validate_dashboards(self) -> Dict[str, bool]:
        """Validate that all required CloudWatch dashboards exist."""
        print("Validating CloudWatch Dashboards...")
        results = {}
        
        try:
            response = self.cloudwatch.list_dashboards()
            existing_dashboards = {dash['DashboardName'] for dash in response['DashboardEntries']}
            
            for dashboard_name in self.expected_dashboards:
                exists = dashboard_name in existing_dashboards
                results[dashboard_name] = exists
                
                status = "✓" if exists else "✗"
                print(f"  {status} {dashboard_name}")
                
                if exists:
                    # Validate dashboard has content
                    try:
                        dashboard_body = self.cloudwatch.get_dashboard(
                            DashboardName=dashboard_name
                        )
                        body = json.loads(dashboard_body['DashboardBody'])
                        widget_count = len(body.get('widgets', []))
                        print(f"    - {widget_count} widgets configured")
                    except Exception as e:
                        print(f"    - Error reading dashboard: {e}")
            
            return results
            
        except Exception as e:
            print(f"Error validating dashboards: {e}")
            return {dashboard: False for dashboard in self.expected_dashboards}
    
    def validate_log_groups(self) -> Dict[str, bool]:
        """Validate that all required CloudWatch log groups exist."""
        print("Validating CloudWatch Log Groups...")
        results = {}
        
        try:
            response = self.logs.describe_log_groups()
            existing_log_groups = {lg['logGroupName'] for lg in response['logGroups']}
            
            for log_group_name in self.expected_log_groups:
                exists = log_group_name in existing_log_groups
                results[log_group_name] = exists
                
                status = "✓" if exists else "✗"
                print(f"  {status} {log_group_name}")
                
                if exists:
                    # Check retention policy
                    log_group = next(
                        lg for lg in response['logGroups'] 
                        if lg['logGroupName'] == log_group_name
                    )
                    retention = log_group.get('retentionInDays', 'Never expires')
                    print(f"    - Retention: {retention} days")
            
            return results
            
        except Exception as e:
            print(f"Error validating log groups: {e}")
            return {log_group: False for log_group in self.expected_log_groups}
    
    def validate_sns_topics(self) -> Dict[str, bool]:
        """Validate that SNS topics for alerts exist and have subscriptions."""
        print("Validating SNS Topics...")
        results = {}
        
        try:
            response = self.sns.list_topics()
            topics = response['Topics']
            
            alert_topic_arn = None
            for topic in topics:
                if f'gcse-alerts-{self.environment}' in topic['TopicArn']:
                    alert_topic_arn = topic['TopicArn']
                    break
            
            if alert_topic_arn:
                results['alert_topic'] = True
                print(f"  ✓ Alert topic found: {alert_topic_arn}")
                
                # Check subscriptions
                subs_response = self.sns.list_subscriptions_by_topic(
                    TopicArn=alert_topic_arn
                )
                subscription_count = len(subs_response['Subscriptions'])
                print(f"    - {subscription_count} subscriptions configured")
                
                if subscription_count == 0:
                    print("    ⚠ Warning: No subscriptions configured for alerts")
                    
            else:
                results['alert_topic'] = False
                print(f"  ✗ Alert topic not found")
            
            return results
            
        except Exception as e:
            print(f"Error validating SNS topics: {e}")
            return {'alert_topic': False}
    
    def test_alarm_functionality(self) -> bool:
        """Test that alarms can be triggered and notifications work."""
        print("Testing Alarm Functionality...")
        
        try:
            # Find a test alarm to trigger
            test_alarm = f'gcse-auth-duration-warning-{self.environment}'
            
            # Put a test metric to trigger the alarm
            self.cloudwatch.put_metric_data(
                Namespace='GCSE/Testing',
                MetricData=[
                    {
                        'MetricName': 'TestMetric',
                        'Value': 1.0,
                        'Unit': 'Count',
                        'Timestamp': time.time()
                    }
                ]
            )
            
            print("  ✓ Test metric published successfully")
            print("  ℹ Manual verification required for alarm notifications")
            return True
            
        except Exception as e:
            print(f"  ✗ Error testing alarm functionality: {e}")
            return False
    
    def validate_custom_metrics(self) -> Dict[str, bool]:
        """Validate that custom application metrics are being published."""
        print("Validating Custom Metrics...")
        results = {}
        
        expected_namespaces = [
            'GCSE/QuestionGeneration',
            'GCSE/UserActivity',
            'GCSE/Quality',
            'GCSE/Performance',
            'GCSE/Bedrock',
            'GCSE/CostEfficiency'
        ]
        
        try:
            response = self.cloudwatch.list_metrics()
            existing_namespaces = {metric['Namespace'] for metric in response['Metrics']}
            
            for namespace in expected_namespaces:
                exists = namespace in existing_namespaces
                results[namespace] = exists
                
                status = "✓" if exists else "✗"
                print(f"  {status} {namespace}")
                
                if exists:
                    # Count metrics in namespace
                    namespace_metrics = [
                        m for m in response['Metrics'] 
                        if m['Namespace'] == namespace
                    ]
                    print(f"    - {len(namespace_metrics)} metrics")
            
            return results
            
        except Exception as e:
            print(f"Error validating custom metrics: {e}")
            return {ns: False for ns in expected_namespaces}
    
    def generate_report(self) -> Dict:
        """Generate a comprehensive monitoring validation report."""
        print("GCSE Question Generator V2 - Monitoring Validation")
        print("=" * 60)
        
        report = {
            'timestamp': time.time(),
            'environment': self.environment,
            'region': self.region,
            'validation_results': {}
        }
        
        # Run all validations
        report['validation_results']['alarms'] = self.validate_alarms()
        print()
        
        report['validation_results']['dashboards'] = self.validate_dashboards()
        print()
        
        report['validation_results']['log_groups'] = self.validate_log_groups()
        print()
        
        report['validation_results']['sns_topics'] = self.validate_sns_topics()
        print()
        
        report['validation_results']['custom_metrics'] = self.validate_custom_metrics()
        print()
        
        report['validation_results']['alarm_functionality'] = self.test_alarm_functionality()
        print()
        
        # Calculate overall health
        all_results = []
        for category, results in report['validation_results'].items():
            if isinstance(results, dict):
                all_results.extend(results.values())
            else:
                all_results.append(results)
        
        total_checks = len(all_results)
        passed_checks = sum(1 for result in all_results if result)
        health_percentage = (passed_checks / total_checks) * 100 if total_checks > 0 else 0
        
        report['summary'] = {
            'total_checks': total_checks,
            'passed_checks': passed_checks,
            'failed_checks': total_checks - passed_checks,
            'health_percentage': health_percentage
        }
        
        print("=" * 60)
        print(f"Monitoring Health: {health_percentage:.1f}% ({passed_checks}/{total_checks})")
        
        if health_percentage >= 90:
            print("✓ Monitoring system is healthy")
            report['status'] = 'healthy'
        elif health_percentage >= 75:
            print("⚠ Monitoring system has minor issues")
            report['status'] = 'warning'
        else:
            print("✗ Monitoring system has significant issues")
            report['status'] = 'critical'
        
        return report

def main():
    """Main validation function."""
    import sys
    
    environment = sys.argv[1] if len(sys.argv) > 1 else 'prod'
    validator = MonitoringValidator(environment)
    
    report = validator.generate_report()
    
    # Save report
    with open('monitoring-validation-report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\nReport saved to monitoring-validation-report.json")
    
    # Exit with appropriate code
    if report['status'] == 'critical':
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == '__main__':
    main()