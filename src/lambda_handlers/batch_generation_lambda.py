"""
Batch Generation Lambda - Generate Multiple Questions

Generates 20-30 questions per invocation and sends each to verification queue.
"""

import json
import logging
import os
import boto3
import uuid
from typing import Dict, List, Any
from datetime import datetime

from src.services.bedrock_service import BedrockService
from src.services.content_retrieval_service import ContentRetrievalService

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
sqs = boto3.client('sqs')
bedrock_runtime = boto3.client('bedrock-runtime', region_name='eu-west-2')
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name='eu-west-2')

# Environment variables
VERIFICATION_QUEUE_URL = os.environ.get('VERIFICATION_QUEUE_URL')
KNOWLEDGE_BASE_ID = os.environ.get('KNOWLEDGE_BASE_ID')
SPECIFICATIONS_BUCKET = os.environ.get('SPECIFICATIONS_BUCKET', 'gcse-specifications-prod-1a64dc99')
EXAMPLES_BUCKET = os.environ.get('EXAMPLES_BUCKET', 'gcse-examples-prod-6e99600d')

# Initialize services
bedrock_service = BedrockService(region='eu-west-2', knowledge_base_id=KNOWLEDGE_BASE_ID)
content_retrieval = ContentRetrievalService(
    specifications_bucket=SPECIFICATIONS_BUCKET,
    examples_bucket=EXAMPLES_BUCKET,
    region='eu-west-2'
)


