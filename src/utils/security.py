"""Security utilities for authentication and rate limiting."""

import time
import hashlib
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

from .constants import (
    RATE_LIMIT_REQUESTS_PER_HOUR,
    RATE_LIMIT_WINDOW_SECONDS,
    API_KEY_HEADER,
    API_KEY_MIN_LENGTH
)

logger = logging.getLogger(__name__)

# In-memory rate limiting store (for Lambda warm containers)
# In production, this would be replaced with Redis or DynamoDB
RATE_LIMIT_STORE = {}
AUTH_FAILURE_LOG = []


class RateLimiter:
    """Rate limiter for API requests."""
    
    def __init__(self, max_requests: int = RATE_LIMIT_REQUESTS_PER_HOUR, 
                 window_seconds: int = RATE_LIMIT_WINDOW_SECONDS):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
    
    def is_allowed(self, client_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is allowed under rate limit.
        
        Args:
            client_id: Unique identifier for the client (API key hash)
            
        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        current_time = time.time()
        
        # Clean up old entries
        self._cleanup_old_entries(current_time)
        
        # Get or create client record
        if client_id not in RATE_LIMIT_STORE:
            RATE_LIMIT_STORE[client_id] = {
                'requests': [],
                'first_request': current_time
            }
        
        client_record = RATE_LIMIT_STORE[client_id]
        
        # Remove requests outside the window
        window_start = current_time - self.window_seconds
        client_record['requests'] = [
            req_time for req_time in client_record['requests']
            if req_time > window_start
        ]
        
        # Check if limit exceeded
        current_count = len(client_record['requests'])
        is_allowed = current_count < self.max_requests
        
        if is_allowed:
            # Add current request
            client_record['requests'].append(current_time)
        
        # Calculate reset time
        if client_record['requests']:
            oldest_request = min(client_record['requests'])
            reset_time = oldest_request + self.window_seconds
        else:
            reset_time = current_time + self.window_seconds
        
        rate_limit_info = {
            'limit': self.max_requests,
            'remaining': max(0, self.max_requests - current_count - (1 if is_allowed else 0)),
            'reset': int(reset_time),
            'retry_after': int(reset_time - current_time) if not is_allowed else 0
        }
        
        return is_allowed, rate_limit_info
    
    def _cleanup_old_entries(self, current_time: float):
        """Clean up old rate limit entries to prevent memory leaks."""
        cutoff_time = current_time - (self.window_seconds * 2)  # Keep some buffer
        
        clients_to_remove = []
        for client_id, record in RATE_LIMIT_STORE.items():
            # Remove old requests
            record['requests'] = [
                req_time for req_time in record['requests']
                if req_time > cutoff_time
            ]
            
            # Mark client for removal if no recent requests
            if not record['requests'] and record['first_request'] < cutoff_time:
                clients_to_remove.append(client_id)
        
        # Remove inactive clients
        for client_id in clients_to_remove:
            del RATE_LIMIT_STORE[client_id]


def authenticate_request(event: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[str]]:
    """Authenticate API request using API key.
    
    Args:
        event: API Gateway event
        
    Returns:
        Tuple of (is_authenticated, client_id, error_message)
    """
    # Extract API key from headers
    headers = event.get('headers', {})
    
    # Check both X-API-Key and x-api-key (case insensitive)
    api_key = None
    for header_name in [API_KEY_HEADER, API_KEY_HEADER.lower(), 'x-api-key']:
        if header_name in headers:
            api_key = headers[header_name]
            break
    
    if not api_key:
        log_auth_failure(
            event.get('requestContext', {}).get('requestId', 'unknown'),
            'missing_api_key',
            event.get('requestContext', {}).get('identity', {}).get('sourceIp', 'unknown')
        )
        return False, None, "Missing API key"
    
    # Validate API key format
    if not _validate_api_key_format(api_key):
        log_auth_failure(
            event.get('requestContext', {}).get('requestId', 'unknown'),
            'invalid_api_key_format',
            event.get('requestContext', {}).get('identity', {}).get('sourceIp', 'unknown')
        )
        return False, None, "Invalid API key format"
    
    # In a real implementation, this would check against a database
    # For now, we'll use a simple validation approach
    if not _is_valid_api_key(api_key):
        log_auth_failure(
            event.get('requestContext', {}).get('requestId', 'unknown'),
            'invalid_api_key',
            event.get('requestContext', {}).get('identity', {}).get('sourceIp', 'unknown')
        )
        return False, None, "Invalid API key"
    
    # Create client ID from API key hash (for rate limiting)
    client_id = hashlib.sha256(api_key.encode()).hexdigest()[:16]
    
    return True, client_id, None


def _validate_api_key_format(api_key: str) -> bool:
    """Validate API key format."""
    if not api_key or len(api_key) < API_KEY_MIN_LENGTH:
        return False
    
    # Check for valid characters
    import re
    if not re.match(r'^[a-zA-Z0-9\-_]+$', api_key):
        return False
    
    return True


def _is_valid_api_key(api_key: str) -> bool:
    """Check if API key is valid.
    
    In production, this would check against a database or key management service.
    For testing/demo purposes, we'll accept keys that match a pattern.
    """
    # Demo implementation - accept keys starting with 'gcse-' and at least 32 chars
    if api_key.startswith('gcse-') and len(api_key) >= 32:
        return True
    
    # Accept test keys for development
    test_keys = [
        'test-api-key-12345678901234567890',
        'demo-api-key-12345678901234567890',
        'gcse-demo-key-1234567890123456789'
    ]
    
    return api_key in test_keys


def log_auth_failure(request_id: str, failure_type: str, source_ip: str):
    """Log authentication failure for security monitoring.
    
    Args:
        request_id: Request ID for tracking
        failure_type: Type of authentication failure
        source_ip: Source IP address
    """
    failure_record = {
        'timestamp': datetime.utcnow().isoformat(),
        'request_id': request_id,
        'failure_type': failure_type,
        'source_ip': source_ip
    }
    
    # Add to in-memory log (in production, this would go to CloudWatch or security system)
    AUTH_FAILURE_LOG.append(failure_record)
    
    # Keep only recent failures to prevent memory issues
    if len(AUTH_FAILURE_LOG) > 1000:
        AUTH_FAILURE_LOG[:] = AUTH_FAILURE_LOG[-500:]
    
    # Log to CloudWatch
    logger.warning(
        "Authentication failure",
        extra={
            "request_id": request_id,
            "failure_type": failure_type,
            "source_ip": source_ip,
            "timestamp": failure_record['timestamp']
        }
    )


def get_auth_failure_stats() -> Dict[str, Any]:
    """Get authentication failure statistics for monitoring."""
    if not AUTH_FAILURE_LOG:
        return {
            'total_failures': 0,
            'recent_failures': 0,
            'failure_types': {},
            'top_source_ips': {}
        }
    
    # Calculate stats for last 24 hours
    cutoff_time = datetime.utcnow() - timedelta(hours=24)
    recent_failures = [
        failure for failure in AUTH_FAILURE_LOG
        if datetime.fromisoformat(failure['timestamp']) > cutoff_time
    ]
    
    # Count failure types
    failure_types = {}
    source_ips = {}
    
    for failure in recent_failures:
        failure_type = failure['failure_type']
        source_ip = failure['source_ip']
        
        failure_types[failure_type] = failure_types.get(failure_type, 0) + 1
        source_ips[source_ip] = source_ips.get(source_ip, 0) + 1
    
    # Get top source IPs
    top_source_ips = dict(sorted(source_ips.items(), key=lambda x: x[1], reverse=True)[:10])
    
    return {
        'total_failures': len(AUTH_FAILURE_LOG),
        'recent_failures': len(recent_failures),
        'failure_types': failure_types,
        'top_source_ips': top_source_ips
    }


def check_rate_limit(client_id: str) -> Tuple[bool, Dict[str, Any]]:
    """Check rate limit for client.
    
    Args:
        client_id: Client identifier
        
    Returns:
        Tuple of (is_allowed, rate_limit_headers)
    """
    rate_limiter = RateLimiter()
    is_allowed, rate_info = rate_limiter.is_allowed(client_id)
    
    # Prepare headers for response
    rate_limit_headers = {
        'X-RateLimit-Limit': str(rate_info['limit']),
        'X-RateLimit-Remaining': str(rate_info['remaining']),
        'X-RateLimit-Reset': str(rate_info['reset'])
    }
    
    if not is_allowed:
        rate_limit_headers['Retry-After'] = str(rate_info['retry_after'])
    
    return is_allowed, rate_limit_headers