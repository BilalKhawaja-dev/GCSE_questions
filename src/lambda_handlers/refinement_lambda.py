"""
RefinementLambda - AI Learning and Question Improvement

This Lambda function runs on a scheduled basis to analyze user feedback and improve
question quality through AI learning. It processes feedback data, identifies
improvement candidates, and generates enhanced question variations.
"""

import json
import logging
import os
import time
from typing import Dict, Any, List, Optional
import boto3
from botocore.exceptions import ClientError
from decimal import Decimal

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')
bedrock = boto3.client('bedrock-runtime', region_name='eu-west-2')

# Environment variables
QUESTION_FEEDBACK_TABLE = os.environ.get('QUESTION_FEEDBACK_TABLE', 'gcse-generator-v2-question-feedback-dev')
QUALITY_SCORES_TABLE = os.environ.get('QUALITY_SCORES_TABLE', 'gcse-generator-v2-quality-scores-dev')
QUESTION_BANK_BUCKET = os.environ.get('QUESTION_BANK_BUCKET', 'gcse-question-bank-dev')
BEDROCK_MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-sonnet-20240229-v1:0')

# Constants
MAX_QUESTIONS_PER_RUN = 100
MIN_FEEDBACK_COUNT = 5
QUALITY_THRESHOLD = 0.7

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle scheduled refinement processing
    
    This function is triggered by EventBridge on a weekly schedule
    """
    try:
        logger.info("Starting RefinementLambda execution")
        
        # Step 1: Fetch feedback data and identify improvement candidates
        improvement_candidates = identify_improvement_candidates()
        logger.info(f"Found {len(improvement_candidates)} questions needing improvement")
        
        if not improvement_candidates:
            logger.info("No questions need improvement at this time")
            return create_success_response(0, 0, "No questions needed improvement")
        
        # Step 2: Process improvement candidates (limit to MAX_QUESTIONS_PER_RUN)
        candidates_to_process = improvement_candidates[:MAX_QUESTIONS_PER_RUN]
        
        improved_count = 0
        failed_count = 0
        
        for candidate in candidates_to_process:
            try:
                success = process_improvement_candidate(candidate)
                if success:
                    improved_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                logger.error(f"Error processing candidate {candidate['question_id']}: {str(e)}")
                failed_count += 1
        
        # Step 3: Update analytics and report results
        update_analytics(improved_count, failed_count)
        
        logger.info(f"RefinementLambda completed: {improved_count} improved, {failed_count} failed")
        
        return create_success_response(improved_count, failed_count, "Refinement process completed successfully")
        
    except Exception as e:
        logger.error(f"Error in RefinementLambda: {str(e)}")
        return create_error_response(f"Refinement process failed: {str(e)}")

def identify_improvement_candidates() -> List[Dict[str, Any]]:
    """Identify questions that need improvement based on feedback data"""
    try:
        quality_table = dynamodb.Table(QUALITY_SCORES_TABLE)
        
        # Scan for questions with low quality scores or sufficient feedback
        response = quality_table.scan(
            FilterExpression='feedback_count >= :min_feedback AND quality_score < :threshold',
            ExpressionAttributeValues={
                ':min_feedback': MIN_FEEDBACK_COUNT,
                ':threshold': Decimal(str(QUALITY_THRESHOLD))
            }
        )
        
        candidates = []
        for item in response.get('Items', []):
            candidates.append({
                'question_id': item['question_id'],
                'quality_score': float(item['quality_score']),
                'feedback_count': item['feedback_count'],
                'helpful_count': item['helpful_count'],
                'not_helpful_count': item['not_helpful_count'],
                'avg_difficulty_rating': float(item['avg_difficulty_rating']),
                'last_updated': item['last_updated']
            })
        
        # Sort by quality score (lowest first) and feedback count (highest first)
        candidates.sort(key=lambda x: (x['quality_score'], -x['feedback_count']))
        
        return candidates
        
    except ClientError as e:
        logger.error(f"DynamoDB error identifying candidates: {e.response['Error']['Message']}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error identifying candidates: {str(e)}")
        return []

def process_improvement_candidate(candidate: Dict[str, Any]) -> bool:
    """Process a single improvement candidate"""
    try:
        question_id = candidate['question_id']
        logger.info(f"Processing improvement for question {question_id}")
        
        # Step 1: Fetch original question data
        original_question = fetch_original_question(question_id)
        if not original_question:
            logger.warning(f"Could not fetch original question data for {question_id}")
            return False
        
        # Step 2: Fetch detailed feedback
        feedback_data = fetch_detailed_feedback(question_id)
        if not feedback_data:
            logger.warning(f"Could not fetch feedback data for {question_id}")
            return False
        
        # Step 3: Generate improved question using Bedrock
        improved_question = generate_improved_question(original_question, feedback_data, candidate)
        if not improved_question:
            logger.warning(f"Could not generate improved question for {question_id}")
            return False
        
        # Step 4: Store improved question in Question Bank
        success = store_improved_question(question_id, improved_question, candidate)
        if not success:
            logger.warning(f"Could not store improved question for {question_id}")
            return False
        
        # Step 5: Update quality metrics
        update_quality_metrics(question_id, candidate)
        
        logger.info(f"Successfully improved question {question_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error processing candidate {candidate.get('question_id', 'unknown')}: {str(e)}")
        return False

def fetch_original_question(question_id: str) -> Optional[Dict[str, Any]]:
    """Fetch original question data from Question Bank or reconstruct from feedback"""
    try:
        # Try to fetch from Question Bank first
        try:
            # Look for existing question in S3
            key = f"generated/{question_id}.json"
            response = s3.get_object(Bucket=QUESTION_BANK_BUCKET, Key=key)
            question_data = json.loads(response['Body'].read().decode('utf-8'))
            return question_data
        except ClientError as e:
            if e.response['Error']['Code'] != 'NoSuchKey':
                raise
        
        # If not found in S3, we'll need to reconstruct from available data
        # For now, return a minimal structure that can be improved
        logger.warning(f"Original question {question_id} not found in Question Bank")
        return {
            'question_id': question_id,
            'question_text': 'Original question text not available',
            'mark_scheme': 'Original mark scheme not available',
            'metadata': {
                'topic': 'unknown',
                'difficulty_score': 5,
                'tier': 'Foundation'
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching original question {question_id}: {str(e)}")
        return None

def fetch_detailed_feedback(question_id: str) -> Optional[Dict[str, Any]]:
    """Fetch detailed feedback data for a question"""
    try:
        feedback_table = dynamodb.Table(QUESTION_FEEDBACK_TABLE)
        
        # Query all feedback for this question
        pk = f"FEEDBACK#{question_id}"
        response = feedback_table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('pk').eq(pk)
        )
        
        feedback_items = response.get('Items', [])
        if not feedback_items:
            return None
        
        # Analyze feedback patterns
        helpful_feedback = [item for item in feedback_items if item.get('helpful', False)]
        not_helpful_feedback = [item for item in feedback_items if not item.get('helpful', True)]
        
        # Extract common issues from comments
        common_issues = extract_common_issues([item.get('comments', '') for item in not_helpful_feedback])
        
        # Calculate difficulty distribution
        difficulty_ratings = [item.get('difficulty_rating', 5) for item in feedback_items]
        avg_difficulty = sum(difficulty_ratings) / len(difficulty_ratings)
        
        return {
            'total_feedback': len(feedback_items),
            'helpful_count': len(helpful_feedback),
            'not_helpful_count': len(not_helpful_feedback),
            'avg_difficulty_rating': avg_difficulty,
            'common_issues': common_issues,
            'difficulty_distribution': difficulty_ratings,
            'sample_comments': [item.get('comments', '') for item in feedback_items if item.get('comments')][:5]
        }
        
    except Exception as e:
        logger.error(f"Error fetching feedback for {question_id}: {str(e)}")
        return None

def extract_common_issues(comments: List[str]) -> List[str]:
    """Extract common issues from feedback comments"""
    # Simple keyword-based analysis for common issues
    issues = []
    
    # Common issue patterns
    issue_patterns = {
        'too_difficult': ['too hard', 'difficult', 'complex', 'confusing'],
        'too_easy': ['too easy', 'simple', 'basic'],
        'unclear_wording': ['unclear', 'confusing', 'ambiguous', 'wording'],
        'mathematical_errors': ['wrong', 'error', 'mistake', 'incorrect'],
        'missing_context': ['context', 'information', 'missing', 'incomplete']
    }
    
    comment_text = ' '.join(comments).lower()
    
    for issue_type, keywords in issue_patterns.items():
        if any(keyword in comment_text for keyword in keywords):
            issues.append(issue_type)
    
    return issues

def generate_improved_question(original_question: Dict[str, Any], feedback_data: Dict[str, Any], 
                             candidate: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Generate an improved version of the question using Bedrock Sonnet"""
    try:
        # Build improvement prompt
        prompt = build_improvement_prompt(original_question, feedback_data, candidate)
        
        # Call Bedrock Sonnet
        response = bedrock.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            contentType='application/json',
            accept='application/json',
            body=json.dumps({
                'anthropic_version': 'bedrock-2023-05-31',
                'max_tokens': 2000,
                'temperature': 0.3,
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ]
            })
        )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        improved_content = response_body['content'][0]['text']
        
        # Parse the improved question JSON
        try:
            improved_question = json.loads(improved_content)
            
            # Add metadata
            improved_question['refinement_metadata'] = {
                'original_question_id': original_question['question_id'],
                'refinement_timestamp': int(time.time()),
                'original_quality_score': candidate['quality_score'],
                'feedback_count': candidate['feedback_count'],
                'improvement_reasons': feedback_data.get('common_issues', []),
                'bedrock_model': BEDROCK_MODEL_ID
            }
            
            return improved_question
            
        except json.JSONDecodeError:
            logger.error(f"Failed to parse improved question JSON: {improved_content}")
            return None
        
    except Exception as e:
        logger.error(f"Error generating improved question: {str(e)}")
        return None

