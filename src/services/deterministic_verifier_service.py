"""Deterministic verification service for fast rule-based checks."""

from typing import Dict, Any, List
from src.models.verification import CheckResult, DeterministicCheckResult


class DeterministicVerifier:
    """Fast, rule-based verification checks before expensive LLM/compute."""
    
    def verify(self, question_data: Dict[str, Any]) -> DeterministicCheckResult:
        """
        Run all deterministic checks on a question.
        
        Args:
            question_data: Dictionary containing question fields
            
        Returns:
            DeterministicCheckResult with pass/fail and issues
        """
        checks = [
            self._validate_schema(question_data),
            self._validate_mcq_structure(question_data),
            self._validate_answer_format(question_data),
            self._validate_paper_constraints(question_data),
            self._check_duplicate_options(question_data)
        ]
        
        return self._aggregate_checks(checks)
    
    def _validate_schema(self, question_data: Dict[str, Any]) -> CheckResult:
        """Validate JSON schema and required fields."""
        required_fields = ['stem', 'options', 'correct_answer', 'topic', 'paper_type']
        
        for field in required_fields:
            if field not in question_data:
                return CheckResult(
                    pass_=False,
                    reason=f"Missing required field: {field}"
                )
        
        return CheckResult(pass_=True, reason="Schema validation passed")
    
    def _validate_mcq_structure(self, question_data: Dict[str, Any]) -> CheckResult:
        """
        Validate MCQ structure rules:
        - Exactly 4 options (A, B, C, D)
        - Exactly 1 marked correct
        - Options are non-empty strings
        """
        options = question_data.get('options', [])
        correct_answer = question_data.get('correct_answer', '')
        
        # Check exactly 4 options
        if len(options) != 4:
            return CheckResult(
                pass_=False,
                reason=f"Must have exactly 4 options, found {len(options)}"
            )
        
        # Check all options are non-empty strings
        for i, option in enumerate(options):
            if not isinstance(option, str) or not option.strip():
                return CheckResult(
                    pass_=False,
                    reason=f"Option {chr(65+i)} is empty or invalid"
                )
        
        # Check correct answer is valid (A, B, C, or D)
        if correct_answer not in ['A', 'B', 'C', 'D']:
            return CheckResult(
                pass_=False,
                reason=f"Invalid correct_answer: {correct_answer}. Must be A, B, C, or D"
            )
        
        return CheckResult(pass_=True, reason="MCQ structure validation passed")
    
    def _validate_answer_format(self, question_data: Dict[str, Any]) -> CheckResult:
        """Validate answer format consistency."""
        # This is a placeholder for more sophisticated format validation
        # Could check for consistent decimal places, fraction formats, etc.
        return CheckResult(pass_=True, reason="Answer format validation passed")
    
    def _validate_paper_constraints(self, question_data: Dict[str, Any]) -> CheckResult:
        """
        Validate paper-specific constraints.
        
        Paper 1 (Non-Calculator):
        - No "calculator" mentions
        - Avoid calculator-dependent rounding phrases
        """
        paper_type = question_data.get('paper_type', '')
        stem = question_data.get('stem', '').lower()
        
        if paper_type == 'P1':
            # Non-calculator checks
            if 'calculator' in stem:
                return CheckResult(
                    pass_=False,
                    reason="P1 (non-calculator) cannot mention calculator"
                )
            
            # Check for calculator-dependent rounding
            if '3 s.f.' in stem and 'decimal' in stem:
                return CheckResult(
                    pass_=False,
                    reason="P1 should avoid calculator-dependent rounding to 3 s.f."
                )
            
            if 'give your answer to' in stem and 'decimal place' in stem:
                return CheckResult(
                    pass_=False,
                    reason="P1 should avoid calculator-dependent decimal place rounding"
                )
        
        return CheckResult(pass_=True, reason="Paper constraints validation passed")
    
    def _check_duplicate_options(self, question_data: Dict[str, Any]) -> CheckResult:
        """Check for duplicate options (string equality)."""
        options = question_data.get('options', [])
        
        # Normalize options for comparison (strip whitespace, lowercase)
        normalized = [opt.strip().lower() for opt in options]
        
        # Check for exact duplicates
        if len(normalized) != len(set(normalized)):
            return CheckResult(
                pass_=False,
                reason="Duplicate options detected (string equality)"
            )
        
        return CheckResult(pass_=True, reason="No duplicate options found")
    
    def _aggregate_checks(self, checks: List[CheckResult]) -> DeterministicCheckResult:
        """Aggregate individual check results into final result."""
        issues = []
        checks_performed = []
        
        for check in checks:
            if check.reason:
                checks_performed.append(check.reason)
            
            if not check.pass_:
                issues.append(check.reason or "Unknown issue")
        
        return DeterministicCheckResult(
            pass_=len(issues) == 0,
            issues=issues,
            checks_performed=checks_performed
        )
