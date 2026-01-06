"""
Performance testing for GCSE Question Generator V2.
Tests load handling, response times, scalability, and cost targets.

Requirements: 12.1, 12.2, 12.3
"""

import asyncio
import time
import concurrent.futures
import pytest
import statistics
from unittest.mock import patch, MagicMock
import json
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestPerformanceValidation:
    """Performance tests for system scalability and response times."""
    
    def test_response_time_targets(self):
        """Test that response times meet targets (<10 seconds for 20 questions)."""
        from src.lambda_handlers.generate_lambda import lambda_handler as generate_handler
        
        # Mock dependencies for performance testing
        with patch('src.services.bedrock_service.BedrockService') as mock_bedrock:
            with patch('src.services.auth_service.AuthService') as mock_auth:
                with patch('src.services.session_service.SessionService') as mock_session:
                    
                    # Setup mocks
                    mock_bedrock_instance = MagicMock()
                    mock_bedrock.return_value = mock_bedrock_instance
                    
                    mock_auth_instance = MagicMock()
                    mock_auth.return_value = mock_auth_instance
                    mock_auth_instance.validate_session_token.return_value = {'valid': True}
                    
                    mock_session_instance = MagicMock()
                    mock_session.return_value = mock_session_instance
                    mock_session_instance.create_session.return_value = 'test_session_id'
                    
                    # Mock Bedrock response for 20 questions
                    questions = []
                    for i in range(20):
                        questions.append({
                            "id": f"q_{i+1:03d}",
                            "question_text": f"Calculate {i+1} + {i+2}",
                            "mark_scheme": f"{i+1} + {i+2} = {2*i+3} [1 mark]",
                            "difficulty_score": (i % 10) + 1,
                            "topic": "arithmetic",
                            "subtopic": "addition",
                            "assessment_objective": "AO1",
                            "learning_objective": "Add integers"
                        })
                    
                    mock_bedrock_instance.invoke_sonnet.return_value = {
                        "questions": questions
                    }
                    
                    # Test event for 20 questions
                    test_event = {
                        "intent": {
                            "topic": "arithmetic",
                            "tier": "foundation",
                            "count": 20,
                            "subtopics": ["addition"]
                        },
                        "enriched_prompt": "Generate 20 arithmetic questions",
                        "difficulty_guidance": {"min_difficulty": 1, "max_difficulty": 5},
                        "specification_context": {
                            "learning_objectives": ["Add integers"],
                            "assessment_objectives": ["AO1"],
                            "common_misconceptions": []
                        },
                        "user_id": "USER#testuser",
                        "session_token": "valid_token"
                    }
                    
                    # Measure response time
                    start_time = time.time()
                    response = generate_handler(test_event, {})
                    end_time = time.time()
                    
                    response_time = end_time - start_time
                    
                    # Verify response time is under 10 seconds
                    assert response_time < 10.0, f"Response time {response_time:.2f}s exceeds 10s target"
                    
                    # Verify all 20 questions were generated
                    assert 'questions' in response
                    assert len(response['questions']) == 20
                    
                    print(f"✓ Generated 20 questions in {response_time:.2f} seconds")
    
    def test_concurrent_user_load(self):
        """Test system behavior under concurrent load (100+ users)."""
        from src.lambda_handlers.interpret_lambda import lambda_handler as interpret_handler
        
        def simulate_user_request(user_id):
            """Simulate a single user request."""
            with patch('src.services.bedrock_service.BedrockService') as mock_bedrock:
                with patch('src.services.auth_service.AuthService') as mock_auth:
                    with patch('src.services.content_retrieval_service.ContentRetrievalService') as mock_content:
                        
                        # Setup mocks
                        mock_bedrock_instance = MagicMock()
                        mock_bedrock.return_value = mock_bedrock_instance
                        
                        mock_auth_instance = MagicMock()
                        mock_auth.return_value = mock_auth_instance
                        mock_auth_instance.validate_session_token.return_value = {'valid': True}
                        
                        mock_content_instance = MagicMock()
                        mock_content.return_value = mock_content_instance
                        mock_content_instance.get_specification_content.return_value = {
                            "topic": "fractions",
                            "learning_objectives": ["Add fractions"],
                            "common_misconceptions": ["Adding denominators"]
                        }
                        
                        mock_bedrock_instance.invoke_haiku.return_value = {
                            "intent": {
                                "topic": "fractions",
                                "tier": "foundation",
                                "count": 5,
                                "subtopics": ["addition"]
                            }
                        }
                        
                        test_event = {
                            "query": f"Generate 5 fraction questions for user {user_id}",
                            "user_id": f"USER#{user_id}",
                            "session_token": f"token_{user_id}"
                        }
                        
                        start_time = time.time()
                        response = interpret_handler(test_event, {})
                        end_time = time.time()
                        
                        return {
                            'user_id': user_id,
                            'response_time': end_time - start_time,
                            'success': 'intent' in response,
                            'response': response
                        }
        
        # Simulate 100 concurrent users
        num_users = 100
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            # Submit all requests
            futures = [
                executor.submit(simulate_user_request, f"user_{i:03d}")
                for i in range(num_users)
            ]
            
            # Collect results
            results = []
            for future in concurrent.futures.as_completed(futures, timeout=60):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f"Request failed: {e}")
        
        # Analyze results
        successful_requests = [r for r in results if r['success']]
        response_times = [r['response_time'] for r in successful_requests]
        
        # Performance assertions
        success_rate = len(successful_requests) / num_users
        assert success_rate >= 0.95, f"Success rate {success_rate:.2%} below 95% threshold"
        
        if response_times:
            avg_response_time = statistics.mean(response_times)
            p95_response_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
            
            assert avg_response_time < 5.0, f"Average response time {avg_response_time:.2f}s exceeds 5s"
            assert p95_response_time < 10.0, f"95th percentile response time {p95_response_time:.2f}s exceeds 10s"
            
            print(f"✓ {num_users} concurrent users: {success_rate:.1%} success rate")
            print(f"✓ Average response time: {avg_response_time:.2f}s")
            print(f"✓ 95th percentile response time: {p95_response_time:.2f}s")
    
    def test_memory_usage_efficiency(self):
        """Test memory usage stays within Lambda limits."""
        import psutil
        import os
        
        from src.lambda_handlers.generate_lambda import lambda_handler as generate_handler
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        with patch('src.services.bedrock_service.BedrockService') as mock_bedrock:
            with patch('src.services.auth_service.AuthService') as mock_auth:
                with patch('src.services.session_service.SessionService') as mock_session:
                    
                    # Setup mocks
                    mock_bedrock_instance = MagicMock()
                    mock_bedrock.return_value = mock_bedrock_instance
                    
                    mock_auth_instance = MagicMock()
                    mock_auth.return_value = mock_auth_instance
                    mock_auth_instance.validate_session_token.return_value = {'valid': True}
                    
                    mock_session_instance = MagicMock()
                    mock_session.return_value = mock_session_instance
                    mock_session_instance.create_session.return_value = 'test_session_id'
                    
                    # Generate large response (50 questions)
                    questions = []
                    for i in range(50):
                        questions.append({
                            "id": f"q_{i+1:03d}",
                            "question_text": f"Solve the equation {i+1}x + {i+2} = {i+10}. Show your working.",
                            "mark_scheme": f"Step 1: {i+1}x = {i+10} - {i+2} = {i+8} [1 mark]\nStep 2: x = {i+8}/{i+1} = {(i+8)/(i+1):.2f} [1 mark]",
                            "difficulty_score": (i % 10) + 1,
                            "topic": "algebra",
                            "subtopic": "linear_equations",
                            "assessment_objective": "AO2",
                            "learning_objective": "Solve linear equations"
                        })
                    
                    mock_bedrock_instance.invoke_sonnet.return_value = {
                        "questions": questions
                    }
                    
                    test_event = {
                        "intent": {
                            "topic": "algebra",
                            "tier": "higher",
                            "count": 50,
                            "subtopics": ["linear_equations"]
                        },
                        "enriched_prompt": "Generate 50 algebra questions",
                        "difficulty_guidance": {"min_difficulty": 6, "max_difficulty": 10},
                        "specification_context": {
                            "learning_objectives": ["Solve linear equations"],
                            "assessment_objectives": ["AO2"],
                            "common_misconceptions": []
                        },
                        "user_id": "USER#testuser",
                        "session_token": "valid_token"
                    }
                    
                    # Execute request
                    response = generate_handler(test_event, {})
                    
                    # Check memory usage after processing
                    peak_memory = process.memory_info().rss / 1024 / 1024  # MB
                    memory_increase = peak_memory - initial_memory
                    
                    # Lambda memory limits: 1024MB for GenerateLambda
                    assert peak_memory < 800, f"Memory usage {peak_memory:.1f}MB exceeds safe threshold"
                    assert memory_increase < 500, f"Memory increase {memory_increase:.1f}MB too high"
                    
                    # Verify response quality
                    assert 'questions' in response
                    assert len(response['questions']) == 50
                    
                    print(f"✓ Memory usage: {peak_memory:.1f}MB (increase: {memory_increase:.1f}MB)")
    
    def test_database_performance(self):
        """Test DynamoDB operation performance."""
        from src.services.session_service import SessionService
        
        with patch('boto3.resource') as mock_boto3:
            mock_dynamodb = MagicMock()
            mock_table = MagicMock()
            mock_boto3.return_value = mock_dynamodb
            mock_dynamodb.Table.return_value = mock_table
            
            # Mock fast DynamoDB responses
            mock_table.put_item.return_value = {}
            mock_table.query.return_value = {
                'Items': [{
                    'PK': 'SESSION#test_session',
                    'SK': 'TIMESTAMP#1234567890',
                    'session_id': 'test_session',
                    'user_id': 'USER#testuser',
                    'query': 'Test query',
                    'generated_questions': [{'id': 'q1', 'text': 'Test'}],
                    'timestamp': 1234567890,
                    'ttl': 1234567890 + 604800
                }]
            }
            
            # Test session creation performance
            session_service = SessionService('eu-west-2', mock_table)
            
            start_time = time.time()
            session_id = session_service.create_session(
                user_id='USER#testuser',
                query='Performance test query',
                questions=[{'id': 'q1', 'text': 'Test question'}]
            )
            creation_time = time.time() - start_time
            
            # Test session retrieval performance
            start_time = time.time()
            sessions = session_service.get_user_sessions('USER#testuser', limit=10)
            retrieval_time = time.time() - start_time
            
            # Performance assertions
            assert creation_time < 1.0, f"Session creation took {creation_time:.3f}s, exceeds 1s"
            assert retrieval_time < 0.5, f"Session retrieval took {retrieval_time:.3f}s, exceeds 0.5s"
            
            print(f"✓ Session creation: {creation_time:.3f}s")
            print(f"✓ Session retrieval: {retrieval_time:.3f}s")
    
    def test_cost_monitoring_thresholds(self):
        """Test cost monitoring and alerting thresholds."""
        from src.services.cost_monitoring_service import CostMonitoringService
        
        with patch('boto3.client') as mock_boto3:
            mock_cloudwatch = MagicMock()
            mock_boto3.return_value = mock_cloudwatch
            
            # Mock cost data - simulate daily costs
            mock_cloudwatch.get_metric_statistics.return_value = {
                'Datapoints': [
                    {'Timestamp': '2024-01-01', 'Sum': 15.50},  # Bedrock costs
                    {'Timestamp': '2024-01-01', 'Sum': 2.30},   # DynamoDB costs
                    {'Timestamp': '2024-01-01', 'Sum': 1.20},   # S3 costs
                ]
            }
            
            cost_service = CostMonitoringService('eu-west-2')
            
            # Test daily cost calculation
            daily_costs = cost_service.get_daily_costs('2024-01-01')
            total_daily_cost = sum(daily_costs.values())
            
            # Cost assertions (target: £30/month = £1/day average)
            assert total_daily_cost < 25.0, f"Daily cost £{total_daily_cost:.2f} exceeds £25 threshold"
            
            # Test cost projection
            monthly_projection = total_daily_cost * 30
            assert monthly_projection < 35.0, f"Monthly projection £{monthly_projection:.2f} exceeds £35 target"
            
            print(f"✓ Daily cost: £{total_daily_cost:.2f}")
            print(f"✓ Monthly projection: £{monthly_projection:.2f}")
    
    def test_auto_scaling_behavior(self):
        """Test DynamoDB auto-scaling behavior simulation."""
        # This test simulates auto-scaling behavior since we can't test actual AWS auto-scaling
        
        # Simulate read/write capacity scaling
        base_read_capacity = 5
        base_write_capacity = 5
        
        # Simulate high load scenario
        simulated_read_requests = 1000  # requests per second
        simulated_write_requests = 200   # requests per second
        
        # Calculate required capacity (assuming 1 RCU = 4KB/s, 1 WCU = 1KB/s)
        required_read_capacity = max(base_read_capacity, simulated_read_requests / 4)
        required_write_capacity = max(base_write_capacity, simulated_write_requests)
        
        # Simulate auto-scaling response (AWS typically scales in steps)
        def calculate_scaled_capacity(current, required):
            if required > current * 0.7:  # Scale up at 70% utilization
                return min(required * 1.5, 4000)  # Scale up by 50%, max 4000
            return current
        
        scaled_read_capacity = calculate_scaled_capacity(base_read_capacity, required_read_capacity)
        scaled_write_capacity = calculate_scaled_capacity(base_write_capacity, required_write_capacity)
        
        # Verify scaling behavior
        assert scaled_read_capacity >= required_read_capacity, "Read capacity insufficient for load"
        assert scaled_write_capacity >= required_write_capacity, "Write capacity insufficient for load"
        
        # Verify cost implications (on-demand pricing simulation)
        read_cost_per_hour = scaled_read_capacity * 0.00013  # $0.00013 per RCU per hour
        write_cost_per_hour = scaled_write_capacity * 0.00065  # $0.00065 per WCU per hour
        
        daily_dynamodb_cost = (read_cost_per_hour + write_cost_per_hour) * 24
        
        # Cost assertion
        assert daily_dynamodb_cost < 10.0, f"DynamoDB daily cost ${daily_dynamodb_cost:.2f} too high"
        
        print(f"✓ Auto-scaling: RCU {base_read_capacity}→{scaled_read_capacity}, WCU {base_write_capacity}→{scaled_write_capacity}")
        print(f"✓ Estimated DynamoDB cost: ${daily_dynamodb_cost:.2f}/day")
    
    def test_bedrock_api_performance(self):
        """Test Bedrock API call performance and retry behavior."""
        from src.services.bedrock_service import BedrockService
        
        with patch('boto3.client') as mock_boto3:
            mock_bedrock = MagicMock()
            mock_boto3.return_value = mock_bedrock
            
            # Mock successful response
            mock_bedrock.invoke_model.return_value = {
                'body': MagicMock()
            }
            mock_bedrock.invoke_model.return_value['body'].read.return_value = json.dumps({
                "content": [{
                    "text": json.dumps({
                        "questions": [
                            {
                                "id": "q1",
                                "question_text": "Test question",
                                "mark_scheme": "Test answer",
                                "difficulty_score": 5
                            }
                        ]
                    })
                }]
            }).encode()
            
            bedrock_service = BedrockService('eu-west-2')
            
            # Test multiple API calls for performance
            response_times = []
            
            for i in range(10):
                start_time = time.time()
                result = bedrock_service.invoke_sonnet("Generate a test question")
                end_time = time.time()
                
                response_times.append(end_time - start_time)
                assert 'questions' in result
            
            # Performance analysis
            avg_response_time = statistics.mean(response_times)
            max_response_time = max(response_times)
            
            # Bedrock performance assertions
            assert avg_response_time < 2.0, f"Average Bedrock response time {avg_response_time:.2f}s too high"
            assert max_response_time < 5.0, f"Max Bedrock response time {max_response_time:.2f}s too high"
            
            print(f"✓ Bedrock API average response: {avg_response_time:.2f}s")
            print(f"✓ Bedrock API max response: {max_response_time:.2f}s")
    
    def test_s3_content_retrieval_performance(self):
        """Test S3 content retrieval performance."""
        from src.services.content_retrieval_service import ContentRetrievalService
        
        with patch('boto3.client') as mock_boto3:
            mock_s3 = MagicMock()
            mock_boto3.return_value = mock_s3
            
            # Mock S3 response with specification content
            mock_s3.get_object.return_value = {
                'Body': MagicMock()
            }
            mock_s3.get_object.return_value['Body'].read.return_value = json.dumps({
                "topic": "fractions",
                "learning_objectives": ["Add fractions", "Subtract fractions"],
                "common_misconceptions": ["Adding denominators"],
                "key_concepts": ["Equivalent fractions", "Common denominators"]
            }).encode()
            
            content_service = ContentRetrievalService('test-bucket', 'eu-west-2')
            
            # Test content retrieval performance
            retrieval_times = []
            
            for topic in ['fractions', 'algebra', 'geometry', 'statistics', 'probability']:
                start_time = time.time()
                content = content_service.get_specification_content(topic)
                end_time = time.time()
                
                retrieval_times.append(end_time - start_time)
                assert content['topic'] == topic
            
            # Performance analysis
            avg_retrieval_time = statistics.mean(retrieval_times)
            max_retrieval_time = max(retrieval_times)
            
            # S3 performance assertions
            assert avg_retrieval_time < 0.5, f"Average S3 retrieval time {avg_retrieval_time:.3f}s too high"
            assert max_retrieval_time < 1.0, f"Max S3 retrieval time {max_retrieval_time:.3f}s too high"
            
            print(f"✓ S3 content retrieval average: {avg_retrieval_time:.3f}s")
            print(f"✓ S3 content retrieval max: {max_retrieval_time:.3f}s")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])