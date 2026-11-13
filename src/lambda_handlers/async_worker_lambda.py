"""
AsyncWorkerLambda handler for processing async question generation from SQS.
"""

import json
import logging
import os
import time
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
KNOWLEDGE_BASE_ID = os.environ.get('KNOWLEDGE_BASE_ID')

# Initialize services
bedrock_service = BedrockService(region=AWS_REGION, knowledge_base_id=KNOWLEDGE_BASE_ID)
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
2. The number of marks - MUST match question complexity:
   - 2 marks: Simple, single-step calculation
   - 3 marks: Two-step problem or requires showing working
   - 4 marks: Multi-step problem with reasoning
   - 5 marks: Complex problem requiring multiple methods
   - 6 marks: Extended problem with justification/proof
3. A difficulty score from 1-10 ({tier} tier: {'1-5' if tier == 'Foundation' else '6-10'})
4. The correct answer with full working/solution

CRITICAL MARK ALLOCATION:
- Higher marks = More complex questions with multiple steps
- Lower marks = Simpler, more direct questions
- Question complexity MUST justify the mark value
- Vary marks across the set (don't use same value for all)

Return the questions as a JSON array with this structure:
[
  {{
    "question_text": "Simple calculation question (2 marks)",
    "marks": 2,
    "difficulty_score": 3,
    "answer": "Direct answer with brief working"
  }},
  {{
    "question_text": "Multi-step problem requiring reasoning and showing all working (5 marks)",
    "marks": 5,
    "difficulty_score": 7,
    "answer": "Detailed step-by-step solution with justification"
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
- VARY difficulty within the {tier} tier range (grades {'1-5' if tier == 'Foundation' else '4-9'})
- VARY marks allocation (2, 3, 4, 5, or 6 marks - NOT always 4!)
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
    """Parse Bedrock response into question objects with improved error handling."""
    import re
    
    try:
        # Log the raw response for debugging
        logger.info(f"Parsing Bedrock response (length: {len(response)} chars)")
        logger.debug(f"Raw response preview: {response[:500]}")
        
        # Clean control characters from response (Haiku sometimes includes them)
        cleaned_response = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', response)
        
        # Look for JSON array in the response
        json_match = re.search(r'\[[\s\S]*\]', cleaned_response)
        if json_match:
            json_str = json_match.group()
        else:
            # Try to extract just the JSON part if wrapped in text
            json_str = cleaned_response.strip()
            if not json_str.startswith('['):
                # Look for array start
                start_idx = json_str.find('[')
                end_idx = json_str.rfind(']')
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = json_str[start_idx:end_idx+1]
                else:
                    logger.error(f"No JSON array found in response")
                    raise ValueError("No JSON array found in Bedrock response")
        
        # Parse JSON
        questions_data = json.loads(json_str)
        
        if not isinstance(questions_data, list):
            logger.error(f"Parsed data is not a list: {type(questions_data)}")
            raise ValueError("Bedrock response is not a JSON array")
        
        if len(questions_data) == 0:
            logger.error("Bedrock returned empty array")
            raise ValueError("Bedrock returned no questions")
        
        questions = []
        for i, q in enumerate(questions_data):
            # Validate question has required fields
            question_text = q.get('question_text', q.get('text', ''))
            
            if not question_text or len(question_text) < 10:
                logger.warning(f"Question {i} has invalid or missing text")
                continue
            
            question = {
                'id': f'q_{request_id}_{i}',
                'question_text': question_text,
                'text': question_text,
                'marks': q.get('marks', 4),
                'topic': topic,
                'tier': tier,
                'difficulty_score': q.get('difficulty_score', 5),
                'answer': q.get('answer', '')
            }
            questions.append(question)
        
        if len(questions) == 0:
            logger.error("No valid questions after parsing")
            raise ValueError("No valid questions in Bedrock response")
        
        logger.info(f"Successfully parsed {len(questions)} questions from Bedrock")
        return questions
        
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.error(f"Failed to parse Bedrock response: {str(e)}")
        logger.error(f"Response preview: {response[:1000]}")
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
    base_prompt = f"""Generate {count} GCSE Mathematics exam questions for {tier} tier on {topic}.

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

    # Enrich with Knowledge Base content
    prompt = bedrock_service.enrich_prompt_with_kb(
        base_prompt=base_prompt,
        topic=topic,
        tier=tier,
        request_id=batch_request_id
    )

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
    """Optimized parsing with robust error handling and JSON repair."""
    import re
    import json
    
    try:
        logger.info(f"Parsing Bedrock response (length: {len(response)} chars)")
        
        # Clean control characters (Haiku fix)
        cleaned_response = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', response)
        
        # Strategy 1: Try to parse complete JSON array
        json_match = re.search(r'\[[\s\S]*?\]', cleaned_response)
        if json_match:
            json_str = json_match.group()
            
            # Try to fix common JSON errors
            # Remove trailing commas
            json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
            # Fix missing commas between objects
            json_str = re.sub(r'}\s*{', '},{', json_str)
            
            try:
                questions_data = json.loads(json_str)
                if isinstance(questions_data, list) and len(questions_data) > 0:
                    return build_valid_questions(questions_data, topic, tier, request_id, start_index)
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parse failed even after fixes: {str(e)}")
        
        # Strategy 2: Extract individual question objects
        logger.info("Trying individual question extraction")
        question_pattern = r'\{\s*"question_text"\s*:\s*"[^"]+"\s*,\s*"marks"\s*:\s*\d+\s*,\s*"difficulty_score"\s*:\s*\d+\s*,\s*"answer"\s*:\s*"[^"]+"\s*\}'
        question_matches = re.findall(question_pattern, cleaned_response, re.DOTALL)
        
        if question_matches:
            questions_data = []
            for match in question_matches:
                try:
                    q_obj = json.loads(match)
                    questions_data.append(q_obj)
                except:
                    continue
            
            if len(questions_data) > 0:
                logger.info(f"Extracted {len(questions_data)} questions individually")
                return build_valid_questions(questions_data, topic, tier, request_id, start_index)
        
        # Strategy 3: More lenient extraction
        logger.info("Trying lenient extraction")
        lenient_pattern = r'\{[^{}]*?"question_text"[^{}]*?\}'
        lenient_matches = re.findall(lenient_pattern, cleaned_response)
        
        if lenient_matches:
            questions_data = []
            for match in lenient_matches:
                try:
                    # Try to fix the JSON before parsing
                    fixed_match = re.sub(r',(\s*})', r'\1', match)
                    q_obj = json.loads(fixed_match)
                    if q_obj.get('question_text'):
                        questions_data.append(q_obj)
                except:
                    continue
            
            if len(questions_data) > 0:
                logger.info(f"Lenient extraction succeeded: {len(questions_data)} questions")
                return build_valid_questions(questions_data, topic, tier, request_id, start_index)
        
        # All strategies failed - log and raise
        logger.error(f"All parsing strategies failed")
        logger.error(f"Response preview: {cleaned_response[:1000]}")
        raise ValueError("Could not extract any valid questions from Bedrock response")
        
    except Exception as e:
        logger.error(f"Parse error: {str(e)}")
        raise


def build_valid_questions(questions_data: list, topic: str, tier: str, request_id: str, start_index: int) -> list:
    """Build and validate question objects from parsed data."""
    questions = []
    
    for i, q in enumerate(questions_data):
        # Get question text
        question_text = q.get('question_text', q.get('text', ''))
        
        # Validate question text
        if not question_text or len(question_text) < 10:
            logger.warning(f"Question {i} has invalid text, skipping")
            continue
        
        # Filter out generic placeholders
        generic_phrases = [
            'solve this', 'calculate the answer to this', 'show your working for this',
            'explain your method', 'find the solution to this', 'work out the answer'
        ]
        
        is_generic = any(phrase in question_text.lower() for phrase in generic_phrases)
        if is_generic and len(question_text) < 50:  # Short + generic = placeholder
            logger.warning(f"Question {i} appears to be a placeholder, skipping")
            continue
        
        question = {
            'id': f'q_{request_id}_{start_index + i}',
            'question_text': question_text,
            'text': question_text,
            'marks': q.get('marks', 4),
            'topic': topic,
            'tier': tier,
            'difficulty_score': q.get('difficulty_score', 5),
            'answer': q.get('answer', 'Answer not provided')
        }
        questions.append(question)
    
    if len(questions) == 0:
        raise ValueError("No valid questions after filtering placeholders")
    
    return questions