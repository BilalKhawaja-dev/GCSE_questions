"""Security utilities for authentication and rate limiting."""

import time
import hashlib
import logging
import re
import json
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta

from .constants import (
    RATE_LIMIT_REQUESTS_PER_HOUR,
    RATE_LIMIT_WINDOW_SECONDS,
    API_KEY_HEADER,
    API_KEY_MIN_LENGTH,
    SQL_INJECTION_PATTERNS,
    XSS_PATTERNS,
    MALICIOUS_CONTENT_PATTERNS,
    MAX_QUERY_LENGTH
)

logger = logging.getLogger(__name__)

# In-memory rate limiting store (for Lambda warm containers)
# In production, this would be replaced with Redis or DynamoDB
RATE_LIMIT_STORE = {}
AUTH_FAILURE_LOG = []
BRUTE_FORCE_ATTEMPTS = {}  # Track failed login attempts by IP/username
BLOCKED_IPS = {}  # Track temporarily blocked IPs

# Security thresholds
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15
MAX_REQUESTS_PER_MINUTE = 60
SUSPICIOUS_ACTIVITY_THRESHOLD = 10


def validate_and_sanitize_input(input_data: Any, input_type: str = "general") -> Tuple[bool, str, Any]:
    """Validate and sanitize user input to prevent injection attacks.
    
    Args:
        input_data: The input data to validate
        input_type: Type of input (query, username, email, etc.)
        
    Returns:
        Tuple of (is_valid, error_message, sanitized_data)
    """
    if input_data is None:
        return False, "Input cannot be null", None
    
    # Convert to string for validation
    input_str = str(input_data)
    
    # Check for basic length limits
    if input_type == "query" and len(input_str) > MAX_QUERY_LENGTH:
        return False, f"Query too long (max {MAX_QUERY_LENGTH} characters)", None
    
    if input_type == "username" and (len(input_str) < 3 or len(input_str) > 50):
        return False, "Username must be 3-50 characters", None
    
    if input_type == "email" and len(input_str) > 254:
        return False, "Email address too long", None
    
    # Check for SQL injection patterns
    for pattern in SQL_INJECTION_PATTERNS:
        if re.search(pattern, input_str, re.IGNORECASE):
            log_security_event("sql_injection_attempt", {"input": input_str[:100], "pattern": pattern})
            return False, "Invalid input detected", None
    
    # Check for XSS patterns
    for pattern in XSS_PATTERNS:
        if re.search(pattern, input_str, re.IGNORECASE):
            log_security_event("xss_attempt", {"input": input_str[:100], "pattern": pattern})
            return False, "Invalid input detected", None
    
    # Check for malicious content patterns
    for pattern in MALICIOUS_CONTENT_PATTERNS:
        if re.search(pattern, input_str, re.IGNORECASE):
            log_security_event("malicious_content_attempt", {"input": input_str[:100], "pattern": pattern})
            return False, "Invalid input detected", None
    
    # Sanitize the input
    sanitized_input = sanitize_string(input_str, input_type)
    
    # Type-specific validation
    if input_type == "email":
        if not _validate_email_format(sanitized_input):
            return False, "Invalid email format", None
    
    elif input_type == "username":
        if not _validate_username_format(sanitized_input):
            return False, "Username contains invalid characters", None
    
    elif input_type == "query":
        if not _validate_query_content(sanitized_input):
            return False, "Query contains invalid content", None
    
    return True, "", sanitized_input


def sanitize_string(input_str: str, input_type: str = "general") -> str:
    """Sanitize string input by removing/escaping dangerous characters.
    
    Args:
        input_str: String to sanitize
        input_type: Type of input for context-specific sanitization
        
    Returns:
        Sanitized string
    """
    if not input_str:
        return ""
    
    # Remove null bytes
    sanitized = input_str.replace('\x00', '')
    
    # Remove control characters except newlines and tabs for queries
    if input_type == "query":
        sanitized = re.sub(r'[\x01-\x08\x0B\x0C\x0E-\x1F\x7F]', '', sanitized)
    else:
        sanitized = re.sub(r'[\x00-\x1F\x7F]', '', sanitized)
    
    # Normalize whitespace
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    
    # For usernames, only allow alphanumeric, underscore, hyphen
    if input_type == "username":
        sanitized = re.sub(r'[^a-zA-Z0-9_-]', '', sanitized)
    
    # For emails, basic sanitization
    elif input_type == "email":
        sanitized = sanitized.lower().strip()
    
    return sanitized


