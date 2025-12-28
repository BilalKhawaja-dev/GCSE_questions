"""
Lambda in-memory caching utilities for GCSE Question Generator.

This module provides caching functionality for Lambda functions to reduce
Bedrock API calls and improve performance while maintaining cost efficiency.
"""

import hashlib
import json
import logging
import os
import time
from typing import Any, Dict, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# Cache disable option for testing
DISABLE_CACHING = os.environ.get('DISABLE_QUESTION_CACHING', 'false').lower() == 'true' 

# Global cache (persists across warm Lambda invocations)
QUERY_CACHE = {}
GENERATION_CACHE = {}

# Cache configuration
CACHE_TTL = 3600  # 1 hour in seconds
MAX_CACHE_SIZE = 100  # Maximum number of cached items per cache type

# Cache metrics (for monitoring)
CACHE_METRICS = {
    'query_hits': 0,
    'query_misses': 0,
    'generation_hits': 0,
    'generation_misses': 0,
    'evictions': 0,
    'invalidations': 0
}


def create_cache_key(data: Dict[str, Any]) -> str:
    """
    Create a deterministic cache key from request data.
    
    Args:
        data: Dictionary containing request parameters
        
    Returns:
        SHA256 hash of the normalized data
    """
    # Normalize the data for consistent hashing
    normalized_data = _normalize_cache_data(data)
    
    # Create JSON string and hash it
    json_str = json.dumps(normalized_data, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(json_str.encode('utf-8')).hexdigest()


def get_cached_query_response(cache_key: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve cached query interpretation response.
    
    Args:
        cache_key: Cache key for the query
        
    Returns:
        Cached response if valid, None otherwise
    """
    if DISABLE_CACHING:
        logger.info("Query caching disabled by environment variable")
        return None
    return _get_cached_response(QUERY_CACHE, cache_key, 'query')


def cache_query_response(cache_key: str, response: Dict[str, Any]) -> None:
    """
    Cache query interpretation response.
    
    Args:
        cache_key: Cache key for the query
        response: Response to cache
    """
    _cache_response(QUERY_CACHE, cache_key, response, 'query')


def get_cached_generation_response(cache_key: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve cached question generation response.
    
    Args:
        cache_key: Cache key for the generation request
        
    Returns:
        Cached response if valid, None otherwise
    """
    if DISABLE_CACHING:
        logger.info("Generation caching disabled by environment variable")
        return None
    return _get_cached_response(GENERATION_CACHE, cache_key, 'generation')


def cache_generation_response(cache_key: str, response: Dict[str, Any]) -> None:
    """
    Cache question generation response.
    
    Args:
        cache_key: Cache key for the generation request
        response: Response to cache
    """
    _cache_response(GENERATION_CACHE, cache_key, response, 'generation')


def invalidate_cache(cache_type: str = 'all') -> int:
    """
    Invalidate cache entries.
    
    Args:
        cache_type: Type of cache to invalidate ('query', 'generation', or 'all')
        
    Returns:
        Number of entries invalidated
    """
    global QUERY_CACHE, GENERATION_CACHE, CACHE_METRICS
    
    invalidated_count = 0
    
    if cache_type in ('query', 'all'):
        invalidated_count += len(QUERY_CACHE)
        QUERY_CACHE.clear()
        logger.info(f"Invalidated query cache")
    
    if cache_type in ('generation', 'all'):
        invalidated_count += len(GENERATION_CACHE)
        GENERATION_CACHE.clear()
        logger.info(f"Invalidated generation cache")
    
    CACHE_METRICS['invalidations'] += invalidated_count
    
    logger.info(
        "Cache invalidation completed",
        extra={
            "cache_type": cache_type,
            "invalidated_count": invalidated_count,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    
    return invalidated_count


def get_cache_metrics() -> Dict[str, Any]:
    """
    Get current cache metrics for monitoring.
    
    Returns:
        Dictionary containing cache hit/miss ratios and other metrics
    """
    global CACHE_METRICS
    
    # Calculate hit ratios
    total_query_requests = CACHE_METRICS['query_hits'] + CACHE_METRICS['query_misses']
    total_generation_requests = CACHE_METRICS['generation_hits'] + CACHE_METRICS['generation_misses']
    
    query_hit_ratio = (
        CACHE_METRICS['query_hits'] / total_query_requests 
        if total_query_requests > 0 else 0.0
    )
    
    generation_hit_ratio = (
        CACHE_METRICS['generation_hits'] / total_generation_requests 
        if total_generation_requests > 0 else 0.0
    )
    
    return {
        'query_cache': {
            'size': len(QUERY_CACHE),
            'hits': CACHE_METRICS['query_hits'],
            'misses': CACHE_METRICS['query_misses'],
            'hit_ratio': round(query_hit_ratio, 3)
        },
        'generation_cache': {
            'size': len(GENERATION_CACHE),
            'hits': CACHE_METRICS['generation_hits'],
            'misses': CACHE_METRICS['generation_misses'],
            'hit_ratio': round(generation_hit_ratio, 3)
        },
        'total_evictions': CACHE_METRICS['evictions'],
        'total_invalidations': CACHE_METRICS['invalidations'],
        'cache_ttl_seconds': CACHE_TTL,
        'max_cache_size': MAX_CACHE_SIZE,
        'timestamp': datetime.utcnow().isoformat()
    }


def _get_cached_response(cache: Dict[str, Any], cache_key: str, cache_type: str) -> Optional[Dict[str, Any]]:
    """
    Internal method to retrieve cached response with TTL validation.
    
    Args:
        cache: Cache dictionary to search
        cache_key: Cache key
        cache_type: Type of cache for metrics
        
    Returns:
        Cached response if valid, None otherwise
    """
    global CACHE_METRICS
    
    if cache_key in cache:
        cached_item = cache[cache_key]
        current_time = time.time()
        
        # Check if cache entry is still valid
        if current_time - cached_item['timestamp'] < CACHE_TTL:
            # Cache hit
            CACHE_METRICS[f'{cache_type}_hits'] += 1
            
            logger.info(
                f"Cache hit for {cache_type}",
                extra={
                    "cache_key": cache_key[:16] + "...",  # Log partial key for privacy
                    "cache_type": cache_type,
                    "age_seconds": int(current_time - cached_item['timestamp'])
                }
            )
            
            return cached_item['response']
        else:
            # Cache entry expired, remove it
            del cache[cache_key]
            logger.debug(f"Expired cache entry removed for {cache_type}")
    
    # Cache miss
    CACHE_METRICS[f'{cache_type}_misses'] += 1
    
    logger.debug(
        f"Cache miss for {cache_type}",
        extra={
            "cache_key": cache_key[:16] + "...",
            "cache_type": cache_type
        }
    )
    
    return None


def _cache_response(cache: Dict[str, Any], cache_key: str, response: Dict[str, Any], cache_type: str) -> None:
    """
    Internal method to cache response with size management.
    
    Args:
        cache: Cache dictionary to store in
        cache_key: Cache key
        response: Response to cache
        cache_type: Type of cache for metrics
    """
    global CACHE_METRICS
    
    # Check if cache is at maximum size
    if len(cache) >= MAX_CACHE_SIZE:
        # Evict oldest entry (simple LRU approximation)
        oldest_key = min(cache.keys(), key=lambda k: cache[k]['timestamp'])
        del cache[oldest_key]
        CACHE_METRICS['evictions'] += 1
        
        logger.debug(
            f"Cache eviction for {cache_type}",
            extra={
                "evicted_key": oldest_key[:16] + "...",
                "cache_type": cache_type,
                "cache_size": len(cache)
            }
        )
    
    # Store the response with timestamp
    cache[cache_key] = {
        'response': response,
        'timestamp': time.time()
    }
    
    logger.info(
        f"Response cached for {cache_type}",
        extra={
            "cache_key": cache_key[:16] + "...",
            "cache_type": cache_type,
            "cache_size": len(cache),
            "response_size": len(json.dumps(response))
        }
    )


def _normalize_cache_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize data for consistent cache key generation.
    
    Args:
        data: Raw request data
        
    Returns:
        Normalized data dictionary
    """
    import re
    
    normalized = {}
    
    # Include only relevant fields for caching
    cache_fields = [
        'query', 'topic', 'subtopic', 'tier', 'count', 
        'specification_version', 'marks'
    ]
    
    for field in cache_fields:
        if field in data and data[field] is not None:
            # Normalize strings to lowercase for consistent hashing
            if isinstance(data[field], str):
                # Normalize whitespace: strip and collapse multiple spaces
                normalized_str = re.sub(r'\s+', ' ', data[field].strip()).lower()
                normalized[field] = normalized_str
            else:
                normalized[field] = data[field]
    
    return normalized