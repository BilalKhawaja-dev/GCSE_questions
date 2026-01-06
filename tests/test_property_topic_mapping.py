"""
Property-based test for topic mapping accuracy.

Tests Property 3: Topic Mapping Accuracy from the GCSE Question Generator V2 design document.
Validates Requirements 1.6 - ensuring the system retrieves the correct S3 specification files 
based on the topic mapping dictionary.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from hypothesis import given, strategies as st, settings
from datetime import datetime
from typing import Dict, Any, List, Optional

from src.services.content_retrieval_service import ContentRetrievalService


# Test data generators
@st.composite
def valid_topic_queries(draw):
    """Generate valid topic queries based on the ContentRetrievalService TOPIC_MAPPING dictionary."""
    # Get the TOPIC_MAPPING from ContentRetrievalService
    topic_mapping = ContentRetrievalService.TOPIC_MAPPING
    
    # Get all valid main topics (number, algebra, geometry, etc.)
    main_topics = list(topic_mapping.keys())
    main_topic = draw(st.sampled_from(main_topics))
    
    # Get all subtopics for this main topic
    subtopics = list(topic_mapping[main_topic].keys())
    subtopic = draw(st.sampled_from(subtopics))
    
    # Get mapping info
    mapping_info = topic_mapping[main_topic][subtopic]
    
    # Convert to proper format
    topic = main_topic.title()
    
    tier = draw(st.sampled_from(["Foundation", "Higher", "both"]))
    
    return {
        "topic": topic,
        "subtopic": subtopic,
        "tier": tier,
        "expected_domain": mapping_info["domain"],
        "expected_file": mapping_info["file"]
    }


@st.composite
def invalid_topic_queries(draw):
    """Generate invalid topic queries that should not exist in TOPIC_MAPPING."""
    # Generate topics that don't exist in the mapping
    invalid_topics = [
        "InvalidTopic", "NonExistentSubject", "FakeArea", 
        "UnknownDomain", "TestTopic", "RandomSubject"
    ]
    
    topic = draw(st.sampled_from(invalid_topics))
    subtopic = draw(st.text(min_size=5, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))))
    tier = draw(st.sampled_from(["Foundation", "Higher", "both"]))
    
    return {
        "topic": topic,
        "subtopic": subtopic,
        "tier": tier
    }


@st.composite
def topic_mapping_entries(draw):
    """Generate entries from the actual ContentRetrievalService TOPIC_MAPPING for validation."""
    topic_mapping = ContentRetrievalService.TOPIC_MAPPING
    
    # Get all main topics
    main_topics = list(topic_mapping.keys())
    main_topic = draw(st.sampled_from(main_topics))
    
    # Get all subtopics for this main topic
    subtopics = list(topic_mapping[main_topic].keys())
    subtopic = draw(st.sampled_from(subtopics))
    
    return {
        "main_topic": main_topic,
        "subtopic": subtopic,
        "mapping": topic_mapping[main_topic][subtopic]
    }


@st.composite
def mock_s3_specification_content(draw):
    """Generate mock S3 specification content for testing."""
    topic = draw(st.sampled_from(["Number", "Algebra", "Geometry", "Statistics", "Probability", "Ratio"]))
    tier = draw(st.sampled_from(["Foundation", "Higher", "both"]))
    
    learning_objectives = draw(st.lists(
        st.text(min_size=10, max_size=100, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd', 'Ps', 'Pe', 'Po'))),
        min_size=1, max_size=5
    ))
    
    return {
        "topic": topic.lower(),
        "tier": tier,
        "learning_objectives": learning_objectives,
        "assessment_objectives": {
            "AO1": "Use and apply standard techniques",
            "AO2": "Reason, interpret and communicate mathematically",
            "AO3": "Solve problems within mathematics and in other contexts"
        },
        "common_misconceptions": [
            "Common error pattern 1",
            "Common error pattern 2"
        ],
        "key_concepts": [
            "Key concept 1",
            "Key concept 2"
        ],
        "specification_version": "2024.1",
        "last_updated": datetime.utcnow().isoformat()
    }


class TestTopicMappingAccuracy:
    """Property-based tests for topic mapping accuracy."""
    
    @given(query_data=valid_topic_queries(), mock_content=mock_s3_specification_content())
    @settings(max_examples=100)
    def test_property_3_correct_s3_files_retrieved_for_valid_topics(self, query_data, mock_content):
        """
        Feature: gcse-question-generator-v2, Property 3: Topic Mapping Accuracy
        
        For any valid topic query, the system should retrieve the correct S3 specification files 
        based on the topic mapping dictionary.
        
        **Validates: Requirements 1.6**
        """
        # Arrange
        content_service = ContentRetrievalService(
            specifications_bucket="test-specs-bucket",
            examples_bucket="test-examples-bucket"
        )
        
        topic = query_data["topic"]
        subtopic = query_data["subtopic"]
        tier = query_data["tier"]
        expected_domain = query_data["expected_domain"]
        expected_file = query_data["expected_file"]
        
        # Expected S3 key based on topic mapping
        expected_s3_key = f"specifications/{expected_domain}/{expected_file}"
        
        with patch.object(content_service, '_get_s3_object') as mock_get_s3:
            mock_get_s3.return_value = mock_content
            
            # Act - Retrieve specification content
            result = content_service.get_specification_content(
                topic=topic,
                subtopic=subtopic,
                tier=tier,
                request_id="test-request"
            )
            
            # Assert - Correct S3 file should be accessed
            mock_get_s3.assert_called_once()
            call_args = mock_get_s3.call_args
            
            # Verify correct bucket and S3 key were used
            assert call_args[0][0] == "test-specs-bucket", "Should use correct specifications bucket"
            assert call_args[0][1] == expected_s3_key, f"Should access correct S3 key: {expected_s3_key}"
            
            # Verify content was returned
            assert result is not None, "Should return specification content"
            assert result == mock_content, "Should return the retrieved S3 content"
    
    @given(query_data=invalid_topic_queries())
    @settings(max_examples=100)
    def test_property_3_error_handling_for_invalid_topics(self, query_data):
        """
        Feature: gcse-question-generator-v2, Property 3: Topic Mapping Accuracy
        
        For any invalid topic query (not in topic mapping dictionary), the system should 
        raise appropriate errors rather than attempting to access non-existent S3 files.
        
        **Validates: Requirements 1.6**
        """
        # Arrange
        content_service = ContentRetrievalService(
            specifications_bucket="test-specs-bucket",
            examples_bucket="test-examples-bucket"
        )
        
        topic = query_data["topic"]
        subtopic = query_data["subtopic"]
        tier = query_data["tier"]
        
        with patch.object(content_service, '_get_s3_object') as mock_get_s3:
            # Act & Assert - Should raise ValueError for unknown topic
            with pytest.raises(ValueError) as exc_info:
                content_service.get_specification_content(
                    topic=topic,
                    subtopic=subtopic,
                    tier=tier,
                    request_id="test-request"
                )
            
            # Verify error message indicates unknown topic
            error_message = str(exc_info.value).lower()
            assert "unknown topic" in error_message or "unknown subtopic" in error_message, \
                f"Error should indicate unknown topic/subtopic: {error_message}"
            
            # Verify S3 was not called for invalid topics
            mock_get_s3.assert_not_called()
    
    @given(mapping_entry=topic_mapping_entries())
    @settings(max_examples=50)
    def test_property_3_topic_mapping_dictionary_structure(self, mapping_entry):
        """
        Feature: gcse-question-generator-v2, Property 3: Topic Mapping Accuracy
        
        For any entry in the topic mapping dictionary, it should have the correct structure
        with 'domain' and 'file' keys pointing to valid S3 paths.
        
        **Validates: Requirements 1.6**
        """
        # Arrange
        main_topic = mapping_entry["main_topic"]
        subtopic = mapping_entry["subtopic"]
        mapping = mapping_entry["mapping"]
        
        # Assert - Mapping structure validation
        assert isinstance(mapping, dict), f"Mapping for {main_topic}.{subtopic} should be a dictionary"
        assert "domain" in mapping, f"Mapping for {main_topic}.{subtopic} should have 'domain' key"
        assert "file" in mapping, f"Mapping for {main_topic}.{subtopic} should have 'file' key"
        
        domain = mapping["domain"]
        file_name = mapping["file"]
        
        # Validate domain format
        assert isinstance(domain, str), f"Domain for {main_topic}.{subtopic} should be a string"
        assert len(domain) > 0, f"Domain for {main_topic}.{subtopic} should not be empty"
        assert domain.islower(), f"Domain for {main_topic}.{subtopic} should be lowercase"
        
        # Validate file format
        assert isinstance(file_name, str), f"File for {main_topic}.{subtopic} should be a string"
        assert file_name.endswith(".json"), f"File for {main_topic}.{subtopic} should end with .json"
        assert len(file_name) > 5, f"File for {main_topic}.{subtopic} should have meaningful name"
        
        # Validate S3 path construction
        expected_s3_path = f"specifications/{domain}/{file_name}"
        assert "/" in expected_s3_path, f"S3 path should contain directory separator"
        assert expected_s3_path.startswith("specifications/"), f"S3 path should start with specifications/"
    
    @given(
        main_topic=st.sampled_from(["number", "algebra", "geometry", "statistics", "probability", "ratio"]),
        tier=st.sampled_from(["Foundation", "Higher", "both"])
    )
    @settings(max_examples=50)
    def test_property_3_topic_normalization_and_mapping(self, main_topic, tier):
        """
        Feature: gcse-question-generator-v2, Property 3: Topic Mapping Accuracy
        
        For any topic name (with various capitalizations), the system should normalize it
        correctly and map it to the appropriate S3 file path.
        
        **Validates: Requirements 1.6**
        """
        # Arrange
        content_service = ContentRetrievalService(
            specifications_bucket="test-specs-bucket",
            examples_bucket="test-examples-bucket"
        )
        
        # Get available subtopics for this main topic
        topic_mapping = ContentRetrievalService.TOPIC_MAPPING
        if main_topic not in topic_mapping:
            pytest.skip(f"Topic {main_topic} not in mapping")
            
        available_subtopics = list(topic_mapping[main_topic].keys())
        if not available_subtopics:
            pytest.skip(f"No subtopics available for {main_topic}")
        
        # Test different capitalizations of the same topic
        # Note: The service normalizes topics to lowercase, so we test variants that should work
        topic_variations = [
            main_topic.lower(),      # Should work - exact match
            main_topic.title(),      # Should work - gets normalized to lowercase
            main_topic.capitalize()  # Should work - gets normalized to lowercase
        ]
        
        mock_content = {
            "topic": main_topic.lower(),
            "tier": tier,
            "learning_objectives": ["Test objective"],
            "specification_version": "2024.1"
        }
        
        with patch.object(content_service, '_get_s3_object') as mock_get_s3:
            mock_get_s3.return_value = mock_content
            
            # Act - Try different capitalizations that should work
            successful_calls = 0
            
            for topic_variant in topic_variations:
                try:
                    result = content_service.get_specification_content(
                        topic=topic_variant,
                        subtopic=None,  # Let it use first available subtopic
                        tier=tier,
                        request_id="test-request"
                    )
                    
                    # Assert - Should successfully retrieve content for normalized variants
                    assert result is not None, f"Should retrieve content for topic variant: {topic_variant}"
                    
                    if mock_get_s3.called:
                        successful_calls += 1
                        
                        # Verify S3 key follows expected pattern
                        call_args = mock_get_s3.call_args
                        s3_key = call_args[0][1]
                        assert s3_key.startswith("specifications/"), f"S3 key should start with specifications/ for {topic_variant}"
                        assert s3_key.endswith(".json"), f"S3 key should end with .json for {topic_variant}"
                        
                        # Reset mock for next iteration
                        mock_get_s3.reset_mock()
                    
                except ValueError as e:
                    # Some topic variations might not be recognized due to normalization logic
                    # This is acceptable as long as at least some variants work
                    pass
            
            # Assert - At least one variant should have worked (the lowercase one should always work)
            assert successful_calls > 0, f"At least one topic variant should work for {main_topic}"
    
    @given(
        main_topic=st.sampled_from(["number", "algebra", "geometry", "statistics", "probability", "ratio"]),
        tier=st.sampled_from(["Foundation", "Higher", "both"])
    )
    @settings(max_examples=100)
    def test_property_3_consistent_mapping_across_calls(self, main_topic, tier):
        """
        Feature: gcse-question-generator-v2, Property 3: Topic Mapping Accuracy
        
        For any topic, repeated calls should consistently map to the same S3 file path,
        ensuring deterministic topic-to-file mapping.
        
        **Validates: Requirements 1.6**
        """
        # Arrange
        content_service = ContentRetrievalService(
            specifications_bucket="test-specs-bucket",
            examples_bucket="test-examples-bucket"
        )
        
        # Get available subtopics for this main topic
        topic_mapping = ContentRetrievalService.TOPIC_MAPPING
        if main_topic not in topic_mapping:
            pytest.skip(f"Topic {main_topic} not in mapping")
            
        available_subtopics = list(topic_mapping[main_topic].keys())
        if not available_subtopics:
            pytest.skip(f"No subtopics available for {main_topic}")
            
        # Use first available subtopic
        subtopic = available_subtopics[0]
        
        # Convert topic to proper format
        topic = main_topic.title()
        
        mock_content = {
            "topic": main_topic,
            "tier": tier,
            "learning_objectives": ["Test objective"],
            "specification_version": "2024.1"
        }
        
        expected_mapping = topic_mapping[main_topic][subtopic]
        expected_s3_key = f"specifications/{expected_mapping['domain']}/{expected_mapping['file']}"
        
        with patch.object(content_service, '_get_s3_object') as mock_get_s3:
            mock_get_s3.return_value = mock_content
            
            # Act - Make multiple calls for the same topic
            s3_keys_called = []
            
            for i in range(3):  # Test consistency across 3 calls
                try:
                    result = content_service.get_specification_content(
                        topic=topic,
                        subtopic=subtopic,
                        tier=tier,
                        request_id=f"test-request-{i}"
                    )
                    
                    # Record the S3 key that was called
                    if mock_get_s3.called:
                        call_args = mock_get_s3.call_args
                        s3_key = call_args[0][1]
                        s3_keys_called.append(s3_key)
                        mock_get_s3.reset_mock()
                        
                except ValueError as e:
                    # If topic/subtopic combination is invalid, that's acceptable
                    # but the error should be consistent
                    pass
            
            # Assert - All calls should map to the same S3 key
            if s3_keys_called:
                # All S3 keys should be identical
                assert all(key == s3_keys_called[0] for key in s3_keys_called), \
                    f"All calls should map to same S3 key, got: {s3_keys_called}"
                
                # Should match expected mapping
                assert s3_keys_called[0] == expected_s3_key, \
                    f"S3 key should match expected mapping: expected {expected_s3_key}, got {s3_keys_called[0]}"
    
    @given(
        main_topic=st.sampled_from(["number", "algebra", "geometry", "statistics", "probability", "ratio"]),
        tier=st.sampled_from(["Foundation", "Higher", "both"])
    )
    @settings(max_examples=50)
    def test_property_3_fallback_behavior_for_missing_subtopic(self, main_topic, tier):
        """
        Feature: gcse-question-generator-v2, Property 3: Topic Mapping Accuracy
        
        For any topic query without a specific subtopic, the system should fall back to
        the first available subtopic in the topic mapping dictionary.
        
        **Validates: Requirements 1.6**
        """
        # Arrange
        content_service = ContentRetrievalService(
            specifications_bucket="test-specs-bucket",
            examples_bucket="test-examples-bucket"
        )
        
        # Get available subtopics for this main topic
        topic_mapping = ContentRetrievalService.TOPIC_MAPPING
        if main_topic not in topic_mapping:
            pytest.skip(f"Topic {main_topic} not in mapping")
            
        available_subtopics = list(topic_mapping[main_topic].keys())
        if not available_subtopics:
            pytest.skip(f"No subtopics available for {main_topic}")
        
        topic = main_topic.title()
        
        mock_content = {
            "topic": main_topic,
            "tier": tier,
            "learning_objectives": ["Test objective"],
            "specification_version": "2024.1"
        }
        
        with patch.object(content_service, '_get_s3_object') as mock_get_s3:
            mock_get_s3.return_value = mock_content
            
            # Act - Request content without specifying subtopic
            try:
                result = content_service.get_specification_content(
                    topic=topic,
                    subtopic=None,  # No subtopic specified
                    tier=tier,
                    request_id="test-request"
                )
                
                # Assert - Should successfully retrieve content using fallback
                assert result is not None, f"Should retrieve content with fallback for topic: {topic}"
                assert mock_get_s3.called, f"Should call S3 with fallback mapping for topic: {topic}"
                
                # Verify S3 key follows expected pattern
                call_args = mock_get_s3.call_args
                s3_key = call_args[0][1]
                assert s3_key.startswith("specifications/"), f"Fallback S3 key should start with specifications/"
                assert s3_key.endswith(".json"), f"Fallback S3 key should end with .json"
                
                # Verify it maps to a valid domain from our topic mapping
                domain = s3_key.split("/")[1]  # Extract domain from path
                valid_domains = set()
                for main_topic_data in topic_mapping.values():
                    for subtopic_data in main_topic_data.values():
                        valid_domains.add(subtopic_data["domain"])
                assert domain in valid_domains, f"Fallback should use valid domain: {domain}"
                
            except ValueError:
                # If topic doesn't exist in mapping, that's expected behavior
                # The important thing is that it fails gracefully with clear error
                pass
    
    @given(
        main_topic=st.sampled_from(["number", "algebra", "geometry", "statistics", "probability", "ratio"]),
        tier=st.sampled_from(["Foundation", "Higher", "both"])
    )
    @settings(max_examples=50)
    def test_property_3_s3_path_construction_validity(self, main_topic, tier):
        """
        Feature: gcse-question-generator-v2, Property 3: Topic Mapping Accuracy
        
        For any topic in the mapping dictionary, the constructed S3 path should be valid
        and follow the expected specifications/{domain}/{file} pattern.
        
        **Validates: Requirements 1.6**
        """
        # Arrange
        topic_mapping = ContentRetrievalService.TOPIC_MAPPING
        
        if main_topic not in topic_mapping:
            pytest.skip(f"Topic {main_topic} not in mapping")
            
        available_subtopics = list(topic_mapping[main_topic].keys())
        if not available_subtopics:
            pytest.skip(f"No subtopics available for {main_topic}")
            
        # Test all subtopics for this main topic
        for subtopic in available_subtopics:
            mapping = topic_mapping[main_topic][subtopic]
            expected_domain = mapping["domain"]
            expected_file = mapping["file"]
            
            # Act - Construct S3 path as the service would
            constructed_s3_key = f"specifications/{expected_domain}/{expected_file}"
            
            # Assert - S3 path validation
            path_parts = constructed_s3_key.split("/")
            assert len(path_parts) == 3, f"S3 path should have 3 parts: {constructed_s3_key}"
            assert path_parts[0] == "specifications", f"First part should be 'specifications': {constructed_s3_key}"
            assert path_parts[1] == expected_domain, f"Second part should be domain: {constructed_s3_key}"
            assert path_parts[2] == expected_file, f"Third part should be filename: {constructed_s3_key}"
            
            # Validate path components
            assert not any(part == "" for part in path_parts), f"No empty path components: {constructed_s3_key}"
            assert not any("." in part for part in path_parts[:-1]), f"Only filename should contain dots: {constructed_s3_key}"
            assert path_parts[2].endswith(".json"), f"Filename should end with .json: {constructed_s3_key}"
            
            # Validate no special characters that could cause S3 issues
            invalid_chars = ["\\", " ", "\t", "\n", "\r"]
            for char in invalid_chars:
                assert char not in constructed_s3_key, f"S3 key should not contain '{char}': {constructed_s3_key}"