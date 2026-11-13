"""
Unit tests for LLM Auditor Service.
"""

import json
import pytest
from unittest.mock import Mock, MagicMock, patch
from src.services.llm_auditor_service import LLMAuditor, AuditResult


@pytest.fixture
def mock_bedrock_client():
    """Create a mock Bedrock client."""
    client = Mock()
    return client


@pytest.fixture
def llm_auditor(mock_bedrock_client):
    """Create LLM auditor instance."""
    return LLMAuditor(mock_bedrock_client)


@pytest.fixture
def sample_question():
    """Sample question for testing."""
    return {
        'stem': 'Solve 2x + 5 = 13',
        'options': ['x = 4', 'x = 9', 'x = 3', 'x = 8'],
        'correct_answer': 'A',
        'paper_type': 'P1',
        'topic': 'algebra',
        'grade': 'foundation'
    }


def create_mock_bedrock_response(audit_data: dict) -> dict:
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


class TestLLMAuditorBasics:
    """Test basic LLM auditor functionality."""
    
    def test_initialization(self, mock_bedrock_client):
        """Test auditor initialization."""
        auditor = LLMAuditor(mock_bedrock_client)
        
        assert auditor.bedrock == mock_bedrock_client
        assert auditor.model_id == "anthropic.claude-3-5-sonnet-20241022-v2:0"
        assert auditor.confidence_threshold == 0.75
        assert auditor.max_retries == 3
    
    def test_custom_model_id(self, mock_bedrock_client):
        """Test initialization with custom model ID."""
        custom_model = "anthropic.claude-3-opus-20240229-v1:0"
        auditor = LLMAuditor(mock_bedrock_client, model_id=custom_model)
        
        assert auditor.model_id == custom_model


class TestPromptBuilding:
    """Test prompt building functionality."""
    
    def test_build_auditor_prompt(self, llm_auditor, sample_question):
        """Test prompt building with sample question."""
        prompt = llm_auditor._build_auditor_prompt(sample_question)
        
        # Check key elements are present
        assert 'Solve 2x + 5 = 13' in prompt
        assert 'A) x = 4' in prompt
        assert 'B) x = 9' in prompt
        assert 'C) x = 3' in prompt
        assert 'D) x = 8' in prompt
        assert 'PROVIDED ANSWER KEY: A' in prompt
        assert 'PAPER TYPE: P1 (NON-CALCULATOR)' in prompt
        assert 'hostile auditor' in prompt
        assert 'strict JSON' in prompt
    
    def test_prompt_paper_type_p2(self, llm_auditor):
        """Test prompt for P2 (calculator) paper."""
        question = {
            'stem': 'Calculate 15% of 80',
            'options': ['10', '12', '15', '20'],
            'correct_answer': 'B',
            'paper_type': 'P2'
        }
        
        prompt = llm_auditor._build_auditor_prompt(question)
        
        assert 'PAPER TYPE: P2 (CALCULATOR)' in prompt
    
    def test_prompt_with_missing_fields(self, llm_auditor):
        """Test prompt building with minimal question data."""
        question = {
            'stem': 'What is 2 + 2?',
            'options': ['3', '4', '5', '6'],
            'correct_answer': 'B'
        }
        
        prompt = llm_auditor._build_auditor_prompt(question)
        
        # Should still work with defaults
        assert 'What is 2 + 2?' in prompt
        assert 'TOPIC: unknown' in prompt
        assert 'GRADE: foundation' in prompt


