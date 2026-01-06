"""
Property-based tests for enhanced query parsing functionality.

Feature: gcse-question-generator-v2, Property 4: Query Parsing Completeness
For any valid user query, InterpretLambda should parse it into a structured intent 
containing topic, tier, and count fields.
"""

import json
import pytest
from hypothesis import given, strategies as st, assume
from unittest.mock import Mock, patch, MagicMock

from src.lambda_handlers.interpret_lambda import lambda_handler
from src.models.query_intent import QueryIntent, EnhancedInterpretResponse


# Test data generators
@st.composite
def valid_query_data(draw):
    """Generate valid query data for testing."""
    topics = ["Number", "Algebra", "Geometry", "Statistics", "Probability", "Ratio"]
    tiers = ["Foundation", "Higher"]
    
    topic = draw(st.sampled_from(topics))
    tier = draw(st.sampled_from(tiers))
    count = draw(st.integers(min_value=1, max_value=100))
    
    # Generate natural language query
    query_templates = [
        f"Generate {count} {tier.lower()} questions on {topic.lower()}",
        f"Create {count} {topic.lower()} questions for {tier.lower()} tier",
        f"I need {count} questions about {topic.lower()} at {tier.lower()} level",
        f"Make {count} {tier.lower()} tier {topic.lower()} problems"
    ]
    
    query = draw(st.sampled_from(query_templates))
    
    return {
        "query": query,
        "expected_topic": topic,
        "expected_tier": tier,
        "expected_count": count
    }


