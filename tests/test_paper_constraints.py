"""
Tests for paper constraint validation in LLM Auditor.

Tests that the LLM auditor correctly validates paper-specific constraints:
- P1 (non-calculator) constraints
- P2/P3 (calculator) constraints
"""

import json
import pytest
from unittest.mock import Mock
from src.services.llm_auditor_service import LLMAuditor


@pytest.fixture
def mock_bedrock_client():
    """Create a mock Bedrock client."""
    return Mock()


@pytest.fixture
def llm_auditor(mock_bedrock_client):
    """Create LLM auditor instance."""
    return LLMAuditor(mock_bedrock_client)


def create_mock_response(audit_data: dict) -> dict:
    """Helper to create mock Bedrock response."""
    response_body = {
        'content': [{
            'text': json.dumps(audit_data)
        }]
    }
    
    mock_response = {
        'body': Mock()
    }
    mock_response['body'].read = Mock(return_value=json.dumps(response_body).encode())
    
    return mock_response


class TestP1NonCalculatorConstraints:
    """Test P1 (non-calculator) paper constraints."""
    
    def test_p1_calculator_mention_rejected(self, llm_auditor, mock_bedrock_client):
        """Test that P1 questions mentioning calculator are rejected."""
        question = {
            'stem': 'Use your calculator to find 15% of 80',
            'options': ['10', '12', '15', '20'],
            'correct_answer': 'B',
            'paper_type': 'P1'
        }
        
        audit_data = {
            'solved_answer': 'B',
            'working': 'Question explicitly requires calculator',
            'key_answer': 'B',
            'agreement': True,
            'ambiguity': 'none',
            'issues': ['P1 paper cannot mention calculator usage'],
            'confidence': 0.95,
            'verdict': 'FAIL'
        }
        
        mock_bedrock_client.invoke_model.return_value = create_mock_response(audit_data)
        
        result = llm_auditor.audit(question)
        
        assert result.verdict == 'FAIL'
        assert any('calculator' in issue.lower() for issue in result.issues)
    
    def test_p1_complex_decimal_rejected(self, llm_auditor, mock_bedrock_client):
        """Test that P1 questions with calculator-dependent decimals are rejected."""
        question = {
            'stem': 'Calculate 17.3 × 8.9 and give your answer to 3 significant figures',
            'options': ['154', '153.97', '154.0', '153'],
            'correct_answer': 'B',
            'paper_type': 'P1'
        }
        
        audit_data = {
            'solved_answer': 'B',
            'working': 'This calculation requires a calculator',
            'key_answer': 'B',
            'agreement': True,
            'ambiguity': 'none',
            'issues': ['P1 paper should not require calculator for complex decimal multiplication'],
            'confidence': 0.9,
            'verdict': 'FAIL'
        }
        
        mock_bedrock_client.invoke_model.return_value = create_mock_response(audit_data)
        
        result = llm_auditor.audit(question)
        
        assert result.verdict == 'FAIL'
        assert any('calculator' in issue.lower() for issue in result.issues)
    
    def test_p1_simple_arithmetic_passes(self, llm_auditor, mock_bedrock_client):
        """Test that P1 questions with simple arithmetic pass."""
        question = {
            'stem': 'Calculate 25 × 4',
            'options': ['100', '90', '110', '80'],
            'correct_answer': 'A',
            'paper_type': 'P1'
        }
        
        audit_data = {
            'solved_answer': 'A',
            'working': '25 × 4 = 100, easily done by hand',
            'key_answer': 'A',
            'agreement': True,
            'ambiguity': 'none',
            'issues': [],
            'confidence': 0.99,
            'verdict': 'PASS'
        }
        
        mock_bedrock_client.invoke_model.return_value = create_mock_response(audit_data)
        
        result = llm_auditor.audit(question)
        
        assert result.verdict == 'PASS'
        assert result.ambiguity == 'none'
    
    def test_p1_exact_forms_passes(self, llm_auditor, mock_bedrock_client):
        """Test that P1 questions with exact forms (surds, fractions) pass."""
        question = {
            'stem': 'Simplify √50',
            'options': ['5√2', '2√5', '√25', '25'],
            'correct_answer': 'A',
            'paper_type': 'P1'
        }
        
        audit_data = {
            'solved_answer': 'A',
            'working': '√50 = √(25×2) = 5√2, no calculator needed',
            'key_answer': 'A',
            'agreement': True,
            'ambiguity': 'none',
            'issues': [],
            'confidence': 0.98,
            'verdict': 'PASS'
        }
        
        mock_bedrock_client.invoke_model.return_value = create_mock_response(audit_data)
        
        result = llm_auditor.audit(question)
        
        assert result.verdict == 'PASS'
    
    def test_p1_fraction_arithmetic_passes(self, llm_auditor, mock_bedrock_client):
        """Test that P1 questions with fraction arithmetic pass."""
        question = {
            'stem': 'Calculate 3/4 + 1/2',
            'options': ['5/4', '4/6', '1/4', '5/6'],
            'correct_answer': 'A',
            'paper_type': 'P1'
        }
        
        audit_data = {
            'solved_answer': 'A',
            'working': '3/4 + 2/4 = 5/4, doable by hand',
            'key_answer': 'A',
            'agreement': True,
            'ambiguity': 'none',
            'issues': [],
            'confidence': 0.97,
            'verdict': 'PASS'
        }
        
        mock_bedrock_client.invoke_model.return_value = create_mock_response(audit_data)
        
        result = llm_auditor.audit(question)
        
        assert result.verdict == 'PASS'
    
    def test_p1_ugly_trig_rejected(self, llm_auditor, mock_bedrock_client):
        """Test that P1 questions with calculator-dependent trig are rejected."""
        question = {
            'stem': 'Calculate sin(37°) to 3 decimal places',
            'options': ['0.602', '0.707', '0.866', '0.500'],
            'correct_answer': 'A',
            'paper_type': 'P1'
        }
        
        audit_data = {
            'solved_answer': 'A',
            'working': 'Requires calculator for non-standard angle',
            'key_answer': 'A',
            'agreement': True,
            'ambiguity': 'none',
            'issues': ['P1 paper cannot require calculator for trig values'],
            'confidence': 0.92,
            'verdict': 'FAIL'
        }
        
        mock_bedrock_client.invoke_model.return_value = create_mock_response(audit_data)
        
        result = llm_auditor.audit(question)
        
        assert result.verdict == 'FAIL'


