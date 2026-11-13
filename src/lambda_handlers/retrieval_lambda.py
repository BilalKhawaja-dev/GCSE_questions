"""Lambda handler for fast question retrieval from verified question bank."""

import json
import os
import random
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from decimal import Decimal
import boto3
from boto3.dynamodb.conditions import Key, Attr


def decimal_to_float(obj):
    """Convert Decimal to float for JSON serialization."""
    if isinstance(obj, list):
        return [decimal_to_float(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, Decimal):
        return float(obj)
    else:
        return obj


# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
cloudwatch = boto3.client('cloudwatch')

# Environment variables
VERIFIED_QUESTIONS_TABLE = os.environ.get('VERIFIED_QUESTIONS_TABLE', 'gcse-generator-v2-verified-questions-dev')
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')

# Performance target
TARGET_RESPONSE_TIME_MS = 100


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Retrieve verified questions from question bank.
    
    Fast retrieval (<100ms) from pre-verified question bank.
    Supports filtering by topic, grade, paper_type, and difficulty range.
    
    Args:
        event: API Gateway event with query parameters
        context: Lambda context
        
    Returns:
        API Gateway response with questions or error
    """
    start_time = time.time()
    
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        # Extract required parameters
        topic = body.get('topic')
        grade = body.get('grade')
        paper_type = body.get('paper_type')
        
        # Validate required parameters
        if not all([topic, grade, paper_type]):
            return {
                'statusCode': 400,
                'headers': _get_cors_headers(),
                'body': json.dumps({
                    'error': 'Missing required parameters',
                    'required': ['topic', 'grade', 'paper_type']
                })
            }
        
        # Extract optional parameters
        difficulty_min = body.get('difficulty_min', 1)
        difficulty_max = body.get('difficulty_max', 10)
        exclude_question_ids = body.get('exclude_question_ids', [])
        count = body.get('count', 5)
        
        # Validate difficulty range
        if not (1 <= difficulty_min <= 10 and 1 <= difficulty_max <= 10):
            return {
                'statusCode': 400,
                'headers': _get_cors_headers(),
                'body': json.dumps({
                    'error': 'Invalid difficulty range',
                    'message': 'Difficulty must be between 1 and 10'
                })
            }
        
        if difficulty_min > difficulty_max:
            return {
                'statusCode': 400,
                'headers': _get_cors_headers(),
                'body': json.dumps({
                    'error': 'Invalid difficulty range',
                    'message': 'difficulty_min must be <= difficulty_max'
                })
            }
        
        # Retrieve questions from DynamoDB
        questions = _retrieve_questions(
            topic=topic,
            grade=grade,
            paper_type=paper_type,
            difficulty_min=difficulty_min,
            difficulty_max=difficulty_max,
            exclude_ids=exclude_question_ids,
            count=count
        )
        
        # Calculate response time
        response_time_ms = (time.time() - start_time) * 1000
        
        # Send CloudWatch metrics
        _send_metrics(
            response_time_ms=response_time_ms,
            questions_returned=len(questions),
            topic=topic,
            grade=grade,
            paper_type=paper_type
        )
        
        # Check if bank is empty
        if not questions:
            return _handle_empty_bank(
                topic=topic,
                grade=grade,
                paper_type=paper_type,
                response_time_ms=response_time_ms
            )
        
        # Return successful response
        return {
            'statusCode': 200,
            'headers': _get_cors_headers(),
            'body': json.dumps({
                'questions': decimal_to_float(questions),
                'metadata': {
                    'total_available': len(questions),
                    'response_time_ms': round(response_time_ms, 2),
                    'source': 'verified_bank'
                }
            })
        }
        
    except Exception as e:
        print(f"Error in retrieval_lambda: {str(e)}")
        
        # Send error metric
        _send_error_metric(str(e))
        
        return {
            'statusCode': 500,
            'headers': _get_cors_headers(),
            'body': json.dumps({
                'error': 'Internal server error',
                'message': 'Failed to retrieve questions'
            })
        }


def _retrieve_questions(
    topic: str,
    grade: str,
    paper_type: str,
    difficulty_min: int,
    difficulty_max: int,
    exclude_ids: List[str],
    count: int
) -> List[Dict[str, Any]]:
    """
    Query DynamoDB for verified questions.
    
    Uses GSI for efficient querying by topic_grade_paper + difficulty range.
    
    Args:
        topic: Question topic
        grade: Grade level (foundation/higher)
        paper_type: Paper type (P1/P2/P3)
        difficulty_min: Minimum difficulty
        difficulty_max: Maximum difficulty
        exclude_ids: Question IDs to exclude
        count: Number of questions to return
        
    Returns:
        List of question dictionaries
    """
    table = dynamodb.Table(VERIFIED_QUESTIONS_TABLE)
    
    # Construct composite key for GSI
    topic_grade_paper = f"{topic}_{grade}_{paper_type}"
    
    # Query using GSI
    response = table.query(
        IndexName='TopicGradePaperDifficultyIndex',
        KeyConditionExpression=Key('topic_grade_paper').eq(topic_grade_paper) & 
                              Key('difficulty').between(difficulty_min, difficulty_max),
        FilterExpression=Attr('verification_status').eq('VERIFIED')
    )
    
    questions = response.get('Items', [])
    
    # Filter out excluded questions
    if exclude_ids:
        questions = [q for q in questions if q.get('question_id') not in exclude_ids]
    
    # Random selection
    if len(questions) > count:
        questions = random.sample(questions, count)
    
    # Update usage tracking for selected questions
    for question in questions:
        _increment_usage_count(question.get('question_id'))
    
    # Format questions for response
    formatted_questions = []
    for q in questions:
        formatted_questions.append({
            'question_id': q.get('question_id'),
            'stem': q.get('stem'),
            'options': q.get('options', []),
            'correct_answer': q.get('correct_answer'),
            'rationale': q.get('rationale'),
            'difficulty': q.get('difficulty'),
            'verification_confidence': q.get('verification_confidence'),
            'topic': q.get('topic'),
            'grade': q.get('grade'),
            'paper_type': q.get('paper_type')
        })
    
    return formatted_questions


def _increment_usage_count(question_id: str) -> None:
    """
    Increment times_served counter for a question.
    
    Args:
        question_id: Question ID to update
    """
    try:
        table = dynamodb.Table(VERIFIED_QUESTIONS_TABLE)
        
        table.update_item(
            Key={'question_id': question_id},
            UpdateExpression='SET times_served = if_not_exists(times_served, :zero) + :inc, last_served = :timestamp',
            ExpressionAttributeValues={
                ':zero': 0,
                ':inc': 1,
                ':timestamp': datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        # Don't fail the request if usage tracking fails
        print(f"Warning: Failed to increment usage count for {question_id}: {str(e)}")


def _handle_empty_bank(
    topic: str,
    grade: str,
    paper_type: str,
    response_time_ms: float
) -> Dict[str, Any]:
    """
    Handle empty question bank scenario.
    
    Returns error with suggestion to use generation endpoint as fallback.
    
    Args:
        topic: Question topic
        grade: Grade level
        paper_type: Paper type
        response_time_ms: Response time in milliseconds
        
    Returns:
        API Gateway response
    """
    # Send empty bank metric
    cloudwatch.put_metric_data(
        Namespace='GCSE/QuestionBank',
        MetricData=[
            {
                'MetricName': 'EmptyBank',
                'Value': 1,
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'Topic', 'Value': topic},
                    {'Name': 'Grade', 'Value': grade},
                    {'Name': 'PaperType', 'Value': paper_type},
                    {'Name': 'Environment', 'Value': ENVIRONMENT}
                ]
            }
        ]
    )
    
    return {
        'statusCode': 404,
        'headers': _get_cors_headers(),
        'body': json.dumps({
            'error': 'No verified questions available',
            'message': f'Question bank is empty for {topic}/{grade}/{paper_type}',
            'suggestion': 'Use generation endpoint as fallback',
            'metadata': {
                'response_time_ms': round(response_time_ms, 2),
                'source': 'verified_bank'
            }
        })
    }


def _send_metrics(
    response_time_ms: float,
    questions_returned: int,
    topic: str,
    grade: str,
    paper_type: str
) -> None:
    """
    Send CloudWatch metrics for retrieval performance.
    
    Args:
        response_time_ms: Response time in milliseconds
        questions_returned: Number of questions returned
        topic: Question topic
        grade: Grade level
        paper_type: Paper type
    """
    try:
        cloudwatch.put_metric_data(
            Namespace='GCSE/QuestionBank',
            MetricData=[
                {
                    'MetricName': 'RetrievalLatency',
                    'Value': response_time_ms,
                    'Unit': 'Milliseconds',
                    'Dimensions': [
                        {'Name': 'Environment', 'Value': ENVIRONMENT}
                    ]
                },
                {
                    'MetricName': 'QuestionsRetrieved',
                    'Value': questions_returned,
                    'Unit': 'Count',
                    'Dimensions': [
                        {'Name': 'Topic', 'Value': topic},
                        {'Name': 'Grade', 'Value': grade},
                        {'Name': 'PaperType', 'Value': paper_type},
                        {'Name': 'Environment', 'Value': ENVIRONMENT}
                    ]
                }
            ]
        )
        
        # Check if we're meeting performance target
        if response_time_ms > TARGET_RESPONSE_TIME_MS:
            cloudwatch.put_metric_data(
                Namespace='GCSE/QuestionBank',
                MetricData=[
                    {
                        'MetricName': 'SlowRetrieval',
                        'Value': 1,
                        'Unit': 'Count',
                        'Dimensions': [
                            {'Name': 'Environment', 'Value': ENVIRONMENT}
                        ]
                    }
                ]
            )
    except Exception as e:
        # Don't fail the request if metrics fail
        print(f"Warning: Failed to send metrics: {str(e)}")


def _send_error_metric(error_message: str) -> None:
    """
    Send error metric to CloudWatch.
    
    Args:
        error_message: Error message
    """
    try:
        cloudwatch.put_metric_data(
            Namespace='GCSE/QuestionBank',
            MetricData=[
                {
                    'MetricName': 'RetrievalErrors',
                    'Value': 1,
                    'Unit': 'Count',
                    'Dimensions': [
                        {'Name': 'Environment', 'Value': ENVIRONMENT}
                    ]
                }
            ]
        )
    except Exception as e:
        print(f"Warning: Failed to send error metric: {str(e)}")


def _get_cors_headers() -> Dict[str, str]:
    """
    Get CORS headers for API Gateway response.
    
    Returns:
        Dictionary of CORS headers
    """
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
    }
