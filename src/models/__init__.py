# Core data models for GCSE Question Generator
from .query_intent import QueryIntent
from .question import Question
from .mark_scheme import MarkScheme
from .specification_content import SpecificationContent
from .user import User, UserSession, AuthRequest, AuthResponse
from .verification import (
    CheckResult,
    VerificationResult,
    DeterministicCheckResult,
    SymPyVerificationResult,
    LLMAuditResult,
    SourceCheck,
    SyllabusCheck,
    AlignmentResult,
    DedupeResult
)

__all__ = [
    "QueryIntent",
    "Question",
    "MarkScheme",
    "SpecificationContent",
    "User",
    "UserSession",
    "AuthRequest",
    "AuthResponse",
    "CheckResult",
    "VerificationResult",
    "DeterministicCheckResult",
    "SymPyVerificationResult",
    "LLMAuditResult",
    "SourceCheck",
    "SyllabusCheck",
    "AlignmentResult",
    "DedupeResult"
]