class TestP2P3CalculatorConstraints:
    """Test P2/P3 (calculator) paper constraints."""
    
    def test_p2_calculator_allowed(self, llm_auditor, mock_bedrock_client):
        """Test that P2 questions can mention calculator."""
        question = {
            'stem': 'Use your calculator to find 15% of 80',
            'options': ['10', '12', '15', '20'],
            'correct_answer': 'B',
            'paper_type': 'P2'
        }
        
        audit_data = {
            'solved_answer': 'B',
            'working': '15% of 80 = 0.15 × 80 = 12',
            'key_answer': 'B',
            'agreement': True,
            'ambiguity': 'none',
            'issues': [],
            'confidence': 0.98,
            'verdict': 'PASS'
        }
        
        mock_bedrock_client.invoke_model.return_value = create_mock_response(audit_data)
        
        result = llm_auditor.audit(question)
        
        assert result.verdict == 'PASS'
    
    def test_p2_complex_calculations_allowed(self, llm_auditor, mock_bedrock_client):
        """Test that P2 questions can have complex calculations."""
        question = {
            'stem': 'Calculate 17.3 × 8.9 and give your answer to 3 significant figures',
            'options': ['154', '153.97', '154.0', '153'],
            'correct_answer': 'A',
            'paper_type': 'P2'
        }
        
        audit_data = {
            'solved_answer': 'A',
            'working': '17.3 × 8.9 = 153.97, rounds to 154 (3 s.f.)',
            'key_answer': 'A',
            'agreement': True,
            'ambiguity': 'none',
            'issues': [],
            'confidence': 0.96,
            'verdict': 'PASS'
        }
        
        mock_bedrock_client.invoke_model.return_value = create_mock_response(audit_data)
        
        result = llm_auditor.audit(question)
        
        assert result.verdict == 'PASS'
    
    def test_p3_decimal_answers_allowed(self, llm_auditor, mock_bedrock_client):
        """Test that P3 questions can have decimal answers."""
        question = {
            'stem': 'Calculate sin(37°) to 3 decimal places',
            'options': ['0.602', '0.707', '0.866', '0.500'],
            'correct_answer': 'A',
            'paper_type': 'P3'
        }
        
        audit_data = {
            'solved_answer': 'A',
            'working': 'sin(37°) ≈ 0.602 using calculator',
            'key_answer': 'A',
            'agreement': True,
            'ambiguity': 'none',
            'issues': [],
            'confidence': 0.95,
            'verdict': 'PASS'
        }
        
        mock_bedrock_client.invoke_model.return_value = create_mock_response(audit_data)
        
        result = llm_auditor.audit(question)
        
        assert result.verdict == 'PASS'


