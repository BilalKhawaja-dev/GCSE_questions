"""
CloudWatch Custom Metrics Service for GCSE Question Generator V2

This service provides methods to publish custom metrics to CloudWatch
for performance monitoring and business intelligence.
"""

import boto3
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from src.utils.logging_service import ComprehensiveLoggingService

# Initialize logger
logging_service = ComprehensiveLoggingService("metrics_service")
logger = logging_service.logger

class MetricsService:
    """Service for publishing custom CloudWatch metrics."""
    
    def __init__(self):
        """Initialize the metrics service with CloudWatch client."""
        self.cloudwatch = boto3.client('cloudwatch', region_name='eu-west-2')
        self.namespace_prefix = "GCSE"
    
    def put_metric(self, namespace: str, metric_name: str, value: float, 
                   unit: str = 'Count', dimensions: Optional[Dict[str, str]] = None,
                   timestamp: Optional[datetime] = None) -> bool:
        """
        Put a single metric to CloudWatch.
        
        Args:
            namespace: CloudWatch namespace (will be prefixed with GCSE/)
            metric_name: Name of the metric
            value: Metric value
            unit: CloudWatch unit (Count, Seconds, Percent, etc.)
            dimensions: Optional dimensions for the metric
            timestamp: Optional timestamp (defaults to now)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            full_namespace = f"{self.namespace_prefix}/{namespace}"
            
            metric_data = {
                'MetricName': metric_name,
                'Value': value,
                'Unit': unit,
                'Timestamp': timestamp or datetime.utcnow()
            }
            
            if dimensions:
                metric_data['Dimensions'] = [
                    {'Name': key, 'Value': value} 
                    for key, value in dimensions.items()
                ]
            
            self.cloudwatch.put_metric_data(
                Namespace=full_namespace,
                MetricData=[metric_data]
            )
            
            logger.debug(f"Published metric {metric_name} = {value} to {full_namespace}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish metric {metric_name}: {str(e)}")
            return False
    
    def put_multiple_metrics(self, namespace: str, metrics: List[Dict[str, Any]]) -> bool:
        """
        Put multiple metrics to CloudWatch in a single call.
        
        Args:
            namespace: CloudWatch namespace (will be prefixed with GCSE/)
            metrics: List of metric dictionaries with keys: name, value, unit, dimensions
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            full_namespace = f"{self.namespace_prefix}/{namespace}"
            
            metric_data = []
            for metric in metrics:
                data = {
                    'MetricName': metric['name'],
                    'Value': metric['value'],
                    'Unit': metric.get('unit', 'Count'),
                    'Timestamp': metric.get('timestamp', datetime.utcnow())
                }
                
                if 'dimensions' in metric and metric['dimensions']:
                    data['Dimensions'] = [
                        {'Name': key, 'Value': value} 
                        for key, value in metric['dimensions'].items()
                    ]
                
                metric_data.append(data)
            
            # CloudWatch allows max 20 metrics per call
            for i in range(0, len(metric_data), 20):
                batch = metric_data[i:i+20]
                self.cloudwatch.put_metric_data(
                    Namespace=full_namespace,
                    MetricData=batch
                )
            
            logger.debug(f"Published {len(metrics)} metrics to {full_namespace}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish multiple metrics: {str(e)}")
            return False
    
    # Question Generation Metrics
    def record_question_generation_success(self, function_name: str, question_count: int, 
                                         generation_time: float, quality_score: float = None):
        """Record successful question generation metrics."""
        metrics = [
            {
                'name': 'SuccessRate',
                'value': 100.0,
                'unit': 'Percent',
                'dimensions': {'Function': function_name}
            },
            {
                'name': 'QuestionsGenerated',
                'value': question_count,
                'unit': 'Count',
                'dimensions': {'Function': function_name}
            },
            {
                'name': 'GenerationTime',
                'value': generation_time,
                'unit': 'Seconds',
                'dimensions': {'Function': function_name}
            }
        ]
        
        if quality_score is not None:
            metrics.append({
                'name': 'AverageQuality',
                'value': quality_score,
                'unit': 'None',
                'dimensions': {'Function': function_name}
            })
        
        self.put_multiple_metrics('QuestionGeneration', metrics)
    
    def record_question_generation_failure(self, function_name: str, error_type: str):
        """Record failed question generation metrics."""
        metrics = [
            {
                'name': 'SuccessRate',
                'value': 0.0,
                'unit': 'Percent',
                'dimensions': {'Function': function_name}
            },
            {
                'name': 'ErrorCount',
                'value': 1,
                'unit': 'Count',
                'dimensions': {'Function': function_name, 'ErrorType': error_type}
            }
        ]
        
        self.put_multiple_metrics('QuestionGeneration', metrics)
    
    # Query Interpretation Metrics
    def record_query_interpretation_success(self, queries_parsed: int, processing_time: float):
        """Record successful query interpretation metrics."""
        metrics = [
            {
                'name': 'SuccessRate',
                'value': 100.0,
                'unit': 'Percent',
                'dimensions': {'Function': 'InterpretLambda'}
            },
            {
                'name': 'QueriesParsed',
                'value': queries_parsed,
                'unit': 'Count',
                'dimensions': {'Function': 'InterpretLambda'}
            },
            {
                'name': 'ProcessingTime',
                'value': processing_time,
                'unit': 'Seconds',
                'dimensions': {'Function': 'InterpretLambda'}
            }
        ]
        
        self.put_multiple_metrics('QuestionGeneration', metrics)
    
    # Bedrock Usage Metrics
    def record_bedrock_usage(self, model: str, tokens_used: int, request_count: int, 
                           estimated_cost: float):
        """Record Bedrock API usage metrics."""
        metrics = [
            {
                'name': 'TokensUsed',
                'value': tokens_used,
                'unit': 'Count',
                'dimensions': {'Model': model}
            },
            {
                'name': 'RequestCount',
                'value': request_count,
                'unit': 'Count',
                'dimensions': {'Model': model}
            },
            {
                'name': 'EstimatedCost',
                'value': estimated_cost,
                'unit': 'None',
                'dimensions': {'Model': model}
            }
        ]
        
        self.put_multiple_metrics('Bedrock', metrics)
    
    # User Activity Metrics
    def record_user_activity(self, active_users: int, questions_generated: int, 
                           sessions_created: int):
        """Record daily user activity metrics."""
        metrics = [
            {
                'name': 'ActiveUsers',
                'value': active_users,
                'unit': 'Count',
                'dimensions': {'Period': 'Daily'}
            },
            {
                'name': 'QuestionsGenerated',
                'value': questions_generated,
                'unit': 'Count',
                'dimensions': {'Period': 'Daily'}
            },
            {
                'name': 'SessionsCreated',
                'value': sessions_created,
                'unit': 'Count',
                'dimensions': {'Period': 'Daily'}
            }
        ]
        
        self.put_multiple_metrics('UserActivity', metrics)
    
    # Quality Metrics
    def record_quality_metrics(self, component: str, average_rating: float, 
                             feedback_count: int):
        """Record quality metrics from user feedback."""
        metrics = [
            {
                'name': 'AverageRating',
                'value': average_rating,
                'unit': 'None',
                'dimensions': {'Component': component}
            },
            {
                'name': 'FeedbackCount',
                'value': feedback_count,
                'unit': 'Count',
                'dimensions': {'Component': component}
            }
        ]
        
        self.put_multiple_metrics('Quality', metrics)
    
    # Performance Metrics
    def record_performance_metrics(self, endpoint: str, response_time: float, 
                                 success: bool = True):
        """Record API endpoint performance metrics."""
        metrics = [
            {
                'name': 'ResponseTime',
                'value': response_time,
                'unit': 'Seconds',
                'dimensions': {'Endpoint': endpoint}
            }
        ]
        
        if success:
            metrics.append({
                'name': 'SuccessCount',
                'value': 1,
                'unit': 'Count',
                'dimensions': {'Endpoint': endpoint}
            })
        else:
            metrics.append({
                'name': 'ErrorCount',
                'value': 1,
                'unit': 'Count',
                'dimensions': {'Endpoint': endpoint}
            })
        
        self.put_multiple_metrics('Performance', metrics)
    
    # Cost Efficiency Metrics
    def record_cost_efficiency(self, cost_per_question: float, cost_per_user: float, 
                             cost_per_session: float):
        """Record cost efficiency metrics."""
        metrics = [
            {
                'name': 'CostPerQuestion',
                'value': cost_per_question,
                'unit': 'None',
                'dimensions': {'Service': 'Total'}
            },
            {
                'name': 'CostPerUser',
                'value': cost_per_user,
                'unit': 'None',
                'dimensions': {'Service': 'Total'}
            },
            {
                'name': 'CostPerSession',
                'value': cost_per_session,
                'unit': 'None',
                'dimensions': {'Service': 'Total'}
            }
        ]
        
        # Calculate inverse metrics (value per dollar)
        if cost_per_question > 0:
            metrics.append({
                'name': 'QuestionsPerDollar',
                'value': 1.0 / cost_per_question,
                'unit': 'Count'
            })
        
        if cost_per_user > 0:
            metrics.append({
                'name': 'UsersPerDollar',
                'value': 1.0 / cost_per_user,
                'unit': 'Count'
            })
        
        if cost_per_session > 0:
            metrics.append({
                'name': 'SessionsPerDollar',
                'value': 1.0 / cost_per_session,
                'unit': 'Count'
            })
        
        self.put_multiple_metrics('CostEfficiency', metrics)
        self.put_multiple_metrics('Usage', metrics[-3:])  # Put inverse metrics in Usage namespace


# Global instance
metrics_service = MetricsService()