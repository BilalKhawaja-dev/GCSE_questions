"""
Tests for syllabus compliance verification.
Validates questions are within Edexcel 1MA1 scope.
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
        syllabus_confidence_threshold=0.7
    )


class TestSyllabusComplianceScenarios:
    """Test various syllabus compliance scenarios."""
    
    @patch.object(KBAlignmentService, '_retrieve_from_kb')
    @patch.object(KBAlignmentService, '_invoke_llm')
    def test_foundation_algebra_in_scope(
        self,
        mock_llm,
        mock_retrieve,
        kb_service
    ):
        """Test Foundation algebra question is in scope."""
        question = {
            'stem': 'Solve 2x + 3 = 11',
            'options': ['x = 4', 'x = 7', 'x = 5', 'x = 8'],
            'correct_answer': 'A',
            'topic': 'algebra',
            'grade': 'foundation',
            'paper_type': 'P1'
        }
        
        mock_retrieve.return_value = [
            {
                'content': 'Edexcel 1MA1 Foundation: Algebra includes solving linear equations of the form ax + b = c',
                'score': 0.95,
                'source': 'edexcel-spec-2024.pdf',
                'metadata': {}
            }
        ]
        
        mock_llm.return_value = json.dumps({
            'in_scope': True,
            'confidence': 0.95,
            'reasoning': 'Linear equations explicitly listed in Foundation algebra syllabus'
        })
        
        result = kb_service._verify_syllabus_compliance(question)
        
        assert result.pass_ is True
        assert result.confidence >= 0.7
    
    @patch.object(KBAlignmentService, '_retrieve_from_kb')
    @patch.object(KBAlignmentService, '_invoke_llm')
    def test_higher_calculus_out_of_scope(
        self,
        mock_llm,
        mock_retrieve,
        kb_service
    ):
        """Test calculus question is out of scope for GCSE."""
        question = {
            'stem': 'Find the derivative of x²',
            'options': ['2x', 'x', '2', 'x²'],
            'correct_answer': 'A',
            'topic': 'calculus',
            'grade': 'higher',
            'paper_type': 'P3'
        }
        
        mock_retrieve.return_value = [
            {
                'content': 'Edexcel 1MA1 does not include calculus or differentiation',
                'score': 0.9,
                'source': 'edexcel-spec-2024.pdf',
                'metadata': {}
            }
        ]
        
        mock_llm.return_value = json.dumps({
            'in_scope': False,
            'confidence': 0.98,
            'reasoning': 'Calculus is not part of GCSE Mathematics syllabus'
        })
        
        result = kb_service._verify_syllabus_compliance(question)
        
        assert result.pass_ is False
    
    @patch.object(KBAlignmentService, '_retrieve_from_kb')
    @patch.object(KBAlignmentService, '_invoke_llm')
    def test_paper_type_constraint_violation(
        self,
        mock_llm,
        mock_retrieve,
        kb_service
    ):
        """Test question violates paper type constraints."""
        question = {
            'stem': 'Use your calculator to find sin(45°) to 3 decimal places',
            'options': ['0.707', '0.500', '0.866', '1.000'],
            'correct_answer': 'A',
            'topic': 'trigonometry',
            'grade': 'foundation',
            'paper_type': 'P1'  # Non-calculator paper
        }
        
        mock_retrieve.return_value = [
            {
                'content': 'Paper 1 is non-calculator. Questions must not require calculator use.',
                'score': 0.92,
                'source': 'edexcel-spec-2024.pdf',
                'metadata': {}
            }
        ]
        
        mock_llm.return_value = json.dumps({
            'in_scope': False,
            'confidence': 0.95,
            'reasoning': 'Question requires calculator but P1 is non-calculator paper'
        })
        
        result = kb_service._verify_syllabus_compliance(question)
        
        assert result.pass_ is False
    
    @patch.object(KBAlignmentService, '_retrieve_from_kb')
    @patch.object(KBAlignmentService, '_invoke_llm')
    def test_foundation_vs_higher_difficulty(
        self,
        mock_llm,
        mock_retrieve,
        kb_service
    ):
        """Test question difficulty appropriate for grade."""
        question = {
            'stem': 'Solve the simultaneous equations: 3x + 2y = 12, 5x - y = 11',
            'options': ['x=2, y=3', 'x=3, y=2', 'x=1, y=4', 'x=4, y=1'],
            'correct_answer': 'A',
            'topic': 'algebra',
            'grade': 'foundation',
            'paper_type': 'P2'
        }
        
        mock_retrieve.return_value = [
            {
                'content': 'Foundation tier: Simple simultaneous equations with integer solutions',
                'score': 0.88,
                'source': 'edexcel-spec-2024.pdf',
                'metadata': {}
            }
        ]
        
        mock_llm.return_value = json.dumps({
            'in_scope': True,
            'confidence': 0.85,
            'reasoning': 'Simultaneous equations with integer solutions are in Foundation syllabus'
        })
        
        result = kb_service._verify_syllabus_compliance(question)
        
        assert result.pass_ is True
    
    @patch.object(KBAlignmentService, '_retrieve_from_kb')
    def test_no_specification_docs_graceful_degradation(
        self,
        mock_retrieve,
        kb_service
    ):
        """Test graceful handling when no specification docs available."""
        question = {
            'stem': 'Test question',
            'options': ['A', 'B', 'C', 'D'],
            'correct_answer': 'A',
            'topic': 'test',
            'grade': 'foundation',
            'paper_type': 'P1'
        }
        
        mock_retrieve.return_value = []
        
        result = kb_service._verify_syllabus_compliance(question)
        
        # Should pass with 0 confidence (don't block on missing specs)
        assert result.pass_ is True
        assert result.confidence == 0.0
        assert 'No specification' in result.reasoning


class TestSyllabusComplianceEdgeCases:
    """Test edge cases in syllabus compliance."""
    
    @patch.object(KBAlignmentService, '_retrieve_from_kb')
    @patch.object(KBAlignmentService, '_invoke_llm')
    def test_borderline_difficulty_uncertain(
        self,
        mock_llm,
        mock_retrieve,
        kb_service
    ):
        """Test borderline difficulty question with uncertain compliance."""
        question = {
            'stem': 'Complex algebraic manipulation',
            'options': ['A', 'B', 'C', 'D'],
            'correct_answer': 'A',
            'topic': 'algebra',
            'grade': 'foundation',
            'paper_type': 'P2'
        }
        
        mock_retrieve.return_value = [
            {
                'content': 'Foundation algebra includes basic manipulation',
                'score': 0.7,
                'source': 'spec.pdf',
                'metadata': {}
            }
        ]
        
        mock_llm.return_value = json.dumps({
            'in_scope': True,
            'confidence': 0.6,  # Below threshold
            'reasoning': 'Uncertain if complexity is appropriate for Foundation'
        })
        
        result = kb_service._verify_syllabus_compliance(question)
        
        # Should fail due to low confidence
        assert result.pass_ is False
        assert result.confidence < 0.7
    
    @patch.object(KBAlignmentService, '_retrieve_from_kb')
    @patch.object(KBAlignmentService, '_invoke_llm')
    def test_topic_in_both_tiers(
        self,
        mock_llm,
        mock_retrieve,
        kb_service
    ):
        """Test topic that appears in both Foundation and Higher."""
        question = {
            'stem': 'Calculate the area of a circle with radius 5cm',
            'options': ['78.5 cm²', '31.4 cm²', '25 cm²', '15.7 cm²'],
            'correct_answer': 'A',
            'topic': 'geometry',
            'grade': 'foundation',
            'paper_type': 'P2'
        }
        
        mock_retrieve.return_value = [
            {
                'content': 'Circle area calculations appear in both Foundation and Higher tiers',
                'score': 0.9,
                'source': 'spec.pdf',
                'metadata': {}
            }
        ]
        
        mock_llm.return_value = json.dumps({
            'in_scope': True,
            'confidence': 0.9,
            'reasoning': 'Circle area is in Foundation syllabus'
        })
        
        result = kb_service._verify_syllabus_compliance(question)
        
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
            'topic': 'test',
            'grade': 'foundation',
            'paper_type': 'P1'
        }
        
        mock_retrieve.side_effect = Exception("KB unavailable")
        
        result = kb_service._verify_syllabus_compliance(question)
        
        # Should gracefully degrade
        assert result.pass_ is True
        assert result.confidence == 0.0
        assert 'error' in result.reasoning.lower()
    
    @patch.object(KBAlignmentService, '_retrieve_from_kb')
    @patch.object(KBAlignmentService, '_invoke_llm')
    def test_llm_error_handling(
        self,
        mock_llm,
        mock_retrieve,
        kb_service
    ):
        """Test error handling when LLM invocation fails."""
        question = {
            'stem': 'Test',
            'options': ['A', 'B', 'C', 'D'],
            'correct_answer': 'A',
            'topic': 'test',
            'grade': 'foundation',
            'paper_type': 'P1'
        }
        
        mock_retrieve.return_value = [
            {'content': 'test', 'score': 0.8, 'source': 'test.pdf', 'metadata': {}}
        ]
        mock_llm.side_effect = Exception("LLM error")
        
        result = kb_service._verify_syllabus_compliance(question)
        
        # Should gracefully degrade
        assert result.pass_ is True
        assert result.confidence == 0.0


class TestSyllabusCompliancePromptConstruction:
    """Test prompt construction for syllabus compliance."""
    
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
            'grade': 'foundation',
            'paper_type': 'P1'
        }
        
        mock_retrieve.return_value = [
            {'content': 'test spec', 'score': 0.9, 'source': 'spec.pdf', 'metadata': {}}
        ]
        mock_llm.return_value = json.dumps({
            'in_scope': True,
            'confidence': 0.9,
            'reasoning': 'test'
        })
        
        kb_service._verify_syllabus_compliance(question)
        
        # Check that LLM was called
        assert mock_llm.called
        prompt = mock_llm.call_args[0][0]
        
        # Verify prompt contains key elements
        assert 'algebra' in prompt
        assert 'foundation' in prompt
        assert 'P1' in prompt
        assert 'Edexcel 1MA1' in prompt
        assert 'in_scope' in prompt.lower()
        assert 'non-calculator' in prompt.lower()  # P1 constraint


class TestSyllabusComplianceRealWorldScenarios:
    """Test real-world syllabus compliance scenarios."""
    
    @patch.object(KBAlignmentService, '_retrieve_from_kb')
    @patch.object(KBAlignmentService, '_invoke_llm')
    def test_pythagoras_foundation_appropriate(
        self,
        mock_llm,
        mock_retrieve,
        kb_service
    ):
        """Test Pythagoras question appropriate for Foundation."""
        question = {
            'stem': 'A right-angled triangle has sides 3cm and 4cm. Find the hypotenuse.',
            'options': ['5cm', '7cm', '6cm', '8cm'],
            'correct_answer': 'A',
            'topic': 'geometry',
            'grade': 'foundation',
            'paper_type': 'P2'
        }
        
        mock_retrieve.return_value = [
            {
                'content': 'Foundation: Pythagoras theorem with integer solutions',
                'score': 0.92,
                'source': 'spec.pdf',
                'metadata': {}
            }
        ]
        
        mock_llm.return_value = json.dumps({
            'in_scope': True,
            'confidence': 0.9,
            'reasoning': 'Pythagoras with integer solutions is Foundation appropriate'
        })
        
        result = kb_service._verify_syllabus_compliance(question)
        
        assert result.pass_ is True
    
    @patch.object(KBAlignmentService, '_retrieve_from_kb')
    @patch.object(KBAlignmentService, '_invoke_llm')
    def test_complex_trig_higher_only(
        self,
        mock_llm,
        mock_retrieve,
        kb_service
    ):
        """Test complex trigonometry is Higher tier only."""
        question = {
            'stem': 'Solve sin(2x) = 0.5 for 0° ≤ x ≤ 180°',
            'options': ['15°, 75°', '30°, 150°', '45°, 135°', '60°, 120°'],
            'correct_answer': 'A',
            'topic': 'trigonometry',
            'grade': 'foundation',
            'paper_type': 'P3'
        }
        
        mock_retrieve.return_value = [
            {
                'content': 'Foundation: Basic trig ratios only. Higher: Solving trig equations',
                'score': 0.9,
                'source': 'spec.pdf',
                'metadata': {}
            }
        ]
        
        mock_llm.return_value = json.dumps({
            'in_scope': False,
            'confidence': 0.95,
            'reasoning': 'Solving trig equations is Higher tier only'
        })
        
        result = kb_service._verify_syllabus_compliance(question)
        
        assert result.pass_ is False
