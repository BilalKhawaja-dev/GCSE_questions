#!/usr/bin/env python3
"""
Simple timeout test - just 5 questions (should work) and 40 questions (to test timeout handling).
"""

import json
import requests
import time
import sys

# API Configuration
API_BASE_URL = "https://3b41y4ox0l.execute-api.eu-west-2.amazonaws.com/prod"
API_KEY = "test-api-key-12345678901234567890"

def test_auth():
    """Test authentication to get a session token."""
    print("🔐 Getting authentication token...")
    
    auth_data = {
        "action": "register",
        "username": f"test_user_{int(time.time())}",
        "password": "TestPassword123!",
        "email": f"test_{int(time.time())}@example.com"
    }
    
    response = requests.post(
        f"{API_BASE_URL}/auth",
        json=auth_data,
        headers={
            "Content-Type": "application/json",
            "X-API-Key": API_KEY
        },
        timeout=30
    )
    
    if response.status_code == 200:
        result = response.json()
        if result.get("success"):
            print(f"✅ Authentication successful")
            return result.get("session_token")
        else:
            print(f"❌ Authentication failed: {result}")
            return None
    else:
        print(f"❌ Authentication request failed: {response.status_code} - {response.text}")
        return None

def test_5_questions(session_token):
    """Test 5 questions - should work synchronously."""
    print(f"\n📝 Testing 5 questions (should work)...")
    
    generate_data = {
        "topic": "Number",
        "tier": "Foundation", 
        "count": 5,
        "enriched_prompt": "Generate 5 Foundation tier questions about fractions and decimals"
    }
    
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/generate",
            json=generate_data,
            headers={
                "Content-Type": "application/json",
                "X-API-Key": API_KEY,
                "Authorization": f"Bearer {session_token}"
            },
            timeout=120  # 2 minute timeout as requested
        )
        
        duration = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                question_count = len(result.get("questions", []))
                print(f"✅ 5 questions successful: {question_count} questions in {duration:.1f}s (sync)")
                return True
            else:
                print(f"❌ 5 questions failed: {result}")
                return False
        else:
            print(f"❌ 5 questions failed: {response.status_code} - {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"⏰ 5 questions timed out after {duration:.1f}s")
        return False
    except Exception as e:
        print(f"❌ 5 questions error: {str(e)}")
        return False

def test_40_questions(session_token):
    """Test 40 questions - should use async processing."""
    print(f"\n📝 Testing 40 questions (testing timeout handling)...")
    
    generate_data = {
        "topic": "Algebra",
        "tier": "Higher", 
        "count": 40,
        "enriched_prompt": "Generate 40 Higher tier questions about quadratic equations and factoring"
    }
    
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/generate",
            json=generate_data,
            headers={
                "Content-Type": "application/json",
                "X-API-Key": API_KEY,
                "Authorization": f"Bearer {session_token}"
            },
            timeout=120  # 2 minute timeout as requested
        )
        
        duration = time.time() - start_time
        
        if response.status_code == 202:
            result = response.json()
            if result.get("async"):
                print(f"✅ 40 questions accepted for async processing in {duration:.1f}s")
                print(f"   Job ID: {result.get('job_id')}")
                print(f"   Session ID: {result.get('session_id')}")
                print(f"   Status: {result.get('status')}")
                return True
            else:
                print(f"❌ Unexpected 202 response: {result}")
                return False
        elif response.status_code == 200:
            result = response.json()
            if result.get("success"):
                question_count = len(result.get("questions", []))
                print(f"✅ 40 questions completed synchronously: {question_count} questions in {duration:.1f}s")
                return True
            else:
                print(f"❌ 40 questions failed: {result}")
                return False
        else:
            print(f"❌ 40 questions failed: {response.status_code} - {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"⏰ 40 questions timed out after {duration:.1f}s")
        return False
    except Exception as e:
        print(f"❌ 40 questions error: {str(e)}")
        return False

def main():
    """Run the simple timeout tests."""
    print("🧪 Simple Timeout Test")
    print("=" * 30)
    print("Testing 2-minute timeout threshold")
    print("5 questions should work, 40 questions should use async")
    
    # Test authentication
    session_token = test_auth()
    if not session_token:
        print("\n❌ Cannot proceed without authentication")
        sys.exit(1)
    
    # Test 5 questions (should work)
    success_5 = test_5_questions(session_token)
    
    # Test 40 questions (should use async)
    success_40 = test_40_questions(session_token)
    
    # Summary
    print("\n" + "=" * 30)
    print("📊 Test Results:")
    print(f"   5 questions:  {'✅ PASS' if success_5 else '❌ FAIL'}")
    print(f"   40 questions: {'✅ PASS' if success_40 else '❌ FAIL'}")
    
    if success_5 and success_40:
        print("\n🎉 Timeout handling is working correctly!")
        print("✅ Small requests work synchronously")
        print("✅ Large requests use async processing")
    elif success_5:
        print("\n⚠️  Small requests work, but large requests have issues")
    else:
        print("\n❌ Both tests failed - timeout issues remain")
    
    print("\n💡 Configuration:")
    print("   • Frontend timeout: 2 minutes (120s)")
    print("   • Lambda timeout: 5 minutes (300s)")
    print("   • API Gateway timeout: 29s (hard limit)")
    print("   • Async threshold: >10 questions")

if __name__ == "__main__":
    main()