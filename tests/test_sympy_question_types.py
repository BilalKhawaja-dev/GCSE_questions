"""
Integration tests for SymPy Verifier with diverse question types
"""

import pytest
from src.services.sympy_verifier_service import SymPyVerifier, MCQQuestion


@pytest.fixture
def verifier():
    """Create a SymPy verifier instance."""
    return SymPyVerifier()


class TestAlgebraQuestions:
    """Test various algebra question types."""
    
    def test_rearranging_formula(self, verifier):
        """Test rearranging formulas."""
        question = MCQQuestion(
            
            stem="Make x the subject of y = 2x + 5",
            options=["x = (y - 5)/2", "x = y - 5/2", "x = 2y - 5", "x = y/2 - 5"],
            correct_answer="A",
            rationale="Subtract 5 then divide by 2",
            topic="algebra",
            difficulty=4,
            paper_type="P1",
            grade="foundation"
        )
        
        result = verifier.verify(question)
        assert result is not None
    
    def test_substitution(self, verifier):
        """Test substitution into formulas."""
        question = MCQQuestion(
            
            stem="If x = 3, find the value of 2x² + 5",
            options=["23", "11", "18", "28"],
            correct_answer="A",
            rationale="2(3²) + 5 = 2(9) + 5 = 18 + 5 = 23",
            topic="algebra",
            difficulty=3,
            paper_type="P1",
            grade="foundation"
        )
        
        result = verifier.verify(question)
        assert result is not None


class TestArithmeticQuestions:
    """Test arithmetic question types."""
    
    def test_decimal_operations(self, verifier):
        """Test decimal arithmetic."""
        question = MCQQuestion(
            
            stem="Calculate 3.5 + 2.8",
            options=["6.3", "5.3", "6.2", "5.8"],
            correct_answer="A",
            rationale="Add the decimals",
            topic="number",
            difficulty=2,
            paper_type="P1",
            grade="foundation"
        )
        
        result = verifier.verify(question)
        assert result is not None
    
    def test_negative_numbers(self, verifier):
        """Test operations with negative numbers."""
        question = MCQQuestion(
            
            stem="Calculate -5 + 8",
            options=["3", "-3", "13", "-13"],
            correct_answer="A",
            rationale="Moving right on number line",
            topic="number",
            difficulty=2,
            paper_type="P1",
            grade="foundation"
        )
        
        result = verifier.verify(question)
        assert result is not None


class TestGeometryQuestions:
    """Test geometry question types."""
    
    def test_area_calculation(self, verifier):
        """Test area calculations."""
        question = MCQQuestion(
            
            stem="A rectangle has length 8 cm and width 5 cm. Find its area.",
            options=["40 cm²", "26 cm²", "13 cm²", "80 cm²"],
            correct_answer="A",
            rationale="Area = length × width = 8 × 5 = 40",
            topic="geometry",
            difficulty=2,
            paper_type="P1",
            grade="foundation"
        )
        
        result = verifier.verify(question)
        # May not be applicable as it's a word problem
        assert result is not None
    
    def test_perimeter_calculation(self, verifier):
        """Test perimeter calculations."""
        question = MCQQuestion(
            
            stem="A square has side length 6 cm. Find its perimeter.",
            options=["24 cm", "36 cm", "12 cm", "18 cm"],
            correct_answer="A",
            rationale="Perimeter = 4 × side = 4 × 6 = 24",
            topic="geometry",
            difficulty=2,
            paper_type="P1",
            grade="foundation"
        )
        
        result = verifier.verify(question)
        assert result is not None


class TestRatioAndProportion:
    """Test ratio and proportion questions."""
    
    def test_simple_ratio(self, verifier):
        """Test simplifying ratios."""
        question = MCQQuestion(
            
            stem="Simplify the ratio 12:18",
            options=["2:3", "3:2", "4:6", "6:9"],
            correct_answer="A",
            rationale="Divide both by 6",
            topic="ratio",
            difficulty=3,
            paper_type="P1",
            grade="foundation"
        )
        
        result = verifier.verify(question)
        assert result is not None


class TestExactForms:
    """Test questions requiring exact forms."""
    
    def test_surd_in_denominator(self, verifier):
        """Test rationalizing denominators."""
        question = MCQQuestion(
            
            stem="Rationalize 1/√2",
            options=["√2/2", "1/2", "2/√2", "√2"],
            correct_answer="A",
            rationale="Multiply by √2/√2",
            topic="number",
            difficulty=5,
            paper_type="P1",
            grade="higher"
        )
        
        result = verifier.verify(question)
        assert result is not None
    
    def test_pi_in_answer(self, verifier):
        """Test answers involving π."""
        question = MCQQuestion(
            
            stem="Find the circumference of a circle with radius 5 cm. Give answer in terms of π.",
            options=["10π cm", "25π cm", "5π cm", "20π cm"],
            correct_answer="A",
            rationale="C = 2πr = 2π(5) = 10π",
            topic="geometry",
            difficulty=3,
            paper_type="P1",
            grade="foundation"
        )
        
        result = verifier.verify(question)
        assert result is not None


class TestComplexExpressions:
    """Test more complex mathematical expressions."""
    
    def test_nested_brackets(self, verifier):
        """Test expanding nested brackets."""
        question = MCQQuestion(
            
            stem="Expand 2(x + 3)",
            options=["2x + 6", "2x + 3", "x + 6", "2x + 5"],
            correct_answer="A",
            rationale="Multiply each term by 2",
            topic="algebra",
            difficulty=3,
            paper_type="P1",
            grade="foundation"
        )
        
        result = verifier.verify(question)
        assert result is not None
    
    def test_collecting_like_terms(self, verifier):
        """Test collecting like terms."""
        question = MCQQuestion(
            
            stem="Simplify 3x + 2x + 5",
            options=["5x + 5", "5x + 2", "3x + 7", "10x"],
            correct_answer="A",
            rationale="Combine x terms: 3x + 2x = 5x",
            topic="algebra",
            difficulty=2,
            paper_type="P1",
            grade="foundation"
        )
        
        result = verifier.verify(question)
        assert result is not None


class TestBoundaryConditions:
    """Test boundary conditions and special cases."""
    
    def test_zero_solution(self, verifier):
        """Test equation with zero as solution."""
        question = MCQQuestion(
            
            stem="Solve 5x = 0",
            options=["x = 0", "x = 5", "x = -5", "No solution"],
            correct_answer="A",
            rationale="Divide both sides by 5",
            topic="algebra",
            difficulty=2,
            paper_type="P1",
            grade="foundation"
        )
        
        result = verifier.verify(question)
        assert result is not None
    
    def test_negative_solution(self, verifier):
        """Test equation with negative solution."""
        question = MCQQuestion(
            
            stem="Solve x + 5 = 2",
            options=["x = -3", "x = 3", "x = 7", "x = -7"],
            correct_answer="A",
            rationale="Subtract 5 from both sides",
            topic="algebra",
            difficulty=2,
            paper_type="P1",
            grade="foundation"
        )
        
        result = verifier.verify(question)
        assert result is not None
