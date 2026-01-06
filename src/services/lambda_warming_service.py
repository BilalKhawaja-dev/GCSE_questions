"""
Lambda Warming Service for GCSE Question Generator V2

This service provides Lambda warming functionality to reduce cold starts
and improve response times.
"""

import boto3
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.utils.logging_service import logger

class LambdaWarmingService:
    """Service for warming Lambda functions to reduce cold starts."""
    
    def __init__(self, region: str = 'eu-west-2'):
        """
        Initialize the Lambda warming service.
        
        Args:
            region: AWS region for Lambda functions
        """
        self.lambda_client = boto3.client('lambda', region_name=region)
        self.cloudwatch = boto3.client('cloudwatch', region_name=region)
        self.region = region
        
        # Default warming configuration
        self.warming_config = {
            'concurrent_executions': 2,  # Number of concurrent invocations per function
            'warming_interval_minutes': 5,  # How often to warm functions
            'timeout_seconds': 30  # Timeout for warming invocations
        }
    
    def warm_function(self, function_name: str, concurrent_executions: int = 2) -> Dict[str, Any]:
        """
        Warm a single Lambda function.
        
        Args:
            function_name: Name of the Lambda function to warm
            concurrent_executions: Number of concurrent warming invocations
            
        Returns:
            Dict with warming results
        """
        logger.info(f"Warming Lambda function: {function_name}")
        
        warming_event = {
            'source': 'lambda-warmer',
            'warmer': True,
            'timestamp': datetime.utcnow().isoformat(),
            'concurrent_execution': True
        }
        
        results = {
            'function_name': function_name,
            'concurrent_executions': concurrent_executions,
            'successful_invocations': 0,
            'failed_invocations': 0,
            'total_duration_ms': 0,
            'errors': []
        }
        
        start_time = time.time()
        
        # Use ThreadPoolExecutor for concurrent warming
        with ThreadPoolExecutor(max_workers=concurrent_executions) as executor:
            # Submit warming invocations
            futures = []
            for i in range(concurrent_executions):
                warming_event['execution_id'] = i
                future = executor.submit(self._invoke_function, function_name, warming_event)
                futures.append(future)
            
            # Collect results
            for future in as_completed(futures, timeout=self.warming_config['timeout_seconds']):
                try:
                    result = future.result()
                    if result['success']:
                        results['successful_invocations'] += 1
                    else:
                        results['failed_invocations'] += 1
                        results['errors'].append(result['error'])
                except Exception as e:
                    results['failed_invocations'] += 1
                    results['errors'].append(str(e))
        
        results['total_duration_ms'] = (time.time() - start_time) * 1000
        
        logger.info(f"Warming completed for {function_name}: "
                   f"{results['successful_invocations']}/{concurrent_executions} successful")
        
        return results
    
    def warm_multiple_functions(self, function_names: List[str], 
                              concurrent_executions: int = 2) -> Dict[str, Any]:
        """
        Warm multiple Lambda functions concurrently.
        
        Args:
            function_names: List of Lambda function names to warm
            concurrent_executions: Number of concurrent warming invocations per function
            
        Returns:
            Dict with warming results for all functions
        """
        logger.info(f"Warming {len(function_names)} Lambda functions")
        
        overall_results = {
            'total_functions': len(function_names),
            'successful_functions': 0,
            'failed_functions': 0,
            'total_duration_ms': 0,
            'function_results': {}
        }
        
        start_time = time.time()
        
        # Warm functions concurrently
        with ThreadPoolExecutor(max_workers=min(len(function_names), 5)) as executor:
            future_to_function = {
                executor.submit(self.warm_function, func_name, concurrent_executions): func_name
                for func_name in function_names
            }
            
            for future in as_completed(future_to_function, timeout=120):  # 2 minute timeout
                function_name = future_to_function[future]
                try:
                    result = future.result()
                    overall_results['function_results'][function_name] = result
                    
                    if result['successful_invocations'] > 0:
                        overall_results['successful_functions'] += 1
                    else:
                        overall_results['failed_functions'] += 1
                        
                except Exception as e:
                    logger.error(f"Failed to warm function {function_name}: {str(e)}")
                    overall_results['failed_functions'] += 1
                    overall_results['function_results'][function_name] = {
                        'function_name': function_name,
                        'error': str(e),
                        'successful_invocations': 0,
                        'failed_invocations': concurrent_executions
                    }
        
        overall_results['total_duration_ms'] = (time.time() - start_time) * 1000
        
        logger.info(f"Warming completed for all functions: "
                   f"{overall_results['successful_functions']}/{len(function_names)} successful")
        
        return overall_results
    
    def _invoke_function(self, function_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invoke a single Lambda function for warming.
        
        Args:
            function_name: Name of the Lambda function
            payload: Payload to send to the function
            
        Returns:
            Dict with invocation result
        """
        try:
            response = self.lambda_client.invoke(
                FunctionName=function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            
            # Check if invocation was successful
            status_code = response['StatusCode']
            if status_code == 200:
                # Read response payload
                response_payload = json.loads(response['Payload'].read())
                
                return {
                    'success': True,
                    'status_code': status_code,
                    'duration_ms': response_payload.get('duration', 0),
                    'response': response_payload
                }
            else:
                return {
                    'success': False,
                    'status_code': status_code,
                    'error': f"Invocation failed with status code {status_code}"
                }
                
        except Exception as e:
            logger.error(f"Failed to invoke {function_name}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_function_cold_start_metrics(self, function_name: str, 
                                      hours: int = 24) -> Dict[str, Any]:
        """
        Get cold start metrics for a Lambda function.
        
        Args:
            function_name: Name of the Lambda function
            hours: Number of hours to look back for metrics
            
        Returns:
            Dict with cold start metrics
        """
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)
            
            # Get initialization duration metrics (cold starts)
            response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/Lambda',
                MetricName='InitDuration',
                Dimensions=[
                    {
                        'Name': 'FunctionName',
                        'Value': function_name
                    }
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,  # 1 hour periods
                Statistics=['Average', 'Maximum', 'SampleCount']
            )
            
            datapoints = response['Datapoints']
            if not datapoints:
                return {
                    'function_name': function_name,
                    'cold_starts': 0,
                    'avg_init_duration_ms': 0,
                    'max_init_duration_ms': 0
                }
            
            # Calculate metrics
            total_cold_starts = sum(dp['SampleCount'] for dp in datapoints)
            avg_init_duration = sum(dp['Average'] * dp['SampleCount'] for dp in datapoints) / total_cold_starts if total_cold_starts > 0 else 0
            max_init_duration = max(dp['Maximum'] for dp in datapoints)
            
            return {
                'function_name': function_name,
                'cold_starts': int(total_cold_starts),
                'avg_init_duration_ms': avg_init_duration,
                'max_init_duration_ms': max_init_duration,
                'time_period_hours': hours
            }
            
        except Exception as e:
            logger.error(f"Failed to get cold start metrics for {function_name}: {str(e)}")
            return {
                'function_name': function_name,
                'cold_starts': 0,
                'avg_init_duration_ms': 0,
                'max_init_duration_ms': 0,
                'error': str(e)
            }
    
    def create_warming_schedule(self, function_names: List[str], 
                              interval_minutes: int = 5) -> Dict[str, Any]:
        """
        Create a warming schedule for Lambda functions.
        
        Args:
            function_names: List of function names to warm
            interval_minutes: Warming interval in minutes
            
        Returns:
            Dict with schedule configuration
        """
        schedule_config = {
            'functions': function_names,
            'interval_minutes': interval_minutes,
            'concurrent_executions': self.warming_config['concurrent_executions'],
            'schedule_expression': f'rate({interval_minutes} minutes)',
            'created_at': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Created warming schedule for {len(function_names)} functions "
                   f"with {interval_minutes} minute interval")
        
        return schedule_config
    
    def analyze_warming_effectiveness(self, function_names: List[str], 
                                    hours: int = 24) -> Dict[str, Any]:
        """
        Analyze the effectiveness of Lambda warming.
        
        Args:
            function_names: List of function names to analyze
            hours: Number of hours to analyze
            
        Returns:
            Dict with warming effectiveness analysis
        """
        logger.info(f"Analyzing warming effectiveness for {len(function_names)} functions")
        
        analysis = {
            'analysis_period_hours': hours,
            'total_functions': len(function_names),
            'function_metrics': {},
            'overall_metrics': {
                'total_cold_starts': 0,
                'avg_init_duration_ms': 0,
                'functions_with_cold_starts': 0
            }
        }
        
        total_init_duration = 0
        total_cold_starts = 0
        functions_with_cold_starts = 0
        
        for function_name in function_names:
            metrics = self.get_function_cold_start_metrics(function_name, hours)
            analysis['function_metrics'][function_name] = metrics
            
            if metrics['cold_starts'] > 0:
                functions_with_cold_starts += 1
                total_cold_starts += metrics['cold_starts']
                total_init_duration += metrics['avg_init_duration_ms'] * metrics['cold_starts']
        
        # Calculate overall metrics
        analysis['overall_metrics']['total_cold_starts'] = total_cold_starts
        analysis['overall_metrics']['functions_with_cold_starts'] = functions_with_cold_starts
        
        if total_cold_starts > 0:
            analysis['overall_metrics']['avg_init_duration_ms'] = total_init_duration / total_cold_starts
        
        # Calculate effectiveness score (lower cold starts = higher effectiveness)
        max_possible_cold_starts = len(function_names) * 24 * (60 // 5)  # Assuming 5-minute intervals
        effectiveness_score = max(0, 100 - (total_cold_starts / max_possible_cold_starts * 100))
        analysis['effectiveness_score'] = effectiveness_score
        
        logger.info(f"Warming effectiveness analysis completed: "
                   f"{effectiveness_score:.1f}% effective, "
                   f"{total_cold_starts} cold starts in {hours} hours")
        
        return analysis


# Global warming service instance
lambda_warming_service = LambdaWarmingService()

if __name__ == "__main__":
    # Example usage for testing
    functions_to_warm = [
        'gcse-interpret-lambda-dev',
        'gcse-generate-lambda-dev',
        'gcse-auth-lambda-dev'
    ]
    
    # Warm functions
    results = lambda_warming_service.warm_multiple_functions(functions_to_warm)
    print(json.dumps(results, indent=2))
    
    # Analyze effectiveness
    analysis = lambda_warming_service.analyze_warming_effectiveness(functions_to_warm)
    print(json.dumps(analysis, indent=2))