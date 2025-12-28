"""Property-based tests for query interpretation functionality.

Feature: gcse-question-generator, Property 1: Query Parsing Completeness
Feature: gcse-question-generator, Property 2: Error Handling for Invalid Queries
Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from hypothesis import given, strategies as st, assume, settings
from src.lambda_handlers.interpret_lambda import lambda_handler, _parse_request_body, _create_error_response
from src.services.bedrock_service import BedrockService
from src.models.query_intent import QueryIntent
from src.utils.constants import VALID_TOPICS, VALID_TIERS


# Hypothesis strategies for generating test data
@st.composite
def valid_natural_language_query_strategy(draw):
    """Generate valid natural language queries containing topic, tier, and count information."""
    topic = draw(st.sampled_from(VALID_TOPICS))
    tier = draw(st.sampled_from(VALID_TIERS))
    count = draw(st.integers(min_value=1, max_value=50))
    
    # Create query templates that contain the required information
    templates = [
        f"Generate {count} {tier.lower()} {topic.lower()} questions",
        f"I need {count} questions on {topic.lower()} for {tier.lower()} tier",
        f"Create {count} {topic.lower()} problems at {tier.lower()} level",
        f"{count} {tier.lower()} questions about {topic.lower()}",
        f"Make {count} {topic.lower()} questions for {tier.lower()} students"
    ]
    
    query = draw(st.sampled_from(templates))
    
    # Add optional subtopic information
    subtopics = {
        "Number": ["fractions", "decimals", "percentages", "integers"],
        "Algebra": ["equations", "expressions", "sequences", "graphs"],
        "Geometry": ["angles", "shapes", "area", "perimeter"],
        "Statistics": ["data analysis", "graphs", "averages"],
        "Probability": ["probability", "chance"],
        "Ratio": ["ratio", "proportion", "scale"]
    }
    
    if draw(st.booleans()):  # 50% chance to add subtopic
        subtopic = draw(st.sampled_from(subtopics.get(topic, [])))
        query = query.replace(topic.lower(), f"{topic.lower()} {subtopic}")
    
    return query


@st.composite
def invalid_query_strategy(draw):
    """Generate invalid, ambiguous, or malformed queries."""
    invalid_types = [
        # Empty or whitespace only
        "",
        "   ",
        "\n\t",
        
        # Too long queries
        "x" * 501,
        
        # Malicious content (using corrected patterns)
        "SELECT * FROM users",
        "DROP TABLE questions",
        "<script>alert('xss')</script>",
        "INSERT INTO database VALUES",
        
        # Ambiguous queries
        "questions please",
        "help me",
        "I need something",
        "math stuff",
        
        # Incomplete information
        "5 questions",  # Missing topic and tier
        "algebra questions",  # Missing count and tier
        "foundation level",  # Missing topic and count
    ]
    
    return draw(st.sampled_from(invalid_types))


@st.composite
def api_gateway_event_strategy(draw, query_strategy):
    """Generate API Gateway event structures."""
    query = draw(query_strategy)
    
    # Create valid API Gateway event structure
    event = {
        "httpMethod": "POST",
        "path": "/api/interpret",
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps({"query": query})
    }
    
    return event


class TestPropertyQueryInterpretation:
    """Property-based tests for query interpretation functionality."""
    
    @given(query=valid_natural_language_query_strategy())
    @settings(max_examples=50, deadline=None)  # Disable deadline for mocked tests
    def test_query_parsing_completeness_property(self, query):
        """Feature: gcse-question-generator, Property 1: Query Parsing Completeness
        
        For any valid natural language query containing topic, tier, and count information,
        the Interpret_Service should extract all components into a structured intent 
        with the correct topic, tier, and count values.
        
        Validates: Requirements 1.1, 1.2, 1.3, 1.4
        """
        # Mock the Bedrock service to return a valid QueryIntent
        with patch('src.lambda_handlers.interpret_lambda.bedrock_service') as mock_bedrock:
            # Create a mock response based on the query content
            mock_intent = self._create_mock_intent_from_query(query)
            mock_bedrock.parse_query_with_haiku.return_value = mock_intent
            
            # Create API Gateway event
            event = {
                "httpMethod": "POST",
                "path": "/api/interpret",
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"query": query})
            }
            
            # Mock Lambda context
            context = Mock()
            context.function_name = "InterpretLambda"
            context.aws_request_id = "test-request-id"
            
            # Call the Lambda handler
            response = lambda_handler(event, context)
            
            # Verify successful response
            assert response["statusCode"] == 200
            
            # Parse response body
            response_body = json.loads(response["body"])
            
            # Verify all required components are present
            assert "topic" in response_body
            assert "tier" in response_body
            assert "count" in response_body
            assert "confidence" in response_body
            
            # Verify components have valid values
            assert response_body["topic"] in VALID_TOPICS
            assert response_body["tier"] in VALID_TIERS
            assert 1 <= response_body["count"] <= 50
            assert 0.0 <= response_body["confidence"] <= 1.0
            
            # Verify response includes metadata
            assert "request_id" in response_body
            assert "timestamp" in response_body
            assert "specification_version" in response_body
    
    @given(query=invalid_query_strategy())
    @settings(max_examples=30, deadline=None)  # Disable deadline for mocked tests
    def test_error_handling_for_invalid_queries_property(self, query):
        """Feature: gcse-question-generator, Property 2: Error Handling for Invalid Queries
        
        For any ambiguous, incomplete, or malformed query, the System should return 
        a descriptive error message containing error type, user-actionable guidance, 
        and a unique request ID.
        
        Validates: Requirements 1.5
        """
        # Mock the Bedrock service to avoid real API calls
        with patch('src.lambda_handlers.interpret_lambda.bedrock_service') as mock_bedrock:
            # For invalid queries that pass validation, mock a parsing failure
            mock_bedrock.parse_query_with_haiku.side_effect = Exception("Unable to parse ambiguous query")
            
            # Create API Gateway event
            event = {
                "httpMethod": "POST",
                "path": "/api/interpret",
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"query": query})
            }
            
            # Mock Lambda context
            context = Mock()
            context.function_name = "InterpretLambda"
            context.aws_request_id = "test-request-id"
            
            # Call the Lambda handler
            response = lambda_handler(event, context)
            
            # For malicious content or validation errors, expect 400
            if (any(pattern in query.lower() for pattern in ["select", "insert", "drop", "script", "javascript"]) 
                or len(query) > 500 
                or any(char in query for char in ["'", '"', ";"])):
                assert response["statusCode"] == 400
                response_body = json.loads(response["body"])
                
                # Verify error response structure
                assert "error" in response_body
                error = response_body["error"]
                
                # Verify required error fields
                assert "type" in error
                assert "message" in error
                assert "guidance" in error
                assert "request_id" in error
                assert "timestamp" in error
                
                # Verify error type is appropriate
                assert error["type"] in ["ValidationError", "TimeoutError", "ServiceUnavailable", "InternalError"]
                
                # Verify guidance is actionable
                assert len(error["guidance"]) > 0
                assert isinstance(error["guidance"], str)
                
                # Verify request ID is present and non-empty
                assert len(error["request_id"]) > 0
            
            # For empty queries, also expect 400
            elif not query.strip():
                assert response["statusCode"] == 400
                response_body = json.loads(response["body"])
                assert "error" in response_body
                assert response_body["error"]["type"] == "ValidationError"
            
            # For queries that pass validation but fail parsing, expect 500
            elif len(query.strip()) > 0 and len(query) <= 500:
                assert response["statusCode"] == 500
                response_body = json.loads(response["body"])
                assert "error" in response_body
                assert response_body["error"]["type"] == "InternalError"
    
    @given(
        topic=st.sampled_from(VALID_TOPICS),
        tier=st.sampled_from(VALID_TIERS),
        count=st.integers(min_value=1, max_value=50),
        confidence=st.floats(min_value=0.0, max_value=1.0)
    )
    def test_bedrock_service_parsing_consistency(self, topic, tier, count, confidence):
        """For any valid topic, tier, count, and confidence combination,
        the BedrockService should create a consistent QueryIntent."""
        
        # Create a mock Bedrock response
        mock_response = json.dumps({
            "topic": topic,
            "subtopic": None,
            "tier": tier,
            "count": count,
            "marks": None,
            "confidence": confidence
        })
        
        # Mock the Bedrock client
        with patch('boto3.client') as mock_boto_client:
            mock_client = Mock()
            mock_boto_client.return_value = mock_client
            
            # Mock the converse API response
            mock_client.converse.return_value = {
                'output': {
                    'message': {
                        'content': [{'text': mock_response}]
                    }
                }
            }
            
            # Create BedrockService and test parsing
            service = BedrockService()
            query = f"Generate {count} {tier.lower()} {topic.lower()} questions"
            
            intent = service.parse_query_with_haiku(query, "test-request-id")
            
            # Verify the parsed intent matches expected values
            assert intent.topic == topic
            assert intent.tier == tier
            assert intent.count == count
            # Confidence might be adjusted by the service, so just check it's valid
            assert 0.0 <= intent.confidence <= 1.0
    
    def test_request_body_parsing_robustness(self):
        """For various request body formats, the parser should handle them appropriately."""
        
        # Test valid JSON string body
        event1 = {"body": '{"query": "test query"}'}
        result1 = _parse_request_body(event1)
        assert result1 == {"query": "test query"}
        
        # Test already parsed dict body
        event2 = {"body": {"query": "test query"}}
        result2 = _parse_request_body(event2)
        assert result2 == {"query": "test query"}
        
        # Test missing body
        event3 = {}
        with pytest.raises(ValueError, match="Missing request body"):
            _parse_request_body(event3)
        
        # Test invalid JSON
        event4 = {"body": "invalid json {"}
        with pytest.raises(ValueError, match="Invalid JSON"):
            _parse_request_body(event4)
    
    def test_error_response_format_consistency(self):
        """For any error response, the format should be consistent and complete."""
        
        error_response = _create_error_response(
            400,
            "ValidationError",
            "Test error message",
            "Test guidance",
            "test-request-id",
            "Test details"
        )
        
        # Verify response structure
        assert error_response["statusCode"] == 400
        assert "headers" in error_response
        assert "body" in error_response
        
        # Verify headers
        headers = error_response["headers"]
        assert headers["Content-Type"] == "application/json"
        assert headers["X-Request-ID"] == "test-request-id"
        
        # Verify error body structure
        body = json.loads(error_response["body"])
        assert "error" in body
        
        error = body["error"]
        assert error["type"] == "ValidationError"
        assert error["message"] == "Test error message"
        assert error["guidance"] == "Test guidance"
        assert error["request_id"] == "test-request-id"
        assert error["details"] == "Test details"
        assert "timestamp" in error
    
    def _create_mock_intent_from_query(self, query: str) -> QueryIntent:
        """Create a mock QueryIntent based on query content."""
        query_lower = query.lower()
        
        # Extract topic
        topic = "Number"  # Default
        for valid_topic in VALID_TOPICS:
            if valid_topic.lower() in query_lower:
                topic = valid_topic
                break
        
        # Extract tier
        tier = "Foundation"  # Default
        if "higher" in query_lower:
            tier = "Higher"
        
        # Extract count
        import re
        count_match = re.search(r'\d+', query)
        count = int(count_match.group()) if count_match else 5
        count = max(1, min(50, count))  # Clamp to valid range
        
        return QueryIntent(
            topic=topic,
            tier=tier,
            count=count,
            confidence=0.8,
            subtopic=None,
            marks=None,
            specification_version="latest"
        )