def _validate_email_format(email: str) -> bool:
    """Validate email format using regex."""
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(email_pattern, email))


def _validate_username_format(username: str) -> bool:
    """Validate username format."""
    # Allow alphanumeric, underscore, hyphen
    username_pattern = r'^[a-zA-Z0-9_-]+$'
    return bool(re.match(username_pattern, username))


def _validate_query_content(query: str) -> bool:
    """Validate query content for educational appropriateness."""
    # Check for minimum meaningful content
    if len(query.strip()) < 3:
        return False
    
    # Check for excessive special characters
    special_char_count = len(re.findall(r'[^a-zA-Z0-9\s]', query))
    if special_char_count > len(query) * 0.3:  # More than 30% special chars
        return False
    
    return True


def check_brute_force_protection(identifier: str, identifier_type: str = "ip") -> Tuple[bool, Dict[str, Any]]:
    """Check if identifier is blocked due to brute force attempts.
    
    Args:
        identifier: IP address, username, or other identifier
        identifier_type: Type of identifier (ip, username, etc.)
        
    Returns:
        Tuple of (is_allowed, block_info)
    """
    current_time = time.time()
    
    # Clean up old blocked entries
    _cleanup_blocked_entries(current_time)
    
    # Check if currently blocked
    block_key = f"{identifier_type}:{identifier}"
    if block_key in BLOCKED_IPS:
        block_info = BLOCKED_IPS[block_key]
        if current_time < block_info['blocked_until']:
            remaining_time = int(block_info['blocked_until'] - current_time)
            return False, {
                'blocked': True,
                'reason': 'brute_force_protection',
                'remaining_seconds': remaining_time,
                'attempts': block_info['attempts']
            }
        else:
            # Block expired, remove it
            del BLOCKED_IPS[block_key]
    
