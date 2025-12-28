"""Admin utilities for API key management and security monitoring."""

import json
import logging
from typing import Dict, Any, List
from datetime import datetime

from .security import get_auth_failure_stats, AUTH_FAILURE_LOG

logger = logging.getLogger(__name__)


def handle_admin_request(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle admin requests for security monitoring and API key management.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        Admin response with security statistics or API key operations
    """
    request_id = event.get('requestContext', {}).get('requestId', 'unknown')
    path = event.get('path', '')
    method = event.get('httpMethod', 'GET')
    
    logger.info(
        "Admin request received",
        extra={
            "request_id": request_id,
            "path": path,
            "method": method
        }
    )
    
    try:
        if path.endswith('/auth-stats'):
            return _handle_auth_stats_request(request_id)
        elif path.endswith('/rate-limit-stats'):
            return _handle_rate_limit_stats_request(request_id)
        elif path.endswith('/security-log'):
            return _handle_security_log_request(request_id, event)
        else:
            return _create_admin_error_response(
                404,
                "NotFound",
                "Admin endpoint not found",
                request_id
            )
    
    except Exception as e:
        logger.error(
            "Admin request failed",
            extra={
                "request_id": request_id,
                "error": str(e),
                "path": path
            }
        )
        return _create_admin_error_response(
            500,
            "InternalError",
            "Admin request failed",
            request_id
        )


def _handle_auth_stats_request(request_id: str) -> Dict[str, Any]:
    """Handle authentication statistics request."""
    try:
        stats = get_auth_failure_stats()
        
        logger.info(
            "Authentication stats requested",
            extra={
                "request_id": request_id,
                "total_failures": stats['total_failures'],
                "recent_failures": stats['recent_failures']
            }
        )
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "X-Request-ID": request_id
            },
            "body": json.dumps({
                "auth_failure_stats": stats,
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": request_id
            })
        }
    
    except Exception as e:
        logger.error(
            "Failed to get auth stats",
            extra={"request_id": request_id, "error": str(e)}
        )
        return _create_admin_error_response(
            500,
            "InternalError",
            "Failed to retrieve authentication statistics",
            request_id
        )


def _handle_rate_limit_stats_request(request_id: str) -> Dict[str, Any]:
    """Handle rate limit statistics request."""
    try:
        from .security import RATE_LIMIT_STORE
        
        # Calculate rate limit statistics
        active_clients = len(RATE_LIMIT_STORE)
        total_requests = sum(
            len(record['requests']) 
            for record in RATE_LIMIT_STORE.values()
        )
        
        # Get top clients by request count
        client_stats = []
        for client_id, record in RATE_LIMIT_STORE.items():
            client_stats.append({
                'client_id': client_id[:8] + '...',  # Partial ID for privacy
                'request_count': len(record['requests']),
                'first_request': datetime.fromtimestamp(record['first_request']).isoformat()
            })
        
        # Sort by request count
        client_stats.sort(key=lambda x: x['request_count'], reverse=True)
        top_clients = client_stats[:10]
        
        stats = {
            'active_clients': active_clients,
            'total_requests_in_window': total_requests,
            'top_clients': top_clients
        }
        
        logger.info(
            "Rate limit stats requested",
            extra={
                "request_id": request_id,
                "active_clients": active_clients,
                "total_requests": total_requests
            }
        )
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "X-Request-ID": request_id
            },
            "body": json.dumps({
                "rate_limit_stats": stats,
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": request_id
            })
        }
    
    except Exception as e:
        logger.error(
            "Failed to get rate limit stats",
            extra={"request_id": request_id, "error": str(e)}
        )
        return _create_admin_error_response(
            500,
            "InternalError",
            "Failed to retrieve rate limit statistics",
            request_id
        )


def _handle_security_log_request(request_id: str, event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle security log request with optional filtering."""
    try:
        # Parse query parameters for filtering
        query_params = event.get('queryStringParameters') or {}
        limit = int(query_params.get('limit', 100))
        failure_type = query_params.get('type')
        
        # Filter and limit log entries
        filtered_log = AUTH_FAILURE_LOG.copy()
        
        if failure_type:
            filtered_log = [
                entry for entry in filtered_log
                if entry['failure_type'] == failure_type
            ]
        
        # Sort by timestamp (most recent first) and limit
        filtered_log.sort(key=lambda x: x['timestamp'], reverse=True)
        filtered_log = filtered_log[:limit]
        
        # Anonymize IP addresses for privacy
        for entry in filtered_log:
            ip = entry['source_ip']
            if '.' in ip:  # IPv4
                parts = ip.split('.')
                entry['source_ip'] = f"{parts[0]}.{parts[1]}.xxx.xxx"
            elif ':' in ip:  # IPv6
                parts = ip.split(':')
                entry['source_ip'] = f"{parts[0]}:{parts[1]}:xxxx:xxxx:xxxx:xxxx:xxxx:xxxx"
        
        logger.info(
            "Security log requested",
            extra={
                "request_id": request_id,
                "total_entries": len(AUTH_FAILURE_LOG),
                "filtered_entries": len(filtered_log),
                "failure_type_filter": failure_type
            }
        )
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "X-Request-ID": request_id
            },
            "body": json.dumps({
                "security_log": filtered_log,
                "total_entries": len(AUTH_FAILURE_LOG),
                "filtered_entries": len(filtered_log),
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": request_id
            })
        }
    
    except Exception as e:
        logger.error(
            "Failed to get security log",
            extra={"request_id": request_id, "error": str(e)}
        )
        return _create_admin_error_response(
            500,
            "InternalError",
            "Failed to retrieve security log",
            request_id
        )


