"""
Tests for embedding management and batch operations

Tests batch embedding generation, storage, and retrieval operations.
"""

import pytest
from unittest.mock import Mock, MagicMock
import json

from src.services.dedupe_service import DedupeService
from src.services.sympy_verifier_service import MCQQuestion


@pytest.fixture
def mock_bedrock_client():
    """Mock Bedrock client"""
    return Mock()


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
        table_name="test_question_bank"
    )


class TestBatchEmbeddingGeneration:
    """Test batch embedding generation operations"""
    
    def test_batch_empty_list(self, dedupe_service):
        """Test batch generation with empty list"""
        embeddings = dedupe_service.batch_generate_embeddings([])
        assert embeddings == {}
    
    def test_batch_single_question(self, dedupe_service, mock_bedrock_client):
        """Test batch generation with single question"""
        question = {
            'question_id': "q1",
            'stem': "Test question",
            'options': ["A", "B", "C", "D"],
            'correct_answer': "A",
            'rationale': "Test",
            'topic': "test",
            'grade': "foundation",
            'paper_type': "P1",
            'difficulty': 5
        }
        
        # Mock Bedrock
        mock_embedding = [0.1] * 1024
        mock_response = {
            'body': Mock(read=lambda: json.dumps({'embedding': mock_embedding}).encode())
        }
        mock_bedrock_client.invoke_model.return_value = mock_response
        
        embeddings = dedupe_service.batch_generate_embeddings([question])
        
        assert len(embeddings) == 1
        assert "q1" in embeddings
        assert embeddings["q1"] == mock_embedding
    
    def test_batch_respects_batch_size(self, dedupe_service, mock_bedrock_client):
        """Test that batch size is respected"""
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
            for i in range(25)
        ]
        
        # Mock Bedrock
        mock_embedding = [0.1] * 1024
        mock_response = {
            'body': Mock(read=lambda: json.dumps({'embedding': mock_embedding}).encode())
        }
        mock_bedrock_client.invoke_model.return_value = mock_response
        
        # Generate with batch size of 10
        embeddings = dedupe_service.batch_generate_embeddings(questions, batch_size=10)
        
        # Should process all 25 questions in 3 batches
        assert len(embeddings) == 25
        assert mock_bedrock_client.invoke_model.call_count == 25
    
    def test_batch_continues_on_error(self, dedupe_service, mock_bedrock_client):
        """Test that batch continues processing after errors"""
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
        
        # Mock Bedrock - fail on questions 1 and 3
        call_count = [0]
        def mock_invoke(modelId, body):
            call_count[0] += 1
            if call_count[0] in [2, 4]:
                raise Exception("Bedrock error")
            return {
                'body': Mock(read=lambda: json.dumps({'embedding': [0.1] * 1024}).encode())
            }
        
        mock_bedrock_client.invoke_model.side_effect = mock_invoke
        
        embeddings = dedupe_service.batch_generate_embeddings(questions)
        
        # Should have 3 successful embeddings
        assert len(embeddings) == 3
        assert "q0" in embeddings
        assert "q2" in embeddings
        assert "q4" in embeddings
        assert "q1" not in embeddings
        assert "q3" not in embeddings


