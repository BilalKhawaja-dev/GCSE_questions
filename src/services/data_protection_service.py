"""Data protection service for encryption, PII handling, and data isolation."""

import hashlib
import hmac
import secrets
import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class DataProtectionService:
    """Service for handling data protection, encryption, and PII management."""
    
    def __init__(self):
        # In production, these would come from AWS Secrets Manager or KMS
        self.encryption_key = self._get_encryption_key()
        self.hmac_key = self._get_hmac_key()
    
    def _get_encryption_key(self) -> bytes:
        """Get encryption key from secure storage."""
        # In production, retrieve from AWS KMS or Secrets Manager
        # For now, use a deterministic key based on environment
        import os
        key_material = os.environ.get('ENCRYPTION_KEY', 'default-key-material-change-in-production')
        return hashlib.sha256(key_material.encode()).digest()
    
    def _get_hmac_key(self) -> bytes:
        """Get HMAC key for data integrity."""
        # In production, retrieve from AWS KMS or Secrets Manager
        import os
        key_material = os.environ.get('HMAC_KEY', 'default-hmac-key-change-in-production')
        return hashlib.sha256(key_material.encode()).digest()
    
    def encrypt_sensitive_data(self, data: str, context: str = "") -> Dict[str, str]:
        """Encrypt sensitive data using AES encryption.
        
        Args:
            data: Data to encrypt
            context: Context for the encryption (for key derivation)
            
        Returns:
            Dictionary with encrypted data and metadata
        """
        try:
            from cryptography.fernet import Fernet
            import base64
            
            # Derive key with context
            context_key = self._derive_key_with_context(context)
            fernet = Fernet(base64.urlsafe_b64encode(context_key))
            
            # Encrypt the data
            encrypted_data = fernet.encrypt(data.encode())
            
            # Create integrity hash
            integrity_hash = hmac.new(
                self.hmac_key,
                encrypted_data,
                hashlib.sha256
            ).hexdigest()
            
            return {
                'encrypted_data': base64.b64encode(encrypted_data).decode(),
                'integrity_hash': integrity_hash,
                'encryption_context': context,
                'encrypted_at': datetime.utcnow().isoformat()
            }
            
        except ImportError:
            # Fallback to basic encoding if cryptography not available
            logger.warning("Cryptography library not available, using basic encoding")
            encoded_data = base64.b64encode(data.encode()).decode()
            return {
                'encrypted_data': encoded_data,
                'integrity_hash': hashlib.sha256(data.encode()).hexdigest(),
                'encryption_context': context,
                'encrypted_at': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Encryption failed: {str(e)}")
            raise
    
    def decrypt_sensitive_data(self, encrypted_package: Dict[str, str]) -> str:
        """Decrypt sensitive data.
        
        Args:
            encrypted_package: Dictionary with encrypted data and metadata
            
        Returns:
            Decrypted data string
        """
        try:
            from cryptography.fernet import Fernet
            import base64
            
            # Verify integrity first
            encrypted_data_bytes = base64.b64decode(encrypted_package['encrypted_data'])
            expected_hash = hmac.new(
                self.hmac_key,
                encrypted_data_bytes,
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(expected_hash, encrypted_package['integrity_hash']):
                raise ValueError("Data integrity check failed")
            
            # Derive key with context
            context = encrypted_package.get('encryption_context', '')
            context_key = self._derive_key_with_context(context)
            fernet = Fernet(base64.urlsafe_b64encode(context_key))
            
            # Decrypt the data
            decrypted_data = fernet.decrypt(encrypted_data_bytes)
            return decrypted_data.decode()
            
        except ImportError:
            # Fallback for basic encoding
            logger.warning("Cryptography library not available, using basic decoding")
            return base64.b64decode(encrypted_package['encrypted_data']).decode()
        except Exception as e:
            logger.error(f"Decryption failed: {str(e)}")
            raise
    
    def _derive_key_with_context(self, context: str) -> bytes:
        """Derive encryption key with context for key separation."""
        context_bytes = context.encode() if context else b''
        return hashlib.pbkdf2_hmac('sha256', self.encryption_key, context_bytes, 100000)[:32]
    
    def detect_and_mask_pii(self, text: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Detect and mask PII in text.
        
        Args:
            text: Text to scan for PII
            
        Returns:
            Tuple of (masked_text, pii_detections)
        """
        pii_detections = []
        masked_text = text
        
        # Email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.finditer(email_pattern, text)
        for match in emails:
            email = match.group()
            masked_email = self._mask_email(email)
            masked_text = masked_text.replace(email, masked_email)
            pii_detections.append({
                'type': 'email',
                'original': email,
                'masked': masked_email,
                'position': match.span()
            })
        
        # Phone numbers (UK format)
        phone_patterns = [
            r'\b(?:\+44|0)(?:\d{2,4}\s?\d{3,4}\s?\d{3,4}|\d{10,11})\b',
            r'\b\d{3}-\d{3}-\d{4}\b',
            r'\b\(\d{3}\)\s?\d{3}-\d{4}\b'
        ]
        
        for pattern in phone_patterns:
            phones = re.finditer(pattern, masked_text)
            for match in phones:
                phone = match.group()
                masked_phone = self._mask_phone(phone)
                masked_text = masked_text.replace(phone, masked_phone)
                pii_detections.append({
                    'type': 'phone',
                    'original': phone,
                    'masked': masked_phone,
                    'position': match.span()
                })
        
        # Potential names (capitalized words that might be names)
        name_pattern = r'\b[A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}\b'
        names = re.finditer(name_pattern, masked_text)
        for match in names:
            name = match.group()
            # Skip common non-name phrases
            if not self._is_likely_name(name):
                continue
            
            masked_name = self._mask_name(name)
            masked_text = masked_text.replace(name, masked_name)
            pii_detections.append({
                'type': 'potential_name',
                'original': name,
                'masked': masked_name,
                'position': match.span()
            })
        
        return masked_text, pii_detections
    
    def _mask_email(self, email: str) -> str:
        """Mask email address."""
        local, domain = email.split('@')
        if len(local) <= 2:
            masked_local = '*' * len(local)
        else:
            masked_local = local[0] + '*' * (len(local) - 2) + local[-1]
        
        domain_parts = domain.split('.')
        if len(domain_parts[0]) <= 2:
            masked_domain = '*' * len(domain_parts[0])
        else:
            masked_domain = domain_parts[0][0] + '*' * (len(domain_parts[0]) - 2) + domain_parts[0][-1]
        
        return f"{masked_local}@{masked_domain}.{'.'.join(domain_parts[1:])}"
    
    def _mask_phone(self, phone: str) -> str:
        """Mask phone number."""
        digits_only = re.sub(r'\D', '', phone)
        if len(digits_only) >= 4:
            masked_digits = '*' * (len(digits_only) - 4) + digits_only[-4:]
        else:
            masked_digits = '*' * len(digits_only)
        
        # Preserve original formatting
        masked_phone = phone
        for i, char in enumerate(phone):
            if char.isdigit():
                digit_index = len([c for c in phone[:i] if c.isdigit()])
                if digit_index < len(masked_digits):
                    masked_phone = masked_phone[:i] + masked_digits[digit_index] + masked_phone[i+1:]
        
        return masked_phone
    
    def _mask_name(self, name: str) -> str:
        """Mask potential name."""
        parts = name.split()
        masked_parts = []
        for part in parts:
            if len(part) <= 2:
                masked_parts.append('*' * len(part))
            else:
                masked_parts.append(part[0] + '*' * (len(part) - 2) + part[-1])
        return ' '.join(masked_parts)
    
    def _is_likely_name(self, text: str) -> bool:
        """Check if text is likely a person's name."""
        # Skip common non-name phrases
        non_names = {
            'GCSE Mathematics', 'Edexcel GCSE', 'Foundation Tier', 'Higher Tier',
            'Question Generator', 'Mark Scheme', 'Assessment Objective'
        }
        
        if text in non_names:
            return False
        
        # Skip if contains numbers
        if re.search(r'\d', text):
            return False
        
        # Skip if all caps (likely acronym)
        if text.isupper():
            return False
        
        return True
    
    def validate_data_isolation(self, user_id: str, data_user_id: str) -> bool:
        """Validate that user can only access their own data.
        
        Args:
            user_id: ID of the requesting user
            data_user_id: ID of the user who owns the data
            
        Returns:
            True if access is allowed
        """
        if not user_id or not data_user_id:
            return False
        
        # Users can only access their own data
        return user_id == data_user_id
    
    def create_audit_trail(self, user_id: str, action: str, resource: str, 
                          additional_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create audit trail entry for data access.
        
        Args:
            user_id: ID of the user performing the action
            action: Action being performed (read, write, delete, etc.)
            resource: Resource being accessed
            additional_data: Additional audit data
            
        Returns:
            Audit trail entry
        """
        audit_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': user_id,
            'action': action,
            'resource': resource,
            'additional_data': additional_data or {},
            'audit_id': secrets.token_hex(16)
        }
        
        # Log audit entry
        logger.info(
            f"Audit: {action} on {resource}",
            extra={
                "audit_trail": True,
                "user_id": user_id,
                "action": action,
                "resource": resource,
                "audit_id": audit_entry['audit_id'],
                "timestamp": audit_entry['timestamp']
            }
        )
        
        return audit_entry
    
    def sanitize_for_storage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize data before storage to remove/mask PII.
        
        Args:
            data: Data dictionary to sanitize
            
        Returns:
            Sanitized data dictionary
        """
        sanitized_data = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                # Check for PII and mask if found
                masked_value, pii_detections = self.detect_and_mask_pii(value)
                sanitized_data[key] = masked_value
                
                # Log PII detection for audit
                if pii_detections:
                    logger.warning(
                        f"PII detected in field {key}",
                        extra={
                            "pii_detection": True,
                            "field": key,
                            "pii_types": [detection['type'] for detection in pii_detections],
                            "detection_count": len(pii_detections)
                        }
                    )
            
            elif isinstance(value, dict):
                # Recursively sanitize nested dictionaries
                sanitized_data[key] = self.sanitize_for_storage(value)
            
            elif isinstance(value, list):
                # Sanitize list items
                sanitized_list = []
                for item in value:
                    if isinstance(item, str):
                        masked_item, _ = self.detect_and_mask_pii(item)
                        sanitized_list.append(masked_item)
                    elif isinstance(item, dict):
                        sanitized_list.append(self.sanitize_for_storage(item))
                    else:
                        sanitized_list.append(item)
                sanitized_data[key] = sanitized_list
            
            else:
                # Keep non-string values as-is
                sanitized_data[key] = value
        
        return sanitized_data
    
    def get_data_retention_policy(self, data_type: str) -> Dict[str, Any]:
        """Get data retention policy for different data types.
        
        Args:
            data_type: Type of data (session, feedback, audit, etc.)
            
        Returns:
            Retention policy configuration
        """
        retention_policies = {
            'session': {
                'retention_days': 7,
                'auto_delete': True,
                'encryption_required': False,
                'pii_masking_required': True
            },
            'feedback': {
                'retention_days': 365,
                'auto_delete': False,
                'encryption_required': False,
                'pii_masking_required': True
            },
            'audit': {
                'retention_days': 2555,  # 7 years
                'auto_delete': False,
                'encryption_required': True,
                'pii_masking_required': True
            },
            'user_profile': {
                'retention_days': -1,  # Indefinite until user deletion
                'auto_delete': False,
                'encryption_required': True,
                'pii_masking_required': False  # User data, not masked
            },
            'question_bank': {
                'retention_days': 1095,  # 3 years
                'auto_delete': False,
                'encryption_required': False,
                'pii_masking_required': True
            }
        }
        
        return retention_policies.get(data_type, {
            'retention_days': 30,
            'auto_delete': True,
            'encryption_required': True,
            'pii_masking_required': True
        })