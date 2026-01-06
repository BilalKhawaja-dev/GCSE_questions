"""
Property-based tests for teacher-specific features functionality.

Feature: gcse-question-generator-v2, Property 7: Teacher Feature Completeness
For any generated content, it should include teacher-specific metadata including 
difficulty scores and topic tracking data.
"""

import json
import pytest
from hypothesis import given, strategies as st, assume
from unittest.mock import Mock, patch

from src.lambda_handlers.interpret_lambda import (
    lambda_handler,
    _enhance_assessment_objectives,
    _generate_teacher_guidance,
    _generate_curriculum_links,
    _generate_differentiation_strategies
)
from src.models.query_intent import QueryIntent


# Test data generators
@st.composite
def teacher_query_data(draw):
    """Generate query data for teacher-specific testing."""
    topics = ["Number", "Algebra", "Geometry", "Statistics", "Probability", "Ratio"]
    tiers = ["Foundation", "Higher"]
    
    topic = draw(st.sampled_from(topics))
    tier = draw(st.sampled_from(tiers))
    count = draw(st.integers(min_value=1, max_value=50))
    
    intent = QueryIntent(
        topic=topic,
        tier=tier,
        count=count,
        confidence=0.8,
        subtopic=draw(st.one_of(st.none(), st.text(min_size=3, max_size=20)))
    )
    
    return intent


@st.composite
def assessment_objectives_data(draw):
    """Generate assessment objectives data for testing."""
    return draw(st.one_of(
        # Dictionary format
        st.dictionaries(
            st.sampled_from(["AO1", "AO2", "AO3"]),
            st.text(min_size=10, max_size=100),
            min_size=1,
            max_size=3
        ),
        # List format
        st.lists(
            st.text(min_size=10, max_size=50),
            min_size=1,
            max_size=3
        ),
        # Empty
        st.just([])
    ))


