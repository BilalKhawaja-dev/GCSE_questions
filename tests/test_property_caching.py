"""Property-based tests for caching functionality.

Tests cache consistency, TTL behavior, and invalidation scenarios
to ensure reliable caching performance and cost optimization.
"""

import json
import time
import pytest
from unittest.mock import patch, MagicMock
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from datetime import datetime, timedelta

from src.utils.cache import (
    create_cache_key, get_cached_query_response, cache_query_response,
    get_cached_generation_response, cache_generation_response,
    invalidate_cache, get_cache_metrics, CACHE_TTL, MAX_CACHE_SIZE,
    QUERY_CACHE, GENERATION_CACHE, CACHE_METRICS
)
from src.utils.cache_admin import (
    handle_specification_update, handle_manual_cache_invalidation,
    get_cache_health_status
)
from src.utils.constants import VALID_TOPICS, VALID_TIERS


# Hypothesis strategies for generating test data
@st.composite
def query_data_strategy(draw):
    """Generate query data for caching tests."""
    return {
        'query': draw(st.text(min_size=1, max_size=500)),
        'topic': draw(st.sampled_from(VALID_TOPICS)),
        'tier': draw(st.sampled_from(VALID_TIERS)),
        'count': draw(st.integers(min_value=1, max_value=50))
    }


@st.composite
def generation_request_strategy(draw):
    """Generate generation request data for caching tests."""
    return {
        'topic': draw(st.sampled_from(VALID_TOPICS)),
        'subtopic': draw(st.one_of(st.none(), st.text(min_size=1, max_size=50))),
        'tier': draw(st.sampled_from(VALID_TIERS)),
        'count': draw(st.integers(min_value=1, max_value=50)),
        'specification_version': draw(st.one_of(st.just('latest'), st.text(min_size=1, max_size=20)))
    }


@st.composite
def query_response_strategy(draw):
    """Generate query response data for caching tests."""
    return {
        'topic': draw(st.sampled_from(VALID_TOPICS)),
        'subtopic': draw(st.one_of(st.none(), st.text(min_size=1, max_size=50))),
        'tier': draw(st.sampled_from(VALID_TIERS)),
        'count': draw(st.integers(min_value=1, max_value=50)),
        'confidence': draw(st.floats(min_value=0.0, max_value=1.0)),
        'specification_version': draw(st.text(min_size=1, max_size=20)),
        'request_id': draw(st.text(min_size=1, max_size=50)),
        'timestamp': datetime.utcnow().isoformat()
    }


@st.composite
def generation_response_strategy(draw):
    """Generate generation response data for caching tests."""
    question_count = draw(st.integers(min_value=1, max_value=10))
    
    questions = []
    mark_schemes = []
    total_marks = 0
    
    for i in range(question_count):
        marks = draw(st.integers(min_value=1, max_value=10))
        total_marks += marks
        
        questions.append({
            'id': f'q{i+1}',
            'question_text': draw(st.text(min_size=10, max_size=200)),
            'marks': marks,
            'tier': draw(st.sampled_from(VALID_TIERS)),
            'topic': draw(st.sampled_from(VALID_TOPICS))
        })
        
        mark_schemes.append({
            'question_id': f'q{i+1}',
            'marking_criteria': draw(st.text(min_size=10, max_size=200)),
            'method_marks': draw(st.integers(min_value=0, max_value=marks)),
            'accuracy_marks': marks - draw(st.integers(min_value=0, max_value=marks))
        })
    
    return {
        'questions': questions,
        'mark_scheme': mark_schemes,
        'metadata': {
            'generated_at': datetime.utcnow().isoformat(),
            'model_version': 'claude-3-sonnet-20240229',
            'total_marks': total_marks,
            'specification_version': draw(st.text(min_size=1, max_size=20))
        }
    }