def _create_admin_error_response(
    status_code: int,
    error_type: str,
    message: str,
    request_id: str
) -> Dict[str, Any]:
    """Create standardized admin error response."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "X-Request-ID": request_id
        },
        "body": json.dumps({
            "error": {
                "type": error_type,
                "message": message,
                "request_id": request_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        })
    }


def generate_test_api_key() -> str:
    """Generate a test API key for development/testing purposes."""
    import secrets
    import string
    
    # Generate a secure random key
    alphabet = string.ascii_letters + string.digits + '-_'
    key_suffix = ''.join(secrets.choice(alphabet) for _ in range(28))
    
    return f"gcse-{key_suffix}"


def validate_api_key_strength(api_key: str) -> Dict[str, Any]:
    """Validate API key strength and provide recommendations.
    
    Args:
        api_key: API key to validate
        
    Returns:
        Validation result with strength score and recommendations
    """
    issues = []
    score = 100
    
    # Check length
    if len(api_key) < 32:
        issues.append("API key should be at least 32 characters long")
        score -= 30
    elif len(api_key) < 40:
        issues.append("Consider using a longer API key (40+ characters)")
        score -= 10
    
    # Check character diversity
    has_upper = any(c.isupper() for c in api_key)
    has_lower = any(c.islower() for c in api_key)
    has_digit = any(c.isdigit() for c in api_key)
    has_special = any(c in '-_' for c in api_key)
    
    char_types = sum([has_upper, has_lower, has_digit, has_special])
    if char_types < 3:
        issues.append("API key should contain uppercase, lowercase, digits, and special characters")
        score -= 20
    
    # Check for common patterns
    if api_key.lower().startswith('test') or api_key.lower().startswith('demo'):
        issues.append("Avoid using predictable prefixes like 'test' or 'demo' in production")
        score -= 15
    
    # Check for repeated patterns
    if len(set(api_key)) < len(api_key) * 0.7:
        issues.append("API key has too many repeated characters")
        score -= 25
    
    strength = "Strong"
    if score < 60:
        strength = "Weak"
    elif score < 80:
        strength = "Medium"
    
    return {
        "strength": strength,
        "score": max(0, score),
        "issues": issues,
        "recommendations": [
            "Use a cryptographically secure random generator",
            "Include uppercase, lowercase, digits, and special characters",
            "Use at least 40 characters for production keys",
            "Avoid predictable patterns or dictionary words"
        ] if issues else []
    }