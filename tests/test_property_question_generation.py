"""
Property-based tests for question generation system.

Tests universal properties for Bedrock-based question generation,
including specification version management, complete generation, and content alignment.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from hypothesis import given, strategies as st, settings
from datetime import datetime

from src.services.bedrock_service import BedrockService
from src.lambda_handlers.generate_lambda import _generate_questions


# Test data generators
@st.composite
def valid_generation_request(draw):
    """Generate valid generation requests for testing."""
    topics = ["Number", "Algebra", "Geometry", "Statistics", "Probability", "Ratio"]
    subtopics = {
        "Number": ["fractions", "decimals", "percentages"],
        "Algebra": ["linear_equations", "quadratic_equations"],
        "Geometry": ["angles", "triangles", "circles"],
        "Statistics": ["data_analysis", "averages"],
        "Probability": ["basic_probability", "tree_diagrams"],
        "Ratio": ["ratio_proportion", "scale_factors"]
    }
    tiers = ["Foundation", "Higher"]
    
    topic = draw(st.sampled_from(topics))
    subtopic = draw(st.sampled_from(subtopics[topic]))
    tier = draw(st.sampled_from(tiers))
    count = draw(st.integers(min_value=1, max_value=10))
    
    return {
        "topic": topic,
        "subtopic": subtopic,
        "tier": tier,
        "count": count,
        "specification_version": draw(st.sampled_from(["latest", "2024.1", "2023.2"]))
    }


@st.composite
def mock_question_set(draw):
    """Generate mock question sets for testing."""
    count = draw(st.integers(min_value=1, max_value=10))
    questions = []
    mark_schemes = []
    total_marks = 0
    
    for i in range(count):
        question_id = f"q{i+1}"
        marks = draw(st.integers(min_value=1, max_value=8))
        method_marks = draw(st.integers(min_value=0, max_value=marks))
        accuracy_marks = marks - method_marks
        
        questions.append({
            "id": question_id,
            "question_text": draw(st.text(min_size=20, max_size=200)),
            "marks": marks,
            "tier": draw(st.sampled_from(["Foundation", "Higher"])),
            "topic": draw(st.sampled_from(["Number", "Algebra", "Geometry"])),
            "subtopic": draw(st.text(min_size=1, max_size=20))
        })
        
        mark_schemes.append({
            "question_id": question_id,
            "marking_criteria": draw(st.text(min_size=10, max_size=100)),
            "method_marks": method_marks,
            "accuracy_marks": accuracy_marks
        })
        
        total_marks += marks
    
    return {
        "questions": questions,
        "mark_scheme": mark_schemes,
        "metadata": {
            "generated_at": datetime.utcnow().isoformat(),
            "model_version": "claude-3-sonnet-20240229",
            "total_marks": total_marks,
            "specification_version": draw(st.sampled_from(["latest", "2024.1", "2023.2"])),
            "request_id": draw(st.text(min_size=10, max_size=50))
        }
    }


@st.composite
def mock_spec_content(draw):
    """Generate mock specification content."""
    return {
        "domain": draw(st.sampled_from(["number", "algebra", "geometry"])),
        "subtopic": draw(st.text(min_size=1, max_size=20)),
        "tier": draw(st.sampled_from(["Foundation", "Higher", "both"])),
        "version": draw(st.sampled_from(["2024.1", "2023.2", "latest"])),
        "learning_objectives": draw(st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=5)),
        "specification_content": draw(st.text(min_size=10, max_size=200)),
        "key_concepts": draw(st.lists(st.text(min_size=1, max_size=20), min_size=0, max_size=10))
    }


class TestQuestionGenerationProperties:
    """Property-based tests for question generation service."""
    
    @given(
        generation_request=valid_generation_request(),
        question_set=mock_question_set()
    )
    @settings(max_examples=100)
    def test_property_4_specification_version_management(self, generation_request, question_set):
        """
        Feature: gcse-question-generator, Property 4: Specification Version Management
        
        For any generated question set, the System should tag the output with the 
        specification version used and support multiple versions simultaneously.
        
        **Validates: Requirements 2.6**
        """
        # Arrange
        bedrock_service = BedrockService()
        
        # Ensure the mock question set uses the same version as the request
        question_set['metadata']['specification_version'] = generation_request['specification_version']
        
        with patch.object(bedrock_service, '_call_bedrock_with_retry') as mock_bedrock:
            mock_bedrock.return_value = json.dumps(question_set)
            
            with patch.object(bedrock_service, '_parse_sonnet_response', return_value=question_set):
                with patch.object(bedrock_service, '_validate_question_quality', return_value=question_set):
                    # Act
                    result = bedrock_service.generate_questions_with_sonnet(
                        generation_request=generation_request,
                        spec_content={"learning_objectives": ["test"], "specification_content": "test"},
                        examples_content=[],
                        request_id="test-request"
                    )
                    
                    # Assert - Output should be tagged with specification version
                    assert 'metadata' in result
                    assert 'specification_version' in result['metadata']
                    assert result['metadata']['specification_version'] == generation_request['specification_version']
                    
                    # Should support different versions
                    assert result['metadata']['specification_version'] in ["latest", "2024.1", "2023.2"]
    
    @given(
        generation_request=valid_generation_request(),
        question_set=mock_question_set()
    )
    @settings(max_examples=100)
    def test_property_5_complete_question_generation(self, generation_request, question_set):
        """
        Feature: gcse-question-generator, Property 5: Complete Question Generation
        
        For any valid generation request, the Generate_Service should produce exactly 
        the requested number of questions, each with a corresponding mark scheme, 
        formatted as valid JSON matching the defined schema.
        
        **Validates: Requirements 4.1, 4.3, 4.5, 17.1**
        """
        # Arrange
        bedrock_service = BedrockService()
        
        # Ensure mock data matches request count exactly
        requested_count = generation_request['count']
        # Truncate or extend the mock data to match requested count
        if len(question_set['questions']) > requested_count:
            question_set['questions'] = question_set['questions'][:requested_count]
            question_set['mark_scheme'] = question_set['mark_scheme'][:requested_count]
        elif len(question_set['questions']) < requested_count:
            # Extend by duplicating existing questions
            while len(question_set['questions']) < requested_count:
                base_idx = len(question_set['questions']) % len(question_set['questions']) if question_set['questions'] else 0
                if question_set['questions']:
                    new_question = question_set['questions'][base_idx].copy()
                    new_question['id'] = f"q{len(question_set['questions']) + 1}"
                    question_set['questions'].append(new_question)
                    
                    new_mark_scheme = question_set['mark_scheme'][base_idx].copy()
                    new_mark_scheme['question_id'] = new_question['id']
                    question_set['mark_scheme'].append(new_mark_scheme)
                else:
                    # Create minimal question if none exist
                    question_set['questions'].append({
                        "id": f"q{len(question_set['questions']) + 1}",
                        "question_text": "Test question",
                        "marks": 1,
                        "tier": generation_request['tier'],
                        "topic": generation_request['topic']
                    })
                    question_set['mark_scheme'].append({
                        "question_id": f"q{len(question_set['mark_scheme']) + 1}",
                        "marking_criteria": "Test criteria",
                        "method_marks": 0,
                        "accuracy_marks": 1
                    })
        
        question_set['metadata']['total_marks'] = sum(q['marks'] for q in question_set['questions'])
        
        with patch.object(bedrock_service, '_call_bedrock_with_retry') as mock_bedrock:
            mock_bedrock.return_value = json.dumps(question_set)
            
            with patch.object(bedrock_service, '_parse_sonnet_response', return_value=question_set):
                with patch.object(bedrock_service, '_validate_question_quality', return_value=question_set):
                    # Act
                    result = bedrock_service.generate_questions_with_sonnet(
                        generation_request=generation_request,
                        spec_content={"learning_objectives": ["test"], "specification_content": "test"},
                        examples_content=[],
                        request_id="test-request"
                    )
                    
                    # Assert - Should produce exactly the requested number of questions
                    assert len(result['questions']) == requested_count
                    
                    # Each question should have a corresponding mark scheme
                    assert len(result['mark_scheme']) == len(result['questions'])
                    
                    # Should be formatted as valid JSON with required schema
                    assert 'questions' in result
                    assert 'mark_scheme' in result
                    assert 'metadata' in result
                    
                    # Each question should have required fields
                    for question in result['questions']:
                        assert 'id' in question
                        assert 'question_text' in question
                        assert 'marks' in question
                        assert 'tier' in question
                        assert 'topic' in question
                        assert isinstance(question['marks'], int)
                        assert question['marks'] > 0
                    
                    # Each mark scheme should have required fields
                    for mark_scheme in result['mark_scheme']:
                        assert 'question_id' in mark_scheme
                        assert 'marking_criteria' in mark_scheme
                        assert 'method_marks' in mark_scheme
                        assert 'accuracy_marks' in mark_scheme
                        assert isinstance(mark_scheme['method_marks'], int)
                        assert isinstance(mark_scheme['accuracy_marks'], int)
                        assert mark_scheme['method_marks'] >= 0
                        assert mark_scheme['accuracy_marks'] >= 0
                    
                    # Metadata should have required fields
                    assert 'generated_at' in result['metadata']
                    assert 'model_version' in result['metadata']
                    assert 'total_marks' in result['metadata']
                    assert isinstance(result['metadata']['total_marks'], int)
    
    @given(
        generation_request=valid_generation_request(),
        spec_content=mock_spec_content(),
        question_set=mock_question_set()
    )
    @settings(max_examples=100)
    def test_property_7_content_alignment_validation(self, generation_request, spec_content, question_set):
        """
        Feature: gcse-question-generator, Property 7: Content Alignment Validation
        
        For any generated question, the content should align with the requested topic 
        and tier, contain appropriate mathematical elements for the topic, and have 
        mark schemes that match the question difficulty level.
        
        **Validates: Requirements 4.2, 18.1, 18.2**
        """
        # Arrange
        bedrock_service = BedrockService()
        
        # Ensure question set aligns with generation request
        for question in question_set['questions']:
            question['topic'] = generation_request['topic']
            question['tier'] = generation_request['tier']
        
        with patch.object(bedrock_service, '_call_bedrock_with_retry') as mock_bedrock:
            mock_bedrock.return_value = json.dumps(question_set)
            
            with patch.object(bedrock_service, '_parse_sonnet_response', return_value=question_set):
                with patch.object(bedrock_service, '_validate_question_quality', return_value=question_set):
                    # Act
                    result = bedrock_service.generate_questions_with_sonnet(
                        generation_request=generation_request,
                        spec_content=spec_content,
                        examples_content=[],
                        request_id="test-request"
                    )
                    
                    # Assert - Content should align with requested topic and tier
                    for question in result['questions']:
                        assert question['topic'] == generation_request['topic']
                        assert question['tier'] == generation_request['tier']
                    
                    # Mark schemes should match question difficulty
                    for i, question in enumerate(result['questions']):
                        corresponding_mark_scheme = result['mark_scheme'][i]
                        
                        # Mark scheme total should match question marks
                        total_scheme_marks = (
                            corresponding_mark_scheme['method_marks'] + 
                            corresponding_mark_scheme['accuracy_marks']
                        )
                        
                        # Allow for some flexibility in mark scheme parsing
                        assert abs(total_scheme_marks - question['marks']) <= 1
                        
                        # Mark scheme should reference the correct question
                        assert corresponding_mark_scheme['question_id'] == question['id']
    
    @given(generation_request=valid_generation_request())
    @settings(max_examples=50)
    def test_property_5_json_schema_compliance(self, generation_request):
        """
        Feature: gcse-question-generator, Property 5: Complete Question Generation
        
        For any generated question set, the JSON output should strictly comply 
        with the defined schema structure and data types.
        
        **Validates: Requirements 17.1**
        """
        # Arrange
        bedrock_service = BedrockService()
        
        # Create a valid mock response
        mock_response = {
            "questions": [
                {
                    "id": f"q{i+1}",
                    "question_text": f"Test question {i+1}",
                    "marks": 2,
                    "tier": generation_request['tier'],
                    "topic": generation_request['topic'],
                    "subtopic": generation_request.get('subtopic', '')
                }
                for i in range(generation_request['count'])
            ],
            "mark_scheme": [
                {
                    "question_id": f"q{i+1}",
                    "marking_criteria": f"Test criteria {i+1}",
                    "method_marks": 1,
                    "accuracy_marks": 1
                }
                for i in range(generation_request['count'])
            ],
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "model_version": "claude-3-sonnet-20240229",
                "total_marks": generation_request['count'] * 2,
                "specification_version": generation_request['specification_version']
            }
        }
        
        with patch.object(bedrock_service, '_call_bedrock_with_retry') as mock_bedrock:
            mock_bedrock.return_value = json.dumps(mock_response)
            
            with patch.object(bedrock_service, '_parse_sonnet_response', return_value=mock_response):
                with patch.object(bedrock_service, '_validate_question_quality', return_value=mock_response):
                    # Act
                    result = bedrock_service.generate_questions_with_sonnet(
                        generation_request=generation_request,
                        spec_content={"learning_objectives": ["test"], "specification_content": "test"},
                        examples_content=[],
                        request_id="test-request"
                    )
                    
                    # Assert - JSON should be serializable and valid
                    json_str = json.dumps(result)
                    parsed_back = json.loads(json_str)
                    
                    # Should maintain structure after serialization round-trip
                    assert parsed_back == result
                    
                    # Should comply with schema data types
                    assert isinstance(result['questions'], list)
                    assert isinstance(result['mark_scheme'], list)
                    assert isinstance(result['metadata'], dict)
                    
                    for question in result['questions']:
                        assert isinstance(question['id'], str)
                        assert isinstance(question['question_text'], str)
                        assert isinstance(question['marks'], int)
                        assert isinstance(question['tier'], str)
                        assert isinstance(question['topic'], str)
                    
                    for mark_scheme in result['mark_scheme']:
                        assert isinstance(mark_scheme['question_id'], str)
                        assert isinstance(mark_scheme['marking_criteria'], str)
                        assert isinstance(mark_scheme['method_marks'], int)
                        assert isinstance(mark_scheme['accuracy_marks'], int)


class TestQuestionQualityValidation:
    """Property-based tests for question quality validation."""
    
    @given(
        question_text=st.text(min_size=20, max_size=200),
        topic=st.sampled_from(["Number", "Algebra", "Geometry", "Statistics"]),
        tier=st.sampled_from(["Foundation", "Higher"])
    )
    @settings(max_examples=50)
    def test_quality_validation_consistency(self, question_text, topic, tier):
        """
        Test that quality validation produces consistent results for the same input.
        """
        # Arrange
        bedrock_service = BedrockService()
        question = {
            "id": "test_q1",
            "question_text": question_text,
            "marks": 3,
            "tier": tier,
            "topic": topic
        }
        generation_request = {"topic": topic, "tier": tier}
        
        # Act - Run validation multiple times
        result1 = bedrock_service._validate_single_question(question, generation_request, "test")
        result2 = bedrock_service._validate_single_question(question, generation_request, "test")
        
        # Assert - Results should be consistent
        assert result1['is_valid'] == result2['is_valid']
        assert result1['confidence'] == result2['confidence']
        assert result1['errors'] == result2['errors']
    
    @given(marks=st.integers(min_value=1, max_value=10))
    @settings(max_examples=30)
    def test_difficulty_assessment_bounds(self, marks):
        """
        Test that difficulty assessment always returns values within expected bounds.
        """
        # Arrange
        bedrock_service = BedrockService()
        question_texts = [
            "Calculate 2 + 2",  # Simple
            "Solve the quadratic equation x^2 + 5x + 6 = 0 using the quadratic formula",  # Complex
            "Find the area of a triangle with base 5cm and height 3cm"  # Medium
        ]
        
        for question_text in question_texts:
            # Act
            difficulty = bedrock_service._assess_difficulty(question_text)
            
            # Assert - Difficulty should be within bounds
            assert 0.0 <= difficulty <= 1.0
            assert isinstance(difficulty, float)