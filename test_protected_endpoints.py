#!/usr/bin/env python3
"""
Test protected endpoints with valid authentication.
"""

import requests
import json
import time

API_BASE_URL = "https://3b41y4ox0l.execute-api.eu-west-2.amazonaws.com/prod"

def get_session_token():
    """Get a valid session token."""
    register_data = {
        "action": "register",
        "username": f"testuser_{int(time.time())}",
        "email": f"test_{int(time.time())}@example.com",
        "password": "TestPassword123!"
    }
    
    response = requests.post(f"{API_BASE_URL}/auth", json=register_data)
    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            return result.get('session_token'), result.get('user_id')
    return None, None

def test_protected_endpoint(endpoint, method, session_token, user_id, data=None):
    """Test a protected endpoint with authentication."""
    headers = {
        'Authorization': f'Bearer {session_token}',
        'Content-Type': 'application/json'
    }
    
    if data is None:
        data = {}
    
    # Add user_id and session_token to request data for endpoints that need it
    if method == 'POST' and endpoint not in ['/auth']:
        data.update({
            'user_id': user_id,
            'session_token': session_token
        })
    
    try:
        if method == 'GET':
            response = requests.get(f"{API_BASE_URL}{endpoint}", headers=headers)
        else:
            response = requests.post(f"{API_BASE_URL}{endpoint}", headers=headers, json=data)
        
        print(f"{method} {endpoint}: Status {response.status_code}")
        if response.status_code < 500:
            try:
                result = response.json()
                print(f"   Response: {json.dumps(result, indent=2)}")
            except:
                print(f"   Response: {response.text}")
        else:
            print(f"   Error: {response.text}")
        print()
        
    except Exception as e:
        print(f"{method} {endpoint}: Error - {str(e)}")
        print()

def main():
    """Test protected endpoints."""
    print("🔐 Testing Protected Endpoints with Authentication")
    print("=" * 60)
    
    # Get session token
    session_token, user_id = get_session_token()
    if not session_token:
        print("❌ Failed to get session token")
        return
    
    print(f"✅ Got session token: {session_token[:20]}...")
    print(f"✅ User ID: {user_id}")
    print()
    
    # Test interpret endpoint
    test_protected_endpoint('/interpret', 'POST', session_token, user_id, {
        'query': 'Generate questions about quadratic equations for Foundation tier'
    })
    
    # Test generate endpoint
    test_protected_endpoint('/generate', 'POST', session_token, user_id, {
        'topic': 'quadratic equations',
        'tier': 'Foundation',
        'count': 2
    })
    
    # Test user sessions
    test_protected_endpoint('/user/sessions', 'GET', session_token, user_id)
    
    # Test user coverage
    test_protected_endpoint('/user/coverage', 'GET', session_token, user_id)

if __name__ == "__main__":
    main()