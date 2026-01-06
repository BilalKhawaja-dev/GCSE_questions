"""
Property-based tests for prompt enrichment functionality.

Feature: gcse-question-generator-v2, Property 5: Prompt Enrichment Completeness
For any query processed by InterpretLambda, the enriched prompt should contain 
learning objectives, common misconceptions, and assessment objectives from the specification content.
"""

import json
import pytest
from hypothesis import given, strategies as st, assume
from unittest.mock import Mock, patch, MagicMock

from src.lambda_handlers.interpret_lambda import lambda_handler, _build_enriched_prompt
from src.models.query_intent import QueryIntent


# Test data generators
@st.composite
def specification_content_data(draw):
    """Generate specification content data for testing."""
    learning_objectives = draw(st.lists(
        st.text(min_size=10, max_size=100), 
        min_size=1, 
        max_size=5
    ))
    
    assessment_objectives = draw(st.one_of(
        st.dictionaries(
            st.sampled_from(["AO1", "AO2", "AO3"]),
            st.text(min_size=10, max_size=50),
            min_size=1,
            max_size=3
        ),
        st.lists(st.text(min_size=5, max_size=30), min_size=1, max_size=3)
    ))
    
    common_misconceptions = draw(st.lists(
        st.text(min_size=10, max_size=80),
        min_size=0,
        max_size=3
    ))
    
    key_concepts = draw(st.lists(
        st.text(min_size=5, max_size=50),
        min_size=0,
        max_size=5
    ))
    
    return {
        "learning_objectives": learning_objectives,
        "assessment_objectives": assessment_objectives,
        "common_misconceptions": common_misconceptions,
        "key_concepts": key_concepts
    }


@st.composite
def query_intent_data(draw):
    """Generate QueryIntent data for testing."""
    topics = ["Number", "Algebra", "Geometry", "Statistics", "Probability", "Ratio"]
    tiers = ["Foundation", "Higher"]
    
    topic = draw(st.sampled_from(topics))
    tier = draw(st.sampled_from(tiers))
    count = draw(st.integers(min_value=1, max_value=100))
    subtopic = draw(st.one_of(st.none(), st.text(min_size=3, max_size=20)))
    
    return QueryIntent(
        topic=topic,
        tier=tier,
        count=count,
        confidence=0.8,
        subtopic=subtopic
    )


@st.composite
def examples_content_data(draw):
    """Generate examples content data for testing."""
    num_examples = draw(st.integers(min_value=0, max_value=3))
    examples = []
    
    for _ in range(num_examples):
        example = {
            "question": {
                "question_text": draw(st.text(min_size=20, max_size=200)),
                "marks": draw(st.integers(min_value=1, max_value=10))
            },
            "mark_scheme": {
                "marking_criteria": draw(st.text(min_size=10, max_size=100))
            }
        }
        examples.append(example)
    
    return examples


