"""
FeedbackLambda - Collect user feedback on generated questions

This Lambda function handles user feedback collection for the AI learning mechanism.
It stores helpful/not helpful ratings and difficulty ratings (1-10) in DynamoDB.
"""

import json
import logging
import os
import time
from typing import Dict, Any
import boto3
from botocore.exceptions import ClientError
from src.utils.security import get_cors_response_headers
from src.services.verification_metrics_service import verification_metrics_service

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')

# Environment variables
QUESTION_FEEDBACK_TABLE = os.environ.get('QUESTION_FEEDBACK_TABLE', 'gcse-generator-v2-question-feedback-dev')
QUALITY_SCORES_TABLE = os.environ.get('QUALITY_SCORES_TABLE', 'gcse-generator-v2-quality-scores-dev')

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle feedback collection requests
    
    Expected event structure (from API Gateway with authorizer):
    {
        "body": {
            "question_id": str,
            "helpful": bool,
            "difficulty_rating": int (1-10, optional),
            "comments": str (optional)
        },
        "requestContext": {
            "authorizer": {
                "user_id": str,
                "session_token": str
            }
        }
    }
    """
    try:
        logger.info(f"Processing feedback request: {json.dumps(event, default=str)}")
        
        # Get user info from authorizer context
        authorizer_context = event.get('requestContext', {}).get('authorizer', {})
        user_id = authorizer_context.get('user_id')
        session_token = authorizer_context.get('session_token')
        
        if not user_id:
            return create_error_response(401, "User not authenticated")
        
        # Parse request body
        body = event.get('body', {})
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except json.JSONDecodeError:
                return create_error_response(400, "Invalid JSON in request body")
        
        # Validate required fields
        if 'question_id' not in body:
            return create_error_response(400, "Missing required field: question_id")
        if 'helpful' not in body:
            return create_error_response(400, "Missing required field: helpful")
        
        question_id = body['question_id']
        helpful = body['helpful']
        difficulty_rating = body.get('difficulty_rating', 5)  # Default to 5 if not provided
        comments = body.get('comments', '')
        issue_reported = body.get('issue_reported', False)
        issue_type = body.get('issue_type', '')
        issue_description = body.get('issue_description', '')
        
        # Validate difficulty rating range if provided
        if not isinstance(difficulty_rating, int) or not (1 <= difficulty_rating <= 10):
            return create_error_response(400, "Difficulty rating must be an integer between 1 and 10")
        
        # Store feedback in DynamoDB
        timestamp = int(time.time())
        feedback_stored = store_feedback(
            question_id=question_id,
            user_id=user_id,
            helpful=helpful,
            difficulty_rating=difficulty_rating,
            comments=comments,
            timestamp=timestamp,
            session_token=session_token,
            issue_reported=issue_reported,
            issue_type=issue_type,
            issue_description=issue_description
        )
        
        if not feedback_stored:
            return create_error_response(500, "Failed to store feedback")
        
        # Update quality scores
        updated_quality_score = update_quality_scores(question_id)
        
        # Record user feedback metrics
        verification_metrics_service.record_user_feedback(
            question_id=question_id,
            helpful=helpful,
            difficulty_rating=difficulty_rating if difficulty_rating != 5 else None,
            issue_reported=issue_reported
        )
        
        logger.info(f"Successfully processed feedback for question {question_id}")
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                **get_cors_response_headers(methods='POST,OPTIONS')
            },
            'body': json.dumps({
                'success': True,
                'message': 'Feedback stored successfully',
                'updated_quality_score': updated_quality_score
            })
        }
        
    except Exception as e:
        logger.error(f"Error processing feedback: {str(e)}")
        return create_error_response(500, f"Internal server error: {str(e)}")

def store_feedback(question_id: str, user_id: str, helpful: bool, difficulty_rating: int, 
                  comments: str, timestamp: int, session_token: str, issue_reported: bool = False,
                  issue_type: str = '', issue_description: str = '') -> bool:
    """Store user feedback in DynamoDB QuestionFeedback table"""
    try:
        feedback_table = dynamodb.Table(QUESTION_FEEDBACK_TABLE)
        
        # Create composite keys
        pk = f"FEEDBACK#{question_id}"
        sk = f"USER#{user_id}#{timestamp}"
        
        # Build feedback item
        item = {
            'pk': pk,
            'sk': sk,
            'question_id': question_id,
            'user_id': user_id,
            'helpful': helpful,
            'difficulty_rating': difficulty_rating,
            'comments': comments,
            'timestamp': timestamp,
            'session_token': session_token,
            'issue_reported': issue_reported
        }
        
        # Add issue details if reported
        if issue_reported:
            item['issue_type'] = issue_type
            item['issue_description'] = issue_description
            item['issue_status'] = 'pending_review'
        
        # Store feedback item
        feedback_table.put_item(Item=item)
        
        logger.info(f"Stored feedback for question {question_id} from user {user_id}, issue_reported={issue_reported}")
        return True
        
    except ClientError as e:
        logger.error(f"DynamoDB error storing feedback: {e.response['Error']['Message']}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error storing feedback: {str(e)}")
        return False

def update_quality_scores(question_id: str) -> float:
    """Update quality scores based on aggregated feedback"""
    try:
        feedback_table = dynamodb.Table(QUESTION_FEEDBACK_TABLE)
        quality_table = dynamodb.Table(QUALITY_SCORES_TABLE)
        
        # Query all feedback for this question
        pk = f"FEEDBACK#{question_id}"
        response = feedback_table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('pk').eq(pk)
        )
        
        feedback_items = response.get('Items', [])
        if not feedback_items:
            logger.warning(f"No feedback found for question {question_id}")
            return 0.0
        
        # Calculate quality metrics
        total_feedback = len(feedback_items)
        helpful_count = sum(1 for item in feedback_items if item.get('helpful', False))
        not_helpful_count = total_feedback - helpful_count
        
        # Calculate average difficulty rating
        difficulty_ratings = [item.get('difficulty_rating', 5) for item in feedback_items]
        avg_difficulty_rating = sum(difficulty_ratings) / len(difficulty_ratings)
        
        # Calculate quality score (0-1 scale)
        # Quality score is based on helpful ratio, with adjustments for sample size
        helpful_ratio = helpful_count / total_feedback if total_feedback > 0 else 0.5
        
        # Apply confidence adjustment for small sample sizes
        confidence_factor = min(1.0, total_feedback / 10.0)  # Full confidence at 10+ feedback items
        quality_score = helpful_ratio * confidence_factor + 0.5 * (1 - confidence_factor)
        
        # Store/update quality scores
        quality_pk = f"QUALITY#{question_id}"
        quality_table.put_item(
            Item={
                'pk': quality_pk,
                'question_id': question_id,
                'quality_score': round(quality_score, 3),
                'feedback_count': total_feedback,
                'helpful_count': helpful_count,
                'not_helpful_count': not_helpful_count,
                'avg_difficulty_rating': round(avg_difficulty_rating, 2),
                'last_updated': int(time.time()),
                'improvement_trend': 0.0  # Will be calculated by RefinementLambda
            }
        )
        
        logger.info(f"Updated quality score for question {question_id}: {quality_score}")
        return quality_score
        
    except ClientError as e:
        logger.error(f"DynamoDB error updating quality scores: {e.response['Error']['Message']}")
        return 0.0
    except Exception as e:
        logger.error(f"Unexpected error updating quality scores: {str(e)}")
        return 0.0

def create_error_response(status_code: int, message: str) -> Dict[str, Any]:
    """Create standardized error response"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            **get_cors_response_headers(methods='POST,OPTIONS')
        },
        'body': json.dumps({
            'success': False,
            'error': message
        })
    }