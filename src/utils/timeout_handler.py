"""
Timeout handling utilities for Lambda functions and long-running operations.

This module provides comprehensive timeout handling with partial result support,
progress tracking, and graceful degradation for the GCSE Question Generator V2 system.
"""

import time
import logging
import functools
from typing import Dict, Any, Optional, List, Callable, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from src.utils.logging_service import get_logging_service, LogContext, ErrorContext

logger = logging.getLogger(__name__)


class TimeoutStrategy(Enum):
    """Strategies for handling timeouts."""
    FAIL_FAST = "fail_fast"           # Fail immediately when timeout detected
    PARTIAL_RESULTS = "partial_results"  # Return partial results if available
    GRACEFUL_DEGRADATION = "graceful_degradation"  # Reduce scope and continue
    RETRY_SMALLER = "retry_smaller"   # Suggest retrying with smaller request


@dataclass
class TimeoutConfig:
    """Configuration for timeout handling."""
    total_timeout_seconds: float
    warning_threshold_percent: float = 0.8  # Warn at 80% of timeout
    critical_threshold_percent: float = 0.9  # Critical at 90% of timeout
    strategy: TimeoutStrategy = TimeoutStrategy.PARTIAL_RESULTS
    enable_progress_tracking: bool = True
    checkpoint_interval_seconds: float = 5.0


@dataclass
class ProgressCheckpoint:
    """Progress checkpoint for timeout monitoring."""
    timestamp: datetime
    operation: str
    progress_percent: float
    items_completed: int
    items_total: int
    partial_results: Optional[Any] = None
    can_return_partial: bool = False


@dataclass
class TimeoutResult:
    """Result of timeout-aware operation."""
    success: bool
    completed: bool
    partial_results: Optional[Any] = None
    progress_percent: float = 0.0
    timeout_occurred: bool = False
    items_completed: int = 0
    items_total: int = 0
    duration_seconds: float = 0.0
    timeout_message: Optional[str] = None
    recovery_suggestions: List[str] = field(default_factory=list)


