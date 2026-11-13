"""
Tests for wording validation in LLM Auditor.

Tests specific wording issues that the LLM auditor should catch:
- Missing units
- Insufficient information
- Diagram-dependent questions without diagrams
- Unclear phrasing
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


class TestMissingUnits:
    """Test detection of missing units in questions."""
    
    def test_missing_units_detected(self, llm_auditor, mock_bedrock_client):
        """Test that missing units are flagged."""
        question = {
            'stem': 'A car travels at 60 for 2 hours. How far does it travel?',
            'options': ['120', '60', '30', '240'],
            'correct_answer': 'A',
            'paper_type': 'P2'
        }
        
        audit_data = {
            'solved_answer': 'A',
            'working': 'Assuming speed is in km/h, distance = 60 * 2 = 120',
            'key_answer': 'A',
            'agreement': True,
            'ambiguity': 'missing-info',
            'issues': ['Missing units for speed (km/h, mph, m/s?)'],
            'confidence': 0.6,
            'verdict': 'FAIL'
        }
        
        mock_bedrock_client.invoke_model.return_value = create_mock_response(audit_data)
        
        result = llm_auditor.audit(question)
        
        assert result.verdict == 'FAIL'
        assert result.ambiguity == 'missing-info'
        assert any('units' in issue.lower() for issue in result.issues)
    
    def test_units_present_passes(self, llm_auditor, mock_bedrock_client):
        """Test that questions with units pass."""
        question = {
            'stem': 'A car travels at 60 km/h for 2 hours. How far does it travel?',
            'options': ['120 km', '60 km', '30 km', '240 km'],
            'correct_answer': 'A',
            'paper_type': 'P2'
        }
        
        audit_data = {
            'solved_answer': 'A',
            'working': 'Distance = speed × time = 60 × 2 = 120 km',
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
        assert result.ambiguity == 'none'


class TestInsufficientInformation:
    """Test detection of insufficient information."""
    
    def test_insufficient_info_detected(self, llm_auditor, mock_bedrock_client):
        """Test that insufficient information is flagged."""
        question = {
            'stem': 'What is the area of the triangle?',
            'options': ['10 cm²', '20 cm²', '15 cm²', '25 cm²'],
            'correct_answer': 'A',
            'paper_type': 'P1'
        }
        
        audit_data = {
            'solved_answer': 'A',
            'working': 'Cannot solve without base and height',
            'key_answer': 'A',
            'agreement': False,
            'ambiguity': 'missing-info',
            'issues': ['No dimensions provided for the triangle'],
            'confidence': 0.2,
            'verdict': 'FAIL'
        }
        
        mock_bedrock_client.invoke_model.return_value = create_mock_response(audit_data)
        
        result = llm_auditor.audit(question)
        
        assert result.verdict == 'FAIL'
        assert result.ambiguity == 'missing-info'
        assert any('dimension' in issue.lower() or 'missing' in issue.lower() 
                   for issue in result.issues)
    
    def test_complete_info_passes(self, llm_auditor, mock_bedrock_client):
        """Test that questions with complete info pass."""
        question = {
            'stem': 'A triangle has base 5 cm and height 4 cm. What is its area?',
            'options': ['10 cm²', '20 cm²', '9 cm²', '25 cm²'],
            'correct_answer': 'A',
            'paper_type': 'P1'
        }
        
        audit_data = {
            'solved_answer': 'A',
            'working': 'Area = (1/2) × base × height = (1/2) × 5 × 4 = 10 cm²',
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
        assert result.ambiguity == 'none'


class TestDiagramDependency:
    """Test detection of diagram-dependent questions."""
    
    def test_diagram_reference_without_diagram(self, llm_auditor, mock_bedrock_client):
        """Test that diagram references without diagrams are flagged."""
        question = {
            'stem': 'In the diagram, what is angle ABC?',
            'options': ['45°', '90°', '60°', '30°'],
            'correct_answer': 'A',
            'paper_type': 'P1'
        }
        
        audit_data = {
            'solved_answer': 'A',
            'working': 'Cannot solve without seeing the diagram',
            'key_answer': 'A',
            'agreement': False,
            'ambiguity': 'missing-info',
            'issues': ['Question references diagram but no diagram provided'],
            'confidence': 0.1,
            'verdict': 'FAIL'
        }
        
        mock_bedrock_client.invoke_model.return_value = create_mock_response(audit_data)
        
        result = llm_auditor.audit(question)
        
        assert result.verdict == 'FAIL'
        assert result.ambiguity == 'missing-info'
        assert any('diagram' in issue.lower() for issue in result.issues)
    
    def test_not_to_scale_without_diagram(self, llm_auditor, mock_bedrock_client):
        """Test that 'not to scale' without diagram is flagged."""
        question = {
            'stem': 'The diagram (not to scale) shows a rectangle. What is its perimeter?',
            'options': ['20 cm', '30 cm', '40 cm', '50 cm'],
            'correct_answer': 'A',
            'paper_type': 'P2'
        }
        
        audit_data = {
            'solved_answer': 'A',
            'working': 'Cannot determine without diagram and dimensions',
            'key_answer': 'A',
            'agreement': False,
            'ambiguity': 'missing-info',
            'issues': ['References diagram (not to scale) but no diagram provided'],
            'confidence': 0.15,
            'verdict': 'FAIL'
        }
        
        mock_bedrock_client.invoke_model.return_value = create_mock_response(audit_data)
        
        result = llm_auditor.audit(question)
        
        assert result.verdict == 'FAIL'
        assert any('diagram' in issue.lower() for issue in result.issues)


class TestUnclearPhrasing:
    """Test detection of unclear phrasing."""
    
    def test_ambiguous_wording(self, llm_auditor, mock_bedrock_client):
        """Test that ambiguous wording is flagged."""
        question = {
            'stem': 'What is the value?',
            'options': ['5', '10', '15', '20'],
            'correct_answer': 'A',
            'paper_type': 'P1'
        }
        
        audit_data = {
            'solved_answer': 'A',
            'working': 'Unclear what value is being asked for',
            'key_answer': 'A',
            'agreement': False,
            'ambiguity': 'unclear-stem',
            'issues': ['Question does not specify which value to find'],
            'confidence': 0.3,
            'verdict': 'FAIL'
        }
        
        mock_bedrock_client.invoke_model.return_value = create_mock_response(audit_data)
        
        result = llm_auditor.audit(question)
        
        assert result.verdict == 'FAIL'
        assert result.ambiguity == 'unclear-stem'
    
    def test_clear_phrasing_passes(self, llm_auditor, mock_bedrock_client):
        """Test that clear phrasing passes."""
        question = {
            'stem': 'Solve for x: 3x + 7 = 22',
            'options': ['x = 5', 'x = 7', 'x = 3', 'x = 15'],
            'correct_answer': 'A',
            'paper_type': 'P1'
        }
        
        audit_data = {
            'solved_answer': 'A',
            'working': 'Subtract 7: 3x = 15, divide by 3: x = 5',
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
        assert result.ambiguity == 'none'


class TestMultipleCorrectAnswers:
    """Test detection of multiple correct answers."""
    
    def test_multiple_correct_detected(self, llm_auditor, mock_bedrock_client):
        """Test that multiple correct answers are flagged."""
        question = {
            'stem': 'Which of these is a prime number?',
            'options': ['2', '3', '4', '6'],
            'correct_answer': 'A',
            'paper_type': 'P1'
        }
        
        audit_data = {
            'solved_answer': 'A',
            'working': 'Both 2 and 3 are prime numbers',
            'key_answer': 'A',
            'agreement': True,
            'ambiguity': 'multiple-correct',
            'issues': ['Both option A (2) and option B (3) are prime numbers'],
            'confidence': 0.95,
            'verdict': 'FAIL'
        }
        
        mock_bedrock_client.invoke_model.return_value = create_mock_response(audit_data)
        
        result = llm_auditor.audit(question)
        
        assert result.verdict == 'FAIL'
        assert result.ambiguity == 'multiple-correct'
    
    def test_single_correct_passes(self, llm_auditor, mock_bedrock_client):
        """Test that single correct answer passes."""
        question = {
            'stem': 'Which of these is the smallest prime number?',
            'options': ['2', '3', '4', '6'],
            'correct_answer': 'A',
            'paper_type': 'P1'
        }
        
        audit_data = {
            'solved_answer': 'A',
            'working': '2 is the smallest prime number',
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


class TestEdgeCases:
    """Test edge cases in wording validation."""
    
    def test_empty_stem(self, llm_auditor, mock_bedrock_client):
        """Test handling of empty question stem."""
        question = {
            'stem': '',
            'options': ['A', 'B', 'C', 'D'],
            'correct_answer': 'A',
            'paper_type': 'P1'
        }
        
        audit_data = {
            'solved_answer': 'A',
            'working': 'No question provided',
            'key_answer': 'A',
            'agreement': False,
            'ambiguity': 'unclear-stem',
            'issues': ['Question stem is empty'],
            'confidence': 0.0,
            'verdict': 'FAIL'
        }
        
        mock_bedrock_client.invoke_model.return_value = create_mock_response(audit_data)
        
        result = llm_auditor.audit(question)
        
        assert result.verdict == 'FAIL'
    
    def test_very_long_question(self, llm_auditor, mock_bedrock_client):
        """Test handling of very long questions."""
        long_stem = "A student " + "walks to school " * 50 + "How far did they walk?"
        
        question = {
            'stem': long_stem,
            'options': ['1 km', '2 km', '3 km', '4 km'],
            'correct_answer': 'A',
            'paper_type': 'P1'
        }
        
        audit_data = {
            'solved_answer': 'A',
            'working': 'Question is overly verbose but solvable',
            'key_answer': 'A',
            'agreement': True,
            'ambiguity': 'none',
            'issues': ['Question could be more concise'],
            'confidence': 0.8,
            'verdict': 'PASS'
        }
        
        mock_bedrock_client.invoke_model.return_value = create_mock_response(audit_data)
        
        result = llm_auditor.audit(question)
        
        # Should still pass if solvable
        assert result.verdict == 'PASS'
