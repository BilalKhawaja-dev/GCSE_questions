"""
Unit tests for DedupeService

Tests embedding generation, similarity detection, and duplicate checking.
"""

import json
import pytest
from unittest.mock import Mock, MagicMock, patch
import numpy as np

from src.services.dedupe_service import DedupeService, DedupeResult
from src.services.sympy_verifier_service import MCQQuestion


@pytest.fixture
def mock_bedrock_client():
    """Mock Bedrock client"""
    client = Mock()
    return client


@pytest.fixture
def mock_dynamodb_client():
    """Mock DynamoDB client"""
    client = Mock()
    table = Mock()
    client.Table.return_value = table
    return client


@pytest.fixture
def dedupe_service(mock_bedrock_client, mock_dynamodb_client):
    """Create DedupeService instance"""
    return DedupeService(
        bedrock_client=mock_bedrock_client,
        dynamodb_client=mock_dynamodb_client,
        table_name="test_question_bank",
        similarity_threshold=0.85
    )


@pytest.fixture
def sample_question():
    """Sample question for testing"""
    return MCQQuestion(
        stem="Solve 2x + 5 = 13",
        options=["x = 4", "x = 9", "x = 3", "x = 8"],
        correct_answer="A",
        rationale="Subtract 5 from both sides to get 2x = 8, then divide by 2",
        topic="algebra",
        grade="foundation",
        paper_type="P1",
        difficulty=5
    )


class TestEmbeddingGeneration:
    """Test embedding generation"""
    
    def test_generate_embedding_success(self, dedupe_service, sample_question, mock_bedrock_client):
        """Test successful embedding generation"""
        # Mock Bedrock response
        mock_embedding = [0.1] * 1024
        mock_response = {
            'body': Mock(read=lambda: json.dumps({'embedding': mock_embedding}).encode())
        }
        mock_bedrock_client.invoke_model.return_value = mock_response
        
        # Generate embedding
        embedding = dedupe_service.generate_embedding(sample_question)
        
        # Verify
        assert len(embedding) == 1024
        assert embedding == mock_embedding
        
        # Verify Bedrock was called correctly
        mock_bedrock_client.invoke_model.assert_called_once()
        call_args = mock_bedrock_client.invoke_model.call_args
        assert call_args[1]['modelId'] == "amazon.titan-embed-text-v2:0"
        
        # Verify text includes stem and options
        body = json.loads(call_args[1]['body'])
        assert "Solve 2x + 5 = 13" in body['inputText']
        assert "x = 4" in body['inputText']
    
    def test_generate_embedding_combines_stem_and_options(
        self, dedupe_service, mock_bedrock_client
    ):
        """Test that embedding combines stem and all options"""
        question = MCQQuestion(
            stem="What is 2 + 2?",
            options=["3", "4", "5", "6"],
            correct_answer="B",
            rationale="Basic addition",
            topic="arithmetic",
            grade="foundation",
            paper_type="P1",
            difficulty=1
        )
        
        mock_embedding = [0.2] * 1024
        mock_response = {
            'body': Mock(read=lambda: json.dumps({'embedding': mock_embedding}).encode())
        }
        mock_bedrock_client.invoke_model.return_value = mock_response
        
        embedding = dedupe_service.generate_embedding(question)
        
        # Verify text includes all parts
        call_args = mock_bedrock_client.invoke_model.call_args
        body = json.loads(call_args[1]['body'])
        text = body['inputText']
        
        assert "What is 2 + 2?" in text
        assert "3" in text
        assert "4" in text
        assert "5" in text
        assert "6" in text
    
    def test_generate_embedding_truncates_long_text(
        self, dedupe_service, mock_bedrock_client
    ):
        """Test that very long text is truncated"""
        long_stem = "A" * 10000  # Very long stem
        question = MCQQuestion(
            stem=long_stem,
            options=["A", "B", "C", "D"],
            correct_answer="A",
            rationale="Test",
            topic="test",
            grade="foundation",
            paper_type="P1",
            difficulty=5
        )
        
        mock_embedding = [0.3] * 1024
        mock_response = {
            'body': Mock(read=lambda: json.dumps({'embedding': mock_embedding}).encode())
        }
        mock_bedrock_client.invoke_model.return_value = mock_response
        
        embedding = dedupe_service.generate_embedding(question)
        
        # Verify text was truncated
        call_args = mock_bedrock_client.invoke_model.call_args
        body = json.loads(call_args[1]['body'])
        assert len(body['inputText']) <= 8000
    
    def test_generate_embedding_bedrock_error(
        self, dedupe_service, sample_question, mock_bedrock_client
    ):
        """Test handling of Bedrock errors"""
        mock_bedrock_client.invoke_model.side_effect = Exception("Bedrock error")
        
        with pytest.raises(Exception):
            dedupe_service.generate_embedding(sample_question)


