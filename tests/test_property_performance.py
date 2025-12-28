"""
Property-based tests for performance requirements.

This module contains property-based tests that validate the performance
properties defined in the design document, specifically:
- Property 6: Interpretation Performance
- Property 8: Generation Performance
"""

import json
import time
from unittest.mock import Mock, patch
from hypothesis import given, settings, strategies as st
import pytest

from src.lambda_handlers.interpret_lambda import lambda_handler as interpret_handler
from src.lambda_handlers.generate_lambda import lambda_handler as generate_handler
from src.models.query_intent import QueryIntent
from src.utils.constants import VALID_TOPICS, VALID_TIERS


# Test data generators
@st.composite
def valid_query_string(draw):
    """Generate valid query strings for interpretation."""
    topic = draw(st.sampled_from(["fractions", "algebra", "geometry", "statistics"]))
    tier = draw(st.sampled_from(["Foundation", "Higher"]))
    count = draw(st.integers(min_value=1, max_value=10))
    
    return f"Generate {count} {tier} {topic} questions"


@st.composite
def valid_generation_request(draw):
    """Generate valid generation requests."""
    return {
        "topic": draw(st.sampled_from(["Number", "Algebra", "Geometry", "Statistics"])),
        "tier": draw(st.sampled_from(["Foundation", "Higher"])),
        "count": draw(st.integers(min_value=1, max_value=10)),
        "specification_version": "latest"
    }


@st.composite
def mock_lambda_context(draw, function_name, remaining_time_ms=None):
    """Generate mock Lambda context objects."""
    context = Mock()
    context.function_name = function_name
    context.aws_request_id = draw(st.text(min_size=10, max_size=20))
    
    if remaining_time_ms is None:
        # Generate realistic remaining time values
        if function_name == "InterpretLambda":
            remaining_time_ms = draw(st.integers(min_value=5000, max_value=30000))  # 5-30 seconds
        else:  # GenerateLambda
            remaining_time_ms = draw(st.integers(min_value=10000, max_value=60000))  # 10-60 seconds
    
    context.get_remaining_time_in_millis.return_value = remaining_time_ms
    return context


