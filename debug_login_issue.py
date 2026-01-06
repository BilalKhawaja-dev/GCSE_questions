#!/usr/bin/env python3
"""
Debug login issue by testing the API directly
"""

import requests
import json
import time

def test_login_api():
    """Test the login API directly to debug the issue"""
    
    api_url = "https://3b41y4ox0l.execute-api.eu-west-2.amazonaws.com/prod"
    
    # Test with the demo user we created
    login_data = {
        "action": "login",
        "username": "demo",
        "password": "Demo123!"
    }
    
    print("🔍 Testing Login API Directly")
    print("=" * 50)
    print(f"API URL: {api_url}/auth")
    print(f"Login Data: {json.dumps(login_data, indent=2)}")
    print()
    
    try:
        print("📡 Sending login request...")
        start_time = time.time()
        
        response = requests.post(
            f"{api_url}/auth", 
            json=login_data, 
            timeout=30,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'DebugScript/1.0'
            }
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"⏱️  Response Time: {duration:.2f} seconds")
        print(f"📊 Status Code: {response.status_code}")
        print(f"📋 Headers: {dict(response.headers)}")
        print()
        
        if response.status_code == 200:
            try:
                data = response.json()
                print("✅ Login Response (Success):")
                print(json.dumps(data, indent=2))
                
                if data.get('success'):
                    print("\n🎯 Login was successful!")
                    print(f"User ID: {data.get('user_id')}")
                    print(f"Session Token: {data.get('session_token', 'N/A')[:20]}...")
                    print(f"Expires At: {data.get('expires_at', 'N/A')}")
                    return True
                else:
                    print(f"\n❌ Login failed: {data.get('message', 'Unknown error')}")
                    
            except json.JSONDecodeError as e:
                print(f"❌ JSON decode error: {e}")
                print(f"Raw response: {response.text}")
                
        else:
            print(f"❌ HTTP Error {response.status_code}")
            print(f"Response: {response.text}")
            
            # Check for common API Gateway errors
            if response.status_code == 403:
                print("\n🔍 This might be a CORS or API Gateway configuration issue")
            elif response.status_code == 500:
                print("\n🔍 This is likely a Lambda function error")
            elif response.status_code == 502:
                print("\n🔍 This is a Bad Gateway error - Lambda might be failing")
            elif response.status_code == 504:
                print("\n🔍 This is a Gateway Timeout - Lambda might be taking too long")
                
    except requests.exceptions.Timeout:
        print("❌ Request timed out after 30 seconds")
        print("🔍 This suggests the Lambda function is not responding")
        
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection error: {e}")
        print("🔍 This suggests a network or DNS issue")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    
    return False

def test_with_wrong_credentials():
    """Test with wrong credentials to see error handling"""
    
    api_url = "https://3b41y4ox0l.execute-api.eu-west-2.amazonaws.com/prod"
    
    # Test with wrong password
    wrong_login_data = {
        "action": "login",
        "username": "demo",
        "password": "WrongPassword123!"
    }
    
    print("\n🔍 Testing with Wrong Credentials")
    print("=" * 50)
    
    try:
        response = requests.post(f"{api_url}/auth", json=wrong_login_data, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            if not data.get('success'):
                print("✅ Wrong credentials properly rejected")
            else:
                print("❌ Wrong credentials were accepted (this is a bug)")
        else:
            print("❌ Unexpected status code for wrong credentials")
            
    except Exception as e:
        print(f"❌ Error testing wrong credentials: {e}")

if __name__ == "__main__":
    print("🧪 DEBUGGING LOGIN ISSUE")
    print("=" * 60)
    
    # Test 1: Valid login
    success = test_login_api()
    
    # Test 2: Invalid login
    test_with_wrong_credentials()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ API LOGIN IS WORKING - Issue is likely in the frontend")
    else:
        print("❌ API LOGIN IS FAILING - Issue is in the backend")