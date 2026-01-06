"""
AuthLambda - AWS Lambda function for user authentication.
Handles user registration, login, and session validation.
"""

import json
import os
import logging
from typing import Dict, Any

from src.models.user import AuthRequest, AuthResponse
from src.services.auth_service import AuthService
from src.services.audit_logging_service import (
    log_authentication_event, 
    log_security_violation,
    AuditEventType,
    AuditSeverity
)
from src.utils.validation import sanitize_json_input
from src.utils.security import validate_and_sanitize_input, get_cors_response_headers

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize service
USERS_TABLE_NAME = os.environ.get('USERS_TABLE_NAME', 'gcse-users-dev')
REGION = os.environ.get('REGION', 'eu-west-2')

auth_service = AuthService(USERS_TABLE_NAME, REGION)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for authentication operations and API Gateway authorization.
    
    Args:
        event: API Gateway event containing request data or authorizer event
        context: Lambda context object
        
    Returns:
        API Gateway response with authentication result or authorization policy
    """
    # Extract client information for audit logging
    source_ip = event.get('requestContext', {}).get('identity', {}).get('sourceIp', 'unknown')
    user_agent = event.get('headers', {}).get('User-Agent', 'unknown')
    request_id = event.get('requestContext', {}).get('requestId', 'unknown')
    
    try:
        # Check if this is an API Gateway authorizer request
        # Authorizer requests have 'type': 'REQUEST' and 'methodArn'
        # They may have 'body' as null or not present at all
        if (event.get('type') == 'REQUEST' and 'methodArn' in event):
            # This is an authorizer request - handle it
            logger.info(f"Authorizer request detected: methodArn={event.get('methodArn')}")
            return handle_authorizer_request(event, context)
        
        # Log request for debugging
        logger.info(f"Auth request received: {json.dumps(event, default=str)}")
        
        # Parse request body
        if 'body' not in event or not event['body']:
            log_security_violation(
                violation_type="invalid_request",
                description="Missing request body in authentication request",
                source_ip=source_ip,
                severity=AuditSeverity.MEDIUM
            )
            return create_error_response(400, "Request body is required")
        
        try:
            body = json.loads(event['body'])
        except json.JSONDecodeError:
            log_security_violation(
                violation_type="malformed_request",
                description="Invalid JSON in authentication request body",
                source_ip=source_ip,
                severity=AuditSeverity.MEDIUM
            )
            return create_error_response(400, "Invalid JSON in request body")
        
        # Validate and sanitize input
        for key, value in body.items():
            if isinstance(value, str):
                is_valid, error_msg, sanitized_value = validate_and_sanitize_input(value, key)
                if not is_valid:
                    log_security_violation(
                        violation_type="input_validation_failure",
                        description=f"Invalid input in field {key}: {error_msg}",
                        source_ip=source_ip,
                        severity=AuditSeverity.HIGH
                    )
                    return create_error_response(400, f"Invalid input in field {key}")
                body[key] = sanitized_value
        
        # Sanitize input
        body = sanitize_json_input(body)
        
        # Create auth request
        auth_request = AuthRequest(
            action=body.get('action'),
            username=body.get('username'),
            password=body.get('password'),
            email=body.get('email'),
            school=body.get('school'),
            subject_specialization=body.get('subject_specialization'),
            session_token=body.get('session_token')
        )
        
        # Validate action
        if not auth_request.action:
            log_security_violation(
                violation_type="missing_action",
                description="Authentication request missing required action field",
                source_ip=source_ip,
                severity=AuditSeverity.MEDIUM
            )
            return create_error_response(400, "Action is required")
        
        # Route to appropriate handler with audit logging
        if auth_request.action == 'register':
            response = auth_service.register_user(auth_request)
            
            # Log registration attempt
            log_authentication_event(
                event_type=AuditEventType.USER_REGISTRATION,
                username=auth_request.username,
                user_id=response.user_id if response.success else None,
                result="success" if response.success else "failure",
                failure_reason=response.message if not response.success else None,
                source_ip=source_ip,
                user_agent=user_agent
            )
            
        elif auth_request.action == 'login':
            response = auth_service.login_user(auth_request)
            
            # Log login attempt
            log_authentication_event(
                event_type=AuditEventType.USER_LOGIN,
                username=auth_request.username,
                user_id=response.user_id if response.success else None,
                result="success" if response.success else "failure",
                failure_reason=response.message if not response.success else None,
                source_ip=source_ip,
                user_agent=user_agent
            )
            
        elif auth_request.action == 'validate':
            if not auth_request.session_token:
                log_security_violation(
                    violation_type="missing_session_token",
                    description="Session validation request missing session token",
                    source_ip=source_ip,
                    severity=AuditSeverity.MEDIUM
                )
                return create_error_response(400, "Session token is required for validation")
            
            is_valid, user_id = auth_service.validate_session(auth_request.session_token)
            response = AuthResponse(
                success=is_valid,
                message="Session valid" if is_valid else "Session invalid",
                user_id=user_id if is_valid else None
            )
            
            # Log session validation
            log_authentication_event(
                event_type=AuditEventType.SESSION_CREATED if is_valid else AuditEventType.AUTHENTICATION_FAILURE,
                user_id=user_id if is_valid else None,
                result="success" if is_valid else "failure",
                failure_reason="Invalid session token" if not is_valid else None,
                source_ip=source_ip,
                user_agent=user_agent
            )
            
        else:
            log_security_violation(
                violation_type="invalid_action",
                description=f"Invalid authentication action: {auth_request.action}",
                source_ip=source_ip,
                severity=AuditSeverity.MEDIUM
            )
            return create_error_response(400, f"Invalid action: {auth_request.action}")
        
        # Create response
        response_body = {
            'success': response.success,
            'message': response.message
        }
        
        if response.session_token:
            response_body['session_token'] = response.session_token
        if response.user_id:
            response_body['user_id'] = response.user_id
        if response.expires_at:
            response_body['expires_at'] = response.expires_at.isoformat()
        
        logger.info(f"Auth response: success={response.success}, message={response.message}")
        
        return {
            'statusCode': 200 if response.success else 400,
            'headers': {
                'Content-Type': 'application/json',
                **get_cors_response_headers(methods='POST,OPTIONS')
            },
            'body': json.dumps(response_body)
        }
        
    except Exception as e:
        logger.error(f"Auth lambda error: {str(e)}", exc_info=True)
        
        # Log system error
        log_security_violation(
            violation_type="system_error",
            description=f"Authentication system error: {str(e)}",
            source_ip=source_ip,
            severity=AuditSeverity.HIGH,
            additional_context={"request_id": request_id, "error": str(e)}
        )
        
        return create_error_response(500, "Internal server error")


def handle_authorizer_request(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle API Gateway authorizer request for session validation.
    
    Args:
        event: API Gateway authorizer event
        context: Lambda context object
        
    Returns:
        API Gateway authorization policy
    """
    source_ip = event.get('requestContext', {}).get('identity', {}).get('sourceIp', 'unknown')
    
    try:
        # Extract session token from Authorization header (case insensitive)
        headers = event.get('headers', {})
        auth_header = None
        
        # Check for Authorization header (case insensitive)
        for header_name, header_value in headers.items():
            if header_name.lower() == 'authorization':
                auth_header = header_value
                break
        
        if not auth_header:
            logger.warning(f"No Authorization header found. Available headers: {list(headers.keys())}")
            
            log_authentication_event(
                event_type=AuditEventType.AUTHENTICATION_FAILURE,
                result="failure",
                failure_reason="Missing Authorization header",
                source_ip=source_ip
            )
            
            return generate_policy('user', 'Deny', event['methodArn'])
        
        # Extract token (expecting format: "Bearer <token>")
        if not auth_header.startswith('Bearer '):
            logger.warning("Invalid Authorization header format")
            
            log_authentication_event(
                event_type=AuditEventType.AUTHENTICATION_FAILURE,
                result="failure",
                failure_reason="Invalid Authorization header format",
                source_ip=source_ip
            )
            
            return generate_policy('user', 'Deny', event['methodArn'])
        
        session_token = auth_header[7:]  # Remove "Bearer " prefix
        
        # Validate session token
        is_valid, user_id = auth_service.validate_session(session_token)
        
        if is_valid and user_id:
            logger.info(f"Session valid for user: {user_id}")
            
            # Log successful authorization
            log_authentication_event(
                event_type=AuditEventType.SESSION_CREATED,
                user_id=user_id,
                result="success",
                source_ip=source_ip
            )
            
            # Generate policy with user context for downstream Lambda functions
            # Note: API Gateway authorizer context values must be strings
            context_data = {
                'user_id': str(user_id),
                'session_token': str(session_token)
            }
            
            return generate_policy(user_id, 'Allow', event['methodArn'], context_data)
        else:
            logger.warning(f"Invalid session token: {session_token[:10]}...")
            
            # Log failed authorization
            log_authentication_event(
                event_type=AuditEventType.AUTHENTICATION_FAILURE,
                result="failure",
                failure_reason="Invalid or expired session token",
                source_ip=source_ip
            )
            
            return generate_policy('user', 'Deny', event['methodArn'])
            
    except Exception as e:
        logger.error(f"Authorizer error: {str(e)}", exc_info=True)
        
        # Log system error in authorization
        log_security_violation(
            violation_type="authorization_system_error",
            description=f"Authorization system error: {str(e)}",
            source_ip=source_ip,
            severity=AuditSeverity.HIGH
        )
        
        return generate_policy('user', 'Deny', event['methodArn'])