def build_improvement_prompt(original_question: Dict[str, Any], feedback_data: Dict[str, Any], 
                           candidate: Dict[str, Any]) -> str:
    """Build the improvement prompt for Bedrock"""
    
    prompt = f"""You are an expert GCSE Mathematics question writer for Edexcel specifications.

Original Question (Quality Score: {candidate['quality_score']:.2f}):
{json.dumps(original_question, indent=2)}

User Feedback Summary:
- Total Feedback: {feedback_data['total_feedback']}
- Helpful: {feedback_data['helpful_count']}/{feedback_data['total_feedback']}
- Average Difficulty Rating: {feedback_data['avg_difficulty_rating']:.1f}/10
- Common Issues: {', '.join(feedback_data.get('common_issues', ['None identified']))}

Sample User Comments:
{chr(10).join(f"- {comment}" for comment in feedback_data.get('sample_comments', [])[:3])}

Task: Generate an improved version of this question that addresses the feedback issues while maintaining Edexcel specification compliance.

Requirements:
1. Address the common issues identified in feedback
2. Adjust difficulty to match user expectations (target: {feedback_data['avg_difficulty_rating']:.1f}/10)
3. Maintain Edexcel GCSE Mathematics specification compliance
4. Ensure clear, unambiguous wording
5. Provide accurate mark scheme with method and accuracy marks
6. Use plain text/Unicode for mathematical notation (no LaTeX)

Generate the improved question in this exact JSON format:
{{
  "question_id": "improved_{original_question['question_id']}_{int(time.time())}",
  "question_text": "Clear, improved question text with proper mathematical notation",
  "mark_scheme": {{
    "marking_criteria": "Detailed marking criteria",
    "method_marks": 2,
    "accuracy_marks": 1
  }},
  "metadata": {{
    "topic": "{original_question.get('metadata', {}).get('topic', 'mathematics')}",
    "subtopic": "specific subtopic",
    "difficulty_score": {min(10, max(1, round(feedback_data['avg_difficulty_rating'])))},
    "tier": "{original_question.get('metadata', {}).get('tier', 'Foundation')}",
    "assessment_objective": "AO1/AO2/AO3",
    "learning_objective": "Specific learning objective from specification"
  }},
  "improvements_made": [
    "List of specific improvements made based on feedback"
  ]
}}

Respond with only the JSON, no additional text."""

    return prompt

