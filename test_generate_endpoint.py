#!/usr/bin/env python3
"""
Test the /generate endpoint with valid authentication.
"""

import requests
import json
import time

API_BASE_URL = "https://3b41y4ox0l.execute-api.eu-west-2.amazonaws.com/prod"

def test_generate_endpoint():
    """Test the /generate endpoint with valid authentication."""
    
    # Get a valid session token
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
    user_id = result.get('user_id')
    print(f"✅ Got session token: {session_token[:20]}...")
    print(f"✅ User ID: {user_id}")
    
    # Test the /generate endpoint
    headers = {
        'Authorization': f'Bearer {session_token}',
        'Content-Type': 'application/json'
    }
    
    data = {
        'topic': 'quadratic equations',
        'tier': 'Foundation',
        'count': 1,
        'user_id': user_id,
        'session_token': session_token
    }
    
    print("\n🔍 Testing /generate endpoint...")
    response = requests.post(f"{API_BASE_URL}/generate", headers=headers, json=data)
    print(f"Status: {response.status_code}")
    
    if response.status_code < 500:
        try:
            result = response.json()
            print(f"Response: {json.dumps(result, indent=2)}")
        except:
            print(f"Response: {response.text}")
    else:
        print(f"Error: {response.text}")

if __name__ == "__main__":
    test_generate_endpoint()