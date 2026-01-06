"""
Error handling utilities for robust system operation.

This module provides comprehensive error handling, retry logic, circuit breaker patterns,
and user-friendly error messaging for the GCSE Question Generator V2 system.
"""

import json
import logging
import time
import functools
from typing import Dict, Any, Optional, Callable, List, Union
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError, BotoCoreError

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Classification of error types for appropriate handling."""
    BEDROCK_API_ERROR = "bedrock_api_error"
    S3_ACCESS_ERROR = "s3_access_error"
    DYNAMODB_ERROR = "dynamodb_error"
    VALIDATION_ERROR = "validation_error"
    TIMEOUT_ERROR = "timeout_error"
    CIRCUIT_BREAKER_OPEN = "circuit_breaker_open"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class ErrorContext:
    """Context information for error handling and logging."""
    error_type: ErrorType
    operation: str
    request_id: str
    attempt: int
    max_attempts: int
    error_message: str
    error_code: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    additional_context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CircuitBreakerState:
    """State tracking for circuit breaker pattern."""
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    state: str = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    failure_threshold: int = 5
    recovery_timeout: int = 60  # seconds


class CircuitBreaker:
    """Circuit breaker implementation for preventing cascading failures."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
        """
        self.state = CircuitBreakerState(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout
        )
        self._lock = False  # Simple lock for thread safety
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerOpenError: If circuit is open
        """
        if self._is_open():
            raise CircuitBreakerOpenError("Circuit breaker is OPEN - too many recent failures")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _is_open(self) -> bool:
        """Check if circuit breaker is open."""
        if self.state.state == "CLOSED":
            return False
        
        if self.state.state == "OPEN":
            # Check if recovery timeout has passed
            if (self.state.last_failure_time and 
                datetime.utcnow() - self.state.last_failure_time > 
                timedelta(seconds=self.state.recovery_timeout)):
                self.state.state = "HALF_OPEN"
                logger.info("Circuit breaker transitioning to HALF_OPEN state")
                return False
            return True
        
        # HALF_OPEN state - allow one attempt
        return False
    
    def _on_success(self):
        """Handle successful operation."""
        if self.state.state == "HALF_OPEN":
            self.state.state = "CLOSED"
            self.state.failure_count = 0
            logger.info("Circuit breaker CLOSED - service recovered")
    
    def _on_failure(self):
        """Handle failed operation."""
        self.state.failure_count += 1
        self.state.last_failure_time = datetime.utcnow()
        
        if self.state.failure_count >= self.state.failure_threshold:
            self.state.state = "OPEN"
            logger.warning(
                f"Circuit breaker OPEN - {self.state.failure_count} consecutive failures",
                extra={
                    "failure_count": self.state.failure_count,
                    "failure_threshold": self.state.failure_threshold
                }
            )


class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class RetryableError(Exception):
    """Exception that indicates operation should be retried."""
    pass


class NonRetryableError(Exception):
    """Exception that indicates operation should not be retried."""
    pass


