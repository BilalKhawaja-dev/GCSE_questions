"""Question data model for generated exam questions."""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class Question:
    """Represents a generated GCSE exam question.
    
    Attributes:
        id: Unique identifier for the question
        question_text: The actual question text with LaTeX notation
        marks: Total marks available for this question
        tier: Difficulty tier ("Foundation" or "Higher")
        topic: Main subject area
        subtopic: Specific subtopic (optional)
        difficulty_score: Numeric difficulty rating (1-10 scale)
        mathematical_elements: List of mathematical concepts present
        difficulty_indicators: List of difficulty indicators
        
        # Verification metadata (for question bank system)
        verification_status: Verification status ("PENDING", "VERIFIED", "REJECTED", "VERIFICATION_ERROR")
        verification_timestamp: ISO timestamp of verification
        verification_confidence: Overall confidence score (0.0-1.0)
        verification_results: Detailed results from each verification layer
        embedding: Vector embedding for similarity detection (1024-dim)
        answer_forms: Canonical forms of answers for validation
        times_served: Number of times question has been served to users
        last_served: ISO timestamp of last time served
        user_feedback_score: Average user feedback score
        reported_issues: Count of user-reported issues
    """
    id: str
    question_text: str
    marks: int
    tier: str
    topic: str
    difficulty_score: int
    subtopic: Optional[str] = None
    mathematical_elements: Optional[List[str]] = None
    difficulty_indicators: Optional[List[str]] = None
    
    # Verification metadata
    verification_status: str = "PENDING"
    verification_timestamp: Optional[str] = None
    verification_confidence: Optional[float] = None
    verification_results: Optional[Dict[str, Any]] = None
    embedding: Optional[List[float]] = None
    answer_forms: Optional[Dict[str, Any]] = None
    times_served: int = 0
    last_served: Optional[str] = None
    user_feedback_score: Optional[float] = None
    reported_issues: int = 0
    
    def __post_init__(self):
        """Validate Question fields after initialization."""
        if not self.id:
            raise ValueError("Question ID cannot be empty")
        
        if not self.question_text:
            raise ValueError("Question text cannot be empty")
        
        if self.marks < 1:
            raise ValueError(f"Invalid marks: {self.marks}. Must be positive")
        
        if self.tier not in ["Foundation", "Higher"]:
            raise ValueError(f"Invalid tier: {self.tier}. Must be 'Foundation' or 'Higher'")
        
        if not self.topic:
            raise ValueError("Topic cannot be empty")
        
        # Validate difficulty score
        if not isinstance(self.difficulty_score, int) or not (1 <= self.difficulty_score <= 10):
            raise ValueError(f"Invalid difficulty_score: {self.difficulty_score}. Must be integer between 1-10")
        
        # Validate difficulty score matches tier expectations
        if self.tier == "Foundation" and self.difficulty_score > 5:
            raise ValueError(f"Foundation tier difficulty_score {self.difficulty_score} should be 1-5")
        elif self.tier == "Higher" and self.difficulty_score < 6:
            raise ValueError(f"Higher tier difficulty_score {self.difficulty_score} should be 6-10")
        
        # Initialize empty lists if None
        if self.mathematical_elements is None:
            self.mathematical_elements = []
        
        if self.difficulty_indicators is None:
            self.difficulty_indicators = []
        
        # Validate verification status
        valid_statuses = ["PENDING", "VERIFIED", "REJECTED", "VERIFICATION_ERROR"]
        if self.verification_status not in valid_statuses:
            raise ValueError(f"Invalid verification_status: {self.verification_status}. Must be one of {valid_statuses}")
        
        # Validate verification confidence if provided
        if self.verification_confidence is not None:
            if not 0.0 <= self.verification_confidence <= 1.0:
                raise ValueError(f"Invalid verification_confidence: {self.verification_confidence}. Must be between 0.0 and 1.0")