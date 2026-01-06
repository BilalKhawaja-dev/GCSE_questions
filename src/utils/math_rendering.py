"""
Mathematical rendering utilities for converting LaTeX to plain text/markdown.

This module provides functions to convert LaTeX mathematical expressions
to human-readable plain text or markdown format for better accessibility
and display without requiring special rendering libraries.
"""

import re
from typing import Dict, List, Tuple


def convert_latex_to_plain_text(text: str) -> str:
    """
    Convert LaTeX mathematical expressions to plain text/markdown format.
    
    This function converts common LaTeX mathematical notation to Unicode
    symbols and plain text equivalents for better readability.
    
    Args:
        text: Input text containing LaTeX expressions
        
    Returns:
        Text with LaTeX expressions converted to plain text/markdown
        
    Examples:
        >>> convert_latex_to_plain_text("\\frac{3}{4}")
        "(3)/(4)"
        >>> convert_latex_to_plain_text("x^{2} + 2x + 1")
        "x² + 2x + 1"
        >>> convert_latex_to_plain_text("\\sqrt{16}")
        "√16"
    """
    if not text:
        return text
    
    # Store original text for comparison
    original_text = text
    
    # Step 0: Remove math mode delimiters FIRST but preserve content
    text = re.sub(r'\$([^$]+)\$', r'\1', text)  # Inline math mode
    text = re.sub(r'\\\(([^)]+)\\\)', r'\1', text)  # Display math mode
    text = re.sub(r'\\\[([^\]]+)\\\]', r'\1', text)  # Display math mode
    
    # Step 1: Convert fractions - \frac{numerator}{denominator} → (numerator)/(denominator)
    # Handle special case for derivatives like d/dx
    text = re.sub(r'\\frac\{d\}\{dx\}', 'd/dx', text)
    text = re.sub(r'\\frac\{d\}\{d([a-zA-Z])\}', r'd/d\1', text)
    
    # General fraction conversion - handle nested braces properly
    def replace_fraction(match):
        full_match = match.group(0)
        # Find the numerator and denominator by counting braces
        start_pos = full_match.find('{')
        if start_pos == -1:
            return full_match
        
        brace_count = 0
        numerator_start = start_pos + 1
        numerator_end = -1
        
        for i, char in enumerate(full_match[numerator_start:], numerator_start):
            if char == '{':
                brace_count += 1
            elif char == '}':
                if brace_count == 0:
                    numerator_end = i
                    break
                brace_count -= 1
        
        if numerator_end == -1:
            return full_match
        
        numerator = full_match[numerator_start:numerator_end]
        
        # Find denominator
        denominator_start = numerator_end + 2  # Skip }{
        if denominator_start >= len(full_match) or full_match[numerator_end:numerator_end+2] != '}{':
            return full_match
        
        brace_count = 0
        denominator_end = -1
        
        for i, char in enumerate(full_match[denominator_start:], denominator_start):
            if char == '{':
                brace_count += 1
            elif char == '}':
                if brace_count == 0:
                    denominator_end = i
                    break
                brace_count -= 1
        
        if denominator_end == -1:
            return full_match
        
        denominator = full_match[denominator_start:denominator_end]
        return f'({numerator})/({denominator})'
    
    text = re.sub(r'\\frac\{[^}]*(?:\{[^}]*\}[^}]*)*\}\{[^}]*(?:\{[^}]*\}[^}]*)*\}', replace_fraction, text)
    
    # Step 2: Convert square roots - \sqrt{x} → √x
    text = re.sub(r'\\sqrt\{([^}]+)\}', r'√\1', text)
    
    # Step 3: Convert exponents - x^{2} → x² (for single digits and common cases)
    superscript_map = {
        '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
        '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
        '+': '⁺', '-': '⁻', '=': '⁼', '(': '⁽', ')': '⁾',
        'n': 'ⁿ', 'x': 'ˣ', 'y': 'ʸ'
    }
    
    def replace_exponent(match):
        exp = match.group(1)
        # For simple single character or digit exponents, use superscript
        if len(exp) == 1 and exp in superscript_map:
            return superscript_map[exp]
        # For simple numeric exponents up to 2 digits
        elif exp.isdigit() and len(exp) <= 2:
            return ''.join(superscript_map.get(c, c) for c in exp)
        # For complex exponents, use ^(expression) format
        else:
            return f'^({exp})'
    
    # Handle both \^{expression} and ^{expression} formats
    text = re.sub(r'\\?\^\{([^}]+)\}', replace_exponent, text)
    text = re.sub(r'\\?\^([0-9])', lambda m: superscript_map.get(m.group(1), f'^{m.group(1)}'), text)
    
    # Step 4: Convert subscripts - x_{1} → x₁
    subscript_map = {
        '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄',
        '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉',
        '+': '₊', '-': '₋', '=': '₌', '(': '₍', ')': '₎',
        'a': 'ₐ', 'e': 'ₑ', 'i': 'ᵢ', 'o': 'ₒ', 'u': 'ᵤ',
        'x': 'ₓ', 'n': 'ₙ'
    }
    
    def replace_subscript(match):
        sub = match.group(1)
        if len(sub) == 1 and sub in subscript_map:
            return subscript_map[sub]
        elif sub.isdigit() and len(sub) <= 2:
            return ''.join(subscript_map.get(c, c) for c in sub)
        else:
            return f'_({sub})'
    
    text = re.sub(r'\\?_\{([^}]+)\}', replace_subscript, text)
    text = re.sub(r'\\?_([0-9])', lambda m: subscript_map.get(m.group(1), f'_{m.group(1)}'), text)
    
    # Step 5: Convert mathematical operators
    operator_replacements = {
        r'\\times': '×',
        r'\\div': '÷',
        r'\\pm': '±',
        r'\\mp': '∓',
        r'\\cdot': '·',
        r'\\ast': '*',
        r'\\star': '⋆',
        r'\\circ': '∘',
        r'\\bullet': '•',
        r'\\oplus': '⊕',
        r'\\ominus': '⊖',
        r'\\otimes': '⊗',
        r'\\oslash': '⊘'
    }
    
    for latex_op, unicode_op in operator_replacements.items():
        text = re.sub(latex_op, unicode_op, text)
    
    # Step 6: Convert comparison operators
    comparison_replacements = {
        r'\\leq': '≤',
        r'\\geq': '≥',
        r'\\neq': '≠',
        r'\\approx': '≈',
        r'\\equiv': '≡',
        r'\\sim': '∼',
        r'\\simeq': '≃',
        r'\\cong': '≅',
        r'\\propto': '∝',
        r'\\ll': '≪',
        r'\\gg': '≫'
    }
    
    for latex_comp, unicode_comp in comparison_replacements.items():
        text = re.sub(latex_comp, unicode_comp, text)
    
    # Step 7: Convert set theory and logic symbols
    set_logic_replacements = {
        r'\\in': '∈',
        r'\\notin': '∉',
        r'\\subset': '⊂',
        r'\\supset': '⊃',
        r'\\subseteq': '⊆',
        r'\\supseteq': '⊇',
        r'\\cup': '∪',
        r'\\cap': '∩',
        r'\\emptyset': '∅',
        r'\\infty': '∞',
        r'\\forall': '∀',
        r'\\exists': '∃',
        r'\\neg': '¬',
        r'\\land': '∧',
        r'\\lor': '∨'
    }
    
    for latex_symbol, unicode_symbol in set_logic_replacements.items():
        text = re.sub(latex_symbol, unicode_symbol, text)
    
    # Step 8: Convert Greek letters (common ones)
    greek_replacements = {
        r'\\alpha': 'α', r'\\beta': 'β', r'\\gamma': 'γ', r'\\delta': 'δ',
        r'\\epsilon': 'ε', r'\\zeta': 'ζ', r'\\eta': 'η', r'\\theta': 'θ',
        r'\\iota': 'ι', r'\\kappa': 'κ', r'\\lambda': 'λ', r'\\mu': 'μ',
        r'\\nu': 'ν', r'\\xi': 'ξ', r'\\pi': 'π', r'\\rho': 'ρ',
        r'\\sigma': 'σ', r'\\tau': 'τ', r'\\upsilon': 'υ', r'\\phi': 'φ',
        r'\\chi': 'χ', r'\\psi': 'ψ', r'\\omega': 'ω',
        r'\\Gamma': 'Γ', r'\\Delta': 'Δ', r'\\Theta': 'Θ', r'\\Lambda': 'Λ',
        r'\\Xi': 'Ξ', r'\\Pi': 'Π', r'\\Sigma': 'Σ', r'\\Phi': 'Φ',
        r'\\Psi': 'Ψ', r'\\Omega': 'Ω'
    }
    
    for latex_greek, unicode_greek in greek_replacements.items():
        text = re.sub(latex_greek, unicode_greek, text)
    
    # Step 9: Convert special functions
    function_replacements = {
        r'\\sin': 'sin',
        r'\\cos': 'cos',
        r'\\tan': 'tan',
        r'\\log': 'log',
        r'\\ln': 'ln',
        r'\\exp': 'exp',
        r'\\lim': 'lim',
        r'\\max': 'max',
        r'\\min': 'min',
        r'\\gcd': 'gcd',
        r'\\lcm': 'lcm'
    }
    
    for latex_func, plain_func in function_replacements.items():
        text = re.sub(latex_func, plain_func, text)
    
    # Step 10: Clean up remaining LaTeX commands (generic cleanup)
    # Remove simple LaTeX commands like \text{...}, \mathrm{...}, etc.
    text = re.sub(r'\\(?:text|mathrm|mathbf|mathit|mathcal|mathbb|mathfrak)\{([^}]+)\}', r'\1', text)
    
    # Remove alignment and spacing commands
    text = re.sub(r'\\(?:left|right|big|Big|bigg|Bigg)([()[\]|])', r'\1', text)
    text = re.sub(r'\\(?:quad|qquad|,|;|!|\s)', ' ', text)
    
    # Remove remaining backslash commands that we haven't handled
    text = re.sub(r'\\[a-zA-Z]+\*?', '', text)
    
    # Step 11: Clean up orphaned braces and extra whitespace
    # Only remove braces that are clearly orphaned (not part of fractions we converted)
    # Be more careful about brace removal - only remove if they don't contain operators
    text = re.sub(r'\{([^{}]*)\}', r'\1', text)
    text = re.sub(r'\s+', ' ', text)  # Multiple spaces to single space
    text = text.strip()
    
    return text


