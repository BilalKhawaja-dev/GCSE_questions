#!/usr/bin/env python3
"""Test script to debug CORS issue with /interpret endpoint using demo user."""

import json
import requests

def test_interpret_endpoint_with_demo():
    """Test the /interpret endpoint with demo user."""
    print("Testing /interpret endpoint with demo user...")
    
    api_url = "https://3b41y4ox0l.execute-api.eu-west-2.amazonaws.com/prod/interpret"
    auth_url = "https://3b41y4ox0l.execute-api.eu-west-2.amazonaws.com/prod/auth"
    
    # Test POST request with demo user
    print("Testing POST request with demo user...")
    try:
        # Login with demo user
        login_data = {
            "action": "login",
            "username": "demo",
            "password": "Demo123!"
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
        print(f"Auth Headers: {dict(auth_response.headers)}")
        
        if auth_response.status_code == 200:
            auth_data = auth_response.json()
            session_token = auth_data.get('session_token')
            user_id = auth_data.get('user_id')
            
            print(f"Session token: {session_token[:20]}..." if session_token else "No session token")
            print(f"User ID: {user_id}")
            
            if session_token and user_id:
                # Now test interpret endpoint
                interpret_data = {
                    "query": "Generate 5 questions about fractions",
                    "user_id": user_id,
                    "session_token": session_token
                }
                
                print(f"\nSending interpret request...")
                print(f"Request data: {json.dumps(interpret_data, indent=2)}")
                
                interpret_response = requests.post(
                    api_url,
                    json=interpret_data,
                    headers={
                        'Origin': 'https://d2ckebo851nz2l.cloudfront.net',
                        'Content-Type': 'application/json',
                        'Authorization': f'Bearer {session_token}'
                    }
                )
                
                print(f"\nInterpret Status: {interpret_response.status_code}")
                print(f"Interpret Headers: {dict(interpret_response.headers)}")
                print(f"Interpret Response: {interpret_response.text}")
                
                # Check specifically for CORS headers
                cors_headers = {
                    'Access-Control-Allow-Origin': interpret_response.headers.get('Access-Control-Allow-Origin'),
                    'Access-Control-Allow-Credentials': interpret_response.headers.get('Access-Control-Allow-Credentials'),
                    'Access-Control-Allow-Headers': interpret_response.headers.get('Access-Control-Allow-Headers'),
                    'Access-Control-Allow-Methods': interpret_response.headers.get('Access-Control-Allow-Methods')
                }
                print(f"\nCORS Headers in response: {json.dumps(cors_headers, indent=2)}")
                
            else:
                print("No session token received from auth")
        else:
            print(f"Auth failed: {auth_response.text}")
        
    except Exception as e:
        print(f"Request failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_interpret_endpoint_with_demo()