"""
Unit tests for GenerateLambda function.

Tests specific examples, edge cases, and error conditions for the
question generation Lambda handler.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.lambda_handlers.generate_lambda import lambda_handler, _generate_questions
from src.services.content_retrieval_service import CircuitBreakerOpenError


def create_mock_context(function_name="GenerateLambda", remaining_time_ms=50000):
    """Helper function to create mock Lambda context."""
    context = Mock()
    context.function_name = function_name
    context.aws_request_id = "test-aws-request-id"
    context.memory_limit_in_mb = 512  # Add memory limit for lambda optimizer
    context.get_remaining_time_in_millis.return_value = remaining_time_ms
    return context


class TestGenerateLambdaHandler:
    """Unit tests for the main Lambda handler function."""
    
    def test_lambda_handler_success(self):
        """Test successful question generation request."""
        # Arrange
        event = {
            "body": json.dumps({
                "topic": "Number",
                "subtopic": "fractions",
                "tier": "Foundation",
                "count": 3,
                "specification_version": "latest"
            }),
            "headers": {
                "Authorization": "Bearer test-session-token"
            },
            "requestContext": {
                "identity": {
                    "sourceIp": "127.0.0.1"
                },
                "requestId": "test-request-id"
            }
        }
        context = Mock()
        context.function_name = "GenerateLambda"
        context.aws_request_id = "test-aws-request-id"
        context.memory_limit_in_mb = 512
        context.get_remaining_time_in_millis.return_value = 50000  # 50 seconds remaining
        
        expected_response = {
            "questions": [
                {
                    "id": "q1",
                    "question_text": "Calculate 1/2 + 1/4",
                    "marks": 2,
                    "tier": "Foundation",
                    "topic": "Number",
                    "subtopic": "fractions"
                }
            ],
            "mark_scheme": [
                {
                    "question_id": "q1",
                    "marking_criteria": "M1: Convert to common denominator, A1: Correct answer",
                    "method_marks": 1,
                    "accuracy_marks": 1
                }
            ],
            "metadata": {
                "generated_at": "2024-12-27T10:30:00Z",
                "model_version": "claude-3-sonnet-20240229",
                "total_marks": 2,
                "specification_version": "latest",
                "request_id": "test-request"
            }
        }
        
        with patch('src.lambda_handlers.generate_lambda._generate_questions', return_value=expected_response), \
             patch('src.lambda_handlers.generate_lambda.authenticate_request', return_value=(True, {'user_id': 'test-user', 'session_token': 'test-token'}, None)):
            # Act
            result = lambda_handler(event, context)
            
            # Debug: Print the actual result if it fails
            if result["statusCode"] != 200:
                print(f"Actual result: {result}")
            
            # Assert
            assert result["statusCode"] == 200
            assert "Content-Type" in result["headers"]
            assert result["headers"]["Content-Type"] == "application/json"
            assert "X-Request-ID" in result["headers"]
            
            body = json.loads(result["body"])
            assert body == expected_response
    
    def test_lambda_handler_missing_body(self):
        """Test handler with missing request body."""
        # Arrange
        event = {}
        context = Mock()
        context.function_name = "GenerateLambda"
        context.aws_request_id = "test-aws-request-id"
        context.memory_limit_in_mb = 512
        context.get_remaining_time_in_millis.return_value = 50000  # 50 seconds remaining
        
        # Act
        result = lambda_handler(event, context)
        
        # Assert
        assert result["statusCode"] == 500  # Caught by outer exception handler
        body = json.loads(result["body"])
        assert body["error"]["type"] == "InternalError"
    
    def test_lambda_handler_invalid_json(self):
        """Test handler with invalid JSON in body."""
        # Arrange
        event = {"body": "invalid json"}
        context = Mock()
        context.function_name = "GenerateLambda"
        context.aws_request_id = "test-aws-request-id"
        context.memory_limit_in_mb = 512
        context.get_remaining_time_in_millis.return_value = 50000  # 50 seconds remaining
        
        # Act
        result = lambda_handler(event, context)
        
        # Assert
        assert result["statusCode"] == 500  # Caught by outer exception handler
        body = json.loads(result["body"])
        assert body["error"]["type"] == "InternalError"
    
    def test_lambda_handler_validation_error(self):
        """Test handler with validation errors."""
        # Arrange
        event = {
            "body": json.dumps({
                "topic": "",  # Invalid empty topic
                "tier": "Invalid",  # Invalid tier
                "count": 0  # Invalid count
            }),
            "headers": {
                "Authorization": "Bearer test-session-token"
            },
            "requestContext": {
                "identity": {
                    "sourceIp": "127.0.0.1"
                },
                "requestId": "test-request-id"
            }
        }
        context = Mock()
        context.function_name = "GenerateLambda"
        context.aws_request_id = "test-aws-request-id"
        context.memory_limit_in_mb = 512
        context.get_remaining_time_in_millis.return_value = 50000  # 50 seconds remaining
        
        with patch('src.lambda_handlers.generate_lambda.authenticate_request', return_value=(True, {'user_id': 'test-user', 'session_token': 'test-token'}, None)):
            # Act
            result = lambda_handler(event, context)
            
            # Assert
            assert result["statusCode"] == 400
            body = json.loads(result["body"])
            assert body["error"]["type"] == "ValidationError"
            assert "validation failed" in body["error"]["message"].lower()
    
    def test_lambda_handler_generation_failure(self):
        """Test handler when question generation fails."""
        # Arrange
        event = {
            "body": json.dumps({
                "topic": "Number",
                "tier": "Foundation",
                "count": 3
            }),
            "headers": {
                "Authorization": "Bearer test-session-token"
            },
            "requestContext": {
                "identity": {
                    "sourceIp": "127.0.0.1"
                },
                "requestId": "test-request-id"
            }
        }
        context = Mock()
        context.function_name = "GenerateLambda"
        context.aws_request_id = "test-aws-request-id"
        context.memory_limit_in_mb = 512
        context.get_remaining_time_in_millis.return_value = 50000  # 50 seconds remaining
        
        with patch('src.lambda_handlers.generate_lambda._generate_questions', 
                  side_effect=Exception("Generation failed")), \
             patch('src.lambda_handlers.generate_lambda.authenticate_request', return_value=(True, {'user_id': 'test-user', 'session_token': 'test-token'}, None)):
            # Act
            result = lambda_handler(event, context)
            
            # Assert
            assert result["statusCode"] == 500
            body = json.loads(result["body"])
            assert body["error"]["type"] == "InternalError"
            assert "Failed to generate questions" in body["error"]["message"]
    
    def test_lambda_handler_unexpected_error(self):
        """Test handler with unexpected error."""
        # Arrange
        event = {
            "body": json.dumps({
                "topic": "Number",
                "tier": "Foundation", 
                "count": 3
            }),
            "headers": {
                "Authorization": "Bearer test-session-token"
            },
            "requestContext": {
                "identity": {
                    "sourceIp": "127.0.0.1"
                },
                "requestId": "test-request-id"
            }
        }
        context = Mock()
        context.function_name = "GenerateLambda"
        context.aws_request_id = "test-aws-request-id"
        context.memory_limit_in_mb = 512
        context.get_remaining_time_in_millis.return_value = 50000  # 50 seconds remaining
        
        with patch('src.lambda_handlers.generate_lambda.validate_generation_request',
                  side_effect=RuntimeError("Unexpected error")), \
             patch('src.lambda_handlers.generate_lambda.authenticate_request', return_value=(True, {'user_id': 'test-user', 'session_token': 'test-token'}, None)):
            # Act
            result = lambda_handler(event, context)
            
            # Assert
            assert result["statusCode"] == 500
            body = json.loads(result["body"])
            assert body["error"]["type"] == "InternalError"
            assert "unexpected error occurred" in body["error"]["message"].lower()


class TestGenerateQuestionsFunction:
    """Unit tests for the _generate_questions function."""
    
    @patch('src.lambda_handlers.generate_lambda.version_service')
    @patch('src.lambda_handlers.generate_lambda.content_service')
    @patch('src.lambda_handlers.generate_lambda.bedrock_service')
    def test_generate_questions_success(self, mock_bedrock, mock_content, mock_version):
        """Test successful question generation with all components."""
        # Arrange
        mock_version.get_version_selection_logic.return_value = "latest"
        # Arrange
        mock_version.get_version_selection_logic.return_value = "latest"
        
        generation_request = {
            "topic": "Number",
            "subtopic": "fractions",
            "tier": "Foundation",
            "count": 2,
            "specification_version": "latest"
        }
        
        mock_spec_content = {
            "domain": "number",
            "subtopic": "fractions",
            "learning_objectives": ["Add fractions with same denominator"],
            "specification_content": "Students should be able to add fractions..."
        }
        
        mock_examples = [
            {
                "question": {
                    "id": "ex1",
                    "question_text": "Calculate 1/2 + 1/4",
                    "marks": 2,
                    "tier": "Foundation"
                },
                "mark_scheme": {
                    "question_id": "ex1",
                    "marking_criteria": "Method and accuracy marks"
                }
            }
        ]
        
        mock_question_set = {
            "questions": [
                {
                    "id": "q1",
                    "question_text": "Add 2/3 + 1/6",
                    "marks": 3,
                    "tier": "Foundation",
                    "topic": "Number"
                }
            ],
            "mark_scheme": [
                {
                    "question_id": "q1",
                    "marking_criteria": "M2: Method, A1: Answer",
                    "method_marks": 2,
                    "accuracy_marks": 1
                }
            ],
            "metadata": {
                "generated_at": "2024-12-27T10:30:00Z",
                "total_marks": 3
            }
        }
        
        mock_content.get_specification_content_versioned.return_value = mock_spec_content
        mock_content.get_examples_content.return_value = mock_examples
        mock_bedrock.generate_questions_with_sonnet.return_value = mock_question_set
        
        # Act
        result = _generate_questions(generation_request, "test-request", create_mock_context())
        
        # Assert
        assert result == mock_question_set
        mock_content.get_specification_content_versioned.assert_called_once_with(
            topic="Number",
            subtopic="fractions",
            tier="Foundation",
            version="latest",
            request_id="test-request"
        )
        mock_content.get_examples_content.assert_called_once_with(
            topic="Number",
            subtopic="fractions",
            tier="Foundation",
            request_id="test-request"
        )
        mock_bedrock.generate_questions_with_sonnet.assert_called_once()
    
    @patch('src.lambda_handlers.generate_lambda.version_service')
    @patch('src.lambda_handlers.generate_lambda.content_service')
    def test_generate_questions_s3_unavailable(self, mock_content, mock_version):
        """Test question generation when S3 is unavailable."""
        # Arrange
        mock_version.get_version_selection_logic.return_value = "latest"
        # Arrange
        mock_version.get_version_selection_logic.return_value = "latest"
        
        generation_request = {
            "topic": "Number",
            "tier": "Foundation",
            "count": 1
        }
        
        mock_content.get_specification_content_versioned.side_effect = CircuitBreakerOpenError("S3 unavailable")
        
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            _generate_questions(generation_request, "test-request", create_mock_context())
        
        assert "Content service temporarily unavailable" in str(exc_info.value)
    
    @patch('src.lambda_handlers.generate_lambda.version_service')
    @patch('src.lambda_handlers.generate_lambda.content_service')
    def test_generate_questions_spec_retrieval_failure(self, mock_content, mock_version):
        """Test question generation when specification retrieval fails."""
        # Arrange
        mock_version.get_version_selection_logic.return_value = "latest"
        # Arrange
        mock_version.get_version_selection_logic.return_value = "latest"
        
        generation_request = {
            "topic": "InvalidTopic",
            "tier": "Foundation",
            "count": 1
        }
        
        mock_content.get_specification_content_versioned.side_effect = ValueError("Unknown topic")
        
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            _generate_questions(generation_request, "test-request", create_mock_context())
        
        assert "Failed to retrieve curriculum content" in str(exc_info.value)
    
    @patch('src.lambda_handlers.generate_lambda.version_service')
    @patch('src.lambda_handlers.generate_lambda.content_service')
    @patch('src.lambda_handlers.generate_lambda.bedrock_service')
    def test_generate_questions_examples_failure_continues(self, mock_bedrock, mock_content, mock_version):
        """Test that generation continues when examples retrieval fails."""
        # Arrange
        mock_version.get_version_selection_logic.return_value = "latest"
        # Arrange
        mock_version.get_version_selection_logic.return_value = "latest"
        
        generation_request = {
            "topic": "Number",
            "tier": "Foundation",
            "count": 1
        }
        
        mock_spec_content = {
            "learning_objectives": ["Test objective"],
            "specification_content": "Test content"
        }
        
        mock_question_set = {
            "questions": [{"id": "q1", "marks": 2}],
            "mark_scheme": [{"question_id": "q1"}],
            "metadata": {"total_marks": 2}
        }
        
        mock_content.get_specification_content_versioned.return_value = mock_spec_content
        mock_content.get_examples_content.side_effect = Exception("Examples unavailable")
        mock_bedrock.generate_questions_with_sonnet.return_value = mock_question_set
        
        # Act
        result = _generate_questions(generation_request, "test-request", create_mock_context())
        
        # Assert - Should succeed despite examples failure
        assert result == mock_question_set
        mock_bedrock.generate_questions_with_sonnet.assert_called_once()
        # Verify examples_content was passed as empty list
        call_args = mock_bedrock.generate_questions_with_sonnet.call_args
        assert call_args[1]['examples_content'] == []
    
    @patch('src.lambda_handlers.generate_lambda.version_service')
    @patch('src.lambda_handlers.generate_lambda.content_service')
    @patch('src.lambda_handlers.generate_lambda.bedrock_service')
    def test_generate_questions_bedrock_failure(self, mock_bedrock, mock_content, mock_version):
        """Test question generation when Bedrock fails."""
        # Arrange
        mock_version.get_version_selection_logic.return_value = "latest"
        # Arrange
        generation_request = {
            "topic": "Number",
            "tier": "Foundation",
            "count": 1
        }
        
        mock_content.get_specification_content_versioned.return_value = {"learning_objectives": []}
        mock_content.get_examples_content.return_value = []
        mock_bedrock.generate_questions_with_sonnet.side_effect = Exception("Bedrock failed")
        
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            _generate_questions(generation_request, "test-request", create_mock_context())
        
        assert "Failed to generate questions" in str(exc_info.value)


class TestS3ContentRetrievalEdgeCases:
    """Unit tests for S3 content retrieval edge cases."""
    
    @patch('src.lambda_handlers.generate_lambda.version_service')
    @patch('src.lambda_handlers.generate_lambda.content_service')
    def test_empty_specification_content(self, mock_content, mock_version):
        """Test handling of empty specification content."""
        # Arrange
        generation_request = {
            "topic": "Number",
            "tier": "Foundation",
            "count": 1
        }
        
        # Empty but valid specification content
        mock_content.get_specification_content_versioned.return_value = {
            "learning_objectives": [],
            "specification_content": "",
            "key_concepts": []
        }
        mock_content.get_examples_content.return_value = []
        
        with patch('src.lambda_handlers.generate_lambda.bedrock_service') as mock_bedrock:
            mock_bedrock.generate_questions_with_sonnet.return_value = {
                "questions": [],
                "mark_scheme": [],
                "metadata": {"total_marks": 0}
            }
            
            # Act
            result = _generate_questions(generation_request, "test-request", create_mock_context())
            
            # Assert - Should handle empty content gracefully
            assert result is not None
            mock_bedrock.generate_questions_with_sonnet.assert_called_once()
    
    @patch('src.lambda_handlers.generate_lambda.version_service')
    @patch('src.lambda_handlers.generate_lambda.content_service')
    def test_malformed_examples_content(self, mock_content, mock_version):
        """Test handling of malformed examples content."""
        # Arrange
        generation_request = {
            "topic": "Number",
            "tier": "Foundation",
            "count": 1
        }
        
        mock_content.get_specification_content_versioned.return_value = {
            "learning_objectives": ["Test"],
            "specification_content": "Test content"
        }
        
        # Malformed examples (missing required fields)
        mock_content.get_examples_content.return_value = [
            {"invalid": "structure"},
            {"question": {"id": "q1"}}  # Missing other required fields
        ]
        
        with patch('src.lambda_handlers.generate_lambda.bedrock_service') as mock_bedrock:
            mock_bedrock.generate_questions_with_sonnet.return_value = {
                "questions": [],
                "mark_scheme": [],
                "metadata": {"total_marks": 0}
            }
            
            # Act
            result = _generate_questions(generation_request, "test-request", create_mock_context())
            
            # Assert - Should handle malformed examples gracefully
            assert result is not None
            # Bedrock should still be called with the malformed examples
            mock_bedrock.generate_questions_with_sonnet.assert_called_once()


class TestQuestionQualityValidationEdgeCases:
    """Unit tests for question quality validation edge cases."""
    
    def test_json_schema_compliance_edge_cases(self):
        """Test JSON schema compliance with edge case data."""
        from src.services.bedrock_service import BedrockService
        
        # Test cases with edge values
        test_cases = [
            # Minimum valid question
            {
                "questions": [
                    {
                        "id": "q1",
                        "question_text": "Calculate 1+1",
                        "marks": 1,
                        "tier": "Foundation",
                        "topic": "Number"
                    }
                ],
                "mark_scheme": [
                    {
                        "question_id": "q1",
                        "marking_criteria": "A1: Correct answer",
                        "method_marks": 0,
                        "accuracy_marks": 1
                    }
                ],
                "metadata": {
                    "generated_at": "2024-12-27T10:30:00Z",
                    "model_version": "claude-3-sonnet-20240229",
                    "total_marks": 1
                }
            },
            # Maximum marks question
            {
                "questions": [
                    {
                        "id": "q1",
                        "question_text": "Complex multi-step problem",
                        "marks": 10,
                        "tier": "Higher",
                        "topic": "Algebra"
                    }
                ],
                "mark_scheme": [
                    {
                        "question_id": "q1",
                        "marking_criteria": "M5: Method marks, A5: Accuracy marks",
                        "method_marks": 5,
                        "accuracy_marks": 5
                    }
                ],
                "metadata": {
                    "generated_at": "2024-12-27T10:30:00Z",
                    "model_version": "claude-3-sonnet-20240229",
                    "total_marks": 10
                }
            }
        ]
        
        bedrock_service = BedrockService()
        
        for test_case in test_cases:
            # Act
            result = bedrock_service._validate_question_quality_enhanced(
                test_case,
                {"topic": "Number", "tier": "Foundation"},
                "test-request"
            )
            
            # Assert - Should validate successfully
            assert result is not None
            assert "quality_validation" in result["metadata"]
            assert "average_confidence" in result["metadata"]["quality_validation"]
            assert isinstance(result["metadata"]["quality_validation"]["average_confidence"], float)
    
    def test_difficulty_assessment_edge_cases(self):
        """Test difficulty assessment with edge case question texts."""
        from src.services.bedrock_service import BedrockService
        
        bedrock_service = BedrockService()
        
        # Test cases
        test_cases = [
            ("", 0.0),  # Empty string
            ("Calculate 1+1", 0.0),  # Very simple
            ("Solve the quadratic equation using the discriminant and factorization methods", 0.1),  # Complex
            ("Find \\frac{d}{dx}[\\sin(x^2)] using the chain rule", 0.1),  # LaTeX notation
        ]
        
        for question_text, expected_min_difficulty in test_cases:
            # Act
            difficulty = bedrock_service._assess_difficulty(question_text)
            
            # Assert
            assert 0.0 <= difficulty <= 1.0
            assert isinstance(difficulty, float)
            # For non-empty questions, difficulty should be reasonable
            if question_text:
                assert difficulty >= expected_min_difficulty or difficulty == 0.0