class TestPerformanceProperties:
    """Property-based tests for performance requirements."""

    @given(
        query=valid_query_string(),
        context=mock_lambda_context("InterpretLambda")
    )
    @settings(max_examples=100)
    def test_property_6_interpretation_performance(self, query, context):
        """
        Feature: gcse-question-generator, Property 6: Interpretation Performance
        
        For any interpretation request, the System should complete processing 
        within 30 seconds or return a timeout error with descriptive message.
        
        **Validates: Requirements 7.4**
        """
        # Mock the Bedrock service to avoid actual API calls
        with patch('src.lambda_handlers.interpret_lambda.bedrock_service') as mock_bedrock:
            mock_intent = QueryIntent(
                topic="Number",
                tier="Foundation", 
                count=5,
                confidence=0.9,
                subtopic="Fractions"
            )
            mock_bedrock.parse_query_with_haiku.return_value = mock_intent
            
            # Create test event
            event = {
                "body": json.dumps({"query": query})
            }
            
            # Record start time
            start_time = time.time()
            
            # Call handler
            response = interpret_handler(event, context)
            
            # Record end time
            end_time = time.time()
            execution_time = end_time - start_time
            
            # Verify response
            assert response["statusCode"] in [200, 504], f"Unexpected status code: {response['statusCode']}"
            
            if response["statusCode"] == 200:
                # Successful response - should complete within reasonable time
                assert execution_time < 30.0, f"Interpretation took {execution_time:.2f}s, exceeding 30s limit"
                
                # Verify response structure
                body = json.loads(response["body"])
                assert "topic" in body
                assert "tier" in body
                assert "count" in body
                assert "confidence" in body
                
            elif response["statusCode"] == 504:
                # Timeout response - should have descriptive error
                body = json.loads(response["body"])
                assert body["error"]["type"] == "TimeoutError"
                assert "30 second timeout" in body["error"]["message"]
                assert "try again" in body["error"]["guidance"].lower()

    @given(
        generation_request=valid_generation_request(),
        context=mock_lambda_context("GenerateLambda")
    )
    @settings(max_examples=100)
    def test_property_8_generation_performance(self, generation_request, context):
        """
        Feature: gcse-question-generator, Property 8: Generation Performance
        
        For any generation request, the System should complete processing 
        within 60 seconds or return a timeout error with descriptive message.
        
        **Validates: Requirements 7.5**
        """
        # Mock all external dependencies
        with patch('src.lambda_handlers.generate_lambda.bedrock_service') as mock_bedrock, \
             patch('src.lambda_handlers.generate_lambda.content_service') as mock_content, \
             patch('src.lambda_handlers.generate_lambda.version_service') as mock_version:
            
            # Mock version service
            mock_version.get_version_selection_logic.return_value = "2024.1"
            
            # Mock content service
            mock_content.get_specification_content_versioned.return_value = {
                "domain": "number",
                "content": "Test specification content"
            }
            mock_content.get_examples_content.return_value = [
                {"question": "Test question", "mark_scheme": "Test marking"}
            ]
            
            # Mock Bedrock service
            mock_question_set = {
                "questions": [
                    {
                        "id": "q1",
                        "question_text": "Test question",
                        "marks": 2,
                        "tier": generation_request["tier"],
                        "topic": generation_request["topic"]
                    }
                ] * generation_request["count"],
                "mark_scheme": [
                    {
                        "question_id": "q1",
                        "marking_criteria": "Test criteria",
                        "method_marks": 1,
                        "accuracy_marks": 1
                    }
                ] * generation_request["count"],
                "metadata": {
                    "generated_at": "2024-12-26T10:30:00Z",
                    "model_version": "claude-3-sonnet-20240229",
                    "total_marks": generation_request["count"] * 2
                }
            }
            mock_bedrock.generate_questions_with_sonnet.return_value = mock_question_set
            
            # Create test event
            event = {
                "body": json.dumps(generation_request)
            }
            
            # Record start time
            start_time = time.time()
            
            # Call handler
            response = generate_handler(event, context)
            
            # Record end time
            end_time = time.time()
            execution_time = end_time - start_time
            
            # Verify response
            assert response["statusCode"] in [200, 504], f"Unexpected status code: {response['statusCode']}"
            
            if response["statusCode"] == 200:
                # Successful response - should complete within reasonable time
                assert execution_time < 60.0, f"Generation took {execution_time:.2f}s, exceeding 60s limit"
                
                # Verify response structure
                body = json.loads(response["body"])
                assert "questions" in body
                assert "mark_scheme" in body
                assert "metadata" in body
                assert len(body["questions"]) == generation_request["count"]
                
            elif response["statusCode"] == 504:
                # Timeout response - should have descriptive error
                body = json.loads(response["body"])
                assert body["error"]["type"] == "TimeoutError"
                assert "60 second timeout" in body["error"]["message"]
                assert "try again" in body["error"]["guidance"].lower()

    @given(
        query=valid_query_string(),
        remaining_time_ms=st.integers(min_value=100, max_value=4000)  # Low remaining time
    )
    @settings(max_examples=50)
    def test_property_6_interpretation_timeout_handling(self, query, remaining_time_ms):
        """
        Feature: gcse-question-generator, Property 6: Interpretation Performance
        
        For any interpretation request with insufficient remaining time,
        the System should return a timeout error immediately.
        
        **Validates: Requirements 7.4**
        """
        # Create context with low remaining time
        context = Mock()
        context.function_name = "InterpretLambda"
        context.aws_request_id = "test-request-id"
        context.get_remaining_time_in_millis.return_value = remaining_time_ms
        
        # Create test event
        event = {
            "body": json.dumps({"query": query})
        }
        
        # Call handler
        response = interpret_handler(event, context)
        
        # Should return timeout error for very low remaining time
        if remaining_time_ms <= 5000:  # 5 second buffer
            assert response["statusCode"] == 504
            body = json.loads(response["body"])
            assert body["error"]["type"] == "TimeoutError"
            assert "30 second timeout" in body["error"]["message"]

    @given(
        generation_request=valid_generation_request(),
        remaining_time_ms=st.integers(min_value=1000, max_value=9000)  # Low remaining time
    )
    @settings(max_examples=50)
    def test_property_8_generation_timeout_handling(self, generation_request, remaining_time_ms):
        """
        Feature: gcse-question-generator, Property 8: Generation Performance
        
        For any generation request with insufficient remaining time,
        the System should return a timeout error immediately.
        
        **Validates: Requirements 7.5**
        """
        # Create context with low remaining time
        context = Mock()
        context.function_name = "GenerateLambda"
        context.aws_request_id = "test-request-id"
        context.get_remaining_time_in_millis.return_value = remaining_time_ms
        
        # Create test event
        event = {
            "body": json.dumps(generation_request)
        }
        
        # Call handler
        response = generate_handler(event, context)
        
        # Should return timeout error for very low remaining time
        if remaining_time_ms <= 10000:  # 10 second buffer
            assert response["statusCode"] == 504
            body = json.loads(response["body"])
            assert body["error"]["type"] == "TimeoutError"
            assert "60 second timeout" in body["error"]["message"]

    @given(
        query=valid_query_string(),
        context=mock_lambda_context("InterpretLambda", remaining_time_ms=25000)  # Normal time
    )
    @settings(max_examples=50)
    def test_property_6_interpretation_execution_time_logging(self, query, context):
        """
        Feature: gcse-question-generator, Property 6: Interpretation Performance
        
        For any interpretation request, the System should log execution time
        for performance monitoring.
        
        **Validates: Requirements 7.4**
        """
        # Mock the Bedrock service
        with patch('src.lambda_handlers.interpret_lambda.bedrock_service') as mock_bedrock:
            mock_intent = QueryIntent(
                topic="Number",
                tier="Foundation",
                count=5,
                confidence=0.9,
                subtopic="Fractions"
            )
            mock_bedrock.parse_query_with_haiku.return_value = mock_intent
            
            # Create test event
            event = {
                "body": json.dumps({"query": query})
            }
            
            # Call handler with logging capture
            with patch('src.lambda_handlers.interpret_lambda.logger') as mock_logger:
                response = interpret_handler(event, context)
                
                # Verify execution time is logged
                if response["statusCode"] == 200:
                    # Check that logger.info was called with execution_time_ms
                    logged_calls = [call for call in mock_logger.info.call_args_list 
                                  if len(call[1]) > 0 and 'extra' in call[1] 
                                  and 'execution_time_ms' in call[1]['extra']]
                    assert len(logged_calls) > 0, "Execution time should be logged"

    @given(
        generation_request=valid_generation_request(),
        context=mock_lambda_context("GenerateLambda", remaining_time_ms=50000)  # Normal time
    )
    @settings(max_examples=50)
    def test_property_8_generation_execution_time_logging(self, generation_request, context):
        """
        Feature: gcse-question-generator, Property 8: Generation Performance
        
        For any generation request, the System should log execution time
        for performance monitoring.
        
        **Validates: Requirements 7.5**
        """
        # Mock all external dependencies
        with patch('src.lambda_handlers.generate_lambda.bedrock_service') as mock_bedrock, \
             patch('src.lambda_handlers.generate_lambda.content_service') as mock_content, \
             patch('src.lambda_handlers.generate_lambda.version_service') as mock_version:
            
            # Mock services
            mock_version.get_version_selection_logic.return_value = "2024.1"
            mock_content.get_specification_content_versioned.return_value = {"content": "test"}
            mock_content.get_examples_content.return_value = []
            
            mock_question_set = {
                "questions": [{"id": "q1", "question_text": "Test", "marks": 2, 
                             "tier": generation_request["tier"], "topic": generation_request["topic"]}],
                "mark_scheme": [{"question_id": "q1", "marking_criteria": "Test", 
                               "method_marks": 1, "accuracy_marks": 1}],
                "metadata": {"generated_at": "2024-12-26T10:30:00Z", 
                           "model_version": "claude-3-sonnet-20240229", "total_marks": 2}
            }
            mock_bedrock.generate_questions_with_sonnet.return_value = mock_question_set
            
            # Create test event
            event = {
                "body": json.dumps(generation_request)
            }
            
            # Call handler with logging capture
            with patch('src.lambda_handlers.generate_lambda.logger') as mock_logger:
                response = generate_handler(event, context)
                
                # Verify execution time is logged
                if response["statusCode"] == 200:
                    # Check that logger.info was called with execution_time_ms
                    logged_calls = [call for call in mock_logger.info.call_args_list 
                                  if len(call[1]) > 0 and 'extra' in call[1] 
                                  and 'execution_time_ms' in call[1]['extra']]
                    assert len(logged_calls) > 0, "Execution time should be logged"