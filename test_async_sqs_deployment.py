"""
Test script for async SQS deployment.
Tests large question generation requests (20, 30, 50 questions).
"""

import requests
import json
import time
import sys

# API Configuration
API_BASE_URL = "https://3b41y4ox0l.execute-api.eu-west-2.amazonaws.com/prod"

def test_async_generation(count: int, topic: str = "Algebra", tier: str = "Higher"):
    """Test async generation with specified question count."""
    
    print(f"\n{'='*60}")
    print(f"Testing Async Generation: {count} {tier} {topic} questions")
    print(f"{'='*60}\n")
    
    # Step 1: Register/Login
    print("Step 1: Authenticating...")
    auth_response = requests.post(
        f"{API_BASE_URL}/auth",
        json={
            "action": "login",
            "username": "test_user",
            "password": "TestPassword123!"
        }
    )
    
    print(f"  Login response: {auth_response.status_code}")
    if auth_response.status_code != 200:
        print(f"  Login response body: {auth_response.text}")
    
    if auth_response.status_code != 200:
        # Try registering with unique email
        import uuid
        unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        print(f"  Registering new user with email: {unique_email}...")
        auth_response = requests.post(
            f"{API_BASE_URL}/auth",
            json={
                "action": "register",
                "username": f"test_user_{uuid.uuid4().hex[:8]}",
                "password": "TestPassword123!",
                "email": unique_email
            }
        )
    
    if auth_response.status_code != 200:
        print(f"  ❌ Authentication failed: {auth_response.status_code}")
        print(f"  Response: {auth_response.text}")
        return False
    
    auth_data = auth_response.json()
    session_token = auth_data.get('session_token')
    user_id = auth_data.get('user_id')
    
    print(f"  ✅ Authenticated as {user_id}")
    
    # Step 2: Interpret query
    print("\nStep 2: Interpreting query...")
    interpret_response = requests.post(
        f"{API_BASE_URL}/interpret",
        headers={"Authorization": f"Bearer {session_token}"},
        json={
            "query": f"{count} {tier} {topic} questions"
        }
    )
    
    if interpret_response.status_code != 200:
        print(f"  ❌ Interpretation failed: {interpret_response.status_code}")
        print(f"  Response: {interpret_response.text}")
        return False
    
    interpret_data = interpret_response.json()
    intent = interpret_data.get('intent', {})
    enriched_prompt = interpret_data.get('enriched_prompt', '')
    
    print(f"  ✅ Query interpreted")
    print(f"     Topic: {intent.get('topic')}")
    print(f"     Tier: {intent.get('tier')}")
    print(f"     Count: {intent.get('count')}")
    
    # Step 3: Generate questions
    print("\nStep 3: Generating questions...")
    generate_response = requests.post(
        f"{API_BASE_URL}/generate",
        headers={"Authorization": f"Bearer {session_token}"},
        json={
            "topic": intent.get('topic'),
            "tier": intent.get('tier'),
            "count": intent.get('count'),
            "enriched_prompt": enriched_prompt
        }
    )
    
    if generate_response.status_code not in [200, 202]:
        print(f"  ❌ Generation failed: {generate_response.status_code}")
        print(f"  Response: {generate_response.text}")
        return False
    
    generate_data = generate_response.json()
    
    # Check if async
    if generate_data.get('async') or generate_response.status_code == 202:
        print(f"  ✅ Async job created")
        print(f"     Job ID: {generate_data.get('job_id')}")
        print(f"     Session ID: {generate_data.get('session_id')}")
        print(f"     Status: {generate_data.get('status')}")
        
        # Step 4: Poll for completion
        session_id = generate_data.get('session_id')
        polling_info = generate_data.get('polling_info', {})
        poll_interval = polling_info.get('recommended_poll_interval_seconds', 5)
        max_wait = polling_info.get('max_wait_time_minutes', 5) * 60
        
        print(f"\nStep 4: Polling for completion (every {poll_interval}s, max {max_wait}s)...")
        
        start_time = time.time()
        poll_count = 0
        
        while time.time() - start_time < max_wait:
            poll_count += 1
            time.sleep(poll_interval)
            
            # Check session status
            session_response = requests.get(
                f"{API_BASE_URL}/user/sessions/{session_id}",
                headers={"Authorization": f"Bearer {session_token}"}
            )
            
            if session_response.status_code != 200:
                print(f"  ⚠️  Poll {poll_count}: Failed to get session status ({session_response.status_code})")
                continue
            
            session_data = session_response.json()
            status = session_data.get('metadata', {}).get('status')
            progress = session_data.get('metadata', {}).get('progress', 0)
            
            print(f"  📊 Poll {poll_count}: Status={status}, Progress={progress}%")
            
            if status == 'completed':
                questions = session_data.get('generated_questions', [])
                generation_time = session_data.get('metadata', {}).get('generation_time', 0)
                
                print(f"\n  ✅ Generation completed!")
                print(f"     Questions generated: {len(questions)}")
                print(f"     Generation time: {generation_time:.2f}s")
                print(f"     Total polls: {poll_count}")
                print(f"     Total wait time: {time.time() - start_time:.2f}s")
                
                # Show first question as sample
                if questions:
                    print(f"\n  Sample question:")
                    print(f"     {questions[0].get('question_text', 'N/A')[:100]}...")
                
                return True
            
            elif status == 'failed':
                error = session_data.get('metadata', {}).get('error', 'Unknown error')
                print(f"\n  ❌ Generation failed: {error}")
                return False
        
        print(f"\n  ❌ Timeout after {max_wait}s")
        return False
    
    else:
        # Synchronous response
        questions = generate_data.get('questions', [])
        print(f"  ✅ Synchronous generation completed")
        print(f"     Questions generated: {len(questions)}")
        
        if questions:
            print(f"\n  Sample question:")
            print(f"     {questions[0].get('question_text', 'N/A')[:100]}...")
        
        return True


def main():
    """Run all async generation tests."""
    
    print("\n" + "="*60)
    print("ASYNC SQS DEPLOYMENT TEST SUITE")
    print("="*60)
    
    test_cases = [
        (11, "Algebra", "Higher"),  # Just above threshold
        (20, "Number", "Foundation"),  # Medium request
        (30, "Geometry", "Higher"),  # Large request
    ]
    
    results = []
    
    for count, topic, tier in test_cases:
        try:
            success = test_async_generation(count, topic, tier)
            results.append((count, topic, tier, success))
        except Exception as e:
            print(f"\n❌ Test failed with exception: {str(e)}")
            results.append((count, topic, tier, False))
        
        # Wait between tests
        time.sleep(2)
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for count, topic, tier, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {count} {tier} {topic} questions")
    
    total_passed = sum(1 for _, _, _, success in results if success)
    total_tests = len(results)
    
    print(f"\nTotal: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total_tests - total_passed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
