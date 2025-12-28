#!/usr/bin/env python3
"""
Architecture Flow Validation and Monitoring

This script creates comprehensive end-to-end flow testing, implements detailed logging
to trace request flow through the system, and validates that AI services are being called.
"""

import os
import sys
import json
import boto3
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import requests
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# AWS Configuration
AWS_REGION = 'eu-west-2'
INTERPRET_LAMBDA_NAME = 'gcse-interpret-lambda-prod'
GENERATE_LAMBDA_NAME = 'gcse-generate-lambda-prod'
API_GATEWAY_URL = 'https://api.gcse-questions.com'  # Update with actual URL

class ArchitectureFlowValidator:
    """Comprehensive architecture flow validation and monitoring"""
    
    def __init__(self):
        """Initialize the validator"""
        self.lambda_client = boto3.client('lambda', region_name=AWS_REGION)
        self.logs_client = boto3.client('logs', region_name=AWS_REGION)
        self.cloudwatch_client = boto3.client('cloudwatch', region_name=AWS_REGION)
        self.bedrock_client = boto3.client('bedrock-runtime', region_name=AWS_REGION)
        
        # Test configuration
        self.test_queries = [
            "Generate 3 Foundation fractions questions",
            "Create 2 Higher algebra equations",
            "I need some geometry questions about angles",
            "Make 4 statistics questions on averages",
            "Generate probability questions for Foundation tier"
        ]
        
    def trace_request_flow(self, query: str, api_key: Optional[str] = None) -> Dict[str, Any]:
        """Trace a complete request flow through the system"""
        
        logger.info(f"🔍 Tracing request flow for query: '{query[:50]}...'")
        
        flow_trace = {
            'query': query,
            'timestamp': datetime.now().isoformat(),
            'steps': [],
            'ai_calls': [],
            'errors': [],
            'performance': {},
            'success': False
        }
        
        start_time = time.time()
        
        try:
            # Step 1: Direct Lambda invocation (InterpretLambda)
            logger.info("Step 1: Testing InterpretLambda directly")
            step_start = time.time()
            
            interpret_payload = {
                'query': query,
                'trace_id': f"trace_{int(time.time())}",
                'disable_cache': True
            }
            
            interpret_response = self.lambda_client.invoke(
                FunctionName=INTERPRET_LAMBDA_NAME,
                Payload=json.dumps(interpret_payload)
            )
            
            interpret_result = json.loads(interpret_response['Payload'].read())
            step_duration = time.time() - step_start
            
            flow_trace['steps'].append({
                'step': 'interpret_lambda',
                'duration': step_duration,
                'status_code': interpret_response.get('StatusCode'),
                'response': interpret_result,
                'success': interpret_response.get('StatusCode') == 200
            })
            
            # Check for AI call in logs
            ai_call_detected = self.check_bedrock_usage('interpret', step_start)
            if ai_call_detected:
                flow_trace['ai_calls'].append({
                    'service': 'bedrock_haiku',
                    'function': 'interpret_lambda',
                    'timestamp': datetime.now().isoformat()
                })
            
            # Step 2: Direct Lambda invocation (GenerateLambda)
            if interpret_result.get('statusCode') == 200:
                logger.info("Step 2: Testing GenerateLambda directly")
                step_start = time.time()
                
                # Extract intent from interpret response
                intent_data = json.loads(interpret_result.get('body', '{}'))
                
                generate_payload = {
                    'topic': intent_data.get('topic', 'Number'),
                    'tier': intent_data.get('tier', 'Foundation'),
                    'count': intent_data.get('count', 3),
                    'trace_id': f"trace_{int(time.time())}",
                    'disable_cache': True
                }
                
                generate_response = self.lambda_client.invoke(
                    FunctionName=GENERATE_LAMBDA_NAME,
                    Payload=json.dumps(generate_payload)
                )
                
                generate_result = json.loads(generate_response['Payload'].read())
                step_duration = time.time() - step_start
                
                flow_trace['steps'].append({
                    'step': 'generate_lambda',
                    'duration': step_duration,
                    'status_code': generate_response.get('StatusCode'),
                    'response': generate_result,
                    'success': generate_response.get('StatusCode') == 200
                })
                
                # Check for AI call in logs
                ai_call_detected = self.check_bedrock_usage('generate', step_start)
                if ai_call_detected:
                    flow_trace['ai_calls'].append({
                        'service': 'bedrock_sonnet',
                        'function': 'generate_lambda',
                        'timestamp': datetime.now().isoformat()
                    })
            
            # Step 3: API Gateway integration test (if API key provided)
            if api_key:
                logger.info("Step 3: Testing API Gateway integration")
                step_start = time.time()
                
                headers = {
                    'Content-Type': 'application/json',
                    'X-API-Key': api_key
                }
                
                # Test /interpret endpoint
                interpret_url = f"{API_GATEWAY_URL}/interpret"
                api_response = requests.post(
                    interpret_url,
                    json={'query': query},
                    headers=headers,
                    timeout=30
                )
                
                step_duration = time.time() - step_start
                
                flow_trace['steps'].append({
                    'step': 'api_gateway_interpret',
                    'duration': step_duration,
                    'status_code': api_response.status_code,
                    'response': api_response.json() if api_response.status_code == 200 else api_response.text,
                    'success': api_response.status_code == 200
                })
            
            # Calculate overall performance
            total_duration = time.time() - start_time
            flow_trace['performance'] = {
                'total_duration': total_duration,
                'interpret_duration': next((s['duration'] for s in flow_trace['steps'] if s['step'] == 'interpret_lambda'), 0),
                'generate_duration': next((s['duration'] for s in flow_trace['steps'] if s['step'] == 'generate_lambda'), 0),
                'ai_calls_detected': len(flow_trace['ai_calls']),
                'steps_successful': sum(1 for s in flow_trace['steps'] if s['success'])
            }
            
            # Determine overall success
            flow_trace['success'] = (
                len(flow_trace['ai_calls']) >= 2 and  # Both AI services called
                flow_trace['performance']['steps_successful'] >= 2  # Both Lambda functions successful
            )
            
            logger.info(f"✅ Flow trace completed - Success: {flow_trace['success']}")
            
        except Exception as e:
            logger.error(f"❌ Flow trace failed: {str(e)}")
            flow_trace['errors'].append({
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
        
        return flow_trace
    
    def check_bedrock_usage(self, function_type: str, start_time: float) -> bool:
        """Check CloudWatch logs for Bedrock API usage"""
        
        try:
            function_name = INTERPRET_LAMBDA_NAME if function_type == 'interpret' else GENERATE_LAMBDA_NAME
            log_group_name = f"/aws/lambda/{function_name}"
            
            # Convert start_time to milliseconds
            start_time_ms = int(start_time * 1000)
            end_time_ms = int(time.time() * 1000)
            
            # Search for Bedrock-related log entries
            response = self.logs_client.filter_log_events(
                logGroupName=log_group_name,
                startTime=start_time_ms,
                endTime=end_time_ms,
                filterPattern="bedrock OR claude OR invoke_model"
            )
            
            events = response.get('events', [])
            return len(events) > 0
            
        except Exception as e:
            logger.warning(f"Could not check Bedrock usage for {function_type}: {str(e)}")
            return False
    
    def create_monitoring_dashboard(self) -> Dict[str, Any]:
        """Create CloudWatch dashboard for architecture monitoring"""
        
        logger.info("📊 Creating architecture monitoring dashboard")
        
        dashboard_body = {
            "widgets": [
                {
                    "type": "metric",
                    "x": 0,
                    "y": 0,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "metrics": [
                            ["AWS/Lambda", "Invocations", "FunctionName", INTERPRET_LAMBDA_NAME],
                            [".", "Duration", ".", "."],
                            [".", "Errors", ".", "."],
                            ["AWS/Lambda", "Invocations", "FunctionName", GENERATE_LAMBDA_NAME],
                            [".", "Duration", ".", "."],
                            [".", "Errors", ".", "."]
                        ],
                        "view": "timeSeries",
                        "stacked": False,
                        "region": AWS_REGION,
                        "title": "Lambda Function Performance",
                        "period": 300
                    }
                },
                {
                    "type": "log",
                    "x": 0,
                    "y": 6,
                    "width": 24,
                    "height": 6,
                    "properties": {
                        "query": f"SOURCE '/aws/lambda/{INTERPRET_LAMBDA_NAME}' | SOURCE '/aws/lambda/{GENERATE_LAMBDA_NAME}'\n| fields @timestamp, @message\n| filter @message like /bedrock|claude|invoke_model/\n| sort @timestamp desc\n| limit 20",
                        "region": AWS_REGION,
                        "title": "AI Service Usage (Bedrock Calls)",
                        "view": "table"
                    }
                },
                {
                    "type": "metric",
                    "x": 12,
                    "y": 0,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "metrics": [
                            ["AWS/ApiGateway", "Count", "ApiName", "gcse-question-generator-api"],
                            [".", "Latency", ".", "."],
                            [".", "4XXError", ".", "."],
                            [".", "5XXError", ".", "."]
                        ],
                        "view": "timeSeries",
                        "stacked": False,
                        "region": AWS_REGION,
                        "title": "API Gateway Performance",
                        "period": 300
                    }
                }
            ]
        }
        
        try:
            dashboard_name = "GCSE-Architecture-Flow-Monitor"
            
            self.cloudwatch_client.put_dashboard(
                DashboardName=dashboard_name,
                DashboardBody=json.dumps(dashboard_body)
            )
            
            logger.info(f"✅ Created dashboard: {dashboard_name}")
            
            return {
                'dashboard_created': True,
                'dashboard_name': dashboard_name,
                'dashboard_url': f"https://console.aws.amazon.com/cloudwatch/home?region={AWS_REGION}#dashboards:name={dashboard_name}"
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to create dashboard: {str(e)}")
            return {'dashboard_created': False, 'error': str(e)}
    
    def create_ai_service_alerts(self) -> Dict[str, Any]:
        """Create CloudWatch alarms for AI service monitoring"""
        
        logger.info("🚨 Creating AI service monitoring alerts")
        
        alerts_created = {}
        
        # Alert 1: No Bedrock calls detected
        try:
            alarm_name = "GCSE-No-Bedrock-Calls-Detected"
            
            self.cloudwatch_client.put_metric_alarm(
                AlarmName=alarm_name,
                ComparisonOperator='LessThanThreshold',
                EvaluationPeriods=2,
                MetricName='Invocations',
                Namespace='AWS/Lambda',
                Period=300,
                Statistic='Sum',
                Threshold=1.0,
                ActionsEnabled=True,
                AlarmDescription='Alert when no Lambda invocations detected (indicating AI services not being called)',
                Dimensions=[
                    {
                        'Name': 'FunctionName',
                        'Value': INTERPRET_LAMBDA_NAME
                    }
                ],
                Unit='Count'
            )
            
            alerts_created['no_bedrock_calls'] = True
            logger.info(f"✅ Created alarm: {alarm_name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to create Bedrock alert: {str(e)}")
            alerts_created['no_bedrock_calls'] = False
        
        # Alert 2: High error rate
        try:
            alarm_name = "GCSE-High-Lambda-Error-Rate"
            
            self.cloudwatch_client.put_metric_alarm(
                AlarmName=alarm_name,
                ComparisonOperator='GreaterThanThreshold',
                EvaluationPeriods=2,
                MetricName='Errors',
                Namespace='AWS/Lambda',
                Period=300,
                Statistic='Sum',
                Threshold=5.0,
                ActionsEnabled=True,
                AlarmDescription='Alert when Lambda error rate is high',
                Dimensions=[
                    {
                        'Name': 'FunctionName',
                        'Value': GENERATE_LAMBDA_NAME
                    }
                ],
                Unit='Count'
            )
            
            alerts_created['high_error_rate'] = True
            logger.info(f"✅ Created alarm: {alarm_name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to create error rate alert: {str(e)}")
            alerts_created['high_error_rate'] = False
        
        return alerts_created
    
    def run_comprehensive_validation(self, api_key: Optional[str] = None) -> Dict[str, Any]:
        """Run comprehensive architecture flow validation"""
        
        logger.info("🏗️ Starting comprehensive architecture flow validation")
        
        validation_results = {
            'timestamp': datetime.now().isoformat(),
            'test_queries': len(self.test_queries),
            'flow_traces': [],
            'ai_service_usage': {
                'bedrock_calls_detected': 0,
                'unique_ai_responses': 0,
                'cache_bypassed': 0
            },
            'performance_metrics': {
                'avg_interpret_duration': 0,
                'avg_generate_duration': 0,
                'total_test_duration': 0
            },
            'architecture_issues': [],
            'monitoring_setup': {},
            'overall_health': 'unknown'
        }
        
        start_time = time.time()
        
        try:
            # Step 1: Run flow traces for each test query
            logger.info("Step 1: Running flow traces for test queries")
            
            for i, query in enumerate(self.test_queries):
                logger.info(f"Testing query {i+1}/{len(self.test_queries)}: {query}")
                
                flow_trace = self.trace_request_flow(query, api_key)
                validation_results['flow_traces'].append(flow_trace)
                
                # Aggregate metrics
                if flow_trace['success']:
                    validation_results['ai_service_usage']['bedrock_calls_detected'] += len(flow_trace['ai_calls'])
                    if len(flow_trace['ai_calls']) >= 2:
                        validation_results['ai_service_usage']['unique_ai_responses'] += 1
                
                # Wait between tests to avoid rate limiting
                time.sleep(2)
            
            # Step 2: Analyze performance metrics
            logger.info("Step 2: Analyzing performance metrics")
            
            successful_traces = [t for t in validation_results['flow_traces'] if t['success']]
            
            if successful_traces:
                interpret_durations = [t['performance']['interpret_duration'] for t in successful_traces]
                generate_durations = [t['performance']['generate_duration'] for t in successful_traces]
                
                validation_results['performance_metrics'] = {
                    'avg_interpret_duration': sum(interpret_durations) / len(interpret_durations),
                    'avg_generate_duration': sum(generate_durations) / len(generate_durations),
                    'total_test_duration': time.time() - start_time,
                    'success_rate': len(successful_traces) / len(validation_results['flow_traces'])
                }
            
            # Step 3: Identify architecture issues
            logger.info("Step 3: Identifying architecture issues")
            
            issues = []
            
            # Check if AI services are being called
            if validation_results['ai_service_usage']['bedrock_calls_detected'] == 0:
                issues.append({
                    'type': 'critical',
                    'issue': 'No Bedrock AI calls detected',
                    'description': 'Lambda functions may be returning cached responses without calling AI services',
                    'recommendation': 'Check cache configuration and ensure DISABLE_QUESTION_CACHING is set'
                })
            
            # Check success rate
            success_rate = validation_results['performance_metrics'].get('success_rate', 0)
            if success_rate < 0.8:
                issues.append({
                    'type': 'warning',
                    'issue': f'Low success rate: {success_rate:.1%}',
                    'description': 'Many requests are failing in the architecture flow',
                    'recommendation': 'Check Lambda function logs and error handling'
                })
            
            # Check performance
            avg_total = (validation_results['performance_metrics'].get('avg_interpret_duration', 0) + 
                        validation_results['performance_metrics'].get('avg_generate_duration', 0))
            if avg_total > 45:  # 45 seconds total
                issues.append({
                    'type': 'warning',
                    'issue': f'Slow response times: {avg_total:.1f}s average',
                    'description': 'Architecture flow is taking longer than expected',
                    'recommendation': 'Optimize Lambda functions and check Bedrock response times'
                })
            
            validation_results['architecture_issues'] = issues
            
            # Step 4: Set up monitoring
            logger.info("Step 4: Setting up monitoring and alerts")
            
            dashboard_result = self.create_monitoring_dashboard()
            alerts_result = self.create_ai_service_alerts()
            
            validation_results['monitoring_setup'] = {
                'dashboard': dashboard_result,
                'alerts': alerts_result
            }
            
            # Step 5: Determine overall health
            if len(issues) == 0 and success_rate >= 0.8:
                validation_results['overall_health'] = 'healthy'
            elif any(i['type'] == 'critical' for i in issues):
                validation_results['overall_health'] = 'critical'
            else:
                validation_results['overall_health'] = 'warning'
            
            logger.info(f"✅ Validation completed - Overall health: {validation_results['overall_health']}")
            
        except Exception as e:
            logger.error(f"💥 Validation failed: {str(e)}")
            validation_results['error'] = str(e)
            validation_results['overall_health'] = 'error'
        
        return validation_results

def main():
    """Main validation function"""
    
    print("🏗️ ARCHITECTURE FLOW VALIDATION AND MONITORING")
    print("=" * 60)
    
    try:
        validator = ArchitectureFlowValidator()
        
        # Get API key from environment or user input
        api_key = os.getenv('GCSE_API_KEY')
        if not api_key:
            print("⚠️ No API key found in GCSE_API_KEY environment variable")
            print("   Some tests will be skipped (API Gateway integration)")
        
        results = validator.run_comprehensive_validation(api_key)
        
        # Print summary
        print(f"\n📊 Validation Results:")
        print(f"   Test queries: {results['test_queries']}")
        print(f"   Successful traces: {sum(1 for t in results['flow_traces'] if t['success'])}")
        print(f"   Bedrock calls detected: {results['ai_service_usage']['bedrock_calls_detected']}")
        print(f"   Overall health: {results['overall_health'].upper()}")
        
        # Print performance metrics
        perf = results['performance_metrics']
        if perf.get('success_rate'):
            print(f"\n⚡ Performance Metrics:")
            print(f"   Success rate: {perf['success_rate']:.1%}")
            print(f"   Avg interpret duration: {perf['avg_interpret_duration']:.2f}s")
            print(f"   Avg generate duration: {perf['avg_generate_duration']:.2f}s")
        
        # Print issues
        if results['architecture_issues']:
            print(f"\n⚠️ Architecture Issues Found:")
            for issue in results['architecture_issues']:
                print(f"   [{issue['type'].upper()}] {issue['issue']}")
                print(f"      → {issue['recommendation']}")
        
        # Print monitoring setup
        monitoring = results['monitoring_setup']
        if monitoring.get('dashboard', {}).get('dashboard_created'):
            print(f"\n📊 Monitoring Dashboard Created:")
            print(f"   {monitoring['dashboard']['dashboard_url']}")
        
        # Save detailed results
        with open('architecture_validation_results.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n💾 Detailed results saved to: architecture_validation_results.json")
        
        if results['overall_health'] in ['healthy', 'warning']:
            print(f"\n🎉 Architecture validation completed!")
            return True
        else:
            print(f"\n💥 Architecture has critical issues that need attention.")
            return False
            
    except Exception as e:
        print(f"\n💥 Validation failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)