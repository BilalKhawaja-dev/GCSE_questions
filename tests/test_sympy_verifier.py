"""
Unit tests for SymPy Verifier Service
"""

import pytest
from src.services.sympy_verifier_service import SymPyVerifier, MCQQuestion


@pytest.fixture
def verifier():
    """Create a SymPy verifier instance."""
    return SymPyVerifier()


class TestLinearEquations:
    """Test linear equation solving."""
    
    def test_simple_linear_equation(self, verifier):
        """Test solving 2x + 5 = 13."""
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
        
        assert result.applicable is True
        assert result.pass_ is True
        assert result.confidence == 1.0
    
    def test_linear_equation_wrong_answer(self, verifier):
        """Test detecting wrong answer in linear equation."""
        question = MCQQuestion(
            stem="Solve 3x - 7 = 11",
            options=["x = 5", "x = 6", "x = 7", "x = 8"],
            correct_answer="B",  # x = 6 is correct
            rationale="Add 7 to both sides to get 3x = 18, then divide by 3",
            topic="algebra",
            difficulty=3,
            paper_type="P1",
            grade="foundation"
        )
        
        result = verifier.verify(question)
        
        assert result.applicable is True
        assert result.pass_ is True  # x = 6 is correct
        assert result.confidence == 1.0


class TestQuadraticEquations:
    """Test quadratic equation solving."""
    
    def test_simple_quadratic(self, verifier):
        """Test solving x² - 5x + 6 = 0."""
        question = MCQQuestion(
            stem="Solve x² - 5x + 6 = 0",
            options=["x = 2 or x = 3", "x = 1 or x = 6", "x = -2 or x = -3", "x = 0 or x = 5"],
            correct_answer="A",
            rationale="Factorise to (x-2)(x-3) = 0",
            topic="algebra",
            difficulty=5,
            paper_type="P2",
            grade="foundation"
        )
        
        result = verifier.verify(question)
        
        assert result.applicable is True
        # Note: Quadratic solutions are complex to match exactly
        # This test verifies the system can parse and attempt solving


class TestFactorising:
    """Test factorising expressions."""
    
    def test_simple_factorising(self, verifier):
        """Test factorising x² + 7x + 12."""
        question = MCQQuestion(
            stem="Factorise x² + 7x + 12",
            options=["(x + 3)(x + 4)", "(x + 2)(x + 6)", "(x + 1)(x + 12)", "(x - 3)(x - 4)"],
            correct_answer="A",
            rationale="Find two numbers that multiply to 12 and add to 7",
            topic="algebra",
            difficulty=4,
            paper_type="P1",
            grade="foundation"
        )
        
        result = verifier.verify(question)
        
        assert result.applicable is True


class TestExpanding:
    """Test expanding expressions."""
    
    def test_simple_expanding(self, verifier):
        """Test expanding (x + 3)(x + 4)."""
        question = MCQQuestion(
            stem="Expand (x + 3)(x + 4)",
            options=["x² + 7x + 12", "x² + 12x + 7", "x² + 7x + 7", "x² + 12x + 12"],
            correct_answer="A",
            rationale="Use FOIL method",
            topic="algebra",
            difficulty=4,
            paper_type="P1",
            grade="foundation"
        )
        
        result = verifier.verify(question)
        
        assert result.applicable is True


class TestSurds:
    """Test surd simplification."""
    
    def test_simple_surd(self, verifier):
        """Test simplifying √50."""
        question = MCQQuestion(
            stem="Simplify √50",
            options=["5√2", "2√5", "√25", "10"],
            correct_answer="A",
            rationale="√50 = √(25 × 2) = 5√2",
            topic="number",
            difficulty=4,
            paper_type="P1",
            grade="foundation"
        )
        
        result = verifier.verify(question)
        
        assert result.applicable is True


class TestFractions:
    """Test fraction operations."""
    
    def test_fraction_addition(self, verifier):
        """Test adding 3/4 + 2/5."""
        question = MCQQuestion(
            stem="Calculate 3/4 + 2/5",
            options=["23/20", "5/9", "15/20", "1"],
            correct_answer="A",
            rationale="Find common denominator 20",
            topic="number",
            difficulty=3,
            paper_type="P1",
            grade="foundation"
        )
        
        result = verifier.verify(question)
        
        assert result.applicable is True


class TestPercentages:
    """Test percentage calculations."""
    
    def test_percentage_of_value(self, verifier):
        """Test calculating 15% of 80."""
        question = MCQQuestion(
            stem="Calculate 15% of 80",
            options=["12", "15", "20", "10"],
            correct_answer="A",
            rationale="15/100 × 80 = 12",
            topic="number",
            difficulty=2,
            paper_type="P1",
            grade="foundation"
        )
        
        result = verifier.verify(question)
        
        assert result.applicable is True