def exponential_backoff_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True
):
    """
    Decorator for exponential backoff retry logic.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        backoff_factor: Multiplier for delay between retries
        jitter: Whether to add random jitter to delays
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except NonRetryableError:
                    # Don't retry non-retryable errors
                    raise
                except Exception as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        # Final attempt failed
                        break
                    
                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                    
                    # Add jitter to prevent thundering herd
                    if jitter:
                        import random
                        delay = delay * (0.5 + random.random() * 0.5)
                    
                    logger.warning(
                        f"Attempt {attempt + 1} failed, retrying in {delay:.2f}s",
                        extra={
                            "function": func.__name__,
                            "attempt": attempt + 1,
                            "max_retries": max_retries,
                            "delay": delay,
                            "error": str(e)
                        }
                    )
                    
                    time.sleep(delay)
            
            # All retries exhausted
            raise last_exception
        
        return wrapper
    return decorator


class ErrorHandler:
    """Centralized error handling for the GCSE Question Generator system."""
    
    def __init__(self):
        """Initialize error handler with circuit breakers for different services."""
        self.bedrock_circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
        self.s3_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)
        self.dynamodb_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)
    
    def handle_bedrock_error(self, error: Exception, context: ErrorContext) -> ErrorContext:
        """
        Handle Bedrock API errors with appropriate classification and user messaging.
        
        Args:
            error: The exception that occurred
            context: Error context information
            
        Returns:
            Updated error context with classification and user message
        """
        context.error_type = ErrorType.BEDROCK_API_ERROR
        
        if isinstance(error, ClientError):
            error_code = error.response.get('Error', {}).get('Code', 'Unknown')
            context.error_code = error_code
            
            # Classify error types
            if error_code in ['ThrottlingException', 'TooManyRequestsException']:
                context.additional_context['user_message'] = (
                    "The AI service is currently busy. Please wait a moment and try again."
                )
                context.additional_context['retry_recommended'] = True
                context.additional_context['retry_delay'] = 5
                
            elif error_code in ['ValidationException', 'InvalidRequestException']:
                context.additional_context['user_message'] = (
                    "There was an issue with your request. Please try rephrasing your question."
                )
                context.additional_context['retry_recommended'] = False
                
            elif error_code in ['ServiceUnavailableException', 'InternalServerException']:
                context.additional_context['user_message'] = (
                    "The AI service is temporarily unavailable. Please try again in a few minutes."
                )
                context.additional_context['retry_recommended'] = True
                context.additional_context['retry_delay'] = 30
                
            else:
                context.additional_context['user_message'] = (
                    "An unexpected error occurred with the AI service. Please try again."
                )
                context.additional_context['retry_recommended'] = True
                context.additional_context['retry_delay'] = 10
        
        else:
            context.additional_context['user_message'] = (
                "Unable to connect to the AI service. Please check your connection and try again."
            )
            context.additional_context['retry_recommended'] = True
            context.additional_context['retry_delay'] = 5
        
        self._log_error(context)
        return context
    
    def handle_s3_error(self, error: Exception, context: ErrorContext) -> ErrorContext:
        """
        Handle S3 access errors with fallback strategies.
        
        Args:
            error: The exception that occurred
            context: Error context information
            
        Returns:
            Updated error context with fallback options
        """
        context.error_type = ErrorType.S3_ACCESS_ERROR
        
        if isinstance(error, ClientError):
            error_code = error.response.get('Error', {}).get('Code', 'Unknown')
            context.error_code = error_code
            
            if error_code == 'NoSuchKey':
                context.additional_context['user_message'] = (
                    "Some specification content is missing. Using cached content where available."
                )
                context.additional_context['fallback_available'] = True
                
            elif error_code == 'AccessDenied':
                context.additional_context['user_message'] = (
                    "Unable to access specification content. Please contact support."
                )
                context.additional_context['fallback_available'] = False
                
            else:
                context.additional_context['user_message'] = (
                    "Unable to load specification content. Using cached content where available."
                )
                context.additional_context['fallback_available'] = True
        
        else:
            context.additional_context['user_message'] = (
                "Network error accessing content. Please try again."
            )
            context.additional_context['fallback_available'] = True
            context.additional_context['retry_recommended'] = True
        
        self._log_error(context)
        return context
    
    def handle_dynamodb_error(self, error: Exception, context: ErrorContext) -> ErrorContext:
        """
        Handle DynamoDB errors with appropriate retry strategies.
        
        Args:
            error: The exception that occurred
            context: Error context information
            
        Returns:
            Updated error context with retry recommendations
        """
        context.error_type = ErrorType.DYNAMODB_ERROR
        
        if isinstance(error, ClientError):
            error_code = error.response.get('Error', {}).get('Code', 'Unknown')
            context.error_code = error_code
            
            if error_code in ['ProvisionedThroughputExceededException', 'ThrottlingException']:
                context.additional_context['user_message'] = (
                    "The system is currently busy. Please wait a moment and try again."
                )
                context.additional_context['retry_recommended'] = True
                context.additional_context['retry_delay'] = 2
                
            elif error_code == 'ValidationException':
                context.additional_context['user_message'] = (
                    "There was an issue saving your data. Please try again."
                )
                context.additional_context['retry_recommended'] = False
                
            else:
                context.additional_context['user_message'] = (
                    "Database error occurred. Please try again."
                )
                context.additional_context['retry_recommended'] = True
                context.additional_context['retry_delay'] = 5
        
        else:
            context.additional_context['user_message'] = (
                "Unable to save data. Please try again."
            )
            context.additional_context['retry_recommended'] = True
        
        self._log_error(context)
        return context
    
    def handle_validation_error(self, error: Exception, context: ErrorContext) -> ErrorContext:
        """
        Handle validation errors with user-friendly messages.
        
        Args:
            error: The exception that occurred
            context: Error context information
            
        Returns:
            Updated error context with user guidance
        """
        context.error_type = ErrorType.VALIDATION_ERROR
        context.additional_context['retry_recommended'] = False
        
        error_message = str(error).lower()
        
        if 'latex' in error_message:
            context.additional_context['user_message'] = (
                "The generated questions contain formatting issues. Please try again."
            )
        elif 'difficulty' in error_message:
            context.additional_context['user_message'] = (
                "Unable to assign appropriate difficulty levels. Please try again."
            )
        elif 'marks' in error_message:
            context.additional_context['user_message'] = (
                "The generated questions have marking issues. Please try again."
            )
        else:
            context.additional_context['user_message'] = (
                "The generated content doesn't meet quality standards. Please try again."
            )
        
        self._log_error(context)
        return context
    
    def handle_timeout_error(self, error: Exception, context: ErrorContext) -> ErrorContext:
        """
        Handle timeout errors with partial result strategies.
        
        Args:
            error: The exception that occurred
            context: Error context information
            
        Returns:
            Updated error context with timeout handling
        """
        context.error_type = ErrorType.TIMEOUT_ERROR
        context.additional_context['user_message'] = (
            "The request is taking longer than expected. You can try again with fewer questions."
        )
        context.additional_context['retry_recommended'] = True
        context.additional_context['retry_delay'] = 0
        context.additional_context['suggestion'] = "Try requesting fewer questions (5-10) for faster results."
        
        self._log_error(context)
        return context
    
    def _log_error(self, context: ErrorContext):
        """Log error with structured context information."""
        logger.error(
            f"Error in {context.operation}",
            extra={
                "error_type": context.error_type.value,
                "request_id": context.request_id,
                "attempt": context.attempt,
                "max_attempts": context.max_attempts,
                "error_message": context.error_message,
                "error_code": context.error_code,
                "timestamp": context.timestamp.isoformat(),
                "additional_context": context.additional_context
            }
        )
    
    def create_user_error_response(self, context: ErrorContext) -> Dict[str, Any]:
        """
        Create user-friendly error response.
        
        Args:
            context: Error context with user messaging
            
        Returns:
            Formatted error response for API
        """
        return {
            "success": False,
            "error": {
                "type": context.error_type.value,
                "message": context.additional_context.get('user_message', 'An unexpected error occurred.'),
                "retry_recommended": context.additional_context.get('retry_recommended', False),
                "retry_delay": context.additional_context.get('retry_delay', 0),
                "suggestion": context.additional_context.get('suggestion'),
                "request_id": context.request_id
            }
        }


def with_error_handling(operation_name: str):
    """
    Decorator to add comprehensive error handling to functions.
    
    Args:
        operation_name: Name of the operation for logging
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            request_id = kwargs.get('request_id', 'unknown')
            error_handler = ErrorHandler()
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                context = ErrorContext(
                    error_type=ErrorType.UNKNOWN_ERROR,
                    operation=operation_name,
                    request_id=request_id,
                    attempt=1,
                    max_attempts=1,
                    error_message=str(e)
                )
                
                # Route to appropriate error handler
                if 'bedrock' in str(e).lower() or isinstance(e, ClientError):
                    context = error_handler.handle_bedrock_error(e, context)
                elif 's3' in str(e).lower():
                    context = error_handler.handle_s3_error(e, context)
                elif 'dynamodb' in str(e).lower():
                    context = error_handler.handle_dynamodb_error(e, context)
                elif 'validation' in str(e).lower():
                    context = error_handler.handle_validation_error(e, context)
                elif 'timeout' in str(e).lower():
                    context = error_handler.handle_timeout_error(e, context)
                else:
                    context.additional_context['user_message'] = (
                        "An unexpected error occurred. Please try again."
                    )
                    error_handler._log_error(context)
                
                # Return error response instead of raising
                return error_handler.create_user_error_response(context)
        
        return wrapper
    return decorator


