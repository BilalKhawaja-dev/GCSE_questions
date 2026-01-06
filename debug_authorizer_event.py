#!/usr/bin/env python3
"""
Debug the authorizer event structure.
"""

import boto3
import json
import time

def debug_authorizer_event():
    """Debug the authorizer event by invoking the Lambda directly."""
    lambda_client = boto3.client('lambda', region_name='eu-west-2')
    
    # Create a test authorizer event that matches what API Gateway sends
    authorizer_event = {
        "type": "REQUEST",
        "methodArn": "arn:aws:execute-api:eu-west-2:981686514879:3b41y4ox0l/prod/POST/generate",
        "resource": "/generate",
        "path": "/generate",
        "httpMethod": "POST",
        "headers": {
            "Authorization": "Bearer test-token",
            "Content-Type": "application/json"
        },
        "multiValueHeaders": {
            "Authorization": ["Bearer test-token"],
            "Content-Type": ["application/json"]
        },
        "queryStringParameters": None,
        "multiValueQueryStringParameters": None,
        "pathParameters": None,
        "stageVariables": None,
        "requestContext": {
            "resourceId": "abc123",
            "resourcePath": "/generate",
            "httpMethod": "POST",
            "extendedRequestId": "test-request-id",
            "requestTime": "02/Jan/2026:16:20:00 +0000",
            "path": "/prod/generate",
            "accountId": "981686514879",
            "protocol": "HTTP/1.1",
            "stage": "prod",
            "domainPrefix": "3b41y4ox0l",
            "requestTimeEpoch": int(time.time() * 1000),
            "requestId": "test-request-id",
            "identity": {
                "cognitoIdentityPoolId": None,
                "accountId": None,
                "cognitoIdentityId": None,
                "caller": None,
                "sourceIp": "127.0.0.1",
                "principalOrgId": None,
                "accessKey": None,
                "cognitoAuthenticationType": None,
                "cognitoAuthenticationProvider": None,
                "userArn": None,
                "userAgent": "curl/8.3.0",
                "user": None
            },
            "domainName": "3b41y4ox0l.execute-api.eu-west-2.amazonaws.com",
            "apiId": "3b41y4ox0l"
        }
    }
    
    print("🔍 Testing authorizer with detailed event...")
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
    debug_authorizer_event()