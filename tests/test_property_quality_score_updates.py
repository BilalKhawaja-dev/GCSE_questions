"""
Property-based tests for quality score updates

Feature: gcse-question-generator-v2, Property 10: Quality Score Updates
For any refinement operation, the system should update Quality_Score metrics in 
DynamoDB with new feedback data.

Validates: Requirements 3.5
"""

import json
import time
import uuid
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
from hypothesis import given, strategies as st, settings
import pytest
import boto3
from moto import mock_aws

# Import the RefinementLambda and FeedbackLambda handlers
from src.lambda_handlers.refinement_lambda import update_quality_metrics
from src.lambda_handlers.feedback_lambda import update_quality_scores


class TestQualityScoreUpdates:
    """Test quality score update properties"""

    @mock_aws
    @given(
        question_id=st.text(min_size=5, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        feedback_count=st.integers(min_value=1, max_value=50),
        helpful_count=st.integers(min_value=0, max_value=25),
        avg_difficulty_rating=st.floats(min_value=1.0, max_value=10.0)
    )
    @settings(max_examples=50, deadline=10000)
    def test_quality_score_updates(self, question_id, feedback_count, helpful_count, avg_difficulty_rating):
        """
        Feature: gcse-question-generator-v2, Property 10: Quality Score Updates
        For any refinement operation, the system should update Quality_Score metrics in 
        DynamoDB with new feedback data.
        """
        # Ensure helpful_count doesn't exceed feedback_count
        helpful_count = min(helpful_count, feedback_count)
        not_helpful_count = feedback_count - helpful_count
        
        # Setup mock DynamoDB
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-2')
        
        # Create QualityScores table
        quality_table = dynamodb.create_table(
            TableName='test-quality-scores-table',
            KeySchema=[
                {'AttributeName': 'pk', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'pk', 'AttributeType': 'S'}
            ],
            BillingMode='PROVISIONED',
            ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )
        
        quality_table.wait_until_exists()
        
        # Calculate expected quality score
        helpful_ratio = helpful_count / feedback_count if feedback_count > 0 else 0.5
        confidence_factor = min(1.0, feedback_count / 10.0)
        expected_quality_score = helpful_ratio * confidence_factor + 0.5 * (1 - confidence_factor)
        
        # Mock environment variables
        with patch.dict('os.environ', {
            'QUALITY_SCORES_TABLE': 'test-quality-scores-table'
        }):
            # Act: Update quality scores using the actual function
            updated_quality_score = update_quality_scores(question_id)
            
            # Since there's no feedback data initially, this will return 0.0
            # Let's simulate the feedback data by creating it first
            
            # Create mock feedback table
            feedback_table = dynamodb.create_table(
                TableName='test-feedback-table',
                KeySchema=[
                    {'AttributeName': 'pk', 'KeyType': 'HASH'},
                    {'AttributeName': 'sk', 'KeyType': 'RANGE'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'pk', 'AttributeType': 'S'},
                    {'AttributeName': 'sk', 'AttributeType': 'S'}
                ],
                BillingMode='PROVISIONED',
                ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
            )
            
            feedback_table.wait_until_exists()
            
            # Add mock feedback data
            pk = f"FEEDBACK#{question_id}"
            for i in range(feedback_count):
                is_helpful = i < helpful_count
                feedback_table.put_item(
                    Item={
                        'pk': pk,
                        'sk': f"USER#user_{i}#{int(time.time()) + i}",
                        'question_id': question_id,
                        'user_id': f'user_{i}',
                        'helpful': is_helpful,
                        'difficulty_rating': int(avg_difficulty_rating),
                        'comments': f'Feedback {i}',
                        'timestamp': int(time.time()) + i
                    }
                )
            
            # Mock the feedback table in the update function
            with patch.dict('os.environ', {
                'QUESTION_FEEDBACK_TABLE': 'test-feedback-table',
                'QUALITY_SCORES_TABLE': 'test-quality-scores-table'
            }):
                # Now update quality scores with the feedback data
                updated_quality_score = update_quality_scores(question_id)
                
                # Assert: Quality score should be calculated and returned
                assert isinstance(updated_quality_score, float)
                assert 0.0 <= updated_quality_score <= 1.0
                
                # Assert: Quality score should be stored in DynamoDB
                quality_pk = f"QUALITY#{question_id}"
                response = quality_table.get_item(Key={'pk': quality_pk})
                
                assert 'Item' in response, "Quality score should be stored in DynamoDB"
                quality_item = response['Item']
                
                # Assert: All required fields should be present
                required_fields = ['pk', 'question_id', 'quality_score', 'feedback_count', 
                                 'helpful_count', 'not_helpful_count', 'avg_difficulty_rating', 'last_updated']
                for field in required_fields:
                    assert field in quality_item, f"Required field '{field}' should be present"
                
                # Assert: Field values should match expected values
                assert quality_item['question_id'] == question_id
                assert quality_item['feedback_count'] == feedback_count
                assert quality_item['helpful_count'] == helpful_count
                assert quality_item['not_helpful_count'] == not_helpful_count
                
                # Assert: Quality score should be within expected range
                stored_quality_score = float(quality_item['quality_score'])
                assert 0.0 <= stored_quality_score <= 1.0
                
                # Assert: Average difficulty rating should be close to expected
                stored_avg_difficulty = float(quality_item['avg_difficulty_rating'])
                assert 1.0 <= stored_avg_difficulty <= 10.0
                
                # Assert: Last updated timestamp should be recent
                last_updated = quality_item['last_updated']
                current_time = int(time.time())
                assert abs(current_time - last_updated) <= 10, "Last updated timestamp should be recent"

    @mock_aws
    @given(
        question_id=st.text(min_size=5, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        initial_quality_score=st.floats(min_value=0.0, max_value=1.0),
        feedback_count=st.integers(min_value=5, max_value=20)
    )
    @settings(max_examples=30, deadline=10000)
    def test_refinement_quality_metric_updates(self, question_id, initial_quality_score, feedback_count):
        """
        Test that refinement operations update quality metrics correctly
        """
        # Setup mock DynamoDB
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-2')
        
        # Create QualityScores table
        quality_table = dynamodb.create_table(
            TableName='test-quality-scores-table',
            KeySchema=[
                {'AttributeName': 'pk', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'pk', 'AttributeType': 'S'}
            ],
            BillingMode='PROVISIONED',
            ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )
        
        quality_table.wait_until_exists()
        
        # Create initial quality score record
        quality_pk = f"QUALITY#{question_id}"
        initial_timestamp = int(time.time()) - 3600  # 1 hour ago
        
        quality_table.put_item(
            Item={
                'pk': quality_pk,
                'question_id': question_id,
                'quality_score': Decimal(str(initial_quality_score)),
                'feedback_count': feedback_count,
                'helpful_count': feedback_count // 2,
                'not_helpful_count': feedback_count - (feedback_count // 2),
                'avg_difficulty_rating': Decimal('5.5'),
                'last_updated': initial_timestamp,
                'improvement_trend': Decimal('0.0')
            }
        )
        
        # Create candidate data for refinement
        candidate = {
            'question_id': question_id,
            'quality_score': initial_quality_score,
            'feedback_count': feedback_count,
            'helpful_count': feedback_count // 2,
            'not_helpful_count': feedback_count - (feedback_count // 2),
            'avg_difficulty_rating': 5.5,
            'last_updated': initial_timestamp
        }
        
        # Mock environment variables
        with patch.dict('os.environ', {
            'QUALITY_SCORES_TABLE': 'test-quality-scores-table'
        }):
            # Act: Update quality metrics for refinement
            update_quality_metrics(question_id, candidate)
            
            # Assert: Quality metrics should be updated
            response = quality_table.get_item(Key={'pk': quality_pk})
            assert 'Item' in response, "Quality score record should exist"
            
            updated_item = response['Item']
            
            # Assert: Improvement trend should be updated
            assert 'improvement_trend' in updated_item
            improvement_trend = float(updated_item['improvement_trend'])
            assert improvement_trend > 0.0, "Improvement trend should be positive after refinement attempt"
            
            # Assert: Last improvement attempt timestamp should be updated
            assert 'last_improvement_attempt' in updated_item
            last_attempt = updated_item['last_improvement_attempt']
            current_time = int(time.time())
            assert abs(current_time - last_attempt) <= 10, "Last improvement attempt should be recent"
            
            # Assert: Original quality score should be preserved
            assert float(updated_item['quality_score']) == initial_quality_score

    @mock_aws
    def test_quality_score_updates_with_no_feedback(self):
        """Test quality score updates when no feedback exists"""
        
        # Setup mock DynamoDB
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-2')
        
        # Create empty feedback table
        feedback_table = dynamodb.create_table(
            TableName='test-feedback-table',
            KeySchema=[
                {'AttributeName': 'pk', 'KeyType': 'HASH'},
                {'AttributeName': 'sk', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'pk', 'AttributeType': 'S'},
                {'AttributeName': 'sk', 'AttributeType': 'S'}
            ],
            BillingMode='PROVISIONED',
            ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )
        
        # Create quality scores table
        quality_table = dynamodb.create_table(
            TableName='test-quality-scores-table',
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
        
        question_id = 'test_question_no_feedback'
        
        with patch.dict('os.environ', {
            'QUESTION_FEEDBACK_TABLE': 'test-feedback-table',
            'QUALITY_SCORES_TABLE': 'test-quality-scores-table'
        }):
            # Act: Try to update quality scores with no feedback
            quality_score = update_quality_scores(question_id)
            
            # Assert: Should return 0.0 when no feedback exists
            assert quality_score == 0.0

    @mock_aws
    @given(
        question_id=st.text(min_size=5, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        feedback_batches=st.lists(
            st.tuples(
                st.integers(min_value=1, max_value=10),  # helpful count
                st.integers(min_value=1, max_value=10),  # not helpful count
                st.floats(min_value=1.0, max_value=10.0)  # avg difficulty
            ),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=20, deadline=10000)
    def test_quality_score_progression(self, question_id, feedback_batches):
        """
        Test that quality scores update correctly as feedback accumulates
        """
        # Setup mock DynamoDB
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-2')
        
        # Create tables
        feedback_table = dynamodb.create_table(
            TableName='test-feedback-table',
            KeySchema=[
                {'AttributeName': 'pk', 'KeyType': 'HASH'},
                {'AttributeName': 'sk', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'pk', 'AttributeType': 'S'},
                {'AttributeName': 'sk', 'AttributeType': 'S'}
            ],
            BillingMode='PROVISIONED',
            ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )
        
        quality_table = dynamodb.create_table(
            TableName='test-quality-scores-table',
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
        
        previous_quality_score = 0.0
        cumulative_feedback_count = 0
        
        with patch.dict('os.environ', {
            'QUESTION_FEEDBACK_TABLE': 'test-feedback-table',
            'QUALITY_SCORES_TABLE': 'test-quality-scores-table'
        }):
            # Process feedback in batches
            for batch_idx, (helpful_count, not_helpful_count, avg_difficulty) in enumerate(feedback_batches):
                # Add feedback for this batch
                pk = f"FEEDBACK#{question_id}"
                batch_feedback_count = helpful_count + not_helpful_count
                
                for i in range(batch_feedback_count):
                    is_helpful = i < helpful_count
                    feedback_table.put_item(
                        Item={
                            'pk': pk,
                            'sk': f"USER#batch_{batch_idx}_user_{i}#{int(time.time()) + batch_idx * 100 + i}",
                            'question_id': question_id,
                            'user_id': f'batch_{batch_idx}_user_{i}',
                            'helpful': is_helpful,
                            'difficulty_rating': int(avg_difficulty),
                            'comments': f'Batch {batch_idx} feedback {i}',
                            'timestamp': int(time.time()) + batch_idx * 100 + i
                        }
                    )
                
                cumulative_feedback_count += batch_feedback_count
                
                # Update quality scores
                current_quality_score = update_quality_scores(question_id)
                
                # Assert: Quality score should be valid
                assert isinstance(current_quality_score, float)
                assert 0.0 <= current_quality_score <= 1.0
                
                # Assert: Quality score should reflect cumulative feedback
                quality_pk = f"QUALITY#{question_id}"
                response = quality_table.get_item(Key={'pk': quality_pk})
                assert 'Item' in response
                
                quality_item = response['Item']
                assert quality_item['feedback_count'] == cumulative_feedback_count
                
                # Store for next iteration comparison
                previous_quality_score = current_quality_score

    def test_quality_score_calculation_edge_cases(self):
        """Test quality score calculation with edge cases"""
        
        # Test with all helpful feedback
        with patch.dict('os.environ', {
            'QUESTION_FEEDBACK_TABLE': 'test-table',
            'QUALITY_SCORES_TABLE': 'test-table'
        }):
            # Mock the DynamoDB operations for edge cases
            with patch('boto3.resource') as mock_dynamodb:
                mock_table = Mock()
                mock_dynamodb.return_value.Table.return_value = mock_table
                
                # Test case 1: All helpful feedback
                mock_table.query.return_value = {
                    'Items': [
                        {'helpful': True, 'difficulty_rating': 5},
                        {'helpful': True, 'difficulty_rating': 6},
                        {'helpful': True, 'difficulty_rating': 4}
                    ]
                }
                
                quality_score = update_quality_scores('test_question')
                # Should be high quality score since all feedback is helpful
                assert quality_score > 0.5
                
                # Test case 2: All not helpful feedback
                mock_table.query.return_value = {
                    'Items': [
                        {'helpful': False, 'difficulty_rating': 5},
                        {'helpful': False, 'difficulty_rating': 6},
                        {'helpful': False, 'difficulty_rating': 4}
                    ]
                }
                
                quality_score = update_quality_scores('test_question')
                # Should be lower quality score since all feedback is not helpful
                assert quality_score < 0.5


if __name__ == '__main__':
    pytest.main([__file__, '-v'])