def validate_question_quality(question: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate generated question meets quality standards.
    
    Args:
        question: Question dictionary to validate
        
    Returns:
        Validation result with errors and confidence score
        
    Raises:
        NonRetryableError: If question has fundamental quality issues
    """
    errors = []
    confidence = 1.0
    
    # Check required fields
    required_fields = ['question_text', 'marks', 'difficulty_score', 'topic', 'tier']
    for field in required_fields:
        if field not in question or question[field] is None:
            errors.append(f"Missing required field: {field}")
            confidence -= 0.3
    
    if errors:
        raise NonRetryableError(f"Question validation failed: {'; '.join(errors)}")
    
    # Check question text quality
    question_text = question.get('question_text', '')
    
    # Minimum length check
    if len(question_text.strip()) < 10:
        errors.append("Question text too short")
        confidence -= 0.4
    
    # Maximum length check
    if len(question_text) > 1000:
        errors.append("Question text too long")
        confidence -= 0.2
    
    # Check for LaTeX syntax (should be converted)
    from src.utils.math_rendering import validate_no_latex_syntax
    if not validate_no_latex_syntax(question_text):
        errors.append("Question contains unconverted LaTeX syntax")
        raise NonRetryableError("Question contains LaTeX syntax - conversion failed")
    
    # Check difficulty score validity
    difficulty_score = question.get('difficulty_score', 0)
    tier = question.get('tier', '')
    
    if not isinstance(difficulty_score, int) or not (1 <= difficulty_score <= 10):
        errors.append(f"Invalid difficulty score: {difficulty_score}")
        confidence -= 0.3
    
    # Check tier-difficulty alignment
    if tier == "Foundation" and difficulty_score > 5:
        errors.append(f"Difficulty score {difficulty_score} too high for Foundation tier")
        confidence -= 0.2
    elif tier == "Higher" and difficulty_score < 6:
        errors.append(f"Difficulty score {difficulty_score} too low for Higher tier")
        confidence -= 0.2
    
    # Check marks validity
    marks = question.get('marks', 0)
    if not isinstance(marks, int) or marks < 1:
        errors.append(f"Invalid marks: {marks}")
        confidence -= 0.3
    
    return {
        'is_valid': len(errors) == 0,
        'confidence': max(0.0, confidence),
        'errors': errors
    }


def create_timeout_handler(timeout_seconds: int = 50):
    """
    Create a timeout handler for Lambda functions.
    
    Args:
        timeout_seconds: Timeout threshold in seconds
        
    Returns:
        Timeout handler function
    """
    def timeout_handler(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            # Add timeout monitoring to kwargs
            kwargs['_timeout_start'] = start_time
            kwargs['_timeout_limit'] = timeout_seconds
            
            try:
                result = func(*args, **kwargs)
                
                # Check if we're approaching timeout
                elapsed = time.time() - start_time
                if elapsed > timeout_seconds * 0.8:  # 80% of timeout
                    logger.warning(
                        f"Function {func.__name__} approaching timeout",
                        extra={
                            "elapsed_time": elapsed,
                            "timeout_limit": timeout_seconds,
                            "completion_percentage": (elapsed / timeout_seconds) * 100
                        }
                    )
                
                return result
                
            except Exception as e:
                elapsed = time.time() - start_time
                if elapsed > timeout_seconds * 0.9:  # Likely a timeout
                    raise TimeoutError(f"Function timed out after {elapsed:.2f} seconds")
                raise e
        
        return wrapper
    return timeout_handler