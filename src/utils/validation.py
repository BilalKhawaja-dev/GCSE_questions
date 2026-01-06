"""Input validation and sanitization utilities."""

import re
import html
import urllib.parse
from typing import Dict, Any, List
from .constants import (
    MAX_QUERY_LENGTH, 
    MIN_QUESTION_COUNT, 
    MAX_QUESTION_COUNT,
    SQL_INJECTION_PATTERNS,
    XSS_PATTERNS,
    MALICIOUS_CONTENT_PATTERNS,
    VALID_TIERS
)


def validate_query_input(query: str) -> Dict[str, Any]:
    """Validate natural language query input.
    
    Args:
        query: Natural language query string
        
    Returns:
        Dict with validation result and any errors
        
    Raises:
        ValueError: If query fails validation
    """
    errors = []
    
    # Check length
    if len(query) > MAX_QUERY_LENGTH:
        errors.append(f"Query too long. Maximum {MAX_QUERY_LENGTH} characters allowed.")
    
    if len(query.strip()) == 0:
        errors.append("Query cannot be empty.")
    
    # Check for malicious content
    malicious_patterns = detect_malicious_content(query)
    if malicious_patterns:
        errors.append(f"Query contains potentially malicious content: {', '.join(malicious_patterns)}")
    
    if errors:
        raise ValueError(f"Query validation failed: {'; '.join(errors)}")
    
    return {
        "valid": True,
        "sanitized_query": sanitize_input(query),
        "length": len(query)
    }


def sanitize_input(text: str) -> str:
    """Sanitize input text to prevent injection attacks.
    
    Args:
        text: Input text to sanitize
        
    Returns:
        Sanitized text safe for processing
    """
    if not text:
        return ""
    
    # HTML encode to prevent XSS
    text = html.escape(text)
    
    # URL decode to handle encoded malicious content
    text = urllib.parse.unquote(text)
    
    # Remove potential HTML/script tags (after HTML encoding)
    text = re.sub(r'&lt;[^&gt;]*&gt;', '', text)
    
    # Remove potential SQL injection characters
    text = re.sub(r'[\'";]', '', text)
    
    # Remove SQL comments
    text = re.sub(r'--.*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    
    # Remove JavaScript protocol handlers
    text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
    text = re.sub(r'vbscript:', '', text, flags=re.IGNORECASE)
    text = re.sub(r'data:', '', text, flags=re.IGNORECASE)
    
    # Remove event handlers
    text = re.sub(r'on\w+\s*=', '', text, flags=re.IGNORECASE)
    
    # Remove expression() CSS function
    text = re.sub(r'expression\s*\([^)]*\)', '', text, flags=re.IGNORECASE)
    
    # Normalize whitespace
    text = ' '.join(text.split())
    
    return text.strip()


def detect_malicious_content(text: str) -> List[str]:
    """Detect potentially malicious patterns in input text.
    
    Args:
        text: Text to analyze
        
    Returns:
        List of detected malicious pattern types
    """
    detected_patterns = []
    
    # Check for SQL injection patterns
    for pattern in SQL_INJECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            detected_patterns.append("SQL injection")
            break
    
    # Check for XSS patterns
    for pattern in XSS_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            detected_patterns.append("XSS")
            break
    
    # Check for other malicious content patterns
    for pattern in MALICIOUS_CONTENT_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            detected_patterns.append("malicious code")
            break
    
    return detected_patterns


def validate_api_key(api_key: str) -> bool:
    """Validate API key format and structure.
    
    Args:
        api_key: API key to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not api_key:
        return False
    
    # Check minimum length
    if len(api_key) < 32:
        return False
    
    # Check for valid characters (alphanumeric and hyphens)
    if not re.match(r'^[a-zA-Z0-9\-_]+$', api_key):
        return False
    
    return True


def sanitize_json_input(data: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize JSON input data recursively.
    
    Args:
        data: Dictionary containing input data
        
    Returns:
        Sanitized dictionary
    """
    if not isinstance(data, dict):
        return data
    
    sanitized = {}
    for key, value in data.items():
        # Sanitize key
        clean_key = sanitize_input(str(key))
        
        # Sanitize value based on type
        if isinstance(value, str):
            sanitized[clean_key] = sanitize_input(value)
        elif isinstance(value, dict):
            sanitized[clean_key] = sanitize_json_input(value)
        elif isinstance(value, list):
            sanitized[clean_key] = [
                sanitize_input(item) if isinstance(item, str) else item
                for item in value
            ]
        else:
            sanitized[clean_key] = value
    
    return sanitized


def validate_email(email: str) -> bool:
    """Validate email format.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if valid email format, False otherwise
    """
    if not email:
        return False
    
    # Basic email regex pattern
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_pattern, email) is not None


