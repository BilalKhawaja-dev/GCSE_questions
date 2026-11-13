"""
SymPy Verification Service

Provides mathematical verification using SymPy for programmatic correctness checking.
Handles algebra, arithmetic, geometry, and other mathematical question types.
"""

import re
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal
from dataclasses import dataclass
import logging

try:
    import sympy as sp
    from sympy import symbols, simplify, solve, sympify, expand, factor
    from sympy import sqrt, pi, sin, cos, tan, Rational
    from sympy.parsing.latex import parse_latex
    import numpy as np
    SYMPY_AVAILABLE = True
except ImportError:
    SYMPY_AVAILABLE = False
    sp = None

from src.models.verification import SymPyVerificationResult

logger = logging.getLogger(__name__)


@dataclass
class MCQQuestion:
    """Simple MCQ question structure for verification."""
    stem: str
    options: List[str]
    correct_answer: str  # Letter: A, B, C, or D
    topic: str
    difficulty: int
    paper_type: str
    grade: str
    rationale: Optional[str] = None


class SymPyVerifier:
    """
    Mathematical verification service using SymPy.
    
    Verifies mathematical correctness for:
    - Linear equations
    - Quadratic equations
    - Simultaneous equations
    - Factorising and expanding
    - Surds and exact forms
    - Fractions, decimals, percentages
    - Pythagoras theorem
    - Basic trigonometry
    """
    
    def __init__(self, tolerance: float = 1e-10):
        """
        Initialize SymPy verifier.
        
        Args:
            tolerance: Numeric tolerance for floating point comparisons
        """
        if not SYMPY_AVAILABLE:
            raise ImportError("SymPy and NumPy are required for mathematical verification")
        
        self.tolerance = tolerance
        self.x, self.y, self.z = symbols('x y z')
        self.a, self.b, self.c = symbols('a b c')
    
    def verify(self, question: MCQQuestion) -> SymPyVerificationResult:
        """
        Verify mathematical correctness of a question.
        
        Args:
            question: MCQ question to verify
            
        Returns:
            SymPyVerificationResult with pass/fail status and details
        """
        try:
            # Check if question is SymPy-solvable
            question_type = self._detect_question_type(question)
            
            if question_type == "not_applicable":
                return SymPyVerificationResult(
                    applicable=False,
                    pass_=None,
                    confidence=0.0,
                    reason="Not a SymPy-solvable question type"
                )
            
            # Parse and solve the question
            solution = self._solve_question(question, question_type)
            
            if solution is None:
                return SymPyVerificationResult(
                    applicable=False,
                    pass_=None,
                    confidence=0.0,
                    reason=f"Failed to parse or solve {question_type} question"
                )
            
            # Compare solution to provided answer
            correct_answer_value = self._extract_answer_value(
                question.correct_answer,
                question.options
            )
            
            if correct_answer_value is None:
                return SymPyVerificationResult(
                    applicable=False,
                    pass_=None,
                    confidence=0.0,
                    reason="Failed to parse correct answer"
                )
            
            # Check if solution matches correct answer
            is_correct = self._check_equality(solution, correct_answer_value)
            
            # Verify distractors are actually wrong
            distractor_check = self._verify_distractors(
                solution,
                question.options,
                question.correct_answer
            )
            
            return SymPyVerificationResult(
                applicable=True,
                pass_=is_correct and len(distractor_check["issues"]) == 0,
                confidence=1.0 if is_correct else 0.0,
                solved_answer=str(solution),
                reason=None if is_correct else f"Solution mismatch: computed {solution}, answer key says {correct_answer_value}",
                distractor_quality=distractor_check
            )
            
        except Exception as e:
            logger.error(f"SymPy verification error: {str(e)}", exc_info=True)
            return SymPyVerificationResult(
                applicable=False,
                pass_=None,
                confidence=0.0,
                reason=f"Verification error: {str(e)}"
            )
    
    def _detect_question_type(self, question: MCQQuestion) -> str:
        """Detect the type of mathematical question."""
        stem = question.stem.lower()
        
        # Linear equations
        if any(word in stem for word in ["solve", "find x", "find y"]):
            if "²" not in stem and "squared" not in stem and "x^2" not in stem:
                return "linear_equation"
            else:
                return "quadratic_equation"
        
        # Factorising
        if "factoris" in stem or "factor" in stem:
            return "factorising"
        
        # Expanding
        if "expand" in stem or "multiply out" in stem:
            return "expanding"
        
        # Surds
        if "√" in stem or "sqrt" in stem or "surd" in stem:
            return "surd"
        
        # Fractions - improved detection
        if "/" in stem or "fraction" in stem:
            if any(word in stem for word in ["simplify", "add", "subtract", "calculate", "+"]):
                return "fraction"
        
        # Percentages
        if "%" in stem or "percent" in stem:
            return "percentage"
        
        # Pythagoras
        if "pythagoras" in stem or ("triangle" in stem and any(word in stem for word in ["hypotenuse", "right-angled", "right angled"])):
            return "pythagoras"
        
        # Trigonometry
        if any(word in stem for word in ["sin", "cos", "tan", "sine", "cosine", "tangent"]):
            return "trigonometry"
        
        # Simultaneous equations
        if "simultaneous" in stem or (stem.count("=") >= 2):
            return "simultaneous"
        
        return "not_applicable"
    
    def _solve_question(self, question: MCQQuestion, question_type: str) -> Optional[Any]:
        """Solve the question based on its type."""
        try:
            if question_type == "linear_equation":
                return self._solve_linear(question.stem)
            elif question_type == "quadratic_equation":
                return self._solve_quadratic(question.stem)
            elif question_type == "simultaneous":
                return self._solve_simultaneous(question.stem)
            elif question_type == "factorising":
                return self._factorise(question.stem)
            elif question_type == "expanding":
                return self._expand(question.stem)
            elif question_type == "surd":
                return self._simplify_surd(question.stem)
            elif question_type == "fraction":
                return self._simplify_fraction(question.stem)
            elif question_type == "percentage":
                return self._calculate_percentage(question.stem)
            elif question_type == "pythagoras":
                return self._solve_pythagoras(question.stem)
            elif question_type == "trigonometry":
                return self._solve_trig(question.stem)
            
            return None
        except Exception as e:
            logger.debug(f"Failed to solve {question_type}: {str(e)}")
            return None
    
    def _solve_linear(self, stem: str) -> Optional[Any]:
        """Solve linear equation like '2x + 5 = 13'."""
        # Extract equation
        equation_match = re.search(r'([0-9x\+\-\*/\s]+)=([0-9x\+\-\*/\s]+)', stem)
        if not equation_match:
            return None
        
        lhs, rhs = equation_match.groups()
        
        # Add multiplication signs where needed (e.g., "2x" -> "2*x")
        lhs = re.sub(r'(\d)([a-z])', r'\1*\2', lhs.strip())
        rhs = re.sub(r'(\d)([a-z])', r'\1*\2', rhs.strip())
        
        try:
            lhs_expr = sympify(lhs)
            rhs_expr = sympify(rhs)
            equation = sp.Eq(lhs_expr, rhs_expr)
            solution = solve(equation, self.x)
            
            if solution:
                return solution[0] if isinstance(solution, list) else solution
        except Exception as e:
            logger.debug(f"Failed to solve linear equation: {str(e)}")
        
        return None
    
    def _solve_quadratic(self, stem: str) -> Optional[Any]:
        """Solve quadratic equation like 'x² - 5x + 6 = 0'."""
        # Normalize notation
        stem = stem.replace("²", "**2").replace("^2", "**2")
        
        # Extract equation
        equation_match = re.search(r'([0-9x\+\-\*/\s\*]+)=([0-9x\+\-\*/\s\*]+)', stem)
        if not equation_match:
            return None
        
        lhs, rhs = equation_match.groups()
        
        # Add multiplication signs where needed
        lhs = re.sub(r'(\d)([a-z])', r'\1*\2', lhs.strip())
        rhs = re.sub(r'(\d)([a-z])', r'\1*\2', rhs.strip())
        
        try:
            lhs_expr = sympify(lhs)
            rhs_expr = sympify(rhs)
            equation = sp.Eq(lhs_expr, rhs_expr)
            solutions = solve(equation, self.x)
            
            # Return solutions as a set for easier comparison
            return set(solutions) if solutions else None
        except Exception as e:
            logger.debug(f"Failed to solve quadratic: {str(e)}")
        
        return None
    
    def _solve_simultaneous(self, stem: str) -> Optional[Any]:
        """Solve simultaneous equations."""
        # Extract two equations
        equations = re.findall(r'([0-9xy\+\-\*/\s]+)=([0-9xy\+\-\*/\s]+)', stem)
        if len(equations) < 2:
            return None
        
        try:
            eq1_lhs = sympify(equations[0][0].strip())
            eq1_rhs = sympify(equations[0][1].strip())
            eq2_lhs = sympify(equations[1][0].strip())
            eq2_rhs = sympify(equations[1][1].strip())
            
            eq1 = sp.Eq(eq1_lhs, eq1_rhs)
            eq2 = sp.Eq(eq2_lhs, eq2_rhs)
            
            solution = solve([eq1, eq2], [self.x, self.y])
            return solution
        except:
            pass
        
        return None
    
    def _factorise(self, stem: str) -> Optional[Any]:
        """Factorise expression like 'x² + 7x + 12'."""
        # Extract expression to factorise
        expr_match = re.search(r'factoris[e]?\s+([0-9x²\+\-\s\^]+)', stem, re.IGNORECASE)
        if not expr_match:
            return None
        
        expr_str = expr_match.group(1).strip()
        expr_str = expr_str.replace("²", "**2").replace("^2", "**2")
        
        # Add multiplication signs
        expr_str = re.sub(r'(\d)([a-z])', r'\1*\2', expr_str)
        
        try:
            expr = sympify(expr_str)
            factored = factor(expr)
            return factored
        except Exception as e:
            logger.debug(f"Failed to factorise: {str(e)}")
        
        return None
    
    def _expand(self, stem: str) -> Optional[Any]:
        """Expand expression like '(x + 3)(x + 4)'."""
        # Extract expression to expand
        expr_match = re.search(r'\(([^)]+)\)\s*\(([^)]+)\)', stem)
        if not expr_match:
            return None
        
        try:
            term1_str = expr_match.group(1).strip()
            term2_str = expr_match.group(2).strip()
            
            # Add multiplication signs
            term1_str = re.sub(r'(\d)([a-z])', r'\1*\2', term1_str)
            term2_str = re.sub(r'(\d)([a-z])', r'\1*\2', term2_str)
            
            term1 = sympify(term1_str)
            term2 = sympify(term2_str)
            expanded = expand(term1 * term2)
            return expanded
        except Exception as e:
            logger.debug(f"Failed to expand: {str(e)}")
        
        return None
    
    def _simplify_surd(self, stem: str) -> Optional[Any]:
        """Simplify surd like '√50'."""
        # Extract surd
        surd_match = re.search(r'√(\d+)', stem)
        if not surd_match:
            surd_match = re.search(r'sqrt\((\d+)\)', stem)
        
        if not surd_match:
            return None
        
        try:
            number = int(surd_match.group(1))
            simplified = sqrt(number)
            return simplified
        except:
            pass
        
        return None
    
    def _simplify_fraction(self, stem: str) -> Optional[Any]:
        """Simplify or calculate fraction."""
        # Extract fractions
        fractions = re.findall(r'(\d+)/(\d+)', stem)
        if not fractions:
            return None
        
        try:
            if len(fractions) == 1:
                # Single fraction to simplify
                num, den = fractions[0]
                result = Rational(int(num), int(den))
                return result
            elif len(fractions) >= 2:
                # Two fractions to add/subtract
                frac1 = Rational(int(fractions[0][0]), int(fractions[0][1]))
                frac2 = Rational(int(fractions[1][0]), int(fractions[1][1]))
                
                if "+" in stem or "add" in stem.lower():
                    return frac1 + frac2
                elif "-" in stem or "subtract" in stem.lower():
                    return frac1 - frac2
                elif "*" in stem or "multiply" in stem.lower() or "×" in stem:
                    return frac1 * frac2
                elif "÷" in stem or "divide" in stem.lower():
                    return frac1 / frac2
        except Exception as e:
            logger.debug(f"Failed to simplify fraction: {str(e)}")
        
        return None
    
    def _calculate_percentage(self, stem: str) -> Optional[Any]:
        """Calculate percentage like '15% of 80'."""
        # Extract percentage calculation
        percent_match = re.search(r'(\d+)%\s+of\s+(\d+)', stem)
        if not percent_match:
            return None
        
        try:
            percent = int(percent_match.group(1))
            value = int(percent_match.group(2))
            result = (percent * value) / 100
            return result
        except:
            pass
        
        return None
    
    def _solve_pythagoras(self, stem: str) -> Optional[Any]:
        """Solve Pythagoras theorem problem."""
        # Extract numbers from stem (ignore units like cm, m)
        numbers = re.findall(r'(\d+(?:\.\d+)?)\s*(?:cm|m|mm)?', stem)
        if len(numbers) < 2:
            return None
        
        try:
            nums = [float(n) for n in numbers]
            
            # Check if finding hypotenuse or side
            if "hypotenuse" in stem.lower():
                # c² = a² + b²
                result = sqrt(nums[0]**2 + nums[1]**2)
            else:
                # a² = c² - b² (finding a side)
                # Assume first number is hypotenuse if larger
                if nums[0] > nums[1]:
                    result = sqrt(nums[0]**2 - nums[1]**2)
                else:
                    result = sqrt(nums[1]**2 - nums[0]**2)
            
            return result
        except Exception as e:
            logger.debug(f"Failed to solve Pythagoras: {str(e)}")
        
        return None
    
    def _solve_trig(self, stem: str) -> Optional[Any]:
        """Solve basic trigonometry (with numeric tolerance)."""
        import math
        
        # Extract angle and trig function
        # Common patterns: "sin(30)", "cos 45", "tan(60°)"
        
        # Try to find trig function and angle
        trig_match = re.search(r'(sin|cos|tan)\s*\(?\s*(\d+(?:\.\d+)?)\s*°?\)?', stem, re.IGNORECASE)
        if not trig_match:
            return None
        
        func_name = trig_match.group(1).lower()
        angle_degrees = float(trig_match.group(2))
        
        # Convert to radians
        angle_radians = math.radians(angle_degrees)
        
        try:
            # Calculate trig value
            if func_name == 'sin':
                result = math.sin(angle_radians)
            elif func_name == 'cos':
                result = math.cos(angle_radians)
            elif func_name == 'tan':
                result = math.tan(angle_radians)
            else:
                return None
            
            # Round to reasonable precision (3 decimal places)
            result = round(result, 3)
            
            return result
        except Exception as e:
            logger.debug(f"Failed to solve trig: {str(e)}")
        
        return None
    
    def _extract_answer_value(self, correct_letter: str, options: List[str]) -> Optional[Any]:
        """Extract the value from the correct answer option."""
        # Find the correct option
        correct_index = ord(correct_letter.upper()) - ord('A')
        if correct_index < 0 or correct_index >= len(options):
            return None
        
        correct_option = options[correct_index]
        
        # Try to parse as mathematical expression
        try:
            # Clean up the option text
            value_str = correct_option.strip()
            
            # Remove units (cm, m, mm, etc.)
            value_str = re.sub(r'\s*(cm|m|mm|km|°|degrees?)\s*$', '', value_str, flags=re.IGNORECASE)
            
            # Handle common formats
            if "x = " in value_str or "y = " in value_str:
                value_str = value_str.split("=")[1].strip()
            
            # Handle "or" in quadratic solutions (e.g., "x = 2 or x = 3")
            if " or " in value_str.lower():
                parts = re.findall(r'[xy]\s*=\s*([^or]+)', value_str, re.IGNORECASE)
                if parts:
                    # Return as a set for comparison
                    solutions = set()
                    for part in parts:
                        part = part.strip()
                        part = part.replace("²", "**2").replace("^2", "**2")
                        part = part.replace("√", "sqrt")
                        part = re.sub(r'(\d)([a-z])', r'\1*\2', part)
                        try:
                            solutions.add(sympify(part))
                        except:
                            pass
                    return solutions if solutions else None
            
            # Replace special characters
            value_str = value_str.replace("²", "**2").replace("^2", "**2")
            value_str = value_str.replace("√", "sqrt")
            
            # Add multiplication signs
            value_str = re.sub(r'(\d)([a-z])', r'\1*\2', value_str)
            
            # Add multiplication between )( for factored forms
            value_str = re.sub(r'\)\s*\(', ')*(', value_str)
            
            # Handle factored form like "(x + 3)(x + 4)"
            if "(" in value_str and ")" in value_str:
                # For factored forms, expand them for comparison
                try:
                    # Parse the factored form
                    expr = sympify(value_str)
                    # Return both factored and expanded for flexible comparison
                    return expr
                except Exception as e:
                    logger.debug(f"Failed to parse factored form: {str(e)}")
            
            # Handle fractions in text form (e.g., "23/20")
            if "/" in value_str and not any(c.isalpha() for c in value_str):
                parts = value_str.split("/")
                if len(parts) == 2:
                    try:
                        return Rational(int(parts[0].strip()), int(parts[1].strip()))
                    except:
                        pass
            
            # Try to sympify
            value = sympify(value_str)
            return value
        except Exception as e:
            logger.debug(f"Failed to parse answer '{correct_option}': {str(e)}")
            # Try as plain number
            try:
                # Remove units first
                clean_str = re.sub(r'\s*(cm|m|mm|km|°|degrees?)\s*$', '', correct_option.strip(), flags=re.IGNORECASE)
                return float(clean_str)
            except:
                pass
        
        return None
    
    def _check_equality(self, computed: Any, expected: Any) -> bool:
        """Check if two values are equal (symbolic or numeric)."""
        try:
            # Handle sets (for quadratic solutions)
            if isinstance(computed, set) and isinstance(expected, set):
                if len(computed) != len(expected):
                    return False
                # Check if all elements match
                for c in computed:
                    found = False
                    for e in expected:
                        if self._check_equality(c, e):
                            found = True
                            break
                    if not found:
                        return False
                return True
            
            # Handle set vs single value
            if isinstance(computed, set):
                return any(self._check_equality(c, expected) for c in computed)
            if isinstance(expected, set):
                return any(self._check_equality(computed, e) for e in expected)
            
            # Try symbolic simplification
            diff = simplify(computed - expected)
            if diff == 0:
                return True
            
            # Try numeric evaluation
            try:
                computed_float = float(computed)
                expected_float = float(expected)
                return abs(computed_float - expected_float) < self.tolerance
            except:
                pass
            
            # Try string comparison for complex expressions
            if str(simplify(computed)) == str(simplify(expected)):
                return True
            
            # Try expanding both and comparing (for factored vs expanded forms)
            try:
                computed_expanded = expand(computed)
                expected_expanded = expand(expected)
                if simplify(computed_expanded - expected_expanded) == 0:
                    return True
            except:
                pass
            
            # Try factoring both and comparing
            try:
                computed_factored = factor(computed)
                expected_factored = factor(expected)
                if simplify(computed_factored - expected_factored) == 0:
                    return True
            except:
                pass
            
        except Exception as e:
            logger.debug(f"Equality check failed: {str(e)}")
        
        return False
    
    def _verify_distractors(
        self,
        correct_solution: Any,
        options: List[str],
        correct_letter: str
    ) -> Dict[str, Any]:
        """Verify that wrong answers are actually wrong."""
        issues = []
        
        for i, option in enumerate(options):
            letter = chr(ord('A') + i)
            
            # Skip the correct answer
            if letter == correct_letter.upper():
                continue
            
            # Try to parse this option
            option_value = self._extract_answer_value(letter, options)
            if option_value is None:
                continue
            
            # Check if this distractor equals the correct answer
            if self._check_equality(correct_solution, option_value):
                issues.append(
                    f"Option {letter} ({option}) equals correct answer"
                )
        
        return {
            "quality": "good" if not issues else "poor",
            "issues": issues
        }
