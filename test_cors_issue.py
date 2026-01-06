#!/usr/bin/env python3
"""Test script to debug CORS issue with /interpret endpoint."""

import json
import requests
import os
from src.utils.security import get_cors_response_headers

def test_cors_headers():
    """Test CORS header generation."""
    print("Testing CORS header generation...")
    
    # Test production environment
    prod_headers = get_cors_response_headers('prod')
    print(f"Production CORS headers: {json.dumps(prod_headers, indent=2)}")
    
    # Test dev environment
    dev_headers = get_cors_response_headers('dev')
    print(f"Development CORS headers: {json.dumps(dev_headers, indent=2)}")
    
    # Test with environment variable
    os.environ['ENVIRONMENT'] = 'prod'
    env_headers = get_cors_response_headers()
    print(f"Environment variable CORS headers: {json.dumps(env_headers, indent=2)}")

def test_interpret_endpoint():
    """Test the /interpret endpoint directly."""
    print("\nTesting /interpret endpoint...")
    
    api_url = "https://3b41y4ox0l.execute-api.eu-west-2.amazonaws.com/prod/interpret"
    
    # Test OPTIONS request (preflight)
    print("Testing OPTIONS request...")
    try:
        options_response = requests.options(
            api_url,
            headers={
                'Origin': 'https://d2ckebo851nz2l.cloudfront.net',
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'Content-Type,Authorization,X-Session-Token'
            }
        )
        print(f"OPTIONS Status: {options_response.status_code}")
        print(f"OPTIONS Headers: {dict(options_response.headers)}")
    except Exception as e:
        print(f"OPTIONS request failed: {e}")
    
    # Test POST request with valid session token
    print("\nTesting POST request...")
    try:
        # First, let's get a valid session token
        auth_url = "https://3b41y4ox0l.execute-api.eu-west-2.amazonaws.com/prod/auth"
        
        # Create test user and login
        login_data = {
            "action": "login",
            "username": "testuser123",
            "password": "testpassword123"
        }
        
        auth_response = requests.post(
            auth_url,
            json=login_data,
            headers={
                'Origin': 'https://d2ckebo851nz2l.cloudfront.net',
                'Content-Type': 'application/json'
            }
        )
        
        print(f"Auth Status: {auth_response.status_code}")
        print(f"Auth Response: {auth_response.text}")
        
        if auth_response.status_code == 200:
            auth_data = auth_response.json()
            session_token = auth_data.get('session_token')
            user_id = auth_data.get('user_id')
            
            if session_token and user_id:
                # Now test interpret endpoint
                interpret_data = {
                    "query": "Generate 5 questions about fractions",
                    "user_id": user_id,
                    "session_token": session_token
                }
                
                interpret_response = requests.post(
                    api_url,
                    json=interpret_data,
                    headers={
                        'Origin': 'https://d2ckebo851nz2l.cloudfront.net',
                        'Content-Type': 'application/json',
                        'Authorization': f'Bearer {session_token}'
                    }
                )
                
                print(f"Interpret Status: {interpret_response.status_code}")
                print(f"Interpret Headers: {dict(interpret_response.headers)}")
                print(f"Interpret Response: {interpret_response.text}")
            else:
                print("No session token received from auth")
        
    except Exception as e:
        print(f"POST request failed: {e}")

if __name__ == "__main__":
    test_cors_headers()
    test_interpret_endpoint()