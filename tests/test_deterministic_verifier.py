"""Unit tests for DeterministicVerifier service."""

import pytest
from src.services.deterministic_verifier_service import DeterministicVerifier
from src.models.verification import CheckResult, DeterministicCheckResult


class TestDeterministicVerifier:
    """Test suite for DeterministicVerifier."""
    
    @pytest.fixture
    def verifier(self):
        """Create a DeterministicVerifier instance."""
        return DeterministicVerifier()
    
    @pytest.fixture
    def valid_question(self):
        """Create a valid question for testing."""
        return {
            'stem': 'Solve 2x + 5 = 13',
            'options': ['x = 4', 'x = 9', 'x = 3', 'x = 8'],
            'correct_answer': 'A',
            'topic': 'algebra',
            'paper_type': 'P2',
            'grade': 'foundation',
            'difficulty': 5
        }
    
    def test_valid_question_passes(self, verifier, valid_question):
        """Test that a valid question passes all checks."""
        result = verifier.verify(valid_question)
        
        assert isinstance(result, DeterministicCheckResult)
        assert result.pass_ is True
        assert len(result.issues) == 0
        assert len(result.checks_performed) > 0
    
    def test_missing_required_field_fails(self, verifier, valid_question):
        """Test that missing required fields fail validation."""
        # Remove stem
        invalid_question = valid_question.copy()
        del invalid_question['stem']
        
        result = verifier.verify(invalid_question)
        
        assert result.pass_ is False
        assert any('Missing required field: stem' in issue for issue in result.issues)
    
    def test_wrong_number_of_options_fails(self, verifier, valid_question):
        """Test that questions with != 4 options fail."""
        # Only 3 options
        invalid_question = valid_question.copy()
        invalid_question['options'] = ['x = 4', 'x = 9', 'x = 3']
        
        result = verifier.verify(invalid_question)
        
        assert result.pass_ is False
        assert any('Must have exactly 4 options' in issue for issue in result.issues)
    
    def test_empty_option_fails(self, verifier, valid_question):
        """Test that empty options fail validation."""
        invalid_question = valid_question.copy()
        invalid_question['options'] = ['x = 4', '', 'x = 3', 'x = 8']
        
        result = verifier.verify(invalid_question)
        
        assert result.pass_ is False
        assert any('empty or invalid' in issue for issue in result.issues)
    
    def test_invalid_correct_answer_fails(self, verifier, valid_question):
        """Test that invalid correct_answer values fail."""
        invalid_question = valid_question.copy()
        invalid_question['correct_answer'] = 'E'  # Invalid
        
        result = verifier.verify(invalid_question)
        
        assert result.pass_ is False
        assert any('Invalid correct_answer' in issue for issue in result.issues)
    
    def test_duplicate_options_fail(self, verifier, valid_question):
        """Test that duplicate options are detected."""
        invalid_question = valid_question.copy()
        invalid_question['options'] = ['x = 4', 'x = 4', 'x = 3', 'x = 8']
        
        result = verifier.verify(invalid_question)
        
        assert result.pass_ is False
        assert any('Duplicate options' in issue for issue in result.issues)
    
    def test_p1_calculator_mention_fails(self, verifier, valid_question):
        """Test that P1 questions mentioning calculator fail."""
        invalid_question = valid_question.copy()
        invalid_question['paper_type'] = 'P1'
        invalid_question['stem'] = 'Use your calculator to solve 2x + 5 = 13'
        
        result = verifier.verify(invalid_question)
        
        assert result.pass_ is False
        assert any('cannot mention calculator' in issue for issue in result.issues)
    
    def test_p1_calculator_rounding_fails(self, verifier, valid_question):
        """Test that P1 questions with calculator-dependent rounding fail."""
        invalid_question = valid_question.copy()
        invalid_question['paper_type'] = 'P1'
        invalid_question['stem'] = 'Give your answer to 3 s.f. as a decimal'
        
        result = verifier.verify(invalid_question)
        
        assert result.pass_ is False
        assert any('calculator-dependent rounding' in issue for issue in result.issues)
    
    def test_p2_calculator_allowed(self, verifier, valid_question):
        """Test that P2/P3 questions can mention calculator."""
        valid_p2_question = valid_question.copy()
        valid_p2_question['paper_type'] = 'P2'
        valid_p2_question['stem'] = 'Use your calculator to find the value'
        
        result = verifier.verify(valid_p2_question)
        
        # Should pass - P2 allows calculator
        assert result.pass_ is True
    
    def test_case_insensitive_duplicate_detection(self, verifier, valid_question):
        """Test that duplicate detection is case-insensitive."""
        invalid_question = valid_question.copy()
        invalid_question['options'] = ['x = 4', 'X = 4', 'x = 3', 'x = 8']
        
        result = verifier.verify(invalid_question)
        
        assert result.pass_ is False
        assert any('Duplicate options' in issue for issue in result.issues)
    
    def test_whitespace_normalized_duplicates(self, verifier, valid_question):
        """Test that whitespace is normalized when checking duplicates."""
        invalid_question = valid_question.copy()
        invalid_question['options'] = ['x = 4', '  x = 4  ', 'x = 3', 'x = 8']
        
        result = verifier.verify(invalid_question)
        
        assert result.pass_ is False
        assert any('Duplicate options' in issue for issue in result.issues)
    
    def test_all_checks_performed_recorded(self, verifier, valid_question):
        """Test that all performed checks are recorded."""
        result = verifier.verify(valid_question)
        
        assert len(result.checks_performed) >= 5  # At least 5 checks
        assert any('Schema validation' in check for check in result.checks_performed)
        assert any('MCQ structure' in check for check in result.checks_performed)
    
    def test_multiple_issues_reported(self, verifier):
        """Test that multiple issues are all reported."""
        invalid_question = {
            'stem': 'Use calculator to solve',  # P1 violation
            'options': ['x = 4', 'x = 4'],  # Wrong count + duplicates
            'correct_answer': 'E',  # Invalid
            'topic': 'algebra',
            'paper_type': 'P1'
        }
        
        result = verifier.verify(invalid_question)
        
        assert result.pass_ is False
        assert len(result.issues) >= 2  # Multiple issues detected


class TestCheckResult:
    """Test CheckResult model."""
    
    def test_check_result_creation(self):
        """Test creating a CheckResult."""
        result = CheckResult(pass_=True, reason="Test passed")
        
        assert result.pass_ is True
        assert result.reason == "Test passed"
        assert result.confidence == 1.0
    
    def test_check_result_with_details(self):
        """Test CheckResult with details."""
        result = CheckResult(
            pass_=False,
            reason="Test failed",
            confidence=0.5,
            details={'error': 'Invalid format'}
        )
        
        assert result.pass_ is False
        assert result.confidence == 0.5
        assert result.details['error'] == 'Invalid format'


class TestDeterministicCheckResult:
    """Test DeterministicCheckResult model."""
    
    def test_deterministic_result_creation(self):
        """Test creating a DeterministicCheckResult."""
        result = DeterministicCheckResult(
            pass_=True,
            issues=[],
            checks_performed=['Schema validation', 'MCQ structure']
        )
        
        assert result.pass_ is True
        assert len(result.issues) == 0
        assert len(result.checks_performed) == 2
    
    def test_deterministic_result_with_issues(self):
        """Test DeterministicCheckResult with issues."""
        result = DeterministicCheckResult(
            pass_=False,
            issues=['Missing field: stem', 'Invalid options count'],
            checks_performed=['Schema validation']
        )
        
        assert result.pass_ is False
        assert len(result.issues) == 2
        assert 'Missing field: stem' in result.issues
