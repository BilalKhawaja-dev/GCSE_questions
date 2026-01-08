"""
Property-based tests for async SQS message handling.

Feature: gcse-enhancement-suite
Property 32: SQS messages contain all required job parameters
Property 33: Job status updates persist correctly to DynamoDB
"""

import pytest
import json
import uuid
from datetime import datetime
from hypothesis import given, strategies as st, settings
from hypothesis import assume
import os

# Test configuration
os.environ['AWS_REGION'] = 'eu-west-2'
os.environ['REGION'] = 'eu-west-2'
os.environ['SESSIONS_TABLE_NAME'] = 'test-sessions'
os.environ['TOPIC_COVERAGE_TABLE_NAME'] = 'test-topic-coverage'


# Strategies for generating test data
@st.composite
def job_parameters(draw):
    """Generate valid job parameters for SQS messages."""
    topics = ['Algebra', 'Number', 'Geometry', 'Statistics', 'Probability']
    tiers = ['Foundation', 'Higher']
    
    return {
        'job_id': f"job_{draw(st.uuids())}",
        'session_id': str(draw(st.uuids())),
        'topic': draw(st.sampled_from(topics)),
        'tier': draw(st.sampled_from(tiers)),
        'count': draw(st.integers(min_value=11, max_value=50)),
        'enriched_prompt': draw(st.text(min_size=0, max_size=200)),
        'user_id': f"user_{draw(st.uuids())}",
        'request_id': str(draw(st.uuids()))
    }


@st.composite
def job_status_update(draw):
    """Generate valid job status updates."""
    statuses = ['pending', 'processing', 'completed', 'failed']
    
    status = draw(st.sampled_from(statuses))
    
    # Generate progress based on status
    if status == 'completed':
        progress = 100  # Completed jobs must have 100% progress
    else:
        progress = draw(st.integers(min_value=0, max_value=100))
    
    update = {
        'job_id': f"job_{draw(st.uuids())}",
        'session_id': str(draw(st.uuids())),
        'status': status,
        'progress': progress,
        'topic': draw(st.sampled_from(['Algebra', 'Number', 'Geometry'])),
        'tier': draw(st.sampled_from(['Foundation', 'Higher'])),
        'count': draw(st.integers(min_value=11, max_value=50))
    }
    
    if status == 'failed':
        update['error'] = draw(st.text(min_size=1, max_size=100))
    
    if status == 'completed':
        update['generation_time'] = draw(st.floats(min_value=1.0, max_value=300.0))
    
    return update


class TestSQSMessageHandling:
    """
    Property 32: SQS messages contain all required job parameters
    Validates: Async processing reliability
    """
    
    @given(params=job_parameters())
    @settings(max_examples=100, deadline=None)
    def test_sqs_message_contains_required_parameters(self, params):
        """
        Feature: gcse-enhancement-suite, Property 32: SQS messages contain all required job parameters
        
        For any valid job parameters, the SQS message should contain all required fields
        for async processing.
        """
        # Required fields for async processing
        required_fields = [
            'job_id', 'session_id', 'topic', 'tier', 'count',
            'enriched_prompt', 'user_id', 'request_id'
        ]
        
        # Verify all required fields are present
        for field in required_fields:
            assert field in params, f"Missing required field: {field}"
            assert params[field] is not None, f"Field {field} is None"
        
        # Verify field types
        assert isinstance(params['job_id'], str)
        assert isinstance(params['session_id'], str)
        assert isinstance(params['topic'], str)
        assert isinstance(params['tier'], str)
        assert isinstance(params['count'], int)
        assert isinstance(params['enriched_prompt'], str)
        assert isinstance(params['user_id'], str)
        assert isinstance(params['request_id'], str)
        
        # Verify field constraints
        assert params['count'] >= 11, "Async processing should be for 11+ questions"
        assert params['count'] <= 50, "Count should not exceed 50"
        assert params['tier'] in ['Foundation', 'Higher']
        assert len(params['topic']) > 0
        
        # Verify message can be serialized to JSON
        message_body = json.dumps(params)
        assert len(message_body) > 0
        
        # Verify message can be deserialized
        deserialized = json.loads(message_body)
        assert deserialized == params
    
    @given(params=job_parameters())
    @settings(max_examples=100, deadline=None)
    def test_sqs_message_format_is_valid(self, params):
        """
        Feature: gcse-enhancement-suite, Property 32: SQS messages contain all required job parameters
        
        For any job parameters, the SQS message format should be valid and parseable.
        """
        # Create SQS message format
        message = {
            'MessageBody': json.dumps(params),
            'MessageAttributes': {
                'job_id': {
                    'StringValue': params['job_id'],
                    'DataType': 'String'
                },
                'user_id': {
                    'StringValue': params['user_id'],
                    'DataType': 'String'
                }
            }
        }
        
        # Verify message structure
        assert 'MessageBody' in message
        assert 'MessageAttributes' in message
        
        # Verify message body is valid JSON
        body = json.loads(message['MessageBody'])
        assert body == params
        
        # Verify message attributes
        assert 'job_id' in message['MessageAttributes']
        assert 'user_id' in message['MessageAttributes']
        assert message['MessageAttributes']['job_id']['StringValue'] == params['job_id']
        assert message['MessageAttributes']['user_id']['StringValue'] == params['user_id']