def handler(event, context):
    """
    Batch generation Lambda handler.
    
    Generates multiple questions and sends each to verification queue.
    
    Args:
        event: Event with topic, grade, paper_type, count
        context: Lambda context
    
    Returns:
        Response with generation summary
    """
    logger.info(f"Batch generation started: {json.dumps(event)}")
    
    try:
        # Parse input
        topic = event.get('topic')
        grade = event.get('grade')
        paper_type = event.get('paper_type')
        count = event.get('count', 20)
        
        if not all([topic, grade, paper_type]):
            raise ValueError("Missing required parameters: topic, grade, paper_type")
        
        logger.info(
            f"Generating {count} questions for "
            f"{topic}/{grade}/{paper_type}"
        )
        
        # Generate questions
        generated_questions = []
        failed_generations = []
        
        for i in range(count):
            try:
                question = generate_single_question(
                    topic=topic,
                    grade=grade,
                    paper_type=paper_type,
                    index=i
                )
                
                if question:
                    generated_questions.append(question)
                    
                    # Send to verification queue
                    send_to_verification_queue(question)
                else:
                    failed_generations.append({
                        'index': i,
                        'reason': 'Generation returned None'
                    })
                    
            except Exception as e:
                logger.error(
                    f"Failed to generate question {i}: {str(e)}",
                    exc_info=True
                )
                failed_generations.append({
                    'index': i,
                    'error': str(e)
                })
        
        # Calculate success rate
        success_rate = len(generated_questions) / count if count > 0 else 0.0
        
        logger.info(
            f"Batch generation complete: "
            f"generated={len(generated_questions)}, "
            f"failed={len(failed_generations)}, "
            f"success_rate={success_rate:.2%}"
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Batch generation complete',
                'topic': topic,
                'grade': grade,
                'paper_type': paper_type,
                'requested_count': count,
                'generated_count': len(generated_questions),
                'failed_count': len(failed_generations),
                'success_rate': success_rate,
                'failures': failed_generations[:10]  # First 10 failures
            })
        }
        
    except Exception as e:
        logger.error(f"Batch generation lambda failed: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }


def generate_single_question(
    topic: str,
    grade: str,
    paper_type: str,
    index: int,
    request_id: str = "batch-gen"
) -> Dict[str, Any]:
    """
    Generate a single question.
    
    Args:
        topic: Question topic
        grade: Grade level
        paper_type: Paper type
        index: Question index in batch
        request_id: Request ID for logging
    
    Returns:
        Generated question dictionary
    """
    try:
        # Use Knowledge Base if available, otherwise fallback to S3
        if KNOWLEDGE_BASE_ID and bedrock_service.kb_service:
            # Use KB for content retrieval
            prompt = build_generation_prompt_with_kb(
                topic=topic,
                grade=grade,
                paper_type=paper_type,
                bedrock_service=bedrock_service,
                request_id=request_id
            )
        else:
            # Fallback to S3 content retrieval
            retrieved_content = content_retrieval.get_specification_content(
                topic=topic,
                subtopic=None
            )
            
            # Build generation prompt
            prompt = build_generation_prompt(
                topic=topic,
                grade=grade,
                paper_type=paper_type,
                retrieved_content=retrieved_content
            )
        
        # Generate question using Bedrock
        response = bedrock_service.call_bedrock_with_retry(
            prompt=prompt,
            request_id=request_id,
            max_tokens=4000,
            temperature=0.7
        )
        
        # Parse response
        question_data = parse_generation_response(response)
        
        if not question_data:
            logger.warning(f"Failed to parse generation response for question {index}")
            return None
        
        # Add metadata
        question_data['question_id'] = str(uuid.uuid4())
        question_data['topic'] = topic
        question_data['grade'] = grade
        question_data['paper_type'] = paper_type
        question_data['created_at'] = datetime.utcnow().isoformat()
        question_data['verification_status'] = 'PENDING'
        
        logger.debug(f"Generated question {index}: {question_data['question_id']}")
        
        return question_data
        
    except Exception as e:
        logger.error(f"Failed to generate question {index}: {str(e)}")
        raise


def build_generation_prompt(
    topic: str,
    grade: str,
    paper_type: str,
    retrieved_content: List[Dict]
) -> str:
    """
    Build prompt for question generation.
    
    Args:
        topic: Question topic
        grade: Grade level
        paper_type: Paper type
        retrieved_content: Retrieved content dict
    
    Returns:
        Generation prompt
    """
    # Format retrieved content - handle dict format
    if isinstance(retrieved_content, dict):
        content_text = retrieved_content.get('content', '')
        if isinstance(content_text, str):
            context = f"[Specification Content]\n{content_text[:2000]}"
        else:
            context = "[No content available]"
    elif isinstance(retrieved_content, list):
        context = "\n\n".join([
            f"[Source {i+1}]\n{doc.get('content', '')}"
            for i, doc in enumerate(retrieved_content[:3])
        ])
    else:
        context = "[No content available]"
    
    # Paper type description
    calculator_note = "NON-CALCULATOR" if paper_type == "P1" else "CALCULATOR ALLOWED"
    
    prompt = f"""Generate a GCSE Mathematics question for Edexcel 1MA1 specification.

REQUIREMENTS:
- Topic: {topic}
- Grade: {grade}
- Paper Type: {paper_type} ({calculator_note})
- Format: Multiple choice with 4 options (A, B, C, D)
- Difficulty: Appropriate for {grade} tier

REFERENCE MATERIAL:
{context}

CONSTRAINTS:
- Question must be based on the reference material above
- Must follow Edexcel 1MA1 syllabus
- Paper 1 questions must be solvable without calculator
- Include clear working/rationale
- Ensure exactly one correct answer
- Make distractors plausible but clearly wrong

OUTPUT FORMAT (JSON):
{{
  "stem": "Question text here",
  "options": ["Option A", "Option B", "Option C", "Option D"],
  "correct_answer": "A",
  "rationale": "Step-by-step solution",
  "difficulty": 5
}}

Generate the question now:"""
    
    return prompt


def build_generation_prompt_with_kb(
    topic: str,
    grade: str,
    paper_type: str,
    bedrock_service: BedrockService,
    request_id: str
) -> str:
    """
    Build generation prompt using Knowledge Base retrieval.
    
    Args:
        topic: Question topic
        grade: Grade level
        paper_type: Paper type
        bedrock_service: Bedrock service with KB
        request_id: Request ID
    
    Returns:
        Generation prompt with KB context
    """
    # Paper type description
    calculator_note = "NON-CALCULATOR" if paper_type == "P1" else "CALCULATOR ALLOWED"
    
    # Base prompt
    base_prompt = f"""Generate a GCSE Mathematics question for Edexcel 1MA1 specification.

REQUIREMENTS:
- Topic: {topic}
- Grade: {grade}
- Paper Type: {paper_type} ({calculator_note})
- Format: Multiple choice with 4 options (A, B, C, D)
- Difficulty: Appropriate for {grade} tier

CONSTRAINTS:
- Must follow Edexcel 1MA1 syllabus
- Paper 1 questions must be solvable without calculator
- Include clear working/rationale
- Ensure exactly one correct answer
- Make distractors plausible but clearly wrong

OUTPUT FORMAT (JSON):
{{
  "stem": "Question text here",
  "options": ["Option A", "Option B", "Option C", "Option D"],
  "correct_answer": "A",
  "rationale": "Step-by-step solution",
  "difficulty": 5
}}

Generate the question now:"""
    
    # Enrich with KB if available
    enriched_prompt = bedrock_service.enrich_prompt_with_kb(
        base_prompt=base_prompt,
        topic=topic,
        tier=grade,
        request_id=request_id
    )
    
    return enriched_prompt


def parse_generation_response(response: str) -> Dict[str, Any]:
    """
    Parse generation response into question data.
    
    Args:
        response: Raw response from Bedrock
    
    Returns:
        Parsed question dictionary or None
    """
    try:
        # Try to extract JSON from response
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = response[json_start:json_end]
            
            # Clean control characters that break JSON parsing
            import re
            json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', json_str)
            
            question_data = json.loads(json_str)
            
            # Validate required fields
            required_fields = ['stem', 'options', 'correct_answer']
            if all(field in question_data for field in required_fields):
                return question_data
        
        logger.warning("Failed to parse generation response as JSON")
        return None
        
    except Exception as e:
        logger.error(f"Failed to parse generation response: {str(e)}")
        return None


def send_to_verification_queue(question: Dict[str, Any]) -> bool:
    """
    Send question to verification queue.
    
    Args:
        question: Question data
    
    Returns:
        True if successful
    """
    try:
        if not VERIFICATION_QUEUE_URL:
            logger.error("VERIFICATION_QUEUE_URL not configured")
            return False
        
        # Send to SQS
        response = sqs.send_message(
            QueueUrl=VERIFICATION_QUEUE_URL,
            MessageBody=json.dumps(question),
            MessageAttributes={
                'question_id': {
                    'StringValue': question['question_id'],
                    'DataType': 'String'
                },
                'topic': {
                    'StringValue': question['topic'],
                    'DataType': 'String'
                }
            }
        )
        
        logger.debug(
            f"Sent question {question['question_id']} to verification queue: "
            f"MessageId={response['MessageId']}"
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to send to verification queue: {str(e)}")
        return False