class TestCosineSimilarity:
    """Test cosine similarity calculation"""
    
    def test_identical_embeddings(self, dedupe_service):
        """Test similarity of identical embeddings is 1.0"""
        embedding = [0.1, 0.2, 0.3, 0.4]
        similarity = dedupe_service._cosine_similarity(embedding, embedding)
        assert abs(similarity - 1.0) < 0.001
    
    def test_orthogonal_embeddings(self, dedupe_service):
        """Test similarity of orthogonal embeddings is 0.0"""
        embedding_a = [1.0, 0.0, 0.0, 0.0]
        embedding_b = [0.0, 1.0, 0.0, 0.0]
        similarity = dedupe_service._cosine_similarity(embedding_a, embedding_b)
        assert abs(similarity - 0.0) < 0.001
    
    def test_opposite_embeddings(self, dedupe_service):
        """Test similarity of opposite embeddings is 0.0 (clamped)"""
        embedding_a = [1.0, 0.0, 0.0, 0.0]
        embedding_b = [-1.0, 0.0, 0.0, 0.0]
        similarity = dedupe_service._cosine_similarity(embedding_a, embedding_b)
        # Cosine similarity of opposite vectors is -1, but we clamp to [0, 1]
        assert similarity >= 0.0
    
    def test_similar_embeddings(self, dedupe_service):
        """Test similarity of similar embeddings"""
        embedding_a = [0.5, 0.5, 0.5, 0.5]
        embedding_b = [0.6, 0.4, 0.5, 0.5]
        similarity = dedupe_service._cosine_similarity(embedding_a, embedding_b)
        assert 0.9 < similarity < 1.0  # Should be high but not perfect
    
    def test_zero_norm_handling(self, dedupe_service):
        """Test handling of zero-norm vectors"""
        embedding_a = [0.0, 0.0, 0.0, 0.0]
        embedding_b = [1.0, 1.0, 1.0, 1.0]
        similarity = dedupe_service._cosine_similarity(embedding_a, embedding_b)
        assert similarity == 0.0


