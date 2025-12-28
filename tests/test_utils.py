"""Unit tests for utility functions."""

import pytest
from src.utils.validation import (
    validate_query_input,
    sanitize_input,
    detect_malicious_content,
    validate_generation_request
)
from src.utils.constants import VALID_TOPICS, VALID_TIERS, TOPIC_MAPPING


class TestValidation:
    """Test cases for validation utilities."""
    
    def test_valid_query_passes_validation(self):
        """Test that valid query passes validation."""
        query = "fractions Foundation 5 questions"
        result = validate_query_input(query)
        
        assert result["valid"] is True
        assert result["sanitized_query"] == query
        assert result["length"] == len(query)
    
    def test_empty_query_fails_validation(self):
        """Test that empty query fails validation."""
        with pytest.raises(ValueError, match="Query cannot be empty"):
            validate_query_input("")
    
    def test_long_query_fails_validation(self):
        """Test that overly long query fails validation."""
        long_query = "a" * 501  # Exceeds 500 character limit
        with pytest.raises(ValueError, match="Query too long"):
            validate_query_input(long_query)
    
    def test_malicious_query_fails_validation(self):
        """Test that malicious query fails validation."""
        malicious_query = "SELECT * FROM users; DROP TABLE questions;"
        with pytest.raises(ValueError, match="potentially malicious content"):
            validate_query_input(malicious_query)
    
    def test_sanitize_input_removes_html(self):
        """Test that sanitize_input removes HTML tags."""
        dirty_input = "<script>alert('xss')</script>fractions"
        clean_input = sanitize_input(dirty_input)
        assert "<script>" not in clean_input
        assert "fractions" in clean_input
    
    def test_sanitize_input_removes_sql_chars(self):
        """Test that sanitize_input removes SQL injection characters."""
        dirty_input = "fractions'; DROP TABLE--"
        clean_input = sanitize_input(dirty_input)
        assert "'" not in clean_input
        assert ";" not in clean_input
        assert "--" not in clean_input
    
    def test_detect_malicious_content_sql_injection(self):
        """Test detection of SQL injection patterns."""
        sql_query = "SELECT * FROM users"
        patterns = detect_malicious_content(sql_query)
        assert "SQL injection" in patterns
    
    def test_detect_malicious_content_xss(self):
        """Test detection of XSS patterns."""
        xss_input = "<script>alert('xss')</script>"
        patterns = detect_malicious_content(xss_input)
        assert "XSS" in patterns
    
    def test_validate_generation_request_valid(self):
        """Test validation of valid generation request."""
        result = validate_generation_request(
            topic="Number",
            tier="Foundation",
            count=5,
            specification_version="2024.1"
        )
        
        assert result["valid"] is True
        assert result["topic"] == "Number"
        assert result["tier"] == "Foundation"
        assert result["count"] == 5
    
    def test_validate_generation_request_invalid_tier(self):
        """Test validation fails for invalid tier."""
        with pytest.raises(ValueError, match="Invalid tier"):
            validate_generation_request(
                topic="Number",
                tier="Invalid",
                count=5
            )
    
    def test_validate_generation_request_invalid_count(self):
        """Test validation fails for invalid count."""
        with pytest.raises(ValueError, match="Invalid count"):
            validate_generation_request(
                topic="Number",
                tier="Foundation",
                count=0  # Invalid
            )


class TestConstants:
    """Test cases for constants."""
    
    def test_valid_topics_not_empty(self):
        """Test that VALID_TOPICS is not empty."""
        assert len(VALID_TOPICS) > 0
        assert "Number" in VALID_TOPICS
        assert "Algebra" in VALID_TOPICS
    
    def test_valid_tiers_correct(self):
        """Test that VALID_TIERS contains expected values."""
        assert VALID_TIERS == ["Foundation", "Higher"]
    
    def test_topic_mapping_structure(self):
        """Test that TOPIC_MAPPING has correct structure."""
        assert len(TOPIC_MAPPING) > 0
        
        # Check a sample mapping
        fractions_mapping = TOPIC_MAPPING.get("fractions")
        assert fractions_mapping is not None
        assert "domain" in fractions_mapping
        assert "file" in fractions_mapping
        assert fractions_mapping["domain"] == "number"
        assert fractions_mapping["file"] == "fractions.json"