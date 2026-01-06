#!/usr/bin/env python3
"""
Debug authorization issue by testing the complete flow
"""

import requests
import json
import time

def test_authorization_flow():
    """Test the complete authorization flow"""
    
    api_url = "https://3b41y4ox0l.execute-api.eu-west-2.amazonaws.com/prod"
    
    print("🔧 Testing Authorization Flow...")
    print()
    
    # Step 1: Login to get session token
    print("Step 1: Login to get session token")
    login_data = {
        "action": "login",
        "username": "demo",
        "password": "Demo123!"
    }
    
    try:
        response = requests.post(f"{api_url}/auth", json=login_data, timeout=30)
        print(f"Login Status: {response.status_code}")
        print(f"Login Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and data.get('session_token'):
                session_token = data['session_token']
                user_id = data['user_id']
                print(f"✅ Login successful! Token: {session_token[:20]}...")
                print()
                
                # Step 2: Test session validation
                print("Step 2: Test session validation")
                validate_data = {
                    "action": "validate",
                    "session_token": session_token
                }
                
                validate_response = requests.post(f"{api_url}/auth", json=validate_data, timeout=30)
                print(f"Validation Status: {validate_response.status_code}")
                print(f"Validation Response: {validate_response.text}")
                print()
                
                # Step 3: Test protected endpoint with Authorization header
                print("Step 3: Test protected endpoint with Authorization header")
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {session_token}",
                    "Origin": "https://d2ckebo851nz2l.cloudfront.net"
                }
                
                interpret_data = {
                    "query": "5 foundation fractions questions",
                    "user_id": user_id,
                    "session_token": session_token
                }
                
                interpret_response = requests.post(f"{api_url}/interpret", 
                                                 json=interpret_data, 
                                                 headers=headers, 
                                                 timeout=30)
                print(f"Interpret Status: {interpret_response.status_code}")
                print(f"Interpret Response: {interpret_response.text}")
                print()
                
                # Step 4: Test with different header formats
                print("Step 4: Test with X-Session-Token header")
                headers_alt = {
                    "Content-Type": "application/json",
                    "X-Session-Token": session_token,
                    "Origin": "https://d2ckebo851nz2l.cloudfront.net"
                }
                
                interpret_response_alt = requests.post(f"{api_url}/interpret", 
                                                     json=interpret_data, 
                                                     headers=headers_alt, 
                                                     timeout=30)
                print(f"Alt Header Status: {interpret_response_alt.status_code}")
                print(f"Alt Header Response: {interpret_response_alt.text}")
                print()
                
                # Step 5: Test session history endpoint
                print("Step 5: Test session history endpoint")
                history_response = requests.get(f"{api_url}/user/sessions", 
                                              headers=headers, 
                                              timeout=30)
                print(f"History Status: {history_response.status_code}")
                print(f"History Response: {history_response.text}")
                
            else:
                print(f"❌ Login failed: {data.get('message', 'Unknown error')}")
        else:
            print(f"❌ Login request failed with status {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_authorization_flow()