class TestDuplicateChecking:
    """Test duplicate detection"""
    
    def test_no_duplicates_found(
        self, dedupe_service, sample_question, mock_bedrock_client, mock_dynamodb_client
    ):
        """Test when no duplicates exist"""
        # Mock embedding generation
        new_embedding = [0.1] * 512 + [0.9] * 512  # Different pattern
        mock_response = {
            'body': Mock(read=lambda: json.dumps({'embedding': new_embedding}).encode())
        }
        mock_bedrock_client.invoke_model.return_value = mock_response
        
        # Mock DynamoDB - return different question with very different embedding
        different_embedding = [0.9] * 512 + [0.1] * 512  # Opposite pattern
        mock_table = mock_dynamodb_client.Table.return_value
        mock_table.scan.return_value = {
            'Items': [
                {
                    'question_id': 'existing-123',
                    'stem': 'Different question',
                    'embedding': different_embedding
                }
            ]
        }
        
        # Check for duplicates
        result = dedupe_service.check_duplicate(sample_question)
        
        # Verify
        assert result.pass_ is True
        assert result.max_similarity < 0.85
        assert result.similar_question_id is None
    
    def test_duplicate_found_above_threshold(
        self, dedupe_service, sample_question, mock_bedrock_client, mock_dynamodb_client
    ):
        """Test when duplicate is found above threshold"""
        # Mock embedding generation
        new_embedding = [0.5] * 1024
        mock_response = {
            'body': Mock(read=lambda: json.dumps({'embedding': new_embedding}).encode())
        }
        mock_bedrock_client.invoke_model.return_value = mock_response
        
        # Mock DynamoDB - return very similar question
        similar_embedding = [0.51] * 1024  # Very similar
        mock_table = mock_dynamodb_client.Table.return_value
        mock_table.scan.return_value = {
            'Items': [
                {
                    'question_id': 'duplicate-456',
                    'stem': 'Solve 2x + 5 = 13',  # Same question
                    'embedding': similar_embedding
                }
            ]
        }
        
        # Check for duplicates
        result = dedupe_service.check_duplicate(sample_question)
        
        # Verify
        assert result.pass_ is False
        assert result.max_similarity > 0.85
        assert result.similar_question_id == 'duplicate-456'
        assert 'Solve 2x + 5 = 13' in result.similar_question_stem
    
    def test_multiple_questions_finds_most_similar(
        self, dedupe_service, sample_question, mock_bedrock_client, mock_dynamodb_client
    ):
        """Test that most similar question is identified"""
        # Mock embedding generation
        new_embedding = [0.5] * 1024
        mock_response = {
            'body': Mock(read=lambda: json.dumps({'embedding': new_embedding}).encode())
        }
        mock_bedrock_client.invoke_model.return_value = mock_response
        
        # Mock DynamoDB - return multiple questions with varying similarity
        mock_table = mock_dynamodb_client.Table.return_value
        mock_table.scan.return_value = {
            'Items': [
                {
                    'question_id': 'q1',
                    'stem': 'Different question',
                    'embedding': [0.1] * 512 + [0.9] * 512  # Low similarity
                },
                {
                    'question_id': 'q2',
                    'stem': 'Similar question',
                    'embedding': [0.51] * 1024  # High similarity (very close to 0.5)
                },
                {
                    'question_id': 'q3',
                    'stem': 'Another question',
                    'embedding': [0.3] * 512 + [0.7] * 512  # Medium similarity
                }
            ]
        }
        
        # Check for duplicates
        result = dedupe_service.check_duplicate(sample_question)
        
        # Verify most similar was identified
        assert result.similar_question_id == 'q2'
    
    def test_uses_precomputed_embedding(
        self, dedupe_service, sample_question, mock_bedrock_client, mock_dynamodb_client
    ):
        """Test using pre-computed embedding"""
        precomputed_embedding = [0.7] * 1024
        
        # Mock DynamoDB
        mock_table = mock_dynamodb_client.Table.return_value
        mock_table.scan.return_value = {'Items': []}
        
        # Check with precomputed embedding
        result = dedupe_service.check_duplicate(
            sample_question,
            existing_embedding=precomputed_embedding
        )
        
        # Verify Bedrock was NOT called
        mock_bedrock_client.invoke_model.assert_not_called()
        
        # Verify embedding was used
        assert result.embedding == precomputed_embedding
    
    def test_skips_questions_without_embeddings(
        self, dedupe_service, sample_question, mock_bedrock_client, mock_dynamodb_client
    ):
        """Test that questions without embeddings are skipped"""
        # Mock embedding generation
        new_embedding = [0.5] * 1024
        mock_response = {
            'body': Mock(read=lambda: json.dumps({'embedding': new_embedding}).encode())
        }
        mock_bedrock_client.invoke_model.return_value = mock_response
        
        # Mock DynamoDB - return question without embedding
        mock_table = mock_dynamodb_client.Table.return_value
        mock_table.scan.return_value = {
            'Items': [
                {
                    'question_id': 'no-embedding',
                    'stem': 'Question without embedding'
                    # No 'embedding' field
                }
            ]
        }
        
        # Check for duplicates
        result = dedupe_service.check_duplicate(sample_question)
        
        # Verify - should pass since no valid embeddings to compare
        assert result.pass_ is True
        assert result.max_similarity == 0.0
    
    def test_error_handling_returns_pass(
        self, dedupe_service, sample_question, mock_bedrock_client, mock_dynamodb_client
    ):
        """Test that errors don't fail verification"""
        # Mock error in embedding generation
        mock_bedrock_client.invoke_model.side_effect = Exception("Bedrock error")
        
        # Check for duplicates
        result = dedupe_service.check_duplicate(sample_question)
        
        # Verify - should pass on error (graceful degradation)
        assert result.pass_ is True
        assert result.max_similarity == 0.0
        assert result.embedding is None


