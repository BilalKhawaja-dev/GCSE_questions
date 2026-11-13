"""
Tests for source alignment verification.
Validates that correct answers align with KB material.
"""

import pytest
import json
from unittest.mock import Mock, patch
from src.services.kb_alignment_service import KBAlignmentService


@pytest.fixture
def kb_service():
    """Create KB alignment service for testing."""
    return KBAlignmentService(
        knowledge_base_id='test-kb-id',
        source_confidence_threshold=0.7
    )


class TestSourceAlignmentScenarios:
    """Test various source alignment scenarios."""
    
    @patch.object(KBAlignmentService, '_retrieve_from_kb')
    @patch.object(KBAlignmentService, '_invoke_llm')
    def test_algebra_question_supported(
        self,
        mock_llm,
        mock_retrieve,
        kb_service
    ):
        """Test algebra question with supporting KB material."""
        question = {
            'stem': 'Solve 3x - 7 = 14',
            'options': ['x = 7', 'x = 21', 'x = 5', 'x = 3'],
            'correct_answer': 'A',
            'topic': 'algebra',
            'grade': 'foundation'
        }
        
        mock_retrieve.return_value = [
            {
                'content': 'To solve 3x - 7 = 14, add 7 to both sides: 3x = 21, then divide by 3: x = 7',
                'score': 0.9,
                'source': 'algebra-guide.pdf',
                'metadata': {}
            }
        ]
        
        mock_llm.return_value = json.dumps({
            'supported': True,
            'confidence': 0.95,
            'reasoning': 'KB material explicitly shows x = 7 is correct'
        })
        
        result = kb_service._verify_source_alignment(question)
        
        assert result.pass_ is True
        assert result.confidence >= 0.7
    
    @patch.object(KBAlignmentService, '_retrieve_from_kb')
    @patch.object(KBAlignmentService, '_invoke_llm')
    def test_geometry_question_contradicted(
        self,
        mock_llm,
        mock_retrieve,
        kb_service
    ):
        """Test geometry question where KB contradicts answer."""
        question = {
            'stem': 'What is the sum of angles in a triangle?',
            'options': ['180°', '360°', '90°', '270°'],
            'correct_answer': 'B',  # Wrong answer
            'topic': 'geometry',
            'grade': 'foundation'
        }
        
        mock_retrieve.return_value = [
            {
                'content': 'The sum of angles in any triangle is always 180 degrees',
                'score': 0.95,
                'source': 'geometry-basics.pdf',
                'metadata': {}
            }
        ]
        
        mock_llm.return_value = json.dumps({
            'supported': False,
            'confidence': 0.98,
            'reasoning': 'KB clearly states sum is 180°, not 360°'
        })
        
        result = kb_service._verify_source_alignment(question)
        
        assert result.pass_ is False
    
    @patch.object(KBAlignmentService, '_retrieve_from_kb')
    @patch.object(KBAlignmentService, '_invoke_llm')
    def test_percentage_question_supported(
        self,
        mock_llm,
        mock_retrieve,
        kb_service
    ):
        """Test percentage question with KB support."""
        question = {
            'stem': 'Calculate 15% of 80',
            'options': ['12', '15', '10', '20'],
            'correct_answer': 'A',
            'topic': 'number',
            'grade': 'foundation'
        }
        
        mock_retrieve.return_value = [
            {
                'content': 'To find 15% of 80: (15/100) × 80 = 12',
                'score': 0.88,
                'source': 'percentages.pdf',
                'metadata': {}
            }
        ]
        
        mock_llm.return_value = json.dumps({
            'supported': True,
            'confidence': 0.92,
            'reasoning': 'KB shows calculation resulting in 12'
        })
        
        result = kb_service._verify_source_alignment(question)
        
        assert result.pass_ is True
    
    @patch.object(KBAlignmentService, '_retrieve_from_kb')
    @patch.object(KBAlignmentService, '_invoke_llm')
    def test_insufficient_kb_material(
        self,
        mock_llm,
        mock_retrieve,
        kb_service
    ):
        """Test when KB has insufficient material."""
        question = {
            'stem': 'Solve complex equation',
            'options': ['A', 'B', 'C', 'D'],
            'correct_answer': 'A',
            'topic': 'algebra'
        }
        
        mock_retrieve.return_value = [
            {
                'content': 'Unrelated algebra content',
                'score': 0.55,
                'source': 'other.pdf',
                'metadata': {}
            }
        ]
        
        mock_llm.return_value = json.dumps({
            'supported': False,
            'confidence': 0.3,  # Low confidence
            'reasoning': 'KB material does not address this specific question'
        })
        
        result = kb_service._verify_source_alignment(question)
        
        # Should fail due to low confidence
        assert result.pass_ is False
        assert result.confidence < 0.7
    
    @patch.object(KBAlignmentService, '_retrieve_from_kb')
    def test_no_kb_documents_graceful_degradation(
        self,
        mock_retrieve,
        kb_service
    ):
        """Test graceful handling when KB returns no documents."""
        question = {
            'stem': 'Test question',
            'options': ['A', 'B', 'C', 'D'],
            'correct_answer': 'A',
            'topic': 'test'
        }
        
        mock_retrieve.return_value = []
        
        result = kb_service._verify_source_alignment(question)
        
        # Should pass with 0 confidence (don't block on KB gaps)
        assert result.pass_ is True
        assert result.confidence == 0.0
        assert 'No KB documents' in result.reasoning


