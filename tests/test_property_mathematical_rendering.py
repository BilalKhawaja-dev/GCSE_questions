"""
Property-based tests for mathematical rendering conversion.

Tests Property 11: Mathematical Rendering Conversion
Validates Requirements 4.1, 4.2, 4.3, 4.4, 4.5
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
import re
from src.utils.math_rendering import convert_latex_to_plain_text, validate_no_latex_syntax


# Strategies for generating LaTeX expressions
@st.composite
def latex_fractions(draw):
    """Generate LaTeX fraction expressions."""
    numerator = draw(st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd'))))
    denominator = draw(st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd'))))
    assume(numerator.strip() and denominator.strip())  # Ensure non-empty after stripping
    return f"\\frac{{{numerator}}}{{{denominator}}}"


@st.composite
def latex_square_roots(draw):
    """Generate LaTeX square root expressions."""
    content = draw(st.text(min_size=1, max_size=15, alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd', 'Pc'))))
    assume(content.strip())  # Ensure non-empty after stripping
    return f"\\sqrt{{{content}}}"


@st.composite
def latex_exponents(draw):
    """Generate LaTeX exponent expressions."""
    base = draw(st.text(min_size=1, max_size=5, alphabet=st.characters(whitelist_categories=('Ll', 'Lu'))))
    exponent = draw(st.one_of(
        st.integers(min_value=0, max_value=99).map(str),
        st.text(min_size=1, max_size=8, alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd', 'Pc')))
    ))
    assume(base.strip() and exponent.strip())
    return f"{base}^{{{exponent}}}"


@st.composite
def latex_operators(draw):
    """Generate LaTeX mathematical operators."""
    operators = ['\\times', '\\div', '\\pm', '\\mp', '\\cdot', '\\leq', '\\geq', '\\neq', '\\approx']
    return draw(st.sampled_from(operators))


@st.composite
def latex_greek_letters(draw):
    """Generate LaTeX Greek letters."""
    greek_letters = ['\\alpha', '\\beta', '\\gamma', '\\delta', '\\pi', '\\theta', '\\lambda', '\\mu', '\\sigma']
    return draw(st.sampled_from(greek_letters))


@st.composite
def latex_functions(draw):
    """Generate LaTeX function names."""
    functions = ['\\sin', '\\cos', '\\tan', '\\log', '\\ln', '\\exp']
    return draw(st.sampled_from(functions))


@st.composite
def math_mode_expressions(draw):
    """Generate expressions wrapped in math mode delimiters."""
    content = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd', 'Pc'))))
    assume(content.strip())
    delimiter_type = draw(st.sampled_from(['dollar', 'paren', 'bracket']))
    
    if delimiter_type == 'dollar':
        return f"${content}$"
    elif delimiter_type == 'paren':
        return f"\\({content}\\)"
    else:  # bracket
        return f"\\[{content}\\]"


@st.composite
def complex_latex_expressions(draw):
    """Generate complex LaTeX expressions combining multiple elements."""
    components = []
    
    # Add 1-3 components
    num_components = draw(st.integers(min_value=1, max_value=3))
    
    for _ in range(num_components):
        component_type = draw(st.sampled_from(['fraction', 'sqrt', 'exponent', 'operator', 'greek', 'function']))
        
        if component_type == 'fraction':
            components.append(draw(latex_fractions()))
        elif component_type == 'sqrt':
            components.append(draw(latex_square_roots()))
        elif component_type == 'exponent':
            components.append(draw(latex_exponents()))
        elif component_type == 'operator':
            components.append(draw(latex_operators()))
        elif component_type == 'greek':
            components.append(draw(latex_greek_letters()))
        elif component_type == 'function':
            components.append(draw(latex_functions()))
    
    return ' '.join(components)


class TestMathematicalRenderingConversion:
    """Test mathematical rendering conversion properties."""
    
    @given(latex_fractions())
    @settings(max_examples=100)
    def test_fraction_conversion_property(self, latex_fraction):
        """
        Feature: gcse-question-generator-v2, Property 11: Mathematical Rendering Conversion
        For any LaTeX fraction expression, the system should convert it to plain text format
        without any remaining LaTeX syntax.
        **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5**
        """
        # Act
        converted = convert_latex_to_plain_text(latex_fraction)
        
        # Assert
        assert validate_no_latex_syntax(converted), f"Converted fraction still contains LaTeX: {converted}"
        assert '\\frac' not in converted, f"Fraction command not converted: {converted}"
        assert '(' in converted and ')' in converted and '/' in converted, f"Fraction not properly formatted: {converted}"
    
    @given(latex_square_roots())
    @settings(max_examples=100)
    def test_square_root_conversion_property(self, latex_sqrt):
        """
        Feature: gcse-question-generator-v2, Property 11: Mathematical Rendering Conversion
        For any LaTeX square root expression, the system should convert it to plain text format
        using Unicode square root symbol or text equivalent.
        **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5**
        """
        # Act
        converted = convert_latex_to_plain_text(latex_sqrt)
        
        # Assert
        assert validate_no_latex_syntax(converted), f"Converted square root still contains LaTeX: {converted}"
        assert '\\sqrt' not in converted, f"Square root command not converted: {converted}"
        assert '√' in converted or 'sqrt' in converted, f"Square root not properly formatted: {converted}"
    
    @given(latex_exponents())
    @settings(max_examples=100)
    def test_exponent_conversion_property(self, latex_exponent):
        """
        Feature: gcse-question-generator-v2, Property 11: Mathematical Rendering Conversion
        For any LaTeX exponent expression, the system should convert it to plain text format
        using Unicode superscripts or caret notation.
        **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5**
        """
        # Act
        converted = convert_latex_to_plain_text(latex_exponent)
        
        # Assert
        assert validate_no_latex_syntax(converted), f"Converted exponent still contains LaTeX: {converted}"
        # Should contain either Unicode superscripts or caret notation
        has_superscript = any(c in converted for c in '⁰¹²³⁴⁵⁶⁷⁸⁹')
        has_caret = '^' in converted
        assert has_superscript or has_caret, f"Exponent not properly formatted: {converted}"
    
    @given(latex_operators())
    @settings(max_examples=100)
    def test_operator_conversion_property(self, latex_operator):
        """
        Feature: gcse-question-generator-v2, Property 11: Mathematical Rendering Conversion
        For any LaTeX mathematical operator, the system should convert it to appropriate
        Unicode symbol or plain text equivalent.
        **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5**
        """
        # Act
        converted = convert_latex_to_plain_text(latex_operator)
        
        # Assert
        assert validate_no_latex_syntax(converted), f"Converted operator still contains LaTeX: {converted}"
        assert not converted.startswith('\\'), f"Operator command not converted: {converted}"
        
        # Check specific conversions
        if latex_operator == '\\times':
            assert '×' in converted
        elif latex_operator == '\\div':
            assert '÷' in converted
        elif latex_operator == '\\pm':
            assert '±' in converted
        elif latex_operator == '\\leq':
            assert '≤' in converted
        elif latex_operator == '\\geq':
            assert '≥' in converted
    
    @given(latex_greek_letters())
    @settings(max_examples=100)
    def test_greek_letter_conversion_property(self, latex_greek):
        """
        Feature: gcse-question-generator-v2, Property 11: Mathematical Rendering Conversion
        For any LaTeX Greek letter, the system should convert it to the appropriate
        Unicode Greek character.
        **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5**
        """
        # Act
        converted = convert_latex_to_plain_text(latex_greek)
        
        # Assert
        assert validate_no_latex_syntax(converted), f"Converted Greek letter still contains LaTeX: {converted}"
        assert not converted.startswith('\\'), f"Greek letter command not converted: {converted}"
        
        # Check that we have a Unicode Greek character
        greek_chars = 'αβγδεζηθικλμνξπρστυφχψωΑΒΓΔΕΖΗΘΙΚΛΜΝΞΠΡΣΤΥΦΧΨΩ'
        assert any(char in converted for char in greek_chars), f"Greek letter not properly converted: {converted}"
    
    @given(latex_functions())
    @settings(max_examples=100)
    def test_function_conversion_property(self, latex_function):
        """
        Feature: gcse-question-generator-v2, Property 11: Mathematical Rendering Conversion
        For any LaTeX function name, the system should convert it to plain text format.
        **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5**
        """
        # Act
        converted = convert_latex_to_plain_text(latex_function)
        
        # Assert
        assert validate_no_latex_syntax(converted), f"Converted function still contains LaTeX: {converted}"
        assert not converted.startswith('\\'), f"Function command not converted: {converted}"
        
        # Check specific conversions
        if latex_function == '\\sin':
            assert 'sin' in converted
        elif latex_function == '\\cos':
            assert 'cos' in converted
        elif latex_function == '\\log':
            assert 'log' in converted
    
    @given(math_mode_expressions())
    @settings(max_examples=100)
    def test_math_mode_removal_property(self, math_expression):
        """
        Feature: gcse-question-generator-v2, Property 11: Mathematical Rendering Conversion
        For any expression wrapped in math mode delimiters, the system should remove
        the delimiters while preserving the content.
        **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5**
        """
        # Act
        converted = convert_latex_to_plain_text(math_expression)
        
        # Assert
        assert validate_no_latex_syntax(converted), f"Converted expression still contains LaTeX: {converted}"
        assert '$' not in converted, f"Dollar signs not removed: {converted}"
        assert '\\(' not in converted and '\\)' not in converted, f"Parentheses delimiters not removed: {converted}"
        assert '\\[' not in converted and '\\]' not in converted, f"Bracket delimiters not removed: {converted}"
    
    @given(complex_latex_expressions())
    @settings(max_examples=100)
    def test_complex_expression_conversion_property(self, complex_expression):
        """
        Feature: gcse-question-generator-v2, Property 11: Mathematical Rendering Conversion
        For any complex LaTeX expression containing multiple mathematical elements,
        the system should convert all elements to plain text format.
        **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5**
        """
        # Act
        converted = convert_latex_to_plain_text(complex_expression)
        
        # Assert
        assert validate_no_latex_syntax(converted), f"Converted complex expression still contains LaTeX: {converted}"
        
        # Check that common LaTeX commands are not present
        latex_commands = ['\\frac', '\\sqrt', '\\times', '\\div', '\\pm', '\\alpha', '\\beta', '\\pi', '\\sin', '\\cos']
        for command in latex_commands:
            assert command not in converted, f"LaTeX command {command} not converted in: {converted}"
    
    @given(st.text(min_size=1, max_size=100))
    @settings(max_examples=100)
    def test_non_latex_text_unchanged_property(self, plain_text):
        """
        Feature: gcse-question-generator-v2, Property 11: Mathematical Rendering Conversion
        For any plain text without LaTeX syntax, the system should return it unchanged
        (except for whitespace normalization).
        **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5**
        """
        # Assume the text doesn't contain LaTeX-like patterns
        assume('\\' not in plain_text)
        assume('$' not in plain_text)
        assume('{' not in plain_text and '}' not in plain_text)
        
        # Act
        converted = convert_latex_to_plain_text(plain_text)
        
        # Assert
        assert validate_no_latex_syntax(converted), f"Plain text validation failed: {converted}"
        # The text should be essentially unchanged (allowing for whitespace normalization)
        normalized_original = ' '.join(plain_text.split())
        normalized_converted = ' '.join(converted.split())
        assert normalized_original == normalized_converted, f"Plain text was modified: '{plain_text}' -> '{converted}'"
    
    @given(st.text(min_size=10, max_size=200))
    @settings(max_examples=50)
    def test_conversion_idempotency_property(self, text):
        """
        Feature: gcse-question-generator-v2, Property 11: Mathematical Rendering Conversion
        For any text, applying the conversion function twice should produce the same result
        as applying it once (idempotency).
        **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5**
        """
        # Act
        first_conversion = convert_latex_to_plain_text(text)
        second_conversion = convert_latex_to_plain_text(first_conversion)
        
        # Assert
        assert first_conversion == second_conversion, f"Conversion is not idempotent: '{first_conversion}' != '{second_conversion}'"
        assert validate_no_latex_syntax(second_conversion), f"Second conversion still contains LaTeX: {second_conversion}"


class TestMathematicalRenderingValidation:
    """Test mathematical rendering validation functions."""
    
    def test_validate_no_latex_syntax_examples(self):
        """Test validation function with known examples."""
        # Valid plain text (should return True)
        valid_examples = [
            "x² + 2x + 1",
            "(3)/(4) + (1)/(2)",
            "√16 = 4",
            "sin(x) + cos(x)",
            "α + β = γ",
            "3 × 4 ÷ 2",
            "x ≤ 5 and y ≥ 10"
        ]
        
        for example in valid_examples:
            assert validate_no_latex_syntax(example), f"Valid example failed validation: {example}"
        
        # Invalid LaTeX syntax (should return False)
        invalid_examples = [
            "\\frac{3}{4}",
            "\\sqrt{16}",
            "$x^2$",
            "\\alpha + \\beta",
            "\\sin(x)",
            "\\times",
            "\\({expression}\\)"
        ]
        
        for example in invalid_examples:
            assert not validate_no_latex_syntax(example), f"Invalid example passed validation: {example}"
    
    def test_conversion_examples_from_module(self):
        """Test conversion using the examples defined in the math_rendering module."""
        from src.utils.math_rendering import get_conversion_examples
        
        examples = get_conversion_examples()
        
        for latex_input, expected_output in examples:
            converted = convert_latex_to_plain_text(latex_input)
            assert converted == expected_output, f"Conversion failed for {latex_input}: expected '{expected_output}', got '{converted}'"
            assert validate_no_latex_syntax(converted), f"Converted output still contains LaTeX: {converted}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])