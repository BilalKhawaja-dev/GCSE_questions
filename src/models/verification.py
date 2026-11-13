"""Verification data models for question verification system."""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class CheckResult:
    """Result from a single verification check."""
    pass_: bool
    reason: Optional[str] = None
    confidence: float = 1.0
    details: Optional[Dict[str, Any]] = None


@dataclass
class VerificationResult:
    """Complete verification result for a question."""
    question_id: str
    verdict: str  # "PASS" or "FAIL"
    verification_results: Dict[str, Any]
    overall_confidence: float
    timestamp: str
    failure_reasons: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate VerificationResult fields."""
        if self.verdict not in ["PASS", "FAIL"]:
            raise ValueError(f"Invalid verdict: {self.verdict}. Must be 'PASS' or 'FAIL'")
        
        if not 0.0 <= self.overall_confidence <= 1.0:
            raise ValueError(f"Invalid confidence: {self.overall_confidence}. Must be between 0.0 and 1.0")


@dataclass
class DeterministicCheckResult:
    """Result from deterministic verification layer."""
    pass_: bool
    issues: List[str] = field(default_factory=list)
    checks_performed: List[str] = field(default_factory=list)


@dataclass
class SymPyVerificationResult:
    """Result from SymPy mathematical verification."""
    applicable: bool
    pass_: Optional[bool] = None
    confidence: float = 0.0
    solved_answer: Optional[str] = None
    reason: Optional[str] = None
    distractor_quality: Optional[Dict[str, Any]] = None


@dataclass
class LLMAuditResult:
    """Result from LLM auditor verification."""
    verdict: str  # "PASS" or "FAIL"
    solved_answer: str
    key_answer: str
    agreement: bool
    ambiguity: str  # "none", "multiple-correct", "unclear-stem", "missing-info"
    issues: List[str]
    confidence: float
    working: Optional[str] = None
    
    def __post_init__(self):
        """Validate LLMAuditResult fields."""
        if self.verdict not in ["PASS", "FAIL"]:
            raise ValueError(f"Invalid verdict: {self.verdict}")
        
        valid_ambiguity = ["none", "multiple-correct", "unclear-stem", "missing-info"]
        if self.ambiguity not in valid_ambiguity:
            raise ValueError(f"Invalid ambiguity: {self.ambiguity}. Must be one of {valid_ambiguity}")
        
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Invalid confidence: {self.confidence}")


@dataclass
class SourceCheck:
    """Result from KB source alignment check."""
    pass_: bool
    confidence: float
    reasoning: str
    supported: bool = False


@dataclass
class SyllabusCheck:
    """Result from KB syllabus compliance check."""
    pass_: bool
    confidence: float
    reasoning: str
    in_scope: bool = False


@dataclass
class AlignmentResult:
    """Result from KB alignment verification."""
    pass_: bool
    source_alignment: SourceCheck
    syllabus_compliance: SyllabusCheck


@dataclass
class DedupeResult:
    """Result from deduplication check."""
    pass_: bool
    max_similarity: float
    similar_question_id: Optional[str] = None
    
    def __post_init__(self):
        """Validate DedupeResult fields."""
        if not 0.0 <= self.max_similarity <= 1.0:
            raise ValueError(f"Invalid similarity: {self.max_similarity}")
