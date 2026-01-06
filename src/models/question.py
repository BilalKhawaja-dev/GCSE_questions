"""Question data model for generated exam questions."""

from dataclasses import dataclass
from typing import List, Optional


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