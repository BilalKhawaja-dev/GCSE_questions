"""Unit tests for retrieval lambda."""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Mock AWS services before importing lambda
with patch('boto3.resource'), patch('boto3.client'):
    from src.lambda_handlers import retrieval_lambda


class TestRetrievalLambda:
    """Test suite for retrieval lambda handler."""
    
    @pytest.fixture
    def mock_dynamodb_table(self):
        """Mock DynamoDB table."""
        table = Mock()
        table.query = Mock()
        table.update_item = Mock()
        return table
    
    @pytest.fixture
    def mock_cloudwatch(self):
        """Mock CloudWatch client."""
        client = Mock()
        client.put_metric_data = Mock()
        return client
    
    @pytest.fixture
    def valid_request_event(self):
        """Valid API Gateway event."""
        return {
            'body': json.dumps({
                'topic': 'algebra',
                'grade': 'foundation',
                'paper_type': 'P1',
                'difficulty_min': 3,
                'difficulty_max': 7,
                'count': 5
            })
        }
    
    @pytest.fixture
    def sample_questions(self):
        """Sample questions from DynamoDB."""
        return [
            {
                'question_id': 'q1',
                'stem': 'Solve 2x + 5 = 13',
                'options': ['x = 4', 'x = 9', 'x = 3', 'x = 8'],
                'correct_answer': 'A',
                'rationale': 'Subtract 5 from both sides',
                'difficulty': 5,
                'verification_confidence': 0.95,
                'topic': 'algebra',
                'grade': 'foundation',
                'paper_type': 'P1',
                'verification_status': 'VERIFIED'
            },
            {
                'question_id': 'q2',
                'stem': 'Expand (x + 3)(x + 4)',
                'options': ['x² + 7x + 12', 'x² + 12', 'x² + 7x', 'x² + 7'],
                'correct_answer': 'A',
                'rationale': 'Use FOIL method',
                'difficulty': 6,
                'verification_confidence': 0.92,
                'topic': 'algebra',
                'grade': 'foundation',
                'paper_type': 'P1',
                'verification_status': 'VERIFIED'
            }
        ]
    
    def test_successful_retrieval(self, mock_dynamodb_table, mock_cloudwatch, valid_request_event, sample_questions):
        """Test successful question retrieval."""
        # Setup mocks
        mock_dynamodb_table.query.return_value = {'Items': sample_questions}
        
        with patch('src.lambda_handlers.retrieval_lambda.dynamodb') as mock_dynamodb, \
             patch('src.lambda_handlers.retrieval_lambda.cloudwatch', mock_cloudwatch):
            mock_dynamodb.Table.return_value = mock_dynamodb_table
            
            # Call handler
            response = retrieval_lambda.handler(valid_request_event, None)
            
            # Verify response
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['questions']
            assert len(body['questions']) <= 5
            assert body['metadata']['source'] == 'verified_bank'
            assert 'response_time_ms' in body['metadata']
            
            # Verify DynamoDB query was called
            mock_dynamodb_table.query.assert_called_once()
            
            # Verify metrics were sent
            mock_cloudwatch.put_metric_data.assert_called()
    
    def test_missing_required_parameters(self, mock_dynamodb_table, mock_cloudwatch):
        """Test error when required parameters are missing."""
        event = {
            'body': json.dumps({
                'topic': 'algebra'
                # Missing grade and paper_type
            })
        }
        
        with patch('src.lambda_handlers.retrieval_lambda.dynamodb') as mock_dynamodb, \
             patch('src.lambda_handlers.retrieval_lambda.cloudwatch', mock_cloudwatch):
            mock_dynamodb.Table.return_value = mock_dynamodb_table
            
            response = retrieval_lambda.handler(event, None)
            
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert 'error' in body
            assert 'required' in body
    
    def test_invalid_difficulty_range(self, mock_dynamodb_table, mock_cloudwatch):
        """Test error when difficulty range is invalid."""
        event = {
            'body': json.dumps({
                'topic': 'algebra',
                'grade': 'foundation',
                'paper_type': 'P1',
                'difficulty_min': 8,
                'difficulty_max': 3  # Invalid: min > max
            })
        }
        
        with patch('src.lambda_handlers.retrieval_lambda.dynamodb') as mock_dynamodb, \
             patch('src.lambda_handlers.retrieval_lambda.cloudwatch', mock_cloudwatch):
            mock_dynamodb.Table.return_value = mock_dynamodb_table
            
            response = retrieval_lambda.handler(event, None)
            
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert 'error' in body
    
    def test_empty_question_bank(self, mock_dynamodb_table, mock_cloudwatch):
        """Test handling of empty question bank."""
        event = {
            'body': json.dumps({
                'topic': 'algebra',
                'grade': 'foundation',
                'paper_type': 'P1',
                'count': 5
            })
        }
        
        # Mock empty result
        mock_dynamodb_table.query.return_value = {'Items': []}
        
        with patch('src.lambda_handlers.retrieval_lambda.dynamodb') as mock_dynamodb, \
             patch('src.lambda_handlers.retrieval_lambda.cloudwatch', mock_cloudwatch):
            mock_dynamodb.Table.return_value = mock_dynamodb_table
            
            response = retrieval_lambda.handler(event, None)
            
            assert response['statusCode'] == 404
            body = json.loads(response['body'])
            assert 'error' in body
            assert 'no verified questions available' in body['error'].lower()
            assert 'suggestion' in body
            
            # Verify empty bank metric was sent
            metric_calls = [call for call in mock_cloudwatch.put_metric_data.call_args_list 
                          if any('EmptyBank' in str(arg) for arg in call[1]['MetricData'])]
            assert len(metric_calls) > 0
    
    def test_exclude_question_ids(self, mock_dynamodb_table, mock_cloudwatch, sample_questions):
        """Test excluding specific question IDs."""
        event = {
            'body': json.dumps({
                'topic': 'algebra',
                'grade': 'foundation',
                'paper_type': 'P1',
                'exclude_question_ids': ['q1'],
                'count': 5
            })
        }
        
        mock_dynamodb_table.query.return_value = {'Items': sample_questions}
        
        with patch('src.lambda_handlers.retrieval_lambda.dynamodb') as mock_dynamodb, \
             patch('src.lambda_handlers.retrieval_lambda.cloudwatch', mock_cloudwatch):
            mock_dynamodb.Table.return_value = mock_dynamodb_table
            
            response = retrieval_lambda.handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            
            # Verify excluded question is not in results
            question_ids = [q['question_id'] for q in body['questions']]
            assert 'q1' not in question_ids
    
    def test_usage_tracking(self, mock_dynamodb_table, mock_cloudwatch, valid_request_event, sample_questions):
        """Test that usage tracking is updated."""
        mock_dynamodb_table.query.return_value = {'Items': sample_questions}
        
        with patch('src.lambda_handlers.retrieval_lambda.dynamodb') as mock_dynamodb, \
             patch('src.lambda_handlers.retrieval_lambda.cloudwatch', mock_cloudwatch):
            mock_dynamodb.Table.return_value = mock_dynamodb_table
            
            response = retrieval_lambda.handler(valid_request_event, None)
            
            assert response['statusCode'] == 200
            
            # Verify update_item was called for usage tracking
            assert mock_dynamodb_table.update_item.called
    
    def test_cors_headers(self, mock_dynamodb_table, mock_cloudwatch, valid_request_event, sample_questions):
        """Test that CORS headers are included."""
        mock_dynamodb_table.query.return_value = {'Items': sample_questions}
        
        with patch('src.lambda_handlers.retrieval_lambda.dynamodb') as mock_dynamodb, \
             patch('src.lambda_handlers.retrieval_lambda.cloudwatch', mock_cloudwatch):
            mock_dynamodb.Table.return_value = mock_dynamodb_table
            
            response = retrieval_lambda.handler(valid_request_event, None)
            
            assert 'headers' in response
            assert 'Access-Control-Allow-Origin' in response['headers']
            assert 'Access-Control-Allow-Headers' in response['headers']
    
    def test_performance_metrics(self, mock_dynamodb_table, mock_cloudwatch, valid_request_event, sample_questions):
        """Test that performance metrics are sent."""
        mock_dynamodb_table.query.return_value = {'Items': sample_questions}
        
        with patch('src.lambda_handlers.retrieval_lambda.dynamodb') as mock_dynamodb, \
             patch('src.lambda_handlers.retrieval_lambda.cloudwatch', mock_cloudwatch):
            mock_dynamodb.Table.return_value = mock_dynamodb_table
            
            response = retrieval_lambda.handler(valid_request_event, None)
            
            assert response['statusCode'] == 200
            
            # Verify metrics were sent
            metric_calls = mock_cloudwatch.put_metric_data.call_args_list
            assert len(metric_calls) > 0
            
            # Check for RetrievalLatency metric
            latency_metrics = [call for call in metric_calls 
                             if any('RetrievalLatency' in str(arg) for arg in call[1]['MetricData'])]
            assert len(latency_metrics) > 0
    
    def test_error_handling(self, mock_dynamodb_table, mock_cloudwatch, valid_request_event):
        """Test error handling when DynamoDB fails."""
        mock_dynamodb_table.query.side_effect = Exception('DynamoDB error')
        
        with patch('src.lambda_handlers.retrieval_lambda.dynamodb') as mock_dynamodb, \
             patch('src.lambda_handlers.retrieval_lambda.cloudwatch', mock_cloudwatch):
            mock_dynamodb.Table.return_value = mock_dynamodb_table
            
            response = retrieval_lambda.handler(valid_request_event, None)
            
            assert response['statusCode'] == 500
            body = json.loads(response['body'])
            assert 'error' in body
            
            # Verify error metric was sent
            metric_calls = [call for call in mock_cloudwatch.put_metric_data.call_args_list 
                          if any('RetrievalErrors' in str(arg) for arg in call[1]['MetricData'])]
            assert len(metric_calls) > 0
    
    def test_random_selection(self, mock_dynamodb_table, mock_cloudwatch, sample_questions):
        """Test that random selection works when more questions available than requested."""
        # Create more questions than requested
        many_questions = sample_questions * 10  # 20 questions
        
        event = {
            'body': json.dumps({
                'topic': 'algebra',
                'grade': 'foundation',
                'paper_type': 'P1',
                'count': 5
            })
        }
        
        mock_dynamodb_table.query.return_value = {'Items': many_questions}
        
        with patch('src.lambda_handlers.retrieval_lambda.dynamodb') as mock_dynamodb, \
             patch('src.lambda_handlers.retrieval_lambda.cloudwatch', mock_cloudwatch):
            mock_dynamodb.Table.return_value = mock_dynamodb_table
            
            response = retrieval_lambda.handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            
            # Should return exactly 5 questions
            assert len(body['questions']) == 5
    
    def test_gsi_query_construction(self, mock_dynamodb_table, mock_cloudwatch, valid_request_event, sample_questions):
        """Test that GSI query is constructed correctly."""
        mock_dynamodb_table.query.return_value = {'Items': sample_questions}
        
        with patch('src.lambda_handlers.retrieval_lambda.dynamodb') as mock_dynamodb, \
             patch('src.lambda_handlers.retrieval_lambda.cloudwatch', mock_cloudwatch):
            mock_dynamodb.Table.return_value = mock_dynamodb_table
            
            response = retrieval_lambda.handler(valid_request_event, None)
            
            assert response['statusCode'] == 200
            
            # Verify query was called with correct parameters
            call_args = mock_dynamodb_table.query.call_args
            assert call_args[1]['IndexName'] == 'TopicGradePaperDifficultyIndex'
            assert 'KeyConditionExpression' in call_args[1]
            assert 'FilterExpression' in call_args[1]
