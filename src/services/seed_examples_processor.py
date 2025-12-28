"""
Seed Examples Processor for GCSE Question Generator

This module handles:
1. Example question parsing and validation
2. JSON structure creation for examples storage
3. Quality scoring for seed examples
"""

import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import re

logger = logging.getLogger(__name__)


@dataclass
class ExampleQuestion:
    """Represents a parsed example question"""
    id: str
    question_text: str
    marks: int
    tier: str
    topic: str
    subtopic: Optional[str] = None
    mathematical_elements: Optional[List[str]] = None


@dataclass
class ExampleMarkScheme:
    """Represents a parsed example mark scheme"""
    question_id: str
    marking_criteria: str
    method_marks: int
    accuracy_marks: int
    total_marks: int
    common_errors: Optional[List[str]] = None


@dataclass
class ValidatedSeedExample:
    """Represents a validated seed example with quality metrics"""
    question: ExampleQuestion
    mark_scheme: ExampleMarkScheme
    quality_score: float
    verification_status: str
    domain: str
    subtopic: str
    validation_errors: List[str]


class SeedExamplesProcessor:
    """Processor for seed examples with validation and quality scoring"""
    
    # Quality scoring weights
    QUALITY_WEIGHTS = {
        'question_length': 0.15,
        'mathematical_content': 0.25,
        'mark_scheme_detail': 0.20,
        'tier_appropriateness': 0.15,
        'marks_alignment': 0.25
    }
    
    # Mathematical element patterns
    MATH_PATTERNS = {
        'arithmetic': r'[+\-×÷=]',
        'fractions': r'\d+/\d+',
        'decimals': r'\d+\.\d+',
        'percentages': r'\d+%',
        'algebra': r'[a-z]\s*[+\-=]|[a-z]\^?\d*',
        'geometry': r'angle|degree|°|triangle|circle',
        'statistics': r'mean|median|mode|average|frequency'
    }
    
    def __init__(self):
        """Initialize the seed examples processor"""
        pass
    
    def parse_example_question(self, question_data: Dict[str, Any]) -> Optional[ExampleQuestion]:
        """
        Parse raw question data into ExampleQuestion object.
        
        Args:
            question_data: Raw question data dictionary
            
        Returns:
            ExampleQuestion object or None if parsing fails
        """
        try:
            # Validate required fields
            required_fields = ['question_text', 'marks', 'tier', 'topic']
            missing_fields = [field for field in required_fields if field not in question_data]
            
            if missing_fields:
                logger.warning(f"Question missing required fields: {missing_fields}")
                return None
            
            # Extract mathematical elements
            mathematical_elements = self._extract_mathematical_elements(
                question_data['question_text']
            )
            
            # Determine subtopic
            subtopic = self._determine_subtopic_from_question(
                question_data['question_text'], 
                question_data['topic']
            )
            
            return ExampleQuestion(
                id=question_data.get('id', self._generate_question_id()),
                question_text=question_data['question_text'],
                marks=int(question_data['marks']),
                tier=question_data['tier'],
                topic=question_data['topic'],
                subtopic=subtopic,
                mathematical_elements=mathematical_elements
            )
            
        except (ValueError, KeyError) as e:
            logger.error(f"Error parsing question data: {str(e)}")
            return None
    
    def parse_example_mark_scheme(self, mark_scheme_data: Dict[str, Any]) -> Optional[ExampleMarkScheme]:
        """
        Parse raw mark scheme data into ExampleMarkScheme object.
        
        Args:
            mark_scheme_data: Raw mark scheme data dictionary
            
        Returns:
            ExampleMarkScheme object or None if parsing fails
        """
        try:
            # Validate required fields
            if 'marking_criteria' not in mark_scheme_data:
                logger.warning("Mark scheme missing marking_criteria")
                return None
            
            # Extract marks breakdown
            method_marks, accuracy_marks = self._extract_marks_breakdown(
                mark_scheme_data.get('marking_criteria', ''),
                mark_scheme_data.get('method_marks', 0),
                mark_scheme_data.get('accuracy_marks', 0)
            )
            
            total_marks = method_marks + accuracy_marks
            
            # Extract common errors if mentioned
            common_errors = self._extract_common_errors(
                mark_scheme_data.get('marking_criteria', '')
            )
            
            return ExampleMarkScheme(
                question_id=mark_scheme_data.get('question_id', ''),
                marking_criteria=mark_scheme_data['marking_criteria'],
                method_marks=method_marks,
                accuracy_marks=accuracy_marks,
                total_marks=total_marks,
                common_errors=common_errors
            )
            
        except (ValueError, KeyError) as e:
            logger.error(f"Error parsing mark scheme data: {str(e)}")
            return None
    
    def validate_seed_example(
        self, 
        question: ExampleQuestion, 
        mark_scheme: ExampleMarkScheme
    ) -> ValidatedSeedExample:
        """
        Validate a seed example and calculate quality score.
        
        Args:
            question: Parsed question object
            mark_scheme: Parsed mark scheme object
            
        Returns:
            ValidatedSeedExample with quality metrics
        """
        validation_errors = []
        
        # Validate marks alignment
        if question.marks != mark_scheme.total_marks:
            validation_errors.append(
                f"Marks mismatch: question={question.marks}, mark_scheme={mark_scheme.total_marks}"
            )
        
        # Validate question quality
        if len(question.question_text) < 10:
            validation_errors.append("Question text too short")
        
        if not question.question_text.strip().endswith(('?', '.')):
            validation_errors.append("Question text should end with punctuation")
        
        # Validate mark scheme quality
        if len(mark_scheme.marking_criteria) < 20:
            validation_errors.append("Mark scheme criteria too brief")
        
        # Calculate quality score
        quality_score = self._calculate_comprehensive_quality_score(question, mark_scheme)
        
        # Determine domain and subtopic
        domain = self._determine_domain(question.topic)
        subtopic = question.subtopic or self._determine_subtopic_from_question(
            question.question_text, question.topic
        )
        
        # Determine verification status
        verification_status = "verified" if len(validation_errors) == 0 else "needs_review"
        
        return ValidatedSeedExample(
            question=question,
            mark_scheme=mark_scheme,
            quality_score=quality_score,
            verification_status=verification_status,
            domain=domain,
            subtopic=subtopic,
            validation_errors=validation_errors
        )
    
    def _extract_mathematical_elements(self, question_text: str) -> List[str]:
        """Extract mathematical elements from question text"""
        elements = []
        
        for element_type, pattern in self.MATH_PATTERNS.items():
            if re.search(pattern, question_text, re.IGNORECASE):
                elements.append(element_type)
        
        return elements
    
    def _determine_subtopic_from_question(self, question_text: str, topic: str) -> str:
        """Determine subtopic based on question content"""
        text_lower = question_text.lower()
        
        # Topic-specific subtopic detection
        if topic.lower() == 'number':
            if 'fraction' in text_lower:
                return 'fractions'
            elif 'decimal' in text_lower:
                return 'decimals'
            elif 'percentage' in text_lower or '%' in text_lower:
                return 'percentages'
            elif 'ratio' in text_lower:
                return 'ratio'
        elif topic.lower() == 'algebra':
            if 'quadratic' in text_lower or 'x²' in text_lower:
                return 'quadratics'
            elif 'simultaneous' in text_lower:
                return 'simultaneous-equations'
            else:
                return 'linear-equations'
        elif topic.lower() == 'geometry':
            if 'trigonometry' in text_lower or any(trig in text_lower for trig in ['sin', 'cos', 'tan']):
                return 'trigonometry'
            elif 'pythagoras' in text_lower:
                return 'pythagoras'
            else:
                return 'angles'
        elif topic.lower() == 'statistics':
            if 'probability' in text_lower:
                return 'probability'
            else:
                return 'data-analysis'
        
        return topic.lower()
    
    def _extract_marks_breakdown(self, criteria: str, method_marks: int, accuracy_marks: int) -> tuple:
        """Extract method and accuracy marks from criteria"""
        # If marks are already provided, use them
        if method_marks > 0 or accuracy_marks > 0:
            return method_marks, accuracy_marks
        
        # Try to extract from criteria text
        method_match = re.search(r'method[:\s]*(\d+)', criteria.lower())
        accuracy_match = re.search(r'accuracy[:\s]*(\d+)', criteria.lower())
        
        method = int(method_match.group(1)) if method_match else 1
        accuracy = int(accuracy_match.group(1)) if accuracy_match else 1
        
        return method, accuracy
    
    def _extract_common_errors(self, criteria: str) -> List[str]:
        """Extract common errors from marking criteria"""
        errors = []
        
        # Look for common error patterns
        error_patterns = [
            r'common error[:\s]*([^.]+)',
            r'mistake[:\s]*([^.]+)',
            r'incorrect[:\s]*([^.]+)'
        ]
        
        for pattern in error_patterns:
            matches = re.findall(pattern, criteria.lower())
            errors.extend(matches)
        
        return errors[:3]  # Limit to 3 common errors
    
    def _calculate_comprehensive_quality_score(
        self, 
        question: ExampleQuestion, 
        mark_scheme: ExampleMarkScheme
    ) -> float:
        """Calculate comprehensive quality score using weighted factors"""
        
        scores = {}
        
        # Question length score (optimal: 50-200 characters)
        length = len(question.question_text)
        if 50 <= length <= 200:
            scores['question_length'] = 1.0
        elif 30 <= length < 50 or 200 < length <= 300:
            scores['question_length'] = 0.7
        else:
            scores['question_length'] = 0.3
        
        # Mathematical content score
        math_elements = len(question.mathematical_elements or [])
        scores['mathematical_content'] = min(1.0, math_elements * 0.3)
        
        # Mark scheme detail score
        criteria_length = len(mark_scheme.marking_criteria)
        if criteria_length >= 50:
            scores['mark_scheme_detail'] = 1.0
        elif criteria_length >= 20:
            scores['mark_scheme_detail'] = 0.7
        else:
            scores['mark_scheme_detail'] = 0.3
        
        # Tier appropriateness score (heuristic based on complexity)
        complexity_indicators = len(re.findall(r'[+\-×÷=()]', question.question_text))
        if question.tier == 'Foundation':
            scores['tier_appropriateness'] = 1.0 if complexity_indicators <= 5 else 0.6
        else:  # Higher tier
            scores['tier_appropriateness'] = 1.0 if complexity_indicators >= 3 else 0.7
        
        # Marks alignment score
        if question.marks == mark_scheme.total_marks:
            scores['marks_alignment'] = 1.0
        else:
            scores['marks_alignment'] = 0.0
        
        # Calculate weighted average
        total_score = sum(
            scores[factor] * self.QUALITY_WEIGHTS[factor] 
            for factor in scores
        )
        
        return round(total_score, 2)
    
    def _determine_domain(self, topic: str) -> str:
        """Determine domain from topic"""
        topic_lower = topic.lower()
        
        if any(word in topic_lower for word in ['number', 'fraction', 'decimal', 'percentage']):
            return 'number'
        elif any(word in topic_lower for word in ['algebra', 'equation', 'quadratic']):
            return 'algebra'
        elif any(word in topic_lower for word in ['geometry', 'angle', 'trigonometry']):
            return 'geometry'
        elif any(word in topic_lower for word in ['statistics', 'probability', 'data']):
            return 'statistics'
        
        return 'general'
    
    def _generate_question_id(self) -> str:
        """Generate a unique question ID"""
        import uuid
        return f"q_{uuid.uuid4().hex[:8]}"
    
    def create_examples_json_structure(
        self, 
        validated_examples: List[ValidatedSeedExample], 
        domain: str, 
        subtopic: str
    ) -> Dict[str, Any]:
        """
        Create JSON structure for examples storage.
        
        Args:
            validated_examples: List of validated seed examples
            domain: Domain name
            subtopic: Subtopic name
            
        Returns:
            Dictionary ready for JSON serialization
        """
        examples_data = []
        
        for example in validated_examples:
            example_dict = {
                "question": asdict(example.question),
                "mark_scheme": asdict(example.mark_scheme),
                "quality_score": example.quality_score,
                "verification_status": example.verification_status
            }
            
            # Add validation info if there are errors
            if example.validation_errors:
                example_dict["validation_errors"] = example.validation_errors
            
            examples_data.append(example_dict)
        
        return {
            "domain": domain,
            "subtopic": subtopic,
            "total_examples": len(examples_data),
            "average_quality_score": round(
                sum(ex.quality_score for ex in validated_examples) / len(validated_examples), 2
            ) if validated_examples else 0.0,
            "examples": examples_data
        }
    
    def process_examples_batch(
        self, 
        raw_examples: List[Dict[str, Any]]
    ) -> Dict[str, List[ValidatedSeedExample]]:
        """
        Process a batch of raw examples and organize by domain/subtopic.
        
        Args:
            raw_examples: List of raw example dictionaries
            
        Returns:
            Dictionary organized by domain/subtopic
        """
        organized_examples = {}
        processed_count = 0
        
        for raw_example in raw_examples:
            try:
                # Parse question and mark scheme
                question = self.parse_example_question(raw_example.get('question', {}))
                mark_scheme = self.parse_example_mark_scheme(raw_example.get('mark_scheme', {}))
                
                if not question or not mark_scheme:
                    logger.warning("Failed to parse example, skipping")
                    continue
                
                # Validate the example
                validated_example = self.validate_seed_example(question, mark_scheme)
                
                # Organize by domain/subtopic
                key = f"{validated_example.domain}/{validated_example.subtopic}"
                if key not in organized_examples:
                    organized_examples[key] = []
                
                organized_examples[key].append(validated_example)
                processed_count += 1
                
            except Exception as e:
                logger.error(f"Error processing example: {str(e)}")
                continue
        
        logger.info(f"Successfully processed {processed_count}/{len(raw_examples)} examples")
        return organized_examples