"""
Simple integration tests for GCSE Question Generator V2.
Tests core functionality without complex AWS mocking.

Requirements: All functional requirements
"""

import json
import pytest
import os
import sys
import bcrypt
from unittest.mock import patch, MagicMock

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestSimpleIntegration:
    """Simple integration tests for core functionality."""
    
    def test_auth_service_integration(self):
        """Test authentication service integration."""
        from src.services.auth_service import AuthService
        from src.models.user import AuthRequest
        
        # Test with mock DynamoDB
        with patch('boto3.resource') as mock_boto3:
            mock_dynamodb = MagicMock()
            mock_table = MagicMock()
            mock_boto3.return_value = mock_dynamodb
            mock_dynamodb.Table.return_value = mock_table
            
            # Mock successful user creation - user doesn't exist initially
            mock_table.get_item.side_effect = [
                {},  # First call - user doesn't exist
                {    # Second call for login - user exists
                    'Item': {
                        'pk': 'USER#testuser',
                        'username': 'testuser',
                        'password_hash': bcrypt.hashpw('TestPass123!'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
                        'email': 'test@example.com'
                    }
                }
            ]
            mock_table.query.return_value = {'Items': []}      # Email doesn't exist
            
            auth_service = AuthService('test-table', 'eu-west-2')
            
            # Test user registration
            register_request = AuthRequest(
                action='register',
                username='testuser',
                password='TestPass123!',
                email='test@example.com'
            )
            
            result = auth_service.register_user(register_request)
            
            assert result.success is True
            assert result.session_token is not None
            
            # Test user login
            login_request = AuthRequest(
                action='login',
                username='testuser',
                password='TestPass123!'
            )
            
            login_result = auth_service.login_user(login_request)
            
            assert login_result.success is True
            assert login_result.session_token is not None
    
    def test_bedrock_service_integration(self):
        """Test Bedrock service integration."""
        from src.services.bedrock_service import BedrockService
        
        with patch('boto3.client') as mock_boto3:
            mock_bedrock = MagicMock()
            mock_boto3.return_value = mock_bedrock
            
            # Mock Haiku response
            mock_bedrock.invoke_model.return_value = {
                'body': MagicMock()
            }
            mock_bedrock.invoke_model.return_value['body'].read.return_value = json.dumps({
                "content": [{
                    "text": json.dumps({
                        "intent": {
                            "topic": "fractions",
                            "tier": "foundation",
                            "count": 3
                        }
                    })
                }]
            }).encode()
            
            bedrock_service = BedrockService('eu-west-2')
            
            # Test Haiku invocation
            result = bedrock_service.invoke_haiku("Test prompt")
            
            assert 'intent' in result
            assert result['intent']['topic'] == 'fractions'
            assert result['intent']['tier'] == 'foundation'
            assert result['intent']['count'] == 3
    
    def test_question_generation_flow(self):
        """Test complete question generation flow."""
        from src.services.bedrock_service import BedrockService
        from src.services.content_retrieval_service import ContentRetrievalService
        from src.utils.math_rendering import convert_latex_to_plain_text
        
        # Test LaTeX conversion
        latex_text = r"Calculate \frac{3}{4} + \frac{1}{2} and express as \sqrt{x^2}"
        converted = convert_latex_to_plain_text(latex_text)
        
        assert r"\frac" not in converted
        assert r"\sqrt" not in converted
        assert "3/4" in converted or "¾" in converted
        
        # Test content retrieval with mock S3
        with patch('boto3.client') as mock_boto3:
            mock_s3 = MagicMock()
            mock_boto3.return_value = mock_s3
            
            mock_s3.get_object.return_value = {
                'Body': MagicMock()
            }
            mock_s3.get_object.return_value['Body'].read.return_value = json.dumps({
                "topic": "fractions",
                "learning_objectives": ["Add fractions", "Subtract fractions"],
                "common_misconceptions": ["Adding denominators"]
            }).encode()
            
            content_service = ContentRetrievalService('test-bucket', 'eu-west-2')
            
            # Test content retrieval
            content = content_service.get_specification_content('fractions')
            
            assert content['topic'] == 'fractions'
            assert len(content['learning_objectives']) == 2
            assert len(content['common_misconceptions']) == 1
    
    def test_session_management_flow(self):
        """Test session management functionality."""
        from src.services.session_service import SessionService
        
        with patch('boto3.resource') as mock_boto3:
            mock_dynamodb = MagicMock()
            mock_table = MagicMock()
            mock_boto3.return_value = mock_dynamodb
            mock_dynamodb.Table.return_value = mock_table
            
            # Mock successful session storage
            mock_table.put_item.return_value = {}
            mock_table.query.return_value = {
                'Items': [{
                    'PK': 'SESSION#test_session',
                    'SK': 'TIMESTAMP#1234567890',
                    'session_id': 'test_session',
                    'user_id': 'USER#testuser',
                    'query': 'Test query',
                    'generated_questions': [
                        {
                            'id': 'q1',
                            'question_text': 'Test question',
                            'mark_scheme': 'Test answer',
                            'difficulty_score': 5
                        }
                    ],
                    'timestamp': 1234567890,
                    'ttl': 1234567890 + 604800
                }]
            }
            
            session_service = SessionService('test-table', 'eu-west-2')
            
            # Test session creation
            session_id = session_service.create_session(
                user_id='USER#testuser',
                query='Test query',
                questions=[{
                    'id': 'q1',
                    'question_text': 'Test question',
                    'mark_scheme': 'Test answer',
                    'difficulty_score': 5
                }]
            )
            
            assert session_id is not None
            
            # Test session retrieval
            sessions = session_service.get_user_sessions('USER#testuser', limit=10)
            
            assert len(sessions) == 1
            assert sessions[0]['session_id'] == 'test_session'
            assert sessions[0]['user_id'] == 'USER#testuser'
            assert len(sessions[0]['generated_questions']) == 1
    
    def test_feedback_collection_flow(self):
        """Test feedback collection functionality."""
        from src.services.feedback_service import FeedbackService
        
        with patch('boto3.resource') as mock_boto3:
            mock_dynamodb = MagicMock()
            mock_feedback_table = MagicMock()
            mock_quality_table = MagicMock()
            mock_boto3.return_value = mock_dynamodb
            
            def table_side_effect(table_name):
                if 'feedback' in table_name:
                    return mock_feedback_table
                elif 'quality' in table_name:
                    return mock_quality_table
                return MagicMock()
            
            mock_dynamodb.Table.side_effect = table_side_effect
            
            # Mock successful feedback storage
            mock_feedback_table.put_item.return_value = {}
            mock_quality_table.get_item.return_value = {
                'Item': {
                    'PK': 'QUALITY#q1',
                    'quality_score': 0.75,
                    'feedback_count': 5,
                    'helpful_count': 4
                }
            }
            mock_quality_table.put_item.return_value = {}
            
            try:
                feedback_service = FeedbackService('test-feedback-table', 'test-quality-table', 'eu-west-2')
                
                # Test feedback submission
                result = feedback_service.submit_feedback(
                    question_id='q1',
                    user_id='USER#testuser',
                    helpful=True,
                    difficulty_rating=5,
                    comments='Good question'
                )
                
                assert result['success'] is True
                assert 'updated_quality_score' in result
                
            except ImportError:
                # FeedbackService might not exist yet, skip this test
                pytest.skip("FeedbackService not implemented yet")
    
    def test_error_handling_mechanisms(self):
        """Test error handling and retry mechanisms."""
        from src.utils.error_handling import handle_bedrock_error, handle_s3_error
        
        # Test Bedrock error handling
        bedrock_error = Exception("Service temporarily unavailable")
        handled_error = handle_bedrock_error(bedrock_error, attempt=1)
        
        assert handled_error is not None
        assert 'retry' in str(handled_error).lower() or 'error' in str(handled_error).lower()
        
        # Test S3 error handling
        s3_error = Exception("Access denied")
        handled_s3_error = handle_s3_error(s3_error, bucket='test-bucket', key='test-key')
        
        assert handled_s3_error is not None
    
    def test_mathematical_rendering_integration(self):
        """Test mathematical rendering across the system."""
        from src.utils.math_rendering import convert_latex_to_plain_text, validate_no_latex_syntax
        
        # Test various LaTeX expressions
        test_cases = [
            (r"\frac{3}{4}", "3/4"),
            (r"\sqrt{16}", "√16"),
            (r"x^{2}", "x²"),
            (r"3 \times 4", "3 × 4"),
            (r"a \div b", "a ÷ b"),
            (r"x \leq 5", "x ≤ 5"),
            (r"y \geq 10", "y ≥ 10")
        ]
        
        for latex_input, expected_pattern in test_cases:
            converted = convert_latex_to_plain_text(latex_input)
            
            # Verify no LaTeX syntax remains
            assert not validate_no_latex_syntax(latex_input)  # Should fail validation (has LaTeX)
            assert validate_no_latex_syntax(converted)        # Should pass validation (no LaTeX)
            
            # Verify conversion contains expected elements
            if expected_pattern in ["3/4", "√16", "x²", "3 × 4", "a ÷ b", "x ≤ 5", "y ≥ 10"]:
                # Check that some form of the expected pattern exists
                assert any(char in converted for char in expected_pattern)
    
    def test_topic_coverage_tracking(self):
        """Test topic coverage tracking functionality."""
        from src.services.topic_coverage_service import TopicCoverageService
        
        with patch('boto3.resource') as mock_boto3:
            mock_dynamodb = MagicMock()
            mock_table = MagicMock()
            mock_boto3.return_value = mock_dynamodb
            mock_dynamodb.Table.return_value = mock_table
            
            # Mock coverage data
            mock_table.put_item.return_value = {}
            mock_table.query.return_value = {
                'Items': [
                    {
                        'PK': 'COVERAGE#USER#testuser#fractions',
                        'SK': 'TIMESTAMP#1234567890',
                        'user_id': 'USER#testuser',
                        'topic': 'fractions',
                        'subtopic': 'addition',
                        'question_count': 5,
                        'timestamp': 1234567890
                    },
                    {
                        'PK': 'COVERAGE#USER#testuser#algebra',
                        'SK': 'TIMESTAMP#1234567800',
                        'user_id': 'USER#testuser',
                        'topic': 'algebra',
                        'subtopic': 'linear_equations',
                        'question_count': 3,
                        'timestamp': 1234567800
                    }
                ]
            }
            
            coverage_service = TopicCoverageService('test-table', 'eu-west-2')
            
            # Test coverage recording
            coverage_service.record_topic_coverage(
                user_id='USER#testuser',
                topic='fractions',
                subtopic='addition',
                question_count=5
            )
            
            # Test coverage statistics
            stats = coverage_service.get_coverage_statistics('USER#testuser', days=30)
            
            assert 'coverage_stats' in stats
            assert len(stats['coverage_stats']) == 2
            
            # Test topic suggestions
            suggestions = coverage_service.get_topic_suggestions('USER#testuser')
            
            assert 'suggested_topics' in suggestions
    
    def test_pdf_export_integration(self):
        """Test PDF export functionality."""
        from src.services.pdf_export_service import PDFExportService
        
        # Test PDF generation with sample data
        questions = [
            {
                'id': 'q1',
                'question_text': 'Calculate 3/4 + 1/2',
                'mark_scheme': '3/4 + 1/2 = 6/8 + 4/8 = 10/8 = 5/4 [2 marks]',
                'difficulty_score': 4,
                'topic': 'fractions',
                'assessment_objective': 'AO1'
            },
            {
                'id': 'q2',
                'question_text': 'Solve for x: 2x + 5 = 13',
                'mark_scheme': '2x = 13 - 5 = 8, x = 4 [2 marks]',
                'difficulty_score': 5,
                'topic': 'algebra',
                'assessment_objective': 'AO2'
            }
        ]
        
        metadata = {
            'user_id': 'USER#testuser',
            'session_id': 'test_session',
            'timestamp': 1234567890,
            'query': 'Generate mixed questions'
        }
        
        pdf_service = PDFExportService()
        
        # Test PDF generation
        pdf_content = pdf_service.generate_pdf(questions, metadata)
        
        assert pdf_content is not None
        assert len(pdf_content) > 0
        assert pdf_content.startswith(b'%PDF')  # PDF header
    
    def test_validation_and_security(self):
        """Test validation and security mechanisms."""
        from src.utils.validation import validate_question_quality, sanitize_json_input
        from src.utils.security import validate_and_sanitize_input
        
        # Test question validation
        valid_question = {
            'id': 'q1',
            'question_text': 'Calculate 2 + 2',
            'mark_scheme': '2 + 2 = 4 [1 mark]',
            'difficulty_score': 2,
            'topic': 'arithmetic',
            'assessment_objective': 'AO1'
        }
        
        invalid_question = {
            'id': 'q2',
            'question_text': '',  # Empty text
            'mark_scheme': 'Answer',
            'difficulty_score': 15,  # Invalid score
            'topic': 'test'
        }
        
        assert validate_question_quality(valid_question) is True
        assert validate_question_quality(invalid_question) is False
        
        # Test input sanitization
        malicious_input = "<script>alert('xss')</script>Calculate 2+2"
        sanitized = validate_and_sanitize_input(malicious_input)
        
        assert '<script>' not in sanitized
        assert 'Calculate 2+2' in sanitized
        
        # Test JSON sanitization
        json_input = {
            'query': 'Generate questions',
            'malicious': '<script>alert("xss")</script>'
        }
        
        sanitized_json = sanitize_json_input(json_input)
        
        assert '<script>' not in str(sanitized_json)
        assert 'Generate questions' in sanitized_json['query']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])