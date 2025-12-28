"""
Cache administration utilities for GCSE Question Generator.

This module provides administrative functions for cache management,
including invalidation triggers and monitoring utilities.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from src.utils.cache import invalidate_cache, get_cache_metrics

logger = logging.getLogger(__name__)


def handle_specification_update(
    topic: Optional[str] = None,
    version: Optional[str] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Handle cache invalidation when specifications are updated.
    
    Args:
        topic: Specific topic that was updated (optional)
        version: Version that was updated (optional)
        request_id: Request ID for logging (optional)
        
    Returns:
        Dictionary with invalidation results
    """
    logger.info(
        "Specification update detected, invalidating caches",
        extra={
            "topic": topic,
            "version": version,
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    
    # For specification updates, we need to invalidate generation cache
    # since questions are based on specification content
    generation_invalidated = invalidate_cache('generation')
    
    # Query cache can remain since it only contains parsed intents
    # However, if the topic mapping changes, we might want to invalidate it too
    query_invalidated = 0
    if topic:
        # If specific topic updated, we could be more selective
        # For now, we'll keep it simple and not invalidate query cache
        pass
    
    result = {
        "invalidation_type": "specification_update",
        "topic": topic,
        "version": version,
        "generation_cache_invalidated": generation_invalidated,
        "query_cache_invalidated": query_invalidated,
        "total_invalidated": generation_invalidated + query_invalidated,
        "timestamp": datetime.utcnow().isoformat(),
        "request_id": request_id
    }
    
    logger.info(
        "Cache invalidation completed",
        extra=result
    )
    
    return result


def handle_manual_cache_invalidation(
    cache_type: str = 'all',
    reason: str = 'manual',
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Handle manual cache invalidation request.
    
    Args:
        cache_type: Type of cache to invalidate ('query', 'generation', or 'all')
        reason: Reason for invalidation
        request_id: Request ID for logging (optional)
        
    Returns:
        Dictionary with invalidation results
    """
    logger.info(
        "Manual cache invalidation requested",
        extra={
            "cache_type": cache_type,
            "reason": reason,
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    
    # Get metrics before invalidation
    metrics_before = get_cache_metrics()
    
    # Perform invalidation
    invalidated_count = invalidate_cache(cache_type)
    
    # Get metrics after invalidation
    metrics_after = get_cache_metrics()
    
    result = {
        "invalidation_type": "manual",
        "cache_type": cache_type,
        "reason": reason,
        "invalidated_count": invalidated_count,
        "metrics_before": metrics_before,
        "metrics_after": metrics_after,
        "timestamp": datetime.utcnow().isoformat(),
        "request_id": request_id
    }
    
    logger.info(
        "Manual cache invalidation completed",
        extra={
            "cache_type": cache_type,
            "invalidated_count": invalidated_count,
            "request_id": request_id
        }
    )
    
    return result


def get_cache_health_status() -> Dict[str, Any]:
    """
    Get cache health status for monitoring.
    
    Returns:
        Dictionary with cache health information
    """
    try:
        metrics = get_cache_metrics()
        
        # Determine health status based on hit ratios
        query_health = "healthy" if metrics['query_cache']['hit_ratio'] >= 0.3 else "degraded"
        generation_health = "healthy" if metrics['generation_cache']['hit_ratio'] >= 0.2 else "degraded"
        
        # Overall health
        overall_health = "healthy" if query_health == "healthy" and generation_health == "healthy" else "degraded"
        
        health_status = {
            "overall_health": overall_health,
            "query_cache_health": query_health,
            "generation_cache_health": generation_health,
            "metrics": metrics,
            "recommendations": _generate_cache_recommendations(metrics),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(
            "Cache health status generated",
            extra={
                "overall_health": overall_health,
                "query_hit_ratio": metrics['query_cache']['hit_ratio'],
                "generation_hit_ratio": metrics['generation_cache']['hit_ratio']
            }
        )
        
        return health_status
        
    except Exception as e:
        logger.error(
            "Failed to generate cache health status",
            extra={"error": str(e)}
        )
        return {
            "overall_health": "unknown",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


def _generate_cache_recommendations(metrics: Dict[str, Any]) -> list:
    """
    Generate cache optimization recommendations based on metrics.
    
    Args:
        metrics: Cache metrics dictionary
        
    Returns:
        List of recommendation strings
    """
    recommendations = []
    
    # Check hit ratios
    if metrics['query_cache']['hit_ratio'] < 0.2:
        recommendations.append(
            "Query cache hit ratio is low. Consider increasing cache TTL or reviewing query patterns."
        )
    
    if metrics['generation_cache']['hit_ratio'] < 0.1:
        recommendations.append(
            "Generation cache hit ratio is low. This is expected for diverse question requests."
        )
    
    # Check evictions
    if metrics['total_evictions'] > 50:
        recommendations.append(
            "High number of cache evictions detected. Consider increasing MAX_CACHE_SIZE."
        )
    
    # Check cache sizes
    if metrics['query_cache']['size'] == 0 and metrics['query_cache']['misses'] > 0:
        recommendations.append(
            "Query cache is empty despite requests. Check for cache invalidation issues."
        )
    
    if not recommendations:
        recommendations.append("Cache performance is optimal.")
    
    return recommendations