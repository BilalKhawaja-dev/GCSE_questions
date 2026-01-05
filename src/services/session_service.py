"""
Session service for managing user sessions and question history.

This service handles storing generated questions in DynamoDB Sessions table
with TTL for automatic cleanup and provides session retrieval functionality.
"""

import json
import logging
import os
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class SessionService:
    """Service for managing user sessions and question history."""
    
    def __init__(self, region: str = 'eu-west-2', table=None):
        """
        Initialize SessionService.
        
        Args:
            region: AWS region for DynamoDB operations
            table: Optional DynamoDB table resource for testing
        """
        self.region = region
        
        if table:
            # Use provided table (for testing)
            self.sessions_table = table
            self.sessions_table_name = table.name
        else:
            # Use connection pool for better performance
            try:
                from src.utils.lambda_optimizer import connection_pool
                self.dynamodb = connection_pool.get_dynamodb_resource(region)
                logger.debug("Using connection pool for DynamoDB")
            except ImportError:
                # Fallback to direct connection if optimizer not available
                self.dynamodb = boto3.resource('dynamodb', region_name=region)
                logger.debug("Using direct DynamoDB connection")
            
            self.sessions_table_name = os.environ.get('SESSIONS_TABLE_NAME')
            
            if not self.sessions_table_name:
                raise ValueError("SESSIONS_TABLE_NAME environment variable is required")
            
            self.sessions_table = self.dynamodb.Table(self.sessions_table_name)
        
        # TTL configuration (7 days = 604800 seconds)
        self.ttl_seconds = 604800
        
    def create_session(
        self,
        user_id: str,
        query: str,
        generated_questions: List[Dict[str, Any]],
        metadata: Dict[str, Any],
        request_id: str
    ) -> str:
        """
        Create a new session with generated questions.
        
        Args:
            user_id: User identifier (e.g., "USER#username")
            query: Original user query
            generated_questions: List of generated question objects
            metadata: Session metadata (topic, tier, question_count, etc.)
            request_id: Request ID for logging
            
        Returns:
            session_id: Unique session identifier
            
        Raises:
            Exception: If session creation fails
        """
        session_id = str(uuid.uuid4())
        timestamp = int(time.time())
        ttl = timestamp + self.ttl_seconds
        
        # Create session item (convert floats to Decimal for DynamoDB)
        processed_metadata = {}
        for key, value in metadata.items():
            if isinstance(value, float):
                processed_metadata[key] = Decimal(str(value))
            else:
                processed_metadata[key] = value
        
        session_item = {
            'pk': f'SESSION#{session_id}',
            'sk': f'TIMESTAMP#{timestamp}',
            'session_id': session_id,
            'user_id': user_id,
            'query': query,
            'generated_questions': generated_questions,
            'timestamp': timestamp,
            'ttl': ttl,
            'metadata': {
                **processed_metadata,
                'created_at': datetime.utcnow().isoformat(),
                'request_id': request_id
            }
        }
        
        try:
            self.sessions_table.put_item(Item=session_item)
            
            logger.info(
                "Session created successfully",
                extra={
                    "session_id": session_id,
                    "user_id": user_id,
                    "question_count": len(generated_questions),
                    "ttl_expires_at": datetime.fromtimestamp(ttl).isoformat(),
                    "request_id": request_id
                }
            )
            
            return session_id
            
        except ClientError as e:
            logger.error(
                "Failed to create session",
                extra={
                    "session_id": session_id,
                    "user_id": user_id,
                    "error": str(e),
                    "request_id": request_id
                }
            )
            raise Exception(f"Failed to create session: {str(e)}")
    
    def get_user_sessions(
        self,
        user_id: str,
        limit: int = 50,
        last_evaluated_key: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Retrieve user's session history with pagination.
        
        Args:
            user_id: User identifier (e.g., "USER#username")
            limit: Maximum number of sessions to return
            last_evaluated_key: Pagination key from previous request
            
        Returns:
            Dictionary containing sessions list and pagination info
            
        Raises:
            Exception: If session retrieval fails
        """
        try:
            query_params = {
                'IndexName': 'UserSessionsIndex',
                'KeyConditionExpression': 'user_id = :user_id',
                'ExpressionAttributeValues': {
                    ':user_id': user_id
                },
                'ScanIndexForward': False,  # Sort by timestamp descending (newest first)
                'Limit': limit
            }
            
            if last_evaluated_key:
                query_params['ExclusiveStartKey'] = last_evaluated_key
            
            response = self.sessions_table.query(**query_params)
            
            # Transform sessions for response
            sessions = []
            for item in response.get('Items', []):
                session = {
                    'session_id': item['session_id'],
                    'query': item['query'],
                    'timestamp': item['timestamp'],
                    'created_at': item['metadata'].get('created_at'),
                    'question_count': len(item.get('generated_questions', [])),
                    'metadata': {
                        'topic': item['metadata'].get('topic'),
                        'tier': item['metadata'].get('tier'),
                        'total_marks': item['metadata'].get('total_marks'),
                        'generation_time': item['metadata'].get('generation_time')
                    }
                }
                sessions.append(session)
            
            result = {
                'sessions': sessions,
                'count': len(sessions),
                'has_more': 'LastEvaluatedKey' in response
            }
            
            if 'LastEvaluatedKey' in response:
                result['last_evaluated_key'] = response['LastEvaluatedKey']
            
            logger.info(
                "Retrieved user sessions",
                extra={
                    "user_id": user_id,
                    "session_count": len(sessions),
                    "has_more": result['has_more']
                }
            )
            
            return result
            
        except ClientError as e:
            logger.error(
                "Failed to retrieve user sessions",
                extra={
                    "user_id": user_id,
                    "error": str(e)
                }
            )
            raise Exception(f"Failed to retrieve sessions: {str(e)}")
    
    def get_session_details(self, session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve detailed session information including all questions.
        
        Args:
            session_id: Session identifier
            user_id: User identifier for security validation
            
        Returns:
            Complete session data or None if not found
            
        Raises:
            Exception: If session retrieval fails
        """
        try:
            # Query by session PK to get the specific session
            response = self.sessions_table.query(
                KeyConditionExpression='pk = :pk',
                ExpressionAttributeValues={
                    ':pk': f'SESSION#{session_id}'
                },
                Limit=1
            )
            
            items = response.get('Items', [])
            if not items:
                return None
            
            session_item = items[0]
            
            # Verify user owns this session
            if session_item.get('user_id') != user_id:
                logger.warning(
                    "Unauthorized session access attempt",
                    extra={
                        "session_id": session_id,
                        "requested_by": user_id,
                        "actual_owner": session_item.get('user_id')
                    }
                )
                return None
            
            # Return complete session data
            session_details = {
                'session_id': session_item['session_id'],
                'user_id': session_item['user_id'],
                'query': session_item['query'],
                'generated_questions': session_item.get('generated_questions', []),
                'timestamp': session_item['timestamp'],
                'created_at': session_item['metadata'].get('created_at'),
                'metadata': session_item['metadata']
            }
            
            logger.info(
                "Retrieved session details",
                extra={
                    "session_id": session_id,
                    "user_id": user_id,
                    "question_count": len(session_details['generated_questions'])
                }
            )
            
            return session_details
            
        except ClientError as e:
            logger.error(
                "Failed to retrieve session details",
                extra={
                    "session_id": session_id,
                    "user_id": user_id,
                    "error": str(e)
                }
            )
            raise Exception(f"Failed to retrieve session details: {str(e)}")
    
    def get_session_statistics(self, user_id: str) -> Dict[str, Any]:
        """
        Get session statistics for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary containing session statistics
        """
        try:
            # Get all user sessions (without pagination for stats)
            response = self.sessions_table.query(
                IndexName='UserSessionsIndex',
                KeyConditionExpression='user_id = :user_id',
                ExpressionAttributeValues={
                    ':user_id': user_id
                },
                ProjectionExpression='session_id, #ts, metadata',
                ExpressionAttributeNames={
                    '#ts': 'timestamp'
                }
            )
            
            sessions = response.get('Items', [])
            
            # Calculate statistics
            total_sessions = len(sessions)
            total_questions = sum(
                session.get('metadata', {}).get('question_count', 0) 
                for session in sessions
            )
            
            # Get recent activity (last 7 days)
            week_ago = int(time.time()) - (7 * 24 * 60 * 60)
            recent_sessions = [
                s for s in sessions 
                if s.get('timestamp', 0) > week_ago
            ]
            
            # Calculate most common topics
            topic_counts = {}
            for session in sessions:
                topic = session.get('metadata', {}).get('topic')
                if topic:
                    topic_counts[topic] = topic_counts.get(topic, 0) + 1
            
            # Sort by count and get top 5
            most_common_topics = sorted(
                [{'topic': t, 'count': c} for t, c in topic_counts.items()],
                key=lambda x: x['count'],
                reverse=True
            )[:5]
            
            stats = {
                'total_sessions': total_sessions,
                'total_questions_generated': total_questions,
                'recent_sessions_7_days': len(recent_sessions),
                'average_questions_per_session': (
                    total_questions / total_sessions if total_sessions > 0 else 0
                ),
                'most_common_topics': most_common_topics
            }
            
            logger.info(
                "Calculated session statistics",
                extra={
                    "user_id": user_id,
                    "stats": stats
                }
            )
            
            return stats
            
        except ClientError as e:
            logger.error(
                "Failed to calculate session statistics",
                extra={
                    "user_id": user_id,
                    "error": str(e)
                }
            )
            return {
                'total_sessions': 0,
                'total_questions_generated': 0,
                'recent_sessions_7_days': 0,
                'average_questions_per_session': 0,
                'most_common_topics': []
            }
    
    def get_session(self, session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session data for PDF export.
        
        Args:
            session_id: Session identifier
            user_id: User identifier for security validation
            
        Returns:
            Session data or None if not found
        """
        return self.get_session_details(session_id, user_id)


# Singleton instance for use across the application
# Only create if environment variables are available (not during testing)
session_service = None
try:
    if os.environ.get('SESSIONS_TABLE_NAME'):
        session_service = SessionService()
except Exception:
    # Will be None during testing, tests should mock or provide their own instance
    pass