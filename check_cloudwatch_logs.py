#!/usr/bin/env python3
"""
CloudWatch Logs Analysis Script

This script checks CloudWatch logs for the Lambda functions to understand
why some GenerateLambda calls are failing and validate Bedrock API usage.
"""

import boto3
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Configuration
AWS_REGION = 'eu-west-2'
INTERPRET_LAMBDA_LOG_GROUP = '/aws/lambda/gcse-interpret-lambda-prod'
GENERATE_LAMBDA_LOG_GROUP = '/aws/lambda/gcse-generate-lambda-prod'

class CloudWatchLogsAnalyzer:
    """Analyzes CloudWatch logs for Lambda functions."""
    
    def __init__(self, region: str = AWS_REGION):
        self.region = region
        self.logs_client = boto3.client('logs', region_name=region)
    
    def get_recent_logs(self, log_group: str, hours: int = 1) -> List[Dict[str, Any]]:
        """
        Get recent log events from a log group.
        
        Args:
            log_group: CloudWatch log group name
            hours: Number of hours to look back
            
        Returns:
            List of log events
        """
        try:
            # Calculate time range
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)
            
            start_timestamp = int(start_time.timestamp() * 1000)
            end_timestamp = int(end_time.timestamp() * 1000)
            
            print(f"🔍 Checking logs in {log_group} from {start_time} to {end_time}")
            
            # Get log streams
            streams_response = self.logs_client.describe_log_streams(
                logGroupName=log_group,
                orderBy='LastEventTime',
                descending=True,
                limit=10
            )
            
            all_events = []
            
            for stream in streams_response['logStreams']:
                stream_name = stream['logStreamName']
                
                try:
                    # Get events from this stream
                    events_response = self.logs_client.get_log_events(
                        logGroupName=log_group,
                        logStreamName=stream_name,
                        startTime=start_timestamp,
                        endTime=end_timestamp
                    )
                    
                    for event in events_response['events']:
                        event['logStreamName'] = stream_name
                        all_events.append(event)
                        
                except Exception as e:
                    print(f"   ⚠️  Error reading stream {stream_name}: {str(e)}")
                    continue
            
            # Sort by timestamp
            all_events.sort(key=lambda x: x['timestamp'])
            
            print(f"   📊 Found {len(all_events)} log events")
            return all_events
            
        except Exception as e:
            print(f"   ❌ Error accessing log group {log_group}: {str(e)}")
            return []
    
    def analyze_bedrock_usage(self, log_events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze log events for Bedrock API usage.
        
        Args:
            log_events: List of CloudWatch log events
            
        Returns:
            Analysis of Bedrock usage
        """
        bedrock_calls = []
        bedrock_errors = []
        
        for event in log_events:
            message = event['message']
            
            # Look for Bedrock API calls
            if 'Calling Bedrock API' in message:
                try:
                    # Try to parse as JSON log
                    if message.strip().startswith('{'):
                        log_data = json.loads(message)
                        bedrock_calls.append({
                            'timestamp': event['timestamp'],
                            'request_id': log_data.get('request_id'),
                            'model_id': log_data.get('model_id'),
                            'attempt': log_data.get('attempt', 1)
                        })
                    else:
                        # Plain text log
                        bedrock_calls.append({
                            'timestamp': event['timestamp'],
                            'message': message,
                            'type': 'plain_text'
                        })
                except json.JSONDecodeError:
                    bedrock_calls.append({
                        'timestamp': event['timestamp'],
                        'message': message,
                        'type': 'plain_text'
                    })
            
            # Look for Bedrock errors
            if 'Bedrock API error' in message or 'Failed to generate questions with Bedrock' in message:
                try:
                    if message.strip().startswith('{'):
                        log_data = json.loads(message)
                        bedrock_errors.append({
                            'timestamp': event['timestamp'],
                            'request_id': log_data.get('request_id'),
                            'error': log_data.get('error'),
                            'error_code': log_data.get('error_code')
                        })
                    else:
                        bedrock_errors.append({
                            'timestamp': event['timestamp'],
                            'message': message,
                            'type': 'plain_text'
                        })
                except json.JSONDecodeError:
                    bedrock_errors.append({
                        'timestamp': event['timestamp'],
                        'message': message,
                        'type': 'plain_text'
                    })
        
        return {
            'total_bedrock_calls': len(bedrock_calls),
            'bedrock_calls': bedrock_calls,
            'total_bedrock_errors': len(bedrock_errors),
            'bedrock_errors': bedrock_errors
        }
    
    def analyze_generation_failures(self, log_events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze log events for question generation failures.
        
        Args:
            log_events: List of CloudWatch log events
            
        Returns:
            Analysis of generation failures
        """
        failures = []
        s3_errors = []
        
        for event in log_events:
            message = event['message']
            
            # Look for generation failures
            if 'Question generation failed' in message or 'Failed to generate questions' in message:
                try:
                    if message.strip().startswith('{'):
                        log_data = json.loads(message)
                        failures.append({
                            'timestamp': event['timestamp'],
                            'request_id': log_data.get('request_id'),
                            'error': log_data.get('error'),
                            'error_type': log_data.get('error_type'),
                            'generation_request': log_data.get('generation_request')
                        })
                    else:
                        failures.append({
                            'timestamp': event['timestamp'],
                            'message': message,
                            'type': 'plain_text'
                        })
                except json.JSONDecodeError:
                    failures.append({
                        'timestamp': event['timestamp'],
                        'message': message,
                        'type': 'plain_text'
                    })
            
            # Look for S3 errors
            if 'S3 service unavailable' in message or 'Failed to retrieve' in message:
                try:
                    if message.strip().startswith('{'):
                        log_data = json.loads(message)
                        s3_errors.append({
                            'timestamp': event['timestamp'],
                            'request_id': log_data.get('request_id'),
                            'error': log_data.get('error')
                        })
                    else:
                        s3_errors.append({
                            'timestamp': event['timestamp'],
                            'message': message,
                            'type': 'plain_text'
                        })
                except json.JSONDecodeError:
                    s3_errors.append({
                        'timestamp': event['timestamp'],
                        'message': message,
                        'type': 'plain_text'
                    })
        
        return {
            'total_failures': len(failures),
            'failures': failures,
            'total_s3_errors': len(s3_errors),
            's3_errors': s3_errors
        }
    
    def analyze_lambda_function(self, log_group: str, function_name: str) -> Dict[str, Any]:
        """
        Analyze a specific Lambda function's logs.
        
        Args:
            log_group: CloudWatch log group name
            function_name: Lambda function name for display
            
        Returns:
            Complete analysis of the function's logs
        """
        print(f"\n{'='*80}")
        print(f"📊 ANALYZING {function_name.upper()} LOGS")
        print(f"{'='*80}")
        
        # Get recent logs
        log_events = self.get_recent_logs(log_group, hours=2)
        
        if not log_events:
            return {
                'function_name': function_name,
                'log_group': log_group,
                'total_events': 0,
                'analysis': 'No recent log events found'
            }
        
        # Analyze Bedrock usage
        bedrock_analysis = self.analyze_bedrock_usage(log_events)
        
        # Analyze failures
        failure_analysis = self.analyze_generation_failures(log_events)
        
        # Print summary
        print(f"📈 Log Events Summary:")
        print(f"   Total events: {len(log_events)}")
        print(f"   Bedrock API calls: {bedrock_analysis['total_bedrock_calls']}")
        print(f"   Bedrock errors: {bedrock_analysis['total_bedrock_errors']}")
        print(f"   Generation failures: {failure_analysis['total_failures']}")
        print(f"   S3 errors: {failure_analysis['total_s3_errors']}")
        
        # Show recent Bedrock calls
        if bedrock_analysis['bedrock_calls']:
            print(f"\n🤖 Recent Bedrock API Calls:")
            for call in bedrock_analysis['bedrock_calls'][-5:]:  # Show last 5
                timestamp = datetime.fromtimestamp(call['timestamp'] / 1000)
                if call.get('type') == 'plain_text':
                    print(f"   {timestamp}: {call['message'][:100]}...")
                else:
                    print(f"   {timestamp}: Model {call.get('model_id', 'unknown')}, Request {call.get('request_id', 'unknown')[:8]}")
        
        # Show recent errors
        if bedrock_analysis['bedrock_errors']:
            print(f"\n❌ Recent Bedrock Errors:")
            for error in bedrock_analysis['bedrock_errors'][-3:]:  # Show last 3
                timestamp = datetime.fromtimestamp(error['timestamp'] / 1000)
                if error.get('type') == 'plain_text':
                    print(f"   {timestamp}: {error['message'][:150]}...")
                else:
                    print(f"   {timestamp}: {error.get('error', 'Unknown error')}")
        
        # Show generation failures
        if failure_analysis['failures']:
            print(f"\n💥 Recent Generation Failures:")
            for failure in failure_analysis['failures'][-3:]:  # Show last 3
                timestamp = datetime.fromtimestamp(failure['timestamp'] / 1000)
                if failure.get('type') == 'plain_text':
                    print(f"   {timestamp}: {failure['message'][:150]}...")
                else:
                    error_type = failure.get('error_type', 'Unknown')
                    error_msg = failure.get('error', 'Unknown error')
                    print(f"   {timestamp}: {error_type} - {error_msg}")
        
        return {
            'function_name': function_name,
            'log_group': log_group,
            'total_events': len(log_events),
            'bedrock_analysis': bedrock_analysis,
            'failure_analysis': failure_analysis
        }
    
    def run_comprehensive_analysis(self) -> Dict[str, Any]:
        """
        Run comprehensive analysis of both Lambda functions.
        
        Returns:
            Complete analysis results
        """
        print(f"\n{'='*100}")
        print(f"🔍 CLOUDWATCH LOGS ANALYSIS")
        print(f"{'='*100}")
        print(f"Analyzing recent logs to understand AI integration and failures")
        
        # Analyze InterpretLambda
        interpret_analysis = self.analyze_lambda_function(
            INTERPRET_LAMBDA_LOG_GROUP, 
            'InterpretLambda'
        )
        
        # Analyze GenerateLambda
        generate_analysis = self.analyze_lambda_function(
            GENERATE_LAMBDA_LOG_GROUP, 
            'GenerateLambda'
        )
        
        # Generate overall summary
        summary = self.generate_overall_summary(interpret_analysis, generate_analysis)
        
        return {
            'interpret_analysis': interpret_analysis,
            'generate_analysis': generate_analysis,
            'summary': summary,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def generate_overall_summary(self, interpret_analysis: Dict, generate_analysis: Dict) -> Dict[str, Any]:
        """
        Generate overall summary of the analysis.
        
        Args:
            interpret_analysis: InterpretLambda analysis results
            generate_analysis: GenerateLambda analysis results
            
        Returns:
            Overall summary
        """
        print(f"\n{'='*100}")
        print(f"📋 OVERALL ANALYSIS SUMMARY")
        print(f"{'='*100}")
        
        # Calculate totals
        total_bedrock_calls = (
            interpret_analysis.get('bedrock_analysis', {}).get('total_bedrock_calls', 0) +
            generate_analysis.get('bedrock_analysis', {}).get('total_bedrock_calls', 0)
        )
        
        total_bedrock_errors = (
            interpret_analysis.get('bedrock_analysis', {}).get('total_bedrock_errors', 0) +
            generate_analysis.get('bedrock_analysis', {}).get('total_bedrock_errors', 0)
        )
        
        total_generation_failures = generate_analysis.get('failure_analysis', {}).get('total_failures', 0)
        total_s3_errors = generate_analysis.get('failure_analysis', {}).get('total_s3_errors', 0)
        
        print(f"🎯 Key Findings:")
        print(f"   Total Bedrock API calls: {total_bedrock_calls}")
        print(f"   Total Bedrock errors: {total_bedrock_errors}")
        print(f"   Total generation failures: {total_generation_failures}")
        print(f"   Total S3 errors: {total_s3_errors}")
        
        # Determine AI integration status
        ai_integration_working = total_bedrock_calls > 0
        bedrock_success_rate = (total_bedrock_calls - total_bedrock_errors) / total_bedrock_calls if total_bedrock_calls > 0 else 0
        
        print(f"\n📊 Assessment:")
        if ai_integration_working:
            print(f"   ✅ AI integration is active (Bedrock calls detected)")
            print(f"   📈 Bedrock success rate: {bedrock_success_rate*100:.1f}%")
        else:
            print(f"   ❌ No Bedrock API calls detected - AI integration may be broken")
        
        if total_generation_failures > 0:
            print(f"   ⚠️  Generation failures detected - investigating causes")
        
        if total_s3_errors > 0:
            print(f"   ⚠️  S3 errors detected - content retrieval issues")
        
        return {
            'ai_integration_working': ai_integration_working,
            'total_bedrock_calls': total_bedrock_calls,
            'total_bedrock_errors': total_bedrock_errors,
            'bedrock_success_rate': bedrock_success_rate,
            'total_generation_failures': total_generation_failures,
            'total_s3_errors': total_s3_errors
        }


def main():
    """Main function to run CloudWatch logs analysis."""
    
    try:
        # Initialize analyzer
        analyzer = CloudWatchLogsAnalyzer()
        
        # Run comprehensive analysis
        results = analyzer.run_comprehensive_analysis()
        
        # Save results to file
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        results_file = f"cloudwatch_analysis_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n💾 Results saved to: {results_file}")
        
        # Return exit code based on analysis
        if results['summary']['ai_integration_working']:
            print("\n🎉 CloudWatch Analysis: AI Integration Active")
            return 0
        else:
            print("\n💥 CloudWatch Analysis: AI Integration Issues Detected")
            return 1
            
    except Exception as e:
        print(f"\n💥 Analysis failed: {str(e)}")
        return 1


if __name__ == "__main__":
    exit(main())