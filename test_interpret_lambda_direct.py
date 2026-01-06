#!/usr/bin/env python3
"""
Test InterpretLambda directly to isolate the issue
"""

import json
import boto3

def test_interpret_lambda():
    """Test InterpretLambda directly"""
    
    # Initialize Lambda client
    lambda_client = boto3.client('lambda', region_name='eu-west-2')
    
    # Create test event with proper authorization context
    test_event = {
        "httpMethod": "POST",
        "path": "/interpret",
        "headers": {
            "Content-Type": "application/json",
            "Authorization": "Bearer test-token"
        },
        "requestContext": {
            "authorizer": {
                "user_id": "demo",
                "session_token": "test-token"
            }
        },
        "body": json.dumps({
            "query": "5 foundation fractions questions"
        })
    }
    
    print("🔧 Testing InterpretLambda directly...")
    print(f"Event: {json.dumps(test_event, indent=2)}")
    
    try:
        # Invoke Lambda function
        response = lambda_client.invoke(
            FunctionName='gcse-interpret-lambda-prod',
            InvocationType='RequestResponse',
            Payload=json.dumps(test_event)
        )
        
        # Parse response
        payload = json.loads(response['Payload'].read())
        
        print(f"Status Code: {response['StatusCode']}")
        print(f"Response: {json.dumps(payload, indent=2)}")
        
        if response['StatusCode'] == 200:
            print("✅ Lambda invocation successful")
        else:
            print("❌ Lambda invocation failed")
            
    except Exception as e:
        print(f"❌ Error invoking Lambda: {str(e)}")

if __name__ == "__main__":
    test_interpret_lambda()