class TestStructuredOutputParsing:
    """Test parsing of LLM structured output."""
    
    def test_parse_valid_json(self, llm_auditor):
        """Test parsing valid JSON response."""
        response_text = json.dumps({
            'solved_answer': 'A',
            'working': 'Subtract 5 from both sides: 2x = 8, then divide by 2: x = 4',
            'key_answer': 'A',
            'agreement': True,
            'ambiguity': 'none',
            'issues': [],
            'confidence': 0.95,
            'verdict': 'PASS'
        })
        
        result = llm_auditor._parse_structured_output(response_text)
        
        assert isinstance(result, AuditResult)
        assert result.solved_answer == 'A'
        assert result.key_answer == 'A'
        assert result.agreement is True
        assert result.ambiguity == 'none'
        assert result.issues == []
        assert result.confidence == 0.95
        assert result.verdict == 'PASS'
    
    def test_parse_json_with_extra_text(self, llm_auditor):
        """Test parsing JSON when LLM adds extra text."""
        response_text = """Here is my analysis:
        
        {
            "solved_answer": "B",
            "working": "Some working",
            "key_answer": "B",
            "agreement": true,
            "ambiguity": "none",
            "issues": [],
            "confidence": 0.85,
            "verdict": "PASS"
        }
        
        That's my assessment."""
        
        result = llm_auditor._parse_structured_output(response_text)
        
        assert result.solved_answer == 'B'
        assert result.confidence == 0.85
    
    def test_parse_fail_verdict(self, llm_auditor):
        """Test parsing FAIL verdict."""
        response_text = json.dumps({
            'solved_answer': 'C',
            'working': 'Working shows C',
            'key_answer': 'A',
            'agreement': False,
            'ambiguity': 'multiple-correct',
            'issues': ['Both A and C could be correct'],
            'confidence': 0.6,
            'verdict': 'FAIL'
        })
        
        result = llm_auditor._parse_structured_output(response_text)
        
        assert result.verdict == 'FAIL'
        assert result.agreement is False
        assert result.ambiguity == 'multiple-correct'
        assert len(result.issues) == 1
    
    def test_parse_invalid_json(self, llm_auditor):
        """Test parsing invalid JSON raises error."""
        response_text = "This is not JSON at all"
        
        with pytest.raises(ValueError, match="Failed to parse structured output"):
            llm_auditor._parse_structured_output(response_text)
    
    def test_parse_empty_response(self, llm_auditor):
        """Test parsing empty response raises error."""
        response_text = ""
        
        with pytest.raises(ValueError):
            llm_auditor._parse_structured_output(response_text)


class TestAuditResultValidation:
    """Test validation of audit results."""
    
    def test_validate_valid_result(self, llm_auditor):
        """Test validation of valid audit result."""
        result = AuditResult(
            verdict='PASS',
            solved_answer='A',
            key_answer='A',
            agreement=True,
            ambiguity='none',
            issues=[],
            confidence=0.9
        )
        
        assert llm_auditor._validate_audit_result(result) is True
    
    def test_validate_invalid_solved_answer(self, llm_auditor):
        """Test validation fails for invalid solved answer."""
        result = AuditResult(
            verdict='PASS',
            solved_answer='E',  # Invalid
            key_answer='A',
            agreement=True,
            ambiguity='none',
            issues=[],
            confidence=0.9
        )
        
        assert llm_auditor._validate_audit_result(result) is False
    
    def test_validate_invalid_ambiguity(self, llm_auditor):
        """Test validation fails for invalid ambiguity value."""
        result = AuditResult(
            verdict='PASS',
            solved_answer='A',
            key_answer='A',
            agreement=True,
            ambiguity='invalid-value',  # Invalid
            issues=[],
            confidence=0.9
        )
        
        assert llm_auditor._validate_audit_result(result) is False
    
    def test_validate_invalid_confidence(self, llm_auditor):
        """Test validation fails for out-of-range confidence."""
        result = AuditResult(
            verdict='PASS',
            solved_answer='A',
            key_answer='A',
            agreement=True,
            ambiguity='none',
            issues=[],
            confidence=1.5  # Invalid
        )
        
        assert llm_auditor._validate_audit_result(result) is False
    
    def test_validate_non_list_issues(self, llm_auditor):
        """Test validation fails for non-list issues."""
        result = AuditResult(
            verdict='PASS',
            solved_answer='A',
            key_answer='A',
            agreement=True,
            ambiguity='none',
            issues="not a list",  # Invalid
            confidence=0.9
        )
        
        assert llm_auditor._validate_audit_result(result) is False


