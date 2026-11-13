"""
Parallel AsyncWorkerLambda handler for simultaneous question generation.
Processes multiple batches concurrently to reduce latency.
"""

import json
import logging
import os
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
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
    AWS Lambda handler for parallel async question generation from SQS messages.
    """
    logger.info(f"ParallelAsyncWorkerLambda invocation started - Processing {len(event.get('Records', []))} messages")
    
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
            
            # Generate questions in parallel
            start_time = time.time()
            questions = generate_questions_parallel(
                topic=topic,
                tier=tier,
                count=count,
                enriched_prompt=enriched_prompt,
                request_id=request_id,
                job_id=job_id,
                session_id=session_id
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
                'questions_generated': len(questions),
                'generation_time': generation_time
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


def generate_questions_parallel(topic: str, tier: str, count: int, enriched_prompt: str, 
                              request_id: str, job_id: str, session_id: str) -> list:
    """Generate questions using parallel processing for maximum speed."""
    
    # For small counts, use single batch
    if count <= 8:
        return generate_single_batch_optimized(topic, tier, count, enriched_prompt, request_id, 0)
    
    # Determine optimal parallel strategy
    if count <= 15:
        # Use 3 parallel batches
        batch_size = max(3, count // 3)
        max_workers = 3
    elif count <= 30:
        # Use 4 parallel batches  
        batch_size = max(4, count // 4)
        max_workers = 4
    else:
        # Use 5 parallel batches for large requests
        batch_size = max(6, count // 5)
        max_workers = 5
    
    # Create batch specifications
    batches = []
    remaining = count
    batch_idx = 0
    
    while remaining > 0:
        current_batch_size = min(batch_size, remaining)
        batches.append({
            'batch_idx': batch_idx,
            'start_idx': count - remaining,
            'batch_size': current_batch_size,
            'batch_request_id': f"{request_id}_parallel_{batch_idx}"
        })
        remaining -= current_batch_size
        batch_idx += 1
    
    logger.info(f"Processing {count} questions in {len(batches)} parallel batches with {max_workers} workers")
    
    # Progress tracking
    def update_progress(completed_batches):
        progress = 10 + int((completed_batches / len(batches)) * 80)  # 10-90% range
        update_job_status(
            session_id=session_id,
            status='processing',
            progress=progress,
            job_id=job_id
        )
    
    # Execute batches in parallel
    all_questions = []
    completed_count = 0
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all batch jobs
        future_to_batch = {
            executor.submit(
                generate_single_batch_optimized,
                topic, tier, batch['batch_size'], enriched_prompt,
                batch['batch_request_id'], batch['start_idx']
            ): batch for batch in batches
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_batch):
            batch = future_to_batch[future]
            try:
                batch_questions = future.result()
                all_questions.extend(batch_questions)
                completed_count += 1
                
                logger.info(f"Batch {batch['batch_idx'] + 1}/{len(batches)} completed: {len(batch_questions)} questions")
                
                # Update progress
                update_progress(completed_count)
                
            except Exception as e:
                logger.error(f"Batch {batch['batch_idx']} failed: {str(e)}")
                # Add fallback questions for failed batch
                fallback_questions = generate_fallback_questions(
                    topic, tier, batch['batch_size'], 
                    batch['batch_request_id'], batch['start_idx']
                )
                all_questions.extend(fallback_questions)
                completed_count += 1
                update_progress(completed_count)
    
    # Sort questions by their original index to maintain order
    all_questions.sort(key=lambda q: int(q.get('id', '0').split('_')[-1]))
    
    logger.info(f"Parallel processing completed: {len(all_questions)} questions generated")
    return all_questions[:count]


def generate_single_batch_optimized(topic: str, tier: str, count: int, enriched_prompt: str, 
                                  batch_request_id: str, start_index: int) -> list:
    """Generate a single batch of questions with optimized prompting."""
    import random
    import hashlib
    
    # Create unique seed for this batch
    seed_string = f"{batch_request_id}_{time.time()}_{random.random()}"
    seed_hash = hashlib.md5(seed_string.encode()).hexdigest()[:8]
    
    # Optimized prompt for faster generation
    prompt = f"""Generate {count} GCSE Mathematics exam questions for {tier} tier on {topic}.

SPEED OPTIMIZATION: Generate questions efficiently with clear structure.
Seed: {seed_hash}

{enriched_prompt if enriched_prompt else ''}

REQUIREMENTS:
- Each question must be unique and exam-appropriate
- Use realistic contexts and varied numerical values
- Appropriate difficulty for {tier} tier
- Clear, concise question text

Return ONLY this JSON array:
[
  {{
    "question_text": "Question text here",
    "marks": 4,
    "difficulty_score": 5,
    "answer": "Solution with final answer"
  }}
]"""

    try:
        # Call Bedrock with optimized settings for speed
        response = bedrock_service.call_bedrock_with_retry(
            prompt, batch_request_id, 
            temperature=0.7,
            max_tokens=4000  # Limit tokens for faster response
        )
        
        # Parse the response
        questions = parse_bedrock_response_optimized(response, topic, tier, batch_request_id, start_index)
        
        return questions
        
    except Exception as e:
        logger.error(f"Batch generation failed for {batch_request_id}: {str(e)}")
        # Return fallback questions for this batch
        return generate_fallback_questions(topic, tier, count, batch_request_id, start_index)


def parse_bedrock_response_optimized(response: str, topic: str, tier: str, 
                                   request_id: str, start_index: int) -> list:
    """Optimized parsing with better error handling."""
    import re
    
    try:
        # Clean control characters (Haiku fix)
        cleaned_response = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', response)
        
        # Extract JSON array
        json_match = re.search(r'\[[\s\S]*?\]', cleaned_response)
        if json_match:
            json_str = json_match.group()
        else:
            # Try to find individual question objects
            question_matches = re.findall(r'\{[^}]*"question_text"[^}]*\}', cleaned_response)
            if question_matches:
                json_str = '[' + ','.join(question_matches) + ']'
            else:
                raise ValueError("No valid JSON found in response")
        
        # Parse JSON
        questions_data = json.loads(json_str)
        
        questions = []
        for i, q in enumerate(questions_data):
            question = {
                'id': f'q_{request_id}_{start_index + i}',
                'question_text': q.get('question_text', q.get('text', f'Question {start_index + i + 1}')),
                'text': q.get('question_text', q.get('text', f'Question {start_index + i + 1}')),
                'marks': q.get('marks', 4),
                'topic': topic,
                'tier': tier,
                'difficulty_score': q.get('difficulty_score', 5),
                'answer': q.get('answer', 'Answer not provided')
            }
            questions.append(question)
        
        return questions
        
    except Exception as e:
        logger.warning(f"Failed to parse Bedrock response: {str(e)}")
        # Return minimal fallback
        return [{
            'id': f'q_{request_id}_{start_index}',
            'question_text': f'Sample {tier} {topic} question',
            'text': f'Sample {tier} {topic} question',
            'marks': 4,
            'topic': topic,
            'tier': tier,
            'difficulty_score': 5,
            'answer': 'Please regenerate for proper question'
        }]


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
        # Don't raise here to avoid breaking the main flow


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
        if answer and answer != "This is a placeholder question. Please try generating again.":
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