#!/usr/bin/env python3
"""Test the CORS function directly to see what's happening."""

import os
import sys
sys.path.append('.')

from src.utils.security import get_cors_response_headers

def test_cors_function():
    """Test the CORS function with different environment settings."""
    
    print("Testing CORS function directly...")
    
    # Test 1: No environment variable set
    if 'ENVIRONMENT' in os.environ:
        del os.environ['ENVIRONMENT']
    
    headers1 = get_cors_response_headers()
    print(f"No ENVIRONMENT var: {headers1}")
    
    # Test 2: Environment variable set to 'prod'
    os.environ['ENVIRONMENT'] = 'prod'
    headers2 = get_cors_response_headers()
    print(f"ENVIRONMENT='prod': {headers2}")
    
    # Test 3: Explicit parameter
    headers3 = get_cors_response_headers('prod')
    print(f"Explicit 'prod': {headers3}")
    
    # Test 4: Environment variable set to 'dev'
    os.environ['ENVIRONMENT'] = 'dev'
    headers4 = get_cors_response_headers()
    print(f"ENVIRONMENT='dev': {headers4}")

if __name__ == "__main__":
    test_cors_function()