#!/usr/bin/env python3
"""
Test Bedrock integration to verify AI calls are working correctly.
This script tests both InterpretLambda and GenerateLambda Bedrock integration.
"""

import json
import boto3
import logging
import time
from datetime import datetime
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# AWS Configuration
AWS_REGION = 'eu-west-2'

def test_interpret_lambda_bedrock():
    """Test InterpretLambda Bedrock integration."""
    print("🧠 TESTING INTERPRET LAMBDA BEDROCK INTEGRATION")
    print("=" * 60)
    
    lambda_client = boto3.client('lambda', region_name=AWS_REGION)
    
    test_queries = [
        "Generate 3 foundation fractions questions",
        "I need 2 higher algebra questions about quadratics", 
        "Create 1 geometry question on pythagoras"
    ]
    
    results = []
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n🔍 Test {i}: {query}")
        
        try:
            # Prepare Lambda payload
            payload = {
                "httpMethod": "POST",
                "headers": {
                    "Content-Type": "application/json",
                    "X-API-Key": "test-key-for-bedrock-verification"
                },
                "body": json.dumps({"query": query})
            }
            
            start_time = time.time()
            
            # Invoke InterpretLambda
            response = lambda_client.invoke(
                FunctionName='gcse-interpret-lambda-prod',
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            
            execution_time = time.time() - start_time
            
            # Parse response
            response_payload = json.loads(response['Payload'].read())
            status_code = response_payload.get('statusCode', 500)
            
            if status_code == 200:
                body = json.loads(response_payload['body'])
                print(f"   ✅ Success ({execution_time:.2f}s)")
                print(f"   📊 Topic: {body.get('topic')}, Tier: {body.get('tier')}, Count: {body.get('count')}")
                print(f"   🎯 Confidence: {body.get('confidence', 0):.2f}")
                
                results.append({
                    'query': query,
                    'status': 'success',
                    'execution_time': execution_time,
                    'topic': body.get('topic'),
                    'tier': body.get('tier'),
                    'count': body.get('count'),
                    'confidence': body.get('confidence')
                })
            else:
                error_body = json.loads(response_payload['body'])
                print(f"   ❌ Failed (Status: {status_code})")
                print(f"   💥 Error: {error_body.get('error', {}).get('message', 'Unknown error')}")
                
                results.append({
                    'query': query,
                    'status': 'failed',
                    'error': error_body.get('error', {}).get('message', 'Unknown error')
                })
                
        except Exception as e:
            print(f"   💥 Exception: {str(e)}")
            results.append({
                'query': query,
                'status': 'exception',
                'error': str(e)
            })
    
    return results

def test_generate_lambda_bedrock():
    """Test GenerateLambda Bedrock integration."""
    print("\n\n🎯 TESTING GENERATE LAMBDA BEDROCK INTEGRATION")
    print("=" * 60)
    
    lambda_client = boto3.client('lambda', region_name=AWS_REGION)
    
    test_requests = [
        {
            "topic": "Number",
            "subtopic": "fractions",
            "tier": "Foundation",
            "count": 2,
            "specification_version": "latest"
        },
        {
            "topic": "Algebra", 
            "subtopic": "linear-equations",
            "tier": "Foundation",
            "count": 1,
            "specification_version": "latest"
        }
    ]
    
    results = []
    
    for i, request in enumerate(test_requests, 1):
        print(f"\n🔍 Test {i}: {request['topic']} - {request['subtopic']} ({request['tier']})")
        
        try:
            # Prepare Lambda payload
            payload = {
                "httpMethod": "POST",
                "headers": {
                    "Content-Type": "application/json",
                    "X-API-Key": "test-key-for-bedrock-verification"
                },
                "body": json.dumps(request)
            }
            
            start_time = time.time()
            
            # Invoke GenerateLambda
            response = lambda_client.invoke(
                FunctionName='gcse-generate-lambda-prod',
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            
            execution_time = time.time() - start_time
            
            # Parse response
            response_payload = json.loads(response['Payload'].read())
            status_code = response_payload.get('statusCode', 500)
            
            if status_code == 200:
                body = json.loads(response_payload['body'])
                questions = body.get('questions', [])
                metadata = body.get('metadata', {})
                
                print(f"   ✅ Success ({execution_time:.2f}s)")
                print(f"   📊 Generated: {len(questions)} questions, {metadata.get('total_marks', 0)} total marks")
                
                # Check for difficulty scores
                difficulty_scores = [q.get('difficulty_score') for q in questions if 'difficulty_score' in q]
                if difficulty_scores:
                    print(f"   🎯 Difficulty scores: {difficulty_scores}")
                else:
                    print(f"   ⚠️  No difficulty scores found")
                
                results.append({
                    'request': request,
                    'status': 'success',
                    'execution_time': execution_time,
                    'question_count': len(questions),
                    'total_marks': metadata.get('total_marks', 0),
                    'has_difficulty_scores': len(difficulty_scores) > 0,
                    'difficulty_scores': difficulty_scores
                })
            else:
                error_body = json.loads(response_payload['body'])
                print(f"   ❌ Failed (Status: {status_code})")
                print(f"   💥 Error: {error_body.get('error', {}).get('message', 'Unknown error')}")
                
                results.append({
                    'request': request,
                    'status': 'failed',
                    'error': error_body.get('error', {}).get('message', 'Unknown error')
                })
                
        except Exception as e:
            print(f"   💥 Exception: {str(e)}")
            results.append({
                'request': request,
                'status': 'exception',
                'error': str(e)
            })
    
    return results

def check_cloudwatch_logs():
    """Check CloudWatch logs for Bedrock API calls."""
    print("\n\n📊 CHECKING CLOUDWATCH LOGS FOR BEDROCK CALLS")
    print("=" * 60)
    
    logs_client = boto3.client('logs', region_name=AWS_REGION)
    
    # Check logs for both Lambda functions
    log_groups = [
        '/aws/lambda/gcse-interpret-lambda-prod',
        '/aws/lambda/gcse-generate-lambda-prod'
    ]
    
    # Look for logs from the last hour
    end_time = int(time.time() * 1000)
    start_time = end_time - (60 * 60 * 1000)  # 1 hour ago
    
    bedrock_calls_found = 0
    
    for log_group in log_groups:
        try:
            print(f"\n🔍 Checking {log_group}")
            
            # Get log events
            response = logs_client.filter_log_events(
                logGroupName=log_group,
                startTime=start_time,
                endTime=end_time,
                filterPattern='Bedrock'
            )
            
            events = response.get('events', [])
            print(f"   📝 Found {len(events)} Bedrock-related log entries")
            
            # Look for specific Bedrock API call patterns
            api_calls = 0
            for event in events:
                message = event.get('message', '')
                if 'Calling Bedrock' in message or 'Bedrock API call successful' in message:
                    api_calls += 1
                    print(f"   ✅ {event.get('timestamp')}: {message[:100]}...")
            
            bedrock_calls_found += api_calls
            print(f"   🎯 Bedrock API calls detected: {api_calls}")
            
        except Exception as e:
            print(f"   ❌ Error checking {log_group}: {str(e)}")
    
    return bedrock_calls_found

def main():
    """Main function to test Bedrock integration."""
    print("🚀 BEDROCK INTEGRATION VERIFICATION")
    print("=" * 60)
    print(f"📅 Test started at: {datetime.now().isoformat()}")
    
    try:
        # Test InterpretLambda
        interpret_results = test_interpret_lambda_bedrock()
        
        # Test GenerateLambda  
        generate_results = test_generate_lambda_bedrock()
        
        # Check CloudWatch logs
        bedrock_calls = check_cloudwatch_logs()
        
        # Print summary
        print("\n\n📊 BEDROCK INTEGRATION TEST SUMMARY")
        print("=" * 60)
        
        # InterpretLambda summary
        interpret_success = len([r for r in interpret_results if r['status'] == 'success'])
        print(f"🧠 InterpretLambda: {interpret_success}/{len(interpret_results)} successful")
        
        # GenerateLambda summary
        generate_success = len([r for r in generate_results if r['status'] == 'success'])
        print(f"🎯 GenerateLambda: {generate_success}/{len(generate_results)} successful")
        
        # Difficulty scoring check
        difficulty_tests = [r for r in generate_results if r['status'] == 'success' and r.get('has_difficulty_scores')]
        print(f"🎯 Difficulty Scoring: {len(difficulty_tests)}/{generate_success} questions have difficulty scores")
        
        # CloudWatch logs
        print(f"📊 CloudWatch: {bedrock_calls} Bedrock API calls detected in logs")
        
        # Overall assessment
        total_tests = len(interpret_results) + len(generate_results)
        total_success = interpret_success + generate_success
        success_rate = (total_success / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"\n🎉 Overall Success Rate: {success_rate:.1f}% ({total_success}/{total_tests})")
        
        if success_rate >= 80 and bedrock_calls > 0:
            print("✅ BEDROCK INTEGRATION VERIFIED - System is working correctly!")
            return True
        else:
            print("❌ BEDROCK INTEGRATION ISSUES DETECTED - Review failed tests")
            return False
            
    except Exception as e:
        logger.error(f"Test failed: {e}")
        print(f"\n💥 Test failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)