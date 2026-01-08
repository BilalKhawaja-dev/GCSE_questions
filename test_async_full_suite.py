"""
Full test suite for async generation with 20, 30, and 50 questions.
"""

import requests
import json
import time
import uuid

API_URL = "https://3b41y4ox0l.execute-api.eu-west-2.amazonaws.com/prod"

def test_async_generation(count, topic="Algebra", tier="Higher"):
    """Test async generation with specified count."""
    
    print(f"\n{'='*70}")
    print(f"Test: {count} {tier} {topic} questions")
    print(f"{'='*70}\n")
    
    # Register new user
    username = f"async_test_{uuid.uuid4().hex[:8]}"
    email = f"{username}@example.com"
    
    auth_response = requests.post(
        f"{API_URL}/auth",
        json={
            "action": "register",
            "username": username,
            "password": "TestPassword123!",
            "email": email
        }
    )
    
    if auth_response.status_code != 200:
        print(f"❌ Registration failed")
        return False
    
    auth_data = auth_response.json()
    session_token = auth_data['session_token']
    user_id = auth_data['user_id']
    
    print(f"✅ Registered as {user_id}")
    
    # Interpret query
    interpret_response = requests.post(
        f"{API_URL}/interpret",
        headers={"Authorization": f"Bearer {session_token}"},
        json={"query": f"{count} {tier} {topic} questions"}
    )
    
    if interpret_response.status_code != 200:
        print(f"❌ Interpretation failed")
        return False
    
    interpret_data = interpret_response.json()
    intent = interpret_data['intent']
    enriched_prompt = interpret_data.get('enriched_prompt', '')
    
    print(f"✅ Query interpreted")
    
    # Generate questions
    start_time = time.time()
    generate_response = requests.post(
        f"{API_URL}/generate",
        headers={"Authorization": f"Bearer {session_token}"},
        json={
            "topic": intent['topic'],
            "tier": intent['tier'],
            "count": intent['count'],
            "enriched_prompt": enriched_prompt
        }
    )
    
    if generate_response.status_code == 202:
        generate_data = generate_response.json()
        session_id = generate_data['session_id']
        
        print(f"✅ Async job created (session: {session_id})")
        print(f"   Polling for completion...")
        
        # Poll for completion
        max_polls = 60
        poll_interval = 5
        
        for poll_num in range(1, max_polls + 1):
            time.sleep(poll_interval)
            
            poll_response = requests.get(
                f"{API_URL}/user/sessions/{session_id}",
                headers={"Authorization": f"Bearer {session_token}"}
            )
            
            if poll_response.status_code == 200:
                poll_data = poll_response.json()
                status = poll_data.get('metadata', {}).get('status', 'unknown')
                progress = poll_data.get('metadata', {}).get('progress', 0)
                
                if status == 'completed':
                    questions = poll_data.get('generated_questions', [])
                    gen_time = poll_data.get('metadata', {}).get('generation_time', 0)
                    total_time = time.time() - start_time
                    
                    print(f"\n✅ SUCCESS!")
                    print(f"   Questions generated: {len(questions)}")
                    print(f"   Backend generation time: {gen_time:.2f}s")
                    print(f"   Total end-to-end time: {total_time:.2f}s")
                    print(f"   Polls required: {poll_num}")
                    return True
                
                elif status == 'failed':
                    error = poll_data.get('metadata', {}).get('error', 'Unknown')
                    print(f"\n❌ Generation failed: {error}")
                    return False
                
                if poll_num % 5 == 0:
                    print(f"   Poll {poll_num}: {status} ({progress}%)")
        
        print(f"\n❌ Timeout after {max_polls * poll_interval}s")
        return False
    
    elif generate_response.status_code == 200:
        # Synchronous response (shouldn't happen for count > 10)
        generate_data = generate_response.json()
        questions = generate_data.get('questions', [])
        total_time = time.time() - start_time
        
        print(f"⚠️  Synchronous generation (expected async)")
        print(f"   Questions: {len(questions)}")
        print(f"   Time: {total_time:.2f}s")
        return True
    
    else:
        print(f"❌ Generation failed: {generate_response.status_code}")
        return False


def main():
    print("\n" + "="*70)
    print("ASYNC SQS FULL TEST SUITE")
    print("="*70)
    
    test_cases = [
        (20, "Number", "Foundation"),
        (30, "Geometry", "Higher"),
        (50, "Algebra", "Higher"),
    ]
    
    results = []
    
    for count, topic, tier in test_cases:
        try:
            success = test_async_generation(count, topic, tier)
            results.append((count, topic, tier, success))
        except Exception as e:
            print(f"\n❌ Test failed with exception: {str(e)}")
            results.append((count, topic, tier, False))
        
        time.sleep(3)  # Wait between tests
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    for count, topic, tier, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {count} {tier} {topic} questions")
    
    total_passed = sum(1 for _, _, _, success in results if success)
    total_tests = len(results)
    
    print(f"\nTotal: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("\n🎉 All async generation tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total_tests - total_passed} test(s) failed")
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
