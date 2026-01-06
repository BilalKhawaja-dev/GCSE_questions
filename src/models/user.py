"""
User data model for authentication system.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class User:
    """User model for authentication and profile management."""
    
    username: str
    password_hash: str
    email: str
    school: Optional[str] = None
    subject_specialization: Optional[str] = None
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    
    def to_dynamodb_item(self) -> dict:
        """Convert user to DynamoDB item format."""
        item = {
            'pk': f'USER#{self.username}',
            'username': self.username,
            'password_hash': self.password_hash,
            'email': self.email
        }
        
        if self.school:
            item['school'] = self.school
        if self.subject_specialization:
            item['subject_specialization'] = self.subject_specialization
        if self.created_at:
            item['created_at'] = self.created_at.isoformat()
        if self.last_login:
            item['last_login'] = self.last_login.isoformat()
            
        return item
    
    @classmethod
    def from_dynamodb_item(cls, item: dict) -> 'User':
        """Create user from DynamoDB item."""
        created_at = None
        if 'created_at' in item:
            created_at = datetime.fromisoformat(item['created_at'])
            
        last_login = None
        if 'last_login' in item:
            last_login = datetime.fromisoformat(item['last_login'])
            
        return cls(
            username=item['username'],
            password_hash=item['password_hash'],
            email=item['email'],
            school=item.get('school'),
            subject_specialization=item.get('subject_specialization'),
            created_at=created_at,
            last_login=last_login
        )


@dataclass
class UserSession:
    """User session model for session management."""
    
    session_id: str
    user_id: str
    query: str
    generated_questions: list
    mark_schemes: list
    timestamp: datetime
    ttl: int  # Unix timestamp for TTL
    
    def to_dynamodb_item(self) -> dict:
        """Convert session to DynamoDB item format."""
        return {
            'pk': f'SESSION#{self.session_id}',
            'sk': f'TIMESTAMP#{self.timestamp.isoformat()}',
            'session_id': self.session_id,
            'user_id': self.user_id,
            'query': self.query,
            'generated_questions': self.generated_questions,
            'mark_schemes': self.mark_schemes,
            'timestamp': self.timestamp.isoformat(),
            'ttl': self.ttl
        }
    
    @classmethod
    def from_dynamodb_item(cls, item: dict) -> 'UserSession':
        """Create session from DynamoDB item."""
        return cls(
            session_id=item['session_id'],
            user_id=item['user_id'],
            query=item['query'],
            generated_questions=item['generated_questions'],
            mark_schemes=item['mark_schemes'],
            timestamp=datetime.fromisoformat(item['timestamp']),
            ttl=item['ttl']
        )


@dataclass
class AuthRequest:
    """Authentication request model."""
    
    action: str  # 'register', 'login', 'validate'
    username: Optional[str] = None
    password: Optional[str] = None
    email: Optional[str] = None
    school: Optional[str] = None
    subject_specialization: Optional[str] = None
    session_token: Optional[str] = None


@dataclass
class AuthResponse:
    """Authentication response model."""
    
    success: bool
    message: str
    session_token: Optional[str] = None
    user_id: Optional[str] = None
    expires_at: Optional[datetime] = None