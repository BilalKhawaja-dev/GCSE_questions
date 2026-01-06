#!/usr/bin/env python3
"""
Create a simple test user with easy credentials
"""

import requests
import json

def create_simple_user():
    """Create a simple test user with easy credentials"""
    
    api_url = "https://3b41y4ox0l.execute-api.eu-west-2.amazonaws.com/prod"
    
    # Simple test user credentials
    test_user = {
        "action": "register",
        "username": "demo",
        "password": "Demo123!",  # Simple but valid password
        "email": "demo@example.com",
        "school": "Demo School",
        "subject_specialization": "Mathematics"
    }
    
    print("🔧 Creating simple demo user...")
    print(f"Username: {test_user['username']}")
    print(f"Password: {test_user['password']}")
    print()
    
    try:
        # Register the test user
        response = requests.post(f"{api_url}/auth", json=test_user, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("✅ Simple demo user created successfully!")
                print("=" * 40)
                print("EASY LOGIN CREDENTIALS:")
                print(f"Username: {test_user['username']}")
                print(f"Password: {test_user['password']}")
                print("=" * 40)
                return True
            else:
                print(f"❌ Registration failed: {data.get('message', 'Unknown error')}")
                if "already exists" in data.get('message', ''):
                    print("✅ User already exists - you can use these credentials:")
                    print("=" * 40)
                    print("EXISTING LOGIN CREDENTIALS:")
                    print(f"Username: {test_user['username']}")
                    print(f"Password: {test_user['password']}")
                    print("=" * 40)
                    return True
        else:
            print(f"❌ Registration request failed with status {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    return False

if __name__ == "__main__":
    create_simple_user()