class RateLimiter:
    """Enhanced rate limiter for API requests with multiple tiers."""
    
    def __init__(self, max_requests: int = RATE_LIMIT_REQUESTS_PER_HOUR, 
                 window_seconds: int = RATE_LIMIT_WINDOW_SECONDS,
                 burst_limit: int = None):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.burst_limit = burst_limit or max_requests // 10  # 10% of hourly limit for burst
    
    def is_allowed(self, client_id: str, request_weight: int = 1) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is allowed under rate limit.
        
        Args:
            client_id: Unique identifier for the client (API key hash or user ID)
            request_weight: Weight of the request (default 1, higher for expensive operations)
            
        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        current_time = time.time()
        
        try:
            # Clean up old entries
            self._cleanup_old_entries(current_time)
            
            # Get or create client record
            if client_id not in RATE_LIMIT_STORE:
                RATE_LIMIT_STORE[client_id] = {
                    'requests': [],
                    'first_request': current_time,
                    'total_weight': 0
                }
            
            client_record = RATE_LIMIT_STORE[client_id]
            
            # Ensure client_record has required fields (handle corrupted data)
            if 'requests' not in client_record:
                client_record['requests'] = []
            if 'first_request' not in client_record:
                client_record['first_request'] = current_time
            if 'total_weight' not in client_record:
                client_record['total_weight'] = 0
            
            # Remove requests outside the window
            window_start = current_time - self.window_seconds
            valid_requests = []
            total_weight = 0
            
            for req in client_record['requests']:
                try:
                    # Handle both tuple format (req_time, weight) and old format (just req_time)
                    if isinstance(req, (list, tuple)) and len(req) >= 2:
                        req_time, weight = req[0], req[1]
                    elif isinstance(req, (int, float)):
                        req_time, weight = req, 1
                    else:
                        continue  # Skip invalid entries
                    
                    if req_time > window_start:
                        valid_requests.append((req_time, weight))
                        total_weight += weight
                except (TypeError, ValueError):
                    continue  # Skip malformed entries
            
            client_record['requests'] = valid_requests
            client_record['total_weight'] = total_weight
            
            # Check burst limit (last minute)
            minute_start = current_time - 60
            recent_requests = [req for req in valid_requests if req[0] > minute_start]
            
            if len(recent_requests) >= MAX_REQUESTS_PER_MINUTE:
                return False, self._get_rate_limit_info(client_record, current_time, "burst_limit_exceeded")
            
            # Check main rate limit
            is_allowed = (total_weight + request_weight) <= self.max_requests
            
            if is_allowed:
                # Add current request
                client_record['requests'].append((current_time, request_weight))
                client_record['total_weight'] += request_weight
            
            return is_allowed, self._get_rate_limit_info(client_record, current_time, 
                                                       "allowed" if is_allowed else "rate_limit_exceeded")
        except Exception as e:
            # If rate limiting fails, log and allow the request (fail open for availability)
            logger.warning(f"Rate limiter error, allowing request: {str(e)}")
            # Reset the client record to prevent future errors
            if client_id in RATE_LIMIT_STORE:
                del RATE_LIMIT_STORE[client_id]
            return True, {
                'limit': self.max_requests,
                'remaining': self.max_requests - 1,
                'reset': int(current_time + self.window_seconds),
                'retry_after': 0,
                'status': 'allowed_on_error',
                'window_seconds': self.window_seconds
            }
    
    def _get_rate_limit_info(self, client_record: Dict, current_time: float, status: str) -> Dict[str, Any]:
        """Generate rate limit information for response headers."""
        # Calculate reset time
        if client_record['requests']:
            oldest_request_time = min(req_time for req_time, _ in client_record['requests'])
            reset_time = oldest_request_time + self.window_seconds
        else:
            reset_time = current_time + self.window_seconds
        
        remaining = max(0, self.max_requests - client_record['total_weight'])
        
        return {
            'limit': self.max_requests,
            'remaining': remaining,
            'reset': int(reset_time),
            'retry_after': int(reset_time - current_time) if status != "allowed" else 0,
            'status': status,
            'window_seconds': self.window_seconds
        }
    
    def _cleanup_old_entries(self, current_time: float):
        """Clean up old rate limit entries to prevent memory leaks."""
        cutoff_time = current_time - (self.window_seconds * 2)  # Keep some buffer
        
        clients_to_remove = []
        for client_id, record in list(RATE_LIMIT_STORE.items()):
            try:
                # Ensure record has requests list
                if 'requests' not in record:
                    record['requests'] = []
                    continue
                
                # Remove old requests, handling both tuple and scalar formats
                valid_requests = []
                for req in record['requests']:
                    try:
                        if isinstance(req, (list, tuple)) and len(req) >= 2:
                            req_time = req[0]
                        elif isinstance(req, (int, float)):
                            req_time = req
                        else:
                            continue
                        
                        if req_time > cutoff_time:
                            # Normalize to tuple format
                            if isinstance(req, (list, tuple)) and len(req) >= 2:
                                valid_requests.append((req[0], req[1]))
                            else:
                                valid_requests.append((req_time, 1))
                    except (TypeError, ValueError):
                        continue
                
                record['requests'] = valid_requests
                
                # Recalculate total weight
                record['total_weight'] = sum(weight for _, weight in valid_requests)
                
                # Mark client for removal if no recent requests
                first_request = record.get('first_request', current_time)
                if not valid_requests and first_request < cutoff_time:
                    clients_to_remove.append(client_id)
            except Exception as e:
                # If record is corrupted, mark for removal
                logger.warning(f"Removing corrupted rate limit record for {client_id}: {str(e)}")
                clients_to_remove.append(client_id)
        
        # Remove inactive or corrupted clients
        for client_id in clients_to_remove:
            try:
                del RATE_LIMIT_STORE[client_id]
            except KeyError:
                pass


