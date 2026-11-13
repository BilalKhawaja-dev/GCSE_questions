#!/usr/bin/env python3
"""
Performance comparison test for parallel optimization.
"""

import boto3
import json
import time

def test_performance():
    """Test and compare performance."""
    
    print("🚀 PARALLEL OPTIMIZATION PERFORMANCE TEST")
    print("=" * 60)
    
    lambda_client = boto3.client('lambda')
    
    # Test cases
    tests = [
        (5, "Small"),
        (10, "Medium"),
        (15, "Large"),
        (20, "Very Large"),
        (30, "Extra Large")
    ]
    
    results = []
    
    for count, desc in tests:
        print(f"\n📊 Testing {desc}: {count} questions")
        
        message = {
            "Records": [{
                "body": json.dumps({
                    "job_id": f"perf_test_{count}_{int(time.time())}",
                    "session_id": f"perf_session_{count}_{int(time.time())}",
                    "topic": "Algebra",
                    "tier": "Foundation",
                    "count": count,
                    "enriched_prompt": f"Generate {count} questions",
                    "user_id": "perf_test",
                    "request_id": f"perf_{count}"
                })
            }]
        }
        
        start = time.time()
        response = lambda_client.invoke(
            FunctionName='gcse-async-worker-lambda-prod',
            InvocationType='RequestResponse',
            Payload=json.dumps(message)
        )
        elapsed = time.time() - start
        
        payload = json.loads(response['Payload'].read())
        body = json.loads(payload.get('body', '{}'))
        
        if body.get('success'):
            result = body['results'][0]
            gen_time = result.get('generation_time', elapsed)
            q_count = result.get('questions_generated', 0)
            
            qps = q_count / gen_time if gen_time > 0 else 0
            
            results.append({
                'count': count,
                'time': gen_time,
                'qps': qps
            })
            
            print(f"   ✅ {q_count} questions in {gen_time:.2f}s ({qps:.2f} q/s)")
        else:
            print(f"   ❌ Failed")
    
    # Summary
    print("\n" + "=" * 60)
    print("📈 PERFORMANCE SUMMARY")
    print("=" * 60)
    
    for r in results:
        print(f"{r['count']:2d} questions: {r['time']:6.2f}s ({r['qps']:.2f} q/s)")
    
    # Calculate improvement
    if len(results) >= 2:
        small_qps = results[0]['qps']
        large_qps = results[-1]['qps']
        
        print(f"\n🎯 Parallel Efficiency:")
        print(f"   Small requests: {small_qps:.2f} q/s")
        print(f"   Large requests: {large_qps:.2f} q/s")
        
        if large_qps > small_qps:
            improvement = (large_qps / small_qps - 1) * 100
            print(f"   Improvement: +{improvement:.1f}% for large requests")

if __name__ == "__main__":
    test_performance()