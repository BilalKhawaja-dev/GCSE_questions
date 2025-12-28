"""
GenerateLambda handler for GCSE question generation.

This Lambda function processes structured QueryIntent objects and generates
high-quality GCSE exam questions with mark schemes using AWS Bedrock Claude Sonnet.
"""

import json
import logging
import os
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

from src.models.query_intent import QueryIntent
from src.models.question import Question
from src.models.mark_scheme import MarkScheme
from src.models.specification_content import SpecificationContent
from src.utils.validation import validate_generation_request, sanitize_json_input
from src.utils.security import authenticate_request, check_rate_limit
from src.utils.constants import VALID_TOPICS, VALID_TIERS, RATE_LIMIT_REQUESTS_PER_HOUR
from src.utils.cache import (
    create_cache_key, get_cached_generation_response, cache_generation_response, get_cache_metrics
)
from src.services.bedrock_service import BedrockService
from src.services.content_retrieval_service import ContentRetrievalService, CircuitBreakerOpenError
from src.services.version_management_service import VersionManagementService

# Configure structured logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
BEDROCK_MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-sonnet-20240229')
SPECIFICATIONS_BUCKET = os.environ.get('SPECIFICATIONS_BUCKET')
EXAMPLES_BUCKET = os.environ.get('EXAMPLES_BUCKET')
AWS_REGION = os.environ.get('AWS_REGION', 'eu-west-2')

