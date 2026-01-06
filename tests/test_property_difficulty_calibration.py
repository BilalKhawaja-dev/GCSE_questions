"""
Property-based tests for difficulty calibration functionality.

Feature: gcse-question-generator-v2, Property 6: Difficulty Calibration Accuracy
For any tier specification (Foundation or Higher), InterpretLambda should 
provide difficulty guidance within the correct range (1-5 for Foundation, 6-10 for Higher).
"""

import json
import pytest
from hypothesis import given, strategies as st, assume
from unittest.mock import Mock, patch

from src.lambda_handlers.interpret_lambda import (
    lambda_handler, 
    _generate_difficulty_guidance,
    _calculate_difficulty_distribution,
    _get_topic_difficulty_adjustments,
    _get_count_specific_recommendations
)
from src.models.query_intent import QueryIntent


# Test data generators
@st.composite
def query_intent_with_tier(draw):
    """Generate QueryIntent with specific tier for testing."""
    topics = ["Number", "Algebra", "Geometry", "Statistics", "Probability", "Ratio"]
    tiers = ["Foundation", "Higher"]
    
    topic = draw(st.sampled_from(topics))
    tier = draw(st.sampled_from(tiers))
    count = draw(st.integers(min_value=1, max_value=100))
    
    return QueryIntent(
        topic=topic,
        tier=tier,
        count=count,
        confidence=0.8,
        subtopic=draw(st.one_of(st.none(), st.text(min_size=3, max_size=20)))
    )