class TestBatchOperations:
    """Test batch embedding generation"""
    
    def test_batch_generate_embeddings(
        self, dedupe_service, mock_bedrock_client
    ):
        """Test batch embedding generation"""
        questions = [
            {
                'question_id': f"q{i}",
                'stem': f"Question {i}",
                'options': ["A", "B", "C", "D"],
                'correct_answer': "A",
                'rationale': "Test",
                'topic': "test",
                'grade': "foundation",
                'paper_type': "P1",
                'difficulty': 5
            }
            for i in range(5)
        ]
        
        # Mock Bedrock responses
        def mock_invoke(modelId, body):
            return {
                'body': Mock(read=lambda: json.dumps({'embedding': [0.1] * 1024}).encode())
            }
        
        mock_bedrock_client.invoke_model.side_effect = mock_invoke
        
        # Generate embeddings
        embeddings = dedupe_service.batch_generate_embeddings(questions, batch_size=2)
        
        # Verify
        assert len(embeddings) == 5
        for i in range(5):
            assert f"q{i}" in embeddings
            assert len(embeddings[f"q{i}"]) == 1024
    
    def test_batch_handles_errors(
        self, dedupe_service, mock_bedrock_client
    ):
        """Test batch generation handles individual errors"""
        questions = [
            {
                'question_id': f"q{i}",
                'stem': f"Question {i}",
                'options': ["A", "B", "C", "D"],
                'correct_answer': "A",
                'rationale': "Test",
                'topic': "test",
                'grade': "foundation",
                'paper_type': "P1",
                'difficulty': 5
            }
            for i in range(3)
        ]
        
        # Mock Bedrock - fail on second question
        call_count = [0]
        def mock_invoke(modelId, body):
            call_count[0] += 1
            if call_count[0] == 2:
                raise Exception("Bedrock error")
            return {
                'body': Mock(read=lambda: json.dumps({'embedding': [0.1] * 1024}).encode())
            }
        
        mock_bedrock_client.invoke_model.side_effect = mock_invoke
        
        # Generate embeddings
        embeddings = dedupe_service.batch_generate_embeddings(questions)
        
        # Verify - should have 2 embeddings (skipped the failed one)
        assert len(embeddings) == 2
        assert "q0" in embeddings
        assert "q2" in embeddings
        assert "q1" not in embeddings


class TestStorageOperations:
    """Test embedding storage"""
    
    def test_store_embedding_success(
        self, dedupe_service, mock_dynamodb_client
    ):
        """Test successful embedding storage"""
        embedding = [0.5] * 1024
        mock_table = mock_dynamodb_client.Table.return_value
        
        result = dedupe_service.store_embedding("test-123", embedding)
        
        assert result is True
        mock_table.update_item.assert_called_once()
        
        # Verify update expression
        call_args = mock_table.update_item.call_args
        assert call_args[1]['Key'] == {'question_id': 'test-123'}
        assert call_args[1]['ExpressionAttributeValues'][':emb'] == embedding
    
    def test_store_embedding_error(
        self, dedupe_service, mock_dynamodb_client
    ):
        """Test handling of storage errors"""
        embedding = [0.5] * 1024
        mock_table = mock_dynamodb_client.Table.return_value
        mock_table.update_item.side_effect = Exception("DynamoDB error")
        
        result = dedupe_service.store_embedding("test-123", embedding)
        
        assert result is False


class TestThresholdConfiguration:
    """Test similarity threshold configuration"""
    
    def test_custom_threshold(
        self, mock_bedrock_client, mock_dynamodb_client, sample_question
    ):
        """Test custom similarity threshold"""
        # Create service with lower threshold
        service = DedupeService(
            bedrock_client=mock_bedrock_client,
            dynamodb_client=mock_dynamodb_client,
            similarity_threshold=0.70  # Lower threshold
        )
        
        # Mock embedding generation
        new_embedding = [0.5] * 1024
        mock_response = {
            'body': Mock(read=lambda: json.dumps({'embedding': new_embedding}).encode())
        }
        mock_bedrock_client.invoke_model.return_value = mock_response
        
        # Mock DynamoDB - return moderately similar question
        similar_embedding = [0.55] * 1024  # Similarity ~0.75
        mock_table = mock_dynamodb_client.Table.return_value
        mock_table.scan.return_value = {
            'Items': [
                {
                    'question_id': 'similar-q',
                    'stem': 'Similar question',
                    'embedding': similar_embedding
                }
            ]
        }
        
        # Check for duplicates
        result = service.check_duplicate(sample_question)
        
        # With lower threshold, should detect as duplicate
        assert result.pass_ is False
        assert result.max_similarity > 0.70
