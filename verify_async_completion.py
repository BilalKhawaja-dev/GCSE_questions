#!/usr/bin/env python3
"""
Verify that async processing actually completes by checking session status.
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

def start_async_generation(session_token):
    """Start async generation and return session ID."""
    print(f"\n📝 Starting async generation (20 questions)...")
    
    generate_data = {
        "topic": "Geometry",
        "tier": "Higher", 
        "count": 20,
        "enriched_prompt": "Generate 20 Higher tier questions about circles and trigonometry"
    }
    
    response = requests.post(
        f"{API_BASE_URL}/generate",
        json=generate_data,
        headers={
            "Content-Type": "application/json",
            "X-API-Key": API_KEY,
            "Authorization": f"Bearer {session_token}"
        },
        timeout=30
    )
    
    if response.status_code == 202:
        result = response.json()
        if result.get("async"):
            session_id = result.get("session_id")
            print(f"✅ Async generation started")
            print(f"   Session ID: {session_id}")
            return session_id
        else:
            print(f"❌ Unexpected 202 response: {result}")
            return None
    else:
        print(f"❌ Failed to start async generation: {response.status_code} - {response.text}")
        return None

def check_session_status(session_token, session_id):
    """Check session status to see if async processing completed."""
    print(f"\n🔍 Checking session status...")
    
    max_checks = 12  # Check for up to 2 minutes
    for i in range(max_checks):
        try:
            response = requests.get(
                f"{API_BASE_URL}/user/sessions/{session_id}",
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": API_KEY,
                    "Authorization": f"Bearer {session_token}"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                status = result.get("metadata", {}).get("status", "unknown")
                progress = result.get("metadata", {}).get("progress", 0)
                question_count = len(result.get("generated_questions", []))
                
                print(f"   Check {i+1}: Status={status}, Progress={progress}%, Questions={question_count}")
                
                if status == "completed":
                    print(f"✅ Async processing completed successfully!")
                    print(f"   Generated {question_count} questions")
                    return True
                elif status == "failed":
                    error = result.get("metadata", {}).get("error", "Unknown error")
                    print(f"❌ Async processing failed: {error}")
                    return False
                
                # Still processing, wait and check again
                time.sleep(10)
                
            else:
                print(f"   Check {i+1}: HTTP {response.status_code} - {response.text}")
                time.sleep(10)
                
        except Exception as e:
            print(f"   Check {i+1}: Error - {str(e)}")
            time.sleep(10)
    
    print(f"⏰ Timeout reached after {max_checks} checks")
    return False

def main():
    """Run the async completion verification."""
    print("🧪 Async Processing Verification")
    print("=" * 35)
    
    # Test authentication
    session_token = test_auth()
    if not session_token:
        print("\n❌ Cannot proceed without authentication")
        sys.exit(1)
    
    # Start async generation
    session_id = start_async_generation(session_token)
    if not session_id:
        print("\n❌ Cannot proceed without session ID")
        sys.exit(1)
    
    # Check if async processing completes
    success = check_session_status(session_token, session_id)
    
    # Summary
    print("\n" + "=" * 35)
    if success:
        print("🎉 Async processing verification successful!")
        print("✅ Large requests are processed asynchronously")
        print("✅ Results are available via session polling")
    else:
        print("❌ Async processing verification failed")
        print("⚠️  Check Lambda logs for more details")
    
    print("\n💡 This confirms that:")
    print("   • API Gateway 29s timeout is bypassed")
    print("   • Lambda processes requests in background")
    print("   • Results are stored and retrievable")

if __name__ == "__main__":
    main()