class TestDifficultyCalibrationAccuracy:
    """Test suite for difficulty calibration accuracy property."""
    
    @patch('src.lambda_handlers.interpret_lambda.authenticate_request')
    @patch('src.lambda_handlers.interpret_lambda.check_rate_limit')
    @patch('src.lambda_handlers.interpret_lambda.bedrock_service')
    @patch('src.lambda_handlers.interpret_lambda.content_service')
    @patch('src.lambda_handlers.interpret_lambda.get_cached_query_response')
    @patch('src.lambda_handlers.interpret_lambda.cache_query_response')
    @given(intent=query_intent_with_tier())
    def test_difficulty_calibration_accuracy_property(
        self,
        mock_cache_response,
        mock_get_cache,
        mock_content_service,
        mock_bedrock_service,
        mock_rate_limit,
        mock_auth,
        intent
    ):
        """
        Feature: gcse-question-generator-v2, Property 6: Difficulty Calibration Accuracy
        For any tier specification (Foundation or Higher), InterpretLambda should 
        provide difficulty guidance within the correct range (1-5 for Foundation, 6-10 for Higher).
        """
        # Setup mocks
        mock_auth.return_value = (True, "test-client", None)
        mock_rate_limit.return_value = (True, {})
        mock_get_cache.return_value = None  # Force fresh processing
        
        mock_bedrock_service.parse_query_with_haiku.return_value = intent
        mock_content_service.get_specification_content.return_value = {
            "learning_objectives": ["Test objective"],
            "assessment_objectives": ["AO1"],
            "common_misconceptions": [],
            "key_concepts": []
        }
        mock_content_service.get_examples_content.return_value = []
        
        # Create test event
        event = {
            "body": json.dumps({
                "query": f"Generate {intent.count} {intent.tier.lower()} questions on {intent.topic.lower()}",
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
        
        # Execute the lambda handler
        response = lambda_handler(event, mock_context)
        
        # Verify response structure
        assert response["statusCode"] == 200
        response_body = json.loads(response["body"])
        
        # Property: Difficulty guidance must be present
        assert "difficulty_guidance" in response_body
        difficulty_guidance = response_body["difficulty_guidance"]
        
        # Property: Must contain required fields
        required_fields = ["min_difficulty", "max_difficulty", "target_distribution", "tier_description"]
        for field in required_fields:
            assert field in difficulty_guidance, f"Missing required field: {field}"
        
        # Property: Difficulty range must match tier
        min_difficulty = difficulty_guidance["min_difficulty"]
        max_difficulty = difficulty_guidance["max_difficulty"]
        
        if intent.tier == "Foundation":
            # Foundation tier: difficulty scores 1-5
            assert min_difficulty == 1, f"Foundation min_difficulty should be 1, got {min_difficulty}"
            assert max_difficulty == 5, f"Foundation max_difficulty should be 5, got {max_difficulty}"
        else:  # Higher tier
            # Higher tier: difficulty scores 6-10
            assert min_difficulty == 6, f"Higher min_difficulty should be 6, got {min_difficulty}"
            assert max_difficulty == 10, f"Higher max_difficulty should be 10, got {max_difficulty}"
        
        # Property: Target distribution must be valid
        target_distribution = difficulty_guidance["target_distribution"]
        assert isinstance(target_distribution, dict)
        
        # Property: All difficulty scores in distribution must be within tier range
        for difficulty_score in target_distribution.keys():
            difficulty_score = int(difficulty_score)
            assert min_difficulty <= difficulty_score <= max_difficulty, \
                f"Difficulty score {difficulty_score} outside range [{min_difficulty}, {max_difficulty}]"
        
        # Property: Distribution percentages should sum to approximately 1.0
        total_percentage = sum(target_distribution.values())
        assert 0.9 <= total_percentage <= 1.1, f"Distribution percentages sum to {total_percentage}, should be ~1.0"
        
        # Property: All percentages should be positive
        for percentage in target_distribution.values():
            assert percentage > 0, f"All percentages should be positive, got {percentage}"
    
    @given(intent=query_intent_with_tier())
    def test_generate_difficulty_guidance_direct(self, intent):
        """
        Test the _generate_difficulty_guidance function directly.
        """
        # Execute the function
        difficulty_guidance = _generate_difficulty_guidance(intent, "test-request-123")
        
        # Property: Must return a dictionary with required fields
        assert isinstance(difficulty_guidance, dict)
        required_fields = ["min_difficulty", "max_difficulty", "target_distribution", "tier_description"]
        for field in required_fields:
            assert field in difficulty_guidance
        
        # Property: Difficulty range must match tier
        if intent.tier == "Foundation":
            assert difficulty_guidance["min_difficulty"] == 1
            assert difficulty_guidance["max_difficulty"] == 5
            assert "grades 1-5" in difficulty_guidance["tier_description"]
        else:
            assert difficulty_guidance["min_difficulty"] == 6
            assert difficulty_guidance["max_difficulty"] == 10
            assert "grades 4-9" in difficulty_guidance["tier_description"]
        
        # Property: Must contain enhanced features
        assert "grade_mapping" in difficulty_guidance
        assert "recommended_marks_range" in difficulty_guidance
        assert "topic_adjustments" in difficulty_guidance
        assert "count_recommendations" in difficulty_guidance
        
        # Property: Grade mapping must cover the tier range
        grade_mapping = difficulty_guidance["grade_mapping"]
        min_diff = difficulty_guidance["min_difficulty"]
        max_diff = difficulty_guidance["max_difficulty"]
        
        for difficulty in range(min_diff, max_diff + 1):
            assert difficulty in grade_mapping, f"Missing grade mapping for difficulty {difficulty}"
        
        # Property: Recommended marks range must be sensible
        marks_range = difficulty_guidance["recommended_marks_range"]
        for difficulty, mark_range in marks_range.items():
            assert len(mark_range) == 2, f"Mark range should have 2 elements, got {len(mark_range)}"
            assert mark_range[0] <= mark_range[1], f"Mark range should be [min, max], got {mark_range}"
            assert mark_range[0] >= 1, f"Minimum marks should be >= 1, got {mark_range[0]}"
    
    @given(
        count=st.integers(min_value=1, max_value=100),
        tier=st.sampled_from(["Foundation", "Higher"])
    )
    def test_calculate_difficulty_distribution_property(self, count, tier):
        """
        Test the difficulty distribution calculation function.
        """
        distribution = _calculate_difficulty_distribution(count, tier)
        
        # Property: Must return a dictionary
        assert isinstance(distribution, dict)
        
        # Property: All keys must be integers within tier range
        if tier == "Foundation":
            valid_range = range(1, 6)  # 1-5
        else:
            valid_range = range(6, 11)  # 6-10
        
        for difficulty in distribution.keys():
            assert difficulty in valid_range, f"Difficulty {difficulty} not in valid range for {tier}"
        
        # Property: All values must be positive percentages
        for percentage in distribution.values():
            assert 0 < percentage <= 1, f"Percentage {percentage} should be between 0 and 1"
        
        # Property: Percentages should sum to approximately 1.0
        total = sum(distribution.values())
        assert 0.9 <= total <= 1.1, f"Total percentage {total} should be approximately 1.0"
        
        # Property: Should have at least one difficulty level
        assert len(distribution) >= 1, "Distribution should have at least one difficulty level"
    
    @given(
        topic=st.sampled_from(["Number", "Algebra", "Geometry", "Statistics", "Probability", "Ratio"]),
        tier=st.sampled_from(["Foundation", "Higher"])
    )
    def test_topic_difficulty_adjustments_property(self, topic, tier):
        """
        Test the topic-specific difficulty adjustments function.
        """
        adjustments = _get_topic_difficulty_adjustments(topic, tier)
        
        # Property: Must return a dictionary
        assert isinstance(adjustments, dict)
        
        # Property: Must contain expected structure
        expected_keys = ["foundation_focus", "higher_focus", "difficulty_note"]
        for key in expected_keys:
            assert key in adjustments, f"Missing key {key} in topic adjustments"
        
        # Property: Focus areas must be lists of strings
        assert isinstance(adjustments["foundation_focus"], list)
        assert isinstance(adjustments["higher_focus"], list)
        
        for focus_item in adjustments["foundation_focus"]:
            assert isinstance(focus_item, str)
            assert len(focus_item) > 0
        
        for focus_item in adjustments["higher_focus"]:
            assert isinstance(focus_item, str)
            assert len(focus_item) > 0
        
        # Property: Difficulty note must be a non-empty string
        assert isinstance(adjustments["difficulty_note"], str)
        assert len(adjustments["difficulty_note"]) > 0
    
    @given(
        count=st.integers(min_value=1, max_value=100),
        tier=st.sampled_from(["Foundation", "Higher"])
    )
    def test_count_specific_recommendations_property(self, count, tier):
        """
        Test the count-specific recommendations function.
        """
        recommendations = _get_count_specific_recommendations(count, tier)
        
        # Property: Must return a dictionary
        assert isinstance(recommendations, dict)
        
        # Property: Must contain required fields
        required_fields = ["strategy", "recommendation", "variety"]
        for field in required_fields:
            assert field in recommendations, f"Missing field {field}"
            assert isinstance(recommendations[field], str)
            assert len(recommendations[field]) > 0
        
        # Property: Strategy should match count ranges
        if count <= 5:
            assert "focused" in recommendations["strategy"].lower()
        elif count <= 15:
            assert "balanced" in recommendations["strategy"].lower()
        elif count <= 30:
            assert "comprehensive" in recommendations["strategy"].lower()
        else:
            assert "extensive" in recommendations["strategy"].lower()
        
        # Property: Large counts should have grouping suggestions
        if count > 20:
            assert "grouping" in recommendations
            assert "suggestion" in recommendations["grouping"]
            assert "rationale" in recommendations["grouping"]
    
    @given(intent=query_intent_with_tier())
    def test_difficulty_guidance_consistency_property(self, intent):
        """
        Property: For the same input, difficulty guidance should be consistent.
        """
        # Generate guidance twice with same inputs
        guidance1 = _generate_difficulty_guidance(intent, "test-1")
        guidance2 = _generate_difficulty_guidance(intent, "test-2")
        
        # Property: Core guidance should be identical
        assert guidance1["min_difficulty"] == guidance2["min_difficulty"]
        assert guidance1["max_difficulty"] == guidance2["max_difficulty"]
        assert guidance1["tier_description"] == guidance2["tier_description"]
        
        # Property: Target distributions should be identical
        assert guidance1["target_distribution"] == guidance2["target_distribution"]
        
        # Property: Grade mappings should be identical
        assert guidance1["grade_mapping"] == guidance2["grade_mapping"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])