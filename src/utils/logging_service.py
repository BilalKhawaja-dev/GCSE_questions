"""
Comprehensive logging service for structured error logging and monitoring.

This service provides structured logging with CloudWatch integration, error context,
and monitoring capabilities for the GCSE Question Generator V2 system.
"""

import json
import logging
import time
import traceback
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from enum import Enum
import boto3
from botocore.exceptions import ClientError

# Configure structured logging format
class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging."""
    
    def format(self, record):
        """Format log record as structured JSON."""
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        
        if hasattr(record, 'operation'):
            log_entry['operation'] = record.operation
        
        if hasattr(record, 'error_type'):
            log_entry['error_type'] = record.error_type
        
        if hasattr(record, 'error_code'):
            log_entry['error_code'] = record.error_code
        
        if hasattr(record, 'duration_ms'):
            log_entry['duration_ms'] = record.duration_ms
        
        if hasattr(record, 'additional_context'):
            log_entry['context'] = record.additional_context
        
        # Add exception information if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        return json.dumps(log_entry, default=str)


class LogLevel(Enum):
    """Log level enumeration."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AlertSeverity(Enum):
    """Alert severity levels for monitoring."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class LogContext:
    """Context information for structured logging."""
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    operation: Optional[str] = None
    session_id: Optional[str] = None
    component: Optional[str] = None
    additional_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorContext:
    """Extended error context for comprehensive error logging."""
    error_type: str
    error_message: str
    error_code: Optional[str] = None
    stack_trace: Optional[str] = None
    request_context: Optional[Dict[str, Any]] = None
    system_context: Optional[Dict[str, Any]] = None
    user_impact: Optional[str] = None
    recovery_actions: Optional[List[str]] = None


@dataclass
class PerformanceMetrics:
    """Performance metrics for operation monitoring."""
    operation: str
    duration_ms: float
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    request_size_bytes: Optional[int] = None
    response_size_bytes: Optional[int] = None
    database_queries: Optional[int] = None
    api_calls: Optional[int] = None


class ComprehensiveLoggingService:
    """Service for comprehensive structured logging and monitoring."""
    
    def __init__(self, service_name: str, environment: str = "development", 
                 cloudwatch_log_group: Optional[str] = None):
        """
        Initialize comprehensive logging service.
        
        Args:
            service_name: Name of the service (e.g., "gcse-generator-v2")
            environment: Environment name (dev, staging, prod)
            cloudwatch_log_group: CloudWatch log group name for centralized logging
        """
        self.service_name = service_name
        self.environment = environment
        self.cloudwatch_log_group = cloudwatch_log_group
        
        # Initialize CloudWatch client if log group specified
        self.cloudwatch_client = None
        if cloudwatch_log_group:
            try:
                self.cloudwatch_client = boto3.client('logs')
                self._ensure_log_group_exists()
            except Exception as e:
                # Fallback to local logging if CloudWatch unavailable
                print(f"Warning: CloudWatch logging unavailable: {e}")
        
        # Configure structured logger
        self.logger = self._setup_structured_logger()
        
        # Error tracking
        self.error_counts = {}
        self.alert_thresholds = {
            AlertSeverity.LOW: 10,      # 10 errors per hour
            AlertSeverity.MEDIUM: 50,   # 50 errors per hour
            AlertSeverity.HIGH: 100,    # 100 errors per hour
            AlertSeverity.CRITICAL: 200 # 200 errors per hour
        }
    
    def _setup_structured_logger(self) -> logging.Logger:
        """Set up structured logger with custom formatter."""
        logger = logging.getLogger(f"{self.service_name}.structured")
        logger.setLevel(logging.DEBUG)
        
        # Remove existing handlers to avoid duplicates
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # Add structured console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(StructuredFormatter())
        logger.addHandler(console_handler)
        
        # Prevent propagation to avoid duplicate logs
        logger.propagate = False
        
        return logger
    
    def _ensure_log_group_exists(self):
        """Ensure CloudWatch log group exists."""
        if not self.cloudwatch_client or not self.cloudwatch_log_group:
            return
        
        try:
            self.cloudwatch_client.create_log_group(
                logGroupName=self.cloudwatch_log_group
            )
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceAlreadyExistsException':
                raise
    
    def log_info(self, message: str, context: Optional[LogContext] = None, 
                 metrics: Optional[PerformanceMetrics] = None):
        """Log informational message with context."""
        extra = self._build_log_extra(context, metrics)
        self.logger.info(message, extra=extra)
        
        # Send to CloudWatch if configured
        if self.cloudwatch_client:
            self._send_to_cloudwatch(LogLevel.INFO, message, extra)
    
    def log_warning(self, message: str, context: Optional[LogContext] = None, 
                   error_context: Optional[ErrorContext] = None):
        """Log warning message with context."""
        extra = self._build_log_extra(context)
        
        if error_context:
            extra.update({
                'error_type': error_context.error_type,
                'error_code': error_context.error_code,
                'user_impact': error_context.user_impact
            })
        
        self.logger.warning(message, extra=extra)
        
        # Send to CloudWatch if configured
        if self.cloudwatch_client:
            self._send_to_cloudwatch(LogLevel.WARNING, message, extra)
    
    def log_error(self, message: str, context: Optional[LogContext] = None, 
                  error_context: Optional[ErrorContext] = None, 
                  exception: Optional[Exception] = None):
        """Log error message with comprehensive context."""
        extra = self._build_log_extra(context)
        
        if error_context:
            extra.update({
                'error_type': error_context.error_type,
                'error_code': error_context.error_code,
                'error_message': error_context.error_message,
                'user_impact': error_context.user_impact,
                'recovery_actions': error_context.recovery_actions,
                'request_context': error_context.request_context,
                'system_context': error_context.system_context
            })
        
        # Log with exception info if provided
        if exception:
            self.logger.error(message, extra=extra, exc_info=True)
        else:
            self.logger.error(message, extra=extra)
        
        # Track error for alerting
        self._track_error(error_context.error_type if error_context else 'unknown')
        
        # Send to CloudWatch if configured
        if self.cloudwatch_client:
            self._send_to_cloudwatch(LogLevel.ERROR, message, extra)
        
        # Check if alert should be triggered
        self._check_alert_thresholds()
    
    def log_critical(self, message: str, context: Optional[LogContext] = None, 
                    error_context: Optional[ErrorContext] = None, 
                    exception: Optional[Exception] = None):
        """Log critical error with immediate alerting."""
        extra = self._build_log_extra(context)
        
        if error_context:
            extra.update({
                'error_type': error_context.error_type,
                'error_code': error_context.error_code,
                'error_message': error_context.error_message,
                'user_impact': error_context.user_impact,
                'recovery_actions': error_context.recovery_actions
            })
        
        # Log with exception info if provided
        if exception:
            self.logger.critical(message, extra=extra, exc_info=True)
        else:
            self.logger.critical(message, extra=extra)
        
        # Track critical error
        self._track_error(f"CRITICAL_{error_context.error_type if error_context else 'unknown'}")
        
        # Send to CloudWatch if configured
        if self.cloudwatch_client:
            self._send_to_cloudwatch(LogLevel.CRITICAL, message, extra)
        
        # Trigger immediate alert for critical errors
        self._trigger_alert(AlertSeverity.CRITICAL, message, extra)
    
    def log_performance(self, metrics: PerformanceMetrics, 
                       context: Optional[LogContext] = None):
        """Log performance metrics."""
        message = f"Performance metrics for {metrics.operation}"
        extra = self._build_log_extra(context, metrics)
        
        # Add performance-specific fields
        extra.update({
            'metric_type': 'performance',
            'operation': metrics.operation,
            'duration_ms': metrics.duration_ms
        })
        
        if metrics.memory_usage_mb:
            extra['memory_usage_mb'] = metrics.memory_usage_mb
        if metrics.cpu_usage_percent:
            extra['cpu_usage_percent'] = metrics.cpu_usage_percent
        if metrics.request_size_bytes:
            extra['request_size_bytes'] = metrics.request_size_bytes
        if metrics.response_size_bytes:
            extra['response_size_bytes'] = metrics.response_size_bytes
        
        self.logger.info(message, extra=extra)
        
        # Send to CloudWatch if configured
        if self.cloudwatch_client:
            self._send_to_cloudwatch(LogLevel.INFO, message, extra)
    
    def log_security_event(self, event_type: str, message: str, 
                          context: Optional[LogContext] = None, 
                          severity: AlertSeverity = AlertSeverity.MEDIUM):
        """Log security-related events with appropriate alerting."""
        extra = self._build_log_extra(context)
        extra.update({
            'event_type': 'security',
            'security_event_type': event_type,
            'severity': severity.value
        })
        
        self.logger.warning(f"SECURITY EVENT: {message}", extra=extra)
        
        # Send to CloudWatch if configured
        if self.cloudwatch_client:
            self._send_to_cloudwatch(LogLevel.WARNING, f"SECURITY EVENT: {message}", extra)
        
        # Trigger alert for security events
        if severity in [AlertSeverity.HIGH, AlertSeverity.CRITICAL]:
            self._trigger_alert(severity, f"Security Event: {message}", extra)
    
    def log_business_event(self, event_type: str, message: str, 
                          context: Optional[LogContext] = None, 
                          business_metrics: Optional[Dict[str, Any]] = None):
        """Log business-related events and metrics."""
        extra = self._build_log_extra(context)
        extra.update({
            'event_type': 'business',
            'business_event_type': event_type
        })
        
        if business_metrics:
            extra['business_metrics'] = business_metrics
        
        self.logger.info(f"BUSINESS EVENT: {message}", extra=extra)
        
        # Send to CloudWatch if configured
        if self.cloudwatch_client:
            self._send_to_cloudwatch(LogLevel.INFO, f"BUSINESS EVENT: {message}", extra)
    
    def _build_log_extra(self, context: Optional[LogContext] = None, 
                        metrics: Optional[PerformanceMetrics] = None) -> Dict[str, Any]:
        """Build extra fields for logging."""
        extra = {
            'service': self.service_name,
            'environment': self.environment,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        if context:
            if context.request_id:
                extra['request_id'] = context.request_id
            if context.user_id:
                extra['user_id'] = context.user_id
            if context.operation:
                extra['operation'] = context.operation
            if context.session_id:
                extra['session_id'] = context.session_id
            if context.component:
                extra['component'] = context.component
            if context.additional_fields:
                extra['additional_context'] = context.additional_fields
        
        if metrics:
            extra['duration_ms'] = metrics.duration_ms
        
        return extra
    
    def _send_to_cloudwatch(self, level: LogLevel, message: str, extra: Dict[str, Any]):
        """Send log entry to CloudWatch."""
        if not self.cloudwatch_client or not self.cloudwatch_log_group:
            return
        
        try:
            log_event = {
                'timestamp': int(time.time() * 1000),
                'message': json.dumps({
                    'level': level.value,
                    'message': message,
                    **extra
                }, default=str)
            }
            
            # Create log stream if needed (use current date)
            log_stream = f"{self.service_name}-{datetime.now().strftime('%Y-%m-%d')}"
            
            try:
                self.cloudwatch_client.create_log_stream(
                    logGroupName=self.cloudwatch_log_group,
                    logStreamName=log_stream
                )
            except ClientError as e:
                if e.response['Error']['Code'] != 'ResourceAlreadyExistsException':
                    return  # Skip CloudWatch logging if stream creation fails
            
            # Send log event
            self.cloudwatch_client.put_log_events(
                logGroupName=self.cloudwatch_log_group,
                logStreamName=log_stream,
                logEvents=[log_event]
            )
            
        except Exception as e:
            # Don't let CloudWatch errors break the application
            print(f"Failed to send log to CloudWatch: {e}")
    
    def _track_error(self, error_type: str):
        """Track error counts for alerting."""
        current_hour = int(time.time() // 3600)
        
        if current_hour not in self.error_counts:
            self.error_counts[current_hour] = {}
        
        if error_type not in self.error_counts[current_hour]:
            self.error_counts[current_hour][error_type] = 0
        
        self.error_counts[current_hour][error_type] += 1
        
        # Clean up old error counts (keep only last 24 hours)
        cutoff_hour = current_hour - 24
        self.error_counts = {
            hour: counts for hour, counts in self.error_counts.items() 
            if hour > cutoff_hour
        }
    
    def _check_alert_thresholds(self):
        """Check if error counts exceed alert thresholds."""
        current_hour = int(time.time() // 3600)
        
        if current_hour not in self.error_counts:
            return
        
        total_errors = sum(self.error_counts[current_hour].values())
        
        # Check thresholds in descending order of severity
        for severity in [AlertSeverity.CRITICAL, AlertSeverity.HIGH, 
                        AlertSeverity.MEDIUM, AlertSeverity.LOW]:
            if total_errors >= self.alert_thresholds[severity]:
                self._trigger_alert(
                    severity, 
                    f"Error threshold exceeded: {total_errors} errors in current hour",
                    {'error_counts': self.error_counts[current_hour]}
                )
                break
    
    def _trigger_alert(self, severity: AlertSeverity, message: str, context: Dict[str, Any]):
        """Trigger alert for monitoring systems."""
        alert_data = {
            'service': self.service_name,
            'environment': self.environment,
            'severity': severity.value,
            'message': message,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'context': context
        }
        
        # Log the alert
        self.logger.critical(f"ALERT TRIGGERED: {message}", extra={
            'alert_severity': severity.value,
            'alert_data': alert_data
        })
        
        # Here you could integrate with alerting systems like:
        # - SNS for email/SMS alerts
        # - Slack webhooks
        # - PagerDuty
        # - Custom monitoring dashboards
        
        # For now, we'll just ensure it's logged prominently
        print(f"🚨 ALERT [{severity.value.upper()}]: {message}")
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get error summary for the specified time period."""
        current_hour = int(time.time() // 3600)
        cutoff_hour = current_hour - hours
        
        total_errors = 0
        error_breakdown = {}
        
        for hour, counts in self.error_counts.items():
            if hour > cutoff_hour:
                for error_type, count in counts.items():
                    total_errors += count
                    if error_type not in error_breakdown:
                        error_breakdown[error_type] = 0
                    error_breakdown[error_type] += count
        
        return {
            'time_period_hours': hours,
            'total_errors': total_errors,
            'error_breakdown': error_breakdown,
            'error_rate_per_hour': total_errors / hours if hours > 0 else 0
        }


# Global logging service instance
_logging_service: Optional[ComprehensiveLoggingService] = None


def get_logging_service() -> ComprehensiveLoggingService:
    """Get or create global logging service instance."""
    global _logging_service
    
    if _logging_service is None:
        import os
        service_name = os.environ.get('SERVICE_NAME', 'gcse-generator-v2')
        environment = os.environ.get('ENVIRONMENT', 'development')
        cloudwatch_log_group = os.environ.get('CLOUDWATCH_LOG_GROUP')
        
        _logging_service = ComprehensiveLoggingService(
            service_name=service_name,
            environment=environment,
            cloudwatch_log_group=cloudwatch_log_group
        )
    
    return _logging_service


def log_operation_start(operation: str, context: Optional[LogContext] = None) -> float:
    """Log operation start and return start time for duration calculation."""
    start_time = time.time()
    
    logging_service = get_logging_service()
    logging_service.log_info(
        f"Starting operation: {operation}",
        context=context
    )
    
    return start_time


def log_operation_end(operation: str, start_time: float, 
                     context: Optional[LogContext] = None,
                     success: bool = True, error: Optional[Exception] = None):
    """Log operation completion with duration and outcome."""
    duration_ms = (time.time() - start_time) * 1000
    
    metrics = PerformanceMetrics(
        operation=operation,
        duration_ms=duration_ms
    )
    
    logging_service = get_logging_service()
    
    if success:
        logging_service.log_info(
            f"Completed operation: {operation} in {duration_ms:.2f}ms",
            context=context,
            metrics=metrics
        )
    else:
        error_context = ErrorContext(
            error_type=type(error).__name__ if error else 'unknown',
            error_message=str(error) if error else 'Operation failed',
            user_impact="Operation failed to complete"
        )
        
        logging_service.log_error(
            f"Failed operation: {operation} after {duration_ms:.2f}ms",
            context=context,
            error_context=error_context,
            exception=error
        )


def operation_logger(operation_name: str):
    """Decorator to automatically log operation start/end with timing."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Extract request_id from kwargs if available
            request_id = kwargs.get('request_id')
            context = LogContext(
                request_id=request_id,
                operation=operation_name,
                component=func.__module__
            )
            
            start_time = log_operation_start(operation_name, context)
            
            try:
                result = func(*args, **kwargs)
                log_operation_end(operation_name, start_time, context, success=True)
                return result
            except Exception as e:
                log_operation_end(operation_name, start_time, context, success=False, error=e)
                raise
        
        return wrapper
    return decorator