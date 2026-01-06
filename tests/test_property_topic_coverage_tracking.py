"""
Property-based tests for topic coverage tracking functionality.

Tests the universal properties that should hold for all topic coverage operations,
ensuring data isolation per user and proper recording of coverage statistics.
"""

import pytest
import time
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, settings, HealthCheck
from moto import mock_aws
import boto3

from src.services.topic_coverage_service import TopicCoverageService


# Test data generators
@st.composite
def user_id_strategy(draw):
    """Generate valid user IDs."""
    username = draw(st.text(min_size=3, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    return f"USER#{username}"


@st.composite
def topic_strategy(draw):
    """Generate valid topic names."""
    topics = [
        'fractions', 'decimals', 'percentages', 'ratio-proportion',
        'algebra', 'linear-equations', 'quadratic-equations', 'simultaneous-equations',
        'geometry', 'area-perimeter', 'pythagoras', 'trigonometry',
        'statistics', 'probability', 'graphs', 'sequences'
    ]
    return draw(st.sampled_from(topics))


@st.composite
def subtopic_strategy(draw):
    """Generate valid subtopic names."""
    subtopics = [
        'addition', 'subtraction', 'multiplication', 'division',
        'simplification', 'solving', 'graphing', 'analysis',
        'basic', 'intermediate', 'advanced', 'applications'
    ]
    return draw(st.sampled_from(subtopics))


@pytest.fixture
def mock_dynamodb_table():
    """Create a mock DynamoDB table for testing."""
    with mock_aws():
        # Create DynamoDB resource
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-2')
        
        # Create the table
        table = dynamodb.create_table(
            TableName='test-topic-coverage',
            KeySchema=[
                {'AttributeName': 'pk', 'KeyType': 'HASH'},
                {'AttributeName': 'sk', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'pk', 'AttributeType': 'S'},
                {'AttributeName': 'sk', 'AttributeType': 'S'},
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
                {'AttributeName': 'topic', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'UserCoverageIndex',
                    'KeySchema': [
                        {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                        {'AttributeName': 'sk', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                },
                {
                    'IndexName': 'TopicPopularityIndex',
                    'KeySchema': [
                        {'AttributeName': 'topic', 'KeyType': 'HASH'},
                        {'AttributeName': 'sk', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        
        # Wait for table to be created
        table.wait_until_exists()
        
        yield table


@pytest.fixture
def topic_coverage_service(mock_dynamodb_table):
    """Create TopicCoverageService instance with mock table."""
    return TopicCoverageService(region='eu-west-2', table_name='test-topic-coverage')


class TestTopicCoverageTracking:
    """Test class for topic coverage tracking properties."""
    
    @given(
        user_id=user_id_strategy(),
        topic=topic_strategy(),
        subtopic=subtopic_strategy(),
        question_count=st.integers(min_value=1, max_value=100)
    )
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_topic_coverage_recording_property(self, topic_coverage_service, user_id, topic, subtopic, question_count):
        """
        Feature: gcse-question-generator-v2, Property 17: Topic Coverage Tracking
        For any question generation session, the system should record topic coverage data 
        in the TopicCoverage DynamoDB table with user isolation.
        
        **Validates: Requirements 13.1, 13.4, 13.5**
        """
        # Clear any existing data from the table to prevent contamination
        table = topic_coverage_service.table
        scan_response = table.scan()
        with table.batch_writer() as batch:
            for item in scan_response['Items']:
                batch.delete_item(Key={'pk': item['pk'], 'sk': item['sk']})
        
        # Arrange
        session_id = f"session_{int(time.time())}"
        request_id = f"req_{int(time.time())}"
        
        # Act - Record topic coverage
        result = topic_coverage_service.record_topic_coverage(
            user_id=user_id,
            topic=topic,
            subtopic=subtopic,
            question_count=question_count,
            session_id=session_id,
            request_id=request_id
        )
        
        # Assert - Coverage should be recorded successfully
        assert result is True, f"Topic coverage recording should succeed for user {user_id}, topic {topic}"
        
        # Verify data was stored by retrieving coverage stats
        coverage_stats = topic_coverage_service.get_user_coverage_stats(user_id, days=1, request_id=request_id)
        
        # Assert - Coverage stats should contain the recorded data
        assert coverage_stats['total_questions'] >= question_count, \
            f"Total questions should include recorded count {question_count}"
        assert topic in coverage_stats['coverage_stats'], \
            f"Topic {topic} should appear in coverage stats"
        assert coverage_stats['coverage_stats'][topic]['count'] >= question_count, \
            f"Topic count should include recorded questions {question_count}"
        assert subtopic in coverage_stats['coverage_stats'][topic]['subtopics'], \
            f"Subtopic {subtopic} should appear in topic coverage"
    
    @given(
        user_ids=st.lists(user_id_strategy(), min_size=2, max_size=5, unique=True),
        topic=topic_strategy(),
        subtopic=subtopic_strategy(),
        question_count=st.integers(min_value=1, max_value=20)
    )
    @settings(max_examples=50, deadline=15000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_user_data_isolation_property(self, topic_coverage_service, user_ids, topic, subtopic, question_count):
        """
        Feature: gcse-question-generator-v2, Property 17: Topic Coverage Tracking
        For any set of users, topic coverage data should be isolated per user,
        ensuring no cross-user data contamination.
        
        **Validates: Requirements 13.4, 13.5**
        """
        # Clear any existing data from the table to prevent contamination
        table = topic_coverage_service.table
        scan_response = table.scan()
        with table.batch_writer() as batch:
            for item in scan_response['Items']:
                batch.delete_item(Key={'pk': item['pk'], 'sk': item['sk']})
        
        # Arrange - Record coverage for each user
        for user_id in user_ids:
            result = topic_coverage_service.record_topic_coverage(
                user_id=user_id,
                topic=topic,
                subtopic=subtopic,
                question_count=question_count,
                session_id=f"session_{user_id}",
                request_id=f"req_{user_id}"
            )
            assert result is True, f"Coverage recording should succeed for user {user_id}"
        
        # Act & Assert - Verify each user's data is isolated
        for user_id in user_ids:
            coverage_stats = topic_coverage_service.get_user_coverage_stats(user_id, days=1)
            
            # Each user should have exactly their own data
            assert coverage_stats['total_questions'] == question_count, \
                f"User {user_id} should have exactly {question_count} questions, not data from other users"
            assert topic in coverage_stats['coverage_stats'], \
                f"User {user_id} should have coverage for topic {topic}"
            assert coverage_stats['coverage_stats'][topic]['count'] == question_count, \
                f"User {user_id} should have exactly {question_count} questions for topic {topic}"
    
    @given(
        user_id=user_id_strategy(),
        topics_and_counts=st.lists(
            st.tuples(topic_strategy(), subtopic_strategy(), st.integers(min_value=1, max_value=10)),
            min_size=1, max_size=10
        )
    )
    @settings(max_examples=50, deadline=15000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_coverage_aggregation_property(self, topic_coverage_service, user_id, topics_and_counts):
        """
        Feature: gcse-question-generator-v2, Property 17: Topic Coverage Tracking
        For any user with multiple topic coverage entries, the system should correctly
        aggregate question counts and maintain accurate statistics.
        
        **Validates: Requirements 13.1, 13.4**
        """
        # Clear any existing data from the table to prevent contamination
        table = topic_coverage_service.table
        scan_response = table.scan()
        with table.batch_writer() as batch:
            for item in scan_response['Items']:
                batch.delete_item(Key={'pk': item['pk'], 'sk': item['sk']})
        
        # Arrange - Record multiple coverage entries
        expected_total = 0
        expected_topics = {}
        
        for topic, subtopic, question_count in topics_and_counts:
            result = topic_coverage_service.record_topic_coverage(
                user_id=user_id,
                topic=topic,
                subtopic=subtopic,
                question_count=question_count,
                session_id=f"session_{topic}_{subtopic}",
                request_id=f"req_{topic}_{subtopic}"
            )
            assert result is True, f"Coverage recording should succeed for {topic}/{subtopic}"
            
            expected_total += question_count
            if topic not in expected_topics:
                expected_topics[topic] = 0
            expected_topics[topic] += question_count
        
        # Act - Get aggregated coverage stats
        coverage_stats = topic_coverage_service.get_user_coverage_stats(user_id, days=1)
        
        # Assert - Totals should match expected aggregation
        assert coverage_stats['total_questions'] == expected_total, \
            f"Total questions should be {expected_total}, got {coverage_stats['total_questions']}"
        
        # Assert - Each topic total should match expected
        for expected_topic, expected_count in expected_topics.items():
            assert expected_topic in coverage_stats['coverage_stats'], \
                f"Topic {expected_topic} should appear in coverage stats"
            assert coverage_stats['coverage_stats'][expected_topic]['count'] == expected_count, \
                f"Topic {expected_topic} should have {expected_count} questions"
    
    @given(
        user_id=user_id_strategy(),
        topic=topic_strategy(),
        subtopic=subtopic_strategy(),
        question_count=st.integers(min_value=1, max_value=20),
        days_back=st.integers(min_value=1, max_value=60)
    )
    @settings(max_examples=50, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_time_based_filtering_property(self, topic_coverage_service, user_id, topic, subtopic, question_count, days_back):
        """
        Feature: gcse-question-generator-v2, Property 17: Topic Coverage Tracking
        For any time period filter, the system should only return coverage data
        within the specified time range.
        
        **Validates: Requirements 13.1**
        """
        # Clear any existing data from the table to prevent contamination
        table = topic_coverage_service.table
        scan_response = table.scan()
        with table.batch_writer() as batch:
            for item in scan_response['Items']:
                batch.delete_item(Key={'pk': item['pk'], 'sk': item['sk']})
        
        # Arrange - Record coverage
        result = topic_coverage_service.record_topic_coverage(
            user_id=user_id,
            topic=topic,
            subtopic=subtopic,
            question_count=question_count,
            session_id=f"session_{topic}",
            request_id=f"req_{topic}"
        )
        assert result is True, "Coverage recording should succeed"
        
        # Act - Get coverage stats for different time periods
        recent_stats = topic_coverage_service.get_user_coverage_stats(user_id, days=days_back)
        very_old_stats = topic_coverage_service.get_user_coverage_stats(user_id, days=0)  # Should return nothing
        
        # Assert - Recent period should include the data
        if days_back >= 1:  # Data was just recorded, so should be included in recent periods
            assert recent_stats['total_questions'] >= question_count, \
                f"Recent stats ({days_back} days) should include recorded questions"
            assert topic in recent_stats['coverage_stats'], \
                f"Recent stats should include topic {topic}"
        
        # Assert - Zero-day period should return no data
        assert very_old_stats['total_questions'] == 0, \
            "Zero-day period should return no coverage data"
        assert len(very_old_stats['coverage_stats']) == 0, \
            "Zero-day period should return empty coverage stats"


class TestTopicSuggestions:
    """Test class for topic suggestion properties."""
    
    @given(
        user_id=user_id_strategy(),
        covered_topics=st.lists(topic_strategy(), min_size=1, max_size=5, unique=True),
        max_suggestions=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=30, deadline=15000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_topic_suggestion_prioritization_property(self, topic_coverage_service, user_id, covered_topics, max_suggestions):
        """
        Feature: gcse-question-generator-v2, Property 18: Topic Suggestion Prioritization
        For any user requesting topic suggestions, the system should prioritize topics
        with the lowest recent coverage based on their TopicCoverage history.
        
        **Validates: Requirements 13.3, 13.6**
        """
        # Arrange - Record coverage for some topics (making them less likely to be suggested)
        for topic in covered_topics:
            result = topic_coverage_service.record_topic_coverage(
                user_id=user_id,
                topic=topic,
                subtopic='general',
                question_count=10,  # High count to make them less likely suggestions
                session_id=f"session_{topic}",
                request_id=f"req_{topic}"
            )
            assert result is True, f"Coverage recording should succeed for topic {topic}"
        
        # Act - Get topic suggestions
        suggestions = topic_coverage_service.get_suggested_topics(
            user_id=user_id,
            days=30,
            max_suggestions=max_suggestions,
            request_id="test_suggestions"
        )
        
        # Assert - Should return suggestions
        assert isinstance(suggestions, list), "Suggestions should be returned as a list"
        assert len(suggestions) <= max_suggestions, \
            f"Should return at most {max_suggestions} suggestions, got {len(suggestions)}"
        
        # Assert - Suggestions should prioritize uncovered topics
        # (Topics that were heavily covered should be less likely to appear in suggestions)
        covered_in_suggestions = sum(1 for topic in suggestions if topic in covered_topics)
        uncovered_in_suggestions = len(suggestions) - covered_in_suggestions
        
        # If there are uncovered topics available, they should be prioritized
        if len(suggestions) > 0:
            # At least some suggestions should be for uncovered topics (unless all topics are covered)
            total_available_topics = 20  # Approximate number of topics in the system
            uncovered_topics_available = total_available_topics - len(covered_topics)
            
            if uncovered_topics_available > 0:
                assert uncovered_in_suggestions > 0, \
                    "Should suggest at least some uncovered topics when available"
    
    @given(
        user_id=user_id_strategy(),
        max_suggestions=st.integers(min_value=1, max_value=15)
    )
    @settings(max_examples=30, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_suggestion_count_limit_property(self, topic_coverage_service, user_id, max_suggestions):
        """
        Feature: gcse-question-generator-v2, Property 18: Topic Suggestion Prioritization
        For any max_suggestions parameter, the system should return at most that many suggestions.
        
        **Validates: Requirements 13.3**
        """
        # Act - Get topic suggestions
        suggestions = topic_coverage_service.get_suggested_topics(
            user_id=user_id,
            days=30,
            max_suggestions=max_suggestions,
            request_id="test_count_limit"
        )
        
        # Assert - Should respect the limit
        assert isinstance(suggestions, list), "Suggestions should be returned as a list"
        assert len(suggestions) <= max_suggestions, \
            f"Should return at most {max_suggestions} suggestions, got {len(suggestions)}"
        
        # Assert - All suggestions should be unique
        assert len(suggestions) == len(set(suggestions)), \
            "All suggestions should be unique topics"
        
        # Assert - All suggestions should be valid topic names
        for suggestion in suggestions:
            assert isinstance(suggestion, str), f"Suggestion should be a string, got {type(suggestion)}"
            assert len(suggestion) > 0, "Suggestion should not be empty"