class TestPassRules:
    """Test pass/fail rule application."""
    
    def test_pass_all_criteria_met(self, llm_auditor):
        """Test PASS when all criteria met."""
        result = AuditResult(
            verdict='PASS',
            solved_answer='A',
            key_answer='A',
            agreement=True,
            ambiguity='none',
            issues=[],
            confidence=0.85
        )
        
        verdict = llm_auditor._apply_pass_rules(result)
        assert verdict == 'PASS'
    
    def test_fail_no_agreement(self, llm_auditor):
        """Test FAIL when answers don't agree."""
        result = AuditResult(
            verdict='PASS',
            solved_answer='B',
            key_answer='A',
            agreement=False,
            ambiguity='none',
            issues=[],
            confidence=0.85
        )
        
        verdict = llm_auditor._apply_pass_rules(result)
        assert verdict == 'FAIL'
    
    def test_fail_ambiguity_present(self, llm_auditor):
        """Test FAIL when ambiguity detected."""
        result = AuditResult(
            verdict='PASS',
            solved_answer='A',
            key_answer='A',
            agreement=True,
            ambiguity='multiple-correct',
            issues=[],
            confidence=0.85
        )
        
        verdict = llm_auditor._apply_pass_rules(result)
        assert verdict == 'FAIL'
    
    def test_fail_low_confidence(self, llm_auditor):
        """Test FAIL when confidence below threshold."""
        result = AuditResult(
            verdict='PASS',
            solved_answer='A',
            key_answer='A',
            agreement=True,
            ambiguity='none',
            issues=[],
            confidence=0.5  # Below 0.75 threshold
        )
        
        verdict = llm_auditor._apply_pass_rules(result)
        assert verdict == 'FAIL'
    
    def test_fail_major_issues(self, llm_auditor):
        """Test FAIL when major issues present."""
        result = AuditResult(
            verdict='PASS',
            solved_answer='A',
            key_answer='A',
            agreement=True,
            ambiguity='none',
            issues=['Question requires calculator for P1 paper'],
            confidence=0.85
        )
        
        verdict = llm_auditor._apply_pass_rules(result)
        assert verdict == 'FAIL'
    
    def test_pass_minor_issues(self, llm_auditor):
        """Test PASS with minor issues."""
        result = AuditResult(
            verdict='PASS',
            solved_answer='A',
            key_answer='A',
            agreement=True,
            ambiguity='none',
            issues=['Could be slightly clearer'],
            confidence=0.85
        )
        
        verdict = llm_auditor._apply_pass_rules(result)
        assert verdict == 'PASS'


class TestBedrockIntegration:
    """Test Bedrock API integration."""
    
    def test_invoke_bedrock_success(self, llm_auditor, mock_bedrock_client):
        """Test successful Bedrock invocation."""
        audit_data = {
            'solved_answer': 'A',
            'working': 'Working',
            'key_answer': 'A',
            'agreement': True,
            'ambiguity': 'none',
            'issues': [],
            'confidence': 0.9,
            'verdict': 'PASS'
        }
        
        mock_bedrock_client.invoke_model.return_value = create_mock_bedrock_response(audit_data)
        
        response = llm_auditor._invoke_bedrock_with_retry("test prompt")
        
        assert json.dumps(audit_data) in response
        mock_bedrock_client.invoke_model.assert_called_once()
    
    def test_invoke_bedrock_with_retry(self, llm_auditor, mock_bedrock_client):
        """Test Bedrock retry logic."""
        audit_data = {
            'solved_answer': 'A',
            'working': 'Working',
            'key_answer': 'A',
            'agreement': True,
            'ambiguity': 'none',
            'issues': [],
            'confidence': 0.9,
            'verdict': 'PASS'
        }
        
        # Fail twice, then succeed
        mock_bedrock_client.invoke_model.side_effect = [
            Exception("Transient error"),
            Exception("Another error"),
            create_mock_bedrock_response(audit_data)
        ]
        
        response = llm_auditor._invoke_bedrock_with_retry("test prompt")
        
        assert json.dumps(audit_data) in response
        assert mock_bedrock_client.invoke_model.call_count == 3
    
    def test_invoke_bedrock_max_retries_exceeded(self, llm_auditor, mock_bedrock_client):
        """Test Bedrock fails after max retries."""
        mock_bedrock_client.invoke_model.side_effect = Exception("Persistent error")
        
        with pytest.raises(Exception, match="Persistent error"):
            llm_auditor._invoke_bedrock_with_retry("test prompt")
        
        assert mock_bedrock_client.invoke_model.call_count == 3