def validate_no_latex_syntax(text: str) -> bool:
    """
    Validate that text contains no LaTeX syntax.
    
    This function checks for common LaTeX patterns to ensure
    mathematical expressions have been properly converted.
    
    Args:
        text: Text to validate
        
    Returns:
        True if no LaTeX syntax found, False otherwise
        
    Examples:
        >>> validate_no_latex_syntax("x² + 2x + 1")
        True
        >>> validate_no_latex_syntax("\\frac{3}{4}")
        False
    """
    if not text:
        return True
    
    # Patterns that indicate LaTeX syntax
    latex_patterns = [
        r'\\frac\{.*?\}\{.*?\}',      # Fractions
        r'\\sqrt\{.*?\}',             # Square roots
        r'\\[a-zA-Z]+\{.*?\}',        # General LaTeX commands with braces
        r'\$.*?\$',                   # Inline math mode
        r'\\\(.*?\\\)',               # Display math mode (parentheses)
        r'\\\[.*?\\\]',               # Display math mode (brackets)
        r'\\[a-zA-Z]+\*?(?![a-zA-Z])', # LaTeX commands without braces
        r'\{.*?\}',                   # Remaining braces (might be LaTeX remnants)
    ]
    
    for pattern in latex_patterns:
        if re.search(pattern, text):
            return False
    
    return True


