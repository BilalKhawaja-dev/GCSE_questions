"""
Property-based tests for question validation functionality.

Tests Property 19: Question Validation
For any malformed question produced by GenerateLambda, the system should validate 
and reject it before returning to the user.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from hypothesis.strategies import composite
import json
import re

from src.services.question_validation_service import (
    QuestionValidationService, ValidationSeverity, ValidationResult
)
from src.utils.constants import VALID_TOPICS, VALID_TIERS


# Test data generators
@composite
def valid_question_data(draw):
    """Generate valid question data for testing."""
    topic = draw(st.sampled_from(VALID_TOPICS))
    tier = draw(st.sampled_from(VALID_TIERS))
    
    # Generate tier-appropriate difficulty score
    if tier.lower() == "foundation":
        difficulty_score = draw(st.integers(min_value=1, max_value=5))
    else:  # Higher tier
        difficulty_score = draw(st.integers(min_value=6, max_value=10))
    
    marks = draw(st.integers(min_value=1, max_value=10))
    
    # Generate question text with mathematical content
    question_starters = ["Calculate", "Find", "Work out", "Solve", "Determine"]
    starter = draw(st.sampled_from(question_starters))
    
    # Add some mathematical content
    number = draw(st.integers(min_value=1, max_value=100))
    
    question_text = f"{starter} the value when x = {number}. Show your working."
    
    return {
        "id": f"q_{draw(st.integers(min_value=1, max_value=1000))}",
        "question_text": question_text,
        "marks": marks,
        "difficulty_score": difficulty_score,
        "topic": topic,
        "tier": tier
    }


@composite
def malformed_question_data(draw):
    """Generate malformed question data for testing validation rejection."""
    malformation_type = draw(st.sampled_from([
        "missing_required_field",
        "invalid_difficulty_score",
        "latex_syntax",
        "empty_question_text",
        "invalid_marks",
        "tier_difficulty_mismatch"
    ]))
    
    # Start with a valid question
    question = draw(valid_question_data())
    
    # Apply malformation
    if malformation_type == "missing_required_field":
        field_to_remove = draw(st.sampled_from(["id", "question_text", "marks", "difficulty_score", "topic", "tier"]))
        del question[field_to_remove]
    
    elif malformation_type == "invalid_difficulty_score":
        question["difficulty_score"] = draw(st.one_of(
            st.integers(max_value=0),  # Too low
            st.integers(min_value=11),  # Too high
            st.text(),  # Wrong type
            st.none()  # Null value
        ))
    
    elif malformation_type == "latex_syntax":
        latex_expressions = [
            "\\frac{3}{4}",
            "\\sqrt{16}",
            "x^{2}",
            "\\times",
            "\\div",
            "$x + y = 5$"
        ]
        latex_expr = draw(st.sampled_from(latex_expressions))
        question["question_text"] = f"Calculate {latex_expr} and show your working."
    
    elif malformation_type == "empty_question_text":
        question["question_text"] = draw(st.one_of(
            st.just(""),
            st.just("   "),  # Whitespace only
            st.text(max_size=5)  # Too short
        ))
    
    elif malformation_type == "invalid_marks":
        question["marks"] = draw(st.one_of(
            st.integers(max_value=0),  # Invalid marks
            st.text(),  # Wrong type
            st.none()  # Null value
        ))
    
    elif malformation_type == "tier_difficulty_mismatch":
        # Foundation tier with Higher difficulty or vice versa
        if question["tier"].lower() == "foundation":
            question["difficulty_score"] = draw(st.integers(min_value=6, max_value=10))
        else:
            question["difficulty_score"] = draw(st.integers(min_value=1, max_value=5))
    
    return question, malformation_type


class TestQuestionValidationProperties:
    """Property-based tests for question validation service."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validation_service = QuestionValidationService()
    
    @given(valid_question_data())
    @settings(max_examples=50)
    def test_valid_questions_pass_validation(self, question):
        """
        Feature: gcse-question-generator-v2, Property 19: Question Validation
        For any well-formed question, the validation service should accept it.
        """
        # Act
        result = self.validation_service.validate_question(question)
        
        # Assert
        assert isinstance(result, ValidationResult)
        assert result.is_valid, f"Valid question was rejected: {[issue.message for issue in result.issues]}"
        assert result.confidence_score > 0.5, f"Confidence too low for valid question: {result.confidence_score}"
        assert len([issue for issue in result.issues if issue.severity == ValidationSeverity.CRITICAL]) == 0
    
    @given(malformed_question_data())
    @settings(max_examples=50)
    def test_malformed_questions_fail_validation(self, question_and_type):
        """
        Feature: gcse-question-generator-v2, Property 19: Question Validation
        For any malformed question, the validation service should reject it with appropriate issues.
        """
        question, malformation_type = question_and_type
        
        # Act
        result = self.validation_service.validate_question(question)
        
        # Assert
        assert isinstance(result, ValidationResult)
        
        # Check that malformed questions are handled appropriately
        if malformation_type in ["missing_required_field", "invalid_difficulty_score", 
                               "latex_syntax", "empty_question_text", "invalid_marks"]:
            # These should be rejected (critical issues)
            critical_issues = [issue for issue in result.issues if issue.severity == ValidationSeverity.CRITICAL]
            assert len(critical_issues) > 0, f"Critical malformation not detected: {malformation_type}"
            assert not result.is_valid, f"Malformed question was accepted: {malformation_type}"
        
        elif malformation_type == "tier_difficulty_mismatch":
            # This should generate warnings but might still be valid
            warning_issues = [issue for issue in result.issues if issue.severity == ValidationSeverity.WARNING]
            assert len(warning_issues) > 0, "Tier-difficulty mismatch not detected"
    
    @given(st.lists(valid_question_data(), min_size=1, max_size=10))
    @settings(max_examples=20)
    def test_question_set_validation_preserves_valid_questions(self, questions):
        """
        Feature: gcse-question-generator-v2, Property 19: Question Validation
        For any set of valid questions, the validation service should preserve all of them.
        """
        # Arrange
        question_set = {
            "questions": questions,
            "mark_scheme": [
                {
                    "question_id": q["id"],
                    "marking_criteria": f"Method mark for {q['topic']}",
                    "method_marks": max(1, q["marks"] - 1),
                    "accuracy_marks": 1
                }
                for q in questions
            ],
            "metadata": {"total_marks": sum(q["marks"] for q in questions)}
        }
        
        # Act
        validated_set = self.validation_service.validate_question_set(question_set)
        
        # Assert
        assert len(validated_set["questions"]) == len(questions), "Valid questions were incorrectly filtered out"
        assert validated_set["metadata"]["validation"]["success_rate"] == 1.0
        assert validated_set["metadata"]["validation"]["valid_questions"] == len(questions)
    
    @given(st.lists(malformed_question_data(), min_size=1, max_size=5))
    @settings(max_examples=20)
    def test_question_set_validation_filters_malformed_questions(self, malformed_questions_and_types):
        """
        Feature: gcse-question-generator-v2, Property 19: Question Validation
        For any set containing malformed questions, the validation service should filter them out.
        """
        # Arrange
        questions = [q for q, _ in malformed_questions_and_types]
        malformation_types = [t for _, t in malformed_questions_and_types]
        
        question_set = {
            "questions": questions,
            "mark_scheme": [],
            "metadata": {"total_marks": 0}
        }
        
        # Act
        validated_set = self.validation_service.validate_question_set(question_set)
        
        # Assert
        # Count expected critical malformations
        critical_malformations = [
            t for t in malformation_types 
            if t in ["missing_required_field", "invalid_difficulty_score", 
                    "latex_syntax", "empty_question_text", "invalid_marks"]
        ]
        
        # The number of valid questions should be less than or equal to original
        assert len(validated_set["questions"]) <= len(questions)
        
        # If all malformations are critical, no questions should remain
        if len(critical_malformations) == len(questions):
            assert len(validated_set["questions"]) == 0, "Critical malformations were not filtered out"
        
        # Success rate should reflect filtering
        expected_max_success_rate = 1.0 - (len(critical_malformations) / len(questions))
        assert validated_set["metadata"]["validation"]["success_rate"] <= expected_max_success_rate + 0.1  # Small tolerance
    
    @given(st.text(min_size=10, max_size=200), st.sampled_from(["\\frac{3}{4}", "\\sqrt{16}", "$x^2$", "\\times", "\\div"]))
    @settings(max_examples=30)
    def test_latex_syntax_detection(self, base_text, latex_expr):
        """
        Feature: gcse-question-generator-v2, Property 19: Question Validation
        For any question containing LaTeX syntax, the validation should detect and reject it.
        """
        # Arrange - inject LaTeX syntax into text
        question = {
            "id": "test_q",
            "question_text": f"{base_text} {latex_expr}",
            "marks": 3,
            "difficulty_score": 5,
            "topic": "Number",
            "tier": "Foundation"
        }
        
        # Act
        result = self.validation_service.validate_question(question)
        
        # Assert
        latex_issues = [
            issue for issue in result.issues 
            if "latex" in issue.message.lower() or "mathematical_formatting" in issue.category
        ]
        assert len(latex_issues) > 0, f"LaTeX syntax not detected in: {question['question_text']}"
        assert not result.is_valid, "Question with LaTeX syntax was accepted"
    
    @given(st.integers(min_value=1, max_value=10))
    @settings(max_examples=20)
    def test_difficulty_tier_alignment_validation(self, difficulty_score):
        """
        Feature: gcse-question-generator-v2, Property 19: Question Validation
        For any question, difficulty score should align with tier expectations.
        """
        # Test Foundation tier
        foundation_question = {
            "id": "test_foundation",
            "question_text": "Calculate 2 + 3",
            "marks": 2,
            "difficulty_score": difficulty_score,
            "topic": "Number",
            "tier": "Foundation"
        }
        
        foundation_result = self.validation_service.validate_question(foundation_question)
        
        # Test Higher tier
        higher_question = {
            "id": "test_higher",
            "question_text": "Solve the quadratic equation x² + 5x + 6 = 0",
            "marks": 4,
            "difficulty_score": difficulty_score,
            "topic": "Algebra",
            "tier": "Higher"
        }
        
        higher_result = self.validation_service.validate_question(higher_question)
        
        # Assert alignment expectations
        if difficulty_score > 5:
            # Should warn for Foundation tier
            foundation_warnings = [
                issue for issue in foundation_result.issues 
                if issue.severity == ValidationSeverity.WARNING and "difficulty" in issue.message.lower()
            ]
            assert len(foundation_warnings) > 0, f"High difficulty {difficulty_score} not flagged for Foundation"
        
        if difficulty_score < 6:
            # Should warn for Higher tier
            higher_warnings = [
                issue for issue in higher_result.issues 
                if issue.severity == ValidationSeverity.WARNING and "difficulty" in issue.message.lower()
            ]
            assert len(higher_warnings) > 0, f"Low difficulty {difficulty_score} not flagged for Higher"
    
    @given(st.integers(min_value=-10, max_value=25))
    @settings(max_examples=30)
    def test_marks_validation_range(self, marks_value):
        """
        Feature: gcse-question-generator-v2, Property 19: Question Validation
        For any question, marks should be validated for reasonable range and type.
        """
        # Arrange
        question = {
            "id": "test_marks",
            "question_text": "Calculate the area of a rectangle with length 5cm and width 3cm.",
            "marks": marks_value,
            "difficulty_score": 3,
            "topic": "Geometry",
            "tier": "Foundation"
        }
        
        # Act
        result = self.validation_service.validate_question(question)
        
        # Assert
        if marks_value < 1:
            # Should be critical error
            critical_issues = [
                issue for issue in result.issues 
                if issue.severity == ValidationSeverity.CRITICAL and "marks" in issue.message.lower()
            ]
            assert len(critical_issues) > 0, f"Invalid marks {marks_value} not detected as critical"
            assert not result.is_valid
        
        elif marks_value > 20:
            # Should be warning
            warning_issues = [
                issue for issue in result.issues 
                if issue.severity == ValidationSeverity.WARNING and "marks" in issue.message.lower()
            ]
            assert len(warning_issues) > 0, f"Very high marks {marks_value} not flagged as warning"
        
        else:
            # Should be acceptable
            marks_critical_issues = [
                issue for issue in result.issues 
                if issue.severity == ValidationSeverity.CRITICAL and "marks" in issue.message.lower()
            ]
            assert len(marks_critical_issues) == 0, f"Valid marks {marks_value} incorrectly flagged as critical"


if __name__ == "__main__":
    pytest.main([__file__])