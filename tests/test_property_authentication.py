"""
Property-based tests for authentication functionality.
Tests universal correctness properties for user login and session management.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import Mock, patch
import boto3
from moto import mock_aws
import bcrypt
from datetime import datetime, timedelta
import uuid

from src.models.user import User, AuthRequest, AuthResponse
from src.services.auth_service import AuthService


# Test data strategies
@st.composite
def valid_usernames(draw):
    """Generate valid usernames (3-50 chars, alphanumeric + underscore)."""
    # Use UUID to ensure uniqueness
    unique_id = str(uuid.uuid4()).replace('-', '')[:8]
    length = draw(st.integers(min_value=3, max_value=35))  # Leave room for unique_id
    base_username = draw(st.text(alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_', min_size=length, max_size=length))
    return f"{base_username}_{unique_id}"


@st.composite
def valid_emails(draw):
    """Generate valid email addresses."""
    # Use UUID to ensure uniqueness
    unique_id = str(uuid.uuid4()).replace('-', '')[:8]
    local_part = draw(st.text(
        alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-',
        min_size=1, max_size=15
    ))
    domain = draw(st.text(
        alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-',
        min_size=1, max_size=15
    ))
    tld = draw(st.sampled_from(['com', 'org', 'edu', 'gov', 'net']))
    return f"{local_part}_{unique_id}@{domain}.{tld}"


@st.composite
def valid_passwords(draw):
    """Generate valid passwords meeting strength requirements."""
    # Ensure at least one of each required character type using ASCII only
    upper = draw(st.text(alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZ', min_size=1, max_size=3))
    lower = draw(st.text(alphabet='abcdefghijklmnopqrstuvwxyz', min_size=1, max_size=3))
    digit = draw(st.text(alphabet='0123456789', min_size=1, max_size=3))
    special = draw(st.text(alphabet='!@#$%^&*(),.?":{}|<>', min_size=1, max_size=3))
    
    # Add additional random characters to reach minimum length
    additional_length = max(0, 8 - len(upper) - len(lower) - len(digit) - len(special))
    additional = draw(st.text(
        alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(),.?":{}|<>',
        min_size=additional_length, max_size=additional_length + 15
    ))
    
    # Combine and shuffle
    all_chars = list(upper + lower + digit + special + additional)
    draw(st.randoms()).shuffle(all_chars)
    return ''.join(all_chars)


@st.composite
def registered_user_data(draw):
    """Generate data for a user that will be registered."""
    return {
        'username': draw(valid_usernames()),
        'password': draw(valid_passwords()),
        'email': draw(valid_emails()),
        'school': draw(st.one_of(st.none(), st.text(max_size=100))),
        'subject_specialization': draw(st.one_of(st.none(), st.text(max_size=50)))
    }


class TestAuthenticationProperties:
    """Property-based tests for authentication token generation."""
    
    def setup_method(self, method):
        """Set up test environment with mocked DynamoDB."""
        # Start AWS mock
        self.mock = mock_aws()
        self.mock.start()
        
        # Create mock DynamoDB table
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-2')
        
        # Delete table if it exists
        try:
            existing_table = dynamodb.Table('test-users')
            existing_table.delete()
            existing_table.wait_until_not_exists()
        except:
            pass
        
        table = dynamodb.create_table(
            TableName='test-users',
            KeySchema=[
                {'AttributeName': 'pk', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'pk', 'AttributeType': 'S'},
                {'AttributeName': 'email', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'EmailIndex',
                    'KeySchema': [
                        {'AttributeName': 'email', 'KeyType': 'HASH'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                }
            ],
            BillingMode='PROVISIONED',
            ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )
        
        # Wait for table to be created
        table.wait_until_exists()
        
        self.auth_service = AuthService('test-users', 'eu-west-2')
    
    def teardown_method(self, method):
        """Clean up after test."""
        self.mock.stop()
    
    @given(registered_user_data())
    @settings(max_examples=20, deadline=10000)
    def test_property_13_authentication_token_generation(self, user_data):
        """
        Property 13: Authentication Token Generation
        
        GIVEN a registered user with valid credentials
        WHEN the user logs in
        THEN a session token is generated
        AND the token is cryptographically secure (at least 32 characters)
        AND the token is unique for each login attempt
        AND the login updates the last_login timestamp
        """
        # Register user first
        registration_request = AuthRequest(
            action='register',
            username=user_data['username'],
            password=user_data['password'],
            email=user_data['email'],
            school=user_data['school'],
            subject_specialization=user_data['subject_specialization']
        )
        
        reg_response = self.auth_service.register_user(registration_request)
        assert reg_response.success, f"Registration failed: {reg_response.message}"
        
        # Login with correct credentials
        login_request = AuthRequest(
            action='login',
            username=user_data['username'],
            password=user_data['password']
        )
        
        login_response = self.auth_service.login_user(login_request)
        
        # Verify login succeeded
        assert login_response.success, f"Login failed: {login_response.message}"
        assert login_response.session_token is not None
        assert login_response.user_id == user_data['username']
        assert login_response.expires_at is not None
        
        # Verify token is cryptographically secure (at least 32 characters)
        assert len(login_response.session_token) >= 32, "Session token too short"
        
        # Verify token contains only URL-safe characters
        import string
        url_safe_chars = string.ascii_letters + string.digits + '-_'
        assert all(c in url_safe_chars for c in login_response.session_token), "Token contains unsafe characters"
        
        # Verify expiration is in the future (7 days)
        now = datetime.utcnow()
        expected_expiry = now + timedelta(days=7)
        time_diff = abs((login_response.expires_at - expected_expiry).total_seconds())
        assert time_diff < 60, "Expiration time not set correctly"  # Allow 1 minute tolerance
        
        # Login again and verify token is different (uniqueness)
        second_login_response = self.auth_service.login_user(login_request)
        assert second_login_response.success
        assert second_login_response.session_token != login_response.session_token, "Tokens should be unique"
    
    @given(registered_user_data())
    @settings(max_examples=20, deadline=10000)
    def test_property_invalid_credentials_rejection(self, user_data):
        """
        Property: Invalid Credentials Rejection
        
        GIVEN a registered user
        WHEN login is attempted with wrong password
        THEN the login should fail
        AND no session token should be generated
        """
        # Register user first
        registration_request = AuthRequest(
            action='register',
            username=user_data['username'],
            password=user_data['password'],
            email=user_data['email']
        )
        
        reg_response = self.auth_service.register_user(registration_request)
        assert reg_response.success
        
        # Login with wrong password
        wrong_password = user_data['password'] + 'WRONG'
        login_request = AuthRequest(
            action='login',
            username=user_data['username'],
            password=wrong_password
        )
        
        login_response = self.auth_service.login_user(login_request)
        
        # Verify login failed
        assert not login_response.success
        assert login_response.session_token is None
        assert "invalid" in login_response.message.lower()
    
    @given(valid_usernames(), valid_passwords())
    @settings(max_examples=20, deadline=5000)
    def test_property_nonexistent_user_rejection(self, username, password):
        """
        Property: Nonexistent User Rejection
        
        GIVEN a username that doesn't exist in the system
        WHEN login is attempted
        THEN the login should fail
        AND no session token should be generated
        """
        login_request = AuthRequest(
            action='login',
            username=username,
            password=password
        )
        
        login_response = self.auth_service.login_user(login_request)
        
        # Verify login failed
        assert not login_response.success
        assert login_response.session_token is None
        assert "invalid" in login_response.message.lower()
    
    @given(st.text(max_size=31))  # Token too short
    @settings(max_examples=10, deadline=5000)
    def test_property_invalid_session_token_rejection(self, invalid_token):
        """
        Property: Invalid Session Token Rejection
        
        GIVEN an invalid session token (too short or malformed)
        WHEN session validation is attempted
        THEN the validation should fail
        """
        is_valid, user_id = self.auth_service.validate_session(invalid_token)
        
        assert not is_valid
        assert user_id is None
    
    def test_property_empty_session_token_rejection(self):
        """
        Property: Empty Session Token Rejection
        
        GIVEN an empty or None session token
        WHEN session validation is attempted
        THEN the validation should fail
        """
        # Test None token
        is_valid, user_id = self.auth_service.validate_session(None)
        assert not is_valid
        assert user_id is None
        
        # Test empty string token
        is_valid, user_id = self.auth_service.validate_session('')
        assert not is_valid
        assert user_id is None
    
    @given(registered_user_data())
    @settings(max_examples=10, deadline=10000)
    def test_property_last_login_update(self, user_data):
        """
        Property: Last Login Timestamp Update
        
        GIVEN a registered user
        WHEN the user logs in successfully
        THEN the last_login timestamp should be updated in the database
        """
        # Register user first
        registration_request = AuthRequest(
            action='register',
            username=user_data['username'],
            password=user_data['password'],
            email=user_data['email']
        )
        
        reg_response = self.auth_service.register_user(registration_request)
        assert reg_response.success
        
        # Get initial user data
        users_table = self.auth_service.users_table
        initial_response = users_table.get_item(
            Key={'pk': f'USER#{user_data["username"]}'}
        )
        initial_user = initial_response['Item']
        initial_last_login = initial_user.get('last_login')
        
        # Login
        login_request = AuthRequest(
            action='login',
            username=user_data['username'],
            password=user_data['password']
        )
        
        login_response = self.auth_service.login_user(login_request)
        assert login_response.success
        
        # Check that last_login was updated
        updated_response = users_table.get_item(
            Key={'pk': f'USER#{user_data["username"]}'}
        )
        updated_user = updated_response['Item']
        updated_last_login = updated_user.get('last_login')
        
        # Verify last_login was updated
        assert updated_last_login is not None
        if initial_last_login:
            assert updated_last_login != initial_last_login
        
        # Verify timestamp is recent (within last minute)
        last_login_time = datetime.fromisoformat(updated_last_login)
        now = datetime.utcnow()
        time_diff = (now - last_login_time).total_seconds()
        assert time_diff < 60, "Last login timestamp not recent enough"
    
    @given(st.text(min_size=1, max_size=2))  # Username too short
    @settings(max_examples=10, deadline=5000)
    def test_property_missing_credentials_rejection(self, short_text):
        """
        Property: Missing Credentials Rejection
        
        GIVEN missing username or password
        WHEN login is attempted
        THEN the login should fail with appropriate error
        """
        # Test missing username
        login_request = AuthRequest(
            action='login',
            username=None,
            password='ValidPassword123!'
        )
        
        response = self.auth_service.login_user(login_request)
        assert not response.success
        assert "required" in response.message.lower()
        
        # Test missing password
        login_request = AuthRequest(
            action='login',
            username='validuser',
            password=None
        )
        
        response = self.auth_service.login_user(login_request)
        assert not response.success
        assert "required" in response.message.lower()


if __name__ == "__main__":
    pytest.main([__file__])