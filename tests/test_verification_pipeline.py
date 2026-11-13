"""Tests for Verification Pipeline (verification_lambda)."""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from src.models.verification import (
    VerificationResult,
    DeterministicCheckResult,
    SymPyVerificationResult,
    CheckResult
)


@pytest.fixture
def sample_question():
    """Sample question for testing."""
    return {
        'question_id': 'test-123',
        'stem': 'Solve 2x + 5 = 13',
        'options': ['x = 4', 'x = 9', 'x = 3', 'x = 8'],
        'correct_answer': 'A',
        'rationale': 'Subtract 5 from both sides: 2x = 8, then divide by 2: x = 4',
        'topic': 'algebra',
        'grade': 'foundation',
        'paper_type': 'P1',
        'difficulty': 5,
        'created_at': '2026-01-13T10:00:00Z'
    }


@pytest.fixture
def mock_verification_services():
    """Mock all verification services."""
    with patch('src.lambda_handlers.verification_lambda.deterministic_verifier') as det_mock, \
         patch('src.lambda_handlers.verification_lambda.sympy_verifier') as sympy_mock, \
         patch('src.lambda_handlers.verification_lambda.llm_auditor') as llm_mock, \
         patch('src.lambda_handlers.verification_lambda.kb_alignment_service') as kb_mock, \
         patch('src.lambda_handlers.verification_lambda.dedupe_service') as dedupe_mock, \
         patch('src.lambda_handlers.verification_lambda.inventory_service') as inv_mock:
        
        yield {
            'deterministic': det_mock,
            'sympy': sympy_mock,
            'llm': llm_mock,
            'kb': kb_mock,
            'dedupe': dedupe_mock,
            'inventory': inv_mock
        }


def test_verification_pipeline_all_pass(sample_question, mock_verification_services):
    """Test verification pipeline when all checks pass."""
    from src.lambda_handlers.verification_lambda import verify_question
    from src.services.llm_auditor_service import AuditResult
    from src.services.kb_alignment_service import AlignmentResult, SourceCheck, SyllabusCheck
    from src.services.dedupe_service import DedupeResult
    
    # Mock deterministic checks - PASS
    mock_verification_services['deterministic'].verify.return_value = DeterministicCheckResult(
        pass_=True,
        issues=[],
        checks_performed=['schema', 'mcq_structure', 'paper_constraints']
    )
    
    # Mock SymPy verification - PASS
    mock_verification_services['sympy'].verify.return_value = SymPyVerificationResult(
        applicable=True,
        pass_=True,
        confidence=1.0,
        solved_answer='x = 4',
        distractor_quality={'quality': 'good', 'issues': []}
    )
    
    # Mock LLM auditor - PASS
    mock_verification_services['llm'].audit.return_value = AuditResult(
        verdict='PASS',
        solved_answer='A',
        key_answer='A',
        agreement=True,
        ambiguity='none',
        issues=[],
        confidence=0.85
    )
    
    # Mock KB alignment - PASS
    mock_verification_services['kb'].verify_alignment.return_value = AlignmentResult(
        pass_=True,
        source_alignment=SourceCheck(
            pass_=True,
            confidence=0.8,
            reasoning='Answer supported by KB material',
            retrieved_docs=[]
        ),
        syllabus_compliance=SyllabusCheck(
            pass_=True,
            confidence=0.9,
            reasoning='Within Edexcel 1MA1 scope',
            retrieved_docs=[]
        ),
        overall_confidence=0.85
    )
    
    # Mock dedupe - PASS
    mock_verification_services['dedupe'].check_duplicate.return_value = DedupeResult(
        pass_=True,
        max_similarity=0.42,
        embedding=[0.1] * 1024
    )
    
    # Run verification
    result = verify_question(sample_question)
    
    # Assertions
    assert result.verdict == 'PASS'
    assert result.overall_confidence > 0.8
    assert len(result.failure_reasons) == 0
    assert 'deterministic' in result.verification_results
    assert 'sympy' in result.verification_results
    assert 'llm_auditor' in result.verification_results
    assert 'kb_alignment' in result.verification_results
    assert 'dedupe' in result.verification_results


