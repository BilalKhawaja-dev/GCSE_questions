"""Specification Content data model for curriculum specifications."""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class SpecificationContent:
    """Represents Edexcel GCSE specification content.
    
    Attributes:
        content: The actual specification text content
        topic: Main subject area
        tier: Difficulty tier ("Foundation", "Higher", or "both")
        version: Specification version identifier
        learning_objectives: List of learning objectives
        domain: Subject domain (e.g., "number", "algebra")
        subtopic: Specific subtopic within the domain
        key_concepts: List of key mathematical concepts
        common_misconceptions: List of common student misconceptions
        assessment_objectives: List of assessment objective codes
        marks_range: Typical marks range for this topic [min, max]
    """
    content: str
    topic: str
    tier: str
    version: str
    learning_objectives: List[str]
    domain: Optional[str] = None
    subtopic: Optional[str] = None
    key_concepts: Optional[List[str]] = None
    common_misconceptions: Optional[List[str]] = None
    assessment_objectives: Optional[List[str]] = None
    marks_range: Optional[List[int]] = None
    
    def __post_init__(self):
        """Validate SpecificationContent fields after initialization."""
        if not self.content:
            raise ValueError("Content cannot be empty")
        
        if not self.topic:
            raise ValueError("Topic cannot be empty")
        
        if self.tier not in ["Foundation", "Higher", "both"]:
            raise ValueError(f"Invalid tier: {self.tier}. Must be 'Foundation', 'Higher', or 'both'")
        
        if not self.version:
            raise ValueError("Version cannot be empty")
        
        if not self.learning_objectives:
            raise ValueError("Learning objectives cannot be empty")
        
        # Initialize empty lists if None
        if self.key_concepts is None:
            self.key_concepts = []
        
        if self.common_misconceptions is None:
            self.common_misconceptions = []
        
        if self.assessment_objectives is None:
            self.assessment_objectives = []
        
        # Validate marks_range if provided
        if self.marks_range is not None:
            if len(self.marks_range) != 2:
                raise ValueError("Marks range must contain exactly 2 values [min, max]")
            if self.marks_range[0] > self.marks_range[1]:
                raise ValueError("Marks range minimum cannot be greater than maximum")