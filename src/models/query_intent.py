"""Query Intent data model for structured query representation."""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class QueryIntent:
    """Structured representation of a parsed natural language query.
    
    Attributes:
        topic: Main subject area (e.g., "Number", "Algebra", "Geometry")
        subtopic: Specific subtopic within the domain (e.g., "Fractions", "Linear Equations")
        tier: Difficulty tier ("Foundation" or "Higher")
        count: Number of questions requested (1-100, increased from 50 for V2)
        marks: Total marks requested (optional)
        confidence: Parsing confidence score (0.0-1.0)
        specification_version: Version of specification to use
        subtopics: List of subtopics if multiple are identified (V2 enhancement)
    """
    topic: str
    tier: str
    count: int
    confidence: float
    subtopic: Optional[str] = None
    marks: Optional[int] = None
    specification_version: str = "latest"
    subtopics: Optional[List[str]] = None
    
    def __post_init__(self):
        """Validate QueryIntent fields after initialization."""
        if self.tier not in ["Foundation", "Higher"]:
            raise ValueError(f"Invalid tier: {self.tier}. Must be 'Foundation' or 'Higher'")
        
        # V2 enhancement: increased limit from 50 to 100
        if not (1 <= self.count <= 100):
            raise ValueError(f"Invalid count: {self.count}. Must be between 1 and 100")
        
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"Invalid confidence: {self.confidence}. Must be between 0.0 and 1.0")
        
        if self.marks is not None and self.marks < 1:
            raise ValueError(f"Invalid marks: {self.marks}. Must be positive")


@dataclass
class EnhancedInterpretResponse:
    """Enhanced response structure for V2 InterpretLambda with prompt enrichment.
    
    This response includes the original intent plus enriched prompt data
    for GenerateLambda to use.
    """
    intent: QueryIntent
    enriched_prompt: str
    difficulty_guidance: Dict[str, Any]
    topic_coverage: Dict[str, Any]
    specification_context: Dict[str, Any]
    request_id: str
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "intent": {
                "topic": self.intent.topic,
                "subtopic": self.intent.subtopic,
                "tier": self.intent.tier,
                "count": self.intent.count,
                "subtopics": self.intent.subtopics or []
            },
            "enriched_prompt": self.enriched_prompt,
            "difficulty_guidance": self.difficulty_guidance,
            "topic_coverage": self.topic_coverage,
            "specification_context": self.specification_context,
            "request_id": self.request_id,
            "timestamp": self.timestamp
        }