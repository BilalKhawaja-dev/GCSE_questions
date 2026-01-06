"""
Property-based tests for feedback storage consistency

Feature: gcse-question-generator-v2, Property 8: Feedback Storage Consistency
For any user feedback submission, the system should immediately store it in the 
QuestionFeedback DynamoDB table with all required fields.

Validates: Requirements 3.1, 3.8
"""

import json
import time
import uuid
from unittest.mock import Mock, patch, MagicMock
from hypothesis import given, strategies as st, settings
import pytest
import boto3
from moto import mock_aws

# Import the FeedbackLambda handler
from src.lambda_handlers.feedback_lambda import handler, store_feedback, update_quality_scores


class TestFeedbackStorageConsistency:
    """Test feedback storage consistency properties"""

    @mock_aws
    @given(
        question_id=st.text(min_size=5, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        user_id=st.text(min_size=5, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        helpful=st.booleans(),
        difficulty_rating=st.integers(min_value=1, max_value=10),
        comments=st.text(max_size=500)
    )
    @settings(max_examples=100, deadline=10000)
    def test_feedback_storage_consistency(self, question_id, user_id, helpful, difficulty_rating, comments):
        """
        Feature: gcse-question-generator-v2, Property 8: Feedback Storage Consistency
        For any user feedback submission, the system should immediately store it in the 
        QuestionFeedback DynamoDB table with all required fields.
        """
        # Setup mock DynamoDB tables
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-2')
        
        # Create QuestionFeedback table
        feedback_table = dynamodb.create_table(
            TableName='gcse-generator-v2-question-feedback-test',
            KeySchema=[
                {'AttributeName': 'pk', 'KeyType': 'HASH'},
                {'AttributeName': 'sk', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'pk', 'AttributeType': 'S'},
                {'AttributeName': 'sk', 'AttributeType': 'S'},
                {'AttributeName': 'question_id', 'AttributeType': 'S'},
                {'AttributeName': 'user_id', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'QuestionFeedbackIndex',
                    'KeySchema': [
                        {'AttributeName': 'question_id', 'KeyType': 'HASH'},
                        {'AttributeName': 'sk', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                },
                {
                    'IndexName': 'UserFeedbackIndex',
                    'KeySchema': [
                        {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                        {'AttributeName': 'sk', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                }
            ],
            BillingMode='PROVISIONED',
            ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )
        
        # Create QualityScores table
        quality_table = dynamodb.create_table(
            TableName='gcse-generator-v2-quality-scores-test',
            KeySchema=[
                {'AttributeName': 'pk', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'pk', 'AttributeType': 'S'},
                {'AttributeName': 'quality_score', 'AttributeType': 'N'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'QualityScoreIndex',
                    'KeySchema': [
                        {'AttributeName': 'quality_score', 'KeyType': 'HASH'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                }
            ],
            BillingMode='PROVISIONED',
            ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )
        
        # Wait for tables to be created
        feedback_table.wait_until_exists()
        quality_table.wait_until_exists()
        
        # Arrange: Create feedback event
        session_token = f"token_{uuid.uuid4().hex[:16]}"
        event = {
            'question_id': question_id,
            'user_id': user_id,
            'session_token': session_token,
            'feedback': {
                'helpful': helpful,
                'difficulty_rating': difficulty_rating,
                'comments': comments
            }
        }
        
        # Mock environment variables
        with patch.dict('os.environ', {
            'QUESTION_FEEDBACK_TABLE': 'gcse-generator-v2-question-feedback-test',
            'QUALITY_SCORES_TABLE': 'gcse-generator-v2-quality-scores-test'
        }):
            # Act: Call the feedback handler
            response = handler(event, {})
            
            # Assert: Response should be successful
            assert response['statusCode'] == 200
            response_body = json.loads(response['body'])
            assert response_body['success'] is True
            assert 'updated_quality_score' in response_body
            
            # Assert: Feedback should be stored in DynamoDB
            pk = f"FEEDBACK#{question_id}"
            
            # Query the feedback table to verify storage
            feedback_response = feedback_table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key('pk').eq(pk)
            )
            
            feedback_items = feedback_response.get('Items', [])
            assert len(feedback_items) >= 1, "Feedback should be stored in DynamoDB"
            
            # Find the feedback item for this user
            user_feedback = None
            for item in feedback_items:
                if item['user_id'] == user_id:
                    user_feedback = item
                    break
            
            assert user_feedback is not None, f"Feedback for user {user_id} should be stored"
            
            # Assert: All required fields should be present
            required_fields = ['pk', 'sk', 'question_id', 'user_id', 'helpful', 
                             'difficulty_rating', 'comments', 'timestamp', 'session_token']
            for field in required_fields:
                assert field in user_feedback, f"Required field '{field}' should be present in stored feedback"
            
            # Assert: Field values should match input
            assert user_feedback['question_id'] == question_id
            assert user_feedback['user_id'] == user_id
            assert user_feedback['helpful'] == helpful
            assert user_feedback['difficulty_rating'] == difficulty_rating
            assert user_feedback['comments'] == comments
            assert user_feedback['session_token'] == session_token
            
            # Assert: Timestamp should be recent (within last 10 seconds)
            current_time = int(time.time())
            stored_timestamp = user_feedback['timestamp']
            assert abs(current_time - stored_timestamp) <= 10, "Timestamp should be recent"
            
            # Assert: Quality scores should be updated
            quality_pk = f"QUALITY#{question_id}"
            quality_response = quality_table.get_item(Key={'pk': quality_pk})
            
            assert 'Item' in quality_response, "Quality score should be created/updated"
            quality_item = quality_response['Item']
            
            # Assert: Quality score fields should be present
            quality_fields = ['pk', 'question_id', 'quality_score', 'feedback_count', 
                            'helpful_count', 'not_helpful_count', 'avg_difficulty_rating', 'last_updated']
            for field in quality_fields:
                assert field in quality_item, f"Quality score field '{field}' should be present"
            
            # Assert: Quality score should be valid (0-1 range)
            quality_score = float(quality_item['quality_score'])
            assert 0.0 <= quality_score <= 1.0, "Quality score should be between 0 and 1"
            
            # Assert: Feedback count should be at least 1
            feedback_count = quality_item['feedback_count']
            assert feedback_count >= 1, "Feedback count should be at least 1"
            
            # Assert: Average difficulty rating should be valid (1-10 range)
            avg_difficulty = float(quality_item['avg_difficulty_rating'])
            assert 1.0 <= avg_difficulty <= 10.0, "Average difficulty rating should be between 1 and 10"

    @mock_aws
    @given(
        question_id=st.text(min_size=5, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        user_id=st.text(min_size=5, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        helpful=st.booleans(),
        difficulty_rating=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=50, deadline=10000)
    def test_multiple_feedback_aggregation(self, question_id, user_id, helpful, difficulty_rating):
        """
        Test that multiple feedback submissions for the same question are properly aggregated
        """
        # Setup mock DynamoDB tables
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-2')
        
        # Create tables (same as above)
        feedback_table = dynamodb.create_table(
            TableName='gcse-generator-v2-question-feedback-test',
            KeySchema=[
                {'AttributeName': 'pk', 'KeyType': 'HASH'},
                {'AttributeName': 'sk', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'pk', 'AttributeType': 'S'},
                {'AttributeName': 'sk', 'AttributeType': 'S'},
                {'AttributeName': 'question_id', 'AttributeType': 'S'},
                {'AttributeName': 'user_id', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'QuestionFeedbackIndex',
                    'KeySchema': [
                        {'AttributeName': 'question_id', 'KeyType': 'HASH'},
                        {'AttributeName': 'sk', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                }
            ],
            BillingMode='PROVISIONED',
            ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )
        
        quality_table = dynamodb.create_table(
            TableName='gcse-generator-v2-quality-scores-test',
            KeySchema=[
                {'AttributeName': 'pk', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'pk', 'AttributeType': 'S'}
            ],
            BillingMode='PROVISIONED',
            ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )
        
        feedback_table.wait_until_exists()
        quality_table.wait_until_exists()
        
        # Submit multiple feedback entries for the same question
        with patch.dict('os.environ', {
            'QUESTION_FEEDBACK_TABLE': 'gcse-generator-v2-question-feedback-test',
            'QUALITY_SCORES_TABLE': 'gcse-generator-v2-quality-scores-test'
        }):
            # Submit first feedback
            event1 = {
                'question_id': question_id,
                'user_id': f"{user_id}_1",
                'session_token': f"token_1_{uuid.uuid4().hex[:8]}",
                'feedback': {
                    'helpful': helpful,
                    'difficulty_rating': difficulty_rating,
                    'comments': 'First feedback'
                }
            }
            
            response1 = handler(event1, {})
            assert response1['statusCode'] == 200
            
            # Submit second feedback
            event2 = {
                'question_id': question_id,
                'user_id': f"{user_id}_2",
                'session_token': f"token_2_{uuid.uuid4().hex[:8]}",
                'feedback': {
                    'helpful': not helpful,  # Opposite of first feedback
                    'difficulty_rating': min(10, difficulty_rating + 1),  # Different rating
                    'comments': 'Second feedback'
                }
            }
            
            response2 = handler(event2, {})
            assert response2['statusCode'] == 200
            
            # Verify aggregation
            quality_pk = f"QUALITY#{question_id}"
            quality_response = quality_table.get_item(Key={'pk': quality_pk})
            
            assert 'Item' in quality_response
            quality_item = quality_response['Item']
            
            # Should have 2 feedback entries
            assert quality_item['feedback_count'] == 2
            
            # Helpful count should reflect the feedback
            expected_helpful_count = 1  # One helpful, one not helpful
            assert quality_item['helpful_count'] == expected_helpful_count
            assert quality_item['not_helpful_count'] == 1
            
            # Quality score should be calculated correctly
            quality_score = float(quality_item['quality_score'])
            assert 0.0 <= quality_score <= 1.0

    def test_invalid_feedback_rejection(self):
        """Test that invalid feedback is properly rejected"""
        
        # Test missing required fields
        invalid_events = [
            # Missing question_id
            {
                'user_id': 'test_user',
                'session_token': 'test_token',
                'feedback': {'helpful': True, 'difficulty_rating': 5}
            },
            # Missing feedback
            {
                'question_id': 'test_question',
                'user_id': 'test_user',
                'session_token': 'test_token'
            },
            # Invalid difficulty rating
            {
                'question_id': 'test_question',
                'user_id': 'test_user',
                'session_token': 'test_token',
                'feedback': {'helpful': True, 'difficulty_rating': 11}  # Out of range
            },
            # Missing helpful field
            {
                'question_id': 'test_question',
                'user_id': 'test_user',
                'session_token': 'test_token',
                'feedback': {'difficulty_rating': 5}
            }
        ]
        
        for invalid_event in invalid_events:
            response = handler(invalid_event, {})
            assert response['statusCode'] == 400
            response_body = json.loads(response['body'])
            assert response_body['success'] is False
            assert 'error' in response_body


if __name__ == '__main__':
    pytest.main([__file__, '-v'])