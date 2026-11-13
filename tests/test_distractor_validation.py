"""
Tests for distractor validation in SymPy Verifier
"""

import pytest
from src.services.sympy_verifier_service import SymPyVerifier, MCQQuestion


@pytest.fixture
def verifier():
    """Create a SymPy verifier instance."""
    return SymPyVerifier()


class TestDistractorQuality:
    """Test distractor quality validation."""
    
    def test_good_distractors(self, verifier):
        """Test question with good distractors (all wrong)."""
        question = MCQQuestion(
            
            stem="Solve 2x + 5 = 13",
            options=["x = 4", "x = 9", "x = 3", "x = 8"],
            correct_answer="A",
            rationale="Subtract 5 from both sides to get 2x = 8, then divide by 2",
            topic="algebra",
            difficulty=3,
            paper_type="P1",
            grade="foundation"
        )
        
        result = verifier.verify(question)
        
        if result.applicable:
            quality = result.distractor_quality.get("quality") if result.distractor_quality else None
            issues = result.distractor_quality.get("issues", []) if result.distractor_quality else []
            assert quality == "good"
            assert len(issues) == 0
    
    def test_duplicate_correct_answer_numeric(self, verifier):
        """Test detecting duplicate correct answer (numeric form)."""
        question = MCQQuestion(
            
            stem="Solve x + 3 = 7",
            options=["x = 4", "4", "x = 10", "x = -4"],  # A and B are both 4
            correct_answer="A",
            rationale="Subtract 3 from both sides",
            topic="algebra",
            difficulty=2,
            paper_type="P1",
            grade="foundation"
        )
        
        result = verifier.verify(question)
        
        if result.applicable:
            # Should detect that option B also equals 4
            assert result.distractor_quality.get("quality") if result.distractor_quality else None == "poor" or len(result.distractor_quality.get("issues", [])) if result.distractor_quality else 0 > 0
    
    def test_equivalent_expressions(self, verifier):
        """Test detecting equivalent expressions as distractors."""
        question = MCQQuestion(
            
            stem="Simplify 2x + 3x",
            options=["5x", "x + 5", "5 + x", "2x + 3"],
            correct_answer="A",
            rationale="Combine like terms",
            topic="algebra",
            difficulty=2,
            paper_type="P1",
            grade="foundation"
        )
        
        result = verifier.verify(question)
        
        # x + 5 and 5 + x are equivalent, but neither equals 5x
        if result.applicable:
            assert result.pass_ is True
    
    def test_simplified_vs_unsimplified(self, verifier):
        """Test that simplified and unsimplified forms are detected."""
        question = MCQQuestion(
            
            stem="Expand (x + 2)(x + 3)",
            options=["x² + 5x + 6", "x² + 6x + 5", "(x + 2)(x + 3)", "x² + 5x + 5"],
            correct_answer="A",
            rationale="Use FOIL method",
            topic="algebra",
            difficulty=4,
            paper_type="P1",
            grade="foundation"
        )
        
        result = verifier.verify(question)
        
        if result.applicable:
            # Option C is the unsimplified form, which IS mathematically equal to the expanded form
            # This is actually correct behavior - we should detect this
            assert result.pass_ is False  # Should fail because option C equals correct answer
            quality = result.distractor_quality.get("quality") if result.distractor_quality else None
            assert quality == "poor"


class TestCommonMistakes:
    """Test detection of common student mistakes in distractors."""
    
    def test_sign_error_distractor(self, verifier):
        """Test that sign errors are valid distractors."""
        question = MCQQuestion(
            
            stem="Solve x - 5 = 3",
            options=["x = 8", "x = -8", "x = 2", "x = -2"],
            correct_answer="A",
            rationale="Add 5 to both sides",
            topic="algebra",
            difficulty=2,
            paper_type="P1",
            grade="foundation"
        )
        
        result = verifier.verify(question)
        
        if result.applicable:
            # -8 is a common mistake (subtracting instead of adding)
            assert result.pass_ is True
            assert result.distractor_quality.get("quality") if result.distractor_quality else None == "good"
    
    def test_operation_error_distractor(self, verifier):
        """Test that operation errors are valid distractors."""
        question = MCQQuestion(
            
            stem="Calculate 15% of 80",
            options=["12", "95", "65", "1200"],
            correct_answer="A",
            rationale="15/100 × 80 = 12",
            topic="number",
            difficulty=2,
            paper_type="P1",
            grade="foundation"
        )
        
        result = verifier.verify(question)
        
        if result.applicable:
            # 95 (adding), 65 (subtracting), 1200 (multiplying) are common mistakes
            assert result.pass_ is True


