"""
Verification Metrics Service for Question Bank Verification System

This service provides methods to publish verification-specific metrics to CloudWatch
for monitoring question bank health, verification quality, and user experience.
"""

import boto3
from datetime import datetime
from typing import Dict, List, Optional, Any
from src.utils.logging_service import ComprehensiveLoggingService

# Initialize logger
logging_service = ComprehensiveLoggingService("verification_metrics_service")
logger = logging_service.logger


class VerificationMetricsService:
    """Service for publishing verification-specific CloudWatch metrics."""
    
    def __init__(self):
        """Initialize the verification metrics service with CloudWatch client."""
        self.cloudwatch = boto3.client('cloudwatch', region_name='eu-west-2')
        self.namespace = "GCSE/QuestionVerification"
    
    def put_metric(self, metric_name: str, value: float, 
                   unit: str = 'Count', dimensions: Optional[Dict[str, str]] = None,
                   timestamp: Optional[datetime] = None) -> bool:
        """
        Put a single metric to CloudWatch.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            unit: CloudWatch unit (Count, Seconds, Percent, Milliseconds, etc.)
            dimensions: Optional dimensions for the metric
            timestamp: Optional timestamp (defaults to now)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
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
                Namespace=self.namespace,
                MetricData=[metric_data]
            )
            
            logger.debug(f"Published metric {metric_name} = {value} to {self.namespace}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish metric {metric_name}: {str(e)}")
            return False
    
    def put_multiple_metrics(self, metrics: List[Dict[str, Any]]) -> bool:
        """
        Put multiple metrics to CloudWatch in a single call.
        
        Args:
            metrics: List of metric dictionaries with keys: name, value, unit, dimensions
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
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
                    Namespace=self.namespace,
                    MetricData=batch
                )
            
            logger.debug(f"Published {len(metrics)} metrics to {self.namespace}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish multiple metrics: {str(e)}")
            return False
    
    # Verification Layer Metrics
    def record_verification_layer_result(self, layer_name: str, passed: bool, 
                                        latency_ms: float, confidence: Optional[float] = None):
        """
        Record verification layer execution result.
        
        Args:
            layer_name: Name of verification layer (Deterministic, SymPy, LLM, KB, Dedupe)
            passed: Whether the verification passed
            latency_ms: Execution time in milliseconds
            confidence: Optional confidence score (0-1)
        """
        metrics = [
            {
                'name': 'VerificationPassRate',
                'value': 100.0 if passed else 0.0,
                'unit': 'Percent',
                'dimensions': {'Layer': layer_name}
            },
            {
                'name': 'VerificationLatency',
                'value': latency_ms,
                'unit': 'Milliseconds',
                'dimensions': {'Layer': layer_name}
            },
            {
                'name': 'VerificationCount',
                'value': 1,
                'unit': 'Count',
                'dimensions': {'Layer': layer_name, 'Result': 'Pass' if passed else 'Fail'}
            }
        ]
        
        if confidence is not None:
            metrics.append({
                'name': 'VerificationConfidence',
                'value': confidence,
                'unit': 'None',
                'dimensions': {'Layer': layer_name}
            })
        
        self.put_multiple_metrics(metrics)
    
    def record_verification_failure_reason(self, layer_name: str, failure_reason: str):
        """
        Record specific failure reason for a verification layer.
        
        Args:
            layer_name: Name of verification layer
            failure_reason: Specific reason for failure
        """
        self.put_metric(
            metric_name='VerificationFailureCount',
            value=1,
            unit='Count',
            dimensions={'Layer': layer_name, 'Reason': failure_reason}
        )
    
    # Question Bank Inventory Metrics
    def record_question_bank_inventory(self, topic: str, grade: str, paper_type: str, 
                                      verified_count: int, target_count: int = 50):
        """
        Record question bank inventory levels.
        
        Args:
            topic: Question topic
            grade: Grade level (foundation/higher)
            paper_type: Paper type (P1/P2/P3)
            verified_count: Current count of verified questions
            target_count: Target count for this combination
        """
        topic_grade_paper = f"{topic}_{grade}_{paper_type}"
        
        metrics = [
            {
                'name': 'VerifiedQuestionCount',
                'value': verified_count,
                'unit': 'Count',
                'dimensions': {'TopicGradePaper': topic_grade_paper}
            },
            {
                'name': 'InventoryLevel',
                'value': (verified_count / target_count) * 100 if target_count > 0 else 0,
                'unit': 'Percent',
                'dimensions': {'TopicGradePaper': topic_grade_paper}
            }
        ]
        
        # Add low inventory alert metric
        if verified_count < 20:
            metrics.append({
                'name': 'LowInventoryAlert',
                'value': 1,
                'unit': 'Count',
                'dimensions': {'TopicGradePaper': topic_grade_paper}
            })
        
        self.put_multiple_metrics(metrics)
    
    # Batch Generation Metrics
    def record_batch_generation_result(self, topic: str, grade: str, paper_type: str,
                                      questions_generated: int, questions_passed: int,
                                      batch_duration_seconds: float):
        """
        Record batch generation and verification results.
        
        Args:
            topic: Question topic
            grade: Grade level
            paper_type: Paper type
            questions_generated: Total questions generated in batch
            questions_passed: Questions that passed verification
            batch_duration_seconds: Total batch processing time
        """
        topic_grade_paper = f"{topic}_{grade}_{paper_type}"
        pass_rate = (questions_passed / questions_generated * 100) if questions_generated > 0 else 0
        
        metrics = [
            {
                'name': 'BatchGenerationCount',
                'value': questions_generated,
                'unit': 'Count',
                'dimensions': {'TopicGradePaper': topic_grade_paper}
            },
            {
                'name': 'BatchPassRate',
                'value': pass_rate,
                'unit': 'Percent',
                'dimensions': {'TopicGradePaper': topic_grade_paper}
            },
            {
                'name': 'BatchDuration',
                'value': batch_duration_seconds,
                'unit': 'Seconds',
                'dimensions': {'TopicGradePaper': topic_grade_paper}
            },
            {
                'name': 'QuestionsPassedVerification',
                'value': questions_passed,
                'unit': 'Count',
                'dimensions': {'TopicGradePaper': topic_grade_paper}
            }
        ]
        
        self.put_multiple_metrics(metrics)
    
    # Retrieval Performance Metrics
    def record_retrieval_performance(self, latency_ms: float, questions_returned: int,
                                    topic: Optional[str] = None, grade: Optional[str] = None):
        """
        Record question retrieval performance.
        
        Args:
            latency_ms: Retrieval latency in milliseconds
            questions_returned: Number of questions returned
            topic: Optional topic filter
            grade: Optional grade filter
        """
        dimensions = {}
        if topic:
            dimensions['Topic'] = topic
        if grade:
            dimensions['Grade'] = grade
        
        metrics = [
            {
                'name': 'RetrievalLatency',
                'value': latency_ms,
                'unit': 'Milliseconds',
                'dimensions': dimensions if dimensions else None
            },
            {
                'name': 'QuestionsServed',
                'value': questions_returned,
                'unit': 'Count',
                'dimensions': dimensions if dimensions else None
            }
        ]
        
        # Add high latency alert
        if latency_ms > 200:
            metrics.append({
                'name': 'HighLatencyAlert',
                'value': 1,
                'unit': 'Count',
                'dimensions': dimensions if dimensions else None
            })
        
        self.put_multiple_metrics(metrics)
    
    # User Feedback Metrics
    def record_user_feedback(self, question_id: str, helpful: bool, 
                           difficulty_rating: Optional[int] = None,
                           issue_reported: bool = False):
        """
        Record user feedback on questions.
        
        Args:
            question_id: Question identifier
            helpful: Whether user found question helpful
            difficulty_rating: Optional difficulty rating (1-10)
            issue_reported: Whether user reported an issue
        """
        metrics = [
            {
                'name': 'UserFeedbackCount',
                'value': 1,
                'unit': 'Count',
                'dimensions': {'Helpful': 'Yes' if helpful else 'No'}
            }
        ]
        
        if difficulty_rating is not None:
            metrics.append({
                'name': 'UserDifficultyRating',
                'value': difficulty_rating,
                'unit': 'None'
            })
        
        if issue_reported:
            metrics.append({
                'name': 'IssueReportCount',
                'value': 1,
                'unit': 'Count'
            })
        
        self.put_multiple_metrics(metrics)
    
    def record_false_positive_rate(self, total_verified: int, issues_reported: int):
        """
        Record false positive rate (good questions incorrectly rejected).
        
        Args:
            total_verified: Total verified questions
            issues_reported: Number of issues reported by users
        """
        false_positive_rate = (issues_reported / total_verified * 100) if total_verified > 0 else 0
        
        self.put_metric(
            metric_name='FalsePositiveRate',
            value=false_positive_rate,
            unit='Percent'
        )
    
    # Cost Tracking Metrics
    def record_verification_cost(self, bedrock_calls: int, estimated_cost_usd: float):
        """
        Record verification cost metrics.
        
        Args:
            bedrock_calls: Number of Bedrock API calls
            estimated_cost_usd: Estimated cost in USD
        """
        metrics = [
            {
                'name': 'BedrockCallCount',
                'value': bedrock_calls,
                'unit': 'Count'
            },
            {
                'name': 'VerificationCost',
                'value': estimated_cost_usd,
                'unit': 'None'
            }
        ]
        
        if bedrock_calls > 0:
            metrics.append({
                'name': 'CostPerVerification',
                'value': estimated_cost_usd / bedrock_calls,
                'unit': 'None'
            })
        
        self.put_multiple_metrics(metrics)
    
    # Replenishment Metrics
    def record_replenishment_execution(self, topics_replenished: int, 
                                      total_questions_generated: int,
                                      execution_duration_seconds: float):
        """
        Record replenishment cron job execution.
        
        Args:
            topics_replenished: Number of topics that needed replenishment
            total_questions_generated: Total questions generated
            execution_duration_seconds: Total execution time
        """
        metrics = [
            {
                'name': 'ReplenishmentExecutionCount',
                'value': 1,
                'unit': 'Count'
            },
            {
                'name': 'TopicsReplenished',
                'value': topics_replenished,
                'unit': 'Count'
            },
            {
                'name': 'QuestionsGeneratedInReplenishment',
                'value': total_questions_generated,
                'unit': 'Count'
            },
            {
                'name': 'ReplenishmentDuration',
                'value': execution_duration_seconds,
                'unit': 'Seconds'
            }
        ]
        
        self.put_multiple_metrics(metrics)
    
    # Overall System Health Metrics
    def record_system_health(self, total_verified_questions: int, 
                           average_pass_rate: float,
                           average_retrieval_latency_ms: float):
        """
        Record overall system health metrics.
        
        Args:
            total_verified_questions: Total questions in verified bank
            average_pass_rate: Average verification pass rate across all layers
            average_retrieval_latency_ms: Average retrieval latency
        """
        metrics = [
            {
                'name': 'TotalVerifiedQuestions',
                'value': total_verified_questions,
                'unit': 'Count'
            },
            {
                'name': 'AveragePassRate',
                'value': average_pass_rate,
                'unit': 'Percent'
            },
            {
                'name': 'AverageRetrievalLatency',
                'value': average_retrieval_latency_ms,
                'unit': 'Milliseconds'
            }
        ]
        
        self.put_multiple_metrics(metrics)


# Global instance
verification_metrics_service = VerificationMetricsService()