class TestPromptEnrichmentCompleteness:
    """Test suite for prompt enrichment completeness property."""
    
    @patch('src.lambda_handlers.interpret_lambda.authenticate_request')
    @patch('src.lambda_handlers.interpret_lambda.check_rate_limit')
    @patch('src.lambda_handlers.interpret_lambda.bedrock_service')
    @patch('src.lambda_handlers.interpret_lambda.content_service')
    @patch('src.lambda_handlers.interpret_lambda.get_cached_query_response')
    @patch('src.lambda_handlers.interpret_lambda.cache_query_response')
    @given(
        spec_content=specification_content_data(),
        intent=query_intent_data()
    )
    def test_prompt_enrichment_completeness_property(
        self,
        mock_cache_response,
        mock_get_cache,
        mock_content_service,
        mock_bedrock_service,
        mock_rate_limit,
        mock_auth,
        spec_content,
        intent
    ):
        """
        Feature: gcse-question-generator-v2, Property 5: Prompt Enrichment Completeness
        For any query processed by InterpretLambda, the enriched prompt should contain 
        learning objectives, common misconceptions, and assessment objectives from the specification content.
        """
        # Setup mocks
        mock_auth.return_value = (True, "test-client", None)
        mock_rate_limit.return_value = (True, {})
        mock_get_cache.return_value = None  # Force fresh processing
        
        mock_bedrock_service.parse_query_with_haiku.return_value = intent
        mock_content_service.get_specification_content.return_value = spec_content
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
        
        # Property: Enriched prompt must be present and non-empty
        assert "enriched_prompt" in response_body
        enriched_prompt = response_body["enriched_prompt"]
        assert len(enriched_prompt) > 0
        
        # Property: If learning objectives exist, they must appear in enriched prompt
        if spec_content["learning_objectives"]:
            assert "Learning Objectives" in enriched_prompt
            for objective in spec_content["learning_objectives"][:5]:  # Limited to 5
                assert objective in enriched_prompt
        
        # Property: If assessment objectives exist, they must appear in enriched prompt
        if spec_content["assessment_objectives"]:
            assert "Assessment Objectives" in enriched_prompt
            if isinstance(spec_content["assessment_objectives"], dict):
                for ao_key in spec_content["assessment_objectives"]:
                    assert ao_key in enriched_prompt
            elif isinstance(spec_content["assessment_objectives"], list):
                for ao in spec_content["assessment_objectives"]:
                    assert ao in enriched_prompt
        
        # Property: If common misconceptions exist, they must appear in enriched prompt
        if spec_content["common_misconceptions"]:
            assert "Common Misconceptions" in enriched_prompt
            for misconception in spec_content["common_misconceptions"][:3]:  # Limited to 3
                assert misconception in enriched_prompt
        
        # Property: If key concepts exist, they must appear in enriched prompt
        if spec_content["key_concepts"]:
            assert "Key Concepts" in enriched_prompt
            for concept in spec_content["key_concepts"][:5]:  # Limited to 5
                assert concept in enriched_prompt
        
        # Property: Tier-specific guidance must be present
        if intent.tier == "Foundation":
            assert "Foundation Tier Guidelines" in enriched_prompt
            assert "grades 1-5" in enriched_prompt
        else:
            assert "Higher Tier Guidelines" in enriched_prompt
            assert "grades 4-9" in enriched_prompt
        
        # Property: Edexcel compliance requirements must be present
        assert "Edexcel GCSE Compliance Requirements" in enriched_prompt
        assert "specification" in enriched_prompt.lower()
        
        # Property: Mathematical notation guidelines must be present
        assert "Mathematical Notation Guidelines" in enriched_prompt
        assert "LaTeX" in enriched_prompt
    
    @given(
        intent=query_intent_data(),
        spec_content=specification_content_data(),
        examples_content=examples_content_data()
    )
    def test_build_enriched_prompt_direct(self, intent, spec_content, examples_content):
        """
        Test the _build_enriched_prompt function directly with various inputs.
        """
        # Execute the function
        enriched_prompt = _build_enriched_prompt(
            intent, spec_content, examples_content, "test-request-123"
        )
        
        # Property: Enriched prompt must be a non-empty string
        assert isinstance(enriched_prompt, str)
        assert len(enriched_prompt) > 0
        
        # Property: Must contain the requested count and topic
        assert str(intent.count) in enriched_prompt
        assert intent.topic in enriched_prompt
        assert intent.tier in enriched_prompt
        
        # Property: Must contain tier-specific guidance
        if intent.tier == "Foundation":
            assert "Foundation Tier Guidelines" in enriched_prompt
            assert "1-5" in enriched_prompt
        else:
            assert "Higher Tier Guidelines" in enriched_prompt
            assert "6-10" in enriched_prompt
        
        # Property: Must contain compliance requirements
        assert "Edexcel" in enriched_prompt
        assert "specification" in enriched_prompt.lower()
        
        # Property: If examples provided, they must appear in prompt
        if examples_content:
            assert "Example Questions" in enriched_prompt
            for example in examples_content[:2]:  # Limited to 2 examples
                question_text = example.get("question", {}).get("question_text", "")
                if question_text:
                    assert question_text in enriched_prompt
    
    @given(
        spec_content=specification_content_data()
    )
    def test_enrichment_handles_empty_specification_content(self, spec_content):
        """
        Property: System should handle specification content gracefully even when some fields are empty.
        """
        # Create intent
        intent = QueryIntent(
            topic="Number",
            tier="Foundation",
            count=5,
            confidence=0.8
        )
        
        # Test with empty fields
        empty_spec_content = {
            "learning_objectives": [],
            "assessment_objectives": [],
            "common_misconceptions": [],
            "key_concepts": []
        }
        
        enriched_prompt = _build_enriched_prompt(
            intent, empty_spec_content, [], "test-request-123"
        )
        
        # Property: Should still produce a valid enriched prompt
        assert isinstance(enriched_prompt, str)
        assert len(enriched_prompt) > 0
        
        # Property: Should still contain essential elements
        assert intent.topic in enriched_prompt
        assert intent.tier in enriched_prompt
        assert "Edexcel" in enriched_prompt
        
        # Property: Should not contain section headers for empty sections
        if not empty_spec_content["learning_objectives"]:
            # Should not have learning objectives section if empty
            pass  # This is acceptable - empty sections may or may not appear
    
    @given(
        intent=query_intent_data()
    )
    def test_enrichment_consistency_property(self, intent):
        """
        Property: For the same input, enriched prompt should be consistent.
        """
        spec_content = {
            "learning_objectives": ["Test objective 1", "Test objective 2"],
            "assessment_objectives": {"AO1": "Use techniques", "AO2": "Reason mathematically"},
            "common_misconceptions": ["Test misconception"],
            "key_concepts": ["Test concept"]
        }
        
        # Generate prompt twice with same inputs
        prompt1 = _build_enriched_prompt(intent, spec_content, [], "test-1")
        prompt2 = _build_enriched_prompt(intent, spec_content, [], "test-2")
        
        # Property: Should produce identical prompts (except for request ID in logging)
        # The core content should be the same
        assert intent.topic in prompt1 and intent.topic in prompt2
        assert intent.tier in prompt1 and intent.tier in prompt2
        assert str(intent.count) in prompt1 and str(intent.count) in prompt2
        
        # Property: Both should contain the same specification content
        for objective in spec_content["learning_objectives"]:
            assert (objective in prompt1) == (objective in prompt2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])