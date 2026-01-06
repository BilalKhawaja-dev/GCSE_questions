#!/usr/bin/env python3
"""
Create a test user for the GCSE Question Generator V2 system
"""

import requests
import json
import sys

def create_test_user():
    """Create a test user with valid credentials"""
    
    api_url = "https://3b41y4ox0l.execute-api.eu-west-2.amazonaws.com/prod"
    
    # Test user credentials
    import time
    timestamp = int(time.time())
    test_user = {
        "action": "register",
        "username": f"demo_user_{timestamp}",
        "password": "TestPass123!",  # Strong password with uppercase, lowercase, number, special char
        "email": f"demo{timestamp}@example.com",
        "school": "Demo School",
        "subject_specialization": "Mathematics"
    }
    
    print("🔧 Creating test user for GCSE Question Generator V2...")
    print(f"Username: {test_user['username']}")
    print(f"Password: {test_user['password']}")
    print(f"Email: {test_user['email']}")
    print()
    
    try:
        # Register the test user
        response = requests.post(f"{api_url}/auth", json=test_user, timeout=30)
        
        print(f"Registration Response Status: {response.status_code}")
        print(f"Registration Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("✅ Test user created successfully!")
                print(f"User ID: {data.get('user_id')}")
                print(f"Session Token: {data.get('session_token', 'N/A')[:20]}...")
                
                # Test login with the same credentials
                print("\n🔍 Testing login with created user...")
                login_data = {
                    "action": "login",
                    "username": test_user['username'],
                    "password": test_user['password']
                }
                
                login_response = requests.post(f"{api_url}/auth", json=login_data, timeout=30)
                print(f"Login Response Status: {login_response.status_code}")
                print(f"Login Response: {login_response.text}")
                
                if login_response.status_code == 200:
                    login_result = login_response.json()
                    if login_result.get('success'):
                        print("✅ Login test successful!")
                        print(f"Login Session Token: {login_result.get('session_token', 'N/A')[:20]}...")
                        
                        print("\n🎯 Test User Ready!")
                        print("=" * 50)
                        print("You can now use these credentials in the frontend:")
                        print(f"Username: {test_user['username']}")
                        print(f"Password: {test_user['password']}")
                        print("=" * 50)
                        return True
                    else:
                        print(f"❌ Login failed: {login_result.get('message', 'Unknown error')}")
                else:
                    print(f"❌ Login request failed with status {login_response.status_code}")
                    
            else:
                print(f"❌ Registration failed: {data.get('message', 'Unknown error')}")
        else:
            print(f"❌ Registration request failed with status {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    
    return False

if __name__ == "__main__":
    success = create_test_user()
    sys.exit(0 if success else 1)