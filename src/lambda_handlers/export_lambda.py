"""
Export Lambda Function for GCSE Question Generator V2

Handles PDF export requests with authentication and proper error handling.
Implements requirements 5.6, 5.7, 5.8 for PDF export functionality.
"""

import json
import base64
import logging
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError

from src.services.pdf_export_service import pdf_export_service
from src.services.session_service import session_service
from src.services.auth_service import auth_service
from src.utils.validation import validate_required_fields
from src.utils.security import validate_and_sanitize_input, get_cors_response_headers

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')


def create_error_response(status_code: int, error_message: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create standardized error response with CORS headers."""
    response_body = {'error': error_message}
    if details:
        response_body['details'] = details
    
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            **get_cors_response_headers(methods='POST,OPTIONS')
        },
        'body': json.dumps(response_body)
    }


def create_success_response(data: Dict[str, Any], content_type: str = 'application/json') -> Dict[str, Any]:
    """Create standardized success response with CORS headers."""
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': content_type,
            **get_cors_response_headers(methods='POST,OPTIONS')
        },
        'body': json.dumps(data) if content_type == 'application/json' else data
    }


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for PDF export requests
    
    Expected event structure:
    {
        "session_id": "string",
        "session_token": "string",
        "user_id": "string",
        "format": "pdf"  # Future extensibility
    }
    """
    try:
        logger.info(f"Export request received: {json.dumps(event, default=str)}")
        
        # Validate required fields
        required_fields = ['session_id', 'session_token', 'user_id']
        validation_result = validate_required_fields(event, required_fields)
        if not validation_result['valid']:
            return create_error_response(
                400, 
                'Missing required fields', 
                {'missing_fields': validation_result['missing_fields']}
            )
        
        # Sanitize inputs
        session_id = sanitize_input(event['session_id'])
        session_token = sanitize_input(event['session_token'])
        user_id = sanitize_input(event['user_id'])
        export_format = sanitize_input(event.get('format', 'pdf'))
        
        # Validate session token
        auth_result = auth_service.validate_session_token(session_token, user_id)
        if not auth_result['valid']:
            logger.warning(f"Invalid session token for user {user_id}")
            return create_error_response(401, 'Invalid or expired session token')
        
        # Only support PDF format for now
        if export_format.lower() != 'pdf':
            return create_error_response(
                400, 
                'Unsupported export format', 
                {'supported_formats': ['pdf']}
            )
        
        # Retrieve session data
        session_data = session_service.get_session(session_id, user_id)
        if not session_data:
            logger.warning(f"Session {session_id} not found for user {user_id}")
            return create_error_response(404, 'Session not found or access denied')
        
        # Get user information for PDF personalization
        user_info = auth_service.get_user_info(user_id)
        
        # Generate PDF
        logger.info(f"Generating PDF for session {session_id}")
        pdf_bytes = pdf_export_service.generate_pdf(session_data, user_info)
        
        # Generate filename
        filename = pdf_export_service.generate_filename(session_data, user_info)
        
        # Encode PDF as base64 for API Gateway response
        pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
        
        logger.info(f"PDF generated successfully: {len(pdf_bytes)} bytes, filename: {filename}")
        
        return create_success_response({
            'success': True,
            'filename': filename,
            'content_type': 'application/pdf',
            'size_bytes': len(pdf_bytes),
            'pdf_data': pdf_base64,
            'metadata': {
                'session_id': session_id,
                'question_count': len(session_data.get('generated_questions', [])),
                'topic': session_data.get('metadata', {}).get('topic'),
                'tier': session_data.get('metadata', {}).get('tier'),
                'generated_at': session_data.get('timestamp')
            }
        })
        
    except ClientError as e:
        logger.error(f"AWS service error in export: {str(e)}")
        return create_error_response(500, 'Service temporarily unavailable', {'message': 'Please try again later'})
    
    except Exception as e:
        logger.error(f"Unexpected error in export: {str(e)}")
        return create_error_response(500, 'Internal server error', {'message': 'An unexpected error occurred'})


def handle_options(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle CORS preflight requests"""
    return {
        'statusCode': 200,
        'headers': get_cors_response_headers(methods='POST,OPTIONS'),
        'body': ''
    }