"""
Property-based tests for user registration functionality.
Tests universal correctness properties for user account creation.
"""

import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import Mock, patch
import boto3
from moto import mock_aws
import bcrypt
from datetime import datetime
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
def valid_registration_requests(draw):
    """Generate valid registration requests."""
    return AuthRequest(
        action='register',
        username=draw(valid_usernames()),
        password=draw(valid_passwords()),
        email=draw(valid_emails()),
        school=draw(st.one_of(st.none(), st.text(max_size=100))),
        subject_specialization=draw(st.one_of(st.none(), st.text(max_size=50)))
    )


class TestUserRegistrationProperties:
    """Property-based tests for user registration storage."""
    
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
    
    @given(valid_registration_requests())
    @settings(max_examples=20, deadline=10000)
    def test_property_12_user_registration_storage(self, registration_request):
        """
        Property 12: User Registration Storage
        
        GIVEN any valid registration request
        WHEN the user is registered
        THEN the user data is stored correctly in DynamoDB
        AND the password is properly hashed
        AND the user can be retrieved by username
        AND the user can be retrieved by email
        """
        # Register user
        response = self.auth_service.register_user(registration_request)
        
        # Verify registration succeeded
        assert response.success, f"Registration failed: {response.message}"
        assert response.session_token is not None
        assert response.user_id == registration_request.username
        assert response.expires_at is not None
        
        # Verify user stored in database by username
        users_table = self.auth_service.users_table
        user_response = users_table.get_item(
            Key={'pk': f'USER#{registration_request.username}'}
        )
        
        assert 'Item' in user_response, "User not found in database"
        stored_user = user_response['Item']
        
        # Verify stored data
        assert stored_user['username'] == registration_request.username
        assert stored_user['email'] == registration_request.email
        assert 'password_hash' in stored_user
        assert stored_user['password_hash'] != registration_request.password  # Password should be hashed
        
        # Verify password hash is valid bcrypt hash
        assert bcrypt.checkpw(
            registration_request.password.encode('utf-8'),
            stored_user['password_hash'].encode('utf-8')
        ), "Password hash verification failed"
        
        # Verify optional fields
        if registration_request.school:
            assert stored_user.get('school') == registration_request.school
        if registration_request.subject_specialization:
            assert stored_user.get('subject_specialization') == registration_request.subject_specialization
        
        # Verify timestamps
        assert 'created_at' in stored_user
        created_at = datetime.fromisoformat(stored_user['created_at'])
        assert isinstance(created_at, datetime)
        
        # Verify user can be retrieved by email
        email_response = users_table.query(
            IndexName='EmailIndex',
            KeyConditionExpression='email = :email',
            ExpressionAttributeValues={':email': registration_request.email}
        )
        
        assert email_response['Items'], "User not found by email lookup"
        assert email_response['Items'][0]['username'] == registration_request.username
    
    @given(valid_registration_requests())
    @settings(max_examples=20, deadline=10000)
    def test_property_duplicate_username_prevention(self, registration_request):
        """
        Property: Duplicate Username Prevention
        
        GIVEN a user is already registered
        WHEN another registration attempt is made with the same username
        THEN the registration should fail
        AND the original user data should remain unchanged
        """
        # Register user first time
        first_response = self.auth_service.register_user(registration_request)
        assert first_response.success, f"First registration failed: {first_response.message}"
        
        # Attempt to register same username again
        duplicate_request = AuthRequest(
            action='register',
            username=registration_request.username,  # Same username
            password='DifferentPassword123!',  # Different password
            email='different@example.com'  # Different email
        )
        
        second_response = self.auth_service.register_user(duplicate_request)
        
        # Verify second registration failed
        assert not second_response.success
        assert "already exists" in second_response.message.lower()
        
        # Verify original user data unchanged
        users_table = self.auth_service.users_table
        user_response = users_table.get_item(
            Key={'pk': f'USER#{registration_request.username}'}
        )
        
        stored_user = user_response['Item']
        assert stored_user['email'] == registration_request.email  # Original email preserved
    
    @given(valid_registration_requests())
    @settings(max_examples=20, deadline=10000)
    def test_property_duplicate_email_prevention(self, registration_request):
        """
        Property: Duplicate Email Prevention
        
        GIVEN a user is already registered with an email
        WHEN another registration attempt is made with the same email
        THEN the registration should fail
        """
        # Register user first time
        first_response = self.auth_service.register_user(registration_request)
        assert first_response.success, f"First registration failed: {first_response.message}"
        
        # Attempt to register different username with same email
        duplicate_request = AuthRequest(
            action='register',
            username='different_user',  # Different username
            password='DifferentPassword123!',
            email=registration_request.email  # Same email
        )
        
        second_response = self.auth_service.register_user(duplicate_request)
        
        # Verify second registration failed
        assert not second_response.success
        assert "already registered" in second_response.message.lower()
    
    @given(st.text(max_size=2))  # Invalid username (too short)
    @settings(max_examples=10, deadline=5000)
    def test_property_invalid_username_rejection(self, invalid_username):
        """
        Property: Invalid Username Rejection
        
        GIVEN an invalid username (too short)
        WHEN registration is attempted
        THEN the registration should fail with appropriate error
        """
        request = AuthRequest(
            action='register',
            username=invalid_username,
            password='ValidPassword123!',
            email='valid@example.com'
        )
        
        response = self.auth_service.register_user(request)
        assert not response.success
    
    @given(st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll')), max_size=7))  # Invalid password (no digits/special chars)
    @settings(max_examples=10, deadline=5000)
    def test_property_weak_password_rejection(self, weak_password):
        """
        Property: Weak Password Rejection
        
        GIVEN a weak password that doesn't meet requirements
        WHEN registration is attempted
        THEN the registration should fail with appropriate error
        """
        request = AuthRequest(
            action='register',
            username='validuser',
            password=weak_password,
            email='valid@example.com'
        )
        
        response = self.auth_service.register_user(request)
        assert not response.success
        assert "password" in response.message.lower()
    
    @given(st.text(alphabet=st.characters(blacklist_characters='@'), max_size=50))  # Invalid email (no @)
    @settings(max_examples=10, deadline=5000)
    def test_property_invalid_email_rejection(self, invalid_email):
        """
        Property: Invalid Email Rejection
        
        GIVEN an invalid email format
        WHEN registration is attempted
        THEN the registration should fail with appropriate error
        """
        request = AuthRequest(
            action='register',
            username='validuser',
            password='ValidPassword123!',
            email=invalid_email
        )
        
        response = self.auth_service.register_user(request)
        assert not response.success
        assert "email" in response.message.lower()


if __name__ == "__main__":
    pytest.main([__file__])