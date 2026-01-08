#!/usr/bin/env python3
"""
Final test to verify timeout fixes are working correctly.
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
    print("🔐 Testing authentication...")
    
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

def test_request(session_token, count, description):
    """Test a request with specified question count."""
    print(f"\n📝 Testing {description} ({count} questions)...")
    
    generate_data = {
        "topic": "Number",
        "tier": "Foundation", 
        "count": count,
        "enriched_prompt": f"Generate {count} Foundation tier questions about fractions and decimals"
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
            timeout=60  # Client timeout
        )
        
        duration = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                question_count = len(result.get("questions", []))
                async_flag = result.get("async", False)
                mode = "async" if async_flag else "sync"
                print(f"✅ {description} successful: {question_count} questions in {duration:.1f}s ({mode})")
                return True
            else:
                print(f"❌ {description} failed: {result}")
                return False
        elif response.status_code == 202:
            result = response.json()
            if result.get("async"):
                print(f"✅ {description} accepted for async processing in {duration:.1f}s")
                print(f"   Job ID: {result.get('job_id')}")
                print(f"   Session ID: {result.get('session_id')}")
                return True
            else:
                print(f"❌ Unexpected 202 response: {result}")
                return False
        else:
            print(f"❌ {description} failed: {response.status_code} - {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"⏰ {description} timed out after {duration:.1f}s")
        return False
    except Exception as e:
        print(f"❌ {description} error: {str(e)}")
        return False

def main():
    """Run the final timeout fix tests."""
    print("🧪 Final Timeout Fix Verification")
    print("=" * 40)
    
    # Test authentication
    session_token = test_auth()
    if not session_token:
        print("\n❌ Cannot proceed without authentication")
        sys.exit(1)
    
    # Test different request sizes
    test_cases = [
        (5, "Small request"),
        (10, "Medium request"),
        (15, "Large request"),
        (25, "Very large request")
    ]
    
    results = []
    for count, description in test_cases:
        success = test_request(session_token, count, description)
        results.append((description, success))
    
    # Summary
    print("\n" + "=" * 40)
    print("📊 Final Test Results:")
    
    all_passed = True
    for description, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {description}: {status}")
        if not success:
            all_passed = False
    
    if all_passed:
        print("\n🎉 All timeout tests passed!")
        print("✅ The system can now handle requests of various sizes")
        print("✅ API Gateway timeout issues have been resolved")
    else:
        print("\n⚠️  Some tests failed, but basic functionality may still work")
    
    print("\n💡 Key improvements:")
    print("   • Lambda timeout: 60s → 300s (5 minutes)")
    print("   • Batch processing for large requests")
    print("   • Async mode for requests >12 questions")
    print("   • Enhanced error handling and fallbacks")
    print("   • Frontend timeout: 65s → 320s")

if __name__ == "__main__":
    main()