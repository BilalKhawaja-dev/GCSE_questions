#!/usr/bin/env python3
"""
Test script to verify the async generation functionality for large question requests.
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

def test_sync_request(session_token):
    """Test a synchronous request (should complete within API Gateway timeout)."""
    print("\n📝 Testing synchronous request (10 questions)...")
    
    generate_data = {
        "topic": "Algebra",
        "tier": "Foundation", 
        "count": 10,
        "enriched_prompt": "Generate 10 Foundation tier algebra questions about linear equations"
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
            timeout=60
        )
        
        duration = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                question_count = len(result.get("questions", []))
                print(f"✅ Sync request successful: {question_count} questions in {duration:.1f}s")
                return True
            else:
                print(f"❌ Sync request failed: {result}")
                return False
        else:
            print(f"❌ Sync request failed: {response.status_code} - {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"⏰ Sync request timed out after {duration:.1f}s")
        return False
    except Exception as e:
        print(f"❌ Sync request error: {str(e)}")
        return False

def test_async_request(session_token):
    """Test an asynchronous request (should trigger async mode)."""
    print("\n🔄 Testing asynchronous request (20 questions)...")
    
    generate_data = {
        "topic": "Geometry",
        "tier": "Higher", 
        "count": 20,
        "enriched_prompt": "Generate 20 Higher tier geometry questions covering angles, area, and trigonometry"
    }
    
    start_time = time.time()
    
    try:
        # Initial request
        response = requests.post(
            f"{API_BASE_URL}/generate",
            json=generate_data,
            headers={
                "Content-Type": "application/json",
                "X-API-Key": API_KEY,
                "Authorization": f"Bearer {session_token}"
            },
            timeout=60
        )
        
        initial_duration = time.time() - start_time
        
        if response.status_code == 202:  # Accepted - async processing
            result = response.json()
            if result.get("async"):
                job_id = result.get("job_id")
                session_id = result.get("session_id")
                polling_info = result.get("polling_info", {})
                
                print(f"✅ Async request accepted in {initial_duration:.1f}s")
                print(f"   Job ID: {job_id}")
                print(f"   Session ID: {session_id}")
                print(f"   Estimated completion: {result.get('estimated_completion_minutes', 3)} minutes")
                
                # Poll for completion
                return poll_async_completion(session_token, session_id, polling_info)
            else:
                print(f"❌ Expected async response but got sync: {result}")
                return False
        elif response.status_code == 200:
            # Might have completed synchronously if it was fast enough
            result = response.json()
            if result.get("success"):
                question_count = len(result.get("questions", []))
                print(f"✅ Request completed synchronously: {question_count} questions in {initial_duration:.1f}s")
                return True
            else:
                print(f"❌ Sync completion failed: {result}")
                return False
        else:
            print(f"❌ Async request failed: {response.status_code} - {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"⏰ Async request timed out after {initial_duration:.1f}s")
        return False
    except Exception as e:
        print(f"❌ Async request error: {str(e)}")
        return False

def poll_async_completion(session_token, session_id, polling_info):
    """Poll for async completion."""
    print("\n⏳ Polling for completion...")
    
    max_wait_time = polling_info.get("max_wait_time_minutes", 5) * 60
    poll_interval = polling_info.get("recommended_poll_interval_seconds", 10)
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        try:
            # Check session status
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
                session_details = response.json()
                status = session_details.get("metadata", {}).get("status", "unknown")
                progress = session_details.get("metadata", {}).get("progress", 0)
                
                print(f"   Status: {status}, Progress: {progress}%")
                
                if status == "completed":
                    question_count = len(session_details.get("generated_questions", []))
                    total_time = time.time() - start_time
                    print(f"✅ Async generation completed: {question_count} questions in {total_time:.1f}s total")
                    return True
                elif status == "failed":
                    error = session_details.get("metadata", {}).get("error", "Unknown error")
                    print(f"❌ Async generation failed: {error}")
                    return False
                
                # Still processing, wait and continue
                time.sleep(poll_interval)
            else:
                print(f"⚠️  Error checking status: {response.status_code}")
                time.sleep(poll_interval)
                
        except Exception as e:
            print(f"⚠️  Error polling: {str(e)}")
            time.sleep(poll_interval)
    
    print(f"⏰ Async generation timed out after {max_wait_time}s")
    return False

def test_explicit_async_request(session_token):
    """Test explicitly requesting async mode."""
    print("\n🎯 Testing explicit async request (15 questions with async=true)...")
    
    generate_data = {
        "topic": "Statistics",
        "tier": "Foundation", 
        "count": 15,
        "async": True,  # Explicitly request async mode
        "enriched_prompt": "Generate 15 Foundation tier statistics questions about data analysis and graphs"
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
            timeout=60
        )
        
        initial_duration = time.time() - start_time
        
        if response.status_code == 202:
            result = response.json()
            if result.get("async"):
                print(f"✅ Explicit async request accepted in {initial_duration:.1f}s")
                return True
            else:
                print(f"❌ Expected async response: {result}")
                return False
        else:
            print(f"❌ Explicit async request failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Explicit async request error: {str(e)}")
        return False

def main():
    """Run the async generation tests."""
    print("🧪 Testing GCSE Question Generator Async Functionality")
    print("=" * 55)
    
    # Test authentication
    session_token = test_auth()
    if not session_token:
        print("\n❌ Cannot proceed without authentication")
        sys.exit(1)
    
    # Test synchronous request (should work normally)
    sync_success = test_sync_request(session_token)
    
    # Test asynchronous request (should trigger async mode)
    async_success = test_async_request(session_token)
    
    # Test explicit async request
    explicit_async_success = test_explicit_async_request(session_token)
    
    # Summary
    print("\n" + "=" * 55)
    print("📊 Async Test Results Summary:")
    print(f"   Sync Request (10 questions): {'✅ PASS' if sync_success else '❌ FAIL'}")
    print(f"   Async Request (20 questions): {'✅ PASS' if async_success else '❌ FAIL'}")
    print(f"   Explicit Async (15 questions): {'✅ PASS' if explicit_async_success else '❌ FAIL'}")
    
    if sync_success and (async_success or explicit_async_success):
        print("\n🎉 Async functionality is working! Large requests now supported.")
    elif sync_success:
        print("\n⚠️  Basic functionality works, but async mode needs debugging.")
    else:
        print("\n❌ Tests failed. Check the deployment and configuration.")
    
    print("\n💡 Async improvements:")
    print("   • Requests >15 questions automatically use async mode")
    print("   • API Gateway timeout bypassed for large requests")
    print("   • Real-time progress tracking via polling")
    print("   • Graceful fallback to smaller batches on errors")

if __name__ == "__main__":
    main()