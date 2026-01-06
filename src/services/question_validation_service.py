"""
Question validation service for comprehensive quality control.

This service provides comprehensive validation of generated questions to ensure
they meet quality standards before being returned to users.
"""

import json
import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from src.utils.math_rendering import validate_no_latex_syntax
from src.utils.constants import VALID_TOPICS, VALID_TIERS

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    CRITICAL = "critical"  # Question must be rejected
    WARNING = "warning"    # Question has issues but may be acceptable
    INFO = "info"         # Minor issues or suggestions


@dataclass
class ValidationIssue:
    """Represents a validation issue found in a question."""
    severity: ValidationSeverity
    category: str
    message: str
    field: Optional[str] = None
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of question validation."""
    is_valid: bool
    confidence_score: float  # 0.0 to 1.0
    issues: List[ValidationIssue]
    quality_metrics: Dict[str, Any]


class QuestionValidationService:
    """Service for comprehensive question validation and quality control."""
    
    # Minimum and maximum lengths for different components
    MIN_QUESTION_LENGTH = 10
    MAX_QUESTION_LENGTH = 1000
    MIN_MARK_SCHEME_LENGTH = 5
    MAX_MARK_SCHEME_LENGTH = 2000
    
    # Required mathematical elements by topic
    TOPIC_REQUIRED_ELEMENTS = {
        "number": ["calculate", "find", "work out"],
        "algebra": ["solve", "equation", "expression", "x", "y"],
        "geometry": ["angle", "area", "perimeter", "triangle", "circle", "shape"],
        "statistics": ["data", "mean", "median", "graph", "chart", "average"],
        "probability": ["probability", "chance", "outcome", "event", "likely"],
        "ratio": ["ratio", "proportion", "scale", "share"]
    }
    
    # Complexity indicators for difficulty assessment
    COMPLEXITY_INDICATORS = {
        "basic": ["add", "subtract", "multiply", "divide", "calculate", "find"],
        "intermediate": ["solve", "simplify", "expand", "factorize", "substitute"],
        "advanced": ["prove", "derive", "optimize", "analyze", "evaluate", "justify"]
    }
    
    # Common mathematical errors to check for
    COMMON_ERRORS = [
        r"\b0/0\b",  # Division by zero
        r"\b\d+/0\b",  # Division by zero
        r"√-\d+",  # Square root of negative number (without complex context)
        r"log\(-\d+\)",  # Logarithm of negative number
    ]
    
    def __init__(self):
        """Initialize the question validation service."""
        self.validation_cache = {}
    
    def validate_question(self, question: Dict[str, Any], 
                         context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """
        Perform comprehensive validation of a single question.
        
        Args:
            question: Question dictionary to validate
            context: Optional context (generation request, etc.)
            
        Returns:
            ValidationResult with detailed analysis
        """
        logger.debug(
            "Starting comprehensive question validation",
            extra={
                "question_id": question.get('id', 'unknown'),
                "topic": question.get('topic', 'unknown')
            }
        )
        
        issues = []
        confidence_score = 1.0
        quality_metrics = {}
        
        # Validate required fields
        field_issues, field_confidence = self._validate_required_fields(question)
        issues.extend(field_issues)
        confidence_score *= field_confidence
        
        # Validate question text quality
        text_issues, text_confidence, text_metrics = self._validate_question_text(question)
        issues.extend(text_issues)
        confidence_score *= text_confidence
        quality_metrics.update(text_metrics)
        
        # Validate mathematical content
        math_issues, math_confidence, math_metrics = self._validate_mathematical_content(question)
        issues.extend(math_issues)
        confidence_score *= math_confidence
        quality_metrics.update(math_metrics)
        
        # Validate difficulty alignment
        difficulty_issues, difficulty_confidence = self._validate_difficulty_alignment(question, context)
        issues.extend(difficulty_issues)
        confidence_score *= difficulty_confidence
        
        # Validate mark scheme
        mark_scheme_issues, mark_scheme_confidence = self._validate_mark_scheme(question)
        issues.extend(mark_scheme_issues)
        confidence_score *= mark_scheme_confidence
        
        # Validate topic alignment
        topic_issues, topic_confidence = self._validate_topic_alignment(question)
        issues.extend(topic_issues)
        confidence_score *= topic_confidence
        
        # Check for common mathematical errors
        error_issues = self._check_mathematical_errors(question)
        issues.extend(error_issues)
        if error_issues:
            confidence_score *= 0.5  # Significant penalty for mathematical errors
        
        # Determine overall validity
        critical_issues = [issue for issue in issues if issue.severity == ValidationSeverity.CRITICAL]
        is_valid = len(critical_issues) == 0
        
        # Add overall quality metrics
        quality_metrics.update({
            'total_issues': len(issues),
            'critical_issues': len(critical_issues),
            'warning_issues': len([i for i in issues if i.severity == ValidationSeverity.WARNING]),
            'info_issues': len([i for i in issues if i.severity == ValidationSeverity.INFO]),
            'confidence_score': confidence_score
        })
        
        result = ValidationResult(
            is_valid=is_valid,
            confidence_score=confidence_score,
            issues=issues,
            quality_metrics=quality_metrics
        )
        
        logger.debug(
            "Question validation completed",
            extra={
                "question_id": question.get('id', 'unknown'),
                "is_valid": is_valid,
                "confidence_score": confidence_score,
                "issue_count": len(issues)
            }
        )
        
        return result
    
    def validate_question_set(self, question_set: Dict[str, Any], 
                            context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Validate an entire question set and filter out invalid questions.
        
        Args:
            question_set: Question set dictionary with questions and mark schemes
            context: Optional context (generation request, etc.)
            
        Returns:
            Filtered question set with only valid questions and validation metadata
        """
        logger.info(
            "Validating question set",
            extra={"question_count": len(question_set.get('questions', []))}
        )
        
        questions = question_set.get('questions', [])
        mark_schemes = question_set.get('mark_scheme', [])
        
        valid_questions = []
        valid_mark_schemes = []
        validation_results = []
        
        for i, question in enumerate(questions):
            try:
                # Validate individual question
                validation_result = self.validate_question(question, context)
                validation_results.append(validation_result)
                
                if validation_result.is_valid:
                    valid_questions.append(question)
                    
                    # Find corresponding mark scheme
                    mark_scheme = next(
                        (ms for ms in mark_schemes if ms.get('question_id') == question.get('id')),
                        None
                    )
                    if mark_scheme:
                        valid_mark_schemes.append(mark_scheme)
                else:
                    logger.warning(
                        f"Question {i+1} failed validation",
                        extra={
                            "question_id": question.get('id', f'q{i+1}'),
                            "critical_issues": len([issue for issue in validation_result.issues 
                                                  if issue.severity == ValidationSeverity.CRITICAL]),
                            "confidence_score": validation_result.confidence_score
                        }
                    )
                    
            except Exception as e:
                logger.error(
                    f"Error validating question {i+1}: {str(e)}",
                    extra={"question_id": question.get('id', f'q{i+1}')}
                )
                # Skip this question
                continue
        
        # Calculate set-level metrics
        if validation_results:
            avg_confidence = sum(r.confidence_score for r in validation_results) / len(validation_results)
            success_rate = len(valid_questions) / len(questions) if questions else 0
        else:
            avg_confidence = 0.0
            success_rate = 0.0
        
        # Update question set
        filtered_question_set = question_set.copy()
        filtered_question_set['questions'] = valid_questions
        filtered_question_set['mark_scheme'] = valid_mark_schemes
        
        # Update metadata
        if 'metadata' not in filtered_question_set:
            filtered_question_set['metadata'] = {}
        
        filtered_question_set['metadata'].update({
            'validation': {
                'total_questions_submitted': len(questions),
                'valid_questions': len(valid_questions),
                'success_rate': success_rate,
                'average_confidence': avg_confidence,
                'validation_timestamp': logger.handlers[0].formatter.formatTime(logger.makeRecord(
                    'validation', logging.INFO, '', 0, '', (), None
                )) if logger.handlers else None
            }
        })
        
        # Recalculate total marks
        total_marks = sum(q.get('marks', 0) for q in valid_questions)
        filtered_question_set['metadata']['total_marks'] = total_marks
        
        logger.info(
            "Question set validation completed",
            extra={
                "original_count": len(questions),
                "valid_count": len(valid_questions),
                "success_rate": success_rate,
                "average_confidence": avg_confidence
            }
        )
        
        return filtered_question_set
    
    def _validate_required_fields(self, question: Dict[str, Any]) -> Tuple[List[ValidationIssue], float]:
        """Validate that all required fields are present and valid."""
        issues = []
        confidence = 1.0
        
        required_fields = ['id', 'question_text', 'marks', 'difficulty_score', 'topic', 'tier']
        
        for field in required_fields:
            if field not in question:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    category="required_fields",
                    message=f"Missing required field: {field}",
                    field=field,
                    suggestion=f"Add {field} field to question"
                ))
                confidence *= 0.7
            elif question[field] is None:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    category="required_fields",
                    message=f"Required field {field} is null",
                    field=field,
                    suggestion=f"Provide valid value for {field}"
                ))
                confidence *= 0.7
        
        return issues, confidence
    
    def _validate_question_text(self, question: Dict[str, Any]) -> Tuple[List[ValidationIssue], float, Dict[str, Any]]:
        """Validate question text quality and characteristics."""
        issues = []
        confidence = 1.0
        metrics = {}
        
        question_text = question.get('question_text', '')
        text_length = len(question_text.strip())
        
        metrics['text_length'] = text_length
        metrics['word_count'] = len(question_text.split())
        
        # Check minimum length
        if text_length < self.MIN_QUESTION_LENGTH:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                category="text_quality",
                message=f"Question text too short ({text_length} chars, minimum {self.MIN_QUESTION_LENGTH})",
                field="question_text",
                suggestion="Provide more detailed question text"
            ))
            confidence *= 0.5
        
        # Check maximum length
        if text_length > self.MAX_QUESTION_LENGTH:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="text_quality",
                message=f"Question text very long ({text_length} chars, maximum {self.MAX_QUESTION_LENGTH})",
                field="question_text",
                suggestion="Consider breaking into multiple questions"
            ))
            confidence *= 0.9
        
        # Check for LaTeX syntax (should be converted)
        if not validate_no_latex_syntax(question_text):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                category="mathematical_formatting",
                message="Question contains unconverted LaTeX syntax",
                field="question_text",
                suggestion="Convert LaTeX to plain text or Unicode"
            ))
            confidence *= 0.3
        
        # Check for question clarity indicators
        question_indicators = ['find', 'calculate', 'work out', 'determine', 'solve', 'show', 'prove']
        has_clear_instruction = any(indicator in question_text.lower() for indicator in question_indicators)
        
        if not has_clear_instruction:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="text_quality",
                message="Question may lack clear instruction",
                field="question_text",
                suggestion="Include clear instruction words like 'find', 'calculate', 'solve'"
            ))
            confidence *= 0.9
        
        metrics['has_clear_instruction'] = has_clear_instruction
        
        # Check for appropriate punctuation
        if not question_text.strip().endswith(('?', '.', ':')):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                category="text_quality",
                message="Question should end with appropriate punctuation",
                field="question_text",
                suggestion="Add question mark, period, or colon at the end"
            ))
        
        return issues, confidence, metrics
    
    def _validate_mathematical_content(self, question: Dict[str, Any]) -> Tuple[List[ValidationIssue], float, Dict[str, Any]]:
        """Validate mathematical content and complexity."""
        issues = []
        confidence = 1.0
        metrics = {}
        
        question_text = question.get('question_text', '').lower()
        
        # Count mathematical elements
        numbers_count = len(re.findall(r'\b\d+(?:\.\d+)?\b', question_text))
        fractions_count = len(re.findall(r'\b\d+/\d+\b', question_text))
        variables_count = len(re.findall(r'\b[a-z]\b', question_text))
        
        metrics.update({
            'numbers_count': numbers_count,
            'fractions_count': fractions_count,
            'variables_count': variables_count
        })
        
        # Check for mathematical content
        if numbers_count == 0 and fractions_count == 0 and variables_count == 0:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="mathematical_content",
                message="Question appears to lack mathematical content",
                field="question_text",
                suggestion="Ensure question contains appropriate mathematical elements"
            ))
            confidence *= 0.8
        
        # Check for units where appropriate
        unit_indicators = ['length', 'distance', 'area', 'volume', 'weight', 'time', 'speed']
        needs_units = any(indicator in question_text for indicator in unit_indicators)
        has_units = bool(re.search(r'\b(cm|m|km|g|kg|s|min|h|mph|kmh)\b', question_text))
        
        if needs_units and not has_units:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                category="mathematical_content",
                message="Question may need units specified",
                field="question_text",
                suggestion="Consider adding appropriate units (cm, m, kg, etc.)"
            ))
        
        metrics['needs_units'] = needs_units
        metrics['has_units'] = has_units
        
        return issues, confidence, metrics
    
    def _validate_difficulty_alignment(self, question: Dict[str, Any], 
                                     context: Optional[Dict[str, Any]]) -> Tuple[List[ValidationIssue], float]:
        """Validate difficulty score alignment with tier and content."""
        issues = []
        confidence = 1.0
        
        difficulty_score = question.get('difficulty_score')
        tier = question.get('tier', '').lower()
        marks = question.get('marks', 0)
        
        # Validate difficulty score range
        if not isinstance(difficulty_score, int) or not (1 <= difficulty_score <= 10):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                category="difficulty_alignment",
                message=f"Invalid difficulty score: {difficulty_score} (must be 1-10)",
                field="difficulty_score",
                suggestion="Set difficulty score between 1 and 10"
            ))
            confidence *= 0.5
            return issues, confidence
        
        # Validate tier-difficulty alignment
        if tier == "foundation" and difficulty_score > 5:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="difficulty_alignment",
                message=f"Difficulty score {difficulty_score} may be too high for Foundation tier",
                field="difficulty_score",
                suggestion="Consider reducing difficulty score to 1-5 for Foundation tier"
            ))
            confidence *= 0.8
        elif tier == "higher" and difficulty_score < 6:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="difficulty_alignment",
                message=f"Difficulty score {difficulty_score} may be too low for Higher tier",
                field="difficulty_score",
                suggestion="Consider increasing difficulty score to 6-10 for Higher tier"
            ))
            confidence *= 0.8
        
        # Validate marks-difficulty relationship (only if marks is valid)
        if isinstance(marks, int) and marks > 0:
            if marks >= 6 and difficulty_score <= 3:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    category="difficulty_alignment",
                    message="High mark question with low difficulty score",
                    field="difficulty_score",
                    suggestion="Consider if difficulty score matches the mark allocation"
                ))
            elif marks <= 2 and difficulty_score >= 8:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    category="difficulty_alignment",
                    message="Low mark question with high difficulty score",
                    field="difficulty_score",
                    suggestion="Consider if difficulty score matches the mark allocation"
                ))
        
        return issues, confidence
    
    def _validate_mark_scheme(self, question: Dict[str, Any]) -> Tuple[List[ValidationIssue], float]:
        """Validate marks allocation and reasonableness."""
        issues = []
        confidence = 1.0
        
        marks = question.get('marks')
        
        # Validate marks type and range
        if not isinstance(marks, int) or marks < 1:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                category="mark_scheme",
                message=f"Invalid marks allocation: {marks}",
                field="marks",
                suggestion="Set marks to positive integer"
            ))
            confidence *= 0.5
        elif marks > 20:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="mark_scheme",
                message=f"Very high marks allocation: {marks}",
                field="marks",
                suggestion="Consider if {marks} marks is appropriate for a single question"
            ))
            confidence *= 0.9
        
        return issues, confidence
    
    def _validate_topic_alignment(self, question: Dict[str, Any]) -> Tuple[List[ValidationIssue], float]:
        """Validate topic alignment and required elements."""
        issues = []
        confidence = 1.0
        
        topic = question.get('topic', '').lower()
        tier = question.get('tier', '').lower()
        question_text = question.get('question_text', '').lower()
        
        # Validate topic is recognized
        if topic not in [t.lower() for t in VALID_TOPICS]:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="topic_alignment",
                message=f"Unrecognized topic: {topic}",
                field="topic",
                suggestion=f"Use one of: {', '.join(VALID_TOPICS)}"
            ))
            confidence *= 0.8
        
        # Validate tier is recognized
        if tier not in [t.lower() for t in VALID_TIERS]:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="topic_alignment",
                message=f"Unrecognized tier: {tier}",
                field="tier",
                suggestion=f"Use one of: {', '.join(VALID_TIERS)}"
            ))
            confidence *= 0.8
        
        # Check for topic-specific required elements
        if topic in self.TOPIC_REQUIRED_ELEMENTS:
            required_elements = self.TOPIC_REQUIRED_ELEMENTS[topic]
            missing_elements = [elem for elem in required_elements if elem not in question_text]
            
            if len(missing_elements) == len(required_elements):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="topic_alignment",
                    message=f"Question may not align with {topic} topic",
                    field="question_text",
                    suggestion=f"Consider including elements like: {', '.join(required_elements[:3])}"
                ))
                confidence *= 0.7
        
        return issues, confidence
    
    def _check_mathematical_errors(self, question: Dict[str, Any]) -> List[ValidationIssue]:
        """Check for common mathematical errors in question text."""
        issues = []
        question_text = question.get('question_text', '')
        
        for error_pattern in self.COMMON_ERRORS:
            if re.search(error_pattern, question_text):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    category="mathematical_errors",
                    message=f"Potential mathematical error detected: {error_pattern}",
                    field="question_text",
                    suggestion="Review mathematical expressions for errors"
                ))
        
        return issues
    
    def get_validation_summary(self, validation_results: List[ValidationResult]) -> Dict[str, Any]:
        """Generate summary statistics from multiple validation results."""
        if not validation_results:
            return {"error": "No validation results provided"}
        
        total_questions = len(validation_results)
        valid_questions = sum(1 for r in validation_results if r.is_valid)
        
        all_issues = []
        for result in validation_results:
            all_issues.extend(result.issues)
        
        issue_categories = {}
        for issue in all_issues:
            category = issue.category
            if category not in issue_categories:
                issue_categories[category] = {"critical": 0, "warning": 0, "info": 0}
            issue_categories[category][issue.severity.value] += 1
        
        avg_confidence = sum(r.confidence_score for r in validation_results) / total_questions
        
        return {
            "total_questions": total_questions,
            "valid_questions": valid_questions,
            "success_rate": valid_questions / total_questions,
            "average_confidence": avg_confidence,
            "total_issues": len(all_issues),
            "issues_by_category": issue_categories,
            "issues_by_severity": {
                "critical": len([i for i in all_issues if i.severity == ValidationSeverity.CRITICAL]),
                "warning": len([i for i in all_issues if i.severity == ValidationSeverity.WARNING]),
                "info": len([i for i in all_issues if i.severity == ValidationSeverity.INFO])
            }
        }