@st.composite
def enhanced_query_event(draw):
    """Generate enhanced query event with user_id and session_token."""
    query_data = draw(valid_query_data())
    user_id = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    session_token = draw(st.text(min_size=10, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    
    return {
        "body": json.dumps({
            "query": query_data["query"],
            "user_id": user_id,
            "session_token": session_token
        }),
        "httpMethod": "POST",
        "headers": {"X-API-Key": "test-key"}
    }, query_data


class TestQueryParsingCompleteness:
    """Test suite for query parsing completeness property."""
    
    @patch('src.lambda_handlers.interpret_lambda.authenticate_request')
    @patch('src.lambda_handlers.interpret_lambda.check_rate_limit')
    @patch('src.lambda_handlers.interpret_lambda.bedrock_service')
    @patch('src.lambda_handlers.interpret_lambda.content_service')
    @patch('src.lambda_handlers.interpret_lambda.get_cached_query_response')
    @patch('src.lambda_handlers.interpret_lambda.cache_query_response')
    @given(event_and_data=enhanced_query_event())
    def test_query_parsing_completeness_property(
        self, 
        mock_cache_response,
        mock_get_cache,
        mock_content_service,
        mock_bedrock_service,
        mock_rate_limit,
        mock_auth,
        event_and_data
    ):
        """
        Feature: gcse-question-generator-v2, Property 4: Query Parsing Completeness
        For any valid user query, InterpretLambda should parse it into a structured intent 
        containing topic, tier, and count fields.
        """
        event, query_data = event_and_data
        
        # Setup mocks
        mock_auth.return_value = (True, "test-client", None)
        mock_rate_limit.return_value = (True, {})
        mock_get_cache.return_value = None  # Force fresh processing
        
        # Mock QueryIntent response
        mock_intent = QueryIntent(
            topic=query_data["expected_topic"],
            tier=query_data["expected_tier"],
            count=query_data["expected_count"],
            confidence=0.9,
            subtopic="test_subtopic"
        )
        mock_bedrock_service.parse_query_with_haiku.return_value = mock_intent
        
        # Mock specification content
        mock_spec_content = {
            "learning_objectives": ["Test objective 1", "Test objective 2"],
            "assessment_objectives": ["AO1", "AO2", "AO3"],
            "common_misconceptions": ["Test misconception"],
            "key_concepts": ["Test concept"]
        }
        mock_content_service.get_specification_content.return_value = mock_spec_content
        mock_content_service.get_examples_content.return_value = []
        
        # Create mock context
        mock_context = Mock()
        mock_context.function_name = "InterpretLambda"
        mock_context.aws_request_id = "test-request-123"
        mock_context.get_remaining_time_in_millis.return_value = 30000
        
        # Execute the lambda handler
        response = lambda_handler(event, mock_context)
        
        # Verify response structure
        assert response["statusCode"] == 200
        
        # Parse response body
        response_body = json.loads(response["body"])
        
        # Property: Response must contain structured intent with required fields
        assert "intent" in response_body
        intent = response_body["intent"]
        
        # Verify required fields are present
        required_fields = ["topic", "tier", "count"]
        for field in required_fields:
            assert field in intent, f"Missing required field: {field}"
        
        # Verify field types and values
        assert isinstance(intent["topic"], str)
        assert isinstance(intent["tier"], str)
        assert isinstance(intent["count"], int)
        
        # Verify tier is valid
        assert intent["tier"] in ["Foundation", "Higher"]
        
        # Verify count is within valid range
        assert 1 <= intent["count"] <= 100
        
        # Verify enhanced response structure
        assert "enriched_prompt" in response_body
        assert "difficulty_guidance" in response_body
        assert "specification_context" in response_body
        assert "topic_coverage" in response_body
        
        # Verify enriched prompt is not empty
        assert len(response_body["enriched_prompt"]) > 0
        
        # Verify difficulty guidance structure
        difficulty_guidance = response_body["difficulty_guidance"]
        assert "min_difficulty" in difficulty_guidance
        assert "max_difficulty" in difficulty_guidance
        assert "target_distribution" in difficulty_guidance
        
        # Verify specification context structure
        spec_context = response_body["specification_context"]
        assert "learning_objectives" in spec_context
        assert "assessment_objectives" in spec_context
        assert "teacher_guidance" in spec_context
    
    @patch('src.lambda_handlers.interpret_lambda.authenticate_request')
    @patch('src.lambda_handlers.interpret_lambda.check_rate_limit')
    @patch('src.lambda_handlers.interpret_lambda.bedrock_service')
    @patch('src.lambda_handlers.interpret_lambda.content_service')
    @patch('src.lambda_handlers.interpret_lambda.get_cached_query_response')
    @given(query_text=st.text(min_size=1, max_size=100))
    def test_query_parsing_handles_any_text_input(
        self,
        mock_get_cache,
        mock_content_service,
        mock_bedrock_service,
        mock_rate_limit,
        mock_auth,
        query_text
    ):
        """
        Property: For any text input, the system should either parse successfully 
        or return a proper error response.
        """
        # Setup mocks
        mock_auth.return_value = (True, "test-client", None)
        mock_rate_limit.return_value = (True, {})
        mock_get_cache.return_value = None
        
        # Mock a valid intent response (system should handle any input gracefully)
        mock_intent = QueryIntent(
            topic="Number",
            tier="Foundation", 
            count=5,
            confidence=0.5
        )
        mock_bedrock_service.parse_query_with_haiku.return_value = mock_intent
        mock_content_service.get_specification_content.return_value = {}
        mock_content_service.get_examples_content.return_value = []
        
        event = {
            "body": json.dumps({
                "query": query_text,
                "user_id": "test_user",
                "session_token": "test_token"
            }),
            "httpMethod": "POST",
            "headers": {"X-API-Key": "test-key"}
        }
        
        mock_context = Mock()
        mock_context.function_name = "InterpretLambda"
        mock_context.aws_request_id = "test-request-123"
        mock_context.get_remaining_time_in_millis.return_value = 30000
        
        # Execute
        response = lambda_handler(event, mock_context)
        
        # Property: System should always return a valid HTTP response
        assert "statusCode" in response
        assert response["statusCode"] in [200, 400, 500]
        
        # Property: Response should always have proper structure
        assert "headers" in response
        assert "body" in response
        
        # If successful, should have proper structure
        if response["statusCode"] == 200:
            response_body = json.loads(response["body"])
            assert "intent" in response_body
            assert "enriched_prompt" in response_body


if __name__ == "__main__":
    pytest.main([__file__, "-v"])