class TimeoutHandler:
    """Handler for managing timeouts in Lambda functions and operations."""
    
    def __init__(self, config: TimeoutConfig):
        """
        Initialize timeout handler.
        
        Args:
            config: Timeout configuration
        """
        self.config = config
        self.start_time = time.time()
        self.checkpoints: List[ProgressCheckpoint] = []
        self.logging_service = get_logging_service()
        self._last_checkpoint_time = self.start_time
        self._warned_at_threshold = False
        self._critical_at_threshold = False
    
    def is_timeout_approaching(self, buffer_seconds: float = 5.0) -> bool:
        """
        Check if timeout is approaching.
        
        Args:
            buffer_seconds: Buffer time before actual timeout
            
        Returns:
            True if timeout is approaching
        """
        elapsed = time.time() - self.start_time
        remaining = self.config.total_timeout_seconds - elapsed
        return remaining <= buffer_seconds
    
    def get_remaining_time(self) -> float:
        """Get remaining time in seconds."""
        elapsed = time.time() - self.start_time
        return max(0, self.config.total_timeout_seconds - elapsed)
    
    def get_elapsed_time(self) -> float:
        """Get elapsed time in seconds."""
        return time.time() - self.start_time
    
    def get_progress_percent(self) -> float:
        """Get progress as percentage of total timeout."""
        elapsed = self.get_elapsed_time()
        return min(100.0, (elapsed / self.config.total_timeout_seconds) * 100)
    
    def should_checkpoint(self) -> bool:
        """Check if it's time for a progress checkpoint."""
        if not self.config.enable_progress_tracking:
            return False
        
        elapsed_since_checkpoint = time.time() - self._last_checkpoint_time
        return elapsed_since_checkpoint >= self.config.checkpoint_interval_seconds
    
    def add_checkpoint(self, operation: str, items_completed: int, items_total: int,
                      partial_results: Optional[Any] = None, 
                      can_return_partial: bool = False) -> bool:
        """
        Add a progress checkpoint.
        
        Args:
            operation: Current operation name
            items_completed: Number of items completed
            items_total: Total number of items
            partial_results: Partial results if available
            can_return_partial: Whether partial results can be returned
            
        Returns:
            True if operation should continue, False if timeout
        """
        now = datetime.utcnow()
        progress_percent = (items_completed / items_total * 100) if items_total > 0 else 0
        
        checkpoint = ProgressCheckpoint(
            timestamp=now,
            operation=operation,
            progress_percent=progress_percent,
            items_completed=items_completed,
            items_total=items_total,
            partial_results=partial_results,
            can_return_partial=can_return_partial
        )
        
        self.checkpoints.append(checkpoint)
        self._last_checkpoint_time = time.time()
        
        # Check timeout thresholds
        elapsed_percent = self.get_progress_percent()
        
        # Warning threshold
        if (elapsed_percent >= self.config.warning_threshold_percent * 100 and 
            not self._warned_at_threshold):
            self._warned_at_threshold = True
            self.logging_service.log_warning(
                f"Operation approaching timeout warning threshold: {elapsed_percent:.1f}%",
                context=LogContext(
                    operation=operation,
                    additional_fields={
                        'progress_percent': progress_percent,
                        'items_completed': items_completed,
                        'items_total': items_total,
                        'elapsed_percent': elapsed_percent
                    }
                )
            )
        
        # Critical threshold
        if (elapsed_percent >= self.config.critical_threshold_percent * 100 and 
            not self._critical_at_threshold):
            self._critical_at_threshold = True
            self.logging_service.log_error(
                f"Operation at critical timeout threshold: {elapsed_percent:.1f}%",
                context=LogContext(
                    operation=operation,
                    additional_fields={
                        'progress_percent': progress_percent,
                        'items_completed': items_completed,
                        'items_total': items_total,
                        'elapsed_percent': elapsed_percent
                    }
                ),
                error_context=ErrorContext(
                    error_type="TimeoutWarning",
                    error_message="Operation approaching timeout",
                    user_impact="Operation may be terminated",
                    recovery_actions=["Consider reducing request size", "Retry with fewer items"]
                )
            )
        
        # Check if we should terminate
        if self.is_timeout_approaching():
            return False
        
        return True
    
    def handle_timeout(self, operation: str, context: Optional[LogContext] = None) -> TimeoutResult:
        """
        Handle timeout situation based on configured strategy.
        
        Args:
            operation: Operation that timed out
            context: Logging context
            
        Returns:
            TimeoutResult with appropriate handling
        """
        elapsed = self.get_elapsed_time()
        latest_checkpoint = self.checkpoints[-1] if self.checkpoints else None
        
        # Log timeout occurrence
        error_context = ErrorContext(
            error_type="TimeoutError",
            error_message=f"Operation {operation} timed out after {elapsed:.2f}s",
            user_impact="Operation was terminated due to timeout",
            recovery_actions=self._get_recovery_suggestions(latest_checkpoint)
        )
        
        self.logging_service.log_error(
            f"Timeout handling for operation: {operation}",
            context=context,
            error_context=error_context
        )
        
        # Handle based on strategy
        if self.config.strategy == TimeoutStrategy.FAIL_FAST:
            return TimeoutResult(
                success=False,
                completed=False,
                timeout_occurred=True,
                duration_seconds=elapsed,
                timeout_message="Operation timed out",
                recovery_suggestions=self._get_recovery_suggestions(latest_checkpoint)
            )
        
        elif self.config.strategy == TimeoutStrategy.PARTIAL_RESULTS:
            if latest_checkpoint and latest_checkpoint.can_return_partial:
                return TimeoutResult(
                    success=True,
                    completed=False,
                    partial_results=latest_checkpoint.partial_results,
                    progress_percent=latest_checkpoint.progress_percent,
                    timeout_occurred=True,
                    items_completed=latest_checkpoint.items_completed,
                    items_total=latest_checkpoint.items_total,
                    duration_seconds=elapsed,
                    timeout_message=f"Partial results returned ({latest_checkpoint.items_completed}/{latest_checkpoint.items_total} items)",
                    recovery_suggestions=self._get_recovery_suggestions(latest_checkpoint)
                )
            else:
                return TimeoutResult(
                    success=False,
                    completed=False,
                    timeout_occurred=True,
                    duration_seconds=elapsed,
                    timeout_message="Operation timed out with no partial results available",
                    recovery_suggestions=self._get_recovery_suggestions(latest_checkpoint)
                )
        
        elif self.config.strategy == TimeoutStrategy.GRACEFUL_DEGRADATION:
            # For graceful degradation, we would need operation-specific logic
            # This is a placeholder for more sophisticated handling
            return TimeoutResult(
                success=True,
                completed=False,
                timeout_occurred=True,
                duration_seconds=elapsed,
                timeout_message="Operation completed with reduced scope due to timeout",
                recovery_suggestions=self._get_recovery_suggestions(latest_checkpoint)
            )
        
        else:  # RETRY_SMALLER
            return TimeoutResult(
                success=False,
                completed=False,
                timeout_occurred=True,
                duration_seconds=elapsed,
                timeout_message="Operation timed out - retry with smaller request recommended",
                recovery_suggestions=self._get_recovery_suggestions(latest_checkpoint)
            )
    
    def _get_recovery_suggestions(self, checkpoint: Optional[ProgressCheckpoint]) -> List[str]:
        """Get recovery suggestions based on current state."""
        suggestions = []
        
        if checkpoint:
            if checkpoint.items_total > 10:
                suggestions.append(f"Try requesting fewer items (current: {checkpoint.items_total})")
            
            if checkpoint.progress_percent > 50:
                suggestions.append("Operation was more than 50% complete - retry may succeed")
            
            if checkpoint.can_return_partial:
                suggestions.append("Partial results were available - consider accepting partial completion")
        
        suggestions.extend([
            "Retry the operation later when system load may be lower",
            "Break large requests into smaller chunks",
            "Contact support if timeouts persist"
        ])
        
        return suggestions
    
    def get_timeout_summary(self) -> Dict[str, Any]:
        """Get summary of timeout handling session."""
        return {
            'total_timeout_seconds': self.config.total_timeout_seconds,
            'elapsed_seconds': self.get_elapsed_time(),
            'remaining_seconds': self.get_remaining_time(),
            'progress_percent': self.get_progress_percent(),
            'checkpoints_count': len(self.checkpoints),
            'strategy': self.config.strategy.value,
            'warning_threshold_reached': self._warned_at_threshold,
            'critical_threshold_reached': self._critical_at_threshold,
            'latest_checkpoint': {
                'operation': self.checkpoints[-1].operation,
                'progress_percent': self.checkpoints[-1].progress_percent,
                'items_completed': self.checkpoints[-1].items_completed,
                'items_total': self.checkpoints[-1].items_total
            } if self.checkpoints else None
        }


