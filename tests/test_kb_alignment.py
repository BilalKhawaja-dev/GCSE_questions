"""
Tests for KB Alignment Service.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from src.services.kb_alignment_service import (
    KBAlignmentService,
    SourceCheck,
    SyllabusCheck,
    AlignmentResult
)


@pytest.fixture
def kb_service():
    """Create KB alignment service for testing."""
    return KBAlignmentService(
        knowledge_base_id='test-kb-id',
        region='eu-west-2',
        source_confidence_threshold=0.7,
        syllabus_confidence_threshold=0.7
    )


@pytest.fixture
def sample_question():
    """Sample question for testing."""
    return {
        'stem': 'Solve 2x + 5 = 13',
        'options': ['x = 4', 'x = 9', 'x = 3', 'x = 8'],
        'correct_answer': 'A',
        'topic': 'algebra',
        'grade': 'foundation',
        'paper_type': 'P1'
    }


@pytest.fixture
def mock_kb_docs():
    """Mock KB retrieval results."""
    return [
        {
            'content': 'Linear equations: To solve 2x + 5 = 13, subtract 5 from both sides to get 2x = 8, then divide by 2 to get x = 4.',
            'score': 0.85,
            'source': 'edexcel-algebra-guide.pdf',
            'metadata': {}
        },
        {
            'content': 'Example: Solve 3x + 7 = 22. Answer: x = 5',
            'score': 0.72,
            'source': 'edexcel-past-paper-2023.pdf',
            'metadata': {}
        }
    ]


class TestKBAlignmentService:
    """Test KB alignment service initialization and basic functionality."""
    
    def test_initialization(self, kb_service):
        """Test service initializes correctly."""
        assert kb_service.knowledge_base_id == 'test-kb-id'
        assert kb_service.region == 'eu-west-2'
        assert kb_service.source_threshold == 0.7
        assert kb_service.syllabus_threshold == 0.7
        assert kb_service.model_id == "anthropic.claude-3-5-sonnet-20241022-v2:0"
    
    def test_custom_thresholds(self):
        """Test custom confidence thresholds."""
        service = KBAlignmentService(
            knowledge_base_id='test-kb',
            source_confidence_threshold=0.8,
            syllabus_confidence_threshold=0.6
        )
        assert service.source_threshold == 0.8
        assert service.syllabus_threshold == 0.6


class TestSourceAlignment:
    """Test source alignment verification."""
    
    @patch.object(KBAlignmentService, '_retrieve_from_kb')
    @patch.object(KBAlignmentService, '_invoke_llm')
    def test_source_alignment_pass(
        self,
        mock_llm,
        mock_retrieve,
        kb_service,
        sample_question,
        mock_kb_docs
    ):
        """Test source alignment passes when answer is supported."""
        mock_retrieve.return_value = mock_kb_docs
        mock_llm.return_value = json.dumps({
            'supported': True,
            'confidence': 0.9,
            'reasoning': 'The retrieved material confirms x = 4 is correct'
        })
        
        result = kb_service._verify_source_alignment(sample_question)
        
        assert result.pass_ is True
        assert result.confidence == 0.9
        assert 'confirms' in result.reasoning
        assert len(result.retrieved_docs) == 2
    
    @patch.object(KBAlignmentService, '_retrieve_from_kb')
    @patch.object(KBAlignmentService, '_invoke_llm')
    def test_source_alignment_fail_unsupported(
        self,
        mock_llm,
        mock_retrieve,
        kb_service,
        sample_question,
        mock_kb_docs
    ):
        """Test source alignment fails when answer is not supported."""
        mock_retrieve.return_value = mock_kb_docs
        mock_llm.return_value = json.dumps({
            'supported': False,
            'confidence': 0.8,
            'reasoning': 'The material suggests a different answer'
        })
        
        result = kb_service._verify_source_alignment(sample_question)
        
        assert result.pass_ is False
        assert result.confidence == 0.8
    
    @patch.object(KBAlignmentService, '_retrieve_from_kb')
    @patch.object(KBAlignmentService, '_invoke_llm')
    def test_source_alignment_fail_low_confidence(
        self,
        mock_llm,
        mock_retrieve,
        kb_service,
        sample_question,
        mock_kb_docs
    ):
        """Test source alignment fails when confidence is too low."""
        mock_retrieve.return_value = mock_kb_docs
        mock_llm.return_value = json.dumps({
            'supported': True,
            'confidence': 0.5,  # Below threshold
            'reasoning': 'Uncertain if material supports this'
        })
        
        result = kb_service._verify_source_alignment(sample_question)
        
        assert result.pass_ is False
        assert result.confidence == 0.5
    
    @patch.object(KBAlignmentService, '_retrieve_from_kb')
    def test_source_alignment_no_docs(
        self,
        mock_retrieve,
        kb_service,
        sample_question
    ):
        """Test graceful handling when no KB docs retrieved."""
        mock_retrieve.return_value = []
        
        result = kb_service._verify_source_alignment(sample_question)
        
        # Should pass with 0 confidence (graceful degradation)
        assert result.pass_ is True
        assert result.confidence == 0.0
        assert 'No KB documents' in result.reasoning
    
    @patch.object(KBAlignmentService, '_retrieve_from_kb')
    @patch.object(KBAlignmentService, '_invoke_llm')
    def test_source_alignment_error_handling(
        self,
        mock_llm,
        mock_retrieve,
        kb_service,
        sample_question
    ):
        """Test error handling in source alignment."""
        mock_retrieve.return_value = [{'content': 'test', 'score': 0.8, 'source': 'test.pdf', 'metadata': {}}]
        mock_llm.side_effect = Exception("LLM error")
        
        result = kb_service._verify_source_alignment(sample_question)
        
        # Should pass with 0 confidence (graceful degradation)
        assert result.pass_ is True
        assert result.confidence == 0.0
        assert 'error' in result.reasoning.lower()


class TestSyllabusCompliance:
    """Test syllabus compliance verification."""
    
    @patch.object(KBAlignmentService, '_retrieve_from_kb')
    @patch.object(KBAlignmentService, '_invoke_llm')
    def test_syllabus_compliance_pass(
        self,
        mock_llm,
        mock_retrieve,
        kb_service,
        sample_question
    ):
        """Test syllabus compliance passes when in scope."""
        mock_retrieve.return_value = [
            {
                'content': 'Edexcel 1MA1 Foundation Tier: Algebra includes solving linear equations',
                'score': 0.9,
                'source': 'edexcel-spec.pdf',
                'metadata': {}
            }
        ]
        mock_llm.return_value = json.dumps({
            'in_scope': True,
            'confidence': 0.95,
            'reasoning': 'Linear equations are explicitly in Foundation algebra syllabus'
        })
        
        result = kb_service._verify_syllabus_compliance(sample_question)
        
        assert result.pass_ is True
        assert result.confidence == 0.95
        assert 'syllabus' in result.reasoning.lower()
    
    @patch.object(KBAlignmentService, '_retrieve_from_kb')
    @patch.object(KBAlignmentService, '_invoke_llm')
    def test_syllabus_compliance_fail_out_of_scope(
        self,
        mock_llm,
        mock_retrieve,
        kb_service,
        sample_question
    ):
        """Test syllabus compliance fails when out of scope."""
        mock_retrieve.return_value = [
            {
                'content': 'Foundation tier does not include complex numbers',
                'score': 0.8,
                'source': 'edexcel-spec.pdf',
                'metadata': {}
            }
        ]
        mock_llm.return_value = json.dumps({
            'in_scope': False,
            'confidence': 0.9,
            'reasoning': 'This topic is not in Foundation tier syllabus'
        })
        
        result = kb_service._verify_syllabus_compliance(sample_question)
        
        assert result.pass_ is False
        assert result.confidence == 0.9
    
    @patch.object(KBAlignmentService, '_retrieve_from_kb')
    def test_syllabus_compliance_no_specs(
        self,
        mock_retrieve,
        kb_service,
        sample_question
    ):
        """Test graceful handling when no specification docs retrieved."""
        mock_retrieve.return_value = []
        
        result = kb_service._verify_syllabus_compliance(sample_question)
        
        # Should pass with 0 confidence (graceful degradation)
        assert result.pass_ is True
        assert result.confidence == 0.0
        assert 'No specification' in result.reasoning


class TestOverallAlignment:
    """Test overall alignment verification."""
    
    @patch.object(KBAlignmentService, '_verify_source_alignment')
    @patch.object(KBAlignmentService, '_verify_syllabus_compliance')
    def test_verify_alignment_both_pass(
        self,
        mock_syllabus,
        mock_source,
        kb_service,
        sample_question
    ):
        """Test overall alignment when both checks pass."""
        mock_source.return_value = SourceCheck(
            pass_=True,
            confidence=0.9,
            reasoning='Source supported',
            retrieved_docs=[]
        )
        mock_syllabus.return_value = SyllabusCheck(
            pass_=True,
            confidence=0.85,
            reasoning='In syllabus',
            retrieved_docs=[]
        )
        
        result = kb_service.verify_alignment(sample_question)
        
        assert result.pass_ is True
        assert result.overall_confidence == 0.875  # Average of 0.9 and 0.85
        assert result.source_alignment.pass_ is True
        assert result.syllabus_compliance.pass_ is True
    
    @patch.object(KBAlignmentService, '_verify_source_alignment')
    @patch.object(KBAlignmentService, '_verify_syllabus_compliance')
    def test_verify_alignment_source_fails(
        self,
        mock_syllabus,
        mock_source,
        kb_service,
        sample_question
    ):
        """Test overall alignment when source check fails."""
        mock_source.return_value = SourceCheck(
            pass_=False,
            confidence=0.5,
            reasoning='Not supported',
            retrieved_docs=[]
        )
        mock_syllabus.return_value = SyllabusCheck(
            pass_=True,
            confidence=0.9,
            reasoning='In syllabus',
            retrieved_docs=[]
        )
        
        result = kb_service.verify_alignment(sample_question)
        
        assert result.pass_ is False  # Fails if either check fails
        assert result.source_alignment.pass_ is False
    
    @patch.object(KBAlignmentService, '_verify_source_alignment')
    @patch.object(KBAlignmentService, '_verify_syllabus_compliance')
    def test_verify_alignment_syllabus_fails(
        self,
        mock_syllabus,
        mock_source,
        kb_service,
        sample_question
    ):
        """Test overall alignment when syllabus check fails."""
        mock_source.return_value = SourceCheck(
            pass_=True,
            confidence=0.9,
            reasoning='Source supported',
            retrieved_docs=[]
        )
        mock_syllabus.return_value = SyllabusCheck(
            pass_=False,
            confidence=0.6,
            reasoning='Out of scope',
            retrieved_docs=[]
        )
        
        result = kb_service.verify_alignment(sample_question)
        
        assert result.pass_ is False
        assert result.syllabus_compliance.pass_ is False
    
    @patch.object(KBAlignmentService, '_verify_source_alignment')
    @patch.object(KBAlignmentService, '_verify_syllabus_compliance')
    def test_verify_alignment_error_handling(
        self,
        mock_syllabus,
        mock_source,
        kb_service,
        sample_question
    ):
        """Test error handling in overall verification."""
        mock_source.side_effect = Exception("KB error")
        
        result = kb_service.verify_alignment(sample_question)
        
        # Should pass with 0 confidence (graceful degradation)
        assert result.pass_ is True
        assert result.overall_confidence == 0.0


class TestKBRetrieval:
    """Test KB retrieval functionality."""
    
    def test_retrieve_from_kb_success(self, kb_service):
        """Test successful KB retrieval."""
        # Mock the bedrock_agent_client directly
        mock_client = Mock()
        kb_service.bedrock_agent_client = mock_client
        
        mock_client.retrieve.return_value = {
            'retrievalResults': [
                {
                    'content': {'text': 'Test content 1 with enough characters to pass the 50 character minimum filter'},
                    'score': 0.85,
                    'metadata': {'x-amz-bedrock-kb-source-uri': 'test1.pdf'}
                },
                {
                    'content': {'text': 'Test content 2 also with enough characters to pass the minimum filter'},
                    'score': 0.72,
                    'metadata': {'x-amz-bedrock-kb-source-uri': 'test2.pdf'}
                }
            ]
        }
        
        results = kb_service._retrieve_from_kb('test query', max_results=5)
        
        assert len(results) == 2
        assert 'Test content 1' in results[0]['content']
        assert results[0]['score'] == 0.85
        assert 'Test content 2' in results[1]['content']
    
    def test_retrieve_from_kb_filters_low_scores(self, kb_service):
        """Test KB retrieval filters out low-confidence results."""
        # Mock the bedrock_agent_client directly
        mock_client = Mock()
        kb_service.bedrock_agent_client = mock_client
        
        mock_client.retrieve.return_value = {
            'retrievalResults': [
                {
                    'content': {'text': 'Good content with enough characters to pass the minimum length filter'},
                    'score': 0.85,
                    'metadata': {}
                },
                {
                    'content': {'text': 'Low score content also with enough characters to pass minimum length'},
                    'score': 0.3,  # Below 0.5 threshold
                    'metadata': {}
                }
            ]
        }
        
        results = kb_service._retrieve_from_kb('test query')
        
        assert len(results) == 1
        assert 'Good content' in results[0]['content']
    
    def test_retrieve_from_kb_error_handling(self, kb_service):
        """Test KB retrieval error handling."""
        # Mock the bedrock_agent_client directly
        mock_client = Mock()
        kb_service.bedrock_agent_client = mock_client
        
        mock_client.retrieve.side_effect = Exception("KB error")
        
        results = kb_service._retrieve_from_kb('test query')
        
        assert results == []  # Returns empty list on error
        assert results == []  # Returns empty list on error


class TestHelperMethods:
    """Test helper methods."""
    
    def test_format_docs(self, kb_service):
        """Test document formatting."""
        docs = [
            {
                'content': 'Content 1',
                'score': 0.9,
                'source': 'doc1.pdf'
            },
            {
                'content': 'Content 2',
                'score': 0.75,
                'source': 'doc2.pdf'
            }
        ]
        
        formatted = kb_service._format_docs(docs)
        
        assert '[Document 1 - Relevance: 90%]' in formatted
        assert 'Content 1' in formatted
        assert '[Document 2 - Relevance: 75%]' in formatted
        assert 'Content 2' in formatted
    
    def test_format_docs_empty(self, kb_service):
        """Test formatting empty document list."""
        formatted = kb_service._format_docs([])
        assert formatted == "No documents retrieved."
    
    def test_parse_json_response_clean(self, kb_service):
        """Test parsing clean JSON response."""
        response = '{"supported": true, "confidence": 0.9}'
        result = kb_service._parse_json_response(response)
        
        assert result['supported'] is True
        assert result['confidence'] == 0.9
    
    def test_parse_json_response_with_text(self, kb_service):
        """Test parsing JSON with surrounding text."""
        response = 'Here is the result: {"supported": true, "confidence": 0.9} as requested.'
        result = kb_service._parse_json_response(response)
        
        assert result['supported'] is True
        assert result['confidence'] == 0.9
    
    def test_parse_json_response_invalid(self, kb_service):
        """Test parsing invalid JSON raises error."""
        response = 'This is not JSON'
        
        with pytest.raises(ValueError, match='Invalid JSON response'):
            kb_service._parse_json_response(response)
