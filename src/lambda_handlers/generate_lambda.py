"""
GenerateLambda handler for GCSE question generation.
"""

import json
import logging
import os
import time
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
    start_time = time.time()
    
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
        
        # Save session to DynamoDB for history tracking
        session_id = None
        try:
            from src.services.session_service import SessionService
            session_service = SessionService(region=AWS_REGION)
            
            session_metadata = {
                'topic': topic,
                'tier': tier,
                'question_count': len(questions),
                'total_marks': sum(q.get('marks', 0) for q in questions),
                'generation_time': time.time() - start_time if 'start_time' in dir() else 0
            }
            
            session_id = session_service.create_session(
                user_id=user_id,
                query=enriched_prompt[:200] if enriched_prompt else f"Generate {count} {tier} {topic} questions",
                generated_questions=questions,
                metadata=session_metadata,
                request_id=request_id
            )
            logger.info(f"Session saved: {session_id}")
        except Exception as e:
            logger.warning(f"Failed to save session (non-critical): {str(e)}")
        
        # Record topic coverage for analytics
        try:
            from src.services.topic_coverage_service import TopicCoverageService
            import os
            coverage_table = os.environ.get('TOPIC_COVERAGE_TABLE_NAME')
            if coverage_table:
                coverage_service = TopicCoverageService(region=AWS_REGION, table_name=coverage_table)
                coverage_service.record_topic_coverage(
                    user_id=user_id,
                    topic=topic,
                    subtopic=body.get('subtopic', topic.lower()),
                    question_count=len(questions),
                    session_id=session_id,
                    request_id=request_id
                )
                logger.info(f"Topic coverage recorded for {topic}")
        except Exception as e:
            logger.warning(f"Failed to record topic coverage (non-critical): {str(e)}")
        
        response_body = {
            'success': True,
            'questions': questions,
            'mark_scheme': mark_schemes,
            'session_id': session_id,
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
    
    # Build the prompt for question generation with answers
    prompt = f"""Generate {count} GCSE Mathematics exam questions for {tier} tier on the topic of {topic}.

{enriched_prompt if enriched_prompt else ''}

For each question, provide:
1. The question text (clear, exam-style wording)
2. The number of marks (typically 2-6 marks)
3. A difficulty score from 1-10
4. The correct answer with full working/solution

Return the questions as a JSON array with this structure:
[
  {{
    "question_text": "The question text here",
    "marks": 4,
    "difficulty_score": 5,
    "answer": "Step-by-step solution with final answer"
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
                'difficulty_score': q.get('difficulty_score', 5),
                'answer': q.get('answer', '')  # Include the answer
            }
            questions.append(question)
        
        return questions
        
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"Failed to parse Bedrock response: {str(e)}")
        raise ValueError(f"Failed to parse question response: {str(e)}")


def generate_fallback_questions(topic: str, tier: str, count: int, request_id: str, start_index: int = 0) -> list:
    """Generate fallback placeholder questions with answers."""
    questions = []
    
    # Topic-specific sample questions with answers
    sample_questions = {
        'Algebra': [
            {"question": "Solve the equation 3x + 7 = 22", "answer": "3x + 7 = 22\n3x = 22 - 7\n3x = 15\nx = 15 ÷ 3\nx = 5"},
            {"question": "Simplify the expression 4a + 2b - a + 3b", "answer": "4a + 2b - a + 3b\n= (4a - a) + (2b + 3b)\n= 3a + 5b"},
            {"question": "Factorise x² + 5x + 6", "answer": "x² + 5x + 6\nFind two numbers that multiply to 6 and add to 5: 2 and 3\n= (x + 2)(x + 3)"},
            {"question": "Make y the subject of the formula x = 2y + 5", "answer": "x = 2y + 5\nx - 5 = 2y\ny = (x - 5) ÷ 2\ny = (x - 5)/2"},
            {"question": "Solve the simultaneous equations: 2x + y = 7 and x - y = 2", "answer": "2x + y = 7 ... (1)\nx - y = 2 ... (2)\nAdding (1) and (2): 3x = 9, so x = 3\nSubstitute into (2): 3 - y = 2, so y = 1\nSolution: x = 3, y = 1"}
        ],
        'Number': [
            {"question": "Calculate 15% of £240", "answer": "15% of £240\n= 15/100 × 240\n= 0.15 × 240\n= £36"},
            {"question": "Write 0.375 as a fraction in its simplest form", "answer": "0.375 = 375/1000\n= 75/200 (÷5)\n= 15/40 (÷5)\n= 3/8 (÷5)"},
            {"question": "Find the highest common factor (HCF) of 24 and 36", "answer": "24 = 2³ × 3\n36 = 2² × 3²\nHCF = 2² × 3 = 4 × 3 = 12"},
            {"question": "Calculate 3.5 × 2.4", "answer": "3.5 × 2.4\n= 35 × 24 ÷ 100\n= 840 ÷ 100\n= 8.4"},
            {"question": "Express 72 as a product of prime factors", "answer": "72 ÷ 2 = 36\n36 ÷ 2 = 18\n18 ÷ 2 = 9\n9 ÷ 3 = 3\n3 ÷ 3 = 1\n72 = 2³ × 3²"}
        ],
        'Geometry': [
            {"question": "Calculate the area of a triangle with base 8cm and height 5cm", "answer": "Area = ½ × base × height\n= ½ × 8 × 5\n= ½ × 40\n= 20 cm²"},
            {"question": "Find the circumference of a circle with radius 7cm. Give your answer in terms of π", "answer": "Circumference = 2πr\n= 2 × π × 7\n= 14π cm"},
            {"question": "Calculate the volume of a cuboid with dimensions 4cm × 3cm × 5cm", "answer": "Volume = length × width × height\n= 4 × 3 × 5\n= 60 cm³"},
            {"question": "Find the missing angle in a triangle where two angles are 65° and 48°", "answer": "Angles in a triangle sum to 180°\nMissing angle = 180° - 65° - 48°\n= 180° - 113°\n= 67°"},
            {"question": "Calculate the length of the hypotenuse in a right-angled triangle with sides 3cm and 4cm", "answer": "Using Pythagoras: c² = a² + b²\nc² = 3² + 4²\nc² = 9 + 16\nc² = 25\nc = √25 = 5 cm"}
        ],
        'Statistics': [
            {"question": "Calculate the mean of the following data: 12, 15, 18, 21, 24", "answer": "Mean = sum of values ÷ number of values\n= (12 + 15 + 18 + 21 + 24) ÷ 5\n= 90 ÷ 5\n= 18"},
            {"question": "Find the median of: 7, 3, 9, 5, 11, 8, 6", "answer": "First, order the data: 3, 5, 6, 7, 8, 9, 11\nThere are 7 values, so median is the 4th value\nMedian = 7"},
            {"question": "A bag contains 3 red balls and 5 blue balls. What is the probability of picking a red ball?", "answer": "Total balls = 3 + 5 = 8\nP(red) = number of red balls ÷ total balls\n= 3/8"},
            {"question": "Draw a frequency table for the data: 2, 3, 2, 4, 3, 2, 5, 3, 4, 2", "answer": "Value | Frequency\n  2   |    4\n  3   |    3\n  4   |    2\n  5   |    1\nTotal |   10"},
            {"question": "Calculate the range of: 45, 32, 67, 28, 51", "answer": "Range = highest value - lowest value\n= 67 - 28\n= 39"}
        ]
    }
    
    # Get questions for the topic, or use generic ones
    topic_data = sample_questions.get(topic, [
        {"question": f"Solve this {topic} problem involving basic concepts", "answer": "Work through the problem step by step, showing all working."},
        {"question": f"Calculate the answer to this {topic} question", "answer": "Apply the relevant formula and show your calculations."},
        {"question": f"Show your working for this {topic} problem", "answer": "Demonstrate each step of your solution clearly."},
        {"question": f"Explain your method for solving this {topic} question", "answer": "Describe your approach and justify each step."},
        {"question": f"Find the solution to this {topic} problem", "answer": "Use appropriate methods to find the answer."}
    ])
    
    for i in range(count):
        idx = (start_index + i) % len(topic_data)
        q_data = topic_data[idx]
        question = {
            'id': f'q_{request_id}_{start_index + i}',
            'question_text': q_data['question'],
            'text': q_data['question'],
            'marks': 4 if tier == 'Foundation' else 5,
            'topic': topic,
            'tier': tier,
            'difficulty_score': 3 if tier == 'Foundation' else 6,
            'answer': q_data['answer']
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
        
        # Use the answer from the question if available
        answer = question.get('answer', '')
        if answer:
            marking_criteria = f"Answer: {answer}\n\nMarking: Award {method_marks} method mark(s) for correct working shown. Award {accuracy_marks} accuracy mark(s) for correct final answer."
        else:
            marking_criteria = f"Award {method_marks} method mark(s) for correct working shown. Award {accuracy_marks} accuracy mark(s) for correct final answer. Accept equivalent methods."
        
        mark_scheme = {
            'question_id': question.get('id'),
            'marking_criteria': marking_criteria,
            'method_marks': method_marks,
            'accuracy_marks': accuracy_marks,
            'answer': answer
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