def get_conversion_examples() -> List[Tuple[str, str]]:
    """
    Get examples of LaTeX to plain text conversions.
    
    Returns:
        List of (latex_input, expected_output) tuples for testing
    """
    return [
        # Fractions
        (r'\frac{3}{4}', '(3)/(4)'),
        (r'\frac{x+1}{x-1}', '(x+1)/(x-1)'),
        (r'\frac{a^2}{b^2}', '(a²)/(b²)'),
        
        # Square roots
        (r'\sqrt{16}', '√16'),
        (r'\sqrt{x^2 + y^2}', '√x² + y²'),
        (r'\sqrt{\frac{3}{4}}', '√(3)/(4)'),
        
        # Exponents
        (r'x^2', 'x²'),
        (r'x^{10}', 'x¹⁰'),
        (r'x^{n+1}', 'x^(n+1)'),
        (r'2^{3x}', '2^(3x)'),
        
        # Subscripts
        (r'x_1', 'x₁'),
        (r'a_{n+1}', 'a_(n+1)'),
        
        # Operators
        (r'3 \times 4', '3 × 4'),
        (r'12 \div 3', '12 ÷ 3'),
        (r'x \pm 2', 'x ± 2'),
        (r'a \cdot b', 'a · b'),
        
        # Comparisons
        (r'x \leq 5', 'x ≤ 5'),
        (r'y \geq 10', 'y ≥ 10'),
        (r'a \neq b', 'a ≠ b'),
        (r'x \approx 3.14', 'x ≈ 3.14'),
        
        # Greek letters
        (r'\pi r^2', 'π r²'),
        (r'\theta = 45°', 'θ = 45°'),
        (r'\alpha + \beta', 'α + β'),
        
        # Functions
        (r'\sin(x)', 'sin(x)'),
        (r'\log_2(8)', 'log₂(8)'),
        (r'\ln(e)', 'ln(e)'),
        
        # Complex expressions
        (r'$\frac{-b \pm \sqrt{b^2 - 4ac}}{2a}$', '(-b ± √b² - 4ac)/(2a)'),
        (r'\frac{d}{dx}(x^2) = 2x', 'd/dx(x²) = 2x'),
        (r'A = \pi r^2', 'A = π r²'),
        
        # Mixed expressions
        (r'If $x^2 + 2x + 1 = 0$, find $x$.', 'If x² + 2x + 1 = 0, find x.'),
        (r'Calculate $\frac{3}{4} \times \frac{2}{5}$', 'Calculate (3)/(4) × (2)/(5)'),
    ]


def test_conversion_examples() -> Dict[str, bool]:
    """
    Test the conversion function with example inputs.
    
    Returns:
        Dictionary mapping test cases to pass/fail status
    """
    examples = get_conversion_examples()
    results = {}
    
    for latex_input, expected_output in examples:
        actual_output = convert_latex_to_plain_text(latex_input)
        passed = actual_output == expected_output
        results[f"{latex_input} → {expected_output}"] = passed
        
        if not passed:
            print(f"FAIL: {latex_input}")
            print(f"  Expected: {expected_output}")
            print(f"  Actual:   {actual_output}")
    
    return results


if __name__ == "__main__":
    # Run tests when module is executed directly
    print("Testing LaTeX to plain text conversion...")
    results = test_conversion_examples()
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed. See details above.")