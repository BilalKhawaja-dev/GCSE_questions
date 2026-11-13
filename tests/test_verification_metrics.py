"""
Tests for Verification Metrics Service

Tests the CloudWatch metrics publishing functionality for the question verification system.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from src.services.verification_metrics_service import VerificationMetricsService, verification_metrics_service


class TestVerificationMetricsService:
    """Test suite for VerificationMetricsService"""
    
    @pytest.fixture
    def metrics_service(self):
        """Create a fresh metrics service instance for testing"""
        return VerificationMetricsService()
    
    @pytest.fixture
    def mock_cloudwatch(self):
        """Mock CloudWatch client"""
        with patch('boto3.client') as mock_client:
            mock_cw = MagicMock()
            mock_client.return_value = mock_cw
            yield mock_cw
    
    def test_initialization(self, metrics_service):
        """Test metrics service initializes correctly"""
        assert metrics_service.namespace == "GCSE/QuestionVerification"
        assert metrics_service.cloudwatch is not None
    
    def test_put_metric_success(self, metrics_service, mock_cloudwatch):
        """Test successfully publishing a single metric"""
        metrics_service.cloudwatch = mock_cloudwatch
        
        result = metrics_service.put_metric(
            metric_name='TestMetric',
            value=42.0,
            unit='Count',
            dimensions={'Layer': 'Test'}
        )
        
        assert result is True
        mock_cloudwatch.put_metric_data.assert_called_once()
        
        # Verify call arguments
        call_args = mock_cloudwatch.put_metric_data.call_args
        assert call_args[1]['Namespace'] == 'GCSE/QuestionVerification'
        assert call_args[1]['MetricData'][0]['MetricName'] == 'TestMetric'
        assert call_args[1]['MetricData'][0]['Value'] == 42.0
        assert call_args[1]['MetricData'][0]['Unit'] == 'Count'
    
    def test_put_metric_with_timestamp(self, metrics_service, mock_cloudwatch):
        """Test publishing metric with custom timestamp"""
        metrics_service.cloudwatch = mock_cloudwatch
        timestamp = datetime(2026, 1, 13, 12, 0, 0)
        
        result = metrics_service.put_metric(
            metric_name='TestMetric',
            value=100.0,
            timestamp=timestamp
        )
        
        assert result is True
        call_args = mock_cloudwatch.put_metric_data.call_args
        assert call_args[1]['MetricData'][0]['Timestamp'] == timestamp
    
    def test_put_metric_failure(self, metrics_service, mock_cloudwatch):
        """Test handling metric publishing failure"""
        metrics_service.cloudwatch = mock_cloudwatch
        mock_cloudwatch.put_metric_data.side_effect = Exception("CloudWatch error")
        
        result = metrics_service.put_metric(
            metric_name='TestMetric',
            value=42.0
        )
        
        assert result is False
    
    def test_put_multiple_metrics(self, metrics_service, mock_cloudwatch):
        """Test publishing multiple metrics in batch"""
        metrics_service.cloudwatch = mock_cloudwatch
        
        metrics = [
            {'name': 'Metric1', 'value': 10, 'unit': 'Count'},
            {'name': 'Metric2', 'value': 20, 'unit': 'Seconds'},
            {'name': 'Metric3', 'value': 30, 'unit': 'Percent'}
        ]
        
        result = metrics_service.put_multiple_metrics(metrics)
        
        assert result is True
        mock_cloudwatch.put_metric_data.assert_called_once()
        
        call_args = mock_cloudwatch.put_metric_data.call_args
        assert len(call_args[1]['MetricData']) == 3
    
    def test_put_multiple_metrics_batching(self, metrics_service, mock_cloudwatch):
        """Test that large metric batches are split correctly (max 20 per call)"""
        metrics_service.cloudwatch = mock_cloudwatch
        
        # Create 45 metrics (should result in 3 calls: 20, 20, 5)
        metrics = [
            {'name': f'Metric{i}', 'value': i, 'unit': 'Count'}
            for i in range(45)
        ]
        
        result = metrics_service.put_multiple_metrics(metrics)
        
        assert result is True
        assert mock_cloudwatch.put_metric_data.call_count == 3
    
    def test_record_verification_layer_result_pass(self, metrics_service, mock_cloudwatch):
        """Test recording successful verification layer result"""
        metrics_service.cloudwatch = mock_cloudwatch
        
        metrics_service.record_verification_layer_result(
            layer_name='Deterministic',
            passed=True,
            latency_ms=50.0,
            confidence=1.0
        )
        
        mock_cloudwatch.put_metric_data.assert_called_once()
        call_args = mock_cloudwatch.put_metric_data.call_args
        metric_data = call_args[1]['MetricData']
        
        # Should have 4 metrics: pass rate, latency, count, confidence
        assert len(metric_data) == 4
        
        # Check pass rate metric
        pass_rate_metric = next(m for m in metric_data if m['MetricName'] == 'VerificationPassRate')
        assert pass_rate_metric['Value'] == 100.0
        assert pass_rate_metric['Unit'] == 'Percent'
    
    def test_record_verification_layer_result_fail(self, metrics_service, mock_cloudwatch):
        """Test recording failed verification layer result"""
        metrics_service.cloudwatch = mock_cloudwatch
        
        metrics_service.record_verification_layer_result(
            layer_name='LLM',
            passed=False,
            latency_ms=5000.0,
            confidence=0.45
        )
        
        call_args = mock_cloudwatch.put_metric_data.call_args
        metric_data = call_args[1]['MetricData']
        
        # Check pass rate metric shows failure
        pass_rate_metric = next(m for m in metric_data if m['MetricName'] == 'VerificationPassRate')
        assert pass_rate_metric['Value'] == 0.0
    
    def test_record_verification_failure_reason(self, metrics_service, mock_cloudwatch):
        """Test recording specific failure reason"""
        metrics_service.cloudwatch = mock_cloudwatch
        
        metrics_service.record_verification_failure_reason(
            layer_name='SymPy',
            failure_reason='parsing_error'
        )
        
        call_args = mock_cloudwatch.put_metric_data.call_args
        metric_data = call_args[1]['MetricData'][0]
        
        assert metric_data['MetricName'] == 'VerificationFailureCount'
        assert metric_data['Value'] == 1
        assert any(d['Name'] == 'Reason' and d['Value'] == 'parsing_error' 
                  for d in metric_data['Dimensions'])
    
    def test_record_question_bank_inventory(self, metrics_service, mock_cloudwatch):
        """Test recording question bank inventory levels"""
        metrics_service.cloudwatch = mock_cloudwatch
        
        metrics_service.record_question_bank_inventory(
            topic='algebra',
            grade='foundation',
            paper_type='P1',
            verified_count=45,
            target_count=50
        )
        
        call_args = mock_cloudwatch.put_metric_data.call_args
        metric_data = call_args[1]['MetricData']
        
        # Should have 2 metrics: count and inventory level
        assert len(metric_data) == 2
        
        # Check inventory level calculation
        inventory_metric = next(m for m in metric_data if m['MetricName'] == 'InventoryLevel')
        assert inventory_metric['Value'] == 90.0  # 45/50 * 100
        assert inventory_metric['Unit'] == 'Percent'
    
    def test_record_question_bank_inventory_low(self, metrics_service, mock_cloudwatch):
        """Test recording low inventory triggers alert metric"""
        metrics_service.cloudwatch = mock_cloudwatch
        
        metrics_service.record_question_bank_inventory(
            topic='algebra',
            grade='foundation',
            paper_type='P1',
            verified_count=15,  # Below 20 threshold
            target_count=50
        )
        
        call_args = mock_cloudwatch.put_metric_data.call_args
        metric_data = call_args[1]['MetricData']
        
        # Should have 3 metrics including low inventory alert
        assert len(metric_data) == 3
        
        alert_metric = next(m for m in metric_data if m['MetricName'] == 'LowInventoryAlert')
        assert alert_metric['Value'] == 1
    
    def test_record_batch_generation_result(self, metrics_service, mock_cloudwatch):
        """Test recording batch generation results"""
        metrics_service.cloudwatch = mock_cloudwatch
        
        metrics_service.record_batch_generation_result(
            topic='algebra',
            grade='foundation',
            paper_type='P1',
            questions_generated=30,
            questions_passed=20,
            batch_duration_seconds=120.0
        )
        
        call_args = mock_cloudwatch.put_metric_data.call_args
        metric_data = call_args[1]['MetricData']
        
        # Should have 4 metrics
        assert len(metric_data) == 4
        
        # Check pass rate calculation
        pass_rate_metric = next(m for m in metric_data if m['MetricName'] == 'BatchPassRate')
        assert pass_rate_metric['Value'] == pytest.approx(66.67, rel=0.01)
    
    def test_record_retrieval_performance(self, metrics_service, mock_cloudwatch):
        """Test recording retrieval performance metrics"""
        metrics_service.cloudwatch = mock_cloudwatch
        
        metrics_service.record_retrieval_performance(
            latency_ms=75.0,
            questions_returned=5,
            topic='algebra',
            grade='foundation'
        )
        
        call_args = mock_cloudwatch.put_metric_data.call_args
        metric_data = call_args[1]['MetricData']
        
        # Should have 2 metrics: latency and questions served
        assert len(metric_data) == 2
        
        latency_metric = next(m for m in metric_data if m['MetricName'] == 'RetrievalLatency')
        assert latency_metric['Value'] == 75.0
        assert latency_metric['Unit'] == 'Milliseconds'
    
    def test_record_retrieval_performance_high_latency(self, metrics_service, mock_cloudwatch):
        """Test high latency triggers alert metric"""
        metrics_service.cloudwatch = mock_cloudwatch
        
        metrics_service.record_retrieval_performance(
            latency_ms=250.0,  # Above 200ms threshold
            questions_returned=5
        )
        
        call_args = mock_cloudwatch.put_metric_data.call_args
        metric_data = call_args[1]['MetricData']
        
        # Should have 3 metrics including high latency alert
        assert len(metric_data) == 3
        
        alert_metric = next(m for m in metric_data if m['MetricName'] == 'HighLatencyAlert')
        assert alert_metric['Value'] == 1
    
    def test_record_user_feedback(self, metrics_service, mock_cloudwatch):
        """Test recording user feedback metrics"""
        metrics_service.cloudwatch = mock_cloudwatch
        
        metrics_service.record_user_feedback(
            question_id='test-123',
            helpful=True,
            difficulty_rating=7,
            issue_reported=False
        )
        
        call_args = mock_cloudwatch.put_metric_data.call_args
        metric_data = call_args[1]['MetricData']
        
        # Should have 2 metrics: feedback count and difficulty rating
        assert len(metric_data) == 2
        
        feedback_metric = next(m for m in metric_data if m['MetricName'] == 'UserFeedbackCount')
        assert any(d['Name'] == 'Helpful' and d['Value'] == 'Yes' 
                  for d in feedback_metric['Dimensions'])
    
    def test_record_user_feedback_with_issue(self, metrics_service, mock_cloudwatch):
        """Test recording user feedback with issue report"""
        metrics_service.cloudwatch = mock_cloudwatch
        
        metrics_service.record_user_feedback(
            question_id='test-123',
            helpful=False,
            issue_reported=True
        )
        
        call_args = mock_cloudwatch.put_metric_data.call_args
        metric_data = call_args[1]['MetricData']
        
        # Should have 2 metrics including issue report count
        assert len(metric_data) == 2
        
        issue_metric = next(m for m in metric_data if m['MetricName'] == 'IssueReportCount')
        assert issue_metric['Value'] == 1
    
    def test_record_false_positive_rate(self, metrics_service, mock_cloudwatch):
        """Test recording false positive rate"""
        metrics_service.cloudwatch = mock_cloudwatch
        
        metrics_service.record_false_positive_rate(
            total_verified=1000,
            issues_reported=30
        )
        
        call_args = mock_cloudwatch.put_metric_data.call_args
        metric_data = call_args[1]['MetricData'][0]
        
        assert metric_data['MetricName'] == 'FalsePositiveRate'
        assert metric_data['Value'] == 3.0  # 30/1000 * 100
        assert metric_data['Unit'] == 'Percent'
    
    def test_record_verification_cost(self, metrics_service, mock_cloudwatch):
        """Test recording verification cost metrics"""
        metrics_service.cloudwatch = mock_cloudwatch
        
        metrics_service.record_verification_cost(
            bedrock_calls=100,
            estimated_cost_usd=0.50
        )
        
        call_args = mock_cloudwatch.put_metric_data.call_args
        metric_data = call_args[1]['MetricData']
        
        # Should have 3 metrics: calls, cost, cost per verification
        assert len(metric_data) == 3
        
        cost_per_metric = next(m for m in metric_data if m['MetricName'] == 'CostPerVerification')
        assert cost_per_metric['Value'] == 0.005  # 0.50/100
    
    def test_record_replenishment_execution(self, metrics_service, mock_cloudwatch):
        """Test recording replenishment execution metrics"""
        metrics_service.cloudwatch = mock_cloudwatch
        
        metrics_service.record_replenishment_execution(
            topics_replenished=15,
            total_questions_generated=450,
            execution_duration_seconds=300.0
        )
        
        call_args = mock_cloudwatch.put_metric_data.call_args
        metric_data = call_args[1]['MetricData']
        
        # Should have 4 metrics
        assert len(metric_data) == 4
        
        execution_metric = next(m for m in metric_data if m['MetricName'] == 'ReplenishmentExecutionCount')
        assert execution_metric['Value'] == 1
    
    def test_record_system_health(self, metrics_service, mock_cloudwatch):
        """Test recording overall system health metrics"""
        metrics_service.cloudwatch = mock_cloudwatch
        
        metrics_service.record_system_health(
            total_verified_questions=25000,
            average_pass_rate=72.5,
            average_retrieval_latency_ms=85.0
        )
        
        call_args = mock_cloudwatch.put_metric_data.call_args
        metric_data = call_args[1]['MetricData']
        
        # Should have 3 metrics
        assert len(metric_data) == 3
        
        total_metric = next(m for m in metric_data if m['MetricName'] == 'TotalVerifiedQuestions')
        assert total_metric['Value'] == 25000
    
    def test_global_instance_exists(self):
        """Test that global verification_metrics_service instance exists"""
        assert verification_metrics_service is not None
        assert isinstance(verification_metrics_service, VerificationMetricsService)


class TestMetricsIntegration:
    """Integration tests for metrics service (requires AWS credentials)"""
    
    @pytest.mark.integration
    def test_publish_real_metric(self):
        """Test publishing a real metric to CloudWatch (integration test)"""
        service = VerificationMetricsService()
        
        result = service.put_metric(
            metric_name='TestMetric',
            value=1.0,
            unit='Count',
            dimensions={'Test': 'Integration'}
        )
        
        # Should succeed if AWS credentials are configured
        assert result is True
    
    @pytest.mark.integration
    def test_publish_verification_metrics(self):
        """Test publishing verification metrics (integration test)"""
        service = VerificationMetricsService()
        
        service.record_verification_layer_result(
            layer_name='Test',
            passed=True,
            latency_ms=100.0,
            confidence=0.95
        )
        
        # Should not raise exception
        assert True