class TestEmbeddingRetrieval:
    """Test embedding retrieval from DynamoDB"""
    
    def test_get_topic_questions_success(
        self, dedupe_service, mock_dynamodb_client
    ):
        """Test successful retrieval of topic questions"""
        mock_table = mock_dynamodb_client.Table.return_value
        mock_table.scan.return_value = {
            'Items': [
                {
                    'question_id': 'q1',
                    'stem': 'Question 1',
                    'embedding': [0.1] * 1024
                },
                {
                    'question_id': 'q2',
                    'stem': 'Question 2',
                    'embedding': [0.2] * 1024
                }
            ]
        }
        
        questions = dedupe_service._get_topic_questions("algebra", "foundation")
        
        assert len(questions) == 2
        assert questions[0]['question_id'] == 'q1'
        assert questions[1]['question_id'] == 'q2'
        
        # Verify scan was called with correct filter
        call_args = mock_table.scan.call_args
        assert ':topic' in call_args[1]['ExpressionAttributeValues']
        assert ':grade' in call_args[1]['ExpressionAttributeValues']
    
    def test_get_topic_questions_empty(
        self, dedupe_service, mock_dynamodb_client
    ):
        """Test retrieval when no questions exist"""
        mock_table = mock_dynamodb_client.Table.return_value
        mock_table.scan.return_value = {'Items': []}
        
        questions = dedupe_service._get_topic_questions("algebra", "foundation")
        
        assert questions == []
    
    def test_get_topic_questions_pagination(
        self, dedupe_service, mock_dynamodb_client
    ):
        """Test handling of paginated results"""
        mock_table = mock_dynamodb_client.Table.return_value
        
        # First page
        first_page = {
            'Items': [
                {'question_id': 'q1', 'stem': 'Q1', 'embedding': [0.1] * 1024}
            ],
            'LastEvaluatedKey': {'question_id': 'q1'}
        }
        
        # Second page
        second_page = {
            'Items': [
                {'question_id': 'q2', 'stem': 'Q2', 'embedding': [0.2] * 1024}
            ]
        }
        
        mock_table.scan.side_effect = [first_page, second_page]
        
        questions = dedupe_service._get_topic_questions("algebra", "foundation")
        
        assert len(questions) == 2
        assert mock_table.scan.call_count == 2
    
    def test_get_topic_questions_respects_limit(
        self, dedupe_service, mock_dynamodb_client
    ):
        """Test that limit parameter is respected"""
        mock_table = mock_dynamodb_client.Table.return_value
        mock_table.scan.return_value = {
            'Items': [
                {'question_id': f'q{i}', 'stem': f'Q{i}', 'embedding': [0.1] * 1024}
                for i in range(10)
            ]
        }
        
        questions = dedupe_service._get_topic_questions(
            "algebra", "foundation", limit=5
        )
        
        # Verify limit was passed to scan
        call_args = mock_table.scan.call_args
        assert call_args[1]['Limit'] == 5
    
    def test_get_topic_questions_error_handling(
        self, dedupe_service, mock_dynamodb_client
    ):
        """Test error handling in retrieval"""
        mock_table = mock_dynamodb_client.Table.return_value
        mock_table.scan.side_effect = Exception("DynamoDB error")
        
        questions = dedupe_service._get_topic_questions("algebra", "foundation")
        
        # Should return empty list on error
        assert questions == []


class TestEmbeddingStorage:
    """Test embedding storage operations"""
    
    def test_store_embedding_updates_dynamodb(
        self, dedupe_service, mock_dynamodb_client
    ):
        """Test that embedding is stored in DynamoDB"""
        embedding = [0.5] * 1024
        mock_table = mock_dynamodb_client.Table.return_value
        
        result = dedupe_service.store_embedding("test-123", embedding)
        
        assert result is True
        
        # Verify update_item was called
        mock_table.update_item.assert_called_once()
        call_args = mock_table.update_item.call_args
        
        # Verify key
        assert call_args[1]['Key'] == {'question_id': 'test-123'}
        
        # Verify update expression
        assert 'SET embedding = :emb' in call_args[1]['UpdateExpression']
        assert call_args[1]['ExpressionAttributeValues'][':emb'] == embedding
    
    def test_store_embedding_handles_errors(
        self, dedupe_service, mock_dynamodb_client
    ):
        """Test error handling in storage"""
        embedding = [0.5] * 1024
        mock_table = mock_dynamodb_client.Table.return_value
        mock_table.update_item.side_effect = Exception("DynamoDB error")
        
        result = dedupe_service.store_embedding("test-123", embedding)
        
        assert result is False
    
    def test_store_multiple_embeddings(
        self, dedupe_service, mock_dynamodb_client
    ):
        """Test storing multiple embeddings"""
        embeddings = {
            "q1": [0.1] * 1024,
            "q2": [0.2] * 1024,
            "q3": [0.3] * 1024
        }
        
        mock_table = mock_dynamodb_client.Table.return_value
        
        results = []
        for question_id, embedding in embeddings.items():
            result = dedupe_service.store_embedding(question_id, embedding)
            results.append(result)
        
        # All should succeed
        assert all(results)
        assert mock_table.update_item.call_count == 3


