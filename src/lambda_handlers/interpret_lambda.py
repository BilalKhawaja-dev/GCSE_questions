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
from typing import Dict, Any, Optional

from src.models.query_intent import QueryIntent
from src.utils.validation import validate_query_input, sanitize_input, sanitize_json_input
from src.utils.security import authenticate_request, check_rate_limit
from src.utils.constants import VALID_TOPICS, VALID_TIERS, RATE_LIMIT_REQUESTS_PER_HOUR
from src.utils.cache import (
    create_cache_key, get_cached_query_response, cache_query_response, get_cache_metrics
)
from src.services.bedrock_service import BedrockService

# Configure structured logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
BEDROCK_MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-haiku-20240307')
AWS_REGION = os.environ.get('AWS_REGION', 'eu-west-2')

# Initialize Bedrock service
bedrock_service = BedrockService(region=AWS_REGION)


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
        
        # Check cache for existing response
        cache_key = create_cache_key({'query': sanitized_query})
        cached_response = get_cached_query_response(cache_key)
        
        if cached_response:
            logger.info(
                "Returning cached query interpretation",
                extra={
                    "request_id": request_id,
                    "cache_key": cache_key[:16] + "...",
                    "topic": cached_response.get('topic'),
                    "tier": cached_response.get('tier'),
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
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key",
                    "X-Request-ID": request_id,
                    "X-Cache-Status": "HIT",
                    **rate_limit_headers
                },
                "body": json.dumps(cached_response)
            }
        
        # Check timeout before expensive Bedrock call
        if _is_approaching_timeout(context, buffer_seconds=2):
            return _create_timeout_error_response(request_id, "InterpretLambda")
        
        # Process query with Bedrock (will be implemented in subtask 2.2)
        try:
            intent = _process_query_with_bedrock(sanitized_query, request_id)
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
        
        # Prepare response data
        response_data = {
            "topic": intent.topic,
            "subtopic": intent.subtopic,
            "tier": intent.tier,
            "count": intent.count,
            "confidence": intent.confidence,
            "specification_version": intent.specification_version,
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Cache the response
        cache_query_response(cache_key, response_data)
        
        # Log successful processing
        execution_time_ms = int((time.time() - start_time) * 1000)
        logger.info(
            "Query processed successfully",
            extra={
                "request_id": request_id,
                "topic": intent.topic,
                "tier": intent.tier,
                "count": intent.count,
                "confidence": intent.confidence,
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


def _process_query_with_bedrock(query: str, request_id: str) -> QueryIntent:
    """
    Process query with Bedrock Claude Haiku.
    
    Args:
        query: Sanitized natural language query
        request_id: Request ID for logging
        
    Returns:
        QueryIntent with parsed components
        
    Raises:
        Exception: If processing fails
    """
    return bedrock_service.parse_query_with_haiku(query, request_id)


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
                "Access-Control-Allow-Origin": "*",
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