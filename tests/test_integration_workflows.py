"""
Integration tests for complete user workflows in GCSE Question Generator V2.
Tests end-to-end user journeys: register → login → generate → feedback → export.

Requirements: All functional requirements
"""

import json
import pytest
import boto3
import requests
import time
from unittest.mock import patch, MagicMock
from moto import mock_aws
import os
from datetime import datetime, timedelta

# Import our services for testing
from src.lambda_handlers.auth_lambda import lambda_handler as auth_handler
from src.lambda_handlers.interpret_lambda import lambda_handler as interpret_handler
from src.lambda_handlers.generate_lambda import lambda_handler as generate_handler
from src.lambda_handlers.feedback_lambda import handler as feedback_handler
from src.lambda_handlers.export_lambda import handler as export_handler
from src.lambda_handlers.session_lambda import lambda_handler as session_handler


class TestIntegrationWorkflows:
    """Integration tests for complete user workflows."""
    
    @pytest.fixture(autouse=True)
    def setup_aws_mocks(self):
        """Set up AWS service mocks for testing."""
        with mock_aws():
            # Create DynamoDB tables
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-2')
            
            # Users table
            users_table = dynamodb.create_table(
                TableName='gcse-generator-v2-users',
                KeySchema=[
                    {'AttributeName': 'PK', 'KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'PK', 'AttributeType': 'S'},
                    {'AttributeName': 'email', 'AttributeType': 'S'}
                ],
                GlobalSecondaryIndexes=[
                    {
                        'IndexName': 'EmailIndex',
                        'KeySchema': [
                            {'AttributeName': 'email', 'KeyType': 'HASH'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'},
                        'BillingMode': 'PAY_PER_REQUEST'
                    }
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            
            # Sessions table
            sessions_table = dynamodb.create_table(
                TableName='gcse-generator-v2-sessions',
                KeySchema=[
                    {'AttributeName': 'PK', 'KeyType': 'HASH'},
                    {'AttributeName': 'SK', 'KeyType': 'RANGE'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'PK', 'AttributeType': 'S'},
                    {'AttributeName': 'SK', 'AttributeType': 'S'},
                    {'AttributeName': 'user_id', 'AttributeType': 'S'}
                ],
                GlobalSecondaryIndexes=[
                    {
                        'IndexName': 'UserSessionsIndex',
                        'KeySchema': [
                            {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                            {'AttributeName': 'SK', 'KeyType': 'RANGE'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'},
                        'BillingMode': 'PAY_PER_REQUEST'
                    }
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            
            # QuestionFeedback table
            feedback_table = dynamodb.create_table(
                TableName='gcse-generator-v2-question-feedback',
                KeySchema=[
                    {'AttributeName': 'PK', 'KeyType': 'HASH'},
                    {'AttributeName': 'SK', 'KeyType': 'RANGE'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'PK', 'AttributeType': 'S'},
                    {'AttributeName': 'SK', 'AttributeType': 'S'},
                    {'AttributeName': 'question_id', 'AttributeType': 'S'},
                    {'AttributeName': 'user_id', 'AttributeType': 'S'}
                ],
                GlobalSecondaryIndexes=[
                    {
                        'IndexName': 'QuestionFeedbackIndex',
                        'KeySchema': [
                            {'AttributeName': 'question_id', 'KeyType': 'HASH'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'},
                        'BillingMode': 'PAY_PER_REQUEST'
                    },
                    {
                        'IndexName': 'UserFeedbackIndex',
                        'KeySchema': [
                            {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                            {'AttributeName': 'SK', 'KeyType': 'RANGE'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'},
                        'BillingMode': 'PAY_PER_REQUEST'
                    }
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            
            # TopicCoverage table
            coverage_table = dynamodb.create_table(
                TableName='gcse-generator-v2-topic-coverage',
                KeySchema=[
                    {'AttributeName': 'PK', 'KeyType': 'HASH'},
                    {'AttributeName': 'SK', 'KeyType': 'RANGE'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'PK', 'AttributeType': 'S'},
                    {'AttributeName': 'SK', 'AttributeType': 'S'},
                    {'AttributeName': 'user_id', 'AttributeType': 'S'}
                ],
                GlobalSecondaryIndexes=[
                    {
                        'IndexName': 'UserCoverageIndex',
                        'KeySchema': [
                            {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                            {'AttributeName': 'SK', 'KeyType': 'RANGE'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'},
                        'BillingMode': 'PAY_PER_REQUEST'
                    }
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            
            # Create S3 buckets
            s3 = boto3.client('s3', region_name='eu-west-2')
            s3.create_bucket(
                Bucket='gcse-specifications-test',
                CreateBucketConfiguration={'LocationConstraint': 'eu-west-2'}
            )
            
            # Upload test specification content
            test_spec = {
                "topic": "fractions",
                "tier": "both",
                "learning_objectives": [
                    "Add and subtract fractions with different denominators",
                    "Multiply and divide fractions"
                ],
                "assessment_objectives": {
                    "AO1": "Use and apply standard techniques",
                    "AO2": "Reason, interpret and communicate mathematically"
                },
                "common_misconceptions": [
                    "Adding denominators when adding fractions"
                ],
                "key_concepts": ["Equivalent fractions", "Lowest common multiple"]
            }
            
            s3.put_object(
                Bucket='gcse-specifications-test',
                Key='mathematics/number/fractions.json',
                Body=json.dumps(test_spec)
            )
            
            yield
    
    def test_complete_user_workflow(self):
        """Test complete user workflow: register → login → generate → feedback → export."""
        
        # Step 1: User Registration
        register_event = {
            "action": "register",
            "username": "test_teacher",
            "password": "SecurePass123!",
            "email": "teacher@school.edu",
            "school": "Test School",
            "subject_specialization": "Mathematics"
        }
        
        with patch('src.services.bedrock_service.BedrockService') as mock_bedrock:
            register_response = auth_handler(register_event, {})
            
        assert register_response['success'] is True
        assert 'session_token' in register_response
        assert register_response['user_id'] == 'USER#test_teacher'
        
        session_token = register_response['session_token']
        user_id = register_response['user_id']
        
        # Step 2: User Login (verify existing user can login)
        login_event = {
            "action": "login",
            "username": "test_teacher",
            "password": "SecurePass123!"
        }
        
        login_response = auth_handler(login_event, {})
        
        assert login_response['success'] is True
        assert 'session_token' in login_response
        assert login_response['user_id'] == 'USER#test_teacher'
        
        # Step 3: Question Generation Workflow
        # 3a: Interpret query
        interpret_event = {
            "query": "Generate 3 foundation tier questions about fractions",
            "user_id": user_id,
            "session_token": session_token
        }
        
        with patch('src.services.bedrock_service.BedrockService') as mock_bedrock:
            mock_bedrock_instance = MagicMock()
            mock_bedrock.return_value = mock_bedrock_instance
            
            # Mock Haiku response for interpretation
            mock_bedrock_instance.invoke_haiku.return_value = {
                "intent": {
                    "topic": "fractions",
                    "tier": "foundation",
                    "count": 3,
                    "subtopics": ["addition", "subtraction"]
                }
            }
            
            interpret_response = interpret_handler(interpret_event, {})
        
        assert 'intent' in interpret_response
        assert interpret_response['intent']['topic'] == 'fractions'
        assert interpret_response['intent']['tier'] == 'foundation'
        assert interpret_response['intent']['count'] == 3
        assert 'enriched_prompt' in interpret_response
        assert 'specification_context' in interpret_response
        
        # 3b: Generate questions
        generate_event = {
            "intent": interpret_response['intent'],
            "enriched_prompt": interpret_response['enriched_prompt'],
            "difficulty_guidance": interpret_response.get('difficulty_guidance', {}),
            "specification_context": interpret_response['specification_context'],
            "user_id": user_id,
            "session_token": session_token
        }
        
        with patch('src.services.bedrock_service.BedrockService') as mock_bedrock:
            mock_bedrock_instance = MagicMock()
            mock_bedrock.return_value = mock_bedrock_instance
            
            # Mock Sonnet response for generation
            mock_bedrock_instance.invoke_sonnet.return_value = {
                "questions": [
                    {
                        "id": "q_001",
                        "question_text": "Calculate 1/2 + 1/4",
                        "mark_scheme": "1/2 + 1/4 = 2/4 + 1/4 = 3/4 [2 marks]",
                        "difficulty_score": 3,
                        "topic": "fractions",
                        "subtopic": "addition",
                        "assessment_objective": "AO1"
                    },
                    {
                        "id": "q_002", 
                        "question_text": "What is 3/4 - 1/3?",
                        "mark_scheme": "3/4 - 1/3 = 9/12 - 4/12 = 5/12 [2 marks]",
                        "difficulty_score": 4,
                        "topic": "fractions",
                        "subtopic": "subtraction",
                        "assessment_objective": "AO1"
                    },
                    {
                        "id": "q_003",
                        "question_text": "Simplify 6/8 to its lowest terms",
                        "mark_scheme": "6/8 = 3/4 [1 mark]",
                        "difficulty_score": 2,
                        "topic": "fractions",
                        "subtopic": "simplification",
                        "assessment_objective": "AO1"
                    }
                ]
            }
            
            generate_response = generate_handler(generate_event, {})
        
        assert 'questions' in generate_response
        assert len(generate_response['questions']) == 3
        assert 'session_id' in generate_response
        
        questions = generate_response['questions']
        session_id = generate_response['session_id']
        
        # Verify question structure
        for question in questions:
            assert 'id' in question
            assert 'question_text' in question
            assert 'mark_scheme' in question
            assert 'difficulty_score' in question
            assert 1 <= question['difficulty_score'] <= 10
            assert 'topic' in question
            assert 'assessment_objective' in question
        
        # Step 4: Feedback Collection
        # Provide feedback on first question
        feedback_event = {
            "question_id": questions[0]['id'],
            "user_id": user_id,
            "session_token": session_token,
            "feedback": {
                "helpful": True,
                "difficulty_rating": 3,
                "comments": "Good question for foundation level"
            }
        }
        
        feedback_response = feedback_handler(feedback_event, {})
        
        assert feedback_response['success'] is True
        assert 'updated_quality_score' in feedback_response
        
        # Provide feedback on second question
        feedback_event_2 = {
            "question_id": questions[1]['id'],
            "user_id": user_id,
            "session_token": session_token,
            "feedback": {
                "helpful": False,
                "difficulty_rating": 6,
                "comments": "Too difficult for foundation tier"
            }
        }
        
        feedback_response_2 = feedback_handler(feedback_event_2, {})
        
        assert feedback_response_2['success'] is True
        
        # Step 5: Session History Retrieval
        history_event = {
            "action": "get_sessions",
            "user_id": user_id,
            "session_token": session_token,
            "limit": 10
        }
        
        history_response = session_handler(history_event, {})
        
        assert 'sessions' in history_response
        assert len(history_response['sessions']) >= 1
        
        # Verify session contains our generated content
        session = history_response['sessions'][0]
        assert session['session_id'] == session_id
        assert 'generated_questions' in session
        assert len(session['generated_questions']) == 3
        
        # Step 6: PDF Export
        export_event = {
            "session_id": session_id,
            "user_id": user_id,
            "session_token": session_token,
            "format": "pdf"
        }
        
        with patch('src.services.pdf_export_service.PDFExportService') as mock_pdf:
            mock_pdf_instance = MagicMock()
            mock_pdf.return_value = mock_pdf_instance
            mock_pdf_instance.generate_pdf.return_value = b"PDF content"
            
            export_response = export_handler(export_event, {})
        
        assert export_response['success'] is True
        assert 'download_url' in export_response
        assert export_response['format'] == 'pdf'
        
    def test_authentication_validation(self):
        """Test authentication validation across all endpoints."""
        
        # Test invalid session token
        invalid_token_event = {
            "query": "Generate questions about algebra",
            "user_id": "USER#test_user",
            "session_token": "invalid_token_123"
        }
        
        with patch('src.services.auth_service.AuthService.validate_session') as mock_validate:
            mock_validate.return_value = False
            
            interpret_response = interpret_handler(invalid_token_event, {})
        
        assert interpret_response['success'] is False
        assert 'authentication' in interpret_response['message'].lower()
        
        # Test missing session token
        no_token_event = {
            "query": "Generate questions about geometry",
            "user_id": "USER#test_user"
        }
        
        interpret_response_2 = interpret_handler(no_token_event, {})
        
        assert interpret_response_2['success'] is False
        assert 'token' in interpret_response_2['message'].lower()
        
    def test_error_handling_and_retry_mechanisms(self):
        """Test error handling and retry mechanisms."""
        
        # Test Bedrock service failure with retry
        interpret_event = {
            "query": "Generate questions about statistics",
            "user_id": "USER#test_user",
            "session_token": "valid_token"
        }
        
        with patch('src.services.bedrock_service.BedrockService') as mock_bedrock:
            mock_bedrock_instance = MagicMock()
            mock_bedrock.return_value = mock_bedrock_instance
            
            # Simulate service failure then success
            mock_bedrock_instance.invoke_haiku.side_effect = [
                Exception("Service temporarily unavailable"),
                Exception("Service temporarily unavailable"),
                {
                    "intent": {
                        "topic": "statistics",
                        "tier": "higher",
                        "count": 2
                    }
                }
            ]
            
            with patch('src.services.auth_service.AuthService.validate_session', return_value=True):
                interpret_response = interpret_handler(interpret_event, {})
        
        # Should succeed after retries
        assert 'intent' in interpret_response
        assert interpret_response['intent']['topic'] == 'statistics'
        
        # Test S3 content retrieval failure with fallback
        with patch('boto3.client') as mock_s3_client:
            mock_s3 = MagicMock()
            mock_s3_client.return_value = mock_s3
            mock_s3.get_object.side_effect = Exception("S3 service unavailable")
            
            with patch('src.services.auth_service.AuthService.validate_session', return_value=True):
                with patch('src.services.bedrock_service.BedrockService') as mock_bedrock:
                    mock_bedrock_instance = MagicMock()
                    mock_bedrock.return_value = mock_bedrock_instance
                    mock_bedrock_instance.invoke_haiku.return_value = {
                        "intent": {"topic": "algebra", "tier": "foundation", "count": 1}
                    }
                    
                    interpret_response = interpret_handler(interpret_event, {})
        
        # Should handle S3 failure gracefully
        assert 'intent' in interpret_response
        
    def test_session_ttl_behavior(self):
        """Test session TTL and automatic expiration."""
        
        # Create a session with TTL
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-2')
        sessions_table = dynamodb.Table('gcse-generator-v2-sessions')
        
        current_time = int(time.time())
        expired_ttl = current_time - 3600  # 1 hour ago (expired)
        valid_ttl = current_time + 604800   # 7 days from now (valid)
        
        # Insert expired session
        sessions_table.put_item(
            Item={
                'PK': 'SESSION#expired_session',
                'SK': f'TIMESTAMP#{current_time - 7200}',
                'session_id': 'expired_session',
                'user_id': 'USER#test_user',
                'query': 'Old query',
                'generated_questions': [],
                'timestamp': current_time - 7200,
                'ttl': expired_ttl
            }
        )
        
        # Insert valid session
        sessions_table.put_item(
            Item={
                'PK': 'SESSION#valid_session',
                'SK': f'TIMESTAMP#{current_time}',
                'session_id': 'valid_session',
                'user_id': 'USER#test_user',
                'query': 'Recent query',
                'generated_questions': [],
                'timestamp': current_time,
                'ttl': valid_ttl
            }
        )
        
        # Retrieve sessions - should only get valid ones
        history_event = {
            "action": "get_sessions",
            "user_id": "USER#test_user",
            "session_token": "valid_token",
            "limit": 10
        }
        
        with patch('src.services.auth_service.AuthService.validate_session', return_value=True):
            history_response = session_handler(history_event, {})
        
        assert 'sessions' in history_response
        # Should only return non-expired sessions
        for session in history_response['sessions']:
            assert session['ttl'] > current_time
        
    def test_data_isolation_between_users(self):
        """Test that user data is properly isolated."""
        
        # Create sessions for two different users
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-2')
        sessions_table = dynamodb.Table('gcse-generator-v2-sessions')
        
        current_time = int(time.time())
        
        # User 1 session
        sessions_table.put_item(
            Item={
                'PK': 'SESSION#user1_session',
                'SK': f'TIMESTAMP#{current_time}',
                'session_id': 'user1_session',
                'user_id': 'USER#user1',
                'query': 'User 1 query',
                'generated_questions': [{'id': 'q1', 'text': 'User 1 question'}],
                'timestamp': current_time,
                'ttl': current_time + 604800
            }
        )
        
        # User 2 session
        sessions_table.put_item(
            Item={
                'PK': 'SESSION#user2_session',
                'SK': f'TIMESTAMP#{current_time}',
                'session_id': 'user2_session',
                'user_id': 'USER#user2',
                'query': 'User 2 query',
                'generated_questions': [{'id': 'q2', 'text': 'User 2 question'}],
                'timestamp': current_time,
                'ttl': current_time + 604800
            }
        )
        
        # User 1 requests their sessions
        history_event_user1 = {
            "action": "get_sessions",
            "user_id": "USER#user1",
            "session_token": "user1_token",
            "limit": 10
        }
        
        with patch('src.services.auth_service.AuthService.validate_session', return_value=True):
            user1_response = session_handler(history_event_user1, {})
        
        # User 2 requests their sessions
        history_event_user2 = {
            "action": "get_sessions",
            "user_id": "USER#user2",
            "session_token": "user2_token",
            "limit": 10
        }
        
        with patch('src.services.auth_service.AuthService.validate_session', return_value=True):
            user2_response = session_handler(history_event_user2, {})
        
        # Verify data isolation
        assert len(user1_response['sessions']) == 1
        assert len(user2_response['sessions']) == 1
        
        assert user1_response['sessions'][0]['user_id'] == 'USER#user1'
        assert user2_response['sessions'][0]['user_id'] == 'USER#user2'
        
        assert user1_response['sessions'][0]['query'] == 'User 1 query'
        assert user2_response['sessions'][0]['query'] == 'User 2 query'
        
    def test_api_rate_limiting_behavior(self):
        """Test API rate limiting and throttling."""
        
        # This would typically test against actual API Gateway
        # For integration testing, we simulate rate limiting behavior
        
        interpret_event = {
            "query": "Generate questions",
            "user_id": "USER#test_user",
            "session_token": "valid_token"
        }
        
        # Simulate multiple rapid requests
        request_count = 0
        
        def mock_rate_limit_check(*args, **kwargs):
            nonlocal request_count
            request_count += 1
            if request_count > 10:  # Simulate rate limit after 10 requests
                raise Exception("Rate limit exceeded")
            return True
        
        with patch('src.services.auth_service.AuthService.validate_session', side_effect=mock_rate_limit_check):
            with patch('src.services.bedrock_service.BedrockService') as mock_bedrock:
                mock_bedrock_instance = MagicMock()
                mock_bedrock.return_value = mock_bedrock_instance
                mock_bedrock_instance.invoke_haiku.return_value = {
                    "intent": {"topic": "algebra", "tier": "foundation", "count": 1}
                }
                
                # Make requests until rate limited
                responses = []
                for i in range(15):
                    try:
                        response = interpret_handler(interpret_event, {})
                        responses.append(response)
                    except Exception as e:
                        if "rate limit" in str(e).lower():
                            break
                        raise
        
        # Should have processed some requests before hitting rate limit
        assert len(responses) == 10
        assert request_count > 10


if __name__ == '__main__':
    pytest.main([__file__, '-v'])