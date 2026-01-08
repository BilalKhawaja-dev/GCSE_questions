"""
AsyncWorkerLambda handler for processing async question generation from SQS.
"""

import json
import logging
import os
import time
from datetime import datetime
from src.services.bedrock_service import BedrockService
from src.services.session_service import SessionService
from src.services.topic_coverage_service import TopicCoverageService

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
AWS_REGION = os.environ.get('AWS_REGION', os.environ.get('REGION', 'eu-west-2'))
SESSIONS_TABLE_NAME = os.environ.get('SESSIONS_TABLE_NAME')
TOPIC_COVERAGE_TABLE_NAME = os.environ.get('TOPIC_COVERAGE_TABLE_NAME')

# Initialize services
bedrock_service = BedrockService(region=AWS_REGION)
session_service = SessionService(region=AWS_REGION)
coverage_service = TopicCoverageService(region=AWS_REGION, table_name=TOPIC_COVERAGE_TABLE_NAME) if TOPIC_COVERAGE_TABLE_NAME else None


def lambda_handler(event, context):
    """
    AWS Lambda handler for async question generation from SQS messages.
    """
    logger.info(f"AsyncWorkerLambda invocation started - Processing {len(event.get('Records', []))} messages")
    
    results = []
    
    for record in event.get('Records', []):
        try:
            # Parse SQS message
            message_body = json.loads(record['body'])
            
            job_id = message_body.get('job_id')
            session_id = message_body.get('session_id')
            topic = message_body.get('topic')
            tier = message_body.get('tier')
            count = message_body.get('count')
            enriched_prompt = message_body.get('enriched_prompt', '')
            user_id = message_body.get('user_id')
            request_id = message_body.get('request_id')
            
            logger.info(f"Processing job {job_id}: {count} {tier} {topic} questions for user {user_id}")
            
            # Update job status to processing
            update_job_status(
                session_id=session_id,
                status='processing',
                progress=10,
                job_id=job_id,
                topic=topic,
                tier=tier,
                count=count
            )
            
            # Generate questions
            start_time = time.time()
            questions = generate_questions_with_bedrock(
                topic=topic,
                tier=tier,
                count=count,
                enriched_prompt=enriched_prompt,
                request_id=request_id
            )
            generation_time = time.time() - start_time
            
            # Generate mark schemes
            mark_schemes = generate_mark_schemes(questions)
            
            # Update job with results
            update_job_status(
                session_id=session_id,
                status='completed',
                progress=100,
                job_id=job_id,
                topic=topic,
                tier=tier,
                count=count,
                questions=questions,
                generation_time=generation_time
            )
            
            # Record topic coverage
            if coverage_service:
                try:
                    coverage_service.record_topic_coverage(
                        user_id=user_id,
                        topic=topic,
                        subtopic=topic.lower(),
                        question_count=len(questions),
                        session_id=session_id,
                        request_id=request_id
                    )
                    logger.info(f"Topic coverage recorded for {topic}")
                except Exception as e:
                    logger.warning(f"Failed to record topic coverage (non-critical): {str(e)}")
            
            logger.info(f"Job {job_id} completed successfully: {len(questions)} questions generated in {generation_time:.2f}s")
            
            results.append({
                'job_id': job_id,
                'status': 'success',
                'questions_generated': len(questions)
            })
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            
            # Try to update job with error status
            try:
                job_id = message_body.get('job_id')
                session_id = message_body.get('session_id')
                
                if job_id and session_id:
                    update_job_status(
                        session_id=session_id,
                        status='failed',
                        progress=0,
                        job_id=job_id,
                        error=str(e)
                    )
            except Exception as update_error:
                logger.error(f"Failed to update job status: {str(update_error)}")
            
            results.append({
                'job_id': message_body.get('job_id', 'unknown'),
                'status': 'failed',
                'error': str(e)
            })
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'success': True,
            'processed': len(results),
            'results': results
        })
    }


