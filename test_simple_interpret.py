#!/usr/bin/env python3
"""
Simple test to isolate InterpretLambda issues
"""

import json
import boto3

def test_simple_interpret():
    """Test with minimal event"""
    
    lambda_client = boto3.client('lambda', region_name='eu-west-2')
    
    # Very simple test event
    test_event = {
        "httpMethod": "POST",
        "path": "/interpret",
        "requestContext": {
            "authorizer": {
                "user_id": "demo",
                "session_token": "test-token"
            }
        },
        "body": json.dumps({
            "query": "test"
        })
    }
    
    print("🔧 Testing with minimal event...")
    
    try:
        response = lambda_client.invoke(
            FunctionName='gcse-interpret-lambda-prod',
            InvocationType='RequestResponse',
            Payload=json.dumps(test_event)
        )
        
        payload = json.loads(response['Payload'].read())
        print(f"Response: {json.dumps(payload, indent=2)}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    test_simple_interpret()