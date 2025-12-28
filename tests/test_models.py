"""Unit tests for core data models."""

import pytest
from src.models import QueryIntent, Question, MarkScheme, SpecificationContent


class TestQueryIntent:
    """Test cases for QueryIntent model."""
    
    def test_valid_query_intent_creation(self, sample_query_intent):
        """Test creating a valid QueryIntent."""
        assert sample_query_intent.topic == "Number"
        assert sample_query_intent.subtopic == "Fractions"
        assert sample_query_intent.tier == "Foundation"
        assert sample_query_intent.count == 5
        assert sample_query_intent.confidence == 0.95
        assert sample_query_intent.specification_version == "2024.1"
    
    def test_invalid_tier_raises_error(self):
        """Test that invalid tier raises ValueError."""
        with pytest.raises(ValueError, match="Invalid tier"):
            QueryIntent(
                topic="Number",
                tier="Invalid",
                count=5,
                confidence=0.95
            )
    
    def test_invalid_count_raises_error(self):
        """Test that invalid count raises ValueError."""
        with pytest.raises(ValueError, match="Invalid count"):
            QueryIntent(
                topic="Number",
                tier="Foundation",
                count=0,  # Invalid: too low
                confidence=0.95
            )
        
        with pytest.raises(ValueError, match="Invalid count"):
            QueryIntent(
                topic="Number",
                tier="Foundation",
                count=51,  # Invalid: too high
                confidence=0.95
            )
    
    def test_invalid_confidence_raises_error(self):
        """Test that invalid confidence raises ValueError."""
        with pytest.raises(ValueError, match="Invalid confidence"):
            QueryIntent(
                topic="Number",
                tier="Foundation",
                count=5,
                confidence=1.5  # Invalid: too high
            )


class TestQuestion:
    """Test cases for Question model."""
    
    def test_valid_question_creation(self, sample_question):
        """Test creating a valid Question."""
        assert sample_question.id == "q1"
        assert "Calculate 3/4 + 1/8" in sample_question.question_text
        assert sample_question.marks == 2
        assert sample_question.tier == "Foundation"
        assert sample_question.topic == "Number"
        assert "fractions" in sample_question.mathematical_elements
    
    def test_empty_id_raises_error(self):
        """Test that empty ID raises ValueError."""
        with pytest.raises(ValueError, match="Question ID cannot be empty"):
            Question(
                id="",
                question_text="Test question",
                marks=2,
                tier="Foundation",
                topic="Number"
            )
    
    def test_empty_question_text_raises_error(self):
        """Test that empty question text raises ValueError."""
        with pytest.raises(ValueError, match="Question text cannot be empty"):
            Question(
                id="q1",
                question_text="",
                marks=2,
                tier="Foundation",
                topic="Number"
            )
    
    def test_invalid_marks_raises_error(self):
        """Test that invalid marks raises ValueError."""
        with pytest.raises(ValueError, match="Invalid marks"):
            Question(
                id="q1",
                question_text="Test question",
                marks=0,  # Invalid: must be positive
                tier="Foundation",
                topic="Number"
            )
    
    def test_none_lists_initialized_as_empty(self):
        """Test that None lists are initialized as empty lists."""
        question = Question(
            id="q1",
            question_text="Test question",
            marks=2,
            tier="Foundation",
            topic="Number"
        )
        assert question.mathematical_elements == []
        assert question.difficulty_indicators == []


class TestMarkScheme:
    """Test cases for MarkScheme model."""
    
    def test_valid_mark_scheme_creation(self, sample_mark_scheme):
        """Test creating a valid MarkScheme."""
        assert sample_mark_scheme.question_id == "q1"
        assert "Convert to common denominator" in sample_mark_scheme.marking_criteria
        assert sample_mark_scheme.method_marks == 1
        assert sample_mark_scheme.accuracy_marks == 1
        assert sample_mark_scheme.total_marks == 2
        assert "Adding denominators" in sample_mark_scheme.common_errors
    
    def test_empty_question_id_raises_error(self):
        """Test that empty question ID raises ValueError."""
        with pytest.raises(ValueError, match="Question ID cannot be empty"):
            MarkScheme(
                question_id="",
                marking_criteria="Test criteria",
                method_marks=1,
                accuracy_marks=1,
                total_marks=2
            )
    
    def test_mismatched_total_marks_raises_error(self):
        """Test that mismatched total marks raises ValueError."""
        with pytest.raises(ValueError, match="Total marks.*must equal"):
            MarkScheme(
                question_id="q1",
                marking_criteria="Test criteria",
                method_marks=1,
                accuracy_marks=1,
                total_marks=3  # Should be 2
            )
    
    def test_negative_marks_raise_error(self):
        """Test that negative marks raise ValueError."""
        with pytest.raises(ValueError, match="Invalid method marks"):
            MarkScheme(
                question_id="q1",
                marking_criteria="Test criteria",
                method_marks=-1,
                accuracy_marks=1,
                total_marks=0
            )


class TestSpecificationContent:
    """Test cases for SpecificationContent model."""
    
    def test_valid_specification_content_creation(self, sample_specification_content):
        """Test creating valid SpecificationContent."""
        assert "add and subtract fractions" in sample_specification_content.content
        assert sample_specification_content.topic == "Number"
        assert sample_specification_content.tier == "Foundation"
        assert sample_specification_content.version == "2024.1"
        assert len(sample_specification_content.learning_objectives) == 2
        assert sample_specification_content.marks_range == [1, 4]
    
    def test_empty_content_raises_error(self):
        """Test that empty content raises ValueError."""
        with pytest.raises(ValueError, match="Content cannot be empty"):
            SpecificationContent(
                content="",
                topic="Number",
                tier="Foundation",
                version="2024.1",
                learning_objectives=["Test objective"]
            )
    
    def test_invalid_tier_raises_error(self):
        """Test that invalid tier raises ValueError."""
        with pytest.raises(ValueError, match="Invalid tier"):
            SpecificationContent(
                content="Test content",
                topic="Number",
                tier="Invalid",
                version="2024.1",
                learning_objectives=["Test objective"]
            )
    
    def test_empty_learning_objectives_raises_error(self):
        """Test that empty learning objectives raises ValueError."""
        with pytest.raises(ValueError, match="Learning objectives cannot be empty"):
            SpecificationContent(
                content="Test content",
                topic="Number",
                tier="Foundation",
                version="2024.1",
                learning_objectives=[]
            )
    
    def test_invalid_marks_range_raises_error(self):
        """Test that invalid marks range raises ValueError."""
        with pytest.raises(ValueError, match="Marks range must contain exactly 2 values"):
            SpecificationContent(
                content="Test content",
                topic="Number",
                tier="Foundation",
                version="2024.1",
                learning_objectives=["Test objective"],
                marks_range=[1, 2, 3]  # Too many values
            )
        
        with pytest.raises(ValueError, match="minimum cannot be greater than maximum"):
            SpecificationContent(
                content="Test content",
                topic="Number",
                tier="Foundation",
                version="2024.1",
                learning_objectives=["Test objective"],
                marks_range=[5, 2]  # Min > Max
            )