class TestFullAuditFlow:
    """Test complete audit flow."""
    
    def test_audit_passing_question(self, llm_auditor, mock_bedrock_client, sample_question):
        """Test audit of a passing question."""
        audit_data = {
            'solved_answer': 'A',
            'working': 'Subtract 5: 2x = 8, divide by 2: x = 4',
            'key_answer': 'A',
            'agreement': True,
            'ambiguity': 'none',
            'issues': [],
            'confidence': 0.95,
            'verdict': 'PASS'
        }
        
        mock_bedrock_client.invoke_model.return_value = create_mock_bedrock_response(audit_data)
        
        result = llm_auditor.audit(sample_question)
        
        assert result.verdict == 'PASS'
        assert result.agreement is True
        assert result.confidence == 0.95
        assert result.ambiguity == 'none'
    
    def test_audit_failing_question(self, llm_auditor, mock_bedrock_client):
        """Test audit of a failing question."""
        question = {
            'stem': 'What is the answer?',
            'options': ['A', 'B', 'C', 'D'],
            'correct_answer': 'A',
            'paper_type': 'P1'
        }
        
        audit_data = {
            'solved_answer': 'B',
            'working': 'Unclear question',
            'key_answer': 'A',
            'agreement': False,
            'ambiguity': 'unclear-stem',
            'issues': ['Question is too vague'],
            'confidence': 0.3,
            'verdict': 'FAIL'
        }
        
        mock_bedrock_client.invoke_model.return_value = create_mock_bedrock_response(audit_data)
        
        result = llm_auditor.audit(question)
        
        assert result.verdict == 'FAIL'
        assert result.agreement is False
        assert result.ambiguity == 'unclear-stem'
    
    def test_audit_with_bedrock_error(self, llm_auditor, mock_bedrock_client, sample_question):
        """Test audit handles Bedrock errors gracefully."""
        mock_bedrock_client.invoke_model.side_effect = Exception("Bedrock error")
        
        result = llm_auditor.audit(sample_question)
        
        assert result.verdict == 'FAIL'
        assert result.confidence == 0.0
        assert 'Audit error' in result.issues[0]
    
    def test_audit_with_invalid_response(self, llm_auditor, mock_bedrock_client, sample_question):
        """Test audit handles invalid LLM response."""
        # Mock response with invalid JSON
        mock_response = {
            'body': Mock()
        }
        mock_response['body'].read = Mock(return_value=json.dumps({
            'content': [{'text': 'Not valid JSON'}]
        }).encode())
        
        mock_bedrock_client.invoke_model.return_value = mock_response
        
        result = llm_auditor.audit(sample_question)
        
        assert result.verdict == 'FAIL'
        assert result.confidence == 0.0


class TestAuditResultDataclass:
    """Test AuditResult dataclass."""
    
    def test_audit_result_creation(self):
        """Test creating AuditResult."""
        result = AuditResult(
            verdict='PASS',
            solved_answer='A',
            key_answer='A',
            agreement=True,
            ambiguity='none',
            issues=[],
            confidence=0.9,
            working='Some working'
        )
        
        assert result.verdict == 'PASS'
        assert result.solved_answer == 'A'
        assert result.working == 'Some working'
    
    def test_audit_result_to_dict(self):
        """Test converting AuditResult to dictionary."""
        result = AuditResult(
            verdict='PASS',
            solved_answer='A',
            key_answer='A',
            agreement=True,
            ambiguity='none',
            issues=[],
            confidence=0.9
        )
        
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert result_dict['verdict'] == 'PASS'
        assert result_dict['confidence'] == 0.9
        assert result_dict['issues'] == []
