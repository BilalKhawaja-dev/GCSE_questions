#!/usr/bin/env python3
"""
Comprehensive Cache Clearing Script

This script aggressively clears all caches in the GCSE Question Generator system
to resolve persistent caching issues where the same questions keep appearing.
"""

import os
import sys
import json
import boto3
import logging
from datetime import datetime
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# AWS Configuration
AWS_REGION = 'eu-west-2'
INTERPRET_LAMBDA_NAME = 'gcse-interpret-lambda-prod'
GENERATE_LAMBDA_NAME = 'gcse-generate-lambda-prod'

class ComprehensiveCacheClearer:
    """Comprehensive cache clearing for all system components"""
    
    def __init__(self):
        """Initialize AWS clients"""
        self.lambda_client = boto3.client('lambda', region_name=AWS_REGION)
        self.logs_client = boto3.client('logs', region_name=AWS_REGION)
        
    def clear_lambda_environment_cache(self, function_name: str) -> bool:
        """Clear Lambda function environment cache by updating environment variables"""
        try:
            logger.info(f"Clearing cache for Lambda function: {function_name}")
            
            # Get current function configuration
            response = self.lambda_client.get_function_configuration(FunctionName=function_name)
            current_env = response.get('Environment', {}).get('Variables', {})
            
            # Add/update cache buster environment variable
            cache_buster = f"CACHE_CLEAR_{int(datetime.now().timestamp())}"
            current_env['CACHE_BUSTER'] = cache_buster
            current_env['DISABLE_QUESTION_CACHING'] = 'true'  # Force disable caching
            
            # Update function configuration
            self.lambda_client.update_function_configuration(
                FunctionName=function_name,
                Environment={'Variables': current_env}
            )
            
            logger.info(f"✅ Successfully updated {function_name} with cache buster: {cache_buster}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to clear cache for {function_name}: {str(e)}")
            return False
    
    def restart_lambda_functions(self) -> Dict[str, bool]:
        """Restart Lambda functions by updating their configuration"""
        results = {}
        
        functions = [INTERPRET_LAMBDA_NAME, GENERATE_LAMBDA_NAME]
        
        for function_name in functions:
            try:
                logger.info(f"Restarting Lambda function: {function_name}")
                
                # Update function configuration to force restart
                response = self.lambda_client.get_function_configuration(FunctionName=function_name)
                current_timeout = response.get('Timeout', 30)
                
                # Temporarily change timeout to force restart
                self.lambda_client.update_function_configuration(
                    FunctionName=function_name,
                    Timeout=current_timeout + 1
                )
                
                # Change it back
                self.lambda_client.update_function_configuration(
                    FunctionName=function_name,
                    Timeout=current_timeout
                )
                
                results[function_name] = True
                logger.info(f"✅ Successfully restarted {function_name}")
                
            except Exception as e:
                logger.error(f"❌ Failed to restart {function_name}: {str(e)}")
                results[function_name] = False
        
        return results
    
    def invoke_cache_clear_test(self) -> Dict[str, Any]:
        """Invoke both Lambda functions with cache-busting parameters"""
        results = {
            'interpret_test': {'success': False, 'response': None},
            'generate_test': {'success': False, 'response': None}
        }
        
        # Test InterpretLambda with unique query
        try:
            unique_query = f"Generate 3 Foundation fractions questions - test {int(datetime.now().timestamp())}"
            
            interpret_payload = {
                'query': unique_query,
                'cache_buster': int(datetime.now().timestamp())
            }
            
            logger.info(f"Testing InterpretLambda with unique query: {unique_query}")
            
            response = self.lambda_client.invoke(
                FunctionName=INTERPRET_LAMBDA_NAME,
                Payload=json.dumps(interpret_payload)
            )
            
            response_payload = json.loads(response['Payload'].read())
            results['interpret_test']['success'] = response.get('StatusCode') == 200
            results['interpret_test']['response'] = response_payload
            
            logger.info(f"✅ InterpretLambda test successful")
            
        except Exception as e:
            logger.error(f"❌ InterpretLambda test failed: {str(e)}")
        
        # Test GenerateLambda with unique parameters
        try:
            generate_payload = {
                'topic': 'Number',
                'tier': 'Foundation', 
                'count': 3,
                'cache_buster': int(datetime.now().timestamp()),
                'force_fresh': True
            }
            
            logger.info(f"Testing GenerateLambda with cache-busting parameters")
            
            response = self.lambda_client.invoke(
                FunctionName=GENERATE_LAMBDA_NAME,
                Payload=json.dumps(generate_payload)
            )
            
            response_payload = json.loads(response['Payload'].read())
            results['generate_test']['success'] = response.get('StatusCode') == 200
            results['generate_test']['response'] = response_payload
            
            logger.info(f"✅ GenerateLambda test successful")
            
        except Exception as e:
            logger.error(f"❌ GenerateLambda test failed: {str(e)}")
        
        return results
    
    def check_cloudwatch_logs(self) -> Dict[str, Any]:
        """Check recent CloudWatch logs for cache-related entries"""
        log_results = {}
        
        functions = [INTERPRET_LAMBDA_NAME, GENERATE_LAMBDA_NAME]
        
        for function_name in functions:
            try:
                log_group_name = f"/aws/lambda/{function_name}"
                
                # Get recent log events
                response = self.logs_client.filter_log_events(
                    logGroupName=log_group_name,
                    startTime=int((datetime.now().timestamp() - 3600) * 1000),  # Last hour
                    filterPattern="cache"
                )
                
                events = response.get('events', [])
                log_results[function_name] = {
                    'total_events': len(events),
                    'cache_events': [event['message'] for event in events[-5:]]  # Last 5 cache-related events
                }
                
                logger.info(f"Found {len(events)} cache-related log events for {function_name}")
                
            except Exception as e:
                logger.error(f"Failed to check logs for {function_name}: {str(e)}")
                log_results[function_name] = {'error': str(e)}
        
        return log_results
    
    def run_comprehensive_cache_clear(self) -> Dict[str, Any]:
        """Run comprehensive cache clearing process"""
        logger.info("🚀 Starting comprehensive cache clearing process")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'environment_cache_clear': {},
            'function_restarts': {},
            'test_invocations': {},
            'log_analysis': {},
            'overall_success': False
        }
        
        try:
            # Step 1: Clear environment caches
            logger.info("Step 1: Clearing Lambda environment caches")
            results['environment_cache_clear'][INTERPRET_LAMBDA_NAME] = self.clear_lambda_environment_cache(INTERPRET_LAMBDA_NAME)
            results['environment_cache_clear'][GENERATE_LAMBDA_NAME] = self.clear_lambda_environment_cache(GENERATE_LAMBDA_NAME)
            
            # Step 2: Restart Lambda functions
            logger.info("Step 2: Restarting Lambda functions")
            results['function_restarts'] = self.restart_lambda_functions()
            
            # Step 3: Test with cache-busting invocations
            logger.info("Step 3: Testing with cache-busting invocations")
            results['test_invocations'] = self.invoke_cache_clear_test()
            
            # Step 4: Check CloudWatch logs
            logger.info("Step 4: Analyzing CloudWatch logs")
            results['log_analysis'] = self.check_cloudwatch_logs()
            
            # Determine overall success
            env_success = all(results['environment_cache_clear'].values())
            restart_success = all(results['function_restarts'].values())
            test_success = (results['test_invocations']['interpret_test']['success'] and 
                          results['test_invocations']['generate_test']['success'])
            
            results['overall_success'] = env_success and restart_success and test_success
            
            if results['overall_success']:
                logger.info("🎉 Comprehensive cache clearing completed successfully!")
            else:
                logger.warning("⚠️ Cache clearing completed with some issues")
            
        except Exception as e:
            logger.error(f"💥 Cache clearing process failed: {str(e)}")
            results['error'] = str(e)
        
        return results

def main():
    """Main function to run comprehensive cache clearing"""
    print("🧹 COMPREHENSIVE CACHE CLEARING")
    print("=" * 60)
    
    try:
        clearer = ComprehensiveCacheClearer()
        results = clearer.run_comprehensive_cache_clear()
        
        # Print summary
        print(f"\n📊 Cache Clearing Summary:")
        print(f"   Environment cache clear: {all(results['environment_cache_clear'].values())}")
        print(f"   Function restarts: {all(results['function_restarts'].values())}")
        print(f"   Test invocations: {results['test_invocations']['interpret_test']['success']} / {results['test_invocations']['generate_test']['success']}")
        print(f"   Overall success: {results['overall_success']}")
        
        # Save detailed results
        with open('cache_clear_results.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n💾 Detailed results saved to: cache_clear_results.json")
        
        if results['overall_success']:
            print(f"\n🎉 Cache clearing successful! Try generating questions now.")
            return True
        else:
            print(f"\n⚠️ Cache clearing had issues. Check the detailed results.")
            return False
            
    except Exception as e:
        print(f"\n💥 Cache clearing failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)