class TestEmbeddingCaching:
    """Test embedding caching and reuse"""
    
    def test_precomputed_embedding_skips_generation(
        self, dedupe_service, mock_bedrock_client, mock_dynamodb_client
    ):
        """Test that precomputed embeddings skip generation"""
        question = {
            'question_id': "q1",
            'stem': "Test",
            'options': ["A", "B", "C", "D"],
            'correct_answer': "A",
            'rationale': "Test",
            'topic': "test",
            'grade': "foundation",
            'paper_type': "P1",
            'difficulty': 5
        }
        
        precomputed = [0.7] * 1024
        
        # Mock DynamoDB
        mock_table = mock_dynamodb_client.Table.return_value
        mock_table.scan.return_value = {'Items': []}
        
        result = dedupe_service.check_duplicate(
            question,
            existing_embedding=precomputed
        )
        
        # Bedrock should not be called
        mock_bedrock_client.invoke_model.assert_not_called()
        
        # Result should include the precomputed embedding
        assert result.embedding == precomputed
    
    def test_embedding_returned_in_result(
        self, dedupe_service, mock_bedrock_client, mock_dynamodb_client
    ):
        """Test that generated embedding is returned in result"""
        question = {
            'question_id': "q1",
            'stem': "Test",
            'options': ["A", "B", "C", "D"],
            'correct_answer': "A",
            'rationale': "Test",
            'topic': "test",
            'grade': "foundation",
            'paper_type': "P1",
            'difficulty': 5
        }
        
        # Mock Bedrock
        generated_embedding = [0.8] * 1024
        mock_response = {
            'body': Mock(read=lambda: json.dumps({'embedding': generated_embedding}).encode())
        }
        mock_bedrock_client.invoke_model.return_value = mock_response
        
        # Mock DynamoDB
        mock_table = mock_dynamodb_client.Table.return_value
        mock_table.scan.return_value = {'Items': []}
        
        result = dedupe_service.check_duplicate(question)
        
        # Result should include the generated embedding
        assert result.embedding == generated_embedding


class TestPerformanceOptimization:
    """Test performance optimization features"""
    
    def test_projection_expression_limits_data(
        self, dedupe_service, mock_dynamodb_client
    ):
        """Test that only necessary fields are retrieved"""
        mock_table = mock_dynamodb_client.Table.return_value
        mock_table.scan.return_value = {'Items': []}
        
        dedupe_service._get_topic_questions("algebra", "foundation")
        
        # Verify projection expression was used
        call_args = mock_table.scan.call_args
        assert 'ProjectionExpression' in call_args[1]
        projection = call_args[1]['ProjectionExpression']
        
        # Should only request necessary fields
        assert 'question_id' in projection
        assert 'stem' in projection
        assert 'embedding' in projection
    
    def test_batch_size_optimization(self, dedupe_service, mock_bedrock_client):
        """Test that batch size can be tuned for performance"""
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
            for i in range(100)
        ]
        
        # Mock Bedrock
        mock_embedding = [0.1] * 1024
        mock_response = {
            'body': Mock(read=lambda: json.dumps({'embedding': mock_embedding}).encode())
        }
        mock_bedrock_client.invoke_model.return_value = mock_response
        
        # Test with different batch sizes
        embeddings_small = dedupe_service.batch_generate_embeddings(
            questions, batch_size=10
        )
        
        embeddings_large = dedupe_service.batch_generate_embeddings(
            questions, batch_size=50
        )
        
        # Both should produce same results
        assert len(embeddings_small) == 100
        assert len(embeddings_large) == 100
