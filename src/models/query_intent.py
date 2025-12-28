"""Query Intent data model for structured query representation."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class QueryIntent:
    """Structured representation of a parsed natural language query.
    
    Attributes:
        topic: Main subject area (e.g., "Number", "Algebra", "Geometry")
        subtopic: Specific subtopic within the domain (e.g., "Fractions", "Linear Equations")
        tier: Difficulty tier ("Foundation" or "Higher")
        count: Number of questions requested (1-50)
        marks: Total marks requested (optional)
        confidence: Parsing confidence score (0.0-1.0)
        specification_version: Version of specification to use
    """
    topic: str
    tier: str
    count: int
    confidence: float
    subtopic: Optional[str] = None
    marks: Optional[int] = None
    specification_version: str = "latest"
    
    def __post_init__(self):
        """Validate QueryIntent fields after initialization."""
        if self.tier not in ["Foundation", "Higher"]:
            raise ValueError(f"Invalid tier: {self.tier}. Must be 'Foundation' or 'Higher'")
        
        if not (1 <= self.count <= 50):
            raise ValueError(f"Invalid count: {self.count}. Must be between 1 and 50")
        
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"Invalid confidence: {self.confidence}. Must be between 0.0 and 1.0")
        
        if self.marks is not None and self.marks < 1:
            raise ValueError(f"Invalid marks: {self.marks}. Must be positive")