class TestSourceAlignmentEdgeCases:
    """Test edge cases in source alignment."""
    
    @patch.object(KBAlignmentService, '_retrieve_from_kb')
    @patch.object(KBAlignmentService, '_invoke_llm')
    def test_multiple_correct_answers_detected(
        self,
        mock_llm,
        mock_retrieve,
        kb_service
    ):
        """Test detection when KB suggests multiple answers could be correct."""
        question = {
            'stem': 'Which is a prime number?',
            'options': ['2', '3', '5', '4'],
            'correct_answer': 'A',
            'topic': 'number'
        }
        
        mock_retrieve.return_value = [
            {
                'content': 'Prime numbers include 2, 3, 5, 7, 11...',
                'score': 0.9,
                'source': 'primes.pdf',
                'metadata': {}
            }
        ]
        
        mock_llm.return_value = json.dumps({
            'supported': True,
            'confidence': 0.85,
            'reasoning': '2 is correct, but note that 3 and 5 are also prime'
        })
        
        result = kb_service._verify_source_alignment(question)
        
        # Should still pass as answer is supported
        assert result.pass_ is True
    
    @patch.object(KBAlignmentService, '_retrieve_from_kb')
    @patch.object(KBAlignmentService, '_invoke_llm')
    def test_answer_format_mismatch(
        self,
        mock_llm,
        mock_retrieve,
        kb_service
    ):
        """Test when answer format differs from KB but is equivalent."""
        question = {
            'stem': 'Simplify √50',
            'options': ['5√2', '√50', '7.07', '25'],
            'correct_answer': 'A',
            'topic': 'number'
        }
        
        mock_retrieve.return_value = [
            {
                'content': 'Simplifying √50: √(25×2) = 5√2',
                'score': 0.92,
                'source': 'surds.pdf',
                'metadata': {}
            }
        ]
        
        mock_llm.return_value = json.dumps({
            'supported': True,
            'confidence': 0.95,
            'reasoning': 'KB confirms 5√2 is the simplified form'
        })
        
        result = kb_service._verify_source_alignment(question)
        
        assert result.pass_ is True
    
    @patch.object(KBAlignmentService, '_retrieve_from_kb')
    @patch.object(KBAlignmentService, '_invoke_llm')
    def test_kb_retrieval_error_handling(
        self,
        mock_llm,
        mock_retrieve,
        kb_service
    ):
        """Test error handling when KB retrieval fails."""
        question = {
            'stem': 'Test',
            'options': ['A', 'B', 'C', 'D'],
            'correct_answer': 'A',
            'topic': 'test'
        }
        
        mock_retrieve.side_effect = Exception("KB service unavailable")
        
        result = kb_service._verify_source_alignment(question)
        
        # Should gracefully degrade
        assert result.pass_ is True
        assert result.confidence == 0.0
        assert 'error' in result.reasoning.lower()
    
    @patch.object(KBAlignmentService, '_retrieve_from_kb')
    @patch.object(KBAlignmentService, '_invoke_llm')
    def test_llm_parsing_error_handling(
        self,
        mock_llm,
        mock_retrieve,
        kb_service
    ):
        """Test error handling when LLM returns invalid JSON."""
        question = {
            'stem': 'Test',
            'options': ['A', 'B', 'C', 'D'],
            'correct_answer': 'A',
            'topic': 'test'
        }
        
        mock_retrieve.return_value = [
            {'content': 'test', 'score': 0.8, 'source': 'test.pdf', 'metadata': {}}
        ]
        mock_llm.return_value = "This is not JSON"
        
        result = kb_service._verify_source_alignment(question)
        
        # Should gracefully degrade
        assert result.pass_ is True
        assert result.confidence == 0.0


class TestSourceAlignmentPromptConstruction:
    """Test prompt construction for source alignment."""
    
    @patch.object(KBAlignmentService, '_retrieve_from_kb')
    @patch.object(KBAlignmentService, '_invoke_llm')
    def test_prompt_includes_all_required_info(
        self,
        mock_llm,
        mock_retrieve,
        kb_service
    ):
        """Test that prompt includes all necessary information."""
        question = {
            'stem': 'Solve x + 5 = 10',
            'options': ['x = 5', 'x = 15', 'x = 10', 'x = 0'],
            'correct_answer': 'A',
            'topic': 'algebra',
            'grade': 'foundation'
        }
        
        mock_retrieve.return_value = [
            {'content': 'test content', 'score': 0.8, 'source': 'test.pdf', 'metadata': {}}
        ]
        mock_llm.return_value = json.dumps({
            'supported': True,
            'confidence': 0.9,
            'reasoning': 'test'
        })
        
        kb_service._verify_source_alignment(question)
        
        # Check that LLM was called
        assert mock_llm.called
        prompt = mock_llm.call_args[0][0]
        
        # Verify prompt contains key elements
        assert 'Solve x + 5 = 10' in prompt
        assert 'A) x = 5' in prompt
        assert 'Retrieved educational material' in prompt
        assert 'supported' in prompt.lower()
