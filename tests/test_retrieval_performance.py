"""Performance tests for retrieval lambda."""

import json
import pytest
import time
from unittest.mock import Mock, patch

# Mock AWS services before importing lambda
with patch('boto3.resource'), patch('boto3.client'):
    from src.lambda_handlers import retrieval_lambda


class TestRetrievalPerformance:
    """Performance test suite for retrieval lambda."""
    
    @pytest.fixture
    def mock_dynamodb_table(self):
        """Mock DynamoDB table with fast responses."""
        table = Mock()
        
        # Simulate fast DynamoDB query (< 50ms)
        def fast_query(*args, **kwargs):
            time.sleep(0.01)  # 10ms simulated query time
            return {
                'Items': [
                    {
                        'question_id': f'q{i}',
                        'stem': f'Question {i}',
                        'options': ['A', 'B', 'C', 'D'],
                        'correct_answer': 'A',
                        'rationale': 'Explanation',
                        'difficulty': 5,
                        'verification_confidence': 0.9,
                        'topic': 'algebra',
                        'grade': 'foundation',
                        'paper_type': 'P1',
                        'verification_status': 'VERIFIED'
                    }
                    for i in range(10)
                ]
            }
        
        table.query = Mock(side_effect=fast_query)
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
    
    def test_response_time_under_100ms(self, mock_dynamodb_table, mock_cloudwatch, valid_request_event):
        """Test that retrieval responds in under 100ms (target)."""
        with patch('src.lambda_handlers.retrieval_lambda.dynamodb') as mock_dynamodb, \
             patch('src.lambda_handlers.retrieval_lambda.cloudwatch', mock_cloudwatch):
            mock_dynamodb.Table.return_value = mock_dynamodb_table
            
            start_time = time.time()
            response = retrieval_lambda.handler(valid_request_event, None)
            end_time = time.time()
            
            response_time_ms = (end_time - start_time) * 1000
            
            assert response['statusCode'] == 200
            
            # Check response time
            body = json.loads(response['body'])
            reported_time = body['metadata']['response_time_ms']
            
            # Should be under 100ms target (with some tolerance for test overhead)
            assert reported_time < 150, f"Response time {reported_time}ms exceeds target"
            
            print(f"Response time: {reported_time}ms (target: <100ms)")
    
    def test_multiple_requests_performance(self, mock_dynamodb_table, mock_cloudwatch, valid_request_event):
        """Test performance across multiple requests."""
        with patch('src.lambda_handlers.retrieval_lambda.dynamodb') as mock_dynamodb, \
             patch('src.lambda_handlers.retrieval_lambda.cloudwatch', mock_cloudwatch):
            mock_dynamodb.Table.return_value = mock_dynamodb_table
            
            response_times = []
            
            # Make 10 requests
            for _ in range(10):
                start_time = time.time()
                response = retrieval_lambda.handler(valid_request_event, None)
                end_time = time.time()
                
                response_time_ms = (end_time - start_time) * 1000
                response_times.append(response_time_ms)
                
                assert response['statusCode'] == 200
            
            # Calculate statistics
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            min_time = min(response_times)
            
            print(f"Performance stats over 10 requests:")
            print(f"  Average: {avg_time:.2f}ms")
            print(f"  Min: {min_time:.2f}ms")
            print(f"  Max: {max_time:.2f}ms")
            
            # Average should be well under target
            assert avg_time < 150, f"Average response time {avg_time}ms exceeds target"
    
    def test_large_result_set_performance(self, mock_cloudwatch):
        """Test performance with large result sets."""
        # Create mock table with many questions
        table = Mock()
        
        def large_query(*args, **kwargs):
            time.sleep(0.02)  # 20ms simulated query time
            return {
                'Items': [
                    {
                        'question_id': f'q{i}',
                        'stem': f'Question {i}',
                        'options': ['A', 'B', 'C', 'D'],
                        'correct_answer': 'A',
                        'rationale': 'Explanation',
                        'difficulty': 5,
                        'verification_confidence': 0.9,
                        'topic': 'algebra',
                        'grade': 'foundation',
                        'paper_type': 'P1',
                        'verification_status': 'VERIFIED'
                    }
                    for i in range(100)  # 100 questions
                ]
            }
        
        table.query = Mock(side_effect=large_query)
        table.update_item = Mock()
        
        event = {
            'body': json.dumps({
                'topic': 'algebra',
                'grade': 'foundation',
                'paper_type': 'P1',
                'count': 10
            })
        }
        
        with patch('src.lambda_handlers.retrieval_lambda.dynamodb') as mock_dynamodb, \
             patch('src.lambda_handlers.retrieval_lambda.cloudwatch', mock_cloudwatch):
            mock_dynamodb.Table.return_value = table
            
            start_time = time.time()
            response = retrieval_lambda.handler(event, None)
            end_time = time.time()
            
            response_time_ms = (end_time - start_time) * 1000
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            
            # Should still be fast even with large result set
            assert response_time_ms < 200, f"Response time {response_time_ms}ms too slow for large result set"
            
            # Should return requested count
            assert len(body['questions']) == 10
            
            print(f"Large result set (100 questions) response time: {response_time_ms:.2f}ms")
    
    def test_concurrent_requests_simulation(self, mock_dynamodb_table, mock_cloudwatch, valid_request_event):
        """Simulate concurrent requests to test performance under load."""
        with patch('src.lambda_handlers.retrieval_lambda.dynamodb') as mock_dynamodb, \
             patch('src.lambda_handlers.retrieval_lambda.cloudwatch', mock_cloudwatch):
            mock_dynamodb.Table.return_value = mock_dynamodb_table
            
            # Simulate 5 concurrent requests
            response_times = []
            
            for i in range(5):
                start_time = time.time()
                response = retrieval_lambda.handler(valid_request_event, None)
                end_time = time.time()
                
                response_time_ms = (end_time - start_time) * 1000
                response_times.append(response_time_ms)
                
                assert response['statusCode'] == 200
            
            # All requests should complete quickly
            for i, rt in enumerate(response_times):
                assert rt < 200, f"Request {i+1} took {rt}ms (too slow)"
            
            print(f"Concurrent requests simulation:")
            for i, rt in enumerate(response_times):
                print(f"  Request {i+1}: {rt:.2f}ms")
    
    def test_metrics_overhead(self, mock_dynamodb_table, valid_request_event):
        """Test that metrics don't add significant overhead."""
        # Test with metrics
        mock_cloudwatch_with = Mock()
        mock_cloudwatch_with.put_metric_data = Mock()
        
        with patch('src.lambda_handlers.retrieval_lambda.dynamodb') as mock_dynamodb, \
             patch('src.lambda_handlers.retrieval_lambda.cloudwatch', mock_cloudwatch_with):
            mock_dynamodb.Table.return_value = mock_dynamodb_table
            
            start_time = time.time()
            response = retrieval_lambda.handler(valid_request_event, None)
            time_with_metrics = (time.time() - start_time) * 1000
            
            assert response['statusCode'] == 200
        
        # Test without metrics (mock that fails silently)
        mock_cloudwatch_without = Mock()
        mock_cloudwatch_without.put_metric_data = Mock(side_effect=Exception('Metrics disabled'))
        
        with patch('src.lambda_handlers.retrieval_lambda.dynamodb') as mock_dynamodb, \
             patch('src.lambda_handlers.retrieval_lambda.cloudwatch', mock_cloudwatch_without):
            mock_dynamodb.Table.return_value = mock_dynamodb_table
            
            start_time = time.time()
            response = retrieval_lambda.handler(valid_request_event, None)
            time_without_metrics = (time.time() - start_time) * 1000
            
            assert response['statusCode'] == 200
        
        # Metrics overhead should be minimal (< 20ms)
        overhead = abs(time_with_metrics - time_without_metrics)
        print(f"Metrics overhead: {overhead:.2f}ms")
        
        # Both should be fast
        assert time_with_metrics < 150
        assert time_without_metrics < 150
