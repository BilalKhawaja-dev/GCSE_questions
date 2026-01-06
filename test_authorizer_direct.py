#!/usr/bin/env python3
"""
Test the authorizer directly by invoking the Lambda function.
"""

import boto3
import json
import time

def test_authorizer_direct():
    """Test the authorizer by invoking the Lambda directly."""
    lambda_client = boto3.client('lambda', region_name='eu-west-2')
    
    # Get a valid session token first
    import requests
    API_BASE_URL = "https://3b41y4ox0l.execute-api.eu-west-2.amazonaws.com/prod"
    
    register_data = {
        "action": "register",
        "username": f"testuser_{int(time.time())}",
        "email": f"test_{int(time.time())}@example.com",
        "password": "TestPassword123!"
    }
    
    response = requests.post(f"{API_BASE_URL}/auth", json=register_data)
    if response.status_code != 200:
        print("❌ Failed to get session token")
        return
    
    result = response.json()
    if not result.get('success'):
        print("❌ Failed to get session token")
        return
    
    session_token = result.get('session_token')
    print(f"✅ Got session token: {session_token[:20]}...")
    
    # Create authorizer event
    authorizer_event = {
        "type": "REQUEST",
        "methodArn": "arn:aws:execute-api:eu-west-2:981686514879:3b41y4ox0l/prod/POST/generate",
        "resource": "/generate",
        "path": "/generate",
        "httpMethod": "POST",
        "headers": {
            "Authorization": f"Bearer {session_token}"
        },
        "requestContext": {
            "identity": {
                "sourceIp": "127.0.0.1"
            }
        }
    }
    
    print("🔍 Testing authorizer directly...")
    print(f"Event: {json.dumps(authorizer_event, indent=2)}")
    
    try:
        response = lambda_client.invoke(
            FunctionName='gcse-auth-lambda-prod',
            Payload=json.dumps(authorizer_event)
        )
        
        payload = json.loads(response['Payload'].read())
        print(f"✅ Authorizer response: {json.dumps(payload, indent=2)}")
        
    except Exception as e:
        print(f"❌ Error invoking authorizer: {str(e)}")

if __name__ == "__main__":
    test_authorizer_direct()