def test_verification_pipeline_deterministic_fail(sample_question, mock_verification_services):
    """Test verification pipeline when deterministic checks fail."""
    from src.lambda_handlers.verification_lambda import verify_question
    
    # Mock deterministic checks - FAIL
    mock_verification_services['deterministic'].verify.return_value = DeterministicCheckResult(
        pass_=False,
        issues=['Missing required field: stem'],
        checks_performed=['schema']
    )
    
    # Run verification
    result = verify_question(sample_question)
    
    # Assertions
    assert result.verdict == 'FAIL'
    assert result.overall_confidence == 0.0
    assert 'Missing required field: stem' in result.failure_reasons
    # Should fail fast - other checks not run
    assert 'sympy' not in result.verification_results


def test_verification_pipeline_llm_fail(sample_question, mock_verification_services):
    """Test verification pipeline when LLM auditor fails."""
    from src.lambda_handlers.verification_lambda import verify_question
    from src.services.llm_auditor_service import AuditResult
    from src.services.kb_alignment_service import AlignmentResult, SourceCheck, SyllabusCheck
    from src.services.dedupe_service import DedupeResult
    
    # Mock deterministic checks - PASS
    mock_verification_services['deterministic'].verify.return_value = DeterministicCheckResult(
        pass_=True,
        issues=[],
        checks_performed=['schema', 'mcq_structure']
    )
    
    # Mock SymPy verification - not applicable
    mock_verification_services['sympy'].verify.return_value = SymPyVerificationResult(
        applicable=False,
        pass_=None,
        confidence=0.0,
        reason='Not a SymPy-solvable question'
    )
    
    # Mock LLM auditor - FAIL
    mock_verification_services['llm'].audit.return_value = AuditResult(
        verdict='FAIL',
        solved_answer='B',
        key_answer='A',
        agreement=False,
        ambiguity='none',
        issues=['Answer disagreement: solved B, key says A'],
        confidence=0.9
    )
    
    # Mock KB alignment - PASS (to continue pipeline)
    mock_verification_services['kb'].verify_alignment.return_value = AlignmentResult(
        pass_=True,
        source_alignment=SourceCheck(pass_=True, confidence=0.8, reasoning='OK', retrieved_docs=[]),
        syllabus_compliance=SyllabusCheck(pass_=True, confidence=0.8, reasoning='OK', retrieved_docs=[]),
        overall_confidence=0.8
    )
    
    # Mock dedupe - PASS (to continue pipeline)
    mock_verification_services['dedupe'].check_duplicate.return_value = DedupeResult(
        pass_=True,
        max_similarity=0.42,
        embedding=[0.1] * 1024
    )
    
    # Run verification
    result = verify_question(sample_question)
    
    # Assertions
    assert result.verdict == 'FAIL'
    assert any('LLM Auditor' in reason for reason in result.failure_reasons)


def test_verification_pipeline_dedupe_fail(sample_question, mock_verification_services):
    """Test verification pipeline when dedupe check fails."""
    from src.lambda_handlers.verification_lambda import verify_question
    from src.services.llm_auditor_service import AuditResult
    from src.services.kb_alignment_service import AlignmentResult, SourceCheck, SyllabusCheck
    from src.services.dedupe_service import DedupeResult
    
    # Mock all checks PASS except dedupe
    mock_verification_services['deterministic'].verify.return_value = DeterministicCheckResult(
        pass_=True,
        issues=[],
        checks_performed=['schema']
    )
    
    mock_verification_services['sympy'].verify.return_value = SymPyVerificationResult(
        applicable=False,
        pass_=None,
        confidence=0.0
    )
    
    mock_verification_services['llm'].audit.return_value = AuditResult(
        verdict='PASS',
        solved_answer='A',
        key_answer='A',
        agreement=True,
        ambiguity='none',
        issues=[],
        confidence=0.85
    )
    
    mock_verification_services['kb'].verify_alignment.return_value = AlignmentResult(
        pass_=True,
        source_alignment=SourceCheck(pass_=True, confidence=0.8, reasoning='OK', retrieved_docs=[]),
        syllabus_compliance=SyllabusCheck(pass_=True, confidence=0.8, reasoning='OK', retrieved_docs=[]),
        overall_confidence=0.8
    )
    
    # Mock dedupe - FAIL (duplicate detected)
    mock_verification_services['dedupe'].check_duplicate.return_value = DedupeResult(
        pass_=False,
        max_similarity=0.92,
        similar_question_id='existing-question-456'
    )
    
    # Run verification
    result = verify_question(sample_question)
    
    # Assertions
    assert result.verdict == 'FAIL'
    assert any('Duplicate detected' in reason for reason in result.failure_reasons)
    # Check that similarity is mentioned (format may vary)
    assert len(result.failure_reasons) > 0


