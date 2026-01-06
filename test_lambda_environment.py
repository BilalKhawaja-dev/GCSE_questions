#!/usr/bin/env python3
"""Test what environment the Lambda function thinks it's running in."""

import json
import requests

def test_lambda_environment():
    """Test what environment variables the Lambda function has."""
    
    # We can test this by looking at the CORS headers returned by the auth endpoint
    # since it uses the same CORS function
    
    auth_url = "https://3b41y4ox0l.execute-api.eu-west-2.amazonaws.com/prod/auth"
    
    # Test with a simple request to see what CORS headers are returned
    try:
        response = requests.post(
            auth_url,
            json={"action": "validate", "session_token": "invalid"},
            headers={
                'Origin': 'https://d2ckebo851nz2l.cloudfront.net',
                'Content-Type': 'application/json'
            }
        )
        
        print(f"Status: {response.status_code}")
        print(f"CORS Headers:")
        cors_headers = {
            'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
            'Access-Control-Allow-Credentials': response.headers.get('Access-Control-Allow-Credentials'),
            'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers'),
            'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods')
        }
        
        for key, value in cors_headers.items():
            print(f"  {key}: {value}")
        
        # Analyze what this tells us about the environment
        origin = cors_headers.get('Access-Control-Allow-Origin')
        if origin == 'https://d2ckebo851nz2l.cloudfront.net':
            print("\n✅ Lambda function is correctly detecting 'prod' environment")
        elif origin == 'http://localhost:3000':
            print("\n❌ Lambda function is detecting 'dev' environment (should be 'prod')")
        elif origin == '*':
            print("\n❌ Lambda function is using wildcard origin (old configuration)")
        else:
            print(f"\n❓ Lambda function is using unexpected origin: {origin}")
            
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_lambda_environment()