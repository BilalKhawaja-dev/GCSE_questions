#!/usr/bin/env python3
"""
Test parallel question generation performance with real API calls.
"""

import time
import json
import requests
import os
from datetime import datetime

# Configuration from frontend env
API_BASE_URL = "https://3b41y4ox0l.execute-api.eu-west-2.amazonaws.com/prod"
API_KEY = "test-api-key-12345678901234567890"

def test_parallel_generation():
    """Test parallel generation with different question counts."""
    
    print("🧪 Testing Parallel Question Generation Performance")
    print("=" * 60)
    print(f"API URL: {API_BASE_URL}")
    
    # Test cases: (count, description)
    test_cases = [
        (3, "Small request (should be synchronous)"),
        (8, "Medium request (should use parallel async)"),
        (15, "Large request (should use parallel async)"),
        (25, "Very large request (should use parallel async)")
    ]
    
    results = []
    
    for count, description in test_cases:
        print(f"\n📊 Testing: {description}")
        print(f"   Requesting {count} questions...")
        
        start_time = time.time()
        
        # Make API request
        try:
            response = make_generation_request(count)
            
            if response.get('async'):
                # Async request - poll for completion
                session_id = response['session_id']
                job_id = response['job_id']
                parallel = response.get('parallel_processing', False)
                
                print(f"   Job ID: {job_id}")
                print(f"   Session ID: {session_id}")
                print(f"   Parallel Processing: {parallel}")
                print(f"   Estimated completion: {response.get('estimated_completion_minutes', 'unknown')} minutes")
                
                # Poll for completion
                completion_time = poll_for_completion(session_id, job_id)
                total_time = completion_time
                
            else:
                # Synchronous request
                total_time = time.time() - start_time
                questions = response.get('questions', [])
                print(f"   Generated {len(questions)} questions synchronously")
            
            results.append({
                'count': count,
                'description': description,
                'time': total_time,
                'async': response.get('async', False),
                'parallel': response.get('parallel_processing', False)
            })
            
            print(f"   ✅ Completed in {total_time:.2f} seconds")
            
        except Exception as e:
            print(f"   ❌ Failed: {str(e)}")
            results.append({
                'count': count,
                'description': description,
                'time': None,
                'error': str(e)
            })
    
    # Print summary
    print("\n" + "=" * 60)
    print("📈 PERFORMANCE SUMMARY")
    print("=" * 60)
    
    for result in results:
        if result.get('time'):
            questions_per_second = result['count'] / result['time']
            mode = "Async (Parallel)" if result.get('parallel') else "Async" if result.get('async') else "Sync"
            print(f"{result['count']:2d} questions: {result['time']:6.2f}s ({questions_per_second:.1f} q/s) - {mode}")
        else:
            print(f"{result['count']:2d} questions: FAILED - {result.get('error', 'Unknown error')}")
    
    # Calculate improvements
    if len([r for r in results if r.get('time')]) >= 2:
        print("\n🚀 PERFORMANCE IMPROVEMENTS:")
        
        # Compare sync vs async
        sync_results = [r for r in results if r.get('time') and not r.get('async')]
        async_results = [r for r in results if r.get('time') and r.get('async')]
        
        if sync_results and async_results:
            sync_rate = sum(r['count'] / r['time'] for r in sync_results) / len(sync_results)
            async_rate = sum(r['count'] / r['time'] for r in async_results) / len(async_results)
            
            if async_rate > sync_rate:
                improvement = async_rate / sync_rate
                print(f"• Async processing is {improvement:.1f}x faster than sync")
            
        # Compare parallel vs non-parallel async
        parallel_results = [r for r in results if r.get('time') and r.get('parallel')]
        if parallel_results:
            parallel_rate = sum(r['count'] / r['time'] for r in parallel_results) / len(parallel_results)
            print(f"• Parallel processing achieves {parallel_rate:.1f} questions/second")

def make_generation_request(count: int):
    """Make a question generation request to the real API."""
    
    # Create a test query
    query = f"{count} Foundation algebra questions"
    
    headers = {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY
    }
    
    # Use the generateQuestionsFromQuery endpoint approach
    data = {
        'query': query,
        'force_async': count > 5,  # Force async for larger requests
        'parallel_processing': True  # Enable parallel processing
    }
    
    # For testing, we need to simulate the full flow
    # First interpret the query, then generate
    try:
        # Step 1: Interpret query (simplified - we'll construct the request directly)
        generate_data = {
            'topic': 'Algebra',
            'tier': 'Foundation',
            'count': count,
            'specification_version': 'latest',
            'enriched_prompt': query,
            'force_async': count > 5,
            'parallel_processing': True
        }
        
        print(f"   Making request to {API_BASE_URL}/generate")
        response = requests.post(
            f"{API_BASE_URL}/generate",
            headers=headers,
            json=generate_data,
            timeout=30  # Short timeout for initial request
        )
        
        if response.status_code != 200:
            raise Exception(f"API returned {response.status_code}: {response.text}")
        
        return response.json()
        
    except requests.exceptions.Timeout:
        raise Exception("Request timed out")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Request failed: {str(e)}")

def poll_for_completion(session_id: str, job_id: str, max_wait: int = 300) -> float:
    """Poll for async job completion using the session endpoint."""
    
    start_time = time.time()
    poll_interval = 3  # seconds (faster for parallel processing)
    
    print(f"   Polling for completion (max {max_wait}s)...")
    
    headers = {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY
    }
    
    while time.time() - start_time < max_wait:
        try:
            # Check session status
            response = requests.get(
                f"{API_BASE_URL}/user/sessions/{session_id}",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                session_data = response.json()
                status = session_data.get('metadata', {}).get('status', 'unknown')
                progress = session_data.get('metadata', {}).get('progress', 0)
                
                elapsed = time.time() - start_time
                print(f"   Status: {status} ({progress}%) - {elapsed:.1f}s elapsed")
                
                if status == 'completed':
                    questions = session_data.get('generated_questions', [])
                    print(f"   Job completed! Generated {len(questions)} questions")
                    return elapsed
                elif status == 'failed':
                    error = session_data.get('metadata', {}).get('error', 'Unknown error')
                    raise Exception(f"Job failed: {error}")
            
            # Still processing, wait and try again
            time.sleep(poll_interval)
            
        except requests.exceptions.RequestException as e:
            print(f"   Polling error: {str(e)}")
            time.sleep(poll_interval)
    
    raise TimeoutError(f"Job {job_id} did not complete within {max_wait} seconds")

if __name__ == "__main__":
    test_parallel_generation()