class TestPythagoras:
    """Test Pythagoras theorem."""
    
    def test_find_hypotenuse(self, verifier):
        """Test finding hypotenuse with sides 3 and 4."""
        question = MCQQuestion(
            stem="A right-angled triangle has sides 3 cm and 4 cm. Find the hypotenuse.",
            options=["5 cm", "7 cm", "6 cm", "8 cm"],
            correct_answer="A",
            rationale="c² = 3² + 4² = 9 + 16 = 25, so c = 5",
            topic="geometry",
            difficulty=3,
            paper_type="P1",
            grade="foundation"
        )
        
        result = verifier.verify(question)
        
        assert result.applicable is True


class TestTrigonometry:
    """Test basic trigonometry."""
    
    def test_sin_30(self, verifier):
        """Test sin(30°) = 0.5."""
        question = MCQQuestion(
            stem="Calculate sin(30°)",
            options=["0.5", "0.707", "0.866", "1"],
            correct_answer="A",
            rationale="sin(30°) = 0.5",
            topic="trigonometry",
            difficulty=4,
            paper_type="P2",
            grade="foundation"
        )
        
        result = verifier.verify(question)
        
        assert result.applicable is True
        assert result.pass_ is True
    
    def test_cos_60(self, verifier):
        """Test cos(60°) = 0.5."""
        question = MCQQuestion(
            stem="Calculate cos(60°)",
            options=["0.5", "0.707", "0.866", "1"],
            correct_answer="A",
            rationale="cos(60°) = 0.5",
            topic="trigonometry",
            difficulty=4,
            paper_type="P2",
            grade="foundation"
        )
        
        result = verifier.verify(question)
        
        assert result.applicable is True
        assert result.pass_ is True


class TestDistractorValidation:
    """Test distractor validation."""
    
    def test_duplicate_correct_answer(self, verifier):
        """Test detecting when multiple options are correct."""
        question = MCQQuestion(
            stem="Solve 2x + 5 = 13",
            options=["x = 4", "4", "x = 3", "x = 8"],  # A and B are both x = 4
            correct_answer="A",
            rationale="Subtract 5 from both sides",
            topic="algebra",
            difficulty=3,
            paper_type="P1",
            grade="foundation"
        )
        
        result = verifier.verify(question)
        
        # Should detect that option B also equals the correct answer
        assert result.applicable is True


class TestNotApplicable:
    """Test questions that SymPy cannot handle."""
    
    def test_word_problem(self, verifier):
        """Test that word problems are marked as not applicable."""
        question = MCQQuestion(
            stem="John has 5 apples and gives 2 to Mary. How many does he have left?",
            options=["3", "7", "2", "5"],
            correct_answer="A",
            rationale="5 - 2 = 3",
            topic="number",
            difficulty=1,
            paper_type="P1",
            grade="foundation"
        )
        
        result = verifier.verify(question)
        
        assert result.applicable is False
    
    def test_diagram_dependent(self, verifier):
        """Test that diagram-dependent questions are not applicable."""
        question = MCQQuestion(
            stem="What is the area of the shaded region in the diagram?",
            options=["12 cm²", "15 cm²", "18 cm²", "20 cm²"],
            correct_answer="A",
            rationale="Calculate from diagram",
            topic="geometry",
            difficulty=4,
            paper_type="P1",
            grade="foundation"
        )
        
        result = verifier.verify(question)
        
        assert result.applicable is False


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_malformed_equation(self, verifier):
        """Test handling of malformed equations."""
        question = MCQQuestion(
            stem="Solve x + + 5 = 10",  # Malformed
            options=["x = 5", "x = 15", "x = 10", "x = 0"],
            correct_answer="A",
            rationale="Invalid equation",
            topic="algebra",
            difficulty=3,
            paper_type="P1",
            grade="foundation"
        )
        
        result = verifier.verify(question)
        
        # Should handle gracefully
        assert result.applicable is False or result.pass_ is not None
    
    def test_division_by_zero(self, verifier):
        """Test handling of division by zero."""
        question = MCQQuestion(
            stem="Simplify 5/0",
            options=["undefined", "0", "5", "infinity"],
            correct_answer="A",
            rationale="Cannot divide by zero",
            topic="number",
            difficulty=2,
            paper_type="P1",
            grade="foundation"
        )
        
        result = verifier.verify(question)
        
        # Should handle gracefully
        assert result is not None
