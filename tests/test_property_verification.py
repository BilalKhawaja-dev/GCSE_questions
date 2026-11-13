"""
Property-Based Tests for Verification System

Tests universal properties that should hold across all verification scenarios.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from hypothesis import HealthCheck
import json

from src.lambda_handlers.verification_lambda import verify_question
from src.services.deterministic_verifier_service import DeterministicVerifier
from src.models.verification import VerificationResult


# Strategies for generating test data
@st.composite
def valid_question(draw):
    """Generate a valid question structure."""
    topic = draw(st.sampled_from([
        'number', 'algebra', 'ratio_proportion',
        'geometry', 'probability', 'statistics'
    ]))
    grade = draw(st.sampled_from(['foundation', 'higher']))
    paper_type = draw(st.sampled_from(['P1', 'P2', 'P3']))
    
    # Generate 4 distinct options
    options = draw(st.lists(
        st.text(min_size=1, max_size=50),
        min_size=4,
        max_size=4,
        unique=True
    ))
    
    correct_answer = draw(st.sampled_from(['A', 'B', 'C', 'D']))
    
    return {
        'question_id': draw(st.uuids()).hex,
        'stem': draw(st.text(min_size=10, max_size=200)),
        'options': options,
        'correct_answer': correct_answer,
        'rationale': draw(st.text(min_size=10, max_size=500)),
        'topic': topic,
        'grade': grade,
        'paper_type': paper_type,
        'difficulty': draw(st.integers(min_value=1, max_value=10))
    }


@st.composite
def invalid_question_duplicate_options(draw):
    """Generate a question with duplicate options."""
    question = draw(valid_question())
    # Make two options the same
    question['options'][1] = question['options'][0]
    return question


@st.composite
def invalid_question_wrong_option_count(draw):
    """Generate a question with wrong number of options."""
    question = draw(valid_question())
    # Add or remove options
    if draw(st.booleans()):
        question['options'].append('Extra option')
    else:
        question['options'] = question['options'][:3]
    return question


class TestVerificationProperties:
    """Property-based tests for verification system."""
    
    @given(valid_question())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_verification_always_returns_result(self, question):
        """
        Property: Verification always returns a VerificationResult.
        
        For any valid question structure, verification should complete
        and return a result (even if it's a failure).
        
        **Validates: Requirements 1.1, 2.1, 3.1, 4.1, 5.1**
        """
        # Run deterministic verification (fast, no external dependencies)
        verifier = DeterministicVerifier()
        result = verifier.verify(question)
        
        # Verify result structure
        assert result is not None
        assert hasattr(result, 'pass_')
        assert isinstance(result.pass_, bool)
        assert hasattr(result, 'issues')
        assert isinstance(result.issues, list)
    
    @given(invalid_question_duplicate_options())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_duplicate_options_always_fail(self, question):
        """
        Property: Questions with duplicate options always fail deterministic checks.
        
        For any question with duplicate options, deterministic verification
        should fail with a duplicate-related issue.
        
        **Validates: Requirements 1.2**
        """
        verifier = DeterministicVerifier()
        result = verifier.verify(question)
        
        # Should fail
        assert result.pass_ is False
        
        # Should have duplicate-related issue
        assert any('duplicate' in issue.lower() for issue in result.issues)
    
    @given(invalid_question_wrong_option_count())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_wrong_option_count_always_fails(self, question):
        """
        Property: Questions without exactly 4 options always fail.
        
        For any question with != 4 options, deterministic verification
        should fail with an option count issue.
        
        **Validates: Requirements 1.2**
        """
        verifier = DeterministicVerifier()
        result = verifier.verify(question)
        
        # Should fail
        assert result.pass_ is False
        
        # Should have option count issue
        assert any(
            'option' in issue.lower() or '4' in issue
            for issue in result.issues
        )
    
    @given(valid_question())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_verification_is_deterministic(self, question):
        """
        Property: Running verification twice on same question gives same result.
        
        For any question, deterministic verification should produce
        identical results on repeated runs.
        
        **Validates: Requirements 1.1**
        """
        verifier = DeterministicVerifier()
        
        # Run twice
        result1 = verifier.verify(question)
        result2 = verifier.verify(question)
        
        # Results should be identical
        assert result1.pass_ == result2.pass_
        assert set(result1.issues) == set(result2.issues)
    
    @given(valid_question())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_pass_implies_no_issues(self, question):
        """
        Property: If verification passes, there should be no issues.
        
        For any question that passes verification, the issues list
        should be empty.
        
        **Validates: Requirements 1.1, 2.1, 3.1**
        """
        verifier = DeterministicVerifier()
        result = verifier.verify(question)
        
        # If passed, no issues
        if result.pass_:
            assert len(result.issues) == 0
    
    @given(valid_question())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_fail_implies_issues_present(self, question):
        """
        Property: If verification fails, there should be at least one issue.
        
        For any question that fails verification, the issues list
        should contain at least one reason.
        
        **Validates: Requirements 1.1, 2.1, 3.1**
        """
        verifier = DeterministicVerifier()
        result = verifier.verify(question)
        
        # If failed, must have issues
        if not result.pass_:
            assert len(result.issues) > 0
    
    @given(
        st.text(min_size=1, max_size=100),
        st.lists(st.text(min_size=1, max_size=50), min_size=4, max_size=4, unique=True),
        st.sampled_from(['A', 'B', 'C', 'D'])
    )
    @settings(max_examples=50)
    def test_property_valid_structure_passes_schema_check(self, stem, options, correct_answer):
        """
        Property: Questions with valid structure pass schema validation.
        
        For any question with valid stem, 4 unique options, and valid answer,
        the schema validation should pass.
        
        **Validates: Requirements 1.1**
        """
        question = {
            'question_id': 'test-id',
            'stem': stem,
            'options': options,
            'correct_answer': correct_answer,
            'topic': 'algebra',
            'grade': 'foundation',
            'paper_type': 'P1',
            'difficulty': 5
        }
        
        verifier = DeterministicVerifier()
        result = verifier.verify(question)
        
        # Schema validation should pass
        # (may fail on other checks, but not schema)
        schema_issues = [
            issue for issue in result.issues
            if 'schema' in issue.lower() or 'missing' in issue.lower()
        ]
        assert len(schema_issues) == 0
    
    @given(valid_question())
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_p1_questions_have_non_calculator_constraint(self, question):
        """
        Property: P1 questions should not mention calculator.
        
        For any P1 question, if it mentions "calculator" in the stem,
        it should fail paper constraint checks.
        
        **Validates: Requirements 1.4**
        """
        # Force P1 paper type
        question['paper_type'] = 'P1'
        
        # Add calculator mention
        question['stem'] = question['stem'] + " Use a calculator to find the answer."
        
        verifier = DeterministicVerifier()
        result = verifier.verify(question)
        
        # Should fail with calculator-related issue
        if 'calculator' in question['stem'].lower():
            assert result.pass_ is False
            assert any(
                'calculator' in issue.lower() or 'p1' in issue.lower()
                for issue in result.issues
            )


class TestVerificationInvariants:
    """Test invariants that should hold across verification."""
    
    @given(valid_question())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_invariant_question_id_preserved(self, question):
        """
        Invariant: Question ID is preserved through verification.
        
        For any question, the question_id should remain unchanged
        after verification.
        
        **Validates: Requirements 6.1**
        """
        original_id = question['question_id']
        
        verifier = DeterministicVerifier()
        result = verifier.verify(question)
        
        # Question ID should be unchanged
        assert question['question_id'] == original_id
    
    @given(valid_question())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_invariant_question_content_unchanged(self, question):
        """
        Invariant: Question content is not modified by verification.
        
        For any question, verification should not modify the question data.
        
        **Validates: Requirements 6.1**
        """
        # Create deep copy for comparison
        original_stem = question['stem']
        original_options = question['options'].copy()
        original_answer = question['correct_answer']
        
        verifier = DeterministicVerifier()
        result = verifier.verify(question)
        
        # Content should be unchanged
        assert question['stem'] == original_stem
        assert question['options'] == original_options
        assert question['correct_answer'] == original_answer


class TestVerificationEdgeCases:
    """Test edge cases in verification."""
    
    @given(valid_question())
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_edge_case_empty_stem(self, question):
        """
        Edge case: Questions with empty stem.
        
        Note: Empty stem is technically valid (field exists), but may be caught
        by other validation layers (LLM auditor, etc.)
        
        **Validates: Requirements 1.1**
        """
        # Force empty stem
        question['stem'] = ''
        
        verifier = DeterministicVerifier()
        result = verifier.verify(question)
        
        # Deterministic verifier checks field presence, not content
        # Empty string is technically valid for schema validation
        # (Would be caught by LLM auditor in full pipeline)
        assert result is not None  # Just verify it doesn't crash
    
    @given(valid_question())
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_edge_case_empty_options(self, question):
        """
        Edge case: Questions with empty options should fail.
        
        **Validates: Requirements 1.2**
        """
        question['options'] = ['', '', '', '']
        
        verifier = DeterministicVerifier()
        result = verifier.verify(question)
        
        # Should fail
        assert result.pass_ is False
    
    @given(valid_question())
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_edge_case_invalid_correct_answer(self, question):
        """
        Edge case: Questions with invalid correct_answer should fail.
        
        **Validates: Requirements 1.3**
        """
        question['correct_answer'] = 'Z'  # Invalid
        
        verifier = DeterministicVerifier()
        result = verifier.verify(question)
        
        # Should fail
        assert result.pass_ is False
    
    @given(valid_question())
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_edge_case_missing_required_fields(self, question):
        """
        Edge case: Questions missing required fields should fail.
        
        **Validates: Requirements 1.1**
        """
        # Remove required field
        del question['stem']
        
        verifier = DeterministicVerifier()
        result = verifier.verify(question)
        
        # Should fail
        assert result.pass_ is False


class TestVerificationPerformance:
    """Test performance properties of verification."""
    
    @given(valid_question())
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_deterministic_verification_is_fast(self, question):
        """
        Property: Deterministic verification completes quickly.
        
        For any question, deterministic verification should complete
        in under 100ms.
        
        **Validates: Requirements 1.1 (Performance)**
        """
        import time
        
        verifier = DeterministicVerifier()
        
        start = time.time()
        result = verifier.verify(question)
        elapsed = time.time() - start
        
        # Should be very fast (< 100ms)
        assert elapsed < 0.1
        assert result is not None