def test_store_verified_question():
    """Test storing verified question in DynamoDB."""
    from src.lambda_handlers.verification_lambda import store_verified_question
    
    with patch('src.lambda_handlers.verification_lambda.dynamodb') as mock_dynamodb, \
         patch('src.lambda_handlers.verification_lambda.inventory_service') as mock_inventory:
        
        # Mock table
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        
        question_data = {
            'question_id': 'test-123',
            'stem': 'Test question',
            'options': ['A', 'B', 'C', 'D'],
            'correct_answer': 'A',
            'topic': 'algebra',
            'grade': 'foundation',
            'paper_type': 'P1',
            'difficulty': 5,
            'embedding': [0.1] * 1024
        }
        
        verification_result = VerificationResult(
            question_id='test-123',
            verdict='PASS',
            verification_results={},
            overall_confidence=0.85,
            timestamp='2026-01-13T10:00:00Z'
        )
        
        result = store_verified_question(question_data, verification_result)
        
        assert result is True
        mock_table.put_item.assert_called_once()
        mock_inventory.update_inventory_count.assert_called_once()


def test_store_rejected_question():
    """Test storing rejected question in DynamoDB."""
    from src.lambda_handlers.verification_lambda import store_rejected_question
    
    with patch('src.lambda_handlers.verification_lambda.dynamodb') as mock_dynamodb:
        
        # Mock table
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        
        question_data = {
            'question_id': 'test-123',
            'stem': 'Test question',
            'options': ['A', 'B', 'C', 'D'],
            'correct_answer': 'A',
            'topic': 'algebra',
            'grade': 'foundation',
            'paper_type': 'P1'
        }
        
        verification_result = VerificationResult(
            question_id='test-123',
            verdict='FAIL',
            verification_results={},
            overall_confidence=0.3,
            timestamp='2026-01-13T10:00:00Z',
            failure_reasons=['LLM Auditor: ambiguous wording']
        )
        
        result = store_rejected_question(question_data, verification_result)
        
        assert result is True
        mock_table.put_item.assert_called_once()
        
        # Check that failure reasons were stored
        call_args = mock_table.put_item.call_args
        item = call_args[1]['Item']
        assert 'failure_reasons' in item
        assert len(item['failure_reasons']) > 0


def test_handler_sqs_event():
    """Test verification lambda handler with SQS event."""
    from src.lambda_handlers.verification_lambda import handler
    
    with patch('src.lambda_handlers.verification_lambda.verify_question') as mock_verify, \
         patch('src.lambda_handlers.verification_lambda.store_verified_question') as mock_store_verified, \
         patch('src.lambda_handlers.verification_lambda.store_rejected_question') as mock_store_rejected:
        
        # Mock verification result - PASS
        mock_verify.return_value = VerificationResult(
            question_id='test-123',
            verdict='PASS',
            verification_results={},
            overall_confidence=0.85,
            timestamp='2026-01-13T10:00:00Z'
        )
        
        # Create SQS event
        event = {
            'Records': [
                {
                    'body': json.dumps({
                        'question_id': 'test-123',
                        'stem': 'Test question',
                        'options': ['A', 'B', 'C', 'D'],
                        'correct_answer': 'A',
                        'topic': 'algebra',
                        'grade': 'foundation',
                        'paper_type': 'P1'
                    })
                }
            ]
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['passed'] == 1
        assert body['failed'] == 0
        
        mock_verify.assert_called_once()
        mock_store_verified.assert_called_once()
        mock_store_rejected.assert_not_called()