def update_job_status(session_id: str, status: str, progress: int, job_id: str, 
                     topic: str = None, tier: str = None, count: int = None,
                     questions: list = None, generation_time: float = None, error: str = None):
    """Update job status in DynamoDB."""
    try:
        metadata = {
            'job_id': job_id,
            'status': status,
            'progress': progress,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        if topic:
            metadata['topic'] = topic
        if tier:
            metadata['tier'] = tier
        if count:
            metadata['count'] = count
        if generation_time:
            metadata['generation_time'] = generation_time
        if error:
            metadata['error'] = error
        
        if status == 'processing':
            metadata['started_at'] = datetime.utcnow().isoformat()
        elif status in ['completed', 'failed']:
            metadata['completed_at'] = datetime.utcnow().isoformat()
        
        if questions:
            metadata['question_count'] = len(questions)
            metadata['total_marks'] = sum(q.get('marks', 0) for q in questions)
            
            # Update session with questions
            session_service.update_session_questions(
                session_id=session_id,
                questions=questions,
                metadata=metadata
            )
        else:
            # Update metadata only
            session_service.update_session_questions(
                session_id=session_id,
                questions=[],
                metadata=metadata
            )
        
        logger.info(f"Job status updated: {job_id} -> {status} ({progress}%)")
        
    except Exception as e:
        logger.error(f"Failed to update job status: {str(e)}")
        raise


def generate_questions_with_bedrock(topic: str, tier: str, count: int, enriched_prompt: str, request_id: str) -> list:
    """Generate questions using Bedrock Claude."""
    import random
    import hashlib
    
    # Create a unique seed for variety
    seed_string = f"{request_id}_{time.time()}_{random.random()}"
    seed_hash = hashlib.md5(seed_string.encode()).hexdigest()[:8]
    
    # For large question counts, use batch processing
    if count > 10:
        return generate_questions_in_batches(topic, tier, count, enriched_prompt, request_id)
    
    # Build the prompt for question generation
    edexcel_spec_context = f"""
OFFICIAL EDEXCEL GCSE SPECIFICATION REQUIREMENTS:
You MUST generate questions that align with the official Edexcel GCSE Mathematics specification.

For {tier} tier, focus on these specification codes:
- Number: N1-N16 (ordering, operations, place value, fractions, decimals, percentages, measures)
- Algebra: A1-A25 (notation, manipulation, graphs, equations, sequences)
- Ratio: R1-R16 (units, scale, proportion, percentages, compound interest)
- Geometry: G1-G25 (properties, constructions, mensuration, vectors)
- Probability: P1-P9 (experiments, outcomes, combined events)
- Statistics: S1-S6 (data analysis, graphs, distributions)

CRITICAL: Each question MUST be UNIQUE and DIFFERENT from any previous questions.
Use varied contexts, different numbers, alternative problem structures, and diverse scenarios.
"""

    prompt = f"""Generate {count} COMPLETELY NEW AND UNIQUE GCSE Mathematics exam questions for {tier} tier on the topic of {topic}.

UNIQUENESS REQUIREMENT (CRITICAL):
- Each question MUST be different from standard textbook examples
- Use VARIED numerical values (avoid common numbers like 2, 3, 5, 10)
- Create DIVERSE real-world contexts (shopping, sports, travel, technology, etc.)
- Apply DIFFERENT problem-solving approaches for each question
- Randomization seed: {seed_hash}

{edexcel_spec_context}

{enriched_prompt if enriched_prompt else ''}

QUESTION GENERATION RULES:
1. Use realistic, engaging contexts that students can relate to
2. Vary the complexity and structure of each question
3. Include different types of problems (calculation, reasoning, problem-solving)
4. Use diverse numerical values (decimals, fractions, mixed numbers, etc.)
5. Create questions that test understanding, not just memorization

For each question, provide:
1. The question text (clear, exam-style wording with unique context)
2. The number of marks (typically 2-6 marks)
3. A difficulty score from 1-10 ({tier} tier: {'1-5' if tier == 'Foundation' else '6-10'})
4. The correct answer with full working/solution

Return the questions as a JSON array with this structure:
[
  {{
    "question_text": "The question text here with unique context",
    "marks": 4,
    "difficulty_score": 5,
    "answer": "Step-by-step solution with final answer"
  }}
]

Only return the JSON array, no other text."""

    try:
        # Call Bedrock to generate questions
        response = bedrock_service.call_bedrock_with_retry(prompt, request_id, temperature=0.7)
        
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
        # Return fallback questions on error
        return generate_fallback_questions(topic, tier, count, request_id)


def generate_questions_in_batches(topic: str, tier: str, count: int, enriched_prompt: str, request_id: str) -> list:
    """Generate questions in batches to handle large requests."""
    
    # Determine batch size based on count
    if count <= 15:
        batch_size = 5
    elif count <= 30:
        batch_size = 6
    else:
        batch_size = 8
    
    all_questions = []
    batches = [(i, min(i + batch_size, count)) for i in range(0, count, batch_size)]
    
    logger.info(f"Processing {count} questions in {len(batches)} batches of size {batch_size}")
    
    for batch_idx, (start_idx, end_idx) in enumerate(batches):
        batch_count = end_idx - start_idx
        
        try:
            logger.info(f"Processing batch {batch_idx + 1}/{len(batches)}: questions {start_idx + 1}-{end_idx}")
            
            # Generate batch with modified prompt for variety
            batch_prompt = f"""{enriched_prompt}

BATCH {batch_idx + 1}/{len(batches)} - Questions {start_idx + 1} to {end_idx}
CRITICAL: Generate COMPLETELY DIFFERENT questions from previous batches.
- Use NEW numerical values
- Create NEW real-world contexts  
- Apply DIFFERENT problem-solving approaches
- Ensure NO repetition of question structures"""
            
            batch_questions = generate_single_batch(
                topic, tier, batch_count, batch_prompt, 
                f"{request_id}_batch_{batch_idx}", start_idx
            )
            
            all_questions.extend(batch_questions)
            
            # Small delay between batches to avoid rate limiting
            time.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Error in batch {batch_idx + 1}: {str(e)}")
            # Continue with next batch rather than failing completely
            continue
    
    # If we don't have enough questions, fill with fallbacks
    if len(all_questions) < count:
        remaining = count - len(all_questions)
        logger.info(f"Adding {remaining} fallback questions to reach target count")
        
        fallback_questions = generate_fallback_questions(
            topic, tier, remaining, request_id, start_index=len(all_questions)
        )
        all_questions.extend(fallback_questions)
    
    logger.info(f"Batch processing completed: {len(all_questions)} questions generated")
    return all_questions[:count]


def generate_single_batch(topic: str, tier: str, count: int, enriched_prompt: str, batch_request_id: str, start_index: int) -> list:
    """Generate a single batch of questions."""
    import random
    import hashlib
    
    # Create unique seed for this batch
    seed_string = f"{batch_request_id}_{time.time()}_{random.random()}"
    seed_hash = hashlib.md5(seed_string.encode()).hexdigest()[:8]
    
    # Build batch-specific prompt
    variety_instructions = ""
    if start_index > 0:
        variety_instructions = f"""
CRITICAL UNIQUENESS REQUIREMENT:
This is batch {start_index // count + 1}, starting at question {start_index + 1}.
You MUST generate questions that are COMPLETELY DIFFERENT from previous batches:
- Use DIFFERENT numerical values (avoid repeating numbers)
- Create NEW real-world contexts (shopping, sports, technology, travel, etc.)
- Apply ALTERNATIVE mathematical approaches
- Vary problem structures and question formats
- NO repetition of question patterns
"""
    
    edexcel_context = f"""
EDEXCEL SPECIFICATION ALIGNMENT:
Generate questions aligned with official Edexcel GCSE Mathematics specification codes.
For {tier} tier {topic}, ensure questions test the appropriate specification requirements.
Use exam-style language and realistic mark allocations.
"""
    
    prompt = f"""Generate {count} COMPLETELY NEW AND UNIQUE GCSE Mathematics exam questions for {tier} tier on the topic of {topic}.

Randomization seed: {seed_hash}

{edexcel_context}

{enriched_prompt if enriched_prompt else ''}

{variety_instructions}

DIVERSITY REQUIREMENTS:
- Use varied numerical values (not just 2, 3, 5, 10)
- Create engaging real-world contexts
- Mix calculation, reasoning, and problem-solving questions
- Vary difficulty within the {tier} tier range
- Ensure each question is structurally different

For each question, provide:
1. The question text (clear, exam-style wording with unique context)
2. The number of marks (typically 2-6 marks)  
3. A difficulty score from 1-10 ({tier} tier: {'1-5' if tier == 'Foundation' else '6-10'})
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
        # Call Bedrock for this batch
        response = bedrock_service.call_bedrock_with_retry(prompt, batch_request_id, temperature=0.7)
        
        # Parse the response
        questions = parse_bedrock_response(response, topic, tier, batch_request_id)
        
        # Adjust question IDs to be unique across batches
        for i, question in enumerate(questions):
            question['id'] = f'q_{batch_request_id}_{start_index + i}'
        
        return questions
        
    except Exception as e:
        logger.error(f"Batch generation failed for {batch_request_id}: {str(e)}")
        # Return fallback questions for this batch
        return generate_fallback_questions(topic, tier, count, batch_request_id, start_index)


def parse_bedrock_response(response: str, topic: str, tier: str, request_id: str) -> list:
    """Parse Bedrock response into question objects."""
    import re
    
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
                'text': q.get('question_text', q.get('text', '')),
                'marks': q.get('marks', 4),
                'topic': topic,
                'tier': tier,
                'difficulty_score': q.get('difficulty_score', 5),
                'answer': q.get('answer', '')
            }
            questions.append(question)
        
        return questions
        
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"Failed to parse Bedrock response: {str(e)}")
        raise ValueError(f"Failed to parse question response: {str(e)}")


def generate_fallback_questions(topic: str, tier: str, count: int, request_id: str, start_index: int = 0) -> list:
    """Generate fallback placeholder questions."""
    questions = []
    
    for i in range(count):
        question = {
            'id': f'q_{request_id}_{start_index + i}',
            'question_text': f"Sample {tier} {topic} question {start_index + i + 1}",
            'text': f"Sample {tier} {topic} question {start_index + i + 1}",
            'marks': 4 if tier == 'Foundation' else 5,
            'topic': topic,
            'tier': tier,
            'difficulty_score': 3 if tier == 'Foundation' else 6,
            'answer': "This is a placeholder question. Please try generating again."
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