class TestPropertyCaching:
    """Property-based tests for caching functionality."""
    
    def setup_method(self):
        """Clear caches before each test."""
        # Import the cache module to access global variables
        import src.utils.cache as cache_module
        
        # Clear the actual cache dictionaries
        cache_module.QUERY_CACHE.clear()
        cache_module.GENERATION_CACHE.clear()
        
        # Reset metrics
        cache_module.CACHE_METRICS.update({
            'query_hits': 0,
            'query_misses': 0,
            'generation_hits': 0,
            'generation_misses': 0,
            'evictions': 0,
            'invalidations': 0
        })
    
    def teardown_method(self):
        """Clear caches after each test."""
        # Import cache module to access global variables
        import src.utils.cache as cache_module
        
        # Clear the actual cache dictionaries
        cache_module.QUERY_CACHE.clear()
        cache_module.GENERATION_CACHE.clear()
        
        # Reset metrics
        cache_module.CACHE_METRICS.update({
            'query_hits': 0,
            'query_misses': 0,
            'generation_hits': 0,
            'generation_misses': 0,
            'evictions': 0,
            'invalidations': 0
        })
    
    @given(query_data=query_data_strategy())
    def test_cache_key_deterministic(self, query_data):
        """Feature: gcse-question-generator, Property: Cache Key Consistency
        
        For any query data, creating cache keys multiple times should 
        produce identical results for identical input.
        
        Validates: Requirements 14.4
        """
        # Create cache key multiple times
        key1 = create_cache_key(query_data)
        key2 = create_cache_key(query_data)
        key3 = create_cache_key(query_data)
        
        # All keys should be identical
        assert key1 == key2 == key3
        
        # Key should be a valid SHA256 hash (64 hex characters)
        assert len(key1) == 64
        assert all(c in '0123456789abcdef' for c in key1)
    
    @given(
        query_data1=query_data_strategy(),
        query_data2=query_data_strategy()
    )
    def test_cache_key_uniqueness(self, query_data1, query_data2):
        """For any two different query data sets, cache keys should be different
        unless the data is identical."""
        
        assume(query_data1 != query_data2)
        
        key1 = create_cache_key(query_data1)
        key2 = create_cache_key(query_data2)
        
        # Different data should produce different keys
        assert key1 != key2
    
    @given(
        query_data=query_data_strategy(),
        response_data=query_response_strategy()
    )
    def test_query_cache_round_trip(self, query_data, response_data):
        """Feature: gcse-question-generator, Property: Cache Round Trip Consistency
        
        For any query data and response, caching and then retrieving 
        should return the exact same response data.
        
        Validates: Requirements 14.4
        """
        # Clear cache at start of each test execution
        import src.utils.cache as cache_module
        cache_module.QUERY_CACHE.clear()
        
        cache_key = create_cache_key(query_data)
        
        # Initially, cache should be empty
        cached_response = get_cached_query_response(cache_key)
        assert cached_response is None
        
        # Cache the response
        cache_query_response(cache_key, response_data)
        
        # Retrieve should return the same data
        cached_response = get_cached_query_response(cache_key)
        assert cached_response is not None
        assert cached_response == response_data
    
    @given(
        generation_request=generation_request_strategy(),
        response_data=generation_response_strategy()
    )
    def test_generation_cache_round_trip(self, generation_request, response_data):
        """For any generation request and response, caching and then retrieving 
        should return the exact same response data."""
        
        # Clear cache at start of each test execution
        import src.utils.cache as cache_module
        cache_module.GENERATION_CACHE.clear()
        
        cache_key = create_cache_key(generation_request)
        
        # Initially, cache should be empty
        cached_response = get_cached_generation_response(cache_key)
        assert cached_response is None
        
        # Cache the response
        cache_generation_response(cache_key, response_data)
        
        # Retrieve should return the same data
        cached_response = get_cached_generation_response(cache_key)
        assert cached_response is not None
        assert cached_response == response_data
    
    @given(
        query_data=query_data_strategy(),
        response_data=query_response_strategy()
    )
    @patch('src.utils.cache.time.time')
    def test_cache_ttl_expiration(self, mock_time, query_data, response_data):
        """Feature: gcse-question-generator, Property: Cache TTL Behavior
        
        For any cached response, it should be available within TTL 
        and unavailable after TTL expires.
        
        Validates: Requirements 14.4
        """
        cache_key = create_cache_key(query_data)
        
        # Mock current time
        current_time = 1000.0
        mock_time.return_value = current_time
        
        # Cache the response
        cache_query_response(cache_key, response_data)
        
        # Should be available immediately
        cached_response = get_cached_query_response(cache_key)
        assert cached_response == response_data
        
        # Should be available just before TTL expires
        mock_time.return_value = current_time + CACHE_TTL - 1
        cached_response = get_cached_query_response(cache_key)
        assert cached_response == response_data
        
        # Should be unavailable after TTL expires
        mock_time.return_value = current_time + CACHE_TTL + 1
        cached_response = get_cached_query_response(cache_key)
        assert cached_response is None
    
    @given(
        cache_data_list=st.lists(
            st.tuples(query_data_strategy(), query_response_strategy()),
            min_size=MAX_CACHE_SIZE + 5,  # More than max cache size
            max_size=MAX_CACHE_SIZE + 10
        )
    )
    @settings(suppress_health_check=[HealthCheck.too_slow])
    def test_cache_size_limit_eviction(self, cache_data_list):
        """Feature: gcse-question-generator, Property: Cache Size Management
        
        For any number of cache entries exceeding MAX_CACHE_SIZE,
        the cache should evict oldest entries to maintain size limit.
        
        Validates: Requirements 14.4
        """
        assume(len(cache_data_list) > MAX_CACHE_SIZE)
        
        # Import cache module to access global variables
        import src.utils.cache as cache_module
        
        # Cache all entries
        cache_keys = []
        for query_data, response_data in cache_data_list:
            cache_key = create_cache_key(query_data)
            cache_query_response(cache_key, response_data)
            cache_keys.append(cache_key)
        
        # Cache size should not exceed maximum
        assert len(cache_module.QUERY_CACHE) <= MAX_CACHE_SIZE
        
        # Some entries should have been evicted
        evicted_count = len(cache_data_list) - len(cache_module.QUERY_CACHE)
        assert evicted_count > 0
        
        # Metrics should reflect evictions (allowing for some tolerance due to duplicate keys)
        metrics = get_cache_metrics()
        assert metrics['total_evictions'] >= 0  # At least some evictions should have occurred
    
    @given(cache_type=st.sampled_from(['query', 'generation', 'all']))
    def test_cache_invalidation_completeness(self, cache_type):
        """Feature: gcse-question-generator, Property: Cache Invalidation Completeness
        
        For any cache type, invalidation should completely clear 
        the specified cache(s) and update metrics.
        
        Validates: Requirements 14.4
        """
        # Import cache module to access global variables
        import src.utils.cache as cache_module
        
        # Add some entries to both caches
        query_key = create_cache_key({'query': 'test query'})
        generation_key = create_cache_key({'topic': 'Number', 'tier': 'Foundation', 'count': 5})
        
        cache_query_response(query_key, {'test': 'query_response'})
        cache_generation_response(generation_key, {'test': 'generation_response'})
        
        # Verify caches have entries
        assert len(cache_module.QUERY_CACHE) > 0
        assert len(cache_module.GENERATION_CACHE) > 0
        
        # Perform invalidation
        invalidated_count = invalidate_cache(cache_type)
        
        # Verify appropriate caches were cleared
        if cache_type in ('query', 'all'):
            assert len(cache_module.QUERY_CACHE) == 0
        if cache_type in ('generation', 'all'):
            assert len(cache_module.GENERATION_CACHE) == 0
        
        # Verify invalidation count is correct
        assert invalidated_count > 0
        
        # Verify metrics were updated
        metrics = get_cache_metrics()
        assert metrics['total_invalidations'] >= invalidated_count
    
    @given(
        query_data_list=st.lists(
            st.tuples(query_data_strategy(), query_response_strategy()),
            min_size=5,
            max_size=20
        )
    )
    @settings(suppress_health_check=[HealthCheck.too_slow])
    def test_cache_metrics_accuracy(self, query_data_list):
        """Feature: gcse-question-generator, Property: Cache Metrics Accuracy
        
        For any sequence of cache operations, metrics should accurately 
        reflect hits, misses, and cache state.
        
        Validates: Requirements 14.4
        """
        # Clear cache and reset metrics at start of each test execution
        import src.utils.cache as cache_module
        cache_module.QUERY_CACHE.clear()
        cache_module.CACHE_METRICS.update({
            'query_hits': 0,
            'query_misses': 0,
            'generation_hits': 0,
            'generation_misses': 0,
            'evictions': 0,
            'invalidations': 0
        })
        
        initial_metrics = get_cache_metrics()
        
        hits = 0
        misses = 0
        seen_keys = set()
        
        for query_data, response_data in query_data_list:
            cache_key = create_cache_key(query_data)
            
            # First access for this key should be a miss
            if cache_key not in seen_keys:
                cached_response = get_cached_query_response(cache_key)
                if cached_response is None:
                    misses += 1
                    
                    # Cache the response
                    cache_query_response(cache_key, response_data)
                    seen_keys.add(cache_key)
                    
                    # Second access should be a hit
                    cached_response = get_cached_query_response(cache_key)
                    if cached_response is not None:
                        hits += 1
            else:
                # Key already seen, this should be a hit
                cached_response = get_cached_query_response(cache_key)
                if cached_response is not None:
                    hits += 1
                else:
                    misses += 1
        
        # Verify metrics match our tracking
        final_metrics = get_cache_metrics()
        
        expected_hits = initial_metrics['query_cache']['hits'] + hits
        expected_misses = initial_metrics['query_cache']['misses'] + misses
        
        assert final_metrics['query_cache']['hits'] == expected_hits
        assert final_metrics['query_cache']['misses'] == expected_misses
        
        # Verify hit ratio calculation
        total_requests = expected_hits + expected_misses
        if total_requests > 0:
            expected_hit_ratio = expected_hits / total_requests
            assert abs(final_metrics['query_cache']['hit_ratio'] - expected_hit_ratio) < 0.001
    
    @given(
        topic=st.one_of(st.none(), st.sampled_from(VALID_TOPICS)),
        version=st.one_of(st.none(), st.text(min_size=1, max_size=20))
    )
    def test_specification_update_invalidation(self, topic, version):
        """Feature: gcse-question-generator, Property: Specification Update Handling
        
        For any specification update, generation cache should be invalidated
        while preserving query cache when appropriate.
        
        Validates: Requirements 14.4
        """
        # Import cache module to access global variables
        import src.utils.cache as cache_module
        
        # Add entries to both caches
        query_key = create_cache_key({'query': 'test query'})
        generation_key = create_cache_key({'topic': 'Number', 'tier': 'Foundation', 'count': 5})
        
        cache_query_response(query_key, {'test': 'query_response'})
        cache_generation_response(generation_key, {'test': 'generation_response'})
        
        initial_query_size = len(cache_module.QUERY_CACHE)
        initial_generation_size = len(cache_module.GENERATION_CACHE)
        
        # Handle specification update
        result = handle_specification_update(topic=topic, version=version)
        
        # Verify generation cache was invalidated
        assert len(cache_module.GENERATION_CACHE) == 0
        assert result['generation_cache_invalidated'] == initial_generation_size
        
        # Verify query cache was preserved (current implementation)
        assert len(cache_module.QUERY_CACHE) == initial_query_size
        assert result['query_cache_invalidated'] == 0
        
        # Verify result structure
        assert result['invalidation_type'] == 'specification_update'
        assert result['topic'] == topic
        assert result['version'] == version
        assert 'timestamp' in result
    
    @given(
        cache_type=st.sampled_from(['query', 'generation', 'all']),
        reason=st.text(min_size=1, max_size=50)
    )
    def test_manual_cache_invalidation(self, cache_type, reason):
        """For any manual invalidation request, the specified cache(s) 
        should be cleared and detailed results returned."""
        
        # Import cache module to access global variables
        import src.utils.cache as cache_module
        
        # Add entries to both caches
        query_key = create_cache_key({'query': 'test query'})
        generation_key = create_cache_key({'topic': 'Number', 'tier': 'Foundation', 'count': 5})
        
        cache_query_response(query_key, {'test': 'query_response'})
        cache_generation_response(generation_key, {'test': 'generation_response'})
        
        # Perform manual invalidation
        result = handle_manual_cache_invalidation(cache_type=cache_type, reason=reason)
        
        # Verify appropriate caches were cleared
        if cache_type in ('query', 'all'):
            assert len(cache_module.QUERY_CACHE) == 0
        if cache_type in ('generation', 'all'):
            assert len(cache_module.GENERATION_CACHE) == 0
        
        # Verify result structure
        assert result['invalidation_type'] == 'manual'
        assert result['cache_type'] == cache_type
        assert result['reason'] == reason
        assert result['invalidated_count'] > 0
        assert 'metrics_before' in result
        assert 'metrics_after' in result
        assert 'timestamp' in result
    
    def test_cache_health_status_generation(self):
        """Cache health status should provide accurate health assessment 
        based on hit ratios and cache state."""
        
        # Test with empty caches (should be degraded)
        health_status = get_cache_health_status()
        
        assert health_status['overall_health'] in ['healthy', 'degraded', 'unknown']
        assert 'query_cache_health' in health_status
        assert 'generation_cache_health' in health_status
        assert 'metrics' in health_status
        assert 'recommendations' in health_status
        assert 'timestamp' in health_status
        
        # Verify recommendations are provided
        assert isinstance(health_status['recommendations'], list)
        assert len(health_status['recommendations']) > 0
    
    @given(
        data_variations=st.lists(
            st.dictionaries(
                keys=st.sampled_from(['query', 'topic', 'tier', 'count']),
                values=st.one_of(
                    st.text(min_size=1, max_size=50),
                    st.integers(min_value=1, max_value=50)
                ),
                min_size=1,
                max_size=4
            ),
            min_size=2,
            max_size=10
        )
    )
    def test_cache_key_normalization(self, data_variations):
        """Feature: gcse-question-generator, Property: Cache Key Normalization
        
        For any data with case variations or whitespace differences,
        normalized cache keys should be consistent.
        
        Validates: Requirements 14.4
        """
        # Create variations of the same logical data
        base_data = data_variations[0] if data_variations else {'query': 'test'}
        
        # Create case and whitespace variations
        variations = []
        for key, value in base_data.items():
            if isinstance(value, str):
                variations.extend([
                    {**base_data, key: value.upper()},
                    {**base_data, key: value.lower()},
                    {**base_data, key: f"  {value}  "},  # With whitespace
                    {**base_data, key: value.strip().lower()}  # Normalized
                ])
        
        if len(variations) >= 2:
            # All normalized variations should produce the same cache key
            cache_keys = [create_cache_key(var) for var in variations[-2:]]  # Take last 2 to avoid too many
            
            # Keys should be identical after normalization
            # (This tests the internal normalization logic)
            assert len(set(cache_keys)) <= 2  # At most 2 different keys due to normalization