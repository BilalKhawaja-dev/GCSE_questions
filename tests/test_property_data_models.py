"""Property-based tests for data model validation.

Feature: gcse-question-generator, Property 1: Query Parsing Completeness
Validates: Requirements 1.1, 1.2, 1.3, 1.4
"""

import pytest
from hypothesis import given, strategies as st, assume
from src.models import QueryIntent, Question, MarkScheme, SpecificationContent
from src.utils.constants import VALID_TOPICS, VALID_TIERS


# Hypothesis strategies for generating test data
@st.composite
def valid_query_intent_strategy(draw):
    """Generate valid QueryIntent instances."""
    topic = draw(st.sampled_from(VALID_TOPICS))
    tier = draw(st.sampled_from(VALID_TIERS))
    count = draw(st.integers(min_value=1, max_value=50))
    confidence = draw(st.floats(min_value=0.0, max_value=1.0))
    subtopic = draw(st.one_of(st.none(), st.text(min_size=1, max_size=50)))
    marks = draw(st.one_of(st.none(), st.integers(min_value=1, max_value=100)))
    version = draw(st.text(min_size=1, max_size=20))
    
    return QueryIntent(
        topic=topic,
        tier=tier,
        count=count,
        confidence=confidence,
        subtopic=subtopic,
        marks=marks,
        specification_version=version
    )


@st.composite
def valid_question_strategy(draw):
    """Generate valid Question instances."""
    id_str = draw(st.text(min_size=1, max_size=20))
    question_text = draw(st.text(min_size=1, max_size=500))
    marks = draw(st.integers(min_value=1, max_value=20))
    tier = draw(st.sampled_from(VALID_TIERS))
    topic = draw(st.sampled_from(VALID_TOPICS))
    subtopic = draw(st.one_of(st.none(), st.text(min_size=1, max_size=50)))
    math_elements = draw(st.one_of(st.none(), st.lists(st.text(min_size=1, max_size=20), max_size=5)))
    difficulty_indicators = draw(st.one_of(st.none(), st.lists(st.text(min_size=1, max_size=20), max_size=5)))
    
    return Question(
        id=id_str,
        question_text=question_text,
        marks=marks,
        tier=tier,
        topic=topic,
        subtopic=subtopic,
        mathematical_elements=math_elements,
        difficulty_indicators=difficulty_indicators
    )


@st.composite
def valid_mark_scheme_strategy(draw):
    """Generate valid MarkScheme instances."""
    question_id = draw(st.text(min_size=1, max_size=20))
    marking_criteria = draw(st.text(min_size=1, max_size=500))
    method_marks = draw(st.integers(min_value=0, max_value=10))
    accuracy_marks = draw(st.integers(min_value=0, max_value=10))
    # Ensure at least one mark is awarded
    assume(method_marks + accuracy_marks > 0)
    total_marks = method_marks + accuracy_marks
    common_errors = draw(st.one_of(st.none(), st.lists(st.text(min_size=1, max_size=100), max_size=5)))
    
    return MarkScheme(
        question_id=question_id,
        marking_criteria=marking_criteria,
        method_marks=method_marks,
        accuracy_marks=accuracy_marks,
        total_marks=total_marks,
        common_errors=common_errors
    )


@st.composite
def valid_specification_content_strategy(draw):
    """Generate valid SpecificationContent instances."""
    content = draw(st.text(min_size=1, max_size=1000))
    topic = draw(st.sampled_from(VALID_TOPICS))
    tier = draw(st.sampled_from(["Foundation", "Higher", "both"]))
    version = draw(st.text(min_size=1, max_size=20))
    learning_objectives = draw(st.lists(st.text(min_size=1, max_size=100), min_size=1, max_size=10))
    domain = draw(st.one_of(st.none(), st.text(min_size=1, max_size=50)))
    subtopic = draw(st.one_of(st.none(), st.text(min_size=1, max_size=50)))
    key_concepts = draw(st.one_of(st.none(), st.lists(st.text(min_size=1, max_size=50), max_size=10)))
    misconceptions = draw(st.one_of(st.none(), st.lists(st.text(min_size=1, max_size=100), max_size=5)))
    assessment_objectives = draw(st.one_of(st.none(), st.lists(st.text(min_size=1, max_size=10), max_size=5)))
    
    # Generate valid marks range
    marks_range = draw(st.one_of(
        st.none(),
        st.lists(st.integers(min_value=1, max_value=20), min_size=2, max_size=2).map(
            lambda x: [min(x), max(x)]  # Ensure min <= max
        )
    ))
    
    return SpecificationContent(
        content=content,
        topic=topic,
        tier=tier,
        version=version,
        learning_objectives=learning_objectives,
        domain=domain,
        subtopic=subtopic,
        key_concepts=key_concepts,
        common_misconceptions=misconceptions,
        assessment_objectives=assessment_objectives,
        marks_range=marks_range
    )