def store_improved_question(question_id: str, improved_question: Dict[str, Any], 
                          candidate: Dict[str, Any]) -> bool:
    """Store the improved question in S3 Question Bank"""
    try:
        # Generate S3 key
        timestamp = int(time.time())
        key = f"refined/improved/{improved_question['question_id']}.json"
        
        # Add storage metadata
        improved_question['storage_metadata'] = {
            'stored_at': timestamp,
            'bucket': QUESTION_BANK_BUCKET,
            'key': key,
            'refinement_run_id': f"refinement_{timestamp}"
        }
        
        # Store in S3
        s3.put_object(
            Bucket=QUESTION_BANK_BUCKET,
            Key=key,
            Body=json.dumps(improved_question, indent=2, default=str),
            ContentType='application/json',
            Metadata={
                'original-question-id': question_id,
                'quality-score': str(candidate['quality_score']),
                'feedback-count': str(candidate['feedback_count']),
                'refinement-timestamp': str(timestamp)
            }
        )
        
        logger.info(f"Stored improved question at s3://{QUESTION_BANK_BUCKET}/{key}")
        return True
        
    except Exception as e:
        logger.error(f"Error storing improved question: {str(e)}")
        return False

def update_quality_metrics(question_id: str, candidate: Dict[str, Any]) -> None:
    """Update quality metrics to reflect improvement processing"""
    try:
        quality_table = dynamodb.Table(QUALITY_SCORES_TABLE)
        
        # Update the quality score record with improvement tracking
        quality_table.update_item(
            Key={'pk': f"QUALITY#{question_id}"},
            UpdateExpression='SET improvement_trend = :trend, last_improvement_attempt = :timestamp',
            ExpressionAttributeValues={
                ':trend': Decimal('0.1'),  # Positive trend indicating improvement attempt
                ':timestamp': int(time.time())
            }
        )
        
    except Exception as e:
        logger.error(f"Error updating quality metrics for {question_id}: {str(e)}")

