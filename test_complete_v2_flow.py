#!/usr/bin/env python3
"""
Test complete V2 authenticated flow
"""

import requests
import json

API_BASE = "https://3b41y4ox0l.execute-api.eu-west-2.amazonaws.com/prod"

def test_complete_flow():
    print("🧪 Testing Complete V2 Authenticated Flow")
    print("=" * 50)
    
    # Step 1: Register user
    print("1️⃣ Registering user...")
    timestamp = int(__import__('time').time())
    auth_data = {
        "action": "register",
        "username": f"testuser_{timestamp}",
        "password": "TestPassword123!",
        "email": f"test{timestamp}@example.com"
    }
    
    response = requests.post(f"{API_BASE}/auth", json=auth_data)
    if response.status_code != 200:
        print(f"❌ Registration failed: {response.status_code} - {response.text}")
        return
    
    auth_result = response.json()
    user_id = auth_result['user_id']
    session_token = auth_result['session_token']
    print(f"✅ User registered: {user_id}")
    
    # Step 2: Test generate endpoint
    print("\n2️⃣ Testing question generation...")
    generate_data = {
        "topic": "quadratic equations",
        "tier": "Foundation",
        "count": 2,
        "user_id": user_id,
        "session_token": session_token
    }
    
    headers = {"Authorization": f"Bearer {session_token}"}
    response = requests.post(f"{API_BASE}/generate", json=generate_data, headers=headers)
    if response.status_code != 200:
        print(f"❌ Generation failed: {response.status_code} - {response.text}")
        return
    
    generate_result = response.json()
    print(f"✅ Generated {len(generate_result['questions'])} questions")
    for i, q in enumerate(generate_result['questions']):
        print(f"   Question {i+1}: {q['text']}")
    
    # Step 3: Test interpret endpoint
    print("\n3️⃣ Testing query interpretation...")
    interpret_data = {
        "query": "I need questions about solving quadratic equations for foundation tier",
        "user_id": user_id,
        "session_token": session_token
    }
    
    headers = {"Authorization": f"Bearer {session_token}"}
    response = requests.post(f"{API_BASE}/interpret", json=interpret_data, headers=headers)
    if response.status_code != 200:
        print(f"❌ Interpretation failed: {response.status_code} - {response.text}")
        return
    
    interpret_result = response.json()
    print(f"✅ Query interpreted successfully")
    print(f"   Topic: {interpret_result.get('topic', 'N/A')}")
    print(f"   Tier: {interpret_result.get('tier', 'N/A')}")
    
    # Step 4: Test sessions endpoint
    print("\n4️⃣ Testing user sessions...")
    headers = {"Authorization": f"Bearer {session_token}"}
    response = requests.get(f"{API_BASE}/user/sessions", headers=headers)
    if response.status_code != 200:
        print(f"❌ Sessions failed: {response.status_code} - {response.text}")
        return
    
    sessions_result = response.json()
    print(f"✅ Sessions retrieved: {len(sessions_result.get('sessions', []))} sessions")
    
    print("\n🎉 Complete V2 Flow Test Successful!")
    print("✅ Authentication working")
    print("✅ Question generation working")  
    print("✅ Query interpretation working")
    print("✅ Session management working")
    print("✅ Authorization working across all endpoints")

if __name__ == "__main__":
    test_complete_flow()