def check_rate_limit_with_weight(identifier: str, request_weight: int = 1) -> Tuple[bool, Dict[str, Any]]:
    """Check rate limit for client or user with request weighting.
    
    Args:
        identifier: Client ID or User ID for rate limiting
        request_weight: Weight of the request (higher for expensive operations)
        
    Returns:
        Tuple of (is_allowed, rate_limit_headers)
    """
    rate_limiter = RateLimiter()
    is_allowed, rate_info = rate_limiter.is_allowed(identifier, request_weight)
    
    # Prepare headers for response
    rate_limit_headers = {
        'X-RateLimit-Limit': str(rate_info['limit']),
        'X-RateLimit-Remaining': str(rate_info['remaining']),
        'X-RateLimit-Reset': str(rate_info['reset']),
        'X-RateLimit-Window': str(rate_info['window_seconds'])
    }
    
    if not is_allowed:
        rate_limit_headers['Retry-After'] = str(rate_info['retry_after'])
        rate_limit_headers['X-RateLimit-Status'] = rate_info['status']
    
    return is_allowed, rate_limit_headers


def record_failed_attempt(identifier: str, identifier_type: str = "ip", failure_type: str = "login"):
    """Record a failed authentication attempt.
    
    Args:
        identifier: IP address, username, or other identifier
        identifier_type: Type of identifier (ip, username, etc.)
        failure_type: Type of failure (login, api_key, etc.)
    """
    current_time = time.time()
    attempt_key = f"{identifier_type}:{identifier}"
    
    # Initialize or update attempt record
    if attempt_key not in BRUTE_FORCE_ATTEMPTS:
        BRUTE_FORCE_ATTEMPTS[attempt_key] = {
            'attempts': [],
            'total_attempts': 0
        }
    
    attempt_record = BRUTE_FORCE_ATTEMPTS[attempt_key]
    
    # Add current attempt
    attempt_record['attempts'].append({
        'timestamp': current_time,
        'failure_type': failure_type
    })
    attempt_record['total_attempts'] += 1
    
    # Remove attempts older than lockout window
    window_start = current_time - (LOCKOUT_DURATION_MINUTES * 60)
    attempt_record['attempts'] = [
        attempt for attempt in attempt_record['attempts']
        if attempt['timestamp'] > window_start
    ]
    
    # Check if should be blocked
    recent_attempts = len(attempt_record['attempts'])
    if recent_attempts >= MAX_LOGIN_ATTEMPTS:
        # Block the identifier
        block_key = f"{identifier_type}:{identifier}"
        BLOCKED_IPS[block_key] = {
            'blocked_until': current_time + (LOCKOUT_DURATION_MINUTES * 60),
            'attempts': recent_attempts,
            'first_attempt': attempt_record['attempts'][0]['timestamp'],
            'block_reason': 'excessive_failed_attempts'
        }
        
        # Log security event
        log_security_event("brute_force_block", {
            "identifier": identifier,
            "identifier_type": identifier_type,
            "attempts": recent_attempts,
            "block_duration_minutes": LOCKOUT_DURATION_MINUTES
        })


def _cleanup_blocked_entries(current_time: float):
    """Clean up expired blocked entries."""
    expired_blocks = [
        block_key for block_key, block_info in BLOCKED_IPS.items()
        if current_time >= block_info['blocked_until']
    ]
    
    for block_key in expired_blocks:
        del BLOCKED_IPS[block_key]


def log_security_event(event_type: str, event_data: Dict[str, Any]):
    """Log security events for monitoring and alerting.
    
    Args:
        event_type: Type of security event
        event_data: Additional event data
    """
    security_event = {
        'timestamp': datetime.utcnow().isoformat(),
        'event_type': event_type,
        'event_data': event_data
    }
    
    # Log to CloudWatch with structured format
    logger.warning(
        f"Security Event: {event_type}",
        extra={
            "security_event": True,
            "event_type": event_type,
            "event_data": event_data,
            "timestamp": security_event['timestamp']
        }
    )


def get_security_headers() -> Dict[str, str]:
    """Get security headers to include in API responses."""
    return {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
        'Referrer-Policy': 'strict-origin-when-cross-origin'
    }


