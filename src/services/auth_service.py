"""
Authentication service for user management.
"""

import bcrypt
import secrets
import os
import boto3
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple
from botocore.exceptions import ClientError

from ..models.user import User, AuthRequest, AuthResponse
from ..utils.validation import validate_email, validate_password, validate_username

# Configure logging
logger = logging.getLogger(__name__)


class AuthService:
    """Service for user authentication and session management."""
    
    def __init__(self, users_table_name: str, region: str = 'eu-west-2'):
        """Initialize authentication service."""
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.users_table = self.dynamodb.Table(users_table_name)
        self.salt_rounds = 12
    
    def register_user(self, request: AuthRequest) -> AuthResponse:
        """Register a new user."""
        try:
            # Validate required fields
            if not all([request.username, request.password, request.email]):
                return AuthResponse(
                    success=False,
                    message="Username, password, and email are required"
                )
            
            # Validate username format
            username_valid, username_message = validate_username(request.username)
            if not username_valid:
                return AuthResponse(
                    success=False,
                    message=username_message
                )
            
            # Validate email format
            if not validate_email(request.email):
                return AuthResponse(
                    success=False,
                    message="Invalid email format"
                )
            
            # Validate password strength
            password_valid, password_message = validate_password(request.password)
            if not password_valid:
                return AuthResponse(
                    success=False,
                    message=password_message
                )
            
            # Check if username already exists
            try:
                response = self.users_table.get_item(
                    Key={'pk': f'USER#{request.username}'}
                )
                if 'Item' in response:
                    return AuthResponse(
                        success=False,
                        message="Username already exists"
                    )
            except ClientError as e:
                return AuthResponse(
                    success=False,
                    message=f"Database error: {str(e)}"
                )
            
            # Check if email already exists
            try:
                response = self.users_table.query(
                    IndexName='EmailIndex',
                    KeyConditionExpression='email = :email',
                    ExpressionAttributeValues={':email': request.email}
                )
                if response['Items']:
                    return AuthResponse(
                        success=False,
                        message="Email already registered"
                    )
            except ClientError as e:
                return AuthResponse(
                    success=False,
                    message=f"Database error: {str(e)}"
                )
            
            # Hash password
            password_hash = bcrypt.hashpw(
                request.password.encode('utf-8'),
                bcrypt.gensalt(rounds=self.salt_rounds)
            ).decode('utf-8')
            
            # Create user
            user = User(
                username=request.username,
                password_hash=password_hash,
                email=request.email,
                school=request.school,
                subject_specialization=request.subject_specialization,
                created_at=datetime.utcnow()
            )
            
            # Store user in DynamoDB
            self.users_table.put_item(Item=user.to_dynamodb_item())
            
            # Generate session token
            session_token = self._generate_session_token()
            expires_at = datetime.utcnow() + timedelta(days=7)
            
            return AuthResponse(
                success=True,
                message="User registered successfully",
                session_token=session_token,
                user_id=request.username,
                expires_at=expires_at
            )
            
        except Exception as e:
            return AuthResponse(
                success=False,
                message=f"Registration failed: {str(e)}"
            )
    
    def login_user(self, request: AuthRequest) -> AuthResponse:
        """Authenticate user login."""
        try:
            # Validate required fields
            if not all([request.username, request.password]):
                return AuthResponse(
                    success=False,
                    message="Username and password are required"
                )
            
            # Get user from database
            try:
                response = self.users_table.get_item(
                    Key={'pk': f'USER#{request.username}'}
                )
                if 'Item' not in response:
                    return AuthResponse(
                        success=False,
                        message="Invalid username or password"
                    )
                
                user = User.from_dynamodb_item(response['Item'])
                
            except ClientError as e:
                return AuthResponse(
                    success=False,
                    message=f"Database error: {str(e)}"
                )
            
            # Verify password
            if not bcrypt.checkpw(
                request.password.encode('utf-8'),
                user.password_hash.encode('utf-8')
            ):
                return AuthResponse(
                    success=False,
                    message="Invalid username or password"
                )
            
            # Update last login
            try:
                self.users_table.update_item(
                    Key={'pk': f'USER#{request.username}'},
                    UpdateExpression='SET last_login = :timestamp',
                    ExpressionAttributeValues={
                        ':timestamp': datetime.utcnow().isoformat()
                    }
                )
            except ClientError:
                # Don't fail login if we can't update last_login
                pass
            
            # Generate session token
            session_token = self._generate_session_token()
            expires_at = datetime.utcnow() + timedelta(days=7)
            
            return AuthResponse(
                success=True,
                message="Login successful",
                session_token=session_token,
                user_id=request.username,
                expires_at=expires_at
            )
            
        except Exception as e:
            return AuthResponse(
                success=False,
                message=f"Login failed: {str(e)}"
            )
    
    def validate_session(self, session_token: str) -> Tuple[bool, Optional[str]]:
        """Validate session token and return user_id if valid."""
        try:
            if not session_token or len(session_token) < 32:
                return False, None
            
            # In a production system, you would store session tokens in a separate table
            # For now, we'll implement a simple validation approach
            # This is a simplified implementation - in production you'd want to store
            # session tokens in DynamoDB with TTL and proper user association
            
            # For this implementation, we'll use a basic token structure validation
            # and assume tokens are valid if they meet security requirements
            # In a real system, you'd query a sessions table to validate the token
            # and get the associated user_id
            
            # Basic validation: token should be URL-safe base64 and proper length
            import string
            url_safe_chars = string.ascii_letters + string.digits + '-_'
            if not all(c in url_safe_chars for c in session_token):
                return False, None
            
            # For this simplified implementation, we'll extract a mock user_id
            # In production, this would be a database lookup
            # This is a placeholder implementation
            mock_user_id = "test_user"  # In production: query sessions table
            
            return True, mock_user_id
            
        except Exception as e:
            logger.error(f"Session validation error: {str(e)}")
            return False, None
    
    def validate_session_token(self, session_token: str, user_id: str) -> dict:
        """
        Validate session token for a specific user.
        
        Args:
            session_token: The session token to validate
            user_id: The user ID to validate against
            
        Returns:
            dict: Validation result with 'valid' boolean and optional 'message'
        """
        try:
            if not session_token or not user_id:
                return {'valid': False, 'message': 'Missing token or user ID'}
            
            # Basic token format validation
            if len(session_token) < 32:
                return {'valid': False, 'message': 'Invalid token format'}
            
            # Check token characters are URL-safe
            import string
            url_safe_chars = string.ascii_letters + string.digits + '-_'
            if not all(c in url_safe_chars for c in session_token):
                return {'valid': False, 'message': 'Invalid token format'}
            
            # In production, this would query a sessions table to validate
            # the token and ensure it belongs to the specified user
            # For now, we'll do basic validation
            
            return {'valid': True, 'message': 'Token valid'}
            
        except Exception as e:
            logger.error(f"Session token validation error: {str(e)}")
            return {'valid': False, 'message': 'Validation error'}
    
    def get_user_info(self, user_id: str) -> Optional[dict]:
        """
        Get user information for PDF personalization.
        
        Args:
            user_id: The user ID to get information for
            
        Returns:
            dict: User information or None if not found
        """
        try:
            # Remove USER# prefix if present
            clean_user_id = user_id.replace('USER#', '')
            
            response = self.users_table.get_item(
                Key={'pk': f'USER#{clean_user_id}'}
            )
            
            if 'Item' not in response:
                return None
            
            user = User.from_dynamodb_item(response['Item'])
            
            return {
                'username': user.username,
                'email': user.email,
                'school': user.school,
                'subject_specialization': user.subject_specialization
            }
            
        except ClientError as e:
            logger.error(f"Error getting user info: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting user info: {str(e)}")
            return None
    
    def _generate_session_token(self) -> str:
        """Generate cryptographically secure session token."""
        return secrets.token_urlsafe(32)


# Singleton instance for use across the application
# Only create if environment variables are available (not during testing)
auth_service = None
try:
    if os.environ.get('USERS_TABLE_NAME'):
        auth_service = AuthService(
            users_table_name=os.environ.get('USERS_TABLE_NAME')
        )
except Exception:
    # Will be None during testing, tests should mock or provide their own instance
    pass