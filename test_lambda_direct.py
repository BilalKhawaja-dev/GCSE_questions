#!/usr/bin/env python3
"""
Test parallel optimization by invoking Lambda functions directly.
"""

import boto3
import json
import time
from datetime import datetime

def test_async_worker_direct():
    """Test the async worker Lambda directly with SQS-like payload."""
    
    print("🧪 Testing Async Worker Lambda Directly")
    print("=" * 50)
    
    lambda_client = boto3.client('lambda')
    
    # Test cases
    test_cases = [
        (5, "Small batch"),
        (10, "Medium batch"), 
        (20, "Large batch")
    ]
    
    for count, description in test_cases:
        print(f"\n📊 Testing: {description} ({count} questions)")
        
        # Create SQS-like message payload
        sqs_message = {
            "Records": [
                {
                    "body": json.dumps({
                        "job_id": f"test_job_{count}_{int(time.time())}",
                        "session_id": f"test_session_{count}_{int(time.time())}",
                        "topic": "Algebra",
                        "tier": "Foundation",
                        "count": count,
                        "enriched_prompt": f"Generate {count} Foundation algebra questions for testing parallel processing",
                        "user_id": "test_user",
                        "request_id": f"test_request_{count}_{int(time.time())}"
                    })
                }
            ]
        }
        
        try:
            start_time = time.time()
            
            # Invoke the async worker Lambda
            response = lambda_client.invoke(
                FunctionName='gcse-async-worker-lambda-prod',
                InvocationType='RequestResponse',  # Synchronous for testing
                Payload=json.dumps(sqs_message)
            )
            
            # Parse response
            response_payload = json.loads(response['Payload'].read())
            execution_time = time.time() - start_time
            
            print(f"   Status Code: {response['StatusCode']}")
            print(f"   Execution Time: {execution_time:.2f}s")
            
            if response['StatusCode'] == 200:
                body = json.loads(response_payload.get('body', '{}'))
                if body.get('success'):
                    results = body.get('results', [])
                    if results:
                        result = results[0]
                        questions_generated = result.get('questions_generated', 0)
                        generation_time = result.get('generation_time', 0)
                        
                        print(f"   ✅ Success: {questions_generated} questions generated")
                        print(f"   Generation Time: {generation_time:.2f}s")
                        print(f"   Questions/Second: {questions_generated/generation_time:.1f}")
                    else:
                        print(f"   ⚠️  No results in response")
                else:
                    print(f"   ❌ Lambda returned success=false")
            else:
                print(f"   ❌ Lambda failed with status {response['StatusCode']}")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")

def test_generate_lambda_direct():
    """Test the generate Lambda directly."""
    
    print("\n🧪 Testing Generate Lambda Directly")
    print("=" * 50)
    
    lambda_client = boto3.client('lambda')
    
    # Test small request (should be sync)
    print(f"\n📊 Testing: Small request (3 questions - should be sync)")
    
    api_event = {
        "body": json.dumps({
            "topic": "Algebra",
            "tier": "Foundation", 
            "count": 3,
            "enriched_prompt": "Generate 3 Foundation algebra questions",
            "user_id": "test_user",
            "session_token": "test_token"
        }),
        "requestContext": {
            "authorizer": {
                "user_id": "test_user",
                "session_token": "test_token"
            }
        }
    }
    
    try:
        start_time = time.time()
        
        response = lambda_client.invoke(
            FunctionName='gcse-generate-lambda-prod',
            InvocationType='RequestResponse',
            Payload=json.dumps(api_event)
        )
        
        response_payload = json.loads(response['Payload'].read())
        execution_time = time.time() - start_time
        
        print(f"   Status Code: {response['StatusCode']}")
        print(f"   Execution Time: {execution_time:.2f}s")
        
        if response['StatusCode'] == 200:
            if response_payload.get('statusCode') == 200:
                body = json.loads(response_payload.get('body', '{}'))
                if body.get('success'):
                    questions = body.get('questions', [])
                    is_async = body.get('async', False)
                    
                    print(f"   ✅ Success: {len(questions)} questions")
                    print(f"   Async Mode: {is_async}")
                    
                    if not is_async:
                        print(f"   Questions/Second: {len(questions)/execution_time:.1f}")
                else:
                    print(f"   ❌ API returned success=false")
            else:
                print(f"   ❌ API returned status {response_payload.get('statusCode')}")
                print(f"   Error: {response_payload.get('body', 'Unknown error')}")
        else:
            print(f"   ❌ Lambda failed with status {response['StatusCode']}")
            
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")

def check_lambda_config():
    """Check Lambda function configurations."""
    
    print("\n🔧 Checking Lambda Configurations")
    print("=" * 50)
    
    lambda_client = boto3.client('lambda')
    
    functions = [
        'gcse-async-worker-lambda-prod',
        'gcse-generate-lambda-prod'
    ]
    
    for func_name in functions:
        try:
            response = lambda_client.get_function_configuration(FunctionName=func_name)
            
            print(f"\n📋 {func_name}:")
            print(f"   Runtime: {response.get('Runtime')}")
            print(f"   Memory: {response.get('MemorySize')}MB")
            print(f"   Timeout: {response.get('Timeout')}s")
            print(f"   Last Modified: {response.get('LastModified')}")
            
            # Check environment variables
            env_vars = response.get('Environment', {}).get('Variables', {})
            parallel_enabled = env_vars.get('PARALLEL_PROCESSING_ENABLED', 'false')
            max_workers = env_vars.get('MAX_PARALLEL_WORKERS', 'not set')
            
            print(f"   Parallel Processing: {parallel_enabled}")
            print(f"   Max Workers: {max_workers}")
            
        except Exception as e:
            print(f"   ❌ Error checking {func_name}: {str(e)}")

if __name__ == "__main__":
    check_lambda_config()
    test_generate_lambda_direct()
    test_async_worker_direct()