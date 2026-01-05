"""
InterpretLambda handler for natural language query interpretation.

This Lambda function processes natural language queries from teachers and tutors,
parsing them into structured QueryIntent objects using AWS Bedrock Claude Haiku.
"""

import json
import logging
import os
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

from src.models.query_intent import QueryIntent, EnhancedInterpretResponse
from src.utils.validation import validate_query_input, sanitize_input, sanitize_json_input
from src.utils.security import authenticate_request, check_rate_limit, get_cors_response_headers
from src.utils.constants import VALID_TOPICS, VALID_TIERS, RATE_LIMIT_REQUESTS_PER_HOUR
from src.utils.cache import (
    create_cache_key, get_cached_query_response, cache_query_response, get_cache_metrics
)
from src.services.bedrock_service import BedrockService
from src.services.content_retrieval_service import ContentRetrievalService

# Configure structured logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
BEDROCK_MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-haiku-20240307')
AWS_REGION = os.environ.get('AWS_REGION', 'eu-west-2')
SPECIFICATIONS_BUCKET = os.environ.get('SPECIFICATIONS_BUCKET', 'gcse-generator-v2-specifications')
EXAMPLES_BUCKET = os.environ.get('EXAMPLES_BUCKET', 'gcse-generator-v2-examples')

# Initialize services
bedrock_service = BedrockService(region=AWS_REGION)
content_service = ContentRetrievalService(
    specifications_bucket=SPECIFICATIONS_BUCKET,
    examples_bucket=EXAMPLES_BUCKET,
    region=AWS_REGION
)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for query interpretation.
    
    Args:
        event: API Gateway event containing the query
        context: Lambda context object
        
    Returns:
        API Gateway response with structured intent or error
    """
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    # Set up structured logging context
    logger.info(
        "InterpretLambda invocation started",
        extra={
            "request_id": request_id,
            "function_name": context.function_name,
            "aws_request_id": context.aws_request_id,
            "timestamp": datetime.utcnow().isoformat(),
            "remaining_time_ms": context.get_remaining_time_in_millis()
        }
    )
    
    try:
        # Check timeout early in execution
        if _is_approaching_timeout(context, buffer_seconds=5):
            return _create_timeout_error_response(request_id, "InterpretLambda")
        
        # Get user info from API Gateway authorizer context
        authorizer_context = event.get('requestContext', {}).get('authorizer', {})
        user_id = authorizer_context.get('user_id')
        session_token = authorizer_context.get('session_token')
        
        if not user_id:
            return _create_error_response(
                401,
                "AuthenticationError",
                "User not authenticated",
                "Authentication required to access this resource",
                request_id
            )
        
        # Use user_id for rate limiting with error handling
        try:
            is_allowed, rate_limit_headers = check_rate_limit(user_id)
        except Exception as rate_limit_error:
            logger.warning(
                "Rate limit check failed, allowing request",
                extra={
                    "request_id": request_id,
                    "error": str(rate_limit_error),
                    "error_type": type(rate_limit_error).__name__
                }
            )
            is_allowed = True
            rate_limit_headers = {}
        
        if not is_allowed:
            return _create_error_response(
                429,
                "RateLimitExceeded",
                "Too many requests",
                f"Rate limit of {RATE_LIMIT_REQUESTS_PER_HOUR} requests per hour exceeded",
                request_id,
                extra_headers=rate_limit_headers
            )
        
        # Check if this is a cache metrics request
        if event.get('httpMethod') == 'GET' and event.get('path', '').endswith('/cache-metrics'):
            return _handle_cache_metrics_request(request_id, rate_limit_headers)
        
        # Parse and sanitize request body
        body = _parse_request_body(event)
        body = sanitize_json_input(body)  # Sanitize the entire JSON input
        query = body.get('query', '').strip()
        
        if not query:
            return _create_error_response(
                400,
                "ValidationError",
                "Query is required",
                "Please provide a non-empty query",
                request_id
            )
        
        logger.info(
            "Processing query",
            extra={
                "request_id": request_id,
                "query_length": len(query),
                "query_preview": query[:50] + "..." if len(query) > 50 else query,
                "user_id": user_id,
                "remaining_time_ms": context.get_remaining_time_in_millis()
            }
        )
        
        # Check timeout before validation
        if _is_approaching_timeout(context, buffer_seconds=3):
            return _create_timeout_error_response(request_id, "InterpretLambda")
        
        # Validate and sanitize input
        try:
            validation_result = validate_query_input(query)
            sanitized_query = validation_result['sanitized_query']
        except ValueError as e:
            logger.warning(
                "Query validation failed",
                extra={
                    "request_id": request_id,
                    "validation_error": str(e),
                    "query_length": len(query)
                }
            )
            return _create_error_response(
                400,
                "ValidationError",
                str(e),
                "Please check your query and try again",
                request_id
            )
        
        # Check cache for existing response (include user context in V2)
        cache_key_data = {'query': sanitized_query}
        if user_id:
            cache_key_data['user_id'] = user_id
        cache_key = create_cache_key(cache_key_data)
        cached_response = get_cached_query_response(cache_key)
        
        if cached_response:
            logger.info(
                "Returning cached query interpretation",
                extra={
                    "request_id": request_id,
                    "cache_key": cache_key[:16] + "...",
                    "topic": cached_response.get('intent', {}).get('topic'),
                    "tier": cached_response.get('intent', {}).get('tier'),
                    "execution_time_ms": int((time.time() - start_time) * 1000)
                }
            )
            
            # Update response with current request metadata
            cached_response['request_id'] = request_id
            cached_response['timestamp'] = datetime.utcnow().isoformat()
            
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    **get_cors_response_headers(methods='POST,OPTIONS'),
                    "X-Request-ID": request_id,
                    "X-Cache-Status": "HIT",
                    **rate_limit_headers
                },
                "body": json.dumps(cached_response)
            }
        
        # Check timeout before expensive Bedrock call
        if _is_approaching_timeout(context, buffer_seconds=2):
            return _create_timeout_error_response(request_id, "InterpretLambda")
        
        # Process query with Bedrock - ALWAYS calls Bedrock (no caching at this level)
        logger.info(
            "Calling Bedrock Haiku for query interpretation",
            extra={
                "request_id": request_id,
                "cache_status": "MISS - calling Bedrock",
                "model_id": BEDROCK_MODEL_ID
            }
        )
        
        try:
            enhanced_response = _process_query_with_enhanced_bedrock(
                sanitized_query, user_id, session_token, request_id
            )
        except Exception as e:
            logger.error(
                "Query processing failed",
                extra={
                    "request_id": request_id,
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            )
            return _create_error_response(
                500,
                "InternalError",
                "Failed to process query",
                "Please try again later",
                request_id
            )
        
        # Prepare response data (V2 enhanced structure)
        response_data = enhanced_response.to_dict()
        
        # Cache the response
        cache_query_response(cache_key, response_data)
        
        # Log successful processing
        execution_time_ms = int((time.time() - start_time) * 1000)
        logger.info(
            "Query processed successfully",
            extra={
                "request_id": request_id,
                "topic": enhanced_response.intent.topic,
                "tier": enhanced_response.intent.tier,
                "count": enhanced_response.intent.count,
                "confidence": enhanced_response.intent.confidence,
                "has_enriched_prompt": bool(enhanced_response.enriched_prompt),
                "cached": True,
                "bedrock_model": BEDROCK_MODEL_ID,
                "bedrock_call_successful": True,
                "execution_time_ms": execution_time_ms
            }
        )
        
        # Return successful response
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                **get_cors_response_headers(methods='POST,OPTIONS'),
                "X-Request-ID": request_id,
                "X-Cache-Status": "MISS",
                **rate_limit_headers
            },
            "body": json.dumps(response_data)
        }
        
    except Exception as e:
        logger.error(
            "Unexpected error in InterpretLambda",
            extra={
                "request_id": request_id,
                "error": str(e),
                "error_type": type(e).__name__,
                "execution_time_ms": int((time.time() - start_time) * 1000)
            }
        )
        return _create_error_response(
            500,
            "InternalError",
            "An unexpected error occurred",
            "Please try again later",
            request_id
        )


def _parse_request_body(event: Dict[str, Any]) -> Dict[str, Any]:
    """Parse and validate the request body from API Gateway event."""
    try:
        if 'body' not in event or event['body'] is None:
            raise ValueError("Missing request body")
        
        body = event['body']
        if isinstance(body, str):
            body = json.loads(body)
        
        if not isinstance(body, dict):
            raise ValueError("Request body must be a JSON object")
        
        return body
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON in request body")
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Failed to parse request body: {str(e)}")


def _process_query_with_enhanced_bedrock(
    query: str, user_id: str, session_token: str, request_id: str
) -> EnhancedInterpretResponse:
    """
    Process query with enhanced Bedrock Claude Haiku including prompt enrichment.
    
    Args:
        query: Sanitized natural language query
        user_id: User ID for personalization (optional)
        session_token: Session token for authentication (optional)
        request_id: Request ID for logging
        
    Returns:
        EnhancedInterpretResponse with parsed components and enriched prompt
        
    Raises:
        Exception: If processing fails
    """
    # Step 1: Parse query with Bedrock Haiku (existing functionality)
    intent = bedrock_service.parse_query_with_haiku(query, request_id)
    
    # Step 2: Retrieve specification content for prompt enrichment
    try:
        spec_content = content_service.get_specification_content(
            topic=intent.topic,
            subtopic=intent.subtopic,
            tier=intent.tier,
            request_id=request_id
        )
        
        # Also try to get examples content for additional context
        try:
            examples_content = content_service.get_examples_content(
                topic=intent.topic,
                subtopic=intent.subtopic,
                tier=intent.tier,
                request_id=request_id
            )
        except Exception as e:
            logger.warning(
                "Failed to retrieve examples content, continuing without examples",
                extra={"request_id": request_id, "error": str(e)}
            )
            examples_content = []
            
    except Exception as e:
        logger.warning(
            "Failed to retrieve specification content, using minimal enrichment",
            extra={
                "request_id": request_id,
                "topic": intent.topic,
                "error": str(e)
            }
        )
        spec_content = {
            "learning_objectives": [],
            "assessment_objectives": [],
            "common_misconceptions": [],
            "key_concepts": []
        }
        examples_content = []
    
    # Step 3: Build enriched prompt with examples
    enriched_prompt = _build_enriched_prompt(intent, spec_content, examples_content, request_id)
    
    # Step 4: Generate difficulty guidance
    difficulty_guidance = _generate_difficulty_guidance(intent, request_id)
    
    # Step 5: Prepare topic coverage data (placeholder for now)
    topic_coverage = _prepare_topic_coverage(intent, user_id, request_id)
    
    # Step 6: Extract specification context with teacher-specific features
    specification_context = {
        "learning_objectives": spec_content.get("learning_objectives", []),
        "assessment_objectives": _enhance_assessment_objectives(spec_content.get("assessment_objectives", [])),
        "common_misconceptions": spec_content.get("common_misconceptions", []),
        "key_concepts": spec_content.get("key_concepts", []),
        "teacher_guidance": _generate_teacher_guidance(intent, spec_content, request_id),
        "curriculum_links": _generate_curriculum_links(intent.topic, intent.tier),
        "differentiation_strategies": _generate_differentiation_strategies(intent.tier, intent.count)
    }
    
    # Step 7: Create enhanced response
    enhanced_response = EnhancedInterpretResponse(
        intent=intent,
        enriched_prompt=enriched_prompt,
        difficulty_guidance=difficulty_guidance,
        topic_coverage=topic_coverage,
        specification_context=specification_context,
        request_id=request_id,
        timestamp=datetime.utcnow().isoformat()
    )
    
    logger.info(
        "Enhanced query processing completed",
        extra={
            "request_id": request_id,
            "topic": intent.topic,
            "tier": intent.tier,
            "enriched_prompt_length": len(enriched_prompt),
            "has_spec_content": bool(spec_content.get("learning_objectives"))
        }
    )
    
    return enhanced_response


def _create_error_response(
    status_code: int,
    error_type: str,
    message: str,
    guidance: str,
    request_id: str,
    details: Optional[str] = None,
    extra_headers: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """Create standardized error response."""
    error_response = {
        "error": {
            "type": error_type,
            "message": message,
            "guidance": guidance,
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    }
    
    if details:
        error_response["error"]["details"] = details
    
    if status_code == 429:
        error_response["error"]["retry_after"] = 60
    
    headers = {
        "Content-Type": "application/json",
        **get_cors_response_headers(methods='POST,OPTIONS'),
        "X-Request-ID": request_id
    }
    
    # Add extra headers if provided (e.g., rate limit headers)
    if extra_headers:
        headers.update(extra_headers)
    
    return {
        "statusCode": status_code,
        "headers": headers,
        "body": json.dumps(error_response)
    }


def _handle_cache_metrics_request(request_id: str, rate_limit_headers: Dict[str, str]) -> Dict[str, Any]:
    """Handle cache metrics request for monitoring."""
    try:
        metrics = get_cache_metrics()
        
        logger.info(
            "Cache metrics requested",
            extra={
                "request_id": request_id,
                "query_hit_ratio": metrics['query_cache']['hit_ratio'],
                "generation_hit_ratio": metrics['generation_cache']['hit_ratio']
            }
        )
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                **get_cors_response_headers(methods='POST,OPTIONS'),
                "X-Request-ID": request_id,
                **rate_limit_headers
            },
            "body": json.dumps(metrics)
        }
    except Exception as e:
        logger.error(
            "Failed to retrieve cache metrics",
            extra={
                "request_id": request_id,
                "error": str(e)
            }
        )
        return _create_error_response(
            500,
            "InternalError",
            "Failed to retrieve cache metrics",
            "Please try again later",
            request_id,
            extra_headers=rate_limit_headers
        )


def _is_approaching_timeout(context: Any, buffer_seconds: int = 2) -> bool:
    """
    Check if Lambda execution is approaching timeout.
    
    Args:
        context: Lambda context object
        buffer_seconds: Buffer time in seconds before timeout
        
    Returns:
        True if approaching timeout, False otherwise
    """
    remaining_time_ms = context.get_remaining_time_in_millis()
    buffer_time_ms = buffer_seconds * 1000
    
    return remaining_time_ms <= buffer_time_ms


def _build_enriched_prompt(
    intent: QueryIntent, 
    spec_content: Dict[str, Any], 
    examples_content: List[Dict[str, Any]], 
    request_id: str
) -> str:
    """
    Build enriched prompt with specification context and examples for GenerateLambda.
    
    Args:
        intent: Parsed query intent
        spec_content: Specification content from S3
        examples_content: Example questions from S3
        request_id: Request ID for logging
        
    Returns:
        Enriched prompt string with specification context and examples
    """
    learning_objectives = spec_content.get("learning_objectives", [])
    assessment_objectives = spec_content.get("assessment_objectives", [])
    common_misconceptions = spec_content.get("common_misconceptions", [])
    key_concepts = spec_content.get("key_concepts", [])
    
    enriched_prompt = f"""Generate {intent.count} GCSE Mathematics questions for {intent.tier} tier on the topic of {intent.topic}"""
    
    if intent.subtopic:
        enriched_prompt += f", specifically focusing on {intent.subtopic}"
    
    enriched_prompt += ".\n\n"
    
    # Add specification context
    if learning_objectives:
        enriched_prompt += "Learning Objectives to address:\n"
        for i, objective in enumerate(learning_objectives[:5], 1):  # Limit to 5 objectives
            enriched_prompt += f"{i}. {objective}\n"
        enriched_prompt += "\n"
    
    if assessment_objectives:
        enriched_prompt += "Assessment Objectives (AO1: Use techniques, AO2: Reason mathematically, AO3: Solve problems):\n"
        if isinstance(assessment_objectives, dict):
            for ao, description in assessment_objectives.items():
                enriched_prompt += f"- {ao}: {description}\n"
        elif isinstance(assessment_objectives, list):
            for ao in assessment_objectives:
                enriched_prompt += f"- {ao}\n"
        enriched_prompt += "\n"
    
    if common_misconceptions:
        enriched_prompt += "Common Misconceptions to avoid or address:\n"
        for i, misconception in enumerate(common_misconceptions[:3], 1):  # Limit to 3 misconceptions
            enriched_prompt += f"{i}. {misconception}\n"
        enriched_prompt += "\n"
    
    if key_concepts:
        enriched_prompt += "Key Concepts to incorporate:\n"
        for i, concept in enumerate(key_concepts[:5], 1):  # Limit to 5 concepts
            enriched_prompt += f"{i}. {concept}\n"
        enriched_prompt += "\n"
    
    # Add example questions if available
    if examples_content:
        enriched_prompt += "Example Questions for Reference (maintain similar style and difficulty):\n"
        for i, example in enumerate(examples_content[:2], 1):  # Limit to 2 examples
            question = example.get('question', {})
            mark_scheme = example.get('mark_scheme', {})
            
            enriched_prompt += f"\nExample {i}:\n"
            enriched_prompt += f"Question: {question.get('question_text', 'N/A')}\n"
            enriched_prompt += f"Marks: {question.get('marks', 'N/A')}\n"
            enriched_prompt += f"Mark Scheme: {mark_scheme.get('marking_criteria', 'N/A')}\n"
        enriched_prompt += "\n"
    
    # Add tier-specific guidance
    if intent.tier == "Foundation":
        enriched_prompt += "Foundation Tier Guidelines:\n"
        enriched_prompt += "- Focus on grades 1-5 content\n"
        enriched_prompt += "- Use clear, straightforward language\n"
        enriched_prompt += "- Provide step-by-step scaffolding\n"
        enriched_prompt += "- Include practical, real-world contexts\n"
        enriched_prompt += "- Difficulty scores should range from 1-5\n\n"
    else:
        enriched_prompt += "Higher Tier Guidelines:\n"
        enriched_prompt += "- Focus on grades 4-9 content\n"
        enriched_prompt += "- Include more complex mathematical reasoning\n"
        enriched_prompt += "- Expect multi-step problem solving\n"
        enriched_prompt += "- Use advanced mathematical vocabulary\n"
        enriched_prompt += "- Difficulty scores should range from 6-10\n\n"
    
    # Add Edexcel compliance requirements
    enriched_prompt += "Edexcel GCSE Compliance Requirements:\n"
    enriched_prompt += "- Follow official Edexcel specification exactly\n"
    enriched_prompt += "- Use Edexcel-style mark scheme format\n"
    enriched_prompt += "- Include method marks (M) and accuracy marks (A)\n"
    enriched_prompt += "- Ensure questions are exam-appropriate\n"
    enriched_prompt += "- Use mathematical notation consistent with Edexcel papers\n"
    enriched_prompt += "- Each question MUST include a difficulty_score field (1-10)\n\n"
    
    # Add mathematical rendering guidance
    enriched_prompt += "Mathematical Notation Guidelines:\n"
    enriched_prompt += "- Use LaTeX for complex mathematical expressions\n"
    enriched_prompt += "- Fractions: \\frac{numerator}{denominator}\n"
    enriched_prompt += "- Square roots: \\sqrt{expression}\n"
    enriched_prompt += "- Exponents: x^{power}\n"
    enriched_prompt += "- Mathematical symbols: \\times, \\div, \\pm, \\leq, \\geq\n"
    enriched_prompt += "- For simple expressions, plain text is acceptable (e.g., 3/4, x^2)\n\n"
    
    logger.info(
        "Built enriched prompt with examples",
        extra={
            "request_id": request_id,
            "prompt_length": len(enriched_prompt),
            "learning_objectives_count": len(learning_objectives),
            "misconceptions_count": len(common_misconceptions),
            "examples_count": len(examples_content)
        }
    )
    
    return enriched_prompt


def _generate_difficulty_guidance(intent: QueryIntent, request_id: str) -> Dict[str, Any]:
    """
    Generate difficulty calibration guidance based on tier with enhanced distribution logic.
    
    Args:
        intent: Parsed query intent
        request_id: Request ID for logging
        
    Returns:
        Dictionary with comprehensive difficulty guidance
    """
    if intent.tier == "Foundation":
        # Foundation tier: grades 1-5, difficulty scores 1-5
        difficulty_guidance = {
            "min_difficulty": 1,
            "max_difficulty": 5,
            "target_distribution": _calculate_difficulty_distribution(intent.count, "Foundation"),
            "tier_description": "Foundation tier (grades 1-5)",
            "guidance": "Focus on fundamental concepts with clear scaffolding",
            "grade_mapping": {
                1: "Grade 1 - Basic number skills",
                2: "Grade 2 - Simple calculations and patterns",
                3: "Grade 3 - Core mathematical concepts",
                4: "Grade 4 - Intermediate problem solving",
                5: "Grade 5 - Advanced foundation concepts"
            },
            "recommended_marks_range": {
                1: [1, 2],  # Very easy questions: 1-2 marks
                2: [2, 3],  # Easy questions: 2-3 marks
                3: [3, 4],  # Medium questions: 3-4 marks
                4: [4, 5],  # Challenging questions: 4-5 marks
                5: [5, 6]   # Very challenging foundation: 5-6 marks
            }
        }
    else:  # Higher tier
        # Higher tier: grades 4-9, difficulty scores 6-10
        difficulty_guidance = {
            "min_difficulty": 6,
            "max_difficulty": 10,
            "target_distribution": _calculate_difficulty_distribution(intent.count, "Higher"),
            "tier_description": "Higher tier (grades 4-9)",
            "guidance": "Include complex reasoning and multi-step problem solving",
            "grade_mapping": {
                6: "Grade 4-5 - Foundation of higher concepts",
                7: "Grade 6 - Intermediate higher mathematics",
                8: "Grade 7 - Advanced problem solving",
                9: "Grade 8 - Complex mathematical reasoning",
                10: "Grade 9 - Exceptional mathematical insight"
            },
            "recommended_marks_range": {
                6: [3, 4],   # Easy higher: 3-4 marks
                7: [4, 5],   # Medium-easy higher: 4-5 marks
                8: [5, 7],   # Medium higher: 5-7 marks
                9: [6, 8],   # Challenging higher: 6-8 marks
                10: [7, 10]  # Very challenging: 7-10 marks
            }
        }
    
    # Add topic-specific difficulty adjustments
    topic_adjustments = _get_topic_difficulty_adjustments(intent.topic, intent.tier)
    difficulty_guidance["topic_adjustments"] = topic_adjustments
    
    # Add question count specific recommendations
    difficulty_guidance["count_recommendations"] = _get_count_specific_recommendations(intent.count, intent.tier)
    
    logger.info(
        "Generated enhanced difficulty guidance",
        extra={
            "request_id": request_id,
            "tier": intent.tier,
            "min_difficulty": difficulty_guidance["min_difficulty"],
            "max_difficulty": difficulty_guidance["max_difficulty"],
            "question_count": intent.count,
            "has_topic_adjustments": bool(topic_adjustments)
        }
    )
    
    return difficulty_guidance


def _calculate_difficulty_distribution(count: int, tier: str) -> Dict[int, float]:
    """
    Calculate optimal difficulty distribution based on question count and tier.
    
    Args:
        count: Number of questions requested
        tier: Foundation or Higher
        
    Returns:
        Dictionary mapping difficulty scores to percentages
    """
    if tier == "Foundation":
        if count <= 5:
            # Small sets: focus on core difficulties
            return {2: 0.2, 3: 0.6, 4: 0.2}
        elif count <= 10:
            # Medium sets: balanced distribution
            return {1: 0.1, 2: 0.2, 3: 0.4, 4: 0.2, 5: 0.1}
        else:
            # Large sets: full range with emphasis on middle
            return {1: 0.1, 2: 0.2, 3: 0.4, 4: 0.2, 5: 0.1}
    else:  # Higher tier
        if count <= 5:
            # Small sets: focus on core higher difficulties
            return {7: 0.2, 8: 0.6, 9: 0.2}
        elif count <= 10:
            # Medium sets: balanced higher distribution
            return {6: 0.1, 7: 0.2, 8: 0.4, 9: 0.2, 10: 0.1}
        else:
            # Large sets: full higher range
            return {6: 0.1, 7: 0.2, 8: 0.4, 9: 0.2, 10: 0.1}


def _get_topic_difficulty_adjustments(topic: str, tier: str) -> Dict[str, Any]:
    """
    Get topic-specific difficulty adjustments and guidance.
    
    Args:
        topic: Mathematical topic
        tier: Foundation or Higher
        
    Returns:
        Dictionary with topic-specific adjustments
    """
    topic_adjustments = {
        "Number": {
            "foundation_focus": ["Basic arithmetic", "Fractions", "Decimals", "Percentages"],
            "higher_focus": ["Surds", "Indices", "Standard form", "Bounds"],
            "difficulty_note": "Number topics can range from very basic to highly complex"
        },
        "Algebra": {
            "foundation_focus": ["Linear equations", "Simple expressions", "Substitution"],
            "higher_focus": ["Quadratics", "Simultaneous equations", "Inequalities", "Functions"],
            "difficulty_note": "Algebra requires strong foundational understanding"
        },
        "Geometry": {
            "foundation_focus": ["Basic shapes", "Area and perimeter", "Angles"],
            "higher_focus": ["Trigonometry", "Circle theorems", "Vectors", "Transformations"],
            "difficulty_note": "Geometry benefits from visual representation"
        },
        "Statistics": {
            "foundation_focus": ["Data collection", "Averages", "Simple graphs"],
            "higher_focus": ["Correlation", "Probability distributions", "Sampling"],
            "difficulty_note": "Statistics requires interpretation skills"
        },
        "Probability": {
            "foundation_focus": ["Basic probability", "Simple events"],
            "higher_focus": ["Conditional probability", "Tree diagrams", "Combinations"],
            "difficulty_note": "Probability requires logical reasoning"
        },
        "Ratio": {
            "foundation_focus": ["Simple ratios", "Proportion", "Scale factors"],
            "higher_focus": ["Similar shapes", "Compound measures", "Growth and decay"],
            "difficulty_note": "Ratio connects to many other mathematical areas"
        }
    }
    
    return topic_adjustments.get(topic, {
        "foundation_focus": ["Basic concepts"],
        "higher_focus": ["Advanced applications"],
        "difficulty_note": "Standard difficulty progression applies"
    })


def _get_count_specific_recommendations(count: int, tier: str) -> Dict[str, Any]:
    """
    Get recommendations based on the number of questions requested.
    
    Args:
        count: Number of questions
        tier: Foundation or Higher
        
    Returns:
        Dictionary with count-specific recommendations
    """
    if count <= 5:
        return {
            "strategy": "focused_practice",
            "recommendation": "Focus on 2-3 core difficulty levels for targeted practice",
            "variety": "Maintain consistent difficulty for skill building"
        }
    elif count <= 15:
        return {
            "strategy": "balanced_assessment",
            "recommendation": "Include full difficulty range with emphasis on target grades",
            "variety": "Mix question types and difficulty levels"
        }
    elif count <= 30:
        return {
            "strategy": "comprehensive_practice",
            "recommendation": "Cover all difficulty levels with multiple examples of each",
            "variety": "Include various question formats and contexts"
        }
    else:
        return {
            "strategy": "extensive_coverage",
            "recommendation": "Ensure comprehensive topic coverage with graduated difficulty",
            "variety": "Include diverse question types, contexts, and mathematical approaches"
        }


def _enhance_assessment_objectives(assessment_objectives: Any) -> Dict[str, Any]:
    """
    Enhance assessment objectives with detailed teacher guidance.
    
    Args:
        assessment_objectives: Raw assessment objectives from specification
        
    Returns:
        Enhanced assessment objectives with teacher guidance
    """
    # Standard Edexcel GCSE Mathematics Assessment Objectives
    standard_aos = {
        "AO1": {
            "title": "Use and apply standard techniques",
            "description": "Use and apply standard techniques",
            "weight": "50%",
            "teacher_guidance": "Focus on procedural fluency and standard methods",
            "question_types": ["Routine calculations", "Standard algorithms", "Direct application of formulas"]
        },
        "AO2": {
            "title": "Reason, interpret and communicate mathematically",
            "description": "Reason, interpret and communicate mathematically",
            "weight": "25%",
            "teacher_guidance": "Emphasize mathematical reasoning and explanation",
            "question_types": ["Proof questions", "Explain reasoning", "Interpret results"]
        },
        "AO3": {
            "title": "Solve problems within mathematics and in other contexts",
            "description": "Solve problems within mathematics and in other contexts",
            "weight": "25%",
            "teacher_guidance": "Include real-world applications and problem-solving",
            "question_types": ["Word problems", "Multi-step problems", "Real-world contexts"]
        }
    }
    
    # If assessment objectives are provided, merge with standard structure
    if isinstance(assessment_objectives, dict):
        for ao_key, ao_value in assessment_objectives.items():
            if ao_key in standard_aos:
                standard_aos[ao_key]["specification_detail"] = ao_value
    elif isinstance(assessment_objectives, list):
        for i, ao in enumerate(assessment_objectives):
            ao_key = f"AO{i+1}"
            if ao_key in standard_aos:
                standard_aos[ao_key]["specification_detail"] = ao
    
    return standard_aos


def _generate_teacher_guidance(intent: QueryIntent, spec_content: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """
    Generate comprehensive teacher guidance for the topic and tier.
    
    Args:
        intent: Parsed query intent
        spec_content: Specification content
        request_id: Request ID for logging
        
    Returns:
        Dictionary with teacher-specific guidance
    """
    teacher_guidance = {
        "lesson_planning": {
            "suggested_lesson_structure": _get_lesson_structure_guidance(intent.tier),
            "prerequisite_knowledge": _get_prerequisite_knowledge(intent.topic, intent.tier),
            "extension_activities": _get_extension_activities(intent.topic, intent.tier),
            "common_errors": spec_content.get("common_misconceptions", [])
        },
        "assessment_guidance": {
            "formative_assessment": _get_formative_assessment_strategies(intent.topic),
            "summative_assessment": _get_summative_assessment_guidance(intent.tier),
            "marking_guidance": _get_marking_guidance(intent.tier),
            "feedback_strategies": _get_feedback_strategies()
        },
        "differentiation": {
            "support_strategies": _get_support_strategies(intent.tier),
            "challenge_strategies": _get_challenge_strategies(intent.tier),
            "accessibility": _get_accessibility_guidance()
        },
        "resources": {
            "recommended_manipulatives": _get_manipulatives(intent.topic),
            "technology_integration": _get_technology_suggestions(intent.topic),
            "real_world_connections": _get_real_world_connections(intent.topic)
        }
    }
    
    logger.info(
        "Generated teacher guidance",
        extra={
            "request_id": request_id,
            "topic": intent.topic,
            "tier": intent.tier,
            "guidance_sections": len(teacher_guidance)
        }
    )
    
    return teacher_guidance


def _generate_curriculum_links(topic: str, tier: str) -> Dict[str, Any]:
    """
    Generate curriculum links and progression pathways.
    
    Args:
        topic: Mathematical topic
        tier: Foundation or Higher
        
    Returns:
        Dictionary with curriculum links
    """
    curriculum_links = {
        "prior_learning": _get_prior_learning_links(topic, tier),
        "future_learning": _get_future_learning_links(topic, tier),
        "cross_curricular": _get_cross_curricular_links(topic),
        "progression_pathway": _get_progression_pathway(topic, tier)
    }
    
    return curriculum_links


def _generate_differentiation_strategies(tier: str, count: int) -> Dict[str, Any]:
    """
    Generate differentiation strategies based on tier and question count.
    
    Args:
        tier: Foundation or Higher
        count: Number of questions
        
    Returns:
        Dictionary with differentiation strategies
    """
    strategies = {
        "by_outcome": {
            "all_students": "Complete basic questions successfully",
            "most_students": "Apply concepts to varied contexts",
            "some_students": "Extend learning to complex problems"
        },
        "by_support": {
            "high_support": "Provide worked examples and scaffolding",
            "medium_support": "Offer hints and prompts when needed",
            "low_support": "Encourage independent problem solving"
        },
        "by_task": {
            "foundation_focus": "Emphasize procedural fluency" if tier == "Foundation" else "Build on foundation skills",
            "core_focus": "Develop conceptual understanding",
            "extension_focus": "Apply to novel situations"
        }
    }
    
    if count > 20:
        strategies["grouping"] = {
            "suggestion": "Consider dividing questions into themed sets",
            "rationale": "Large question sets benefit from structured grouping"
        }
    
    return strategies


# Helper functions for teacher guidance components

def _get_lesson_structure_guidance(tier: str) -> List[str]:
    """Get suggested lesson structure for the tier."""
    if tier == "Foundation":
        return [
            "Starter: Review prerequisite knowledge (5-10 minutes)",
            "Main: Introduce concept with concrete examples (20-25 minutes)",
            "Practice: Guided practice with scaffolding (15-20 minutes)",
            "Plenary: Consolidate learning and address misconceptions (5-10 minutes)"
        ]
    else:
        return [
            "Starter: Challenge problem or review (5-10 minutes)",
            "Main: Explore concept through investigation (25-30 minutes)",
            "Practice: Independent application and extension (15-20 minutes)",
            "Plenary: Reflect on learning and make connections (5-10 minutes)"
        ]


def _get_prerequisite_knowledge(topic: str, tier: str) -> List[str]:
    """Get prerequisite knowledge for the topic and tier."""
    prerequisites = {
        "Number": ["Basic arithmetic", "Place value", "Fractions basics"] if tier == "Foundation" 
                 else ["All foundation number skills", "Algebraic manipulation"],
        "Algebra": ["Number skills", "Basic equations"] if tier == "Foundation"
                  else ["Linear algebra", "Quadratic basics"],
        "Geometry": ["Basic shapes", "Angle facts"] if tier == "Foundation"
                   else ["Coordinate geometry", "Trigonometry basics"],
        "Statistics": ["Data handling", "Basic graphs"] if tier == "Foundation"
                     else ["Statistical measures", "Probability"],
        "Probability": ["Fractions", "Basic probability"] if tier == "Foundation"
                      else ["Tree diagrams", "Conditional probability"],
        "Ratio": ["Fractions", "Multiplication"] if tier == "Foundation"
                else ["Proportional reasoning", "Similar shapes"]
    }
    return prerequisites.get(topic, ["Basic mathematical skills"])


def _get_extension_activities(topic: str, tier: str) -> List[str]:
    """Get extension activities for the topic and tier."""
    extensions = {
        "Number": ["Investigate number patterns", "Explore different number systems"],
        "Algebra": ["Create and solve own equations", "Investigate algebraic identities"],
        "Geometry": ["Design geometric constructions", "Explore geometric proofs"],
        "Statistics": ["Conduct statistical investigations", "Analyze real data sets"],
        "Probability": ["Design probability experiments", "Explore theoretical vs experimental probability"],
        "Ratio": ["Investigate golden ratio", "Explore scale factors in art and architecture"]
    }
    return extensions.get(topic, ["Investigate real-world applications"])


def _get_formative_assessment_strategies(topic: str) -> List[str]:
    """Get formative assessment strategies for the topic."""
    return [
        "Exit tickets with key concept questions",
        "Mini-whiteboards for quick checks",
        "Peer assessment of problem-solving methods",
        "Self-assessment using success criteria",
        "Diagnostic questions targeting common misconceptions"
    ]


def _get_summative_assessment_guidance(tier: str) -> Dict[str, Any]:
    """Get summative assessment guidance for the tier."""
    return {
        "question_types": "Mix of procedural and problem-solving questions",
        "time_allocation": "1-2 minutes per mark as a general guide",
        "mark_distribution": "Balance AO1, AO2, and AO3 objectives",
        "accessibility": "Consider visual, auditory, and kinesthetic learners"
    }


def _get_marking_guidance(tier: str) -> Dict[str, Any]:
    """Get marking guidance for the tier."""
    return {
        "method_marks": "Award for correct mathematical methods",
        "accuracy_marks": "Award for correct final answers",
        "communication": "Look for clear mathematical communication",
        "partial_credit": "Award partial marks for partially correct solutions"
    }


def _get_feedback_strategies() -> List[str]:
    """Get effective feedback strategies."""
    return [
        "Focus on the mathematics, not the student",
        "Highlight what was done well before areas for improvement",
        "Provide specific, actionable next steps",
        "Use questioning to guide student thinking",
        "Encourage mathematical reasoning and explanation"
    ]


def _get_support_strategies(tier: str) -> List[str]:
    """Get support strategies for struggling students."""
    return [
        "Break complex problems into smaller steps",
        "Provide visual representations and manipulatives",
        "Use worked examples with clear explanations",
        "Offer alternative solution methods",
        "Provide additional practice with similar problems"
    ]


def _get_challenge_strategies(tier: str) -> List[str]:
    """Get challenge strategies for advanced students."""
    return [
        "Provide open-ended investigation tasks",
        "Encourage multiple solution methods",
        "Introduce extension topics and connections",
        "Promote peer tutoring opportunities",
        "Set challenging real-world problem contexts"
    ]


def _get_accessibility_guidance() -> List[str]:
    """Get accessibility guidance for inclusive teaching."""
    return [
        "Provide visual and auditory representations",
        "Use clear, simple language in instructions",
        "Allow extra time for processing",
        "Offer alternative recording methods",
        "Ensure materials are physically accessible"
    ]


def _get_manipulatives(topic: str) -> List[str]:
    """Get recommended manipulatives for the topic."""
    manipulatives = {
        "Number": ["Base-10 blocks", "Fraction strips", "Number lines"],
        "Algebra": ["Algebra tiles", "Balance scales", "Graphing tools"],
        "Geometry": ["Geometric shapes", "Measuring tools", "Coordinate grids"],
        "Statistics": ["Data collection sheets", "Graphing materials", "Calculators"],
        "Probability": ["Dice", "Coins", "Spinners", "Cards"],
        "Ratio": ["Measuring tools", "Scale models", "Proportion grids"]
    }
    return manipulatives.get(topic, ["Basic mathematical tools"])


def _get_technology_suggestions(topic: str) -> List[str]:
    """Get technology integration suggestions for the topic."""
    return [
        "Graphing calculators for complex calculations",
        "Dynamic geometry software for visualizations",
        "Spreadsheets for data analysis",
        "Online simulations for probability experiments",
        "Mathematical modeling software"
    ]


def _get_real_world_connections(topic: str) -> List[str]:
    """Get real-world connections for the topic."""
    connections = {
        "Number": ["Personal finance", "Cooking and recipes", "Shopping and discounts"],
        "Algebra": ["Engineering design", "Business modeling", "Scientific formulas"],
        "Geometry": ["Architecture", "Art and design", "Navigation"],
        "Statistics": ["Sports analysis", "Market research", "Scientific studies"],
        "Probability": ["Insurance", "Games and gambling", "Weather forecasting"],
        "Ratio": ["Maps and scale", "Photography", "Architecture"]
    }
    return connections.get(topic, ["Everyday mathematical applications"])


def _get_prior_learning_links(topic: str, tier: str) -> List[str]:
    """Get prior learning links for curriculum progression."""
    return [f"Previous {topic.lower()} concepts", "Related mathematical skills", "Foundation knowledge"]


def _get_future_learning_links(topic: str, tier: str) -> List[str]:
    """Get future learning links for curriculum progression."""
    if tier == "Foundation":
        return [f"Higher tier {topic.lower()}", "A-level mathematics preparation", "Further applications"]
    else:
        return [f"Advanced {topic.lower()}", "A-level mathematics", "University mathematics"]


def _get_cross_curricular_links(topic: str) -> List[str]:
    """Get cross-curricular links for the topic."""
    links = {
        "Number": ["Science calculations", "Geography data", "Business studies"],
        "Algebra": ["Physics formulas", "Chemistry equations", "Economics modeling"],
        "Geometry": ["Art and design", "Technology design", "Geography mapping"],
        "Statistics": ["Science experiments", "Geography data analysis", "Psychology research"],
        "Probability": ["Science uncertainty", "History analysis", "Economics risk"],
        "Ratio": ["Art proportions", "Geography scale", "Science concentrations"]
    }
    return links.get(topic, ["Science", "Technology", "Real-world applications"])


def _get_progression_pathway(topic: str, tier: str) -> Dict[str, str]:
    """Get progression pathway information."""
    return {
        "current_level": f"{tier} tier {topic}",
        "next_steps": f"Advanced {topic.lower()} concepts",
        "long_term": "A-level Mathematics preparation"
    }


def _prepare_topic_coverage(intent: QueryIntent, user_id: str, request_id: str) -> Dict[str, Any]:
    """
    Prepare topic coverage data for user (placeholder implementation).
    
    Args:
        intent: Parsed query intent
        user_id: User ID for personalization
        request_id: Request ID for logging
        
    Returns:
        Dictionary with topic coverage information
    """
    # Placeholder implementation - will be enhanced in later tasks
    topic_coverage = {
        "recent_topics": [],  # Will be populated from DynamoDB in later tasks
        "suggested_topics": [],  # Will be populated based on coverage analysis
        "coverage_stats": {},  # Will be populated from TopicCoverage table
        "current_topic": intent.topic,
        "current_subtopic": intent.subtopic
    }
    
    # Basic topic suggestions based on current topic (static for now)
    topic_suggestions = {
        "Number": ["Algebra", "Ratio", "Statistics"],
        "Algebra": ["Geometry", "Number", "Statistics"],
        "Geometry": ["Number", "Algebra", "Statistics"],
        "Statistics": ["Probability", "Number", "Algebra"],
        "Probability": ["Statistics", "Number", "Ratio"],
        "Ratio": ["Number", "Algebra", "Geometry"]
    }
    
    topic_coverage["suggested_topics"] = topic_suggestions.get(intent.topic, [])
    
    logger.info(
        "Prepared topic coverage data",
        extra={
            "request_id": request_id,
            "current_topic": intent.topic,
            "has_user_id": bool(user_id),
            "suggested_count": len(topic_coverage["suggested_topics"])
        }
    )
    
    return topic_coverage


def _create_timeout_error_response(request_id: str, function_name: str) -> Dict[str, Any]:
    """
    Create timeout error response with descriptive message.
    
    Args:
        request_id: Request ID for tracking
        function_name: Name of the Lambda function
        
    Returns:
        Standardized timeout error response
    """
    timeout_seconds = 30 if function_name == "InterpretLambda" else 60
    
    logger.error(
        f"{function_name} approaching timeout",
        extra={
            "request_id": request_id,
            "timeout_seconds": timeout_seconds,
            "function_name": function_name
        }
    )
    
    return _create_error_response(
        504,
        "TimeoutError",
        f"Request processing exceeded {timeout_seconds} second timeout limit",
        "Please try again with a simpler query or contact support if the issue persists",
        request_id,
        details=f"{function_name} timeout after {timeout_seconds} seconds"
    )