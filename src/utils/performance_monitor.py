"""
Performance Monitoring Utility for GCSE Question Generator V2

This utility collects performance metrics from various AWS services
and publishes them to CloudWatch for monitoring and alerting.
"""

import boto3
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from src.services.metrics_service import metrics_service
from src.utils.logging_service import logger

class PerformanceMonitor:
    """Utility class for collecting and publishing performance metrics."""
    
    def __init__(self):
        """Initialize the performance monitor with AWS clients."""
        self.cloudwatch = boto3.client('cloudwatch', region_name='eu-west-2')
        self.dynamodb = boto3.client('dynamodb', region_name='eu-west-2')
        self.lambda_client = boto3.client('lambda', region_name='eu-west-2')
        self.s3 = boto3.client('s3', region_name='eu-west-2')
        
    def collect_lambda_performance_metrics(self, function_names: List[str], 
                                         time_period_minutes: int = 60) -> Dict[str, Dict]:
        """
        Collect performance metrics for Lambda functions.
        
        Args:
            function_names: List of Lambda function names to monitor
            time_period_minutes: Time period to collect metrics for
            
        Returns:
            Dict containing performance metrics for each function
        """
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=time_period_minutes)
        
        metrics = {}
        
        for function_name in function_names:
            try:
                # Get invocation count
                invocations = self._get_cloudwatch_metric(
                    'AWS/Lambda', 'Invocations', 
                    {'FunctionName': function_name},
                    start_time, end_time, 'Sum'
                )
                
                # Get error count
                errors = self._get_cloudwatch_metric(
                    'AWS/Lambda', 'Errors',
                    {'FunctionName': function_name},
                    start_time, end_time, 'Sum'
                )
                
                # Get average duration
                duration = self._get_cloudwatch_metric(
                    'AWS/Lambda', 'Duration',
                    {'FunctionName': function_name},
                    start_time, end_time, 'Average'
                )
                
                # Get throttles
                throttles = self._get_cloudwatch_metric(
                    'AWS/Lambda', 'Throttles',
                    {'FunctionName': function_name},
                    start_time, end_time, 'Sum'
                )
                
                # Calculate success rate
                success_rate = 100.0
                if invocations > 0:
                    success_rate = ((invocations - errors) / invocations) * 100
                
                metrics[function_name] = {
                    'invocations': invocations,
                    'errors': errors,
                    'duration_ms': duration,
                    'throttles': throttles,
                    'success_rate': success_rate
                }
                
                logger.debug(f"Collected metrics for {function_name}: {metrics[function_name]}")
                
            except Exception as e:
                logger.error(f"Failed to collect metrics for {function_name}: {str(e)}")
                metrics[function_name] = {
                    'invocations': 0, 'errors': 0, 'duration_ms': 0, 
                    'throttles': 0, 'success_rate': 0
                }
        
        return metrics
    
    def collect_dynamodb_performance_metrics(self, table_names: List[str]) -> Dict[str, Dict]:
        """
        Collect performance metrics for DynamoDB tables.
        
        Args:
            table_names: List of DynamoDB table names to monitor
            
        Returns:
            Dict containing performance metrics for each table
        """
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=1)
        
        metrics = {}
        
        for table_name in table_names:
            try:
                # Get consumed read capacity
                read_capacity = self._get_cloudwatch_metric(
                    'AWS/DynamoDB', 'ConsumedReadCapacityUnits',
                    {'TableName': table_name},
                    start_time, end_time, 'Sum'
                )
                
                # Get consumed write capacity
                write_capacity = self._get_cloudwatch_metric(
                    'AWS/DynamoDB', 'ConsumedWriteCapacityUnits',
                    {'TableName': table_name},
                    start_time, end_time, 'Sum'
                )
                
                # Get throttled requests
                read_throttles = self._get_cloudwatch_metric(
                    'AWS/DynamoDB', 'ReadThrottledEvents',
                    {'TableName': table_name},
                    start_time, end_time, 'Sum'
                )
                
                write_throttles = self._get_cloudwatch_metric(
                    'AWS/DynamoDB', 'WriteThrottledEvents',
                    {'TableName': table_name},
                    start_time, end_time, 'Sum'
                )
                
                metrics[table_name] = {
                    'read_capacity_used': read_capacity,
                    'write_capacity_used': write_capacity,
                    'read_throttles': read_throttles,
                    'write_throttles': write_throttles
                }
                
                logger.debug(f"Collected DynamoDB metrics for {table_name}: {metrics[table_name]}")
                
            except Exception as e:
                logger.error(f"Failed to collect DynamoDB metrics for {table_name}: {str(e)}")
                metrics[table_name] = {
                    'read_capacity_used': 0, 'write_capacity_used': 0,
                    'read_throttles': 0, 'write_throttles': 0
                }
        
        return metrics
    
    def collect_s3_performance_metrics(self, bucket_names: List[str]) -> Dict[str, Dict]:
        """
        Collect performance metrics for S3 buckets.
        
        Args:
            bucket_names: List of S3 bucket names to monitor
            
        Returns:
            Dict containing performance metrics for each bucket
        """
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=1)
        
        metrics = {}
        
        for bucket_name in bucket_names:
            try:
                # Get request metrics
                get_requests = self._get_cloudwatch_metric(
                    'AWS/S3', 'GetRequests',
                    {'BucketName': bucket_name},
                    start_time, end_time, 'Sum'
                )
                
                put_requests = self._get_cloudwatch_metric(
                    'AWS/S3', 'PutRequests',
                    {'BucketName': bucket_name},
                    start_time, end_time, 'Sum'
                )
                
                # Get error metrics
                errors_4xx = self._get_cloudwatch_metric(
                    'AWS/S3', '4xxErrors',
                    {'BucketName': bucket_name},
                    start_time, end_time, 'Sum'
                )
                
                errors_5xx = self._get_cloudwatch_metric(
                    'AWS/S3', '5xxErrors',
                    {'BucketName': bucket_name},
                    start_time, end_time, 'Sum'
                )
                
                metrics[bucket_name] = {
                    'get_requests': get_requests,
                    'put_requests': put_requests,
                    'errors_4xx': errors_4xx,
                    'errors_5xx': errors_5xx
                }
                
                logger.debug(f"Collected S3 metrics for {bucket_name}: {metrics[bucket_name]}")
                
            except Exception as e:
                logger.error(f"Failed to collect S3 metrics for {bucket_name}: {str(e)}")
                metrics[bucket_name] = {
                    'get_requests': 0, 'put_requests': 0,
                    'errors_4xx': 0, 'errors_5xx': 0
                }
        
        return metrics
    
    def publish_performance_summary(self, lambda_metrics: Dict, dynamodb_metrics: Dict, 
                                  s3_metrics: Dict):
        """
        Publish a performance summary to CloudWatch.
        
        Args:
            lambda_metrics: Lambda performance metrics
            dynamodb_metrics: DynamoDB performance metrics
            s3_metrics: S3 performance metrics
        """
        try:
            # Calculate overall system health score
            total_lambda_invocations = sum(m['invocations'] for m in lambda_metrics.values())
            total_lambda_errors = sum(m['errors'] for m in lambda_metrics.values())
            
            overall_success_rate = 100.0
            if total_lambda_invocations > 0:
                overall_success_rate = ((total_lambda_invocations - total_lambda_errors) / 
                                      total_lambda_invocations) * 100
            
            # Calculate average response time
            avg_response_time = 0.0
            if lambda_metrics:
                response_times = [m['duration_ms'] for m in lambda_metrics.values() if m['duration_ms'] > 0]
                if response_times:
                    avg_response_time = sum(response_times) / len(response_times) / 1000  # Convert to seconds
            
            # Publish system-wide metrics
            system_metrics = [
                {
                    'name': 'SystemHealthScore',
                    'value': overall_success_rate,
                    'unit': 'Percent'
                },
                {
                    'name': 'AverageResponseTime',
                    'value': avg_response_time,
                    'unit': 'Seconds'
                },
                {
                    'name': 'TotalInvocations',
                    'value': total_lambda_invocations,
                    'unit': 'Count'
                },
                {
                    'name': 'TotalErrors',
                    'value': total_lambda_errors,
                    'unit': 'Count'
                }
            ]
            
            metrics_service.put_multiple_metrics('SystemPerformance', system_metrics)
            
            # Publish individual function performance metrics
            for function_name, metrics in lambda_metrics.items():
                function_metrics = [
                    {
                        'name': 'SuccessRate',
                        'value': metrics['success_rate'],
                        'unit': 'Percent',
                        'dimensions': {'Function': function_name}
                    },
                    {
                        'name': 'AverageResponseTime',
                        'value': metrics['duration_ms'] / 1000,  # Convert to seconds
                        'unit': 'Seconds',
                        'dimensions': {'Function': function_name}
                    }
                ]
                
                metrics_service.put_multiple_metrics('FunctionPerformance', function_metrics)
            
            logger.info("Published performance summary to CloudWatch")
            
        except Exception as e:
            logger.error(f"Failed to publish performance summary: {str(e)}")
    
    def _get_cloudwatch_metric(self, namespace: str, metric_name: str, 
                              dimensions: Dict[str, str], start_time: datetime, 
                              end_time: datetime, statistic: str) -> float:
        """
        Get a single metric value from CloudWatch.
        
        Args:
            namespace: CloudWatch namespace
            metric_name: Name of the metric
            dimensions: Metric dimensions
            start_time: Start time for the metric query
            end_time: End time for the metric query
            statistic: Statistic to retrieve (Sum, Average, etc.)
            
        Returns:
            float: Metric value or 0 if not found
        """
        try:
            response = self.cloudwatch.get_metric_statistics(
                Namespace=namespace,
                MetricName=metric_name,
                Dimensions=[
                    {'Name': key, 'Value': value} 
                    for key, value in dimensions.items()
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,  # 1 hour period
                Statistics=[statistic]
            )
            
            if response['Datapoints']:
                return response['Datapoints'][-1][statistic]  # Get the latest value
            else:
                return 0.0
                
        except Exception as e:
            logger.error(f"Failed to get CloudWatch metric {metric_name}: {str(e)}")
            return 0.0
    
    def run_performance_monitoring(self, environment: str = 'dev'):
        """
        Run a complete performance monitoring cycle.
        
        Args:
            environment: Environment name (dev, prod, etc.)
        """
        logger.info("Starting performance monitoring cycle")
        
        # Define function names based on environment
        lambda_functions = [
            f"gcse-interpret-lambda-{environment}",
            f"gcse-generate-lambda-{environment}",
            f"gcse-auth-lambda-{environment}",
            f"gcse-feedback-lambda-{environment}",
            f"gcse-session-lambda-{environment}",
            f"gcse-export-lambda-{environment}",
            f"gcse-topic-coverage-lambda-{environment}",
            f"gcse-refinement-lambda-{environment}"
        ]
        
        # Define table names based on environment
        dynamodb_tables = [
            f"{environment}-users",
            f"{environment}-sessions",
            f"{environment}-question-feedback",
            f"{environment}-quality-scores",
            f"{environment}-topic-coverage"
        ]
        
        # Define bucket names based on environment
        s3_buckets = [
            f"gcse-generator-{environment}-specifications",
            f"gcse-generator-{environment}-examples",
            f"gcse-generator-{environment}-question-bank",
            f"gcse-generator-{environment}-frontend"
        ]
        
        try:
            # Collect metrics
            lambda_metrics = self.collect_lambda_performance_metrics(lambda_functions)
            dynamodb_metrics = self.collect_dynamodb_performance_metrics(dynamodb_tables)
            s3_metrics = self.collect_s3_performance_metrics(s3_buckets)
            
            # Publish summary
            self.publish_performance_summary(lambda_metrics, dynamodb_metrics, s3_metrics)
            
            logger.info("Performance monitoring cycle completed successfully")
            
        except Exception as e:
            logger.error(f"Performance monitoring cycle failed: {str(e)}")
            raise


# Global instance
performance_monitor = PerformanceMonitor()

if __name__ == "__main__":
    # Run performance monitoring when script is executed directly
    import sys
    environment = sys.argv[1] if len(sys.argv) > 1 else 'dev'
    performance_monitor.run_performance_monitoring(environment)