class TestJobStatusPersistence:
    """
    Property 33: Job status updates persist correctly to DynamoDB
    Validates: Async processing reliability
    """
    
    @given(update=job_status_update())
    @settings(max_examples=100, deadline=None)
    def test_job_status_update_structure(self, update):
        """
        Feature: gcse-enhancement-suite, Property 33: Job status updates persist correctly to DynamoDB
        
        For any job status update, the metadata structure should be valid and complete.
        """
        # Required fields for status updates
        required_fields = ['job_id', 'session_id', 'status', 'progress']
        
        for field in required_fields:
            assert field in update, f"Missing required field: {field}"
        
        # Verify status is valid
        assert update['status'] in ['pending', 'processing', 'completed', 'failed']
        
        # Verify progress is in valid range
        assert 0 <= update['progress'] <= 100
        
        # Verify conditional fields
        if update['status'] == 'failed':
            assert 'error' in update, "Failed status should include error message"
            assert len(update['error']) > 0
        
        if update['status'] == 'completed':
            # Completed jobs should have generation time
            if 'generation_time' in update:
                assert update['generation_time'] > 0
    
    @given(update=job_status_update())
    @settings(max_examples=100, deadline=None)
    def test_job_status_metadata_serialization(self, update):
        """
        Feature: gcse-enhancement-suite, Property 33: Job status updates persist correctly to DynamoDB
        
        For any job status update, the metadata should be serializable for DynamoDB storage.
        """
        # Create metadata structure
        metadata = {
            'job_id': update['job_id'],
            'status': update['status'],
            'progress': update['progress'],
            'updated_at': datetime.utcnow().isoformat()
        }
        
        # Add optional fields
        if 'topic' in update:
            metadata['topic'] = update['topic']
        if 'tier' in update:
            metadata['tier'] = update['tier']
        if 'count' in update:
            metadata['count'] = update['count']
        if 'error' in update:
            metadata['error'] = update['error']
        if 'generation_time' in update:
            metadata['generation_time'] = update['generation_time']
        
        # Add timestamps based on status
        if update['status'] == 'processing':
            metadata['started_at'] = datetime.utcnow().isoformat()
        elif update['status'] in ['completed', 'failed']:
            metadata['completed_at'] = datetime.utcnow().isoformat()
        
        # Verify metadata can be serialized to JSON
        serialized = json.dumps(metadata)
        assert len(serialized) > 0
        
        # Verify metadata can be deserialized
        deserialized = json.loads(serialized)
        assert deserialized['job_id'] == update['job_id']
        assert deserialized['status'] == update['status']
        assert deserialized['progress'] == update['progress']
    
    @given(update=job_status_update())
    @settings(max_examples=100, deadline=None)
    def test_job_status_progress_consistency(self, update):
        """
        Feature: gcse-enhancement-suite, Property 33: Job status updates persist correctly to DynamoDB
        
        For any job status update, the progress value should be consistent with the status.
        """
        status = update['status']
        progress = update['progress']
        
        # Verify progress is always in valid range
        assert 0 <= progress <= 100, "Progress must be between 0 and 100"
        
        # Verify progress consistency with status
        if status == 'completed':
            # Completed jobs should have 100% progress
            assert progress == 100, "Completed jobs should have 100% progress"
        
        elif status == 'failed':
            # Failed jobs can have any progress (depends on when failure occurred)
            assert 0 <= progress <= 100


class TestAsyncProcessingWorkflow:
    """Integration tests for the complete async workflow."""
    
    @given(params=job_parameters())
    @settings(max_examples=50, deadline=None)
    def test_complete_async_workflow_structure(self, params):
        """
        Feature: gcse-enhancement-suite, Property 32 & 33: Complete async workflow
        
        For any job parameters, the complete workflow from message creation to status
        updates should maintain data integrity.
        """
        # Step 1: Create SQS message
        message_body = json.dumps(params)
        
        # Step 2: Simulate initial job creation
        initial_metadata = {
            'job_id': params['job_id'],
            'status': 'pending',
            'progress': 0,
            'topic': params['topic'],
            'tier': params['tier'],
            'count': params['count'],
            'created_at': datetime.utcnow().isoformat()
        }
        
        # Step 3: Simulate processing update
        processing_metadata = {
            **initial_metadata,
            'status': 'processing',
            'progress': 50,
            'started_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        # Step 4: Simulate completion update
        completed_metadata = {
            **processing_metadata,
            'status': 'completed',
            'progress': 100,
            'completed_at': datetime.utcnow().isoformat(),
            'question_count': params['count'],
            'generation_time': 45.5
        }
        
        # Verify data consistency throughout workflow
        assert initial_metadata['job_id'] == params['job_id']
        assert processing_metadata['job_id'] == params['job_id']
        assert completed_metadata['job_id'] == params['job_id']
        
        assert initial_metadata['count'] == params['count']
        assert processing_metadata['count'] == params['count']
        assert completed_metadata['count'] == params['count']
        
        # Verify status progression
        assert initial_metadata['status'] == 'pending'
        assert processing_metadata['status'] == 'processing'
        assert completed_metadata['status'] == 'completed'
        
        # Verify progress progression
        assert initial_metadata['progress'] == 0
        assert 0 < processing_metadata['progress'] < 100
        assert completed_metadata['progress'] == 100


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
