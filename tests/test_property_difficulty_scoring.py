"""
Property-based test for difficulty scoring completeness.

Tests Property 2: Difficulty Score Completeness from the GCSE Question Generator V2 design document.
Validates Requirements 1.3 - ensuring each generated question includes a valid difficulty score (1-10 scale).
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from hypothesis import given, strategies as st, settings
from datetime import datetime
from typing import Dict, Any, List

from src.services.bedrock_service import BedrockService
from src.lambda_handlers.generate_lambda import _generate_questions


# Test data generators
@st.composite
def generation_requests(draw):
    """Generate valid generation requests for testing difficulty scoring."""
    topic = draw(st.sampled_from(["Number", "Algebra", "Geometry", "Statistics", "Probability", "Ratio"]))
    tier = draw(st.sampled_from(["Foundation", "Higher"]))
    count = draw(st.integers(min_value=1, max_value=10))
    
    return {
        "topic": topic,
        "tier": tier,
        "count": count,
        "specification_version": "latest"
    }


@st.composite
def mock_bedrock_questions(draw):
    """Generate mock Bedrock responses with questions for testing difficulty scoring."""
    count = draw(st.integers(min_value=1, max_value=10))
    tier = draw(st.sampled_from(["Foundation", "Higher"]))
    
    questions = []
    mark_schemes = []
    
    for i in range(count):
        # Generate question with varying complexity
        question_text = draw(st.text(min_size=20, max_size=200, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd', 'Ps', 'Pe', 'Po'))))
        marks = draw(st.integers(min_value=1, max_value=8))
        
        # Sometimes include difficulty score, sometimes don't (to test auto-assignment)
        include_difficulty = draw(st.booleans())
        
        question = {
            "id": f"q{i+1}",
            "question_text": question_text,
            "marks": marks,
            "tier": tier,
            "topic": "Number"
        }
        
        if include_difficulty:
            # Sometimes provide valid difficulty score, sometimes invalid (to test validation)
            if draw(st.booleans()):
                # Valid difficulty score
                if tier == "Foundation":
                    question["difficulty_score"] = draw(st.integers(min_value=1, max_value=5))
                else:
                    question["difficulty_score"] = draw(st.integers(min_value=6, max_value=10))
            else:
                # Invalid difficulty score (to test correction)
                question["difficulty_score"] = draw(st.integers(min_value=-5, max_value=15))
        
        questions.append(question)
        
        mark_schemes.append({
            "question_id": f"q{i+1}",
            "marking_criteria": f"Test criteria for question {i+1}",
            "method_marks": max(1, marks - 1),
            "accuracy_marks": 1
        })
    
    return {
        "questions": questions,
        "mark_scheme": mark_schemes,
        "metadata": {
            "generated_at": datetime.utcnow().isoformat(),
            "model_version": "claude-3-sonnet-20240229",
            "total_marks": sum(q["marks"] for q in questions),
            "specification_version": "latest"
        }
    }


@st.composite
def questions_without_difficulty_scores(draw):
    """Generate questions without difficulty scores to test auto-assignment."""
    count = draw(st.integers(min_value=1, max_value=5))
    tier = draw(st.sampled_from(["Foundation", "Higher"]))
    
    questions = []
    for i in range(count):
        question_text = draw(st.text(min_size=20, max_size=100, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd', 'Ps', 'Pe', 'Po'))))
        marks = draw(st.integers(min_value=1, max_value=6))
        
        questions.append({
            "id": f"q{i+1}",
            "question_text": question_text,
            "marks": marks,
            "tier": tier,
            "topic": "Number"
            # Deliberately omit difficulty_score
        })
    
    return questions, tier


@st.composite
def questions_with_invalid_difficulty_scores(draw):
    """Generate questions with invalid difficulty scores to test validation."""
    count = draw(st.integers(min_value=1, max_value=5))
    tier = draw(st.sampled_from(["Foundation", "Higher"]))
    
    questions = []
    for i in range(count):
        question_text = draw(st.text(min_size=20, max_size=100, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd', 'Ps', 'Pe', 'Po'))))
        marks = draw(st.integers(min_value=1, max_value=6))
        
        # Generate invalid difficulty scores
        invalid_score = draw(st.one_of(
            st.integers(max_value=0),  # Too low
            st.integers(min_value=11),  # Too high
            st.floats(),  # Wrong type
            st.text()  # Wrong type
        ))
        
        questions.append({
            "id": f"q{i+1}",
            "question_text": question_text,
            "marks": marks,
            "tier": tier,
            "topic": "Number",
            "difficulty_score": invalid_score
        })
    
    return questions, tier


class TestDifficultyScoreCompleteness:
    """Property-based tests for difficulty score completeness."""
    
    @given(generation_request=generation_requests(), mock_response=mock_bedrock_questions())
    @settings(max_examples=100)
    def test_property_2_all_generated_questions_have_valid_difficulty_scores(self, generation_request, mock_response):
        """
        Feature: gcse-question-generator-v2, Property 2: Difficulty Score Completeness
        
        For any generated question, it should include a valid difficulty score between 1 and 10.
        
        **Validates: Requirements 1.3**
        """
        # Arrange
        bedrock_service = BedrockService()
        
        with patch.object(bedrock_service, '_call_bedrock_with_retry') as mock_bedrock:
            mock_bedrock.return_value = json.dumps(mock_response)
            
            # Act - Generate questions (let _parse_sonnet_response and _validate_question_quality do their work)
            result = bedrock_service.generate_questions_with_sonnet(
                generation_request=generation_request,
                spec_content={"learning_objectives": ["test"], "specification_content": "test"},
                examples_content=[],
                request_id="test-request"
            )
            
            # Assert - All questions must have valid difficulty scores after processing
            questions = result["questions"]
            assert len(questions) > 0, "Should generate at least one question"
            
            for i, question in enumerate(questions):
                # Each question must have a difficulty_score field (auto-assigned if missing)
                assert "difficulty_score" in question, f"Question {i+1} missing difficulty_score field"
                
                difficulty_score = question["difficulty_score"]
                
                # Difficulty score must be an integer
                assert isinstance(difficulty_score, int), f"Question {i+1} difficulty_score must be integer, got {type(difficulty_score)}"
                
                # Difficulty score must be in valid range (1-10)
                assert 1 <= difficulty_score <= 10, f"Question {i+1} difficulty_score {difficulty_score} not in range 1-10"
                
                # Difficulty score must match tier constraints (corrected by parsing logic)
                tier = question.get("tier", generation_request.get("tier", "Foundation"))
                if tier == "Foundation":
                    assert 1 <= difficulty_score <= 5, f"Foundation question {i+1} difficulty_score {difficulty_score} not in range 1-5"
                elif tier == "Higher":
                    assert 6 <= difficulty_score <= 10, f"Higher question {i+1} difficulty_score {difficulty_score} not in range 6-10"
    
    @given(questions_data=questions_without_difficulty_scores())
    @settings(max_examples=100)
    def test_property_2_auto_assignment_of_missing_difficulty_scores(self, questions_data):
        """
        Feature: gcse-question-generator-v2, Property 2: Difficulty Score Completeness
        
        For any question without a difficulty score, the system should auto-assign a valid 
        difficulty score based on the tier and question characteristics.
        
        **Validates: Requirements 1.3**
        """
        # Arrange
        questions, tier = questions_data
        bedrock_service = BedrockService()
        
        generation_request = {
            "topic": "Number",
            "tier": tier,
            "count": len(questions),
            "specification_version": "latest"
        }
        
        mock_response = {
            "questions": questions,
            "mark_scheme": [
                {
                    "question_id": f"q{i+1}",
                    "marking_criteria": f"Test criteria {i+1}",
                    "method_marks": 1,
                    "accuracy_marks": 1
                }
                for i in range(len(questions))
            ],
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "model_version": "claude-3-sonnet-20240229",
                "total_marks": sum(q["marks"] for q in questions),
                "specification_version": "latest"
            }
        }
        
        with patch.object(bedrock_service, '_call_bedrock_with_retry') as mock_bedrock:
            mock_bedrock.return_value = json.dumps(mock_response)
            
            # Act - Parse response (this should auto-assign difficulty scores)
            result = bedrock_service._parse_sonnet_response(
                json.dumps(mock_response), 
                generation_request, 
                "test-request"
            )
            
            # Assert - All questions should now have valid difficulty scores
            processed_questions = result["questions"]
            
            for i, question in enumerate(processed_questions):
                # Each question must now have a difficulty_score field
                assert "difficulty_score" in question, f"Question {i+1} should have auto-assigned difficulty_score"
                
                difficulty_score = question["difficulty_score"]
                
                # Difficulty score must be valid
                assert isinstance(difficulty_score, int), f"Auto-assigned difficulty_score must be integer"
                assert 1 <= difficulty_score <= 10, f"Auto-assigned difficulty_score {difficulty_score} not in range 1-10"
                
                # Difficulty score must match tier
                if tier == "Foundation":
                    assert 1 <= difficulty_score <= 5, f"Foundation auto-assigned difficulty_score {difficulty_score} not in range 1-5"
                elif tier == "Higher":
                    assert 6 <= difficulty_score <= 10, f"Higher auto-assigned difficulty_score {difficulty_score} not in range 6-10"
    
    @given(questions_data=questions_with_invalid_difficulty_scores())
    @settings(max_examples=100)
    def test_property_2_correction_of_invalid_difficulty_scores(self, questions_data):
        """
        Feature: gcse-question-generator-v2, Property 2: Difficulty Score Completeness
        
        For any question with an invalid difficulty score, the system should correct it 
        to a valid score within the appropriate range for the tier.
        
        **Validates: Requirements 1.3**
        """
        # Arrange
        questions, tier = questions_data
        bedrock_service = BedrockService()
        
        generation_request = {
            "topic": "Number",
            "tier": tier,
            "count": len(questions),
            "specification_version": "latest"
        }
        
        mock_response = {
            "questions": questions,
            "mark_scheme": [
                {
                    "question_id": f"q{i+1}",
                    "marking_criteria": f"Test criteria {i+1}",
                    "method_marks": 1,
                    "accuracy_marks": 1
                }
                for i in range(len(questions))
            ],
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "model_version": "claude-3-sonnet-20240229",
                "total_marks": sum(q["marks"] for q in questions),
                "specification_version": "latest"
            }
        }
        
        with patch.object(bedrock_service, '_call_bedrock_with_retry') as mock_bedrock:
            mock_bedrock.return_value = json.dumps(mock_response)
            
            # Act - Parse response (this should correct invalid difficulty scores)
            result = bedrock_service._parse_sonnet_response(
                json.dumps(mock_response), 
                generation_request, 
                "test-request"
            )
            
            # Assert - All questions should now have valid difficulty scores
            processed_questions = result["questions"]
            
            for i, question in enumerate(processed_questions):
                # Each question must have a corrected difficulty_score field
                assert "difficulty_score" in question, f"Question {i+1} should have corrected difficulty_score"
                
                difficulty_score = question["difficulty_score"]
                
                # Difficulty score must be valid after correction
                assert isinstance(difficulty_score, int), f"Corrected difficulty_score must be integer"
                assert 1 <= difficulty_score <= 10, f"Corrected difficulty_score {difficulty_score} not in range 1-10"
                
                # Difficulty score must match tier after correction
                if tier == "Foundation":
                    assert 1 <= difficulty_score <= 5, f"Foundation corrected difficulty_score {difficulty_score} not in range 1-5"
                elif tier == "Higher":
                    assert 6 <= difficulty_score <= 10, f"Higher corrected difficulty_score {difficulty_score} not in range 6-10"
    
    @given(
        tier=st.sampled_from(["Foundation", "Higher"]),
        question_text=st.text(min_size=10, max_size=100, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd', 'Ps', 'Pe', 'Po'))),
        marks=st.integers(min_value=1, max_value=8)
    )
    @settings(max_examples=100)
    def test_property_2_difficulty_score_assignment_logic(self, tier, question_text, marks):
        """
        Feature: gcse-question-generator-v2, Property 2: Difficulty Score Completeness
        
        For any question characteristics (tier, text, marks), the difficulty score assignment
        logic should produce a valid score within the appropriate tier range.
        
        **Validates: Requirements 1.3**
        """
        # Arrange
        bedrock_service = BedrockService()
        
        question = {
            "question_text": question_text,
            "marks": marks,
            "tier": tier
        }
        
        # Act - Assign difficulty score
        assigned_score = bedrock_service._assign_difficulty_score(question, tier)
        
        # Assert - Assigned score must be valid
        assert isinstance(assigned_score, int), f"Assigned difficulty score must be integer, got {type(assigned_score)}"
        assert 1 <= assigned_score <= 10, f"Assigned difficulty score {assigned_score} not in range 1-10"
        
        # Score must match tier constraints
        if tier == "Foundation":
            assert 1 <= assigned_score <= 5, f"Foundation assigned score {assigned_score} not in range 1-5"
        elif tier == "Higher":
            assert 6 <= assigned_score <= 10, f"Higher assigned score {assigned_score} not in range 6-10"
    
    @given(
        count=st.integers(min_value=1, max_value=20),
        tier=st.sampled_from(["Foundation", "Higher"])
    )
    @settings(max_examples=50)
    def test_property_2_difficulty_score_consistency_across_batch(self, count, tier):
        """
        Feature: gcse-question-generator-v2, Property 2: Difficulty Score Completeness
        
        For any batch of generated questions, all questions should have consistent
        difficulty score validation and assignment regardless of batch size.
        
        **Validates: Requirements 1.3**
        """
        # Arrange
        bedrock_service = BedrockService()
        
        # Create a batch of questions with mixed difficulty score states
        questions = []
        for i in range(count):
            question = {
                "id": f"q{i+1}",
                "question_text": f"Test question {i+1} for batch processing",
                "marks": 2,
                "tier": tier,
                "topic": "Number"
            }
            
            # Randomly include/exclude difficulty scores to test batch processing
            if i % 3 == 0:
                # No difficulty score (should be auto-assigned)
                pass
            elif i % 3 == 1:
                # Valid difficulty score
                if tier == "Foundation":
                    question["difficulty_score"] = 3
                else:
                    question["difficulty_score"] = 8
            else:
                # Invalid difficulty score (should be corrected)
                question["difficulty_score"] = 99
            
            questions.append(question)
        
        generation_request = {
            "topic": "Number",
            "tier": tier,
            "count": count,
            "specification_version": "latest"
        }
        
        mock_response = {
            "questions": questions,
            "mark_scheme": [
                {
                    "question_id": f"q{i+1}",
                    "marking_criteria": f"Test criteria {i+1}",
                    "method_marks": 1,
                    "accuracy_marks": 1
                }
                for i in range(count)
            ],
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "model_version": "claude-3-sonnet-20240229",
                "total_marks": count * 2,
                "specification_version": "latest"
            }
        }
        
        with patch.object(bedrock_service, '_call_bedrock_with_retry') as mock_bedrock:
            mock_bedrock.return_value = json.dumps(mock_response)
            
            # Act - Process the batch
            result = bedrock_service._parse_sonnet_response(
                json.dumps(mock_response), 
                generation_request, 
                "test-request"
            )
            
            # Assert - All questions in batch should have valid difficulty scores
            processed_questions = result["questions"]
            assert len(processed_questions) == count, f"Should process all {count} questions"
            
            for i, question in enumerate(processed_questions):
                # Each question must have a valid difficulty_score
                assert "difficulty_score" in question, f"Batch question {i+1} missing difficulty_score"
                
                difficulty_score = question["difficulty_score"]
                assert isinstance(difficulty_score, int), f"Batch question {i+1} difficulty_score must be integer"
                assert 1 <= difficulty_score <= 10, f"Batch question {i+1} difficulty_score {difficulty_score} not in range 1-10"
                
                # Tier consistency across batch
                if tier == "Foundation":
                    assert 1 <= difficulty_score <= 5, f"Batch Foundation question {i+1} difficulty_score {difficulty_score} not in range 1-5"
                elif tier == "Higher":
                    assert 6 <= difficulty_score <= 10, f"Batch Higher question {i+1} difficulty_score {difficulty_score} not in range 6-10"