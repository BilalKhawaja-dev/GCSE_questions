#!/usr/bin/env python3
"""
Test session endpoint directly to diagnose 403 errors
"""

import requests
import json
import os

# API configuration
API_BASE_URL = "https://3b41y4ox0l.execute-api.eu-west-2.amazonaws.com/prod"

def test_with_valid_token():
    """Test session endpoint with a valid token"""
    
    # First, get a valid token by logging in
    login_data = {
        "action": "login",
        "username": "testuser",
        "password": "TestPassword123!"
    }
    
    print("🔐 Logging in to get valid token...")
    login_response = requests.post(
        f"{API_BASE_URL}/auth",
        json=login_data,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Login Status: {login_response.status_code}")
    print(f"Login Response: {login_response.text}")
    
    if login_response.status_code != 200:
        print("❌ Login failed, cannot test session endpoint")
        return
    
    login_result = login_response.json()
    if not login_result.get('success'):
        print("❌ Login unsuccessful")
        return
    
    session_token = login_result.get('session_token')
    if not session_token:
        print("❌ No session token received")
        return
    
    print(f"✅ Got session token: {session_token[:20]}...")
    
    # Now test the session endpoint
    print("\n📊 Testing session history endpoint...")
    
    headers = {
        "Authorization": f"Bearer {session_token}",
        "Content-Type": "application/json"
    }
    
    session_response = requests.get(
        f"{API_BASE_URL}/user/sessions?limit=50",
        headers=headers
    )
    
    print(f"Session Status: {session_response.status_code}")
    print(f"Session Headers: {dict(session_response.headers)}")
    print(f"Session Response: {session_response.text}")
    
    # Test topic coverage endpoint
    print("\n📈 Testing topic coverage endpoint...")
    
    coverage_response = requests.get(
        f"{API_BASE_URL}/user/coverage?days=30",
        headers=headers
    )
    
    print(f"Coverage Status: {coverage_response.status_code}")
    print(f"Coverage Headers: {dict(coverage_response.headers)}")
    print(f"Coverage Response: {coverage_response.text}")

def test_without_token():
    """Test endpoints without token to confirm 403 behavior"""
    
    print("\n🚫 Testing without authorization token...")
    
    # Test session endpoint without token
    session_response = requests.get(
        f"{API_BASE_URL}/user/sessions?limit=50"
    )
    
    print(f"No Token Session Status: {session_response.status_code}")
    print(f"No Token Session Response: {session_response.text}")
    
    # Test coverage endpoint without token
    coverage_response = requests.get(
        f"{API_BASE_URL}/user/coverage?days=30"
    )
    
    print(f"No Token Coverage Status: {coverage_response.status_code}")
    print(f"No Token Coverage Response: {coverage_response.text}")

if __name__ == "__main__":
    print("🧪 Testing Session and Topic Coverage Endpoints")
    print("=" * 60)
    
    test_with_valid_token()
    test_without_token()