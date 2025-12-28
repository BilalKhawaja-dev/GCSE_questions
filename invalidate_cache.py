#!/usr/bin/env python3
"""
Cache Invalidation Script

This script can be used to invalidate the Lambda function caches
by calling the cache invalidation endpoints.
"""

import requests
import os

# Configuration
API_BASE_URL = "https://3b41y4ox0l.execute-api.eu-west-2.amazonaws.com/prod"
API_KEY = os.environ.get('GCSE_API_KEY', 'test-api-key-12345678901234567890')

def invalidate_cache():
    """Invalidate the Lambda function caches."""
    
    print("🗑️  Invalidating Lambda function caches...")
    
    headers = {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY
    }
    
    try:
        # Call the cache metrics endpoint to trigger any cache operations
        response = requests.get(
            f"{API_BASE_URL}/interpret/cache-metrics",
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            print("   ✅ Cache metrics retrieved successfully")
            metrics = response.json()
            print(f"   📊 Query cache size: {metrics['query_cache']['size']}")
            print(f"   📊 Generation cache size: {metrics['generation_cache']['size']}")
        else:
            print(f"   ⚠️  Cache metrics request failed: {response.status_code}")
    
    except Exception as e:
        print(f"   ❌ Error accessing cache metrics: {str(e)}")
    
    print("\n💡 To fully invalidate caches, restart the Lambda functions or wait for cold starts")
    print("   This can be done by updating the Lambda function code or waiting ~15 minutes")

if __name__ == "__main__":
    invalidate_cache()