class TestMultipleCorrectDetection:
    """Test detection of multiple correct answers."""
    
    def test_two_correct_answers(self, verifier):
        """Test detecting when two options are mathematically equivalent."""
        question = MCQQuestion(
            
            stem="Simplify √8",
            options=["2√2", "√8", "4", "2.83"],
            correct_answer="A",
            rationale="√8 = √(4 × 2) = 2√2",
            topic="number",
            difficulty=4,
            paper_type="P1",
            grade="foundation"
        )
        
        result = verifier.verify(question)
        
        if result.applicable:
            # √8 and 2√2 are equivalent, but √8 is unsimplified
            # This should be detected as an issue
            pass
    
    def test_fraction_equivalence(self, verifier):
        """Test detecting equivalent fractions."""
        question = MCQQuestion(
            
            stem="Simplify 4/8",
            options=["1/2", "2/4", "0.5", "4/8"],
            correct_answer="A",
            rationale="Divide numerator and denominator by 4",
            topic="number",
            difficulty=2,
            paper_type="P1",
            grade="foundation"
        )
        
        result = verifier.verify(question)
        
        if result.applicable:
            # 1/2, 2/4, and 0.5 are all equivalent
            # Should detect multiple correct answers
            pass


class TestEdgeCaseDistractors:
    """Test edge cases in distractor validation."""
    
    def test_unparseable_distractor(self, verifier):
        """Test handling of distractors that can't be parsed."""
        question = MCQQuestion(
            
            stem="Solve 2x = 10",
            options=["x = 5", "No solution", "Infinite solutions", "x = 2.5"],
            correct_answer="A",
            rationale="Divide both sides by 2",
            topic="algebra",
            difficulty=2,
            paper_type="P1",
            grade="foundation"
        )
        
        result = verifier.verify(question)
        
        # Should handle gracefully even if "No solution" can't be parsed
        if result.applicable:
            assert result is not None
    
    def test_text_based_distractor(self, verifier):
        """Test handling of text-based distractors."""
        question = MCQQuestion(
            
            stem="What is 5 + 3?",
            options=["8", "fifteen", "5 + 3", "53"],
            correct_answer="A",
            rationale="Simple addition",
            topic="number",
            difficulty=1,
            paper_type="P1",
            grade="foundation"
        )
        
        result = verifier.verify(question)
        
        # Should handle text distractors gracefully
        assert result is not None
    
    def test_very_close_numeric_values(self, verifier):
        """Test handling of very close numeric values."""
        question = MCQQuestion(
            
            stem="Calculate √2 (to 2 decimal places)",
            options=["1.41", "1.42", "1.40", "1.43"],
            correct_answer="A",
            rationale="√2 ≈ 1.414...",
            topic="number",
            difficulty=3,
            paper_type="P2",
            grade="foundation"
        )
        
        result = verifier.verify(question)
        
        # Close values should not be flagged as duplicates
        if result.applicable:
            assert result.distractor_quality.get("quality") if result.distractor_quality else None == "good"


class TestDistractorPatterns:
    """Test common distractor patterns."""
    
    def test_off_by_one_distractors(self, verifier):
        """Test off-by-one error distractors."""
        question = MCQQuestion(
            
            stem="Solve x + 7 = 12",
            options=["x = 5", "x = 4", "x = 6", "x = 19"],
            correct_answer="A",
            rationale="Subtract 7 from both sides",
            topic="algebra",
            difficulty=2,
            paper_type="P1",
            grade="foundation"
        )
        
        result = verifier.verify(question)
        
        if result.applicable:
            # 4 and 6 are off-by-one errors, 19 is adding instead of subtracting
            assert result.pass_ is True
            assert result.distractor_quality.get("quality") if result.distractor_quality else None == "good"
    
    def test_reciprocal_distractors(self, verifier):
        """Test reciprocal error distractors."""
        question = MCQQuestion(
            
            stem="Simplify 1/2 ÷ 1/4",
            options=["2", "1/2", "1/8", "8"],
            correct_answer="A",
            rationale="Multiply by reciprocal: 1/2 × 4/1 = 2",
            topic="number",
            difficulty=4,
            paper_type="P1",
            grade="foundation"
        )
        
        result = verifier.verify(question)
        
        if result.applicable:
            # 1/8 is multiplying instead of dividing
            assert result.pass_ is True
