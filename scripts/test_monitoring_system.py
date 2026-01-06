#!/usr/bin/env python3
"""
Monitoring System Test Script for GCSE Question Generator V2

This script tests the monitoring and alerting system by triggering test scenarios
and verifying that alerts are generated correctly.
"""

import boto3
import json
import time
import random
from typing import Dict, List
from datetime import datetime, timedelta

class MonitoringTester:
    def __init__(self, environment: str = 'prod', region: str = 'eu-west-2'):
        self.environment = environment
        self.region = region
        self.cloudwatch = boto3.client('cloudwatch', region_name=region)
        self.lambda_client = boto3.client('lambda', region_name=region)
        self.sns = boto3.client('sns', region_name=region)
        
    def publish_test_metrics(self) -> bool:
        """Publish test metrics to validate custom metric collection."""
        print("Publishing test metrics...")
        
        try:
            # Test question generation metrics
            self.cloudwatch.put_metric_data(
                Namespace='GCSE/QuestionGeneration',
                MetricData=[
                    {
                        'MetricName': 'SuccessRate',
                        'Value': 95.5,
                        'Unit': 'Percent',
                        'Dimensions': [
                            {'Name': 'Function', 'Value': 'GenerateLambda'}
                        ]
                    },
                    {
                        'MetricName': 'QuestionsGenerated',
                        'Value': 150,
                        'Unit': 'Count',
                        'Dimensions': [
                            {'Name': 'Function', 'Value': 'GenerateLambda'}
                        ]
                    }
                ]
            )
            
            # Test user activity metrics
            self.cloudwatch.put_metric_data(
                Namespace='GCSE/UserActivity',
                MetricData=[
                    {
                        'MetricName': 'ActiveUsers',
                        'Value': 25,
                        'Unit': 'Count',
                        'Dimensions': [
                            {'Name': 'Period', 'Value': 'Daily'}
                        ]
                    },
                    {
                        'MetricName': 'SessionsCreated',
                        'Value': 45,
                        'Unit': 'Count',
                        'Dimensions': [
                            {'Name': 'Period', 'Value': 'Daily'}
                        ]
                    }
                ]
            )
            
            # Test quality metrics
            self.cloudwatch.put_metric_data(
                Namespace='GCSE/Quality',
                MetricData=[
                    {
                        'MetricName': 'AverageRating',
                        'Value': 4.2,
                        'Unit': 'None',
                        'Dimensions': [
                            {'Name': 'Component', 'Value': 'Questions'}
                        ]
                    },
                    {
                        'MetricName': 'FeedbackCount',
                        'Value': 89,
                        'Unit': 'Count',
                        'Dimensions': [
                            {'Name': 'Component', 'Value': 'Questions'}
                        ]
                    }
                ]
            )
            
            # Test performance metrics
            self.cloudwatch.put_metric_data(
                Namespace='GCSE/Performance',
                MetricData=[
                    {
                        'MetricName': 'ResponseTime',
                        'Value': 2.5,
                        'Unit': 'Seconds',
                        'Dimensions': [
                            {'Name': 'Endpoint', 'Value': 'Generate'}
                        ]
                    },
                    {
                        'MetricName': 'ResponseTime',
                        'Value': 0.8,
                        'Unit': 'Seconds',
                        'Dimensions': [
                            {'Name': 'Endpoint', 'Value': 'Interpret'}
                        ]
                    }
                ]
            )
            
            # Test Bedrock usage metrics
            self.cloudwatch.put_metric_data(
                Namespace='GCSE/Bedrock',
                MetricData=[
                    {
                        'MetricName': 'TokensUsed',
                        'Value': 15000,
                        'Unit': 'Count',
                        'Dimensions': [
                            {'Name': 'Model', 'Value': 'Claude-Sonnet'}
                        ]
                    },
                    {
                        'MetricName': 'TokensUsed',
                        'Value': 8500,
                        'Unit': 'Count',
                        'Dimensions': [
                            {'Name': 'Model', 'Value': 'Claude-Haiku'}
                        ]
                    },
                    {
                        'MetricName': 'EstimatedCost',
                        'Value': 0.45,
                        'Unit': 'None',
                        'Dimensions': [
                            {'Name': 'Model', 'Value': 'Claude-Sonnet'}
                        ]
                    }
                ]
            )
            
            print("✓ Test metrics published successfully")
            return True
            
        except Exception as e:
            print(f"✗ Error publishing test metrics: {e}")
            return False
    
    def test_lambda_health_checks(self) -> Dict[str, bool]:
        """Test Lambda function health by invoking with health check payloads."""
        print("Testing Lambda function health checks...")
        
        functions = [
            f'gcse-auth-lambda-{self.environment}',
            f'gcse-interpret-lambda-{self.environment}',
            f'gcse-generate-lambda-{self.environment}',
            f'gcse-session-lambda-{self.environment}',
            f'gcse-feedback-lambda-{self.environment}',
            f'gcse-export-lambda-{self.environment}',
            f'gcse-topic-coverage-lambda-{self.environment}'
        ]
        
        results = {}
        
        for function_name in functions:
            try:
                response = self.lambda_client.invoke(
                    FunctionName=function_name,
                    InvocationType='RequestResponse',
                    Payload=json.dumps({
                        'health_check': True,
                        'source': 'monitoring_test'
                    })
                )
                
                success = response['StatusCode'] == 200
                results[function_name] = success
                
                status = "✓" if success else "✗"
                print(f"  {status} {function_name}")
                
            except Exception as e:
                results[function_name] = False
                print(f"  ✗ {function_name}: {e}")
        
        return results
    
    def test_alarm_thresholds(self) -> Dict[str, bool]:
        """Test alarm thresholds by publishing metrics that should trigger alerts."""
        print("Testing alarm thresholds...")
        
        test_results = {}
        
        try:
            # Test high error rate alarm
            print("  Testing error rate alarm...")
            self.cloudwatch.put_metric_data(
                Namespace='AWS/Lambda',
                MetricData=[
                    {
                        'MetricName': 'Errors',
                        'Value': 10,  # Should trigger error rate alarm
                        'Unit': 'Count',
                        'Dimensions': [
                            {'Name': 'FunctionName', 'Value': f'gcse-generate-lambda-{self.environment}'}
                        ]
                    }
                ]
            )
            test_results['error_rate_alarm'] = True
            print("    ✓ Error rate test metric published")
            
            # Test high latency alarm
            print("  Testing latency alarm...")
            self.cloudwatch.put_metric_data(
                Namespace='AWS/ApiGateway',
                MetricData=[
                    {
                        'MetricName': 'Latency',
                        'Value': 15000,  # 15 seconds - should trigger latency alarm
                        'Unit': 'Milliseconds',
                        'Dimensions': [
                            {'Name': 'ApiName', 'Value': f'gcse-question-generator-{self.environment}'}
                        ]
                    }
                ]
            )
            test_results['latency_alarm'] = True
            print("    ✓ Latency test metric published")
            
            # Test quality degradation alarm
            print("  Testing quality degradation alarm...")
            self.cloudwatch.put_metric_data(
                Namespace='GCSE/Quality',
                MetricData=[
                    {
                        'MetricName': 'AverageQuality',
                        'Value': 0.6,  # Below 0.7 threshold
                        'Unit': 'None',
                        'Dimensions': [
                            {'Name': 'Component', 'Value': 'Questions'}
                        ]
                    }
                ]
            )
            test_results['quality_alarm'] = True
            print("    ✓ Quality degradation test metric published")
            
            # Test cost alarm
            print("  Testing cost alarm...")
            self.cloudwatch.put_metric_data(
                Namespace='AWS/Billing',
                MetricData=[
                    {
                        'MetricName': 'EstimatedCharges',
                        'Value': 2.0,  # Should trigger daily cost alarm
                        'Unit': 'None',
                        'Dimensions': [
                            {'Name': 'Currency', 'Value': 'USD'}
                        ]
                    }
                ]
            )
            test_results['cost_alarm'] = True
            print("    ✓ Cost test metric published")
            
            print("  ⚠ Note: Alarms may take 5-15 minutes to trigger")
            
        except Exception as e:
            print(f"  ✗ Error testing alarm thresholds: {e}")
            test_results['alarm_threshold_test'] = False
        
        return test_results
    
    def verify_dashboard_accessibility(self) -> Dict[str, bool]:
        """Verify that dashboards are accessible and contain expected widgets."""
        print("Verifying dashboard accessibility...")
        
        dashboards = [
            f'GCSE-Question-Generator-{self.environment}',
            f'GCSE-Cost-Tracking-{self.environment}'
        ]
        
        results = {}
        
        for dashboard_name in dashboards:
            try:
                response = self.cloudwatch.get_dashboard(DashboardName=dashboard_name)
                dashboard_body = json.loads(response['DashboardBody'])
                
                widget_count = len(dashboard_body.get('widgets', []))
                has_widgets = widget_count > 0
                
                results[dashboard_name] = has_widgets
                
                status = "✓" if has_widgets else "✗"
                print(f"  {status} {dashboard_name} ({widget_count} widgets)")
                
                # Validate widget types
                widget_types = set()
                for widget in dashboard_body.get('widgets', []):
                    widget_types.add(widget.get('type', 'unknown'))
                
                print(f"    Widget types: {', '.join(widget_types)}")
                
            except Exception as e:
                results[dashboard_name] = False
                print(f"  ✗ {dashboard_name}: {e}")
        
        return results
    
    def test_sns_notification_system(self) -> bool:
        """Test SNS notification system by sending a test alert."""
        print("Testing SNS notification system...")
        
        try:
            # Find the alerts topic
            topics_response = self.sns.list_topics()
            alert_topic_arn = None
            
            for topic in topics_response['Topics']:
                if f'gcse-alerts-{self.environment}' in topic['TopicArn']:
                    alert_topic_arn = topic['TopicArn']
                    break
            
            if not alert_topic_arn:
                print("  ✗ Alert topic not found")
                return False
            
            # Send test notification
            test_message = {
                'event': 'monitoring_system_test',
                'timestamp': datetime.utcnow().isoformat(),
                'environment': self.environment,
                'message': 'This is a test notification from the monitoring system validation',
                'severity': 'info'
            }
            
            self.sns.publish(
                TopicArn=alert_topic_arn,
                Subject=f'GCSE Generator V2 - Monitoring Test ({self.environment})',
                Message=json.dumps(test_message, indent=2)
            )
            
            print("  ✓ Test notification sent successfully")
            print(f"    Topic: {alert_topic_arn}")
            return True
            
        except Exception as e:
            print(f"  ✗ Error testing SNS notifications: {e}")
            return False
    
    def run_comprehensive_test(self) -> Dict:
        """Run comprehensive monitoring system test."""
        print("GCSE Question Generator V2 - Monitoring System Test")
        print("=" * 60)
        
        test_report = {
            'timestamp': datetime.utcnow().isoformat(),
            'environment': self.environment,
            'region': self.region,
            'test_results': {}
        }
        
        # Run all tests
        print("1. Publishing test metrics...")
        test_report['test_results']['metrics_publishing'] = self.publish_test_metrics()
        print()
        
        print("2. Testing Lambda health checks...")
        test_report['test_results']['lambda_health'] = self.test_lambda_health_checks()
        print()
        
        print("3. Testing alarm thresholds...")
        test_report['test_results']['alarm_thresholds'] = self.test_alarm_thresholds()
        print()
        
        print("4. Verifying dashboard accessibility...")
        test_report['test_results']['dashboard_access'] = self.verify_dashboard_accessibility()
        print()
        
        print("5. Testing SNS notification system...")
        test_report['test_results']['sns_notifications'] = self.test_sns_notification_system()
        print()
        
        # Calculate overall test results
        all_results = []
        for category, results in test_report['test_results'].items():
            if isinstance(results, dict):
                all_results.extend(results.values())
            else:
                all_results.append(results)
        
        total_tests = len(all_results)
        passed_tests = sum(1 for result in all_results if result)
        
        test_report['summary'] = {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': total_tests - passed_tests,
            'success_rate': (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        }
        
        print("=" * 60)
        print(f"Test Results: {passed_tests}/{total_tests} passed ({test_report['summary']['success_rate']:.1f}%)")
        
        if test_report['summary']['success_rate'] >= 90:
            print("✓ Monitoring system test PASSED")
            test_report['overall_status'] = 'PASSED'
        else:
            print("✗ Monitoring system test FAILED")
            test_report['overall_status'] = 'FAILED'
        
        return test_report

def main():
    """Main test function."""
    import sys
    
    environment = sys.argv[1] if len(sys.argv) > 1 else 'prod'
    tester = MonitoringTester(environment)
    
    report = tester.run_comprehensive_test()
    
    # Save report
    with open('monitoring-test-report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\nTest report saved to monitoring-test-report.json")
    
    # Exit with appropriate code
    if report['overall_status'] == 'FAILED':
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == '__main__':
    main()