def update_analytics(improved_count: int, failed_count: int) -> None:
    """Update analytics data in S3"""
    try:
        timestamp = int(time.time())
        analytics_key = f"analytics/refinement-run-{timestamp}.json"
        
        analytics_data = {
            'run_timestamp': timestamp,
            'questions_improved': improved_count,
            'questions_failed': failed_count,
            'total_processed': improved_count + failed_count,
            'success_rate': improved_count / (improved_count + failed_count) if (improved_count + failed_count) > 0 else 0,
            'bedrock_model': BEDROCK_MODEL_ID,
            'max_questions_per_run': MAX_QUESTIONS_PER_RUN,
            'quality_threshold': QUALITY_THRESHOLD,
            'min_feedback_count': MIN_FEEDBACK_COUNT
        }
        
        s3.put_object(
            Bucket=QUESTION_BANK_BUCKET,
            Key=analytics_key,
            Body=json.dumps(analytics_data, indent=2, default=str),
            ContentType='application/json'
        )
        
        logger.info(f"Updated analytics at s3://{QUESTION_BANK_BUCKET}/{analytics_key}")
        
    except Exception as e:
        logger.error(f"Error updating analytics: {str(e)}")

def create_success_response(improved_count: int, failed_count: int, message: str) -> Dict[str, Any]:
    """Create a success response"""
    return {
        'statusCode': 200,
        'body': json.dumps({
            'success': True,
            'message': message,
            'results': {
                'questions_improved': improved_count,
                'questions_failed': failed_count,
                'total_processed': improved_count + failed_count,
                'timestamp': int(time.time())
            }
        })
    }

def create_error_response(message: str) -> Dict[str, Any]:
    """Create an error response"""
    return {
        'statusCode': 500,
        'body': json.dumps({
            'success': False,
            'error': message,
            'timestamp': int(time.time())
        })
    }