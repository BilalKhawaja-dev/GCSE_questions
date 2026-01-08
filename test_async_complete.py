"""
Complete end-to-end test of async generation with same user.
"""

import requests
import json
import time

API_URL = "https://3b41y4ox0l.execute-api.eu-west-2.amazonaws.com/prod"

print("=== Complete Async Generation Test ===\n")

# Step 1: Register new user
print("Step 1: Registering new user...")
import uuid
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
    print(f"❌ Registration failed: {auth_response.text}")
    exit(1)

auth_data = auth_response.json()
session_token = auth_data['session_token']
user_id = auth_data['user_id']

print(f"✅ Registered as {user_id}")
print(f"   Session token: {session_token[:20]}...\n")

# Step 2: Interpret query
print("Step 2: Interpreting query for 15 questions...")
interpret_response = requests.post(
    f"{API_URL}/interpret",
    headers={"Authorization": f"Bearer {session_token}"},
    json={"query": "15 Higher Algebra questions"}
)

if interpret_response.status_code != 200:
    print(f"❌ Interpretation failed: {interpret_response.text}")
    exit(1)

interpret_data = interpret_response.json()
intent = interpret_data['intent']
enriched_prompt = interpret_data.get('enriched_prompt', '')

print(f"✅ Query interpreted: {intent['count']} {intent['tier']} {intent['topic']}\n")

# Step 3: Generate questions (should be async)
print("Step 3: Generating questions...")
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

print(f"   HTTP Status: {generate_response.status_code}")

if generate_response.status_code == 202:
    generate_data = generate_response.json()
    print(f"✅ Async job created")
    print(f"   Job ID: {generate_data['job_id']}")
    print(f"   Session ID: {generate_data['session_id']}")
    print(f"   Status: {generate_data['status']}\n")
    
    session_id = generate_data['session_id']
    
    # Step 4: Poll for completion
    print("Step 4: Polling for completion...")
    max_polls = 30
    poll_interval = 5
    
    for poll_num in range(1, max_polls + 1):
        time.sleep(poll_interval)
        
        poll_response = requests.get(
            f"{API_URL}/user/sessions/{session_id}",
            headers={"Authorization": f"Bearer {session_token}"}
        )
        
        print(f"   Poll {poll_num}: HTTP {poll_response.status_code}", end="")
        
        if poll_response.status_code == 200:
            poll_data = poll_response.json()
            status = poll_data.get('metadata', {}).get('status', 'unknown')
            progress = poll_data.get('metadata', {}).get('progress', 0)
            
            print(f" - Status: {status}, Progress: {progress}%")
            
            if status == 'completed':
                questions = poll_data.get('generated_questions', [])
                gen_time = poll_data.get('metadata', {}).get('generation_time', 0)
                
                print(f"\n✅ Generation completed!")
                print(f"   Questions generated: {len(questions)}")
                print(f"   Generation time: {gen_time:.2f}s")
                print(f"   Total polls: {poll_num}")
                print(f"   Total wait time: {poll_num * poll_interval}s")
                
                if questions:
                    print(f"\n   Sample question:")
                    print(f"   {questions[0].get('question_text', 'N/A')[:100]}...")
                
                exit(0)
            
            elif status == 'failed':
                error = poll_data.get('metadata', {}).get('error', 'Unknown')
                print(f"\n❌ Generation failed: {error}")
                exit(1)
        else:
            print(f" - Session not found")
    
    print(f"\n❌ Timeout after {max_polls * poll_interval}s")
    exit(1)

elif generate_response.status_code == 200:
    # Synchronous response
    generate_data = generate_response.json()
    questions = generate_data.get('questions', [])
    print(f"✅ Synchronous generation completed")
    print(f"   Questions: {len(questions)}")
    exit(0)

else:
    print(f"❌ Generation failed: {generate_response.status_code}")
    print(f"   Response: {generate_response.text}")
    exit(1)
