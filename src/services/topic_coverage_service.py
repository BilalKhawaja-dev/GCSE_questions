"""
Topic Coverage Service for tracking user topic coverage statistics.

This service handles recording topic coverage data and providing analytics
for topic suggestions and coverage statistics.
"""

import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class TopicCoverageService:
    """Service for managing topic coverage tracking and analytics."""
    
    def __init__(self, region: str = 'eu-west-2', table_name: Optional[str] = None):
        """
        Initialize the TopicCoverageService.
        
        Args:
            region: AWS region for DynamoDB
            table_name: DynamoDB table name (optional, uses environment if not provided)
        """
        self.region = region
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        
        # Use provided table name or get from environment
        import os
        self.table_name = table_name or os.environ.get('TOPIC_COVERAGE_TABLE_NAME')
        
        if not self.table_name:
            raise ValueError("TopicCoverage table name must be provided or set in TOPIC_COVERAGE_TABLE_NAME environment variable")
        
        self.table = self.dynamodb.Table(self.table_name)
        
        logger.info(
            "TopicCoverageService initialized",
            extra={
                "region": region,
                "table_name": self.table_name
            }
        )
    
    def record_topic_coverage(
        self,
        user_id: str,
        topic: str,
        subtopic: str,
        question_count: int,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> bool:
        """
        Record topic coverage data for a user.
        
        Args:
            user_id: User identifier
            topic: Main topic (e.g., "fractions", "algebra")
            subtopic: Specific subtopic (e.g., "addition", "linear-equations")
            question_count: Number of questions generated for this topic
            session_id: Optional session identifier
            request_id: Optional request identifier for logging
            
        Returns:
            True if successfully recorded, False otherwise
        """
        try:
            timestamp = int(time.time())
            timestamp_str = datetime.utcnow().isoformat()
            
            # Create partition key and sort key
            pk = f"COVERAGE#{user_id}#{topic}"
            sk = f"TIMESTAMP#{timestamp}"
            
            item = {
                'pk': pk,
                'sk': sk,
                'user_id': user_id,
                'topic': topic,
                'subtopic': subtopic,
                'question_count': question_count,
                'timestamp': timestamp,
                'timestamp_str': timestamp_str
            }
            
            # Add optional fields
            if session_id:
                item['session_id'] = session_id
            if request_id:
                item['request_id'] = request_id
            
            # Store in DynamoDB
            self.table.put_item(Item=item)
            
            logger.info(
                "Topic coverage recorded successfully",
                extra={
                    "user_id": user_id,
                    "topic": topic,
                    "subtopic": subtopic,
                    "question_count": question_count,
                    "session_id": session_id,
                    "request_id": request_id,
                    "timestamp": timestamp_str
                }
            )
            
            return True
            
        except ClientError as e:
            logger.error(
                "Failed to record topic coverage",
                extra={
                    "user_id": user_id,
                    "topic": topic,
                    "subtopic": subtopic,
                    "error": str(e),
                    "error_code": e.response.get('Error', {}).get('Code'),
                    "request_id": request_id
                }
            )
            return False
        except Exception as e:
            logger.error(
                "Unexpected error recording topic coverage",
                extra={
                    "user_id": user_id,
                    "topic": topic,
                    "subtopic": subtopic,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "request_id": request_id
                }
            )
            return False
    
    def get_user_coverage_stats(
        self,
        user_id: str,
        days: int = 30,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get topic coverage statistics for a user over the specified time period.
        
        Args:
            user_id: User identifier
            days: Number of days to look back (default 30)
            request_id: Optional request identifier for logging
            
        Returns:
            Dictionary containing coverage statistics
        """
        try:
            # Calculate timestamp threshold (days ago)
            cutoff_time = datetime.utcnow() - timedelta(days=days)
            cutoff_timestamp = int(cutoff_time.timestamp())
            
            # Query user coverage data using GSI
            response = self.table.query(
                IndexName='UserCoverageIndex',
                KeyConditionExpression='user_id = :user_id AND sk >= :cutoff',
                ExpressionAttributeValues={
                    ':user_id': user_id,
                    ':cutoff': f"TIMESTAMP#{cutoff_timestamp}"
                }
            )
            
            items = response.get('Items', [])
            
            # Process coverage data
            coverage_stats = {}
            total_questions = 0
            
            for item in items:
                topic = item['topic']
                subtopic = item['subtopic']
                # Convert Decimal to int
                question_count = int(item['question_count']) if item.get('question_count') else 0
                timestamp_str = item.get('timestamp_str', '')
                
                if topic not in coverage_stats:
                    coverage_stats[topic] = {
                        'count': 0,
                        'subtopics': {},
                        'last_generated': timestamp_str,
                        'percentage': 0
                    }
                
                coverage_stats[topic]['count'] += question_count
                total_questions += question_count
                
                # Track subtopic coverage
                if subtopic not in coverage_stats[topic]['subtopics']:
                    coverage_stats[topic]['subtopics'][subtopic] = 0
                coverage_stats[topic]['subtopics'][subtopic] += question_count
                
                # Update last generated timestamp (keep most recent)
                if timestamp_str > coverage_stats[topic]['last_generated']:
                    coverage_stats[topic]['last_generated'] = timestamp_str
            
            # Calculate percentages
            for topic_data in coverage_stats.values():
                if total_questions > 0:
                    topic_data['percentage'] = round((topic_data['count'] / total_questions) * 100, 1)
            
            logger.info(
                "Retrieved user coverage statistics",
                extra={
                    "user_id": user_id,
                    "days": days,
                    "total_questions": total_questions,
                    "topics_covered": len(coverage_stats),
                    "request_id": request_id
                }
            )
            
            return {
                'coverage_stats': coverage_stats,
                'total_questions': total_questions,
                'coverage_percentage': round((len(coverage_stats) / 20) * 100, 1) if coverage_stats else 0,  # Assuming ~20 main topics
                'period_days': days
            }
            
        except ClientError as e:
            logger.error(
                "Failed to retrieve user coverage statistics",
                extra={
                    "user_id": user_id,
                    "days": days,
                    "error": str(e),
                    "error_code": e.response.get('Error', {}).get('Code'),
                    "request_id": request_id
                }
            )
            return {
                'coverage_stats': {},
                'total_questions': 0,
                'coverage_percentage': 0,
                'period_days': days,
                'error': 'Failed to retrieve coverage statistics'
            }
        except Exception as e:
            logger.error(
                "Unexpected error retrieving coverage statistics",
                extra={
                    "user_id": user_id,
                    "days": days,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "request_id": request_id
                }
            )
            return {
                'coverage_stats': {},
                'total_questions': 0,
                'coverage_percentage': 0,
                'period_days': days,
                'error': 'Unexpected error occurred'
            }
    
    def get_suggested_topics(
        self,
        user_id: str,
        days: int = 30,
        max_suggestions: int = 5,
        request_id: Optional[str] = None
    ) -> List[str]:
        """
        Get topic suggestions based on underrepresented topics in user's recent coverage.
        
        Args:
            user_id: User identifier
            days: Number of days to analyze (default 30)
            max_suggestions: Maximum number of suggestions to return
            request_id: Optional request identifier for logging
            
        Returns:
            List of suggested topic names
        """
        try:
            # Get current coverage statistics
            coverage_data = self.get_user_coverage_stats(user_id, days, request_id)
            coverage_stats = coverage_data.get('coverage_stats', {})
            
            # Define all available topics (this could be loaded from configuration)
            all_topics = [
                'fractions', 'decimals', 'percentages', 'ratio-proportion',
                'algebra', 'linear-equations', 'quadratic-equations', 'simultaneous-equations',
                'geometry', 'area-perimeter', 'pythagoras', 'trigonometry',
                'statistics', 'probability', 'graphs', 'sequences',
                'number-properties', 'indices-surds', 'functions', 'inequalities'
            ]
            
            # Calculate coverage scores (lower = more underrepresented)
            topic_scores = []
            for topic in all_topics:
                if topic in coverage_stats:
                    # Topic has been covered - score based on recency and frequency
                    count = coverage_stats[topic]['count']
                    last_generated = coverage_stats[topic]['last_generated']
                    
                    # Parse timestamp and calculate days since last generation
                    try:
                        last_dt = datetime.fromisoformat(last_generated.replace('Z', '+00:00'))
                        days_since = (datetime.utcnow() - last_dt.replace(tzinfo=None)).days
                    except:
                        days_since = days  # Assume it was at the start of the period
                    
                    # Score: higher days_since and lower count = higher priority
                    score = days_since + (1.0 / max(count, 1))
                else:
                    # Topic never covered - highest priority
                    score = days + 10  # Give uncovered topics extra priority
                
                topic_scores.append((topic, score))
            
            # Sort by score (highest first) and take top suggestions
            topic_scores.sort(key=lambda x: x[1], reverse=True)
            suggested_topics = [topic for topic, score in topic_scores[:max_suggestions]]
            
            logger.info(
                "Generated topic suggestions",
                extra={
                    "user_id": user_id,
                    "days": days,
                    "suggested_topics": suggested_topics,
                    "total_topics_analyzed": len(all_topics),
                    "covered_topics": len(coverage_stats),
                    "request_id": request_id
                }
            )
            
            return suggested_topics
            
        except Exception as e:
            logger.error(
                "Failed to generate topic suggestions",
                extra={
                    "user_id": user_id,
                    "days": days,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "request_id": request_id
                }
            )
            return []
    
    def get_topic_popularity_stats(
        self,
        days: int = 30,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get global topic popularity statistics across all users.
        
        Args:
            days: Number of days to analyze (default 30)
            request_id: Optional request identifier for logging
            
        Returns:
            Dictionary containing topic popularity statistics
        """
        try:
            # Calculate timestamp threshold
            cutoff_time = datetime.utcnow() - timedelta(days=days)
            cutoff_timestamp = int(cutoff_time.timestamp())
            
            # This would require scanning the table or using a different GSI
            # For now, return a placeholder implementation
            logger.info(
                "Topic popularity stats requested",
                extra={
                    "days": days,
                    "request_id": request_id,
                    "note": "Global popularity stats require table scan - placeholder implementation"
                }
            )
            
            return {
                'popularity_stats': {},
                'total_users': 0,
                'total_questions': 0,
                'period_days': days,
                'note': 'Global popularity tracking not yet implemented'
            }
            
        except Exception as e:
            logger.error(
                "Failed to retrieve topic popularity statistics",
                extra={
                    "days": days,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "request_id": request_id
                }
            )
            return {
                'popularity_stats': {},
                'total_users': 0,
                'total_questions': 0,
                'period_days': days,
                'error': 'Failed to retrieve popularity statistics'
            }