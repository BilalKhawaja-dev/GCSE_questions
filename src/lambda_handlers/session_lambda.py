"""
SessionLambda handler for session history management.

This Lambda function handles session history retrieval, session details,
and session statistics for authenticated users.
"""

import json
import logging
import os
import time
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional

from src.services.session_service import SessionService
from src.utils.validation import sanitize_json_input
from src.utils.security import authenticate_request, get_cors_response_headers

# Configure structured logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
SESSIONS_TABLE_NAME = os.environ.get('SESSIONS_TABLE_NAME')
AWS_REGION = os.environ.get('AWS_REGION', 'eu-west-2')

# Initialize services
session_service = SessionService(region=AWS_REGION)


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle Decimal types from DynamoDB."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            # Convert to int if it's a whole number, otherwise float
            if obj % 1 == 0:
                return int(obj)
            return float(obj)
        return super().default(obj)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for session management operations.
    
    Args:
        event: API Gateway event containing the session request
        context: Lambda context object
        
    Returns:
        API Gateway response with session data or error
    """
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    # Set up structured logging context
    logger.info(
        "SessionLambda invocation started",
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
        
        # Determine action based on HTTP method and path
        http_method = event.get('httpMethod', 'GET')
        path = event.get('path', '')
        path_parameters = event.get('pathParameters') or {}
        query_parameters = event.get('queryStringParameters') or {}
        
        logger.info(
            "Processing session request",
            extra={
                "request_id": request_id,
                "user_id": user_id,
                "http_method": http_method,
                "path": path,
                "path_parameters": path_parameters,
                "query_parameters": query_parameters
            }
        )
        
        # Route to appropriate handler
        if http_method == 'GET':
            if path.endswith('/sessions'):
                # GET /user/sessions - List user sessions
                return _handle_list_sessions(user_id, query_parameters, request_id)
            elif path.endswith('/statistics'):
                # GET /user/statistics - Get session statistics
                return _handle_session_statistics(user_id, request_id)
            elif 'session_id' in path_parameters:
                # GET /user/sessions/{session_id} - Get session details
                session_id = path_parameters['session_id']
                return _handle_session_details(user_id, session_id, request_id)
            else:
                return _create_error_response(
                    404,
                    "NotFound",
                    "Endpoint not found",
                    "Please check the URL and try again",
                    request_id
                )
        else:
            return _create_error_response(
                405,
                "MethodNotAllowed",
                f"Method {http_method} not allowed",
                "Only GET method is supported for session endpoints",
                request_id
            )
        
    except Exception as e:
        logger.error(
            "Unexpected error in SessionLambda",
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


def _handle_list_sessions(user_id: str, query_parameters: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """
    Handle GET /user/sessions request to list user's session history.
    
    Args:
        user_id: User identifier
        query_parameters: Query string parameters (limit, last_evaluated_key)
        request_id: Request ID for logging
        
    Returns:
        API Gateway response with session list
    """
    try:
        # Parse query parameters
        limit = int(query_parameters.get('limit', 50))
        limit = min(max(limit, 1), 100)  # Clamp between 1 and 100
        
        last_evaluated_key = None
        if 'last_evaluated_key' in query_parameters:
            try:
                last_evaluated_key = json.loads(query_parameters['last_evaluated_key'])
            except json.JSONDecodeError:
                logger.warning(
                    "Invalid last_evaluated_key parameter",
                    extra={"request_id": request_id, "user_id": user_id}
                )
        
        # Retrieve user sessions
        sessions_result = session_service.get_user_sessions(
            user_id=user_id,
            limit=limit,
            last_evaluated_key=last_evaluated_key
        )
        
        logger.info(
            "Retrieved user sessions",
            extra={
                "request_id": request_id,
                "user_id": user_id,
                "session_count": sessions_result['count'],
                "has_more": sessions_result['has_more']
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
            "body": json.dumps(sessions_result, cls=DecimalEncoder)
        }
        
    except Exception as e:
        logger.error(
            "Failed to retrieve user sessions",
            extra={
                "request_id": request_id,
                "user_id": user_id,
                "error": str(e)
            }
        )
        return _create_error_response(
            500,
            "InternalError",
            "Failed to retrieve session history",
            "Please try again later",
            request_id
        )


def _handle_session_details(user_id: str, session_id: str, request_id: str) -> Dict[str, Any]:
    """
    Handle GET /user/sessions/{session_id} request to get session details.
    
    Args:
        user_id: User identifier
        session_id: Session identifier
        request_id: Request ID for logging
        
    Returns:
        API Gateway response with session details
    """
    try:
        # Retrieve session details
        session_details = session_service.get_session_details(session_id, user_id)
        
        if not session_details:
            return _create_error_response(
                404,
                "NotFound",
                "Session not found",
                "The requested session does not exist or you don't have access to it",
                request_id
            )
        
        logger.info(
            "Retrieved session details",
            extra={
                "request_id": request_id,
                "user_id": user_id,
                "session_id": session_id,
                "question_count": len(session_details.get('generated_questions', []))
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
            "body": json.dumps(session_details, cls=DecimalEncoder)
        }
        
    except Exception as e:
        logger.error(
            "Failed to retrieve session details",
            extra={
                "request_id": request_id,
                "user_id": user_id,
                "session_id": session_id,
                "error": str(e)
            }
        )
        return _create_error_response(
            500,
            "InternalError",
            "Failed to retrieve session details",
            "Please try again later",
            request_id
        )


def _handle_session_statistics(user_id: str, request_id: str) -> Dict[str, Any]:
    """
    Handle GET /user/statistics request to get session statistics.
    
    Args:
        user_id: User identifier
        request_id: Request ID for logging
        
    Returns:
        API Gateway response with session statistics
    """
    try:
        # Get session statistics
        statistics = session_service.get_session_statistics(user_id)
        
        logger.info(
            "Retrieved session statistics",
            extra={
                "request_id": request_id,
                "user_id": user_id,
                "total_sessions": statistics['total_sessions'],
                "recent_sessions": statistics['recent_sessions_7_days']
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
            "body": json.dumps(statistics, cls=DecimalEncoder)
        }
        
    except Exception as e:
        logger.error(
            "Failed to retrieve session statistics",
            extra={
                "request_id": request_id,
                "user_id": user_id,
                "error": str(e)
            }
        )
        return _create_error_response(
            500,
            "InternalError",
            "Failed to retrieve session statistics",
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
    
    headers = {
        "Content-Type": "application/json",
        **get_cors_response_headers(methods='GET,OPTIONS'),
        "X-Request-ID": request_id,
        "X-API-Version": "1.0"
    }
    
    return {
        "statusCode": status_code,
        "headers": headers,
        "body": json.dumps(error_response)
    }