def validate_cors_origin(origin: str, allowed_origins: List[str]) -> bool:
    """Validate CORS origin against allowed list.
    
    Args:
        origin: Origin header from request
        allowed_origins: List of allowed origins
        
    Returns:
        True if origin is allowed
    """
    if not origin:
        return False
    
    # Check exact matches
    if origin in allowed_origins:
        return True
    
    # Check wildcard patterns
    for allowed_origin in allowed_origins:
        if allowed_origin == "*":
            return True
        if allowed_origin.startswith("*."):
            domain = allowed_origin[2:]
            if origin.endswith(f".{domain}") or origin == domain:
                return True
    
    return False
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


def authenticate_request(event: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """Authenticate API request using session token or API key.
    
    Args:
        event: API Gateway event
        
    Returns:
        Tuple of (is_authenticated, auth_info, error_message)
        auth_info contains: {'user_id': str, 'session_token': str} for session auth
                           or {'client_id': str} for API key auth
    """
    # Extract client IP for brute force protection
    source_ip = event.get('requestContext', {}).get('identity', {}).get('sourceIp', 'unknown')
    request_id = event.get('requestContext', {}).get('requestId', 'unknown')
    
    # Check brute force protection
    ip_allowed, block_info = check_brute_force_protection(source_ip, "ip")
    if not ip_allowed:
        log_auth_failure(request_id, 'ip_blocked', source_ip, {
            'block_reason': block_info.get('reason'),
            'remaining_seconds': block_info.get('remaining_seconds')
        })
        return False, None, f"IP temporarily blocked. Try again in {block_info.get('remaining_seconds', 0)} seconds"
    
    # Validate input data
    headers = event.get('headers', {})
    
    # Sanitize and validate headers
    for header_name, header_value in headers.items():
        if header_value:
            is_valid, error_msg, _ = validate_and_sanitize_input(header_value, "general")
            if not is_valid:
                log_security_event("invalid_header", {
                    "header_name": header_name,
                    "source_ip": source_ip,
                    "error": error_msg
                })
                record_failed_attempt(source_ip, "ip", "invalid_header")
                return False, None, "Invalid request headers"
    
    # Check for session token first (for authenticated users)
    session_token = None
    for header_name in ['Authorization', 'authorization', 'X-Session-Token', 'x-session-token']:
        if header_name in headers:
            auth_header = headers[header_name]
            if auth_header.startswith('Bearer '):
                session_token = auth_header[7:]  # Remove 'Bearer ' prefix
            elif header_name.lower().endswith('session-token'):
                session_token = auth_header
            break
    
    if session_token:
        # Validate session token format
        is_valid, error_msg, sanitized_token = validate_and_sanitize_input(session_token, "general")
        if not is_valid:
            record_failed_attempt(source_ip, "ip", "invalid_session_token_format")
            return False, None, "Invalid session token format"
        
        # Validate session token with AuthService
        try:
            from src.services.auth_service import AuthService
            auth_service = AuthService()
            
            validation_result = auth_service.validate_session_token(sanitized_token)
            if validation_result['valid']:
                return True, {
                    'user_id': validation_result['user_id'],
                    'session_token': sanitized_token
                }, None
            else:
                record_failed_attempt(source_ip, "ip", "invalid_session_token")
                log_auth_failure(request_id, 'invalid_session_token', source_ip)
                return False, None, "Invalid or expired session token"
                
        except Exception as e:
            logger.error(f"Session token validation failed: {str(e)}")
            record_failed_attempt(source_ip, "ip", "auth_service_error")
            return False, None, "Authentication service error"
    
    # Fall back to API key authentication
    api_key = None
    for header_name in [API_KEY_HEADER, API_KEY_HEADER.lower(), 'x-api-key']:
        if header_name in headers:
            api_key = headers[header_name]
            break
    
    if not api_key:
        record_failed_attempt(source_ip, "ip", "missing_auth")
        log_auth_failure(request_id, 'missing_auth', source_ip)
        return False, None, "Missing session token or API key"
    
    # Validate and sanitize API key
    is_valid, error_msg, sanitized_key = validate_and_sanitize_input(api_key, "general")
    if not is_valid:
        record_failed_attempt(source_ip, "ip", "invalid_api_key_format")
        return False, None, "Invalid API key format"
    
    # Validate API key format
    if not _validate_api_key_format(sanitized_key):
        record_failed_attempt(source_ip, "ip", "invalid_api_key_format")
        log_auth_failure(request_id, 'invalid_api_key_format', source_ip)
        return False, None, "Invalid API key format"
    
    # Check API key validity
    if not _is_valid_api_key(sanitized_key):
        record_failed_attempt(source_ip, "ip", "invalid_api_key")
        log_auth_failure(request_id, 'invalid_api_key', source_ip)
        return False, None, "Invalid API key"
    
    # Create client ID from API key hash (for rate limiting)
    client_id = hashlib.sha256(sanitized_key.encode()).hexdigest()[:16]
    
    return True, {'client_id': client_id}, None


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


def log_auth_failure(request_id: str, failure_type: str, source_ip: str, additional_context: Optional[Dict[str, Any]] = None):
    """Log authentication failure for security monitoring.
    
    Args:
        request_id: Request ID for tracking
        failure_type: Type of authentication failure
        source_ip: Source IP address
        additional_context: Additional context information
    """
    failure_record = {
        'timestamp': datetime.utcnow().isoformat(),
        'request_id': request_id,
        'failure_type': failure_type,
        'source_ip': source_ip,
        'additional_context': additional_context or {}
    }
    
    # Add to in-memory log (in production, this would go to CloudWatch or security system)
    AUTH_FAILURE_LOG.append(failure_record)
    
    # Keep only recent failures to prevent memory issues
    if len(AUTH_FAILURE_LOG) > 1000:
        AUTH_FAILURE_LOG[:] = AUTH_FAILURE_LOG[-500:]
    
    # Log to CloudWatch with enhanced context
    logger.warning(
        "Authentication failure",
        extra={
            "request_id": request_id,
            "failure_type": failure_type,
            "source_ip": source_ip,
            "timestamp": failure_record['timestamp'],
            "additional_context": additional_context or {},
            "security_alert": True
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


def check_rate_limit(identifier: str) -> Tuple[bool, Dict[str, Any]]:
    """Check rate limit for client or user.
    
    Args:
        identifier: Client ID or User ID for rate limiting
        
    Returns:
        Tuple of (is_allowed, rate_limit_headers)
    """
    rate_limiter = RateLimiter()
    is_allowed, rate_info = rate_limiter.is_allowed(identifier)
    
    # Prepare headers for response
    rate_limit_headers = {
        'X-RateLimit-Limit': str(rate_info['limit']),
        'X-RateLimit-Remaining': str(rate_info['remaining']),
        'X-RateLimit-Reset': str(rate_info['reset'])
    }
    
    if not is_allowed:
        rate_limit_headers['Retry-After'] = str(rate_info['retry_after'])
    
    return is_allowed, rate_limit_headers


def get_cors_headers(environment: str = None) -> Dict[str, str]:
    """Get CORS headers based on environment.
    
    Args:
        environment: Environment name (prod, dev, etc.)
        
    Returns:
        Dictionary of CORS headers
    """
    import os
    
    # Get environment from parameter or environment variable
    env = environment or os.environ.get('ENVIRONMENT', 'dev')
    
    # Set origin based on environment
    if env == 'prod':
        origin = 'https://d2ckebo851nz2l.cloudfront.net'
    else:
        origin = 'http://localhost:3000'
    
    return {
        'Access-Control-Allow-Origin': origin,
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Session-Token',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
        'Access-Control-Allow-Credentials': 'true'
    }


def get_cors_response_headers(environment: str = None, methods: str = None) -> Dict[str, str]:
    """Get CORS response headers for Lambda functions.
    
    Args:
        environment: Environment name (prod, dev, etc.)
        methods: Allowed methods (defaults to GET,POST,OPTIONS)
        
    Returns:
        Dictionary of CORS response headers
    """
    cors_headers = get_cors_headers(environment)
    
    # Override methods if specified
    if methods:
        cors_headers['Access-Control-Allow-Methods'] = methods
    
    return cors_headers