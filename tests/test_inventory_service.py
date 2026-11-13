"""Tests for Inventory Service."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from src.services.inventory_service import InventoryService


@pytest.fixture
def mock_dynamodb():
    """Mock DynamoDB resource."""
    dynamodb = Mock()
    
    # Mock verified questions table
    verified_table = Mock()
    verified_table.name = 'verified_question_bank'
    
    # Mock inventory table
    inventory_table = Mock()
    inventory_table.name = 'question_bank_inventory'
    
    # Configure table() to return appropriate mock
    def table_side_effect(name):
        if name == 'verified_question_bank':
            return verified_table
        elif name == 'question_bank_inventory':
            return inventory_table
        return Mock()
    
    dynamodb.Table = Mock(side_effect=table_side_effect)
    
    return dynamodb, verified_table, inventory_table


def test_count_verified_questions(mock_dynamodb):
    """Test counting verified questions for a combination."""
    dynamodb, verified_table, _ = mock_dynamodb
    
    # Mock query response
    verified_table.query.return_value = {
        'Count': 42,
        'Items': []
    }
    
    service = InventoryService(
        dynamodb_resource=dynamodb,
        verified_table_name='verified_question_bank',
        inventory_table_name='question_bank_inventory'
    )
    
    count = service.count_verified_questions(
        topic='algebra',
        grade='foundation',
        paper_type='P1'
    )
    
    assert count == 42
    verified_table.query.assert_called_once()


def test_get_inventory_status_existing(mock_dynamodb):
    """Test getting inventory status for existing record."""
    dynamodb, _, inventory_table = mock_dynamodb
    
    # Mock get_item response
    inventory_table.get_item.return_value = {
        'Item': {
            'topic_grade_paper': 'algebra_foundation_P1',
            'verified_count': 45,
            'target_count': 50,
            'generation_pass_rate': 0.67
        }
    }
    
    service = InventoryService(
        dynamodb_resource=dynamodb,
        verified_table_name='verified_question_bank',
        inventory_table_name='question_bank_inventory'
    )
    
    status = service.get_inventory_status(
        topic='algebra',
        grade='foundation',
        paper_type='P1'
    )
    
    assert status['verified_count'] == 45
    assert status['target_count'] == 50
    assert status['generation_pass_rate'] == 0.67


def test_get_inventory_status_new(mock_dynamodb):
    """Test getting inventory status for new record."""
    dynamodb, _, inventory_table = mock_dynamodb
    
    # Mock get_item response (no item)
    inventory_table.get_item.return_value = {}
    
    service = InventoryService(
        dynamodb_resource=dynamodb,
        verified_table_name='verified_question_bank',
        inventory_table_name='question_bank_inventory',
        target_count=50
    )
    
    status = service.get_inventory_status(
        topic='algebra',
        grade='foundation',
        paper_type='P1'
    )
    
    assert status['verified_count'] == 0
    assert status['target_count'] == 50
    assert 'updated_at' in status


def test_update_inventory_count(mock_dynamodb):
    """Test updating inventory count."""
    dynamodb, _, inventory_table = mock_dynamodb
    
    service = InventoryService(
        dynamodb_resource=dynamodb,
        verified_table_name='verified_question_bank',
        inventory_table_name='question_bank_inventory'
    )
    
    result = service.update_inventory_count(
        topic='algebra',
        grade='foundation',
        paper_type='P1',
        increment=1
    )
    
    assert result is True
    inventory_table.update_item.assert_called_once()


def test_get_depleted_topics(mock_dynamodb):
    """Test getting depleted topics."""
    dynamodb, _, inventory_table = mock_dynamodb
    
    # Mock scan response
    inventory_table.scan.return_value = {
        'Items': [
            {
                'topic_grade_paper': 'algebra_foundation_P1',
                'verified_count': 30,
                'target_count': 50,
                'generation_pass_rate': 0.65
            },
            {
                'topic_grade_paper': 'geometry_higher_P2',
                'verified_count': 55,
                'target_count': 50,
                'generation_pass_rate': 0.70
            },
            {
                'topic_grade_paper': 'number_foundation_P3',
                'verified_count': 10,
                'target_count': 50,
                'generation_pass_rate': 0.60
            }
        ]
    }
    
    service = InventoryService(
        dynamodb_resource=dynamodb,
        verified_table_name='verified_question_bank',
        inventory_table_name='question_bank_inventory',
        target_count=50
    )
    
    depleted = service.get_depleted_topics(threshold_percentage=1.0)
    
    # Should return 2 depleted topics (30 and 10, not 55)
    assert len(depleted) == 2
    assert depleted[0]['verified_count'] == 30
    assert depleted[0]['deficit'] == 20
    assert depleted[1]['verified_count'] == 10
    assert depleted[1]['deficit'] == 40


def test_update_replenishment_timestamp(mock_dynamodb):
    """Test updating replenishment timestamp."""
    dynamodb, _, inventory_table = mock_dynamodb
    
    service = InventoryService(
        dynamodb_resource=dynamodb,
        verified_table_name='verified_question_bank',
        inventory_table_name='question_bank_inventory'
    )
    
    result = service.update_replenishment_timestamp(
        topic='algebra',
        grade='foundation',
        paper_type='P1'
    )
    
    assert result is True
    inventory_table.update_item.assert_called_once()


def test_update_pass_rate(mock_dynamodb):
    """Test updating generation pass rate."""
    dynamodb, _, inventory_table = mock_dynamodb
    
    service = InventoryService(
        dynamodb_resource=dynamodb,
        verified_table_name='verified_question_bank',
        inventory_table_name='question_bank_inventory'
    )
    
    result = service.update_pass_rate(
        topic='algebra',
        grade='foundation',
        paper_type='P1',
        pass_rate=0.75
    )
    
    assert result is True
    inventory_table.update_item.assert_called_once()


def test_initialize_inventory(mock_dynamodb):
    """Test initializing inventory records."""
    dynamodb, _, inventory_table = mock_dynamodb
    
    # Mock get_item to return no existing items
    inventory_table.get_item.return_value = {}
    
    service = InventoryService(
        dynamodb_resource=dynamodb,
        verified_table_name='verified_question_bank',
        inventory_table_name='question_bank_inventory',
        target_count=50
    )
    
    topics = ['algebra', 'geometry']
    grades = ['foundation', 'higher']
    paper_types = ['P1', 'P2']
    
    created = service.initialize_inventory(topics, grades, paper_types)
    
    # Should create 2 * 2 * 2 = 8 records
    assert created == 8
    assert inventory_table.put_item.call_count == 8