# Initialize services
bedrock_service = BedrockService(region=AWS_REGION)
content_service = ContentRetrievalService(
    specifications_bucket=SPECIFICATIONS_BUCKET,
    examples_bucket=EXAMPLES_BUCKET,
    region=AWS_REGION
)
version_service = VersionManagementService()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for question generation.
    
    Args:
        event: API Gateway event containing the generation request
        context: Lambda context object
        
    Returns:
        API Gateway response with generated questions and mark schemes or error
    """
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    # Set up structured logging context
    logger.info(
        "GenerateLambda invocation started",
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
        if _is_approaching_timeout(context, buffer_seconds=10):
            return _create_timeout_error_response(request_id, "GenerateLambda")
        
        # Authenticate request
        is_authenticated, client_id, auth_error = authenticate_request(event)
        if not is_authenticated:
            return _create_error_response(
                401,
                "AuthenticationError",
                auth_error,
                "Please provide a valid API key in the X-API-Key header",
                request_id
            )
        
        # Check rate limit
        is_allowed, rate_limit_headers = check_rate_limit(client_id)
        if not is_allowed:
            return _create_error_response(
                429,
                "RateLimitExceeded",
                "Too many requests",
                f"Rate limit of {RATE_LIMIT_REQUESTS_PER_HOUR} requests per hour exceeded",
                request_id,
                extra_headers=rate_limit_headers
            )
        
        # Parse and sanitize request body
        body = _parse_request_body(event)
        body = sanitize_json_input(body)  # Sanitize the entire JSON input
        
        logger.info(
            "Processing generation request",
            extra={
                "request_id": request_id,
                "request_body": body,
                "remaining_time_ms": context.get_remaining_time_in_millis()
            }
        )
        
        # Check timeout before validation
        if _is_approaching_timeout(context, buffer_seconds=8):
            return _create_timeout_error_response(request_id, "GenerateLambda")
        
        # Validate generation request
        try:
            validation_result = validate_generation_request(request_body=body)
            generation_request = validation_result['generation_request']
        except ValueError as e:
            logger.warning(
                "Generation request validation failed",
                extra={
                    "request_id": request_id,
                    "validation_error": str(e),
                    "request_body": body
                }
            )
            return _create_error_response(
                400,
                "ValidationError",
                str(e),
                "Please check your request parameters and try again",
                request_id
            )
        
        # Check cache for existing response
        cache_key = create_cache_key(generation_request)
        cached_response = get_cached_generation_response(cache_key)
        
        if cached_response:
            logger.info(
                "Returning cached question generation",
                extra={
                    "request_id": request_id,
                    "cache_key": cache_key[:16] + "...",
                    "topic": generation_request.get('topic'),
                    "tier": generation_request.get('tier'),
                    "count": generation_request.get('count'),
                    "execution_time_ms": int((time.time() - start_time) * 1000)
                }
            )
            
            # Update metadata with current request info
            if 'metadata' in cached_response:
                cached_response['metadata']['request_id'] = request_id
                cached_response['metadata']['cached_at'] = datetime.utcnow().isoformat()
            
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key",
                    "X-Request-ID": request_id,
                    "X-API-Version": "1.0",
                    "X-Cache-Status": "HIT",
                    **rate_limit_headers
                },
                "body": json.dumps(cached_response)
            }
        
        # Check timeout before expensive generation process
        if _is_approaching_timeout(context, buffer_seconds=5):
            return _create_timeout_error_response(request_id, "GenerateLambda")
        
        # Generate questions (will be implemented in subsequent subtasks)
        try:
            question_set = _generate_questions(generation_request, request_id, context)
        except Exception as e:
            logger.error(
                "Question generation failed",
                extra={
                    "request_id": request_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "generation_request": generation_request
                }
            )
            return _create_error_response(
                500,
                "InternalError",
                "Failed to generate questions",
                "Please try again later",
                request_id
            )
        
        # Cache the generated response
        cache_generation_response(cache_key, question_set)
        
        # Log successful generation
        execution_time_ms = int((time.time() - start_time) * 1000)
        logger.info(
            "Questions generated successfully",
            extra={
                "request_id": request_id,
                "question_count": len(question_set['questions']),
                "total_marks": question_set['metadata']['total_marks'],
                "topic": generation_request['topic'],
                "tier": generation_request['tier'],
                "cached": True,
                "execution_time_ms": execution_time_ms
            }
        )
        
        # Return successful response
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key",
                "X-Request-ID": request_id,
                "X-API-Version": "1.0",
                "X-Cache-Status": "MISS",
                **rate_limit_headers
            },
            "body": json.dumps(question_set)
        }
        
    except Exception as e:
        logger.error(
            "Unexpected error in GenerateLambda",
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
        if 'body' not in event:
            raise ValueError("Missing request body")
        
        body = event['body']
        if isinstance(body, str):
            body = json.loads(body)
        
        return body
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON in request body")
    except Exception as e:
        raise ValueError(f"Failed to parse request body: {str(e)}")


def _generate_questions(generation_request: Dict[str, Any], request_id: str, context: Any) -> Dict[str, Any]:
    """
    Generate questions based on the request.
    
    Args:
        generation_request: Validated generation request
        request_id: Request ID for logging
        context: Lambda context for timeout monitoring
        
    Returns:
        Generated question set with questions, mark schemes, and metadata
        
    Raises:
        Exception: If generation fails
    """
    logger.info(
        "Starting question generation",
        extra={
            "request_id": request_id,
            "topic": generation_request.get('topic'),
            "tier": generation_request.get('tier'),
            "count": generation_request.get('count'),
            "specification_version": generation_request.get('specification_version', 'latest'),
            "remaining_time_ms": context.get_remaining_time_in_millis()
        }
    )
    
    # Check timeout before starting generation process
    if _is_approaching_timeout(context, buffer_seconds=5):
        raise Exception("Timeout approaching - insufficient time to complete generation")
    
    # Determine specification version to use
    requested_version = generation_request.get('specification_version')
    version_to_use = version_service.get_version_selection_logic(requested_version)
    
    logger.info(
        "Using specification version",
        extra={
            "request_id": request_id,
            "requested_version": requested_version,
            "version_to_use": version_to_use
        }
    )
    
    # Step 1: Retrieve specification content with version support
    try:
        # Check timeout before S3 operations
        if _is_approaching_timeout(context, buffer_seconds=4):
            raise Exception("Timeout approaching - insufficient time for content retrieval")
            
        spec_content = content_service.get_specification_content_versioned(
            topic=generation_request['topic'],
            subtopic=generation_request.get('subtopic'),
            tier=generation_request['tier'],
            version=version_to_use,
            request_id=request_id
        )
        logger.info(
            "Retrieved specification content",
            extra={
                "request_id": request_id, 
                "content_size": len(str(spec_content)),
                "version": version_to_use,
                "remaining_time_ms": context.get_remaining_time_in_millis()
            }
        )
    except CircuitBreakerOpenError:
        logger.error(
            "S3 service unavailable - cannot retrieve specifications",
            extra={"request_id": request_id}
        )
        raise Exception("Content service temporarily unavailable. Please try again later.")
    except Exception as e:
        logger.error(
            "Failed to retrieve specification content",
            extra={"request_id": request_id, "error": str(e), "version": version_to_use}
        )
        raise Exception(f"Failed to retrieve curriculum content: {str(e)}")
    
    # Step 2: Retrieve seed examples (examples don't need versioning for now)
    try:
        # Check timeout before examples retrieval
        if _is_approaching_timeout(context, buffer_seconds=3):
            logger.warning(
                "Timeout approaching - skipping examples retrieval",
                extra={"request_id": request_id}
            )
            examples_content = []
        else:
            examples_content = content_service.get_examples_content(
                topic=generation_request['topic'],
                subtopic=generation_request.get('subtopic'),
                tier=generation_request['tier'],
                request_id=request_id
            )
            logger.info(
                "Retrieved examples content",
                extra={
                    "request_id": request_id, 
                    "example_count": len(examples_content),
                    "remaining_time_ms": context.get_remaining_time_in_millis()
                }
            )
    except Exception as e:
        logger.warning(
            "Failed to retrieve examples content, continuing without examples",
            extra={"request_id": request_id, "error": str(e)}
        )
        examples_content = []
    
    # Step 3: Generate questions with Bedrock Claude Sonnet
    try:
        # Final timeout check before expensive Bedrock call
        if _is_approaching_timeout(context, buffer_seconds=2):
            raise Exception("Timeout approaching - insufficient time for question generation")
            
        question_set = bedrock_service.generate_questions_with_sonnet(
            generation_request=generation_request,
            spec_content=spec_content,
            examples_content=examples_content,
            request_id=request_id
        )
        
        # Add specification version to metadata
        question_set['metadata']['specification_version'] = version_to_use
        
        logger.info(
            "Questions generated with Bedrock",
            extra={
                "request_id": request_id,
                "question_count": len(question_set['questions']),
                "total_marks": question_set['metadata']['total_marks'],
                "specification_version": version_to_use,
                "remaining_time_ms": context.get_remaining_time_in_millis()
            }
        )
        return question_set
        
    except Exception as e:
        logger.error(
            "Failed to generate questions with Bedrock",
            extra={"request_id": request_id, "error": str(e)}
        )
        raise Exception(f"Failed to generate questions: {str(e)}")


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
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key",
        "X-Request-ID": request_id,
        "X-API-Version": "1.0"
    }
    
    # Add extra headers if provided (e.g., rate limit headers)
    if extra_headers:
        headers.update(extra_headers)
    
    return {
        "statusCode": status_code,
        "headers": headers,
        "body": json.dumps(error_response)
    }


def _is_approaching_timeout(context: Any, buffer_seconds: int = 5) -> bool:
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
        "Please try again with a simpler request or contact support if the issue persists",
        request_id,
        details=f"{function_name} timeout after {timeout_seconds} seconds"
    )