def validate_username(username: str) -> tuple[bool, str]:
    """Validate username format and requirements.
    
    Args:
        username: Username to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not username:
        return False, "Username is required"
    
    if len(username) < 3:
        return False, "Username must be at least 3 characters long"
    
    if len(username) > 50:
        return False, "Username must be less than 50 characters long"
    
    # Check for valid characters (alphanumeric and underscore only)
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False, "Username can only contain letters, numbers, and underscores"
    
    return True, "Username is valid"


def validate_password(password: str) -> tuple[bool, str]:
    """Validate password strength.
    
    Args:
        password: Password to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not password:
        return False, "Password is required"
    
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if len(password) > 128:
        return False, "Password must be less than 128 characters long"
    
    # Check for at least one uppercase letter
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    # Check for at least one lowercase letter
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    # Check for at least one digit
    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit"
    
    # Check for at least one special character
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    
    return True, "Password is valid"


def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> Dict[str, Any]:
    """
    Validate that all required fields are present in the data.
    
    Args:
        data: Dictionary containing the data to validate
        required_fields: List of required field names
        
    Returns:
        Dictionary with validation result and missing fields
    """
    missing_fields = []
    
    for field in required_fields:
        if field not in data or data[field] is None or (isinstance(data[field], str) and not data[field].strip()):
            missing_fields.append(field)
    
    return {
        'valid': len(missing_fields) == 0,
        'missing_fields': missing_fields
    }


def validate_generation_request(topic: str = None, tier: str = None, count: int = None, 
                              specification_version: str = "latest", request_body: Dict[str, Any] = None) -> Dict[str, Any]:
    """Validate question generation request parameters.
    
    Args:
        topic: Topic for question generation (or None if using request_body)
        tier: Tier level (Foundation/Higher) (or None if using request_body)
        count: Number of questions to generate (or None if using request_body)
        specification_version: Version of specification to use
        request_body: Request body containing generation parameters (alternative to individual params)
        
    Returns:
        Dict with validation result and sanitized request
        
    Raises:
        ValueError: If parameters fail validation
    """
    errors = []
    
    # Handle both parameter styles - individual params or request_body dict
    if request_body is not None:
        # Extract from request body
        topic = request_body.get('topic', '').strip() if request_body.get('topic') else None
        tier = request_body.get('tier', '').strip() if request_body.get('tier') else None
        count = request_body.get('count')
        specification_version = request_body.get('specification_version', 'latest').strip()
        subtopic = request_body.get('subtopic')
        marks = request_body.get('marks')
    else:
        # Use individual parameters
        topic = topic.strip() if topic else None
        tier = tier.strip() if tier else None
        subtopic = None
        marks = None
    
    # Validate topic (basic check - not empty)
    if not topic:
        errors.append("Topic is required and cannot be empty")
    
    # Validate tier
    if not tier:
        errors.append("Tier is required and cannot be empty")
    elif tier not in VALID_TIERS:
        errors.append(f"Invalid tier: {tier}. Must be one of {VALID_TIERS}")
    
    # Validate count
    if count is None:
        errors.append("Count is required")
    else:
        try:
            count = int(count)
            if not (MIN_QUESTION_COUNT <= count <= MAX_QUESTION_COUNT):
                errors.append(f"Invalid count: {count}. Must be between {MIN_QUESTION_COUNT} and {MAX_QUESTION_COUNT}")
        except (ValueError, TypeError):
            errors.append("Count must be a valid integer")
    
    # Validate specification version format
    if not specification_version:
        specification_version = "latest"
    
    if errors:
        raise ValueError(f"Generation request validation failed: {'; '.join(errors)}")
    
    # Return format expected by tests
    if request_body is not None:
        return {
            "valid": True,
            "generation_request": {
                "topic": topic,
                "tier": tier,
                "count": count,
                "specification_version": specification_version,
                "subtopic": subtopic,
                "marks": marks
            }
        }
    else:
        return {
            "valid": True,
            "topic": topic,
            "tier": tier,
            "count": count,
            "specification_version": specification_version
        }