#!/usr/bin/env python3
"""
AI Integration Pipeline Validation Script

This script validates that the two-stage AI processing pipeline is working correctly:
1. InterpretLambda (Claude Haiku) - Natural language → Structured intent
2. GenerateLambda (Claude Sonnet) - Structured intent → Questions

Tests different queries to ensure unique responses and validates actual Bedrock API calls.
"""

import json
import requests
import time
import uuid
from typing import Dict, Any, List
import os
from datetime import datetime

# Configuration
API_BASE_URL = "https://3b41y4ox0l.execute-api.eu-west-2.amazonaws.com/prod"
API_KEY = os.environ.get('GCSE_API_KEY', 'test-api-key-12345678901234567890')

# Test queries to validate unique responses
TEST_QUERIES = [
    "Generate 3 Foundation fractions questions",
    "Create 2 Higher algebra questions about linear equations", 
    "I need 4 Foundation geometry questions on angles",
    "Make 1 Higher statistics question about mean and median",
    "Generate 5 Foundation number questions with decimals",
    "Create 3 Higher probability questions",
    "I want 2 Foundation ratio questions",
    "Generate 4 Higher quadratic equation questions"
]

class AIIntegrationValidator:
    """Validates AI integration pipeline functionality."""
    
    def __init__(self, api_base_url: str, api_key: str):
        self.api_base_url = api_base_url
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'X-API-Key': api_key
        })
        
        # Track responses for uniqueness validation
        self.interpret_responses = []
        self.generation_responses = []
        
    def validate_interpret_lambda(self, query: str) -> Dict[str, Any]:
        """
        Test InterpretLambda with a specific query.
        
        Args:
            query: Natural language query to test
            
        Returns:
            Response data and metadata
        """
        print(f"\n🔍 Testing InterpretLambda with query: '{query}'")
        
        start_time = time.time()
        
        try:
            response = self.session.post(
                f"{self.api_base_url}/interpret",
                json={"query": query},
                timeout=35  # Slightly longer than Lambda timeout
            )
            
            response_time = time.time() - start_time
            
            print(f"   ⏱️  Response time: {response_time:.2f}s")
            print(f"   📊 Status code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for cache status
                cache_status = response.headers.get('X-Cache-Status', 'UNKNOWN')
                print(f"   💾 Cache status: {cache_status}")
                
                # Validate response structure
                required_fields = ['topic', 'tier', 'count', 'confidence', 'request_id']
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    print(f"   ❌ Missing fields: {missing_fields}")
                    return {"success": False, "error": f"Missing fields: {missing_fields}"}
                
                print(f"   ✅ Parsed intent:")
                print(f"      Topic: {data['topic']}")
                print(f"      Tier: {data['tier']}")
                print(f"      Count: {data['count']}")
                print(f"      Confidence: {data['confidence']:.2f}")
                print(f"      Request ID: {data['request_id']}")
                
                # Store for uniqueness check
                self.interpret_responses.append({
                    'query': query,
                    'response': data,
                    'cache_status': cache_status,
                    'response_time': response_time
                })
                
                return {
                    "success": True,
                    "data": data,
                    "cache_status": cache_status,
                    "response_time": response_time
                }
                
            else:
                error_data = response.json() if response.content else {}
                print(f"   ❌ Error: {error_data}")
                return {"success": False, "error": error_data}
                
        except requests.exceptions.Timeout:
            print(f"   ⏰ Request timed out after 35 seconds")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            print(f"   💥 Exception: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def validate_generate_lambda(self, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Test GenerateLambda with structured intent.
        
        Args:
            intent_data: Structured intent from InterpretLambda
            
        Returns:
            Response data and metadata
        """
        print(f"\n🎯 Testing GenerateLambda with intent:")
        print(f"   Topic: {intent_data['topic']}, Tier: {intent_data['tier']}, Count: {intent_data['count']}")
        
        start_time = time.time()
        
        # Prepare generation request
        generation_request = {
            "topic": intent_data['topic'],
            "tier": intent_data['tier'],
            "count": intent_data['count'],
            "specification_version": "latest"
        }
        
        if 'subtopic' in intent_data and intent_data['subtopic']:
            generation_request['subtopic'] = intent_data['subtopic']
        
        try:
            response = self.session.post(
                f"{self.api_base_url}/generate",
                json=generation_request,
                timeout=65  # Slightly longer than Lambda timeout
            )
            
            response_time = time.time() - start_time
            
            print(f"   ⏱️  Response time: {response_time:.2f}s")
            print(f"   📊 Status code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for cache status
                cache_status = response.headers.get('X-Cache-Status', 'UNKNOWN')
                print(f"   💾 Cache status: {cache_status}")
                
                # Validate response structure
                required_fields = ['questions', 'mark_scheme', 'metadata']
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    print(f"   ❌ Missing fields: {missing_fields}")
                    return {"success": False, "error": f"Missing fields: {missing_fields}"}
                
                questions = data['questions']
                mark_schemes = data['mark_scheme']
                metadata = data['metadata']
                
                print(f"   ✅ Generated {len(questions)} questions:")
                for i, question in enumerate(questions[:2], 1):  # Show first 2 questions
                    print(f"      Q{i}: {question['question_text'][:100]}...")
                    print(f"          Marks: {question['marks']}, Topic: {question['topic']}")
                
                print(f"   📈 Total marks: {metadata['total_marks']}")
                print(f"   🤖 Model version: {metadata['model_version']}")
                print(f"   📚 Spec version: {metadata.get('specification_version', 'N/A')}")
                
                # Store for uniqueness check
                self.generation_responses.append({
                    'request': generation_request,
                    'response': data,
                    'cache_status': cache_status,
                    'response_time': response_time
                })
                
                return {
                    "success": True,
                    "data": data,
                    "cache_status": cache_status,
                    "response_time": response_time
                }
                
            else:
                error_data = response.json() if response.content else {}
                print(f"   ❌ Error: {error_data}")
                return {"success": False, "error": error_data}
                
        except requests.exceptions.Timeout:
            print(f"   ⏰ Request timed out after 65 seconds")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            print(f"   💥 Exception: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def test_end_to_end_pipeline(self, query: str) -> Dict[str, Any]:
        """
        Test complete end-to-end pipeline for a single query.
        
        Args:
            query: Natural language query to test
            
        Returns:
            Complete pipeline test results
        """
        print(f"\n{'='*80}")
        print(f"🚀 TESTING END-TO-END PIPELINE")
        print(f"Query: '{query}'")
        print(f"{'='*80}")
        
        # Step 1: Test InterpretLambda
        interpret_result = self.validate_interpret_lambda(query)
        
        if not interpret_result["success"]:
            return {
                "query": query,
                "success": False,
                "stage": "interpret",
                "error": interpret_result["error"]
            }
        
        # Step 2: Test GenerateLambda
        generate_result = self.validate_generate_lambda(interpret_result["data"])
        
        if not generate_result["success"]:
            return {
                "query": query,
                "success": False,
                "stage": "generate",
                "error": generate_result["error"],
                "interpret_data": interpret_result["data"]
            }
        
        # Step 3: Validate pipeline integrity
        pipeline_validation = self.validate_pipeline_integrity(
            query, interpret_result, generate_result
        )
        
        return {
            "query": query,
            "success": True,
            "interpret_result": interpret_result,
            "generate_result": generate_result,
            "pipeline_validation": pipeline_validation,
            "total_time": interpret_result["response_time"] + generate_result["response_time"]
        }
    
    def validate_pipeline_integrity(self, query: str, interpret_result: Dict, generate_result: Dict) -> Dict[str, Any]:
        """
        Validate that the pipeline maintains integrity between stages.
        
        Args:
            query: Original query
            interpret_result: InterpretLambda result
            generate_result: GenerateLambda result
            
        Returns:
            Pipeline integrity validation results
        """
        validation_results = {
            "topic_consistency": False,
            "tier_consistency": False,
            "count_consistency": False,
            "ai_processing_evidence": False,
            "unique_content": False
        }
        
        interpret_data = interpret_result["data"]
        generate_data = generate_result["data"]
        
        # Check topic consistency
        if interpret_data["topic"] == generate_data["questions"][0]["topic"]:
            validation_results["topic_consistency"] = True
            print(f"   ✅ Topic consistency: {interpret_data['topic']}")
        else:
            print(f"   ❌ Topic mismatch: {interpret_data['topic']} vs {generate_data['questions'][0]['topic']}")
        
        # Check tier consistency
        if interpret_data["tier"] == generate_data["questions"][0]["tier"]:
            validation_results["tier_consistency"] = True
            print(f"   ✅ Tier consistency: {interpret_data['tier']}")
        else:
            print(f"   ❌ Tier mismatch: {interpret_data['tier']} vs {generate_data['questions'][0]['tier']}")
        
        # Check count consistency
        if interpret_data["count"] == len(generate_data["questions"]):
            validation_results["count_consistency"] = True
            print(f"   ✅ Count consistency: {interpret_data['count']}")
        else:
            print(f"   ❌ Count mismatch: {interpret_data['count']} vs {len(generate_data['questions'])}")
        
        # Check for evidence of AI processing (not just cached responses)
        cache_evidence = []
        if interpret_result["cache_status"] == "MISS":
            cache_evidence.append("InterpretLambda cache miss")
        if generate_result["cache_status"] == "MISS":
            cache_evidence.append("GenerateLambda cache miss")
        
        if cache_evidence:
            validation_results["ai_processing_evidence"] = True
            print(f"   ✅ AI processing evidence: {', '.join(cache_evidence)}")
        else:
            print(f"   ⚠️  Both responses cached - may not be testing AI processing")
        
        # Check for unique content (questions should be different from previous tests)
        question_texts = [q["question_text"] for q in generate_data["questions"]]
        is_unique = True
        
        for prev_response in self.generation_responses[:-1]:  # Exclude current response
            prev_questions = [q["question_text"] for q in prev_response["response"]["questions"]]
            if any(q in prev_questions for q in question_texts):
                is_unique = False
                break
        
        validation_results["unique_content"] = is_unique
        if is_unique:
            print(f"   ✅ Unique content generated")
        else:
            print(f"   ❌ Duplicate content detected - possible caching issue")
        
        return validation_results
    
    def run_comprehensive_validation(self) -> Dict[str, Any]:
        """
        Run comprehensive validation of the AI integration pipeline.
        
        Returns:
            Complete validation results
        """
        print(f"\n{'='*100}")
        print(f"🧪 COMPREHENSIVE AI INTEGRATION PIPELINE VALIDATION")
        print(f"{'='*100}")
        print(f"Testing {len(TEST_QUERIES)} different queries to validate:")
        print(f"1. Two-stage AI processing (Haiku → Sonnet)")
        print(f"2. Unique response generation")
        print(f"3. Pipeline integrity")
        print(f"4. Actual Bedrock API usage")
        
        results = []
        
        for i, query in enumerate(TEST_QUERIES, 1):
            print(f"\n📝 Test {i}/{len(TEST_QUERIES)}")
            result = self.test_end_to_end_pipeline(query)
            results.append(result)
            
            # Add delay between tests to avoid rate limiting
            if i < len(TEST_QUERIES):
                time.sleep(2)
        
        # Generate summary report
        summary = self.generate_validation_summary(results)
        
        return {
            "test_results": results,
            "summary": summary,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def generate_validation_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate summary of validation results.
        
        Args:
            results: List of test results
            
        Returns:
            Summary statistics and findings
        """
        print(f"\n{'='*100}")
        print(f"📊 VALIDATION SUMMARY")
        print(f"{'='*100}")
        
        total_tests = len(results)
        successful_tests = sum(1 for r in results if r["success"])
        
        print(f"Total tests: {total_tests}")
        print(f"Successful tests: {successful_tests}")
        print(f"Success rate: {successful_tests/total_tests*100:.1f}%")
        
        if successful_tests == 0:
            print("❌ No successful tests - AI integration appears to be broken")
            return {
                "success_rate": 0.0,
                "ai_integration_working": False,
                "issues": ["No successful API calls"]
            }
        
        # Analyze successful tests
        successful_results = [r for r in results if r["success"]]
        
        # Check cache behavior
        interpret_cache_misses = sum(1 for r in successful_results 
                                   if r["interpret_result"]["cache_status"] == "MISS")
        generate_cache_misses = sum(1 for r in successful_results 
                                  if r["generate_result"]["cache_status"] == "MISS")
        
        print(f"\n🔍 Cache Analysis:")
        print(f"InterpretLambda cache misses: {interpret_cache_misses}/{successful_tests}")
        print(f"GenerateLambda cache misses: {generate_cache_misses}/{successful_tests}")
        
        # Check pipeline integrity
        integrity_checks = ["topic_consistency", "tier_consistency", "count_consistency", 
                          "ai_processing_evidence", "unique_content"]
        
        integrity_scores = {}
        for check in integrity_checks:
            score = sum(1 for r in successful_results 
                       if r["pipeline_validation"][check]) / successful_tests
            integrity_scores[check] = score
            print(f"{check}: {score*100:.1f}%")
        
        # Check for unique content generation
        unique_questions = set()
        duplicate_count = 0
        
        for result in successful_results:
            questions = result["generate_result"]["data"]["questions"]
            for question in questions:
                q_text = question["question_text"]
                if q_text in unique_questions:
                    duplicate_count += 1
                else:
                    unique_questions.add(q_text)
        
        total_questions = sum(len(r["generate_result"]["data"]["questions"]) 
                            for r in successful_results)
        uniqueness_rate = (total_questions - duplicate_count) / total_questions if total_questions > 0 else 0
        
        print(f"\n📝 Content Analysis:")
        print(f"Total questions generated: {total_questions}")
        print(f"Unique questions: {len(unique_questions)}")
        print(f"Duplicate questions: {duplicate_count}")
        print(f"Uniqueness rate: {uniqueness_rate*100:.1f}%")
        
        # Determine overall AI integration status
        ai_integration_working = (
            successful_tests > 0 and
            (interpret_cache_misses > 0 or generate_cache_misses > 0) and
            integrity_scores["topic_consistency"] > 0.8 and
            integrity_scores["tier_consistency"] > 0.8 and
            uniqueness_rate > 0.5
        )
        
        issues = []
        if successful_tests == 0:
            issues.append("No successful API calls")
        if interpret_cache_misses == 0 and generate_cache_misses == 0:
            issues.append("All responses cached - AI may not be processing")
        if integrity_scores["topic_consistency"] < 0.8:
            issues.append("Topic consistency issues between stages")
        if integrity_scores["tier_consistency"] < 0.8:
            issues.append("Tier consistency issues between stages")
        if uniqueness_rate < 0.5:
            issues.append("High duplicate content rate - caching issue suspected")
        
        print(f"\n🎯 Overall Assessment:")
        if ai_integration_working:
            print("✅ AI integration appears to be working correctly")
        else:
            print("❌ AI integration has issues:")
            for issue in issues:
                print(f"   - {issue}")
        
        return {
            "success_rate": successful_tests / total_tests,
            "ai_integration_working": ai_integration_working,
            "cache_analysis": {
                "interpret_cache_misses": interpret_cache_misses,
                "generate_cache_misses": generate_cache_misses
            },
            "integrity_scores": integrity_scores,
            "content_analysis": {
                "total_questions": total_questions,
                "unique_questions": len(unique_questions),
                "duplicate_questions": duplicate_count,
                "uniqueness_rate": uniqueness_rate
            },
            "issues": issues
        }


def main():
    """Main function to run AI integration validation."""
    
    # Check for API key
    if not os.environ.get('GCSE_API_KEY'):
        print("⚠️  Warning: GCSE_API_KEY environment variable not set, using default test key")
    
    # Initialize validator
    validator = AIIntegrationValidator(API_BASE_URL, API_KEY)
    
    # Run comprehensive validation
    results = validator.run_comprehensive_validation()
    
    # Save results to file
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    results_file = f"ai_integration_validation_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to: {results_file}")
    
    # Return exit code based on validation success
    if results["summary"]["ai_integration_working"]:
        print("\n🎉 AI Integration Validation: PASSED")
        return 0
    else:
        print("\n💥 AI Integration Validation: FAILED")
        return 1


if __name__ == "__main__":
    exit(main())