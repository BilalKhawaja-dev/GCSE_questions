"""Mark Scheme data model for question marking criteria."""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class MarkScheme:
    """Represents marking criteria for a GCSE exam question.
    
    Attributes:
        question_id: ID of the associated question
        marking_criteria: Detailed marking criteria text
        method_marks: Marks awarded for method/working
        accuracy_marks: Marks awarded for correct answer
        total_marks: Total marks available (should equal method + accuracy)
        common_errors: List of common student errors to watch for
    """
    question_id: str
    marking_criteria: str
    method_marks: int
    accuracy_marks: int
    total_marks: int
    common_errors: Optional[List[str]] = None
    
    def __post_init__(self):
        """Validate MarkScheme fields after initialization."""
        if not self.question_id:
            raise ValueError("Question ID cannot be empty")
        
        if not self.marking_criteria:
            raise ValueError("Marking criteria cannot be empty")
        
        if self.method_marks < 0:
            raise ValueError(f"Invalid method marks: {self.method_marks}. Must be non-negative")
        
        if self.accuracy_marks < 0:
            raise ValueError(f"Invalid accuracy marks: {self.accuracy_marks}. Must be non-negative")
        
        if self.total_marks != (self.method_marks + self.accuracy_marks):
            raise ValueError(
                f"Total marks ({self.total_marks}) must equal method marks ({self.method_marks}) "
                f"+ accuracy marks ({self.accuracy_marks})"
            )
        
        if self.total_marks < 1:
            raise ValueError(f"Invalid total marks: {self.total_marks}. Must be positive")
        
        # Initialize empty list if None
        if self.common_errors is None:
            self.common_errors = []