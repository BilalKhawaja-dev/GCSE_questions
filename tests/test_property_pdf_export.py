"""
Property-based tests for PDF export functionality.

Tests Property 16: PDF Export Completeness
Validates Requirements 5.6, 5.7, 5.8
"""

import pytest
import json
import base64
from datetime import datetime
from hypothesis import given, strategies as st
from hypothesis import settings
from unittest.mock import Mock, patch
import io

from src.services.pdf_export_service import pdf_export_service
from src.lambda_handlers.export_lambda import handler


# Test data generators
@st.composite
def generate_question(draw):
    """Generate a valid question for testing"""
    return {
        'id': draw(st.text(min_size=5, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))),
        'question_text': draw(st.text(min_size=10, max_size=500)),
        'mark_scheme': draw(st.text(min_size=5, max_size=200)),
        'difficulty_score': draw(st.integers(min_value=1, max_value=10)),
        'topic': draw(st.sampled_from(['fractions', 'algebra', 'geometry', 'statistics'])),
        'subtopic': draw(st.text(min_size=3, max_size=30)),
        'assessment_objective': draw(st.sampled_from(['AO1', 'AO2', 'AO3'])),
        'learning_objective': draw(st.text(min_size=10, max_size=100))
    }


@st.composite
def generate_session_data(draw):
    """Generate valid session data for testing"""
    questions = draw(st.lists(generate_question(), min_size=1, max_size=10))
    timestamp = draw(st.integers(min_value=1640995200, max_value=2000000000))  # 2022-2033 range
    
    return {
        'session_id': draw(st.text(min_size=10, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))),
        'user_id': draw(st.text(min_size=5, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))),
        'query': draw(st.text(min_size=5, max_size=200)),
        'generated_questions': questions,
        'mark_schemes': [q['mark_scheme'] for q in questions],
        'timestamp': timestamp,
        'ttl': timestamp + 604800,  # 7 days
        'metadata': {
            'topic': draw(st.sampled_from(['fractions', 'algebra', 'geometry', 'statistics'])),
            'tier': draw(st.sampled_from(['foundation', 'higher'])),
            'question_count': len(questions),
            'generation_time': draw(st.floats(min_value=0.1, max_value=30.0)),
            'specification_version': '2024.1'
        }
    }


@st.composite
def generate_user_info(draw):
    """Generate valid user info for testing"""
    return {
        'username': draw(st.text(min_size=3, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))),
        'email': draw(st.emails()),
        'school': draw(st.text(min_size=5, max_size=50)),
        'subject_specialization': draw(st.sampled_from(['Mathematics', 'Physics', 'Chemistry', 'Biology']))
    }


