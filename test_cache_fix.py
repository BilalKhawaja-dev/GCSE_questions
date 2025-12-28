#!/usr/bin/env python3
"""
Test Cache Fix Validation

This script tests if the cache clearing was successful by making direct API calls
with proper authentication to verify unique question generation.
"""

import os
import sys
import json
import time
import requests
import logging
from datetime import datetime
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# API Configuration - Update these with actual values
API_BASE_URL = 'https://api.gcse-questions.com'  # Update with actual API Gateway URL
API_KEY = 'your-api-key-here'  # Update with actual API key

class CacheFixTester:
    """Test if cache clearing resolved the duplicate questions issue"""
    
    def __init__(self, api_url: str, api_key: str):
        """Initialize the tester"""
        self.api_url = api_url
        self.api_key = api_key
        self.headers = {
            'Content-Type': 'application/json',
            'X-API-Key': api_key
        }
        
    def test_unique_question_generation(self) -> Dict[str, Any]:
        """Test that the same query generates different questions each time"""
        
        logger.info("🧪 Testing unique question generation")
        
        test_query = "Generate 3 Foundation fractions questions"
        results = {
            'test_query': test_query,
            'timestamp': datetime.now().isoformat(),
            'attempts': [],
            'unique_responses': 0,
            'cache_bypassed': False,
            'success': False
        }
        
        # Make 3 identical requests
        for i in range(3):
            logger.info(f"Attempt {i+1}/3: Making request")
            
            try:
                # Step 1: Interpret query
                interpret_response = requests.post(
                    f"{self.api_url}/interpret",
                    json={'query': test_query},
                    headers=self.headers,
                    timeout=30
                )
                
                if interpret_response.status_code != 200:
                    logger.error(f"Interpret failed: {interpret_response.status_code} - {interpret_response.text}")
                    results['attempts'].append({
                        'attempt': i+1,
                        'interpret_success': False,
                        'error': interpret_response.text
                    })
                    continue
                
                interpret_data = interpret_response.json()
                
                # Step 2: Generate questions
                generate_payload = {
                    'topic': interpret_data.get('topic', 'Number'),
                    'tier': interpret_data.get('tier', 'Foundation'),
                    'count': interpret_data.get('count', 3)
                }
                
                generate_response = requests.post(
                    f"{self.api_url}/generate",
                    json=generate_payload,
                    headers=self.headers,
                    timeout=60
                )
                
                if generate_response.status_code != 200:
                    logger.error(f"Generate failed: {generate_response.status_code} - {generate_response.text}")
                    results['attempts'].append({
                        'attempt': i+1,
                        'interpret_success': True,
                        'generate_success': False,
                        'error': generate_response.text
                    })
                    continue
                
                generate_data = generate_response.json()
                
                # Extract question texts for comparison
                questions = generate_data.get('questions', [])
                question_texts = [q.get('question_text', '') for q in questions]
                
                results['attempts'].append({
                    'attempt': i+1,
                    'interpret_success': True,
                    'generate_success': True,
                    'question_count': len(questions),
                    'question_texts': question_texts,
                    'response_time': generate_response.elapsed.total_seconds()
                })
                
                logger.info(f"✅ Attempt {i+1} successful - {len(questions)} questions generated")
                
                # Wait between requests
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"❌ Attempt {i+1} failed: {str(e)}")
                results['attempts'].append({
                    'attempt': i+1,
                    'error': str(e)
                })
        
        # Analyze results for uniqueness
        successful_attempts = [a for a in results['attempts'] if a.get('generate_success', False)]
        
        if len(successful_attempts) >= 2:
            # Compare question texts between attempts
            all_question_sets = [set(a['question_texts']) for a in successful_attempts]
            
            unique_sets = 0
            for i, question_set in enumerate(all_question_sets):
                is_unique = True
                for j, other_set in enumerate(all_question_sets):
                    if i != j and question_set == other_set:
                        is_unique = False
                        break
                if is_unique:
                    unique_sets += 1
            
            results['unique_responses'] = unique_sets
            results['cache_bypassed'] = unique_sets > 1
            results['success'] = results['cache_bypassed']
            
            if results['cache_bypassed']:
                logger.info("🎉 Cache bypassed successfully - unique questions generated!")
            else:
                logger.warning("⚠️ Same questions returned - cache may still be active")
        else:
            logger.error("❌ Not enough successful attempts to test uniqueness")
        
        return results
    
    def test_different_queries(self) -> Dict[str, Any]:
        """Test that different queries generate appropriate responses"""
        
        logger.info("🔄 Testing different query types")
        
        test_queries = [
            "Generate 2 Foundation number questions",
            "Create 3 Higher algebra problems", 
            "I need geometry questions about angles",
            "Make statistics questions on averages"
        ]
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'test_queries': test_queries,
            'responses': [],
            'topics_detected': set(),
            'tiers_detected': set(),
            'success': False
        }
        
        for query in test_queries:
            logger.info(f"Testing query: {query}")
            
            try:
                # Interpret query
                interpret_response = requests.post(
                    f"{self.api_url}/interpret",
                    json={'query': query},
                    headers=self.headers,
                    timeout=30
                )
                
                if interpret_response.status_code == 200:
                    interpret_data = interpret_response.json()
                    
                    results['responses'].append({
                        'query': query,
                        'topic': interpret_data.get('topic'),
                        'tier': interpret_data.get('tier'),
                        'count': interpret_data.get('count'),
                        'confidence': interpret_data.get('confidence')
                    })
                    
                    results['topics_detected'].add(interpret_data.get('topic'))
                    results['tiers_detected'].add(interpret_data.get('tier'))
                    
                    logger.info(f"✅ Detected: {interpret_data.get('topic')} / {interpret_data.get('tier')}")
                else:
                    logger.error(f"❌ Query failed: {interpret_response.status_code}")
                
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"❌ Query failed: {str(e)}")
        
        # Convert sets to lists for JSON serialization
        results['topics_detected'] = list(results['topics_detected'])
        results['tiers_detected'] = list(results['tiers_detected'])
        
        # Success if we detected multiple topics and tiers
        results['success'] = len(results['topics_detected']) > 1 and len(results['tiers_detected']) > 1
        
        return results
    
    def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run comprehensive cache fix testing"""
        
        logger.info("🚀 Starting comprehensive cache fix testing")
        
        test_results = {
            'timestamp': datetime.now().isoformat(),
            'api_url': self.api_url,
            'tests': {},
            'overall_success': False
        }
        
        try:
            # Test 1: Unique question generation
            logger.info("Test 1: Unique question generation")
            unique_test = self.test_unique_question_generation()
            test_results['tests']['unique_generation'] = unique_test
            
            # Test 2: Different query handling
            logger.info("Test 2: Different query handling")
            different_queries_test = self.test_different_queries()
            test_results['tests']['different_queries'] = different_queries_test
            
            # Determine overall success
            test_results['overall_success'] = (
                unique_test.get('success', False) and
                different_queries_test.get('success', False)
            )
            
            if test_results['overall_success']:
                logger.info("🎉 All tests passed - cache fix successful!")
            else:
                logger.warning("⚠️ Some tests failed - cache issues may persist")
            
        except Exception as e:
            logger.error(f"💥 Testing failed: {str(e)}")
            test_results['error'] = str(e)
        
        return test_results

def main():
    """Main testing function"""
    
    print("🧪 CACHE FIX VALIDATION TEST")
    print("=" * 60)
    
    # Check if API URL and key are configured
    api_url = os.getenv('GCSE_API_URL', API_BASE_URL)
    api_key = os.getenv('GCSE_API_KEY', API_KEY)
    
    if api_key == 'your-api-key-here':
        print("⚠️ API key not configured!")
        print("   Set GCSE_API_KEY environment variable or update the script")
        print("   Example: export GCSE_API_KEY='your-actual-api-key'")
        return False
    
    if api_url == 'https://api.gcse-questions.com':
        print("⚠️ API URL may need updating!")
        print("   Set GCSE_API_URL environment variable with actual API Gateway URL")
        print("   Example: export GCSE_API_URL='https://your-api-id.execute-api.eu-west-2.amazonaws.com/prod'")
    
    try:
        tester = CacheFixTester(api_url, api_key)
        results = tester.run_comprehensive_test()
        
        # Print summary
        print(f"\n📊 Test Results:")
        unique_test = results['tests'].get('unique_generation', {})
        different_test = results['tests'].get('different_queries', {})
        
        print(f"   Unique generation test: {'✅ PASSED' if unique_test.get('success') else '❌ FAILED'}")
        print(f"   Different queries test: {'✅ PASSED' if different_test.get('success') else '❌ FAILED'}")
        print(f"   Overall success: {'✅ PASSED' if results['overall_success'] else '❌ FAILED'}")
        
        # Print details
        if unique_test.get('cache_bypassed'):
            print(f"\n🎉 Cache successfully bypassed!")
            print(f"   Unique responses: {unique_test.get('unique_responses', 0)}")
        else:
            print(f"\n⚠️ Cache may still be active")
            print(f"   Same questions returned across attempts")
        
        if different_test.get('success'):
            print(f"\n🔄 Query interpretation working correctly")
            print(f"   Topics detected: {different_test.get('topics_detected', [])}")
            print(f"   Tiers detected: {different_test.get('tiers_detected', [])}")
        
        # Save detailed results
        with open('cache_fix_test_results.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n💾 Detailed results saved to: cache_fix_test_results.json")
        
        if results['overall_success']:
            print(f"\n🎉 Cache fix validation successful!")
            print(f"   The system is now generating unique questions")
            return True
        else:
            print(f"\n⚠️ Cache fix validation failed")
            print(f"   Check the detailed results and API configuration")
            return False
            
    except Exception as e:
        print(f"\n💥 Testing failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)