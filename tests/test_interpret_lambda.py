"""Unit tests for InterpretLambda functionality.

Tests confidence scoring edge cases, input validation boundary conditions,
and Bedrock integration error scenarios.

Requirements: 1.5, 16.1
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError, BotoCoreError

from src.lambda_handlers.interpret_lambda import (
    lambda_handler, 
    _parse_request_body, 
    _create_error_response,
    _process_query_with_enhanced_bedrock
)
from src.services.bedrock_service import BedrockService
from src.models.query_intent import QueryIntent


class TestInterpretLambdaHandler:
    """Unit tests for the main Lambda handler function."""
    
    def test_successful_query_processing(self):
        """Test successful processing of a valid query."""
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
                "body": json.dumps({"query": "Generate 5 Foundation fractions questions"})
            }
            context = Mock()
            context.function_name = "InterpretLambda"
            context.aws_request_id = "test-request-id"
            context.get_remaining_time_in_millis.return_value = 25000  # 25 seconds remaining
            
            # Call handler
            response = lambda_handler(event, context)
            
            # Verify response
            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            assert body["topic"] == "Number"
            assert body["tier"] == "Foundation"
            assert body["count"] == 5
            assert body["confidence"] == 0.9
            assert body["subtopic"] == "Fractions"
    
    def test_empty_query_validation(self):
        """Test validation of empty queries."""
        event = {
            "body": json.dumps({"query": ""})
        }
        context = Mock()
        context.function_name = "InterpretLambda"
        context.aws_request_id = "test-request-id"
        context.get_remaining_time_in_millis.return_value = 25000  # 25 seconds remaining
        
        response = lambda_handler(event, context)
        
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"]["type"] == "ValidationError"
        assert "required" in body["error"]["message"].lower()
    
    def test_query_too_long_validation(self):
        """Test validation of queries exceeding 500 character limit."""
        long_query = "x" * 501
        event = {
            "body": json.dumps({"query": long_query})
        }
        context = Mock()
        context.function_name = "InterpretLambda"
        context.aws_request_id = "test-request-id"
        context.get_remaining_time_in_millis.return_value = 25000  # 25 seconds remaining
        
        response = lambda_handler(event, context)
        
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"]["type"] == "ValidationError"
        assert "too long" in body["error"]["message"].lower()
    
    def test_malicious_content_detection(self):
        """Test detection and rejection of malicious content."""
        malicious_queries = [
            "SELECT * FROM users; DROP TABLE questions;",
            "<script>alert('xss')</script>",
            "'; DELETE FROM database; --"
        ]
        
        for query in malicious_queries:
            event = {
                "body": json.dumps({"query": query})
            }
            context = Mock()
            context.function_name = "InterpretLambda"
            context.aws_request_id = "test-request-id"
            context.get_remaining_time_in_millis.return_value = 25000  # 25 seconds remaining
            
            response = lambda_handler(event, context)
            
            assert response["statusCode"] == 400
            body = json.loads(response["body"])
            assert body["error"]["type"] == "ValidationError"
            assert "malicious" in body["error"]["message"].lower()
    
    def test_bedrock_service_failure_handling(self):
        """Test handling of Bedrock service failures."""
        with patch('src.lambda_handlers.interpret_lambda.bedrock_service') as mock_bedrock:
            mock_bedrock.parse_query_with_haiku.side_effect = Exception("Bedrock API failed")
            
            event = {
                "body": json.dumps({"query": "Generate 5 math questions"})
            }
            context = Mock()
            context.function_name = "InterpretLambda"
            context.aws_request_id = "test-request-id"
            context.get_remaining_time_in_millis.return_value = 25000  # 25 seconds remaining
            
            response = lambda_handler(event, context)
            
            assert response["statusCode"] == 500
            body = json.loads(response["body"])
            assert body["error"]["type"] == "InternalError"
            assert "try again later" in body["error"]["guidance"].lower()
    
    def test_invalid_json_body_handling(self):
        """Test handling of invalid JSON in request body."""
        event = {
            "body": "invalid json {"
        }
        context = Mock()
        context.function_name = "InterpretLambda"
        context.aws_request_id = "test-request-id"
        context.get_remaining_time_in_millis.return_value = 25000  # 25 seconds remaining
        
        response = lambda_handler(event, context)
        
        assert response["statusCode"] == 500
        body = json.loads(response["body"])
        assert body["error"]["type"] == "InternalError"
    
    def test_missing_request_body(self):
        """Test handling of missing request body."""
        event = {}
        context = Mock()
        context.function_name = "InterpretLambda"
        context.aws_request_id = "test-request-id"
        context.get_remaining_time_in_millis.return_value = 25000  # 25 seconds remaining
        
        response = lambda_handler(event, context)
        
        assert response["statusCode"] == 500
        body = json.loads(response["body"])
        assert body["error"]["type"] == "InternalError"


class TestBedrockService:
    """Unit tests for BedrockService functionality."""
    
    def test_confidence_scoring_edge_cases(self):
        """Test confidence scoring algorithm with various edge cases."""
        service = BedrockService()
        
        # Test case 1: Perfect match - topic, tier, and count all mentioned
        confidence = service._calculate_confidence_score(
            topic="Number",
            tier="Foundation", 
            count=5,
            original_query="Generate 5 Foundation number questions",
            model_confidence=0.9
        )
        assert abs(confidence - 0.9) < 0.001  # No reduction
        
        # Test case 2: Missing tier mention
        confidence = service._calculate_confidence_score(
            topic="Algebra",
            tier="Higher",
            count=3,
            original_query="Generate 3 algebra questions",
            model_confidence=0.8
        )
        assert abs(confidence - 0.7) < 0.001  # Reduced by 0.1 for missing tier
        
        # Test case 3: Missing topic keywords
        confidence = service._calculate_confidence_score(
            topic="Statistics",
            tier="Foundation",
            count=2,
            original_query="Generate 2 Foundation questions",
            model_confidence=0.7
        )
        assert abs(confidence - 0.5) < 0.001  # Reduced by 0.2 for missing topic keywords
        
        # Test case 4: No count mentioned
        confidence = service._calculate_confidence_score(
            topic="Geometry",
            tier="Higher",
            count=5,
            original_query="Generate Higher geometry questions",
            model_confidence=0.6
        )
        assert abs(confidence - 0.5) < 0.001  # Reduced by 0.1 for missing count
        
        # Test case 5: Confidence floor at 0.0
        confidence = service._calculate_confidence_score(
            topic="Probability",
            tier="Foundation",
            count=1,
            original_query="help me",
            model_confidence=0.1
        )
        assert confidence == 0.0  # Should not go below 0.0
        
        # Test case 6: Confidence ceiling at 1.0
        confidence = service._calculate_confidence_score(
            topic="Number",
            tier="Foundation",
            count=5,
            original_query="Generate 5 Foundation number fraction questions",
            model_confidence=1.2  # Above 1.0
        )
        assert confidence == 1.0  # Should not exceed 1.0
    
    def test_bedrock_api_retry_logic(self):
        """Test exponential backoff retry logic for Bedrock API failures."""
        with patch('boto3.client') as mock_boto_client:
            mock_client = Mock()
            mock_boto_client.return_value = mock_client
            
            # Mock ClientError for first 3 attempts, success on 4th
            mock_client.converse.side_effect = [
                ClientError(
                    error_response={'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
                    operation_name='Converse'
                ),
                ClientError(
                    error_response={'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
                    operation_name='Converse'
                ),
                ClientError(
                    error_response={'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
                    operation_name='Converse'
                ),
                {
                    'output': {
                        'message': {
                            'content': [{'text': '{"topic": "Number", "tier": "Foundation", "count": 5, "confidence": 0.8}'}]
                        }
                    }
                }
            ]
            
            service = BedrockService()
            
            # Mock time.sleep to avoid actual delays in tests
            with patch('time.sleep'):
                result = service._call_bedrock_with_retry(
                    model_id='test-model',
                    prompt='test prompt',
                    request_id='test-id'
                )
            
            assert '"topic": "Number"' in result
            assert mock_client.converse.call_count == 4
    
    def test_bedrock_api_max_retries_exceeded(self):
        """Test behavior when max retries are exceeded."""
        with patch('boto3.client') as mock_boto_client:
            mock_client = Mock()
            mock_boto_client.return_value = mock_client
            
            # Mock consistent failures
            mock_client.converse.side_effect = ClientError(
                error_response={'Error': {'Code': 'ServiceUnavailable', 'Message': 'Service down'}},
                operation_name='Converse'
            )
            
            service = BedrockService()
            
            with patch('time.sleep'):
                with pytest.raises(Exception, match="Bedrock API failed after 4 attempts"):
                    service._call_bedrock_with_retry(
                        model_id='test-model',
                        prompt='test prompt',
                        request_id='test-id'
                    )
            
            assert mock_client.converse.call_count == 4  # 3 retries + 1 initial
    
    def test_boto_core_error_handling(self):
        """Test handling of BotoCoreError exceptions."""
        with patch('boto3.client') as mock_boto_client:
            mock_client = Mock()
            mock_boto_client.return_value = mock_client
            
            # Mock BotoCoreError
            mock_client.converse.side_effect = BotoCoreError()
            
            service = BedrockService()
            
            with patch('time.sleep'):
                with pytest.raises(Exception, match="Boto3 error after 4 attempts"):
                    service._call_bedrock_with_retry(
                        model_id='test-model',
                        prompt='test prompt',
                        request_id='test-id'
                    )
    
    def test_haiku_response_parsing_edge_cases(self):
        """Test parsing of various Claude Haiku response formats."""
        service = BedrockService()
        
        # Test case 1: Valid JSON response
        response = '{"topic": "Number", "tier": "Foundation", "count": 5, "confidence": 0.8}'
        intent = service._parse_haiku_response(response, "test query", "test-id")
        assert intent.topic == "Number"
        assert intent.tier == "Foundation"
        assert intent.count == 5
        
        # Test case 2: JSON wrapped in markdown
        response = '```json\n{"topic": "Algebra", "tier": "Higher", "count": 3, "confidence": 0.9}\n```'
        intent = service._parse_haiku_response(response, "test query", "test-id")
        assert intent.topic == "Algebra"
        assert intent.tier == "Higher"
        
        # Test case 3: Invalid topic gets corrected
        response = '{"topic": "InvalidTopic", "tier": "Foundation", "count": 2, "confidence": 0.7}'
        intent = service._parse_haiku_response(response, "test query", "test-id")
        assert intent.topic == "Number"  # Should default to Number
        
        # Test case 4: Invalid tier gets corrected
        response = '{"topic": "Number", "tier": "InvalidTier", "count": 4, "confidence": 0.6}'
        intent = service._parse_haiku_response(response, "test query", "test-id")
        assert intent.tier == "Foundation"  # Should default to Foundation
        
        # Test case 5: Invalid count gets corrected
        response = '{"topic": "Number", "tier": "Foundation", "count": 100, "confidence": 0.5}'
        intent = service._parse_haiku_response(response, "test query", "test-id")
        assert intent.count == 5  # Should default to 5
        
        # Test case 6: Missing required fields raises exception
        response = '{"topic": "Number"}'  # Missing tier, count, confidence
        with pytest.raises(Exception, match="Missing required field"):
            service._parse_haiku_response(response, "test query", "test-id")
        
        # Test case 7: Invalid JSON raises exception
        response = 'not json at all'
        with pytest.raises(Exception, match="No JSON found in response"):
            service._parse_haiku_response(response, "test query", "test-id")
    
    def test_prompt_construction(self):
        """Test construction of interpretation prompts."""
        service = BedrockService()
        
        query = "Generate 5 Foundation algebra questions"
        prompt = service._construct_interpretation_prompt(query)
        
        # Verify prompt contains required elements
        assert query in prompt
        assert "Valid topics:" in prompt
        assert "Valid tiers:" in prompt
        assert "JSON" in prompt
        assert all(topic in prompt for topic in ["Number", "Algebra", "Geometry"])
        assert "Foundation" in prompt and "Higher" in prompt


class TestUtilityFunctions:
    """Unit tests for utility functions."""
    
    def test_parse_request_body_variations(self):
        """Test parsing of different request body formats."""
        # Test string JSON body
        event1 = {"body": '{"query": "test"}'}
        result1 = _parse_request_body(event1)
        assert result1 == {"query": "test"}
        
        # Test dict body
        event2 = {"body": {"query": "test"}}
        result2 = _parse_request_body(event2)
        assert result2 == {"query": "test"}
        
        # Test missing body
        event3 = {}
        with pytest.raises(ValueError, match="Missing request body"):
            _parse_request_body(event3)
        
        # Test invalid JSON
        event4 = {"body": "invalid{json"}
        with pytest.raises(ValueError, match="Invalid JSON"):
            _parse_request_body(event4)
    
    def test_error_response_creation(self):
        """Test creation of standardized error responses."""
        response = _create_error_response(
            400,
            "ValidationError",
            "Test message",
            "Test guidance",
            "test-id",
            "Test details"
        )
        
        assert response["statusCode"] == 400
        assert response["headers"]["Content-Type"] == "application/json"
        assert response["headers"]["X-Request-ID"] == "test-id"
        
        body = json.loads(response["body"])
        assert body["error"]["type"] == "ValidationError"
        assert body["error"]["message"] == "Test message"
        assert body["error"]["guidance"] == "Test guidance"
        assert body["error"]["request_id"] == "test-id"
        assert body["error"]["details"] == "Test details"
        assert "timestamp" in body["error"]
    
    def test_error_response_with_retry_after(self):
        """Test error response includes retry_after for 429 status."""
        response = _create_error_response(
            429,
            "TooManyRequests",
            "Rate limit exceeded",
            "Wait before retrying",
            "test-id"
        )
        
        body = json.loads(response["body"])
        assert body["error"]["retry_after"] == 60
    
    def test_input_validation_boundary_conditions(self):
        """Test input validation at boundary conditions."""
        from src.utils.validation import validate_query_input
        
        # Test exactly 500 characters (should pass)
        query_500 = "x" * 500
        result = validate_query_input(query_500)
        assert result["valid"] is True
        
        # Test 501 characters (should fail)
        query_501 = "x" * 501
        with pytest.raises(ValueError, match="too long"):
            validate_query_input(query_501)
        
        # Test single character (should pass)
        result = validate_query_input("x")
        assert result["valid"] is True
        
        # Test whitespace only (should fail)
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_query_input("   ")
        
        # Test empty string (should fail)
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_query_input("")