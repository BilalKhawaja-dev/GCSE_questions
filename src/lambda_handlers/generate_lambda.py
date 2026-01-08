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
    AWS Lambda handler for question generation with async support for large requests.
    """
    import uuid
    from datetime import datetime
    
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    logger.info(f"GenerateLambda invocation started - Request ID: {request_id}")
    
    # Check if this is an async processing invocation
    if event.get('async_processing'):
        return handle_async_processing(event, context)
    
    try:
        # Parse request body first
        if 'body' not in event or not event['body']:
            return create_error_response(400, "Request body is required", request_id)
        
        try:
            body = json.loads(event['body'])
        except json.JSONDecodeError:
            return create_error_response(400, "Invalid JSON in request body", request_id)
        
        # Get user info - handle both API Gateway and Function URL requests
        authorizer_context = event.get('requestContext', {}).get('authorizer', {})
        user_id = authorizer_context.get('user_id') or body.get('user_id')
        session_token = authorizer_context.get('session_token') or body.get('session_token')
        
        # Basic auth check
        if not user_id or not session_token:
            return create_error_response(401, "Authentication required", request_id)
        
        # Extract required fields
        topic = body.get('topic')
        tier = body.get('tier')
        count = body.get('count', 1)
        enriched_prompt = body.get('enriched_prompt', '')
        async_mode = body.get('async', False)  # Allow client to request async mode
        
        # Basic validation
        if not all([topic, tier]):
            return create_error_response(400, "Missing required fields: topic, tier", request_id)
        
        if count < 1 or count > 50:
            return create_error_response(400, "Count must be between 1 and 50", request_id)
        
        # Determine if we should use async mode based on count or explicit request
        # Use async processing for requests > 8 questions via SQS
        # Keep threshold low to avoid API Gateway timeouts
        use_async = count > 8 or async_mode
        
        if use_async:
            # For large requests, send to SQS and return immediately with job ID
            return handle_async_generation_sqs(
                topic=topic,
                tier=tier,
                count=count,
                enriched_prompt=enriched_prompt,
                user_id=user_id,
                request_id=request_id
            )
        
        # For smaller requests, process synchronously
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


def handle_async_processing(event, context):
    """
    Handle async processing invocation from Lambda.
    """
    import time
    from datetime import datetime
    
    job_id = event.get('job_id')
    session_id = event.get('session_id')
    topic = event.get('topic')
    tier = event.get('tier')
    count = event.get('count')
    enriched_prompt = event.get('enriched_prompt', '')
    user_id = event.get('user_id')
    request_id = event.get('request_id')
    
    logger.info(f"Processing async job {job_id} for {count} questions")
    
    try:
        from src.services.session_service import SessionService
        session_service = SessionService(region=AWS_REGION)
        
        # Update job status to processing
        job_metadata = {
            'job_id': job_id,
            'status': 'processing',
            'topic': topic,
            'tier': tier,
            'count': count,
            'progress': 10,
            'started_at': datetime.utcnow().isoformat()
        }
        
        session_service.update_session_questions(
            session_id=session_id,
            questions=[],
            metadata=job_metadata
        )
        
        # Generate questions
        questions = generate_questions_with_bedrock(
            topic=topic,
            tier=tier,
            count=count,
            enriched_prompt=enriched_prompt,
            request_id=request_id
        )
        
        # Generate mark schemes
        mark_schemes = generate_mark_schemes(questions)
        
        # Update job with results
        job_metadata.update({
            'status': 'completed',
            'progress': 100,
            'completed_at': datetime.utcnow().isoformat(),
            'question_count': len(questions),
            'total_marks': sum(q.get('marks', 0) for q in questions)
        })
        
        # Update session with final results
        session_service.update_session_questions(
            session_id=session_id,
            questions=questions,
            metadata=job_metadata
        )
        
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
                    subtopic=topic.lower(),
                    question_count=len(questions),
                    session_id=session_id,
                    request_id=request_id
                )
                logger.info(f"Topic coverage recorded for {topic}")
        except Exception as e:
            logger.warning(f"Failed to record topic coverage (non-critical): {str(e)}")
        
        logger.info(f"Async generation completed - Job ID: {job_id}, Questions: {len(questions)}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'job_id': job_id,
                'session_id': session_id,
                'questions_generated': len(questions)
            })
        }
        
    except Exception as e:
        logger.error(f"Async generation failed - Job ID: {job_id}, Error: {str(e)}")
        
        try:
            # Update job with error status
            job_metadata = {
                'job_id': job_id,
                'status': 'failed',
                'error': str(e),
                'completed_at': datetime.utcnow().isoformat()
            }
            
            # Generate fallback questions
            fallback_questions = generate_fallback_questions(topic, tier, min(count, 10), request_id)
            
            session_service.update_session_questions(
                session_id=session_id,
                questions=fallback_questions,
                metadata=job_metadata
            )
            
            logger.info(f"Fallback questions generated for failed job {job_id}")
            
        except Exception as update_error:
            logger.error(f"Failed to update job status: {str(update_error)}")
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'job_id': job_id,
                'error': str(e)
            })
        }


def handle_async_generation_sqs(topic: str, tier: str, count: int, enriched_prompt: str, user_id: str, request_id: str) -> dict:
    """
    Handle asynchronous question generation using SQS.
    Sends message to SQS queue and returns immediately with job ID.
    """
    import boto3
    from datetime import datetime, timedelta
    
    logger.info(f"Starting async generation via SQS for {count} questions - Request ID: {request_id}")
    
    # Create a job ID for tracking
    job_id = f"job_{request_id}"
    
    try:
        from src.services.session_service import SessionService
        session_service = SessionService(region=AWS_REGION)
        
        # Create initial job record with pending status
        job_metadata = {
            'job_id': job_id,
            'status': 'pending',
            'topic': topic,
            'tier': tier,
            'count': count,
            'progress': 0,
            'created_at': datetime.utcnow().isoformat(),
            'estimated_completion': (datetime.utcnow() + timedelta(minutes=3)).isoformat()
        }
        
        # Create session to track job
        session_id = session_service.create_session(
            user_id=user_id,
            query=f"Async generation: {count} {tier} {topic} questions",
            generated_questions=[],  # Empty initially
            metadata=job_metadata,
            request_id=request_id
        )
        
        # Send message to SQS queue
        sqs_client = boto3.client('sqs', region_name=AWS_REGION)
        queue_url = os.environ.get('ASYNC_QUEUE_URL')
        
        if not queue_url:
            raise ValueError("ASYNC_QUEUE_URL environment variable not set")
        
        message_body = {
            'job_id': job_id,
            'session_id': session_id,
            'topic': topic,
            'tier': tier,
            'count': count,
            'enriched_prompt': enriched_prompt,
            'user_id': user_id,
            'request_id': request_id
        }
        
        response = sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message_body),
            MessageAttributes={
                'job_id': {
                    'StringValue': job_id,
                    'DataType': 'String'
                },
                'user_id': {
                    'StringValue': user_id,
                    'DataType': 'String'
                }
            }
        )
        
        logger.info(f"Message sent to SQS - Job ID: {job_id}, Message ID: {response['MessageId']}")
        
        # Return immediately with job information
        response_body = {
            'success': True,
            'async': True,
            'job_id': job_id,
            'session_id': session_id,
            'status': 'pending',
            'estimated_completion_minutes': 3,
            'progress': 0,
            'message': f'Large request ({count} questions) is being processed asynchronously. Use the session_id to check status.',
            'polling_info': {
                'check_status_endpoint': f'/user/sessions/{session_id}',
                'recommended_poll_interval_seconds': 5,
                'max_wait_time_minutes': 5
            },
            'request_id': request_id,
            'generated_at': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Async job created via SQS - Job ID: {job_id}, Session ID: {session_id}")
        
        return {
            'statusCode': 202,  # Accepted - processing asynchronously
            'headers': {
                'Content-Type': 'application/json',
                **get_cors_response_headers(methods='POST,OPTIONS')
            },
            'body': json.dumps(response_body)
        }
        
    except Exception as e:
        logger.error(f"Failed to create async job via SQS: {str(e)}")
        return create_error_response(500, f"Failed to start async processing: {str(e)}", request_id)


def handle_async_generation(topic: str, tier: str, count: int, enriched_prompt: str, user_id: str, request_id: str) -> dict:
    """
    Handle asynchronous question generation for large requests.
    Returns immediately with a job ID, processes in background using Lambda async invoke.
    """
    import boto3
    from datetime import datetime, timedelta
    
    logger.info(f"Starting async generation for {count} questions - Request ID: {request_id}")
    
    # Create a job ID for tracking
    job_id = f"job_{request_id}"
    
    # Store initial job status in DynamoDB for tracking
    try:
        from src.services.session_service import SessionService
        session_service = SessionService(region=AWS_REGION)
        
        # Create initial job record with processing status
        job_metadata = {
            'job_id': job_id,
            'status': 'processing',
            'topic': topic,
            'tier': tier,
            'count': count,
            'progress': 0,
            'created_at': datetime.utcnow().isoformat(),
            'estimated_completion': (datetime.utcnow() + timedelta(minutes=2)).isoformat()
        }
        
        # Store job status (we'll use sessions table for simplicity)
        session_id = session_service.create_session(
            user_id=user_id,
            query=f"Async generation: {count} {tier} {topic} questions",
            generated_questions=[],  # Empty initially
            metadata=job_metadata,
            request_id=request_id
        )
        
        # Invoke Lambda asynchronously to process the request
        try:
            lambda_client = boto3.client('lambda', region_name=AWS_REGION)
            
            # Prepare payload for async processing
            async_payload = {
                'async_processing': True,
                'job_id': job_id,
                'session_id': session_id,
                'topic': topic,
                'tier': tier,
                'count': count,
                'enriched_prompt': enriched_prompt,
                'user_id': user_id,
                'request_id': request_id
            }
            
            # Get current Lambda function name from context
            function_name = f"gcse-generate-lambda-{os.environ.get('ENVIRONMENT', 'dev')}"
            
            # Invoke Lambda asynchronously
            lambda_client.invoke(
                FunctionName=function_name,
                InvocationType='Event',  # Async invocation
                Payload=json.dumps(async_payload)
            )
            
            logger.info(f"Async Lambda invoked for job {job_id}")
            
        except Exception as e:
            logger.error(f"Failed to invoke async Lambda: {str(e)}")
            
            # Update job with error status
            job_metadata.update({
                'status': 'failed',
                'error': f'Failed to start async processing: {str(e)}',
                'completed_at': datetime.utcnow().isoformat()
            })
            
            session_service.update_session_questions(
                session_id=session_id,
                questions=[],
                metadata=job_metadata
            )
        
        # Small delay to ensure DynamoDB write completes (eventual consistency)
        time.sleep(0.5)
        
        # Verify session was created
        try:
            verify_session = session_service.get_session_details(session_id, user_id)
            if not verify_session:
                logger.error(f"Session {session_id} not found immediately after creation")
        except Exception as e:
            logger.warning(f"Could not verify session creation: {str(e)}")
        
        # Return immediately with job information
        response_body = {
            'success': True,
            'async': True,
            'job_id': job_id,
            'session_id': session_id,
            'status': 'processing',
            'estimated_completion_minutes': 2,
            'progress': 0,
            'message': f'Large request ({count} questions) is being processed asynchronously. Use the session_id to check status.',
            'polling_info': {
                'check_status_endpoint': f'/user/sessions/{session_id}',
                'recommended_poll_interval_seconds': 10,
                'max_wait_time_minutes': 3
            },
            'request_id': request_id,
            'generated_at': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Async job created - Job ID: {job_id}, Session ID: {session_id}")
        
        return {
            'statusCode': 202,  # Accepted - processing asynchronously
            'headers': {
                'Content-Type': 'application/json',
                **get_cors_response_headers(methods='POST,OPTIONS')
            },
            'body': json.dumps(response_body)
        }
        
    except Exception as e:
        logger.error(f"Failed to create async job: {str(e)}")
        return create_error_response(500, f"Failed to start async processing: {str(e)}", request_id)


def generate_questions_with_bedrock(topic: str, tier: str, count: int, enriched_prompt: str, request_id: str) -> list:
    """Generate questions using Bedrock Claude with timeout handling."""
    
    # Import timeout handling
    from src.utils.timeout_handler import (
        create_lambda_timeout_handler, 
        handle_question_generation_timeout,
        monitor_operation_progress
    )
    
    # Create timeout handler with buffer for Lambda context
    import time
    start_time = time.time()
    
    # For large question counts, use batch processing
    if count > 10:
        return generate_questions_in_batches(topic, tier, count, enriched_prompt, request_id)
    
    # Build the prompt for question generation with answers and randomization
    import random
    import hashlib
    
    # Create a unique seed based on request_id and timestamp for variety
    seed_string = f"{request_id}_{time.time()}_{random.random()}"
    seed_hash = hashlib.md5(seed_string.encode()).hexdigest()[:8]
    
    # Add Edexcel specification context
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
        # Call Bedrock to generate questions with higher temperature for variety
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
        raise


def generate_questions_in_batches(topic: str, tier: str, count: int, enriched_prompt: str, request_id: str) -> list:
    """Generate questions in batches to handle large requests and avoid timeouts."""
    
    from src.utils.timeout_handler import (
        TimeoutHandler, TimeoutConfig, TimeoutStrategy,
        monitor_operation_progress
    )
    import time
    
    # Configure timeout handler for batch processing
    config = TimeoutConfig(
        total_timeout_seconds=280,  # Leave 20 seconds buffer for Lambda
        strategy=TimeoutStrategy.PARTIAL_RESULTS,
        warning_threshold_percent=0.7,
        critical_threshold_percent=0.85
    )
    
    timeout_handler = TimeoutHandler(config)
    
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
    
    # Progress monitor
    progress_monitor = monitor_operation_progress(
        "batch_question_generation", 
        len(batches), 
        timeout_handler
    )
    
    for batch_idx, (start_idx, end_idx) in enumerate(batches):
        batch_count = end_idx - start_idx
        
        # Check timeout before processing batch
        if timeout_handler.is_timeout_approaching(buffer_seconds=30):
            logger.warning(f"Timeout approaching, stopping at batch {batch_idx + 1}/{len(batches)}")
            break
        
        try:
            logger.info(f"Processing batch {batch_idx + 1}/{len(batches)}: questions {start_idx + 1}-{end_idx}")
            
            # Generate batch with modified prompt for variety and uniqueness
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
            
            # Update progress
            can_continue = progress_monitor(
                batch_idx + 1, 
                partial_results=all_questions,
                can_return_partial=True
            )
            
            if not can_continue:
                logger.warning(f"Timeout detected, returning partial results: {len(all_questions)} questions")
                break
                
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
    """Generate a single batch of questions with randomization and Edexcel spec alignment."""
    
    import random
    import hashlib
    import time
    
    # Create unique seed for this batch
    seed_string = f"{batch_request_id}_{time.time()}_{random.random()}"
    seed_hash = hashlib.md5(seed_string.encode()).hexdigest()[:8]
    
    # Build batch-specific prompt with variety instructions and Edexcel spec
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
        # Call Bedrock for this batch with higher temperature for variety
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