def generate_policy(principal_id: str, effect: str, resource: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Generate API Gateway authorization policy.
    
    Args:
        principal_id: User identifier
        effect: 'Allow' or 'Deny'
        resource: Resource ARN
        context: Optional context to pass to downstream Lambda functions
        
    Returns:
        Authorization policy document
    """
    # For Allow policies, grant access to all resources in the API
    # For Deny policies, deny access to the specific resource
    if effect == 'Allow':
        # Extract the API Gateway ARN base and allow access to all resources
        # Resource format: arn:aws:execute-api:region:account:api-id/stage/method/resource-path
        resource_parts = resource.split('/')
        if len(resource_parts) >= 3:
            # Create wildcard resource: arn:aws:execute-api:region:account:api-id/stage/*/*
            api_base = '/'.join(resource_parts[:2])  # arn:aws:execute-api:region:account:api-id/stage
            wildcard_resource = f"{api_base}/*/*"
        else:
            wildcard_resource = resource
        
        policy_resource = wildcard_resource
    else:
        policy_resource = resource
    
    policy = {
        'principalId': principal_id,
        'policyDocument': {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Action': 'execute-api:Invoke',
                    'Effect': effect,
                    'Resource': policy_resource
                }
            ]
        }
    }
    
    # Add context if provided
    if context:
        policy['context'] = context
    
    return policy


def create_error_response(status_code: int, message: str) -> Dict[str, Any]:
    """Create standardized error response."""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            **get_cors_response_headers(methods='POST,OPTIONS')
        },
        'body': json.dumps({
            'success': False,
            'message': message
        })
    }