class TestTeacherFeatureCompleteness:
    """Test suite for teacher feature completeness property."""
    
    @patch('src.lambda_handlers.interpret_lambda.authenticate_request')
    @patch('src.lambda_handlers.interpret_lambda.check_rate_limit')
    @patch('src.lambda_handlers.interpret_lambda.bedrock_service')
    @patch('src.lambda_handlers.interpret_lambda.content_service')
    @patch('src.lambda_handlers.interpret_lambda.get_cached_query_response')
    @patch('src.lambda_handlers.interpret_lambda.cache_query_response')
    @given(intent=teacher_query_data())
    def test_teacher_feature_completeness_property(
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
        Feature: gcse-question-generator-v2, Property 7: Teacher Feature Completeness
        For any generated content, it should include teacher-specific metadata including 
        difficulty scores and topic tracking data.
        """
        # Setup mocks
        mock_auth.return_value = (True, "test-client", None)
        mock_rate_limit.return_value = (True, {})
        mock_get_cache.return_value = None  # Force fresh processing
        
        mock_bedrock_service.parse_query_with_haiku.return_value = intent
        mock_content_service.get_specification_content.return_value = {
            "learning_objectives": ["Test objective 1", "Test objective 2"],
            "assessment_objectives": {"AO1": "Use techniques", "AO2": "Reason mathematically"},
            "common_misconceptions": ["Test misconception"],
            "key_concepts": ["Test concept"]
        }
        mock_content_service.get_examples_content.return_value = []
        
        # Create test event
        event = {
            "body": json.dumps({
                "query": f"Generate {intent.count} {intent.tier.lower()} questions on {intent.topic.lower()}",
                "user_id": "test_teacher",
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
        
        # Property: Must contain specification context with teacher features
        assert "specification_context" in response_body
        spec_context = response_body["specification_context"]
        
        # Property: Must contain enhanced assessment objectives
        assert "assessment_objectives" in spec_context
        assessment_objectives = spec_context["assessment_objectives"]
        
        # Property: Assessment objectives must be enhanced with teacher guidance
        if isinstance(assessment_objectives, dict):
            for ao_key, ao_data in assessment_objectives.items():
                if isinstance(ao_data, dict):
                    # Enhanced format should have additional teacher information
                    assert "title" in ao_data or "description" in ao_data
        
        # Property: Must contain teacher guidance
        assert "teacher_guidance" in spec_context
        teacher_guidance = spec_context["teacher_guidance"]
        
        # Property: Teacher guidance must have required sections
        required_guidance_sections = ["lesson_planning", "assessment_guidance", "differentiation", "resources"]
        for section in required_guidance_sections:
            assert section in teacher_guidance, f"Missing teacher guidance section: {section}"
        
        # Property: Lesson planning must contain structured guidance
        lesson_planning = teacher_guidance["lesson_planning"]
        assert "suggested_lesson_structure" in lesson_planning
        assert "prerequisite_knowledge" in lesson_planning
        assert "extension_activities" in lesson_planning
        
        # Property: Assessment guidance must contain practical advice
        assessment_guidance = teacher_guidance["assessment_guidance"]
        assert "formative_assessment" in assessment_guidance
        assert "summative_assessment" in assessment_guidance
        assert "marking_guidance" in assessment_guidance
        assert "feedback_strategies" in assessment_guidance
        
        # Property: Must contain curriculum links
        assert "curriculum_links" in spec_context
        curriculum_links = spec_context["curriculum_links"]
        assert "prior_learning" in curriculum_links
        assert "future_learning" in curriculum_links
        assert "cross_curricular" in curriculum_links
        assert "progression_pathway" in curriculum_links
        
        # Property: Must contain differentiation strategies
        assert "differentiation_strategies" in spec_context
        diff_strategies = spec_context["differentiation_strategies"]
        assert "by_outcome" in diff_strategies
        assert "by_support" in diff_strategies
        assert "by_task" in diff_strategies
        
        # Property: Difficulty guidance must include teacher-specific information
        assert "difficulty_guidance" in response_body
        difficulty_guidance = response_body["difficulty_guidance"]
        assert "grade_mapping" in difficulty_guidance
        assert "recommended_marks_range" in difficulty_guidance
        
        # Property: Topic coverage must be present for user tracking
        assert "topic_coverage" in response_body
        topic_coverage = response_body["topic_coverage"]
        assert "current_topic" in topic_coverage
        assert "suggested_topics" in topic_coverage
    
    @given(assessment_objectives=assessment_objectives_data())
    def test_enhance_assessment_objectives_property(self, assessment_objectives):
        """
        Test the assessment objectives enhancement function.
        """
        enhanced_aos = _enhance_assessment_objectives(assessment_objectives)
        
        # Property: Must return a dictionary
        assert isinstance(enhanced_aos, dict)
        
        # Property: Must contain standard AO1, AO2, AO3 structure
        standard_aos = ["AO1", "AO2", "AO3"]
        for ao in standard_aos:
            assert ao in enhanced_aos, f"Missing standard assessment objective: {ao}"
        
        # Property: Each AO must have required teacher guidance fields
        for ao_key, ao_data in enhanced_aos.items():
            assert isinstance(ao_data, dict)
            required_fields = ["title", "description", "weight", "teacher_guidance", "question_types"]
            for field in required_fields:
                assert field in ao_data, f"Missing field {field} in {ao_key}"
            
            # Property: Teacher guidance must be non-empty string
            assert isinstance(ao_data["teacher_guidance"], str)
            assert len(ao_data["teacher_guidance"]) > 0
            
            # Property: Question types must be a list
            assert isinstance(ao_data["question_types"], list)
            assert len(ao_data["question_types"]) > 0
    
    @given(intent=teacher_query_data())
    def test_generate_teacher_guidance_property(self, intent):
        """
        Test the teacher guidance generation function.
        """
        spec_content = {
            "learning_objectives": ["Test objective"],
            "common_misconceptions": ["Test misconception"]
        }
        
        teacher_guidance = _generate_teacher_guidance(intent, spec_content, "test-request-123")
        
        # Property: Must return a dictionary with required sections
        assert isinstance(teacher_guidance, dict)
        required_sections = ["lesson_planning", "assessment_guidance", "differentiation", "resources"]
        for section in required_sections:
            assert section in teacher_guidance, f"Missing section: {section}"
        
        # Property: Each section must contain appropriate subsections
        lesson_planning = teacher_guidance["lesson_planning"]
        assert "suggested_lesson_structure" in lesson_planning
        assert "prerequisite_knowledge" in lesson_planning
        assert "extension_activities" in lesson_planning
        
        # Property: Lesson structure must be appropriate for tier
        lesson_structure = lesson_planning["suggested_lesson_structure"]
        assert isinstance(lesson_structure, list)
        assert len(lesson_structure) > 0
        
        if intent.tier == "Foundation":
            # Foundation should emphasize scaffolding
            structure_text = " ".join(lesson_structure).lower()
            assert "scaffolding" in structure_text or "guided" in structure_text
        else:
            # Higher should emphasize investigation
            structure_text = " ".join(lesson_structure).lower()
            assert "investigation" in structure_text or "independent" in structure_text
        
        # Property: Resources section must contain practical suggestions
        resources = teacher_guidance["resources"]
        assert "recommended_manipulatives" in resources
        assert "technology_integration" in resources
        assert "real_world_connections" in resources
        
        # Property: All resource lists must be non-empty
        for resource_type, resource_list in resources.items():
            assert isinstance(resource_list, list)
            assert len(resource_list) > 0
    
    @given(
        topic=st.sampled_from(["Number", "Algebra", "Geometry", "Statistics", "Probability", "Ratio"]),
        tier=st.sampled_from(["Foundation", "Higher"])
    )
    def test_generate_curriculum_links_property(self, topic, tier):
        """
        Test the curriculum links generation function.
        """
        curriculum_links = _generate_curriculum_links(topic, tier)
        
        # Property: Must return a dictionary with required sections
        assert isinstance(curriculum_links, dict)
        required_sections = ["prior_learning", "future_learning", "cross_curricular", "progression_pathway"]
        for section in required_sections:
            assert section in curriculum_links, f"Missing section: {section}"
        
        # Property: Prior and future learning must be lists
        assert isinstance(curriculum_links["prior_learning"], list)
        assert isinstance(curriculum_links["future_learning"], list)
        assert isinstance(curriculum_links["cross_curricular"], list)
        
        # Property: All lists must be non-empty
        for section in ["prior_learning", "future_learning", "cross_curricular"]:
            assert len(curriculum_links[section]) > 0, f"Empty section: {section}"
        
        # Property: Progression pathway must be a dictionary
        progression = curriculum_links["progression_pathway"]
        assert isinstance(progression, dict)
        assert "current_level" in progression
        assert "next_steps" in progression
        assert "long_term" in progression
        
        # Property: Current level should mention the topic and tier
        current_level = progression["current_level"].lower()
        assert topic.lower() in current_level
        assert tier.lower() in current_level
    
    @given(
        tier=st.sampled_from(["Foundation", "Higher"]),
        count=st.integers(min_value=1, max_value=100)
    )
    def test_generate_differentiation_strategies_property(self, tier, count):
        """
        Test the differentiation strategies generation function.
        """
        strategies = _generate_differentiation_strategies(tier, count)
        
        # Property: Must return a dictionary with required sections
        assert isinstance(strategies, dict)
        required_sections = ["by_outcome", "by_support", "by_task"]
        for section in required_sections:
            assert section in strategies, f"Missing section: {section}"
        
        # Property: Each section must contain appropriate guidance
        by_outcome = strategies["by_outcome"]
        assert "all_students" in by_outcome
        assert "most_students" in by_outcome
        assert "some_students" in by_outcome
        
        by_support = strategies["by_support"]
        assert "high_support" in by_support
        assert "medium_support" in by_support
        assert "low_support" in by_support
        
        by_task = strategies["by_task"]
        assert "foundation_focus" in by_task
        assert "core_focus" in by_task
        assert "extension_focus" in by_task
        
        # Property: All guidance must be non-empty strings
        for section_name, section_data in strategies.items():
            if isinstance(section_data, dict):
                for key, value in section_data.items():
                    if isinstance(value, str):
                        assert len(value) > 0, f"Empty guidance in {section_name}.{key}"
        
        # Property: Large question counts should have grouping suggestions
        if count > 20:
            assert "grouping" in strategies
            assert "suggestion" in strategies["grouping"]
            assert "rationale" in strategies["grouping"]
    
    @given(intent=teacher_query_data())
    def test_teacher_features_consistency_property(self, intent):
        """
        Property: For the same input, teacher features should be consistent.
        """
        spec_content = {
            "learning_objectives": ["Test objective"],
            "assessment_objectives": {"AO1": "Use techniques"},
            "common_misconceptions": ["Test misconception"],
            "key_concepts": ["Test concept"]
        }
        
        # Generate teacher guidance twice with same inputs
        guidance1 = _generate_teacher_guidance(intent, spec_content, "test-1")
        guidance2 = _generate_teacher_guidance(intent, spec_content, "test-2")
        
        # Property: Core structure should be identical
        assert guidance1.keys() == guidance2.keys()
        
        # Property: Lesson planning should be consistent for same tier
        lesson1 = guidance1["lesson_planning"]["suggested_lesson_structure"]
        lesson2 = guidance2["lesson_planning"]["suggested_lesson_structure"]
        assert lesson1 == lesson2, "Lesson structure should be consistent for same tier"
        
        # Property: Resources should be consistent for same topic
        resources1 = guidance1["resources"]["recommended_manipulatives"]
        resources2 = guidance2["resources"]["recommended_manipulatives"]
        assert resources1 == resources2, "Recommended manipulatives should be consistent for same topic"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])