"""Audit logging service for security monitoring and compliance."""

import json
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)

class AuditEventType(Enum):
    """Types of audit events."""
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_REGISTRATION = "user_registration"
    SESSION_CREATED = "session_created"
    SESSION_EXPIRED = "session_expired"
    QUESTION_GENERATED = "question_generated"
    FEEDBACK_SUBMITTED = "feedback_submitted"
    DATA_ACCESSED = "data_accessed"
    DATA_MODIFIED = "data_modified"
    DATA_DELETED = "data_deleted"
    EXPORT_REQUESTED = "export_requested"
    SECURITY_VIOLATION = "security_violation"
    AUTHENTICATION_FAILURE = "authentication_failure"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    ADMIN_ACTION = "admin_action"
    SYSTEM_ERROR = "system_error"

class AuditSeverity(Enum):
    """Severity levels for audit events."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AuditLoggingService:
    """Service for comprehensive audit logging and security monitoring."""
    
    def __init__(self):
        self.logger = logging.getLogger("audit")
        # Configure structured logging for audit events
        self._configure_audit_logger()
    
    def _configure_audit_logger(self):
        """Configure audit logger with structured format."""
        # In production, this would send to CloudWatch Logs with specific log group
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - AUDIT - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def log_audit_event(self, 
                       event_type: AuditEventType,
                       user_id: Optional[str] = None,
                       session_id: Optional[str] = None,
                       resource: Optional[str] = None,
                       action: Optional[str] = None,
                       result: str = "success",
                       severity: AuditSeverity = AuditSeverity.LOW,
                       source_ip: Optional[str] = None,
                       user_agent: Optional[str] = None,
                       additional_data: Optional[Dict[str, Any]] = None) -> str:
        """Log an audit event with comprehensive context.
        
        Args:
            event_type: Type of audit event
            user_id: ID of the user performing the action
            session_id: Session ID if applicable
            resource: Resource being accessed/modified
            action: Specific action being performed
            result: Result of the action (success, failure, error)
            severity: Severity level of the event
            source_ip: Source IP address
            user_agent: User agent string
            additional_data: Additional context data
            
        Returns:
            Audit event ID for tracking
        """
        audit_id = self._generate_audit_id()
        timestamp = datetime.utcnow().isoformat()
        
        audit_event = {
            "audit_id": audit_id,
            "timestamp": timestamp,
            "event_type": event_type.value,
            "severity": severity.value,
            "user_id": user_id,
            "session_id": session_id,
            "resource": resource,
            "action": action,
            "result": result,
            "source_ip": source_ip,
            "user_agent": user_agent,
            "additional_data": additional_data or {}
        }
        
        # Log to CloudWatch with structured format
        self.logger.info(
            f"Audit Event: {event_type.value}",
            extra={
                "audit_event": True,
                "audit_data": audit_event
            }
        )
        
        # Check for suspicious patterns
        self._analyze_for_suspicious_activity(audit_event)
        
        return audit_id
    
    def log_authentication_event(self,
                               event_type: AuditEventType,
                               username: Optional[str] = None,
                               user_id: Optional[str] = None,
                               result: str = "success",
                               failure_reason: Optional[str] = None,
                               source_ip: Optional[str] = None,
                               user_agent: Optional[str] = None) -> str:
        """Log authentication-related events.
        
        Args:
            event_type: Authentication event type
            username: Username attempting authentication
            user_id: User ID if authentication successful
            result: Result of authentication attempt
            failure_reason: Reason for failure if applicable
            source_ip: Source IP address
            user_agent: User agent string
            
        Returns:
            Audit event ID
        """
        severity = AuditSeverity.MEDIUM if result == "success" else AuditSeverity.HIGH
        
        additional_data = {
            "username": username,
            "failure_reason": failure_reason
        }
        
        return self.log_audit_event(
            event_type=event_type,
            user_id=user_id,
            action="authenticate",
            result=result,
            severity=severity,
            source_ip=source_ip,
            user_agent=user_agent,
            additional_data=additional_data
        )
    
    def log_data_access_event(self,
                            user_id: str,
                            resource: str,
                            action: str,
                            data_type: str,
                            record_count: Optional[int] = None,
                            source_ip: Optional[str] = None,
                            session_id: Optional[str] = None) -> str:
        """Log data access events for compliance.
        
        Args:
            user_id: ID of user accessing data
            resource: Resource being accessed
            action: Action performed (read, write, delete)
            data_type: Type of data accessed
            record_count: Number of records accessed
            source_ip: Source IP address
            session_id: Session ID
            
        Returns:
            Audit event ID
        """
        additional_data = {
            "data_type": data_type,
            "record_count": record_count
        }
        
        return self.log_audit_event(
            event_type=AuditEventType.DATA_ACCESSED,
            user_id=user_id,
            session_id=session_id,
            resource=resource,
            action=action,
            severity=AuditSeverity.LOW,
            source_ip=source_ip,
            additional_data=additional_data
        )
    
    def log_security_violation(self,
                             violation_type: str,
                             description: str,
                             user_id: Optional[str] = None,
                             source_ip: Optional[str] = None,
                             severity: AuditSeverity = AuditSeverity.HIGH,
                             additional_context: Optional[Dict[str, Any]] = None) -> str:
        """Log security violations and suspicious activities.
        
        Args:
            violation_type: Type of security violation
            description: Description of the violation
            user_id: User ID if known
            source_ip: Source IP address
            severity: Severity of the violation
            additional_context: Additional context information
            
        Returns:
            Audit event ID
        """
        additional_data = {
            "violation_type": violation_type,
            "description": description,
            "additional_context": additional_context or {}
        }
        
        audit_id = self.log_audit_event(
            event_type=AuditEventType.SECURITY_VIOLATION,
            user_id=user_id,
            action="security_violation",
            result="violation_detected",
            severity=severity,
            source_ip=source_ip,
            additional_data=additional_data
        )
        
        # Trigger security alert for high/critical violations
        if severity in [AuditSeverity.HIGH, AuditSeverity.CRITICAL]:
            self._trigger_security_alert(violation_type, description, audit_id)
        
        return audit_id
    
    def log_admin_action(self,
                        admin_user_id: str,
                        action: str,
                        target_resource: str,
                        target_user_id: Optional[str] = None,
                        changes_made: Optional[Dict[str, Any]] = None,
                        source_ip: Optional[str] = None) -> str:
        """Log administrative actions for accountability.
        
        Args:
            admin_user_id: ID of admin performing action
            action: Administrative action performed
            target_resource: Resource being modified
            target_user_id: Target user ID if applicable
            changes_made: Details of changes made
            source_ip: Source IP address
            
        Returns:
            Audit event ID
        """
        additional_data = {
            "target_user_id": target_user_id,
            "changes_made": changes_made or {}
        }
        
        return self.log_audit_event(
            event_type=AuditEventType.ADMIN_ACTION,
            user_id=admin_user_id,
            resource=target_resource,
            action=action,
            severity=AuditSeverity.MEDIUM,
            source_ip=source_ip,
            additional_data=additional_data
        )
    
    def _generate_audit_id(self) -> str:
        """Generate unique audit event ID."""
        import secrets
        timestamp = int(time.time() * 1000)  # milliseconds
        random_part = secrets.token_hex(8)
        return f"audit_{timestamp}_{random_part}"
    
    def _analyze_for_suspicious_activity(self, audit_event: Dict[str, Any]):
        """Analyze audit event for suspicious patterns."""
        # This would be enhanced with ML-based anomaly detection in production
        
        event_type = audit_event.get("event_type")
        user_id = audit_event.get("user_id")
        source_ip = audit_event.get("source_ip")
        
        # Check for rapid successive failures
        if event_type == AuditEventType.AUTHENTICATION_FAILURE.value:
            self._check_rapid_auth_failures(user_id, source_ip)
        
        # Check for unusual access patterns
        if event_type == AuditEventType.DATA_ACCESSED.value:
            self._check_unusual_data_access(user_id, audit_event)
        
        # Check for off-hours activity
        self._check_off_hours_activity(audit_event)
    
    def _check_rapid_auth_failures(self, user_id: Optional[str], source_ip: Optional[str]):
        """Check for rapid authentication failures indicating brute force."""
        # In production, this would query CloudWatch Logs or a security database
        # For now, we'll log a warning for manual review
        
        if user_id or source_ip:
            logger.warning(
                "Potential brute force attack detected",
                extra={
                    "security_alert": True,
                    "alert_type": "brute_force_suspected",
                    "user_id": user_id,
                    "source_ip": source_ip
                }
            )
    
    def _check_unusual_data_access(self, user_id: Optional[str], audit_event: Dict[str, Any]):
        """Check for unusual data access patterns."""
        additional_data = audit_event.get("additional_data", {})
        record_count = additional_data.get("record_count", 0)
        
        # Flag large data access requests
        if record_count and record_count > 1000:
            logger.warning(
                "Large data access request detected",
                extra={
                    "security_alert": True,
                    "alert_type": "large_data_access",
                    "user_id": user_id,
                    "record_count": record_count
                }
            )
    
    def _check_off_hours_activity(self, audit_event: Dict[str, Any]):
        """Check for activity during off-hours."""
        timestamp = datetime.fromisoformat(audit_event["timestamp"])
        hour = timestamp.hour
        
        # Flag activity between 11 PM and 6 AM UTC
        if hour >= 23 or hour <= 6:
            severity = audit_event.get("severity")
            if severity in ["high", "critical"]:
                logger.warning(
                    "Off-hours high-severity activity detected",
                    extra={
                        "security_alert": True,
                        "alert_type": "off_hours_activity",
                        "timestamp": audit_event["timestamp"],
                        "event_type": audit_event["event_type"]
                    }
                )
    
    def _trigger_security_alert(self, violation_type: str, description: str, audit_id: str):
        """Trigger security alert for critical violations."""
        # In production, this would send to SNS topic for alerting
        logger.critical(
            f"SECURITY ALERT: {violation_type}",
            extra={
                "security_alert": True,
                "alert_type": "critical_security_violation",
                "violation_type": violation_type,
                "description": description,
                "audit_id": audit_id,
                "requires_immediate_attention": True
            }
        )
    
    def get_audit_summary(self, 
                         start_time: datetime,
                         end_time: datetime,
                         user_id: Optional[str] = None,
                         event_types: Optional[List[AuditEventType]] = None) -> Dict[str, Any]:
        """Get audit summary for a time period.
        
        Args:
            start_time: Start of time period
            end_time: End of time period
            user_id: Filter by user ID
            event_types: Filter by event types
            
        Returns:
            Audit summary statistics
        """
        # In production, this would query CloudWatch Logs or audit database
        # For now, return a placeholder summary
        
        return {
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            },
            "filters": {
                "user_id": user_id,
                "event_types": [et.value for et in event_types] if event_types else None
            },
            "summary": {
                "total_events": 0,
                "events_by_type": {},
                "events_by_severity": {},
                "unique_users": 0,
                "unique_ips": 0,
                "security_violations": 0
            },
            "note": "Audit summary would be populated from CloudWatch Logs in production"
        }
    
    def create_compliance_report(self, 
                               start_date: datetime,
                               end_date: datetime) -> Dict[str, Any]:
        """Create compliance report for audit purposes.
        
        Args:
            start_date: Start date for report
            end_date: End date for report
            
        Returns:
            Compliance report data
        """
        return {
            "report_id": self._generate_audit_id(),
            "generated_at": datetime.utcnow().isoformat(),
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "compliance_metrics": {
                "data_access_events": 0,
                "authentication_events": 0,
                "security_violations": 0,
                "admin_actions": 0,
                "user_registrations": 0,
                "data_exports": 0
            },
            "security_summary": {
                "failed_logins": 0,
                "blocked_ips": 0,
                "suspicious_activities": 0,
                "policy_violations": 0
            },
            "data_protection": {
                "pii_access_events": 0,
                "encryption_status": "enabled",
                "data_retention_compliance": "compliant"
            },
            "recommendations": [
                "Regular security training for users",
                "Review and update access policies",
                "Monitor for unusual access patterns",
                "Implement additional MFA where appropriate"
            ],
            "note": "Detailed metrics would be populated from audit logs in production"
        }


# Global audit service instance
audit_service = AuditLoggingService()


def log_audit_event(*args, **kwargs) -> str:
    """Convenience function for logging audit events."""
    return audit_service.log_audit_event(*args, **kwargs)


def log_authentication_event(*args, **kwargs) -> str:
    """Convenience function for logging authentication events."""
    return audit_service.log_authentication_event(*args, **kwargs)


def log_data_access_event(*args, **kwargs) -> str:
    """Convenience function for logging data access events."""
    return audit_service.log_data_access_event(*args, **kwargs)


def log_security_violation(*args, **kwargs) -> str:
    """Convenience function for logging security violations."""
    return audit_service.log_security_violation(*args, **kwargs)


def log_admin_action(*args, **kwargs) -> str:
    """Convenience function for logging admin actions."""
    return audit_service.log_admin_action(*args, **kwargs)