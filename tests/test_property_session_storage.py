"""
Property-based tests for session storage functionality.

Tests Property 14: Session Storage with TTL
For any question generation session, the system should store the session data 
in DynamoDB Sessions table with proper TTL expiration.
"""

import json
import time
import uuid
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import Mock, patch, MagicMock

import pytest
from hypothesis import given, strategies as st, settings
from moto import mock_aws

from src.services.session_service import SessionService


# Test data generators
@st.composite
def generate_user_id(draw):
    """Generate valid user ID."""
    username = draw(st.text(min_size=3, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    return f"USER#{username}"


@st.composite
def generate_query(draw):
    """Generate user query string."""
    return draw(st.text(min_size=5, max_size=200))


@st.composite
def generate_question(draw):
    """Generate a question object."""
    return {
        'id': str(uuid.uuid4()),
        'question_text': draw(st.text(min_size=10, max_size=500)),
        'mark_scheme': draw(st.text(min_size=5, max_size=200)),
        'difficulty_score': draw(st.integers(min_value=1, max_value=10)),
        'topic': draw(st.sampled_from(['fractions', 'algebra', 'geometry', 'statistics'])),
        'subtopic': draw(st.text(min_size=3, max_size=50)),
        'assessment_objective': draw(st.sampled_from(['AO1', 'AO2', 'AO3'])),
        'learning_objective': draw(st.text(min_size=10, max_size=100))
    }


@st.composite
def generate_questions_list(draw):
    """Generate list of questions."""
    count = draw(st.integers(min_value=1, max_value=20))
    return [draw(generate_question()) for _ in range(count)]


@st.composite
def generate_session_metadata(draw):
    """Generate session metadata."""
    return {
        'topic': draw(st.sampled_from(['fractions', 'algebra', 'geometry', 'statistics'])),
        'tier': draw(st.sampled_from(['foundation', 'higher'])),
        'question_count': draw(st.integers(min_value=1, max_value=20)),
        'total_marks': draw(st.integers(min_value=1, max_value=100)),
        'generation_time': draw(st.floats(min_value=0.1, max_value=10.0)),
        'specification_version': draw(st.text(min_size=3, max_size=10))
    }


class TestSessionStorageProperties:
    """Property-based tests for session storage."""
    
    @mock_aws
    def setup_method(self, method):
        """Set up test environment with mocked DynamoDB."""
        # Set AWS credentials for moto
        os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
        os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
        os.environ['AWS_SECURITY_TOKEN'] = 'testing'
        os.environ['AWS_SESSION_TOKEN'] = 'testing'
        os.environ['AWS_DEFAULT_REGION'] = 'eu-west-2'
        
        import boto3
        
        # Create mock DynamoDB table
        self.dynamodb = boto3.resource('dynamodb', region_name='eu-west-2')
        
        # Create Sessions table
        self.table = self.dynamodb.create_table(
            TableName='test-sessions-table',
            KeySchema=[
                {'AttributeName': 'pk', 'KeyType': 'HASH'},
                {'AttributeName': 'sk', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'pk', 'AttributeType': 'S'},
                {'AttributeName': 'sk', 'AttributeType': 'S'},
                {'AttributeName': 'user_id', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'UserSessionsIndex',
                    'KeySchema': [
                        {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                        {'AttributeName': 'sk', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        
        # Initialize session service with test table
        self.session_service = SessionService(region='eu-west-2', table=self.table)
    
    @given(
        user_id=generate_user_id(),
        query=generate_query(),
        questions=generate_questions_list(),
        metadata=generate_session_metadata()
    )
    @settings(max_examples=50, deadline=10000)
    @mock_aws
    def test_session_storage_with_ttl(self, user_id, query, questions, metadata):
        """
        Feature: gcse-question-generator-v2, Property 14: Session Storage with TTL
        For any question generation session, the system should store the session data 
        in DynamoDB Sessions table with proper TTL expiration.
        **Validates: Requirements 5.3**
        """
        # Set AWS credentials for moto
        os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
        os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
        os.environ['AWS_SECURITY_TOKEN'] = 'testing'
        os.environ['AWS_SESSION_TOKEN'] = 'testing'
        os.environ['AWS_DEFAULT_REGION'] = 'eu-west-2'
        
        # Set up test environment with mocked DynamoDB
        import boto3
        
        # Create mock DynamoDB table
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-2')
        
        # Create Sessions table
        table = dynamodb.create_table(
            TableName='test-sessions-table',
            KeySchema=[
                {'AttributeName': 'pk', 'KeyType': 'HASH'},
                {'AttributeName': 'sk', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'pk', 'AttributeType': 'S'},
                {'AttributeName': 'sk', 'AttributeType': 'S'},
                {'AttributeName': 'user_id', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'UserSessionsIndex',
                    'KeySchema': [
                        {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                        {'AttributeName': 'sk', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        
        # Initialize session service with test table
        session_service = SessionService(region='eu-west-2', table=table)
        
        # Arrange
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Act
        session_id = session_service.create_session(
            user_id=user_id,
            query=query,
            generated_questions=questions,
            metadata=metadata,
            request_id=request_id
        )
        
        # Assert - Session ID should be returned
        assert session_id is not None
        assert isinstance(session_id, str)
        assert len(session_id) > 0
        
        # Verify session was stored in DynamoDB
        response = table.query(
            KeyConditionExpression='pk = :pk',
            ExpressionAttributeValues={
                ':pk': f'SESSION#{session_id}'
            }
        )
        
        items = response.get('Items', [])
        assert len(items) == 1, "Session should be stored in DynamoDB"
        
        stored_session = items[0]
        
        # Verify session structure
        assert stored_session['session_id'] == session_id
        assert stored_session['user_id'] == user_id
        assert stored_session['query'] == query
        assert stored_session['generated_questions'] == questions
        
        # Verify TTL is set correctly (7 days = 604800 seconds)
        assert 'ttl' in stored_session
        ttl_value = stored_session['ttl']
        expected_ttl = stored_session['timestamp'] + 604800
        assert ttl_value == expected_ttl, "TTL should be set to 7 days from creation"
        
        # Verify TTL is in the future
        current_time = int(time.time())
        assert ttl_value > current_time, "TTL should be in the future"
        
        # Verify TTL is approximately 7 days from now (allow 60 second variance)
        expected_expiry = current_time + 604800
        assert abs(ttl_value - expected_expiry) <= 60, "TTL should be approximately 7 days from now"
        
        # Verify metadata is stored correctly
        stored_metadata = stored_session['metadata']
        for key, value in metadata.items():
            stored_value = stored_metadata[key]
            # Handle Decimal conversion for floats
            if isinstance(value, float):
                assert float(stored_value) == value, f"Metadata field {key} should be preserved"
            else:
                assert stored_value == value, f"Metadata field {key} should be preserved"
        
        # Verify additional metadata fields
        assert 'created_at' in stored_metadata
        assert 'request_id' in stored_metadata
        assert stored_metadata['request_id'] == request_id
        
        # Verify timestamp is reasonable
        assert 'timestamp' in stored_session
        session_timestamp = stored_session['timestamp']
        # Convert Decimal to float for comparison
        if hasattr(session_timestamp, '__float__'):
            session_timestamp = float(session_timestamp)
        assert abs(session_timestamp - start_time) <= 5, "Timestamp should be close to creation time"
    
    @given(
        user_id=generate_user_id(),
        query=generate_query(),
        questions=generate_questions_list(),
        metadata=generate_session_metadata()
    )
    @settings(max_examples=30, deadline=10000)
    def test_session_retrieval_after_storage(self, user_id, query, questions, metadata):
        """
        Test that stored sessions can be retrieved correctly.
        This extends Property 14 to verify the complete storage-retrieval cycle.
        """
        # Arrange
        request_id = str(uuid.uuid4())
        
        # Act - Store session
        session_id = self.session_service.create_session(
            user_id=user_id,
            query=query,
            generated_questions=questions,
            metadata=metadata,
            request_id=request_id
        )
        
        # Act - Retrieve session
        retrieved_session = self.session_service.get_session_details(session_id, user_id)
        
        # Assert - Session should be retrievable
        assert retrieved_session is not None
        assert retrieved_session['session_id'] == session_id
        assert retrieved_session['user_id'] == user_id
        assert retrieved_session['query'] == query
        assert retrieved_session['generated_questions'] == questions
        
        # Verify metadata preservation
        retrieved_metadata = retrieved_session['metadata']
        for key, value in metadata.items():
            assert retrieved_metadata[key] == value
    
    @given(
        user_id=generate_user_id(),
        query=generate_query(),
        questions=generate_questions_list(),
        metadata=generate_session_metadata()
    )
    @settings(max_examples=20, deadline=10000)
    def test_session_user_isolation(self, user_id, query, questions, metadata):
        """
        Test that sessions are properly isolated between users.
        This verifies the security aspect of Property 14.
        """
        # Arrange
        request_id = str(uuid.uuid4())
        other_user_id = f"USER#{uuid.uuid4().hex[:10]}"
        
        # Act - Store session for first user
        session_id = self.session_service.create_session(
            user_id=user_id,
            query=query,
            generated_questions=questions,
            metadata=metadata,
            request_id=request_id
        )
        
        # Act - Try to retrieve session as different user
        retrieved_session = self.session_service.get_session_details(session_id, other_user_id)
        
        # Assert - Other user should not be able to access the session
        assert retrieved_session is None, "Users should not be able to access other users' sessions"
        
        # Act - Original user should still be able to access
        original_user_session = self.session_service.get_session_details(session_id, user_id)
        
        # Assert - Original user should have access
        assert original_user_session is not None
        assert original_user_session['session_id'] == session_id
    
    @given(
        user_id=generate_user_id(),
        sessions_count=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=20, deadline=15000)
    def test_multiple_sessions_storage(self, user_id, sessions_count):
        """
        Test that multiple sessions can be stored for the same user.
        This verifies scalability aspects of Property 14.
        """
        # Arrange
        stored_session_ids = []
        
        # Act - Store multiple sessions
        for i in range(sessions_count):
            query = f"Test query {i}"
            questions = [{'id': str(uuid.uuid4()), 'question_text': f'Question {i}', 'mark_scheme': f'Marks {i}', 'difficulty_score': (i % 10) + 1, 'topic': 'test', 'subtopic': 'test', 'assessment_objective': 'AO1', 'learning_objective': 'test'}]
            metadata = {'topic': 'test', 'tier': 'foundation', 'question_count': 1, 'total_marks': 5, 'generation_time': 1.0, 'specification_version': 'v1'}
            request_id = str(uuid.uuid4())
            
            session_id = self.session_service.create_session(
                user_id=user_id,
                query=query,
                generated_questions=questions,
                metadata=metadata,
                request_id=request_id
            )
            
            stored_session_ids.append(session_id)
        
        # Assert - All sessions should be stored
        assert len(stored_session_ids) == sessions_count
        assert len(set(stored_session_ids)) == sessions_count, "All session IDs should be unique"
        
        # Act - Retrieve user sessions
        user_sessions = self.session_service.get_user_sessions(user_id, limit=50)
        
        # Assert - All sessions should be retrievable
        assert user_sessions['count'] == sessions_count
        retrieved_session_ids = [s['session_id'] for s in user_sessions['sessions']]
        
        for session_id in stored_session_ids:
            assert session_id in retrieved_session_ids, f"Session {session_id} should be retrievable"
    
    @given(
        user_id=generate_user_id(),
        sessions_count=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=20, deadline=15000)
    @mock_aws
    def test_session_history_retrieval(self, user_id, sessions_count):
        """
        Feature: gcse-question-generator-v2, Property 15: Session History Retrieval
        For any user requesting their history, the system should retrieve all past sessions 
        from the Sessions table matching their user ID.
        **Validates: Requirements 5.4**
        """
        # Set AWS credentials for moto
        os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
        os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
        os.environ['AWS_SECURITY_TOKEN'] = 'testing'
        os.environ['AWS_SESSION_TOKEN'] = 'testing'
        os.environ['AWS_DEFAULT_REGION'] = 'eu-west-2'
        
        # Set up test environment with mocked DynamoDB
        import boto3
        
        # Create mock DynamoDB table
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-2')
        
        # Create Sessions table
        table = dynamodb.create_table(
            TableName='test-sessions-table',
            KeySchema=[
                {'AttributeName': 'pk', 'KeyType': 'HASH'},
                {'AttributeName': 'sk', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'pk', 'AttributeType': 'S'},
                {'AttributeName': 'sk', 'AttributeType': 'S'},
                {'AttributeName': 'user_id', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'UserSessionsIndex',
                    'KeySchema': [
                        {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                        {'AttributeName': 'sk', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        
        # Initialize session service with test table
        session_service = SessionService(region='eu-west-2', table=table)
        
        # Arrange - Create multiple sessions for the user
        created_sessions = []
        for i in range(sessions_count):
            query = f"Test query {i}"
            questions = [{'id': str(uuid.uuid4()), 'question_text': f'Question {i}', 'mark_scheme': f'Marks {i}', 'difficulty_score': (i % 10) + 1, 'topic': 'test', 'subtopic': 'test', 'assessment_objective': 'AO1', 'learning_objective': 'test'}]
            metadata = {'topic': 'test', 'tier': 'foundation', 'question_count': 1, 'total_marks': 5, 'generation_time': 1.0, 'specification_version': 'v1'}
            request_id = str(uuid.uuid4())
            
            session_id = session_service.create_session(
                user_id=user_id,
                query=query,
                generated_questions=questions,
                metadata=metadata,
                request_id=request_id
            )
            
            created_sessions.append({
                'session_id': session_id,
                'query': query,
                'questions': questions,
                'metadata': metadata
            })
        
        # Act - Retrieve user sessions
        retrieved_sessions = session_service.get_user_sessions(user_id, limit=50)
        
        # Assert - All created sessions should be retrievable
        assert retrieved_sessions['count'] == sessions_count, f"Should retrieve {sessions_count} sessions"
        assert len(retrieved_sessions['sessions']) == sessions_count, f"Should return {sessions_count} sessions"
        
        # Verify session data integrity
        retrieved_session_ids = {s['session_id'] for s in retrieved_sessions['sessions']}
        created_session_ids = {s['session_id'] for s in created_sessions}
        
        assert retrieved_session_ids == created_session_ids, "All created sessions should be retrievable"
        
        # Verify session metadata is preserved
        for retrieved_session in retrieved_sessions['sessions']:
            session_id = retrieved_session['session_id']
            
            # Find corresponding created session
            created_session = next(s for s in created_sessions if s['session_id'] == session_id)
            
            # Verify basic fields
            assert retrieved_session['query'] == created_session['query']
            assert retrieved_session['question_count'] == len(created_session['questions'])
            
            # Verify metadata fields
            assert retrieved_session['metadata']['topic'] == created_session['metadata']['topic']
            assert retrieved_session['metadata']['tier'] == created_session['metadata']['tier']
            assert retrieved_session['metadata']['total_marks'] == created_session['metadata']['total_marks']
        
        # Verify sessions are ordered by timestamp (newest first)
        timestamps = [s['timestamp'] for s in retrieved_sessions['sessions']]
        assert timestamps == sorted(timestamps, reverse=True), "Sessions should be ordered by timestamp descending"
        
        # Test pagination behavior
        if sessions_count > 1:
            # Test with limit of 1
            paginated_result = session_service.get_user_sessions(user_id, limit=1)
            assert paginated_result['count'] == 1, "Should respect limit parameter"
            assert paginated_result['has_more'] == True, "Should indicate more sessions available"
            assert 'last_evaluated_key' in paginated_result, "Should provide pagination key"
    
    @given(
        user_id=generate_user_id(),
        other_user_id=generate_user_id()
    )
    @settings(max_examples=10, deadline=10000)
    @mock_aws
    def test_session_retrieval_user_isolation(self, user_id, other_user_id):
        """
        Test that session retrieval properly isolates users.
        This extends Property 15 to verify security aspects.
        """
        # Ensure users are different
        if user_id == other_user_id:
            other_user_id = f"USER#{uuid.uuid4().hex[:10]}"
        
        # Set AWS credentials for moto
        os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
        os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
        os.environ['AWS_SECURITY_TOKEN'] = 'testing'
        os.environ['AWS_SESSION_TOKEN'] = 'testing'
        os.environ['AWS_DEFAULT_REGION'] = 'eu-west-2'
        
        # Set up test environment with mocked DynamoDB
        import boto3
        
        # Create mock DynamoDB table
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-2')
        
        # Create Sessions table
        table = dynamodb.create_table(
            TableName='test-sessions-table',
            KeySchema=[
                {'AttributeName': 'pk', 'KeyType': 'HASH'},
                {'AttributeName': 'sk', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'pk', 'AttributeType': 'S'},
                {'AttributeName': 'sk', 'AttributeType': 'S'},
                {'AttributeName': 'user_id', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'UserSessionsIndex',
                    'KeySchema': [
                        {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                        {'AttributeName': 'sk', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        
        # Initialize session service with test table
        session_service = SessionService(region='eu-west-2', table=table)
        
        # Arrange - Create sessions for both users
        user1_session_id = session_service.create_session(
            user_id=user_id,
            query="User 1 query",
            generated_questions=[{'id': 'q1', 'question_text': 'Q1', 'mark_scheme': 'M1', 'difficulty_score': 5, 'topic': 'test', 'subtopic': 'test', 'assessment_objective': 'AO1', 'learning_objective': 'test'}],
            metadata={'topic': 'test', 'tier': 'foundation', 'question_count': 1, 'total_marks': 5, 'generation_time': 1.0, 'specification_version': 'v1'},
            request_id='req1'
        )
        
        user2_session_id = session_service.create_session(
            user_id=other_user_id,
            query="User 2 query",
            generated_questions=[{'id': 'q2', 'question_text': 'Q2', 'mark_scheme': 'M2', 'difficulty_score': 7, 'topic': 'test', 'subtopic': 'test', 'assessment_objective': 'AO2', 'learning_objective': 'test'}],
            metadata={'topic': 'test', 'tier': 'higher', 'question_count': 1, 'total_marks': 8, 'generation_time': 1.5, 'specification_version': 'v1'},
            request_id='req2'
        )
        
        # Act - Retrieve sessions for each user
        user1_sessions = session_service.get_user_sessions(user_id)
        user2_sessions = session_service.get_user_sessions(other_user_id)
        
        # Assert - Each user should only see their own sessions
        assert user1_sessions['count'] == 1, "User 1 should see exactly 1 session"
        assert user2_sessions['count'] == 1, "User 2 should see exactly 1 session"
        
        assert user1_sessions['sessions'][0]['session_id'] == user1_session_id
        assert user2_sessions['sessions'][0]['session_id'] == user2_session_id
        
        assert user1_sessions['sessions'][0]['query'] == "User 1 query"
        assert user2_sessions['sessions'][0]['query'] == "User 2 query"
        
        # Verify no cross-contamination
        user1_session_ids = {s['session_id'] for s in user1_sessions['sessions']}
        user2_session_ids = {s['session_id'] for s in user2_sessions['sessions']}
        
        assert user1_session_ids.isdisjoint(user2_session_ids), "Users should not see each other's sessions"
    
    @mock_aws
    def test_table_connection(self):
        """Test that the mocked table works."""
        # Set AWS credentials for moto
        os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
        os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
        os.environ['AWS_SECURITY_TOKEN'] = 'testing'
        os.environ['AWS_SESSION_TOKEN'] = 'testing'
        os.environ['AWS_DEFAULT_REGION'] = 'eu-west-2'
        
        # Set up test environment with mocked DynamoDB
        import boto3
        
        # Create mock DynamoDB table
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-2')
        
        # Create Sessions table
        table = dynamodb.create_table(
            TableName='test-sessions-table',
            KeySchema=[
                {'AttributeName': 'pk', 'KeyType': 'HASH'},
                {'AttributeName': 'sk', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'pk', 'AttributeType': 'S'},
                {'AttributeName': 'sk', 'AttributeType': 'S'},
                {'AttributeName': 'user_id', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'UserSessionsIndex',
                    'KeySchema': [
                        {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                        {'AttributeName': 'sk', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        
        # Test direct table access
        response = table.put_item(
            Item={
                'pk': 'TEST#123',
                'sk': 'TIMESTAMP#123',
                'test_data': 'test_value'
            }
        )
        
        # Verify item was stored
        response = table.get_item(
            Key={
                'pk': 'TEST#123',
                'sk': 'TIMESTAMP#123'
            }
        )
        
        assert 'Item' in response
        assert response['Item']['test_data'] == 'test_value'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])