def with_timeout_handling(timeout_seconds: float, 
                         strategy: TimeoutStrategy = TimeoutStrategy.PARTIAL_RESULTS):
    """
    Decorator to add timeout handling to functions.
    
    Args:
        timeout_seconds: Maximum execution time
        strategy: Timeout handling strategy
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            config = TimeoutConfig(
                total_timeout_seconds=timeout_seconds,
                strategy=strategy
            )
            
            timeout_handler = TimeoutHandler(config)
            
            # Add timeout handler to kwargs
            kwargs['_timeout_handler'] = timeout_handler
            
            try:
                result = func(*args, **kwargs)
                
                # Check if result indicates timeout
                if isinstance(result, TimeoutResult):
                    return result
                
                # Normal completion
                return TimeoutResult(
                    success=True,
                    completed=True,
                    partial_results=result,
                    progress_percent=100.0,
                    duration_seconds=timeout_handler.get_elapsed_time()
                )
                
            except Exception as e:
                if "timeout" in str(e).lower():
                    return timeout_handler.handle_timeout(func.__name__)
                raise
        
        return wrapper
    return decorator


def create_lambda_timeout_handler(lambda_context: Any, 
                                buffer_seconds: float = 10.0) -> TimeoutHandler:
    """
    Create timeout handler for AWS Lambda function.
    
    Args:
        lambda_context: AWS Lambda context object
        buffer_seconds: Buffer time before Lambda timeout
        
    Returns:
        Configured TimeoutHandler
    """
    # Calculate available time (Lambda timeout minus buffer)
    remaining_time_ms = lambda_context.get_remaining_time_in_millis()
    available_seconds = (remaining_time_ms / 1000.0) - buffer_seconds
    
    config = TimeoutConfig(
        total_timeout_seconds=max(5.0, available_seconds),  # Minimum 5 seconds
        strategy=TimeoutStrategy.PARTIAL_RESULTS,
        warning_threshold_percent=0.7,  # Earlier warning for Lambda
        critical_threshold_percent=0.85  # Earlier critical for Lambda
    )
    
    return TimeoutHandler(config)


def handle_question_generation_timeout(questions_generated: List[Dict[str, Any]], 
                                     questions_requested: int,
                                     timeout_handler: TimeoutHandler) -> Dict[str, Any]:
    """
    Handle timeout specifically for question generation operations.
    
    Args:
        questions_generated: Questions generated so far
        questions_requested: Total questions requested
        timeout_handler: Timeout handler instance
        
    Returns:
        Response with partial results or timeout error
    """
    if len(questions_generated) > 0:
        # Return partial results
        return {
            'success': True,
            'questions': questions_generated,
            'metadata': {
                'requested_count': questions_requested,
                'generated_count': len(questions_generated),
                'completion_status': 'partial_timeout',
                'timeout_occurred': True,
                'message': f'Generated {len(questions_generated)} of {questions_requested} questions before timeout'
            },
            'suggestions': [
                f'Try requesting fewer questions (you requested {questions_requested})',
                'Consider breaking large requests into smaller batches',
                'Retry the operation - it may complete faster on subsequent attempts'
            ]
        }
    else:
        # No questions generated
        return {
            'success': False,
            'error': {
                'type': 'TimeoutError',
                'message': 'Request timed out before any questions could be generated',
                'suggestions': [
                    'Try requesting fewer questions',
                    'Retry the operation later',
                    'Check if the topic/subtopic is valid'
                ]
            }
        }


def monitor_operation_progress(operation_name: str, 
                             total_items: int,
                             timeout_handler: Optional[TimeoutHandler] = None) -> Callable:
    """
    Context manager for monitoring operation progress with timeout handling.
    
    Args:
        operation_name: Name of the operation
        total_items: Total number of items to process
        timeout_handler: Optional timeout handler
        
    Returns:
        Progress monitoring function
    """
    def progress_monitor(items_completed: int, 
                        partial_results: Optional[Any] = None,
                        can_return_partial: bool = False) -> bool:
        """
        Update progress and check for timeout.
        
        Args:
            items_completed: Number of items completed
            partial_results: Partial results if available
            can_return_partial: Whether partial results can be returned
            
        Returns:
            True if operation should continue, False if timeout
        """
        if timeout_handler:
            return timeout_handler.add_checkpoint(
                operation_name,
                items_completed,
                total_items,
                partial_results,
                can_return_partial
            )
        return True
    
    return progress_monitor


# Utility functions for common timeout scenarios

def is_lambda_timeout_approaching(lambda_context: Any, buffer_seconds: float = 5.0) -> bool:
    """Check if Lambda function is approaching timeout."""
    remaining_ms = lambda_context.get_remaining_time_in_millis()
    return remaining_ms <= (buffer_seconds * 1000)


def create_timeout_response(operation: str, partial_results: Optional[Any] = None,
                          items_completed: int = 0, items_total: int = 0) -> Dict[str, Any]:
    """Create standardized timeout response."""
    response = {
        'success': partial_results is not None,
        'timeout_occurred': True,
        'operation': operation,
        'message': f'Operation timed out after completing {items_completed} of {items_total} items'
    }
    
    if partial_results is not None:
        response['partial_results'] = partial_results
        response['completion_percentage'] = (items_completed / items_total * 100) if items_total > 0 else 0
    
    response['suggestions'] = [
        'Try reducing the request size',
        'Retry the operation',
        'Break large requests into smaller chunks'
    ]
    
    return response