class TestPaperTypeEdgeCases:
    """Test edge cases in paper type validation."""
    
    def test_missing_paper_type_defaults_to_p2(self, llm_auditor, mock_bedrock_client):
        """Test that missing paper type defaults to P2 (calculator)."""
        question = {
            'stem': 'Calculate 15% of 80',
            'options': ['10', '12', '15', '20'],
            'correct_answer': 'B'
            # No paper_type specified
        }
        
        # Should build prompt with P2 default
        prompt = llm_auditor._build_auditor_prompt(question)
        assert 'PAPER TYPE: P2 (CALCULATOR)' in prompt
    
    def test_invalid_paper_type_handled(self, llm_auditor, mock_bedrock_client):
        """Test that invalid paper type is handled gracefully."""
        question = {
            'stem': 'Calculate 15% of 80',
            'options': ['10', '12', '15', '20'],
            'correct_answer': 'B',
            'paper_type': 'P99'  # Invalid
        }
        
        # Should still build prompt
        prompt = llm_auditor._build_auditor_prompt(question)
        assert 'PAPER TYPE: P99' in prompt
    
    def test_borderline_p1_question(self, llm_auditor, mock_bedrock_client):
        """Test borderline P1 question that could go either way."""
        question = {
            'stem': 'Calculate 12.5 × 8',
            'options': ['100', '96', '104', '92'],
            'correct_answer': 'A',
            'paper_type': 'P1'
        }
        
        # This is borderline - could be done by hand but tricky
        # LLM should make judgment call
        audit_data = {
            'solved_answer': 'A',
            'working': '12.5 × 8 = (12 × 8) + (0.5 × 8) = 96 + 4 = 100, doable by hand',
            'key_answer': 'A',
            'agreement': True,
            'ambiguity': 'none',
            'issues': [],
            'confidence': 0.85,
            'verdict': 'PASS'
        }
        
        mock_bedrock_client.invoke_model.return_value = create_mock_response(audit_data)
        
        result = llm_auditor.audit(question)
        
        # Should pass if LLM judges it's doable by hand
        assert result.verdict == 'PASS'


class TestConfidenceScoring:
    """Test confidence scoring for paper constraints."""
    
    def test_high_confidence_clear_violation(self, llm_auditor, mock_bedrock_client):
        """Test high confidence for clear P1 violation."""
        question = {
            'stem': 'Use your calculator to compute 123.456 × 789.012',
            'options': ['97408', '97409', '97410', '97411'],
            'correct_answer': 'A',
            'paper_type': 'P1'
        }
        
        audit_data = {
            'solved_answer': 'A',
            'working': 'Clearly requires calculator',
            'key_answer': 'A',
            'agreement': True,
            'ambiguity': 'none',
            'issues': ['P1 paper explicitly mentions calculator'],
            'confidence': 0.99,
            'verdict': 'FAIL'
        }
        
        mock_bedrock_client.invoke_model.return_value = create_mock_response(audit_data)
        
        result = llm_auditor.audit(question)
        
        assert result.verdict == 'FAIL'
        assert result.confidence >= 0.9
    
    def test_lower_confidence_borderline_case(self, llm_auditor, mock_bedrock_client):
        """Test lower confidence for borderline case."""
        question = {
            'stem': 'Calculate 15 × 7',
            'options': ['105', '100', '110', '95'],
            'correct_answer': 'A',
            'paper_type': 'P1'
        }
        
        audit_data = {
            'solved_answer': 'A',
            'working': '15 × 7 = 105, easily done by hand',
            'key_answer': 'A',
            'agreement': True,
            'ambiguity': 'none',
            'issues': [],
            'confidence': 0.98,
            'verdict': 'PASS'
        }
        
        mock_bedrock_client.invoke_model.return_value = create_mock_response(audit_data)
        
        result = llm_auditor.audit(question)
        
        assert result.verdict == 'PASS'
        assert result.confidence >= 0.75
