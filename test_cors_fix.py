#!/usr/bin/env python3
"""
Test CORS and API functionality after fixes
"""

import requests
import json

def test_cors_and_api():
    """Test CORS headers and API functionality"""
    
    # API Gateway URL
    api_url = "https://3b41y4ox0l.execute-api.eu-west-2.amazonaws.com/prod"
    
    print("Testing CORS and API functionality...")
    print("=" * 50)
    
    # Test 1: OPTIONS request for CORS preflight
    print("\n1. Testing CORS preflight (OPTIONS /interpret)")
    try:
        response = requests.options(
            f"{api_url}/interpret",
            headers={
                "Origin": "https://d2ckebo851nz2l.cloudfront.net",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type,Authorization"
            }
        )
        
        print(f"Status: {response.status_code}")
        print("CORS Headers:")
        for header, value in response.headers.items():
            if "access-control" in header.lower():
                print(f"  {header}: {value}")
                
        if response.status_code == 200:
            print("✅ CORS preflight successful")
        else:
            print("❌ CORS preflight failed")
            
    except Exception as e:
        print(f"❌ CORS preflight error: {e}")
    
    # Test 2: Register a new test user
    print("\n2. Testing user registration")
    session_token = None
    user_id = None
    
    try:
        register_data = {
            "action": "register",
            "username": "testuser333",
            "password": "TestPass123!",
            "email": "test333@example.com"
        }
        
        response = requests.post(
            f"{api_url}/auth",
            json=register_data,
            headers={
                "Content-Type": "application/json",
                "Origin": "https://d2ckebo851nz2l.cloudfront.net"
            }
        )
        
        print(f"Status: {response.status_code}")
        print("Response CORS Headers:")
        for header, value in response.headers.items():
            if "access-control" in header.lower():
                print(f"  {header}: {value}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Registration successful: {data.get('message', 'No message')}")
            print(f"Response data: {data}")
            session_token = data.get('session_token')
            user_id = data.get('user_id')
        else:
            print(f"❌ Registration failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Registration error: {e}")
    
    # Test 3: Try to interpret a query (this was failing with 500 error)
    print("\n3. Testing interpret endpoint")
    if session_token and user_id:
        try:
            interpret_data = {
                "query": "Generate 3 questions about fractions for Foundation tier",
                "user_id": user_id,
                "session_token": session_token
            }
            
            response = requests.post(
                f"{api_url}/interpret",
                json=interpret_data,
                headers={
                    "Content-Type": "application/json",
                    "Origin": "https://d2ckebo851nz2l.cloudfront.net",
                    "Authorization": f"Bearer {session_token}"
                }
            )
            
            print(f"Status: {response.status_code}")
            print("Response CORS Headers:")
            for header, value in response.headers.items():
                if "access-control" in header.lower():
                    print(f"  {header}: {value}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Interpret successful")
                print(f"Intent: {data.get('intent', {})}")
            else:
                print(f"❌ Interpret failed: {response.text}")
                
        except Exception as e:
            print(f"❌ Interpret error: {e}")
    else:
        print("⏭️  Skipping interpret test (no session token)")

if __name__ == "__main__":
    test_cors_and_api()