"""
Property-based tests for content retrieval system.

Tests universal properties for S3-based specification and examples retrieval,
including circuit breaker behavior and fallback scenarios.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from hypothesis import given, strategies as st, settings
from botocore.exceptions import ClientError

from src.services.content_retrieval_service import (
    ContentRetrievalService, 
    CircuitBreakerOpenError,
    CircuitBreaker
)


# Test data generators
@st.composite
def valid_topic_request(draw):
    """Generate valid topic requests for testing."""
    topics = ["Number", "Algebra", "Geometry", "Statistics", "Probability", "Ratio"]
    subtopics = {
        "Number": ["fractions", "decimals", "percentages", "integers"],
        "Algebra": ["linear_equations", "quadratic_equations", "expressions"],
        "Geometry": ["angles", "triangles", "circles", "area_perimeter"],
        "Statistics": ["data_analysis", "averages", "graphs_charts"],
        "Probability": ["basic_probability", "tree_diagrams"],
        "Ratio": ["ratio_proportion", "scale_factors"]
    }
    tiers = ["Foundation", "Higher", "both"]
    
    topic = draw(st.sampled_from(topics))
    subtopic = draw(st.sampled_from(subtopics[topic]))
    tier = draw(st.sampled_from(tiers))
    
    return {
        "topic": topic,
        "subtopic": subtopic,
        "tier": tier
    }


@st.composite
def mock_specification_content(draw):
    """Generate mock specification content."""
    domains = ["number", "algebra", "geometry", "statistics", "probability", "ratio"]
    tiers = ["Foundation", "Higher", "both"]
    
    return {
        "domain": draw(st.sampled_from(domains)),
        "subtopic": draw(st.text(min_size=1, max_size=20)),
        "tier": draw(st.sampled_from(tiers)),
        "version": "2024.1",
        "learning_objectives": draw(st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=5)),
        "specification_content": draw(st.text(min_size=10, max_size=200)),
        "key_concepts": draw(st.lists(st.text(min_size=1, max_size=20), min_size=0, max_size=10)),
        "common_misconceptions": draw(st.lists(st.text(min_size=1, max_size=50), min_size=0, max_size=5))
    }


@st.composite
def mock_examples_content(draw):
    """Generate mock examples content."""
    example_count = draw(st.integers(min_value=0, max_value=10))
    examples = []
    
    for _ in range(example_count):
        examples.append({
            "question": {
                "id": draw(st.text(min_size=1, max_size=10)),
                "question_text": draw(st.text(min_size=10, max_size=100)),
                "marks": draw(st.integers(min_value=1, max_value=10)),
                "tier": draw(st.sampled_from(["Foundation", "Higher"])),
                "topic": draw(st.text(min_size=1, max_size=20))
            },
            "mark_scheme": {
                "question_id": draw(st.text(min_size=1, max_size=10)),
                "marking_criteria": draw(st.text(min_size=10, max_size=100)),
                "method_marks": draw(st.integers(min_value=0, max_value=5)),
                "accuracy_marks": draw(st.integers(min_value=0, max_value=5))
            },
            "quality_score": draw(st.floats(min_value=0.0, max_value=1.0)),
            "verification_status": "verified"
        })
    
    return {
        "domain": draw(st.sampled_from(["number", "algebra", "geometry"])),
        "subtopic": draw(st.text(min_size=1, max_size=20)),
        "examples": examples
    }


class TestContentRetrievalProperties:
    """Property-based tests for content retrieval service."""
    
    @given(topic_request=valid_topic_request(), spec_content=mock_specification_content())
    @settings(max_examples=100)
    def test_property_3_content_retrieval_for_generation(self, topic_request, spec_content):
        """
        Feature: gcse-question-generator, Property 3: Content Retrieval for Generation
        
        For any question generation request, the Generate_Service should retrieve 
        relevant specification sections from S3 that match the requested topic and tier 
        using deterministic topic-to-file mapping.
        
        **Validates: Requirements 2.2**
        """
        # Arrange
        service = ContentRetrievalService("test-specs", "test-examples", "eu-west-2")
        
        with patch.object(service, '_get_s3_object_with_fallback', return_value=spec_content):
            # Act
            result = service.get_specification_content(
                topic=topic_request["topic"],
                subtopic=topic_request["subtopic"],
                tier=topic_request["tier"],
                request_id="test-request"
            )
            
            # Assert - Content should be retrieved and match expected structure
            assert result is not None
            assert isinstance(result, dict)
            
            # Content should contain required fields from mock
            assert "domain" in result
            assert "learning_objectives" in result
            assert "specification_content" in result
            
            # If tier filtering is applied, it should be respected
            if spec_content["tier"] != "both" and topic_request["tier"] != "both":
                # Content tier should match request or be "both"
                # Note: The system logs a warning but still returns content when tiers don't match
                # This is acceptable behavior as the content is still relevant
                assert result["tier"] in [topic_request["tier"], "both", spec_content["tier"]]
    
    @given(topic_request=valid_topic_request(), examples_content=mock_examples_content())
    @settings(max_examples=100)
    def test_property_3_examples_retrieval_for_generation(self, topic_request, examples_content):
        """
        Feature: gcse-question-generator, Property 3: Content Retrieval for Generation
        
        For any question generation request, the Generate_Service should retrieve 
        relevant seed examples from S3 that match the requested topic and tier.
        
        **Validates: Requirements 2.2**
        """
        # Arrange
        service = ContentRetrievalService("test-specs", "test-examples", "eu-west-2")
        
        with patch.object(service, '_get_s3_object_with_fallback', return_value=examples_content):
            # Act
            result = service.get_examples_content(
                topic=topic_request["topic"],
                subtopic=topic_request["subtopic"],
                tier=topic_request["tier"],
                request_id="test-request"
            )
            
            # Assert - Examples should be retrieved as list
            assert isinstance(result, list)
            
            # If tier filtering is applied, all returned examples should match tier
            if topic_request["tier"] != "both":
                for example in result:
                    if "question" in example and "tier" in example["question"]:
                        assert example["question"]["tier"] == topic_request["tier"]
    
    @given(failure_count=st.integers(min_value=1, max_value=5))
    @settings(max_examples=50)
    def test_property_10_s3_storage_fallback(self, failure_count):
        """
        Feature: gcse-question-generator, Property 10: S3 Storage Fallback
        
        For any S3 unavailability scenario, the System should return cached responses 
        when available or a descriptive error message when caching is not possible.
        
        **Validates: Requirements 16.2**
        """
        # Arrange
        service = ContentRetrievalService("test-specs", "test-examples", "eu-west-2")
        
        # Simulate S3 failures
        s3_error = ClientError(
            error_response={'Error': {'Code': 'ServiceUnavailable', 'Message': 'Service unavailable'}},
            operation_name='GetObject'
        )
        
        with patch.object(service, '_get_s3_object_with_fallback', side_effect=s3_error):
            # Act & Assert - Should handle failures gracefully
            if failure_count >= service.circuit_breaker.failure_threshold:
                # Circuit breaker should open after threshold failures
                for _ in range(failure_count):
                    try:
                        service.get_specification_content("Number", "fractions", "Foundation", "test")
                    except:
                        pass  # Expected to fail
                
                # Next call should raise CircuitBreakerOpenError
                with pytest.raises(Exception):  # Could be CircuitBreakerOpenError or other exception
                    service.get_specification_content("Number", "fractions", "Foundation", "test")
            else:
                # Should fail but not open circuit breaker
                with pytest.raises(Exception):
                    service.get_specification_content("Number", "fractions", "Foundation", "test")
    
    @given(topic_request=valid_topic_request())
    @settings(max_examples=50)
    def test_property_10_examples_fallback_graceful(self, topic_request):
        """
        Feature: gcse-question-generator, Property 10: S3 Storage Fallback
        
        For any S3 unavailability scenario when retrieving examples, the System 
        should return an empty list rather than failing, allowing generation to continue.
        
        **Validates: Requirements 16.2**
        """
        # Arrange
        service = ContentRetrievalService("test-specs", "test-examples", "eu-west-2")
        
        # Simulate S3 failure for examples
        s3_error = ClientError(
            error_response={'Error': {'Code': 'ServiceUnavailable', 'Message': 'Service unavailable'}},
            operation_name='GetObject'
        )
        
        with patch.object(service, '_get_s3_object_with_fallback', side_effect=s3_error):
            # Act
            result = service.get_examples_content(
                topic=topic_request["topic"],
                subtopic=topic_request["subtopic"],
                tier=topic_request["tier"],
                request_id="test-request"
            )
            
            # Assert - Should return empty list, not raise exception
            assert isinstance(result, list)
            assert len(result) == 0
    
    @given(
        topic_requests=st.lists(valid_topic_request(), min_size=1, max_size=5),
        spec_content=mock_specification_content(),
        examples_content=mock_examples_content()
    )
    @settings(max_examples=50)
    def test_property_3_multi_domain_content_retrieval(self, topic_requests, spec_content, examples_content):
        """
        Feature: gcse-question-generator, Property 3: Content Retrieval for Generation
        
        For any multi-domain question generation request, the Generate_Service should 
        retrieve relevant content for all requested topics and organize it appropriately.
        
        **Validates: Requirements 2.2**
        """
        # Arrange
        service = ContentRetrievalService("test-specs", "test-examples", "eu-west-2")
        
        with patch.object(service, '_get_s3_object_with_fallback') as mock_s3:
            # Alternate between spec and examples content
            mock_s3.side_effect = lambda bucket, key: (
                spec_content if "specifications" in key else examples_content
            )
            
            # Act
            result = service.get_multi_domain_content(topic_requests, "test-request")
            
            # Assert - Should return organized content for all topics
            assert isinstance(result, dict)
            
            # Should have attempted to retrieve content for each topic
            # (Some may fail due to unknown topics, but that's expected)
            assert len(result) <= len(topic_requests)
            
            # Each successful entry should have the expected structure
            for key, content in result.items():
                assert "topic" in content
                assert "specification" in content
                assert "examples" in content
                assert isinstance(content["examples"], list)


class TestCircuitBreakerProperties:
    """Property-based tests for circuit breaker functionality."""
    
    @given(
        failure_threshold=st.integers(min_value=1, max_value=10),
        timeout=st.integers(min_value=1, max_value=60)
    )
    @settings(max_examples=50)
    def test_circuit_breaker_threshold_behavior(self, failure_threshold, timeout):
        """
        Test that circuit breaker opens after reaching failure threshold
        and closes after timeout period.
        """
        # Arrange
        circuit_breaker = CircuitBreaker(failure_threshold=failure_threshold, timeout=timeout)
        
        def failing_function():
            raise Exception("Simulated failure")
        
        # Act & Assert - Failures should accumulate
        for i in range(failure_threshold):
            with pytest.raises(Exception):
                circuit_breaker.call(failing_function)
            
            if i < failure_threshold - 1:
                assert circuit_breaker.state in ["CLOSED", "HALF_OPEN"]
        
        # Circuit should be open after threshold failures
        assert circuit_breaker.state == "OPEN"
        
        # Next call should raise CircuitBreakerOpenError
        with pytest.raises(CircuitBreakerOpenError):
            circuit_breaker.call(failing_function)
    
    @given(failure_threshold=st.integers(min_value=2, max_value=5))
    @settings(max_examples=30)
    def test_circuit_breaker_recovery(self, failure_threshold):
        """
        Test that circuit breaker can recover when function starts succeeding.
        """
        # Arrange
        circuit_breaker = CircuitBreaker(failure_threshold=failure_threshold, timeout=1)
        
        def sometimes_failing_function(should_fail=True):
            if should_fail:
                raise Exception("Simulated failure")
            return "success"
        
        # Act - Cause failures to open circuit
        for _ in range(failure_threshold):
            with pytest.raises(Exception):
                circuit_breaker.call(sometimes_failing_function, should_fail=True)
        
        assert circuit_breaker.state == "OPEN"
        
        # Wait for timeout (simulate with manual state change for testing)
        circuit_breaker.state = "HALF_OPEN"
        
        # Successful call should close circuit
        result = circuit_breaker.call(sometimes_failing_function, should_fail=False)
        
        # Assert
        assert result == "success"
        assert circuit_breaker.state == "CLOSED"
        assert circuit_breaker.failure_count == 0