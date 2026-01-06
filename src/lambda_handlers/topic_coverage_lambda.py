"""
TopicCoverageLambda handler for topic coverage analytics and suggestions.

This Lambda function provides endpoints for retrieving user topic coverage
statistics and generating topic suggestions based on underrepresented areas.
"""

import json
import logging
import os
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from src.utils.validation import sanitize_json_input
from src.utils.security import authenticate_request, get_cors_response_headers
from src.services.topic_coverage_service import TopicCoverageService

# Configure structured logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
TOPIC_COVERAGE_TABLE_NAME = os.environ.get('TOPIC_COVERAGE_TABLE_NAME')
AWS_REGION = os.environ.get('AWS_REGION', 'eu-west-2')

# Initialize services
topic_coverage_service = TopicCoverageService(region=AWS_REGION, table_name=TOPIC_COVERAGE_TABLE_NAME)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for topic coverage analytics.
    
    Args:
        event: API Gateway event containing the coverage request
        context: Lambda context object
        
    Returns:
        API Gateway response with coverage statistics or suggestions
    """
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    # Set up structured logging context
    logger.info(
        "TopicCoverageLambda invocation started",
        extra={
            "request_id": request_id,
            "function_name": context.function_name,
            "aws_request_id": context.aws_request_id,
            "timestamp": datetime.utcnow().isoformat(),
            "remaining_time_ms": context.get_remaining_time_in_millis()
        }
    )
    
    try:
        # Extract session token from Authorization header
        headers = event.get('headers', {})
        auth_header = None
        
        # Check for Authorization header (case insensitive)
        for header_name, header_value in headers.items():
            if header_name.lower() == 'authorization':
                auth_header = header_value
                break
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return _create_error_response(
                401,
                "AuthenticationError",
                "Missing or invalid Authorization header",
                "Please provide a valid Bearer token",
                request_id
            )
        
        session_token = auth_header[7:]  # Remove "Bearer " prefix
        
        # Validate session token using auth service
        from src.services.auth_service import AuthService
        import os
        auth_service = AuthService(
            users_table_name=os.environ.get('USERS_TABLE_NAME'),
            region=os.environ.get('REGION', 'eu-west-2')
        )
        
        is_valid, user_id = auth_service.validate_session(session_token)
        
        if not is_valid or not user_id:
            return _create_error_response(
                401,
                "AuthenticationError",
                "Invalid or expired session token",
                "Please log in again",
                request_id
            )
        
        # Parse request path to determine action
        path = event.get('path', '')
        http_method = event.get('httpMethod', 'GET')
        
        logger.info(
            "Processing topic coverage request",
            extra={
                "request_id": request_id,
                "user_id": user_id,
                "path": path,
                "method": http_method
            }
        )
        
        # Route to appropriate handler based on path
        if path.endswith('/coverage'):
            return _handle_coverage_stats(event, user_id, request_id)
        elif path.endswith('/suggestions'):
            return _handle_topic_suggestions(event, user_id, request_id)
        else:
            return _create_error_response(
                404,
                "NotFound",
                f"Endpoint not found: {path}",
                "Please check the API documentation for valid endpoints",
                request_id
            )
        
    except Exception as e:
        logger.error(
            "Unexpected error in TopicCoverageLambda",
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


def _handle_coverage_stats(event: Dict[str, Any], user_id: str, request_id: str) -> Dict[str, Any]:
    """
    Handle topic coverage statistics request.
    
    Args:
        event: API Gateway event
        user_id: Authenticated user ID
        request_id: Request ID for logging
        
    Returns:
        API Gateway response with coverage statistics
    """
    try:
        # Parse query parameters
        query_params = event.get('queryStringParameters') or {}
        days = int(query_params.get('days', 30))
        
        # Validate days parameter
        if days < 1 or days > 365:
            return _create_error_response(
                400,
                "ValidationError",
                "Days parameter must be between 1 and 365",
                "Please provide a valid number of days",
                request_id
            )
        
        # Get coverage statistics
        coverage_data = topic_coverage_service.get_user_coverage_stats(
            user_id=user_id,
            days=days,
            request_id=request_id
        )
        
        # Check for service errors
        if 'error' in coverage_data:
            return _create_error_response(
                500,
                "ServiceError",
                coverage_data['error'],
                "Please try again later",
                request_id
            )
        
        logger.info(
            "Coverage statistics retrieved successfully",
            extra={
                "request_id": request_id,
                "user_id": user_id,
                "days": days,
                "total_questions": coverage_data.get('total_questions', 0),
                "topics_covered": len(coverage_data.get('coverage_stats', {}))
            }
        )
        
        # Serialize response body
        try:
            response_body = json.dumps(coverage_data)
        except (TypeError, ValueError) as json_error:
            logger.error(f"JSON serialization error: {json_error}", extra={"coverage_data": str(coverage_data)[:500]})
            return _create_error_response(500, "SerializationError", "Failed to serialize response", "Please try again", request_id)
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                **get_cors_response_headers(methods='GET,OPTIONS'),
                "X-Request-ID": request_id,
                "X-API-Version": "1.0"
            },
            "body": response_body
        }
        
    except ValueError as e:
        return _create_error_response(
            400,
            "ValidationError",
            str(e),
            "Please check your request parameters",
            request_id
        )
    except Exception as e:
        import traceback
        logger.error(
            "Failed to retrieve coverage statistics",
            extra={
                "request_id": request_id,
                "user_id": user_id,
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc()
            }
        )
        return _create_error_response(
            500,
            "InternalError",
            "Failed to retrieve coverage statistics",
            "Please try again later",
            request_id
        )


def _handle_topic_suggestions(event: Dict[str, Any], user_id: str, request_id: str) -> Dict[str, Any]:
    """
    Handle topic suggestions request.
    
    Args:
        event: API Gateway event
        user_id: Authenticated user ID
        request_id: Request ID for logging
        
    Returns:
        API Gateway response with topic suggestions
    """
    try:
        # Parse query parameters
        query_params = event.get('queryStringParameters') or {}
        days = int(query_params.get('days', 30))
        max_suggestions = int(query_params.get('max_suggestions', 5))
        
        # Validate parameters
        if days < 1 or days > 365:
            return _create_error_response(
                400,
                "ValidationError",
                "Days parameter must be between 1 and 365",
                "Please provide a valid number of days",
                request_id
            )
        
        if max_suggestions < 1 or max_suggestions > 20:
            return _create_error_response(
                400,
                "ValidationError",
                "Max suggestions must be between 1 and 20",
                "Please provide a valid number of suggestions",
                request_id
            )
        
        # Get topic suggestions
        suggestions = topic_coverage_service.get_suggested_topics(
            user_id=user_id,
            days=days,
            max_suggestions=max_suggestions,
            request_id=request_id
        )
        
        # Also get current coverage stats for context
        coverage_data = topic_coverage_service.get_user_coverage_stats(
            user_id=user_id,
            days=days,
            request_id=request_id
        )
        
        response_data = {
            "suggested_topics": suggestions,
            "suggestion_count": len(suggestions),
            "analysis_period_days": days,
            "current_coverage": {
                "total_questions": coverage_data.get('total_questions', 0),
                "topics_covered": len(coverage_data.get('coverage_stats', {})),
                "coverage_percentage": coverage_data.get('coverage_percentage', 0)
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(
            "Topic suggestions generated successfully",
            extra={
                "request_id": request_id,
                "user_id": user_id,
                "days": days,
                "max_suggestions": max_suggestions,
                "suggestions_count": len(suggestions),
                "current_coverage_percentage": coverage_data.get('coverage_percentage', 0)
            }
        )
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                **get_cors_response_headers(methods='GET,OPTIONS'),
                "X-Request-ID": request_id,
                "X-API-Version": "1.0"
            },
            "body": json.dumps(response_data)
        }
        
    except ValueError as e:
        return _create_error_response(
            400,
            "ValidationError",
            str(e),
            "Please check your request parameters",
            request_id
        )
    except Exception as e:
        logger.error(
            "Failed to generate topic suggestions",
            extra={
                "request_id": request_id,
                "user_id": user_id,
                "error": str(e),
                "error_type": type(e).__name__
            }
        )
        return _create_error_response(
            500,
            "InternalError",
            "Failed to generate topic suggestions",
            "Please try again later",
            request_id
        )


def _create_error_response(
    status_code: int,
    error_type: str,
    message: str,
    guidance: str,
    request_id: str,
    details: Optional[str] = None
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
    
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            **get_cors_response_headers(methods='GET,OPTIONS'),
            "X-Request-ID": request_id,
            "X-API-Version": "1.0"
        },
        "body": json.dumps(error_response)
    }