class TestPropertyDataModels:
    """Property-based tests for data model validation."""
    
    @given(query_intent=valid_query_intent_strategy())
    def test_query_intent_validation_completeness(self, query_intent):
        """Feature: gcse-question-generator, Property 1: Query Parsing Completeness
        
        For any valid QueryIntent with topic, tier, and count information,
        the model should maintain all components with correct validation.
        
        Validates: Requirements 1.1, 1.2, 1.3, 1.4
        """
        # Verify all required fields are present and valid
        assert query_intent.topic in VALID_TOPICS
        assert query_intent.tier in VALID_TIERS
        assert 1 <= query_intent.count <= 50
        assert 0.0 <= query_intent.confidence <= 1.0
        
        # Verify optional fields are handled correctly
        if query_intent.subtopic is not None:
            assert isinstance(query_intent.subtopic, str)
            assert len(query_intent.subtopic) > 0
        
        if query_intent.marks is not None:
            assert query_intent.marks > 0
        
        assert isinstance(query_intent.specification_version, str)
        assert len(query_intent.specification_version) > 0
    
    @given(question=valid_question_strategy())
    def test_question_model_completeness(self, question):
        """For any valid Question, all required fields should be properly validated
        and optional fields should be initialized correctly."""
        
        # Verify required fields
        assert isinstance(question.id, str) and len(question.id) > 0
        assert isinstance(question.question_text, str) and len(question.question_text) > 0
        assert question.marks > 0
        assert question.tier in VALID_TIERS
        assert question.topic in VALID_TOPICS
        
        # Verify optional fields are properly initialized
        assert isinstance(question.mathematical_elements, list)
        assert isinstance(question.difficulty_indicators, list)
        
        if question.subtopic is not None:
            assert isinstance(question.subtopic, str)
            assert len(question.subtopic) > 0
    
    @given(mark_scheme=valid_mark_scheme_strategy())
    def test_mark_scheme_consistency(self, mark_scheme):
        """For any valid MarkScheme, the total marks should equal 
        method marks plus accuracy marks."""
        
        # Verify required fields
        assert isinstance(mark_scheme.question_id, str) and len(mark_scheme.question_id) > 0
        assert isinstance(mark_scheme.marking_criteria, str) and len(mark_scheme.marking_criteria) > 0
        assert mark_scheme.method_marks >= 0
        assert mark_scheme.accuracy_marks >= 0
        assert mark_scheme.total_marks > 0
        
        # Verify marks consistency (key property)
        assert mark_scheme.total_marks == (mark_scheme.method_marks + mark_scheme.accuracy_marks)
        
        # Verify optional fields are properly initialized
        assert isinstance(mark_scheme.common_errors, list)
    
    @given(spec_content=valid_specification_content_strategy())
    def test_specification_content_structure(self, spec_content):
        """For any valid SpecificationContent, all required fields should be present
        and marks range should be properly ordered."""
        
        # Verify required fields
        assert isinstance(spec_content.content, str) and len(spec_content.content) > 0
        assert spec_content.topic in VALID_TOPICS
        assert spec_content.tier in ["Foundation", "Higher", "both"]
        assert isinstance(spec_content.version, str) and len(spec_content.version) > 0
        assert isinstance(spec_content.learning_objectives, list)
        assert len(spec_content.learning_objectives) > 0
        
        # Verify optional fields are properly initialized
        assert isinstance(spec_content.key_concepts, list)
        assert isinstance(spec_content.common_misconceptions, list)
        assert isinstance(spec_content.assessment_objectives, list)
        
        # Verify marks range consistency if present
        if spec_content.marks_range is not None:
            assert len(spec_content.marks_range) == 2
            assert spec_content.marks_range[0] <= spec_content.marks_range[1]
            assert all(mark > 0 for mark in spec_content.marks_range)
    
    @given(
        topic=st.sampled_from(VALID_TOPICS),
        tier=st.sampled_from(VALID_TIERS),
        count=st.integers(min_value=1, max_value=50),
        confidence=st.floats(min_value=0.0, max_value=1.0)
    )
    def test_query_intent_boundary_values(self, topic, tier, count, confidence):
        """For any combination of valid boundary values, QueryIntent should be created successfully."""
        
        query_intent = QueryIntent(
            topic=topic,
            tier=tier,
            count=count,
            confidence=confidence
        )
        
        assert query_intent.topic == topic
        assert query_intent.tier == tier
        assert query_intent.count == count
        assert query_intent.confidence == confidence
        assert query_intent.specification_version == "latest"  # Default value
    
    @given(
        invalid_tier=st.text().filter(lambda x: x not in VALID_TIERS),
        count=st.integers(min_value=1, max_value=50),
        confidence=st.floats(min_value=0.0, max_value=1.0)
    )
    def test_query_intent_invalid_tier_rejection(self, invalid_tier, count, confidence):
        """For any invalid tier value, QueryIntent creation should raise ValueError."""
        
        with pytest.raises(ValueError, match="Invalid tier"):
            QueryIntent(
                topic="Number",
                tier=invalid_tier,
                count=count,
                confidence=confidence
            )
    
    @given(
        invalid_count=st.one_of(
            st.integers(max_value=0),  # Too low
            st.integers(min_value=51)  # Too high
        ),
        confidence=st.floats(min_value=0.0, max_value=1.0)
    )
    def test_query_intent_invalid_count_rejection(self, invalid_count, confidence):
        """For any invalid count value, QueryIntent creation should raise ValueError."""
        
        with pytest.raises(ValueError, match="Invalid count"):
            QueryIntent(
                topic="Number",
                tier="Foundation",
                count=invalid_count,
                confidence=confidence
            )