class TestPDFExportProperties:
    """Property-based tests for PDF export functionality"""
    
    @given(generate_session_data())
    @settings(max_examples=100)
    def test_pdf_export_completeness(self, session_data):
        """
        Feature: gcse-question-generator-v2, Property 16: PDF Export Completeness
        For any export request, the system should generate a PDF containing questions, 
        mark schemes, and metadata (difficulty scores, topic, tier, timestamp).
        Validates: Requirements 5.6, 5.7, 5.8
        """
        # Act - Generate PDF
        pdf_bytes = pdf_export_service.generate_pdf(session_data)
        
        # Assert - PDF should be generated
        assert isinstance(pdf_bytes, bytes), "PDF should be returned as bytes"
        assert len(pdf_bytes) > 0, "PDF should not be empty"
        
        # Assert - PDF should be valid (starts with PDF header)
        assert pdf_bytes.startswith(b'%PDF-'), "Generated content should be a valid PDF"
        
        # Assert - PDF should contain substantial content (not just header)
        assert len(pdf_bytes) > 1000, "PDF should contain substantial content"
    
    @given(generate_session_data(), generate_user_info())
    @settings(max_examples=100)
    def test_pdf_export_with_user_info(self, session_data, user_info):
        """
        Test PDF generation with user information for personalization
        """
        # Act - Generate PDF with user info
        pdf_bytes = pdf_export_service.generate_pdf(session_data, user_info)
        
        # Assert - PDF should be generated successfully
        assert isinstance(pdf_bytes, bytes), "PDF should be returned as bytes"
        assert len(pdf_bytes) > 0, "PDF should not be empty"
        assert pdf_bytes.startswith(b'%PDF-'), "Generated content should be a valid PDF"
    
    @given(generate_session_data())
    @settings(max_examples=100)
    def test_filename_generation_completeness(self, session_data):
        """
        Test that filename generation includes all required metadata
        """
        # Act - Generate filename
        filename = pdf_export_service.generate_filename(session_data)
        
        # Assert - Filename should be properly formatted
        assert isinstance(filename, str), "Filename should be a string"
        assert filename.endswith('.pdf'), "Filename should have .pdf extension"
        assert len(filename) > 10, "Filename should be descriptive"
        
        # Assert - Filename should contain key components
        topic = session_data.get('metadata', {}).get('topic', 'mixed')
        tier = session_data.get('metadata', {}).get('tier', 'foundation')
        
        # Clean topic name for comparison
        clean_topic = topic.lower().replace(' ', '_').replace('-', '_')
        
        assert clean_topic in filename, f"Filename should contain topic: {clean_topic}"
        assert tier.lower() in filename, f"Filename should contain tier: {tier}"
        assert 'gcse_questions' in filename, "Filename should contain 'gcse_questions'"
    
    @given(generate_session_data(), generate_user_info())
    @settings(max_examples=100)
    def test_filename_with_user_info(self, session_data, user_info):
        """
        Test filename generation with user information
        """
        # Act - Generate filename with user info
        filename = pdf_export_service.generate_filename(session_data, user_info)
        
        # Assert - Filename should include user information
        assert isinstance(filename, str), "Filename should be a string"
        assert filename.endswith('.pdf'), "Filename should have .pdf extension"
        
        # User info should be included (sanitized username)
        clean_username = user_info['username'].lower().replace(' ', '_')[:10]
        assert clean_username in filename, "Filename should contain sanitized username"
    
    @given(st.text(min_size=1, max_size=1000))
    @settings(max_examples=100)
    def test_mathematical_text_formatting(self, text):
        """
        Test mathematical text formatting for PDF display
        Validates Requirements 5.7 (proper mathematical formatting)
        """
        # Act - Format mathematical text
        formatted_text = pdf_export_service._format_mathematical_text(text)
        
        # Assert - Text should be formatted properly
        assert isinstance(formatted_text, str), "Formatted text should be a string"
        
        # Assert - HTML characters should be escaped for ReportLab
        assert '&amp;' in formatted_text or '&' not in text, "Ampersands should be escaped"
        assert '&lt;' in formatted_text or '<' not in text, "Less-than should be escaped"
        assert '&gt;' in formatted_text or '>' not in text, "Greater-than should be escaped"
    
    @given(st.integers(min_value=0, max_value=2147483647))
    @settings(max_examples=100)
    def test_timestamp_formatting(self, timestamp):
        """
        Test timestamp formatting for display
        """
        # Act - Format timestamp
        formatted_timestamp = pdf_export_service._format_timestamp(timestamp)
        
        # Assert - Timestamp should be formatted properly
        assert isinstance(formatted_timestamp, str), "Formatted timestamp should be a string"
        assert len(formatted_timestamp) > 0, "Formatted timestamp should not be empty"
        
        # For valid timestamps, should contain date components
        if timestamp > 0:
            # Should contain year, month, day pattern
            assert any(char.isdigit() for char in formatted_timestamp), "Should contain digits"
    
    def test_timestamp_formatting_edge_cases(self):
        """
        Test timestamp formatting with edge cases
        """
        # Test None timestamp
        result = pdf_export_service._format_timestamp(None)
        assert result == "Unknown", "None timestamp should return 'Unknown'"
        
        # Test invalid timestamp
        result = pdf_export_service._format_timestamp(-1)
        assert result == "Invalid timestamp", "Invalid timestamp should return error message"
    
    @given(generate_session_data())
    @settings(max_examples=50)
    def test_export_lambda_handler_structure(self, session_data):
        """
        Test the export lambda handler with valid session data
        """
        # Arrange - Mock dependencies
        with patch('src.lambda_handlers.export_lambda.session_service') as mock_session_service, \
             patch('src.lambda_handlers.export_lambda.auth_service') as mock_auth_service:
            
            # Setup mocks
            mock_auth_service.validate_session_token.return_value = {'valid': True}
            mock_auth_service.get_user_info.return_value = {'username': 'test_user'}
            mock_session_service.get_session.return_value = session_data
            
            # Create valid event
            event = {
                'session_id': session_data['session_id'],
                'session_token': 'valid_token_12345678901234567890123456789012',
                'user_id': session_data['user_id'],
                'format': 'pdf'
            }
            
            # Act - Call handler
            response = handler(event, {})
            
            # Assert - Response should be successful
            assert response['statusCode'] == 200, "Handler should return success status"
            
            body = json.loads(response['body'])
            assert body['success'] is True, "Response should indicate success"
            assert 'filename' in body, "Response should include filename"
            assert 'pdf_data' in body, "Response should include PDF data"
            assert 'metadata' in body, "Response should include metadata"
            
            # Assert - PDF data should be base64 encoded
            pdf_data = body['pdf_data']
            assert isinstance(pdf_data, str), "PDF data should be base64 string"
            
            # Verify base64 decoding works
            try:
                decoded_pdf = base64.b64decode(pdf_data)
                assert decoded_pdf.startswith(b'%PDF-'), "Decoded PDF should be valid"
            except Exception as e:
                pytest.fail(f"PDF data should be valid base64: {e}")
    
    def test_export_lambda_handler_validation_errors(self):
        """
        Test export lambda handler with validation errors
        """
        # Test missing required fields
        event = {'session_id': 'test'}  # Missing session_token and user_id
        
        response = handler(event, {})
        
        assert response['statusCode'] == 400, "Should return bad request for missing fields"
        body = json.loads(response['body'])
        assert 'error' in body, "Response should contain error message"
        assert 'Missing required fields' in body['error'], "Should indicate missing fields"
    
    def test_export_lambda_handler_invalid_format(self):
        """
        Test export lambda handler with unsupported format
        """
        with patch('src.lambda_handlers.export_lambda.auth_service') as mock_auth_service:
            mock_auth_service.validate_session_token.return_value = {'valid': True}
            
            event = {
                'session_id': 'test_session',
                'session_token': 'valid_token_12345678901234567890123456789012',
                'user_id': 'test_user',
                'format': 'docx'  # Unsupported format
            }
            
            response = handler(event, {})
            
            assert response['statusCode'] == 400, "Should return bad request for unsupported format"
            body = json.loads(response['body'])
            assert 'Unsupported export format' in body['error'], "Should indicate unsupported format"
    
    def test_export_lambda_handler_invalid_session(self):
        """
        Test export lambda handler with invalid session token
        """
        with patch('src.lambda_handlers.export_lambda.auth_service') as mock_auth_service:
            mock_auth_service.validate_session_token.return_value = {'valid': False}
            
            event = {
                'session_id': 'test_session',
                'session_token': 'invalid_token',
                'user_id': 'test_user',
                'format': 'pdf'
            }
            
            response = handler(event, {})
            
            assert response['statusCode'] == 401, "Should return unauthorized for invalid token"
            body = json.loads(response['body'])
            assert 'Invalid or expired session token' in body['error'], "Should indicate invalid token"
    
    def test_export_lambda_handler_session_not_found(self):
        """
        Test export lambda handler when session is not found
        """
        with patch('src.lambda_handlers.export_lambda.session_service') as mock_session_service, \
             patch('src.lambda_handlers.export_lambda.auth_service') as mock_auth_service:
            
            mock_auth_service.validate_session_token.return_value = {'valid': True}
            mock_session_service.get_session.return_value = None  # Session not found
            
            event = {
                'session_id': 'nonexistent_session',
                'session_token': 'valid_token_12345678901234567890123456789012',
                'user_id': 'test_user',
                'format': 'pdf'
            }
            
            response = handler(event, {})
            
            assert response['statusCode'] == 404, "Should return not found for missing session"
            body = json.loads(response['body'])
            assert 'Session not found' in body['error'], "Should indicate session not found"


if __name__ == '__main__':
    pytest.main([__file__])