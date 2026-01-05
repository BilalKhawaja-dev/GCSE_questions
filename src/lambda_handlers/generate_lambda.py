"""
GenerateLambda handler for GCSE question generation.
"""

import json
import logging
import os
from src.utils.security import get_cors_response_headers
from src.services.bedrock_service import BedrockService

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
AWS_REGION = os.environ.get('AWS_REGION', os.environ.get('REGION', 'eu-west-2'))

# Initialize Bedrock service
bedrock_service = BedrockService(region=AWS_REGION)

def lambda_handler(event, context):
    """
    AWS Lambda handler for question generation.
    """
    import uuid
    from datetime import datetime
    
    request_id = str(uuid.uuid4())
    
    logger.info(f"GenerateLambda invocation started - Request ID: {request_id}")
    
    try:
        # Get user info from API Gateway authorizer context
        authorizer_context = event.get('requestContext', {}).get('authorizer', {})
        user_id = authorizer_context.get('user_id')
        session_token = authorizer_context.get('session_token')
        
        if not user_id:
            return create_error_response(400, "User not authenticated", request_id)
        
        # Parse request body
        if 'body' not in event or not event['body']:
            return create_error_response(400, "Request body is required", request_id)
        
        try:
            body = json.loads(event['body'])
        except json.JSONDecodeError:
            return create_error_response(400, "Invalid JSON in request body", request_id)
        
        # Extract required fields
        topic = body.get('topic')
        tier = body.get('tier')
        count = body.get('count', 1)
        enriched_prompt = body.get('enriched_prompt', '')
        
        # Basic validation
        if not all([topic, tier]):
            return create_error_response(400, "Missing required fields: topic, tier", request_id)
        
        if count < 1 or count > 100:
            return create_error_response(400, "Count must be between 1 and 100", request_id)
        
        # Generate questions using Bedrock
        try:
            questions = generate_questions_with_bedrock(
                topic=topic,
                tier=tier,
                count=count,
                enriched_prompt=enriched_prompt,
                request_id=request_id
            )
        except Exception as e:
            logger.warning(f"Bedrock generation failed, using fallback: {str(e)}")
            # Fallback to placeholder questions if Bedrock fails
            questions = generate_fallback_questions(topic, tier, count, request_id)
        
        # Create response with mark schemes
        mark_schemes = generate_mark_schemes(questions)
        
        response_body = {
            'success': True,
            'questions': questions,
            'mark_scheme': mark_schemes,
            'request_id': request_id,
            'generated_at': datetime.utcnow().isoformat(),
            'metadata': {
                'total_marks': sum(q.get('marks', 0) for q in questions),
                'model_version': 'claude-3-haiku',
                'generated_at': datetime.utcnow().isoformat()
            }
        }
        
        logger.info(f"Generated {len(questions)} questions for request {request_id}")
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                **get_cors_response_headers(methods='POST,OPTIONS')
            },
            'body': json.dumps(response_body)
        }
        
    except Exception as e:
        logger.error(f"GenerateLambda error: {str(e)}", exc_info=True)
        return create_error_response(500, "Internal server error", request_id)


def generate_questions_with_bedrock(topic: str, tier: str, count: int, enriched_prompt: str, request_id: str) -> list:
    """Generate questions using Bedrock Claude."""
    
    # Build the prompt for question generation
    prompt = f"""Generate {count} GCSE Mathematics exam questions for {tier} tier on the topic of {topic}.

{enriched_prompt if enriched_prompt else ''}

For each question, provide:
1. The question text (clear, exam-style wording)
2. The number of marks (typically 2-6 marks)
3. A difficulty score from 1-10

Return the questions as a JSON array with this structure:
[
  {{
    "question_text": "The question text here",
    "marks": 4,
    "difficulty_score": 5
  }}
]

Only return the JSON array, no other text."""

    try:
        # Call Bedrock to generate questions
        response = bedrock_service.call_bedrock_with_retry(prompt, request_id)
        
        # Parse the response
        questions = parse_bedrock_response(response, topic, tier, request_id)
        
        # Ensure we have the right number of questions
        if len(questions) < count:
            # Add fallback questions if needed
            fallback = generate_fallback_questions(topic, tier, count - len(questions), request_id, start_index=len(questions))
            questions.extend(fallback)
        
        return questions[:count]
        
    except Exception as e:
        logger.error(f"Bedrock question generation failed: {str(e)}")
        raise


def parse_bedrock_response(response: str, topic: str, tier: str, request_id: str) -> list:
    """Parse Bedrock response into question objects."""
    import re
    
    # Try to extract JSON from the response
    try:
        # Look for JSON array in the response
        json_match = re.search(r'\[[\s\S]*\]', response)
        if json_match:
            questions_data = json.loads(json_match.group())
        else:
            questions_data = json.loads(response)
        
        questions = []
        for i, q in enumerate(questions_data):
            question = {
                'id': f'q_{request_id}_{i}',
                'question_text': q.get('question_text', q.get('text', '')),
                'text': q.get('question_text', q.get('text', '')),  # Include both for compatibility
                'marks': q.get('marks', 4),
                'topic': topic,
                'tier': tier,
                'difficulty_score': q.get('difficulty_score', 5)
            }
            questions.append(question)
        
        return questions
        
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"Failed to parse Bedrock response: {str(e)}")
        raise ValueError(f"Failed to parse question response: {str(e)}")


def generate_fallback_questions(topic: str, tier: str, count: int, request_id: str, start_index: int = 0) -> list:
    """Generate fallback placeholder questions."""
    questions = []
    
    # Topic-specific sample questions
    sample_questions = {
        'Algebra': [
            "Solve the equation 3x + 7 = 22",
            "Simplify the expression 4a + 2b - a + 3b",
            "Factorise x² + 5x + 6",
            "Make y the subject of the formula x = 2y + 5",
            "Solve the simultaneous equations: 2x + y = 7 and x - y = 2"
        ],
        'Number': [
            "Calculate 15% of £240",
            "Write 0.375 as a fraction in its simplest form",
            "Find the highest common factor (HCF) of 24 and 36",
            "Calculate 3.5 × 2.4",
            "Express 72 as a product of prime factors"
        ],
        'Geometry': [
            "Calculate the area of a triangle with base 8cm and height 5cm",
            "Find the circumference of a circle with radius 7cm. Give your answer in terms of π",
            "Calculate the volume of a cuboid with dimensions 4cm × 3cm × 5cm",
            "Find the missing angle in a triangle where two angles are 65° and 48°",
            "Calculate the length of the hypotenuse in a right-angled triangle with sides 3cm and 4cm"
        ],
        'Statistics': [
            "Calculate the mean of the following data: 12, 15, 18, 21, 24",
            "Find the median of: 7, 3, 9, 5, 11, 8, 6",
            "A bag contains 3 red balls and 5 blue balls. What is the probability of picking a red ball?",
            "Draw a frequency table for the data: 2, 3, 2, 4, 3, 2, 5, 3, 4, 2",
            "Calculate the range of: 45, 32, 67, 28, 51"
        ]
    }
    
    # Get questions for the topic, or use generic ones
    topic_questions = sample_questions.get(topic, [
        f"Solve this {topic} problem involving basic concepts",
        f"Calculate the answer to this {topic} question",
        f"Show your working for this {topic} problem",
        f"Explain your method for solving this {topic} question",
        f"Find the solution to this {topic} problem"
    ])
    
    for i in range(count):
        idx = (start_index + i) % len(topic_questions)
        question = {
            'id': f'q_{request_id}_{start_index + i}',
            'question_text': topic_questions[idx],
            'text': topic_questions[idx],
            'marks': 4 if tier == 'Foundation' else 5,
            'topic': topic,
            'tier': tier,
            'difficulty_score': 3 if tier == 'Foundation' else 6
        }
        questions.append(question)
    
    return questions


def generate_mark_schemes(questions: list) -> list:
    """Generate mark schemes for questions."""
    mark_schemes = []
    
    for question in questions:
        marks = question.get('marks', 4)
        method_marks = max(1, int(marks * 0.6))
        accuracy_marks = marks - method_marks
        
        mark_scheme = {
            'question_id': question.get('id'),
            'marking_criteria': f"Award {method_marks} method mark(s) for correct working shown. Award {accuracy_marks} accuracy mark(s) for correct final answer. Accept equivalent methods.",
            'method_marks': method_marks,
            'accuracy_marks': accuracy_marks
        }
        mark_schemes.append(mark_scheme)
    
    return mark_schemes



def create_error_response(status_code, message, request_id):
    """Create standardized error response."""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            **get_cors_response_headers(methods='POST,OPTIONS')
        },
        'body': json.dumps({
            'success': False,
            'message': message,
            'request_id': request_id
        })
    }
