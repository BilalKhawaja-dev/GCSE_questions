"""
Property-based test for question generation variation.

Tests Property 1: Question Generation Variation from the GCSE Question Generator V2 design document.
Validates Requirements 1.1, 1.2 - ensuring different queries generate different questions
and no identical cached responses across different topics or repeated requests.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from hypothesis import given, strategies as st, settings
from datetime import datetime
from typing import Dict, Any, List

from src.services.bedrock_service import BedrockService
from src.lambda_handlers.generate_lambda import _generate_questions
from src.lambda_handlers.interpret_lambda import _process_query_with_enhanced_bedrock


# Test data generators
@st.composite
def different_topic_queries(draw):
    """Generate pairs of queries with different topics for testing variation."""
    topics = ["Number", "Algebra", "Geometry", "Statistics", "Probability", "Ratio"]
    
    # Generate two different topics
    topic1 = draw(st.sampled_from(topics))
    topic2 = draw(st.sampled_from([t for t in topics if t != topic1]))
    
    tier = draw(st.sampled_from(["Foundation", "Higher"]))
    count = draw(st.integers(min_value=1, max_value=5))
    
    query1 = {
        "topic": topic1,
        "tier": tier,
        "count": count,
        "specification_version": "latest"
    }
    
    query2 = {
        "topic": topic2,
        "tier": tier,
        "count": count,
        "specification_version": "latest"
    }
    
    return query1, query2


@st.composite
def identical_queries(draw):
    """Generate identical queries for testing repeated request variation."""
    topic = draw(st.sampled_from(["Number", "Algebra", "Geometry", "Statistics", "Probability", "Ratio"]))
    tier = draw(st.sampled_from(["Foundation", "Higher"]))
    count = draw(st.integers(min_value=1, max_value=5))
    
    query = {
        "topic": topic,
        "tier": tier,
        "count": count,
        "specification_version": "latest"
    }
    
    return query


@st.composite
def mock_bedrock_responses(draw):
    """Generate different mock Bedrock responses for testing variation."""
    count = draw(st.integers(min_value=1, max_value=5))
    
    # Generate unique question sets
    questions1 = []
    questions2 = []
    mark_schemes1 = []
    mark_schemes2 = []
    
    for i in range(count):
        # First set of questions
        q1_text = draw(st.text(min_size=20, max_size=100, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd', 'Ps', 'Pe', 'Po'))))
        q1_marks = draw(st.integers(min_value=1, max_value=6))
        
        questions1.append({
            "id": f"q{i+1}",
            "question_text": f"Question Set 1: {q1_text}",
            "marks": q1_marks,
            "tier": "Foundation",
            "topic": "Number",
            "difficulty_score": draw(st.integers(min_value=1, max_value=5))
        })
        
        mark_schemes1.append({
            "question_id": f"q{i+1}",
            "marking_criteria": f"Mark scheme 1 for question {i+1}",
            "method_marks": max(1, q1_marks - 1),
            "accuracy_marks": 1
        })
        
        # Second set of questions (different content)
        q2_text = draw(st.text(min_size=20, max_size=100, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd', 'Ps', 'Pe', 'Po'))))
        q2_marks = draw(st.integers(min_value=1, max_value=6))
        
        questions2.append({
            "id": f"q{i+1}",
            "question_text": f"Question Set 2: {q2_text}",
            "marks": q2_marks,
            "tier": "Foundation",
            "topic": "Number",
            "difficulty_score": draw(st.integers(min_value=1, max_value=5))
        })
        
        mark_schemes2.append({
            "question_id": f"q{i+1}",
            "marking_criteria": f"Mark scheme 2 for question {i+1}",
            "method_marks": max(1, q2_marks - 1),
            "accuracy_marks": 1
        })
    
    response1 = {
        "questions": questions1,
        "mark_scheme": mark_schemes1,
        "metadata": {
            "generated_at": datetime.utcnow().isoformat(),
            "model_version": "claude-3-sonnet-20240229",
            "total_marks": sum(q["marks"] for q in questions1),
            "specification_version": "latest"
        }
    }
    
    response2 = {
        "questions": questions2,
        "mark_scheme": mark_schemes2,
        "metadata": {
            "generated_at": datetime.utcnow().isoformat(),
            "model_version": "claude-3-sonnet-20240229",
            "total_marks": sum(q["marks"] for q in questions2),
            "specification_version": "latest"
        }
    }
    
    return response1, response2


class TestQuestionGenerationVariation:
    """Property-based tests for question generation variation."""
    
    @given(query_pairs=different_topic_queries(), mock_responses=mock_bedrock_responses())
    @settings(max_examples=100)
    def test_property_1_different_topics_generate_different_questions(self, query_pairs, mock_responses):
        """
        Feature: gcse-question-generator-v2, Property 1: Question Generation Variation
        
        For any set of queries with different topics, the system should generate 
        different question sets, ensuring no identical cached responses across different topics.
        
        **Validates: Requirements 1.1**
        """
        # Arrange
        query1, query2 = query_pairs
        response1, response2 = mock_responses
        
        bedrock_service = BedrockService()
        
        # Mock different responses for different topics
        with patch.object(bedrock_service, '_call_bedrock_with_retry') as mock_bedrock:
            # Set up side effect to return different responses for different calls
            mock_bedrock.side_effect = [json.dumps(response1), json.dumps(response2)]
            
            with patch.object(bedrock_service, '_parse_sonnet_response') as mock_parse:
                mock_parse.side_effect = [response1, response2]
                
                with patch.object(bedrock_service, '_validate_question_quality') as mock_validate:
                    mock_validate.side_effect = [response1, response2]
                    
                    # Act - Generate questions for different topics
                    result1 = bedrock_service.generate_questions_with_sonnet(
                        generation_request=query1,
                        spec_content={"learning_objectives": ["test"], "specification_content": "test"},
                        examples_content=[],
                        request_id="test-request-1"
                    )
                    
                    result2 = bedrock_service.generate_questions_with_sonnet(
                        generation_request=query2,
                        spec_content={"learning_objectives": ["test"], "specification_content": "test"},
                        examples_content=[],
                        request_id="test-request-2"
                    )
                    
                    # Assert - Different topics should generate different questions
                    assert result1 != result2, "Different topics should generate different question sets"
                    
                    # Verify questions are actually different
                    questions1_text = [q["question_text"] for q in result1["questions"]]
                    questions2_text = [q["question_text"] for q in result2["questions"]]
                    
                    # At least some questions should be different
                    assert questions1_text != questions2_text, "Question texts should be different for different topics"
                    
                    # Verify Bedrock was called twice (no caching at Bedrock level)
                    assert mock_bedrock.call_count == 2, "Bedrock should be called for each different topic"
    
    @given(query=identical_queries(), mock_responses=mock_bedrock_responses())
    @settings(max_examples=100)
    def test_property_1_repeated_queries_generate_different_questions(self, query, mock_responses):
        """
        Feature: gcse-question-generator-v2, Property 1: Question Generation Variation
        
        For any identical query submitted multiple times, the system should generate 
        varied questions (not identical cached responses), ensuring question diversity.
        
        **Validates: Requirements 1.2**
        """
        # Arrange
        response1, response2 = mock_responses
        
        bedrock_service = BedrockService()
        
        # Mock different responses for repeated identical queries
        with patch.object(bedrock_service, '_call_bedrock_with_retry') as mock_bedrock:
            # Set up side effect to return different responses for repeated calls
            mock_bedrock.side_effect = [json.dumps(response1), json.dumps(response2)]
            
            with patch.object(bedrock_service, '_parse_sonnet_response') as mock_parse:
                mock_parse.side_effect = [response1, response2]
                
                with patch.object(bedrock_service, '_validate_question_quality') as mock_validate:
                    mock_validate.side_effect = [response1, response2]
                    
                    # Act - Generate questions for the same query twice
                    result1 = bedrock_service.generate_questions_with_sonnet(
                        generation_request=query,
                        spec_content={"learning_objectives": ["test"], "specification_content": "test"},
                        examples_content=[],
                        request_id="test-request-1"
                    )
                    
                    result2 = bedrock_service.generate_questions_with_sonnet(
                        generation_request=query,
                        spec_content={"learning_objectives": ["test"], "specification_content": "test"},
                        examples_content=[],
                        request_id="test-request-2"
                    )
                    
                    # Assert - Same query should generate different questions (no caching)
                    assert result1 != result2, "Repeated identical queries should generate different question sets"
                    
                    # Verify questions are actually different
                    questions1_text = [q["question_text"] for q in result1["questions"]]
                    questions2_text = [q["question_text"] for q in result2["questions"]]
                    
                    # Questions should be different to ensure variety
                    assert questions1_text != questions2_text, "Question texts should be different for repeated queries"
                    
                    # Verify Bedrock was called twice (no caching at Bedrock level)
                    assert mock_bedrock.call_count == 2, "Bedrock should be called for each request, even if identical"
    
    @given(
        topic1=st.sampled_from(["Number", "Algebra", "Geometry"]),
        topic2=st.sampled_from(["Statistics", "Probability", "Ratio"]),
        tier=st.sampled_from(["Foundation", "Higher"]),
        count=st.integers(min_value=1, max_value=3)
    )
    @settings(max_examples=50)
    def test_property_1_bedrock_api_calls_for_each_request(self, topic1, topic2, tier, count):
        """
        Feature: gcse-question-generator-v2, Property 1: Question Generation Variation
        
        For any generation request, the system should call Bedrock API for each request
        without relying on cached Bedrock responses, ensuring fresh AI generation.
        
        **Validates: Requirements 1.4, 1.5**
        """
        # Arrange
        bedrock_service = BedrockService()
        
        query1 = {"topic": topic1, "tier": tier, "count": count, "specification_version": "latest"}
        query2 = {"topic": topic2, "tier": tier, "count": count, "specification_version": "latest"}
        
        # Create different mock responses
        mock_response1 = {
            "questions": [
                {
                    "id": f"q{i+1}",
                    "question_text": f"Test question {i+1} for {topic1}",
                    "marks": 2,
                    "tier": tier,
                    "topic": topic1,
                    "difficulty_score": 3
                }
                for i in range(count)
            ],
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
        
        mock_response2 = {
            "questions": [
                {
                    "id": f"q{i+1}",
                    "question_text": f"Test question {i+1} for {topic2}",
                    "marks": 2,
                    "tier": tier,
                    "topic": topic2,
                    "difficulty_score": 3
                }
                for i in range(count)
            ],
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
            mock_bedrock.side_effect = [json.dumps(mock_response1), json.dumps(mock_response2)]
            
            with patch.object(bedrock_service, '_parse_sonnet_response') as mock_parse:
                mock_parse.side_effect = [mock_response1, mock_response2]
                
                with patch.object(bedrock_service, '_validate_question_quality') as mock_validate:
                    mock_validate.side_effect = [mock_response1, mock_response2]
                    
                    # Act - Make two different requests
                    result1 = bedrock_service.generate_questions_with_sonnet(
                        generation_request=query1,
                        spec_content={"learning_objectives": ["test"], "specification_content": "test"},
                        examples_content=[],
                        request_id="test-request-1"
                    )
                    
                    result2 = bedrock_service.generate_questions_with_sonnet(
                        generation_request=query2,
                        spec_content={"learning_objectives": ["test"], "specification_content": "test"},
                        examples_content=[],
                        request_id="test-request-2"
                    )
                    
                    # Assert - Bedrock should be called for each request
                    assert mock_bedrock.call_count == 2, "Bedrock API should be called for each generation request"
                    
                    # Verify different results were returned
                    assert result1 != result2, "Different requests should produce different results"
                    
                    # Verify topic-specific content
                    assert all(q["topic"] == topic1 for q in result1["questions"]), f"All questions in result1 should be for topic {topic1}"
                    assert all(q["topic"] == topic2 for q in result2["questions"]), f"All questions in result2 should be for topic {topic2}"
    
    @given(
        query_text1=st.text(min_size=10, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd', 'Ps', 'Pe', 'Po'))),
        query_text2=st.text(min_size=10, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd', 'Ps', 'Pe', 'Po')))
    )
    @settings(max_examples=50)
    def test_property_1_interpret_lambda_calls_bedrock_for_each_query(self, query_text1, query_text2):
        """
        Feature: gcse-question-generator-v2, Property 1: Question Generation Variation
        
        For any query interpretation request, InterpretLambda should call Bedrock Haiku
        for each request without relying on cached Bedrock responses.
        
        **Validates: Requirements 1.4**
        """
        # Arrange
        bedrock_service = BedrockService()
        
        # Ensure queries are different
        if query_text1 == query_text2:
            query_text2 = query_text2 + " different"
        
        # Mock different interpretation responses
        mock_response1 = json.dumps({
            "topic": "Number",
            "subtopic": "fractions",
            "tier": "Foundation",
            "count": 5,
            "confidence": 0.9
        })
        
        mock_response2 = json.dumps({
            "topic": "Algebra",
            "subtopic": "equations",
            "tier": "Higher",
            "count": 3,
            "confidence": 0.8
        })
        
        with patch.object(bedrock_service, '_call_bedrock_with_retry') as mock_bedrock:
            mock_bedrock.side_effect = [mock_response1, mock_response2]
            
            with patch.object(bedrock_service, '_parse_haiku_response') as mock_parse:
                from src.models.query_intent import QueryIntent
                
                intent1 = QueryIntent(
                    topic="Number",
                    subtopic="fractions",
                    tier="Foundation",
                    count=5,
                    confidence=0.9,
                    specification_version="latest"
                )
                
                intent2 = QueryIntent(
                    topic="Algebra",
                    subtopic="equations",
                    tier="Higher",
                    count=3,
                    confidence=0.8,
                    specification_version="latest"
                )
                
                mock_parse.side_effect = [intent1, intent2]
                
                # Act - Process two different queries
                result1 = bedrock_service.parse_query_with_haiku(query_text1, "test-request-1")
                result2 = bedrock_service.parse_query_with_haiku(query_text2, "test-request-2")
                
                # Assert - Bedrock should be called for each query
                assert mock_bedrock.call_count == 2, "Bedrock API should be called for each query interpretation"
                
                # Verify different results were returned
                assert result1.topic != result2.topic or result1.tier != result2.tier, "Different queries should produce different interpretations"
                
                # Verify both calls were made with proper parameters
                assert len(mock_bedrock.call_args_list) == 2, "Should have two separate Bedrock API calls"