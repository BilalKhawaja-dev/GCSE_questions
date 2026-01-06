"""
Cost Monitoring Service for GCSE Question Generator V2

This service monitors AWS costs and provides cost analysis and alerting
to ensure the system stays within budget constraints.
"""

import boto3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from src.services.metrics_service import metrics_service
from src.utils.logging_service import logger

class CostMonitoringService:
    """Service for monitoring and analyzing AWS costs."""
    
    def __init__(self):
        """Initialize the cost monitoring service."""
        self.ce_client = boto3.client('ce', region_name='us-east-1')  # Cost Explorer is in us-east-1
        self.cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')  # Billing metrics in us-east-1
        self.sns = boto3.client('sns', region_name='eu-west-2')
        
        # Cost targets for V2 (in USD)
        self.daily_target = 1.33  # $40/month = $1.33/day
        self.monthly_target = 40.0
        self.bedrock_daily_target = 0.75  # $22.5/month for Bedrock
        self.dynamodb_daily_target = 0.50  # $15/month for DynamoDB
        
    def get_current_month_costs(self) -> Dict[str, float]:
        """
        Get current month costs broken down by service.
        
        Returns:
            Dict mapping service names to costs in USD
        """
        try:
            # Get first day of current month
            now = datetime.utcnow()
            start_date = now.replace(day=1).strftime('%Y-%m-%d')
            end_date = now.strftime('%Y-%m-%d')
            
            response = self.ce_client.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date,
                    'End': end_date
                },
                Granularity='MONTHLY',
                Metrics=['BlendedCost'],
                GroupBy=[
                    {
                        'Type': 'DIMENSION',
                        'Key': 'SERVICE'
                    }
                ]
            )
            
            costs = {}
            for result in response['ResultsByTime']:
                for group in result['Groups']:
                    service_name = group['Keys'][0]
                    cost = float(group['Metrics']['BlendedCost']['Amount'])
                    costs[service_name] = cost
            
            logger.debug(f"Current month costs: {costs}")
            return costs
            
        except Exception as e:
            logger.error(f"Failed to get current month costs: {str(e)}")
            return {}
    
    def get_daily_costs(self, days: int = 7) -> Dict[str, List[Tuple[str, float]]]:
        """
        Get daily costs for the last N days broken down by service.
        
        Args:
            days: Number of days to retrieve
            
        Returns:
            Dict mapping service names to list of (date, cost) tuples
        """
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            response = self.ce_client.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity='DAILY',
                Metrics=['BlendedCost'],
                GroupBy=[
                    {
                        'Type': 'DIMENSION',
                        'Key': 'SERVICE'
                    }
                ]
            )
            
            daily_costs = {}
            for result in response['ResultsByTime']:
                date = result['TimePeriod']['Start']
                for group in result['Groups']:
                    service_name = group['Keys'][0]
                    cost = float(group['Metrics']['BlendedCost']['Amount'])
                    
                    if service_name not in daily_costs:
                        daily_costs[service_name] = []
                    daily_costs[service_name].append((date, cost))
            
            logger.debug(f"Daily costs for {days} days: {len(daily_costs)} services")
            return daily_costs
            
        except Exception as e:
            logger.error(f"Failed to get daily costs: {str(e)}")
            return {}
    
    def get_bedrock_usage_costs(self) -> Dict[str, float]:
        """
        Get detailed Bedrock usage and costs.
        
        Returns:
            Dict with Bedrock cost breakdown
        """
        try:
            # Get current month Bedrock costs
            now = datetime.utcnow()
            start_date = now.replace(day=1).strftime('%Y-%m-%d')
            end_date = now.strftime('%Y-%m-%d')
            
            response = self.ce_client.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date,
                    'End': end_date
                },
                Granularity='MONTHLY',
                Metrics=['BlendedCost', 'UsageQuantity'],
                GroupBy=[
                    {
                        'Type': 'DIMENSION',
                        'Key': 'USAGE_TYPE'
                    }
                ],
                Filter={
                    'Dimensions': {
                        'Key': 'SERVICE',
                        'Values': ['Amazon Bedrock']
                    }
                }
            )
            
            bedrock_costs = {
                'total_cost': 0.0,
                'haiku_cost': 0.0,
                'sonnet_cost': 0.0,
                'total_tokens': 0
            }
            
            for result in response['ResultsByTime']:
                for group in result['Groups']:
                    usage_type = group['Keys'][0]
                    cost = float(group['Metrics']['BlendedCost']['Amount'])
                    usage = float(group['Metrics']['UsageQuantity']['Amount'])
                    
                    bedrock_costs['total_cost'] += cost
                    
                    if 'haiku' in usage_type.lower():
                        bedrock_costs['haiku_cost'] += cost
                    elif 'sonnet' in usage_type.lower():
                        bedrock_costs['sonnet_cost'] += cost
                    
                    # Estimate tokens (rough approximation)
                    if 'input' in usage_type.lower() or 'output' in usage_type.lower():
                        bedrock_costs['total_tokens'] += usage
            
            logger.debug(f"Bedrock costs: {bedrock_costs}")
            return bedrock_costs
            
        except Exception as e:
            logger.error(f"Failed to get Bedrock costs: {str(e)}")
            return {'total_cost': 0.0, 'haiku_cost': 0.0, 'sonnet_cost': 0.0, 'total_tokens': 0}
    
    def calculate_cost_efficiency_metrics(self, costs: Dict[str, float], 
                                        usage_stats: Dict[str, int]) -> Dict[str, float]:
        """
        Calculate cost efficiency metrics.
        
        Args:
            costs: Service costs in USD
            usage_stats: Usage statistics (questions, users, sessions)
            
        Returns:
            Dict with cost efficiency metrics
        """
        total_cost = sum(costs.values())
        
        efficiency_metrics = {
            'total_daily_cost': total_cost,
            'cost_per_question': 0.0,
            'cost_per_user': 0.0,
            'cost_per_session': 0.0,
            'questions_per_dollar': 0.0,
            'users_per_dollar': 0.0,
            'sessions_per_dollar': 0.0
        }
        
        if total_cost > 0:
            if usage_stats.get('questions', 0) > 0:
                efficiency_metrics['cost_per_question'] = total_cost / usage_stats['questions']
                efficiency_metrics['questions_per_dollar'] = usage_stats['questions'] / total_cost
            
            if usage_stats.get('users', 0) > 0:
                efficiency_metrics['cost_per_user'] = total_cost / usage_stats['users']
                efficiency_metrics['users_per_dollar'] = usage_stats['users'] / total_cost
            
            if usage_stats.get('sessions', 0) > 0:
                efficiency_metrics['cost_per_session'] = total_cost / usage_stats['sessions']
                efficiency_metrics['sessions_per_dollar'] = usage_stats['sessions'] / total_cost
        
        return efficiency_metrics
    
    def check_cost_thresholds(self, current_costs: Dict[str, float]) -> List[Dict[str, str]]:
        """
        Check if current costs exceed defined thresholds.
        
        Args:
            current_costs: Current costs by service
            
        Returns:
            List of threshold violations
        """
        violations = []
        total_cost = sum(current_costs.values())
        
        # Check daily total cost
        if total_cost > self.daily_target:
            violations.append({
                'type': 'daily_total',
                'threshold': self.daily_target,
                'actual': total_cost,
                'message': f"Daily cost ${total_cost:.2f} exceeds target ${self.daily_target:.2f}"
            })
        
        # Check Bedrock costs
        bedrock_cost = current_costs.get('Amazon Bedrock', 0.0)
        if bedrock_cost > self.bedrock_daily_target:
            violations.append({
                'type': 'bedrock_daily',
                'threshold': self.bedrock_daily_target,
                'actual': bedrock_cost,
                'message': f"Bedrock daily cost ${bedrock_cost:.2f} exceeds target ${self.bedrock_daily_target:.2f}"
            })
        
        # Check DynamoDB costs
        dynamodb_cost = current_costs.get('Amazon DynamoDB', 0.0)
        if dynamodb_cost > self.dynamodb_daily_target:
            violations.append({
                'type': 'dynamodb_daily',
                'threshold': self.dynamodb_daily_target,
                'actual': dynamodb_cost,
                'message': f"DynamoDB daily cost ${dynamodb_cost:.2f} exceeds target ${self.dynamodb_daily_target:.2f}"
            })
        
        return violations
    
    def send_cost_alert(self, violations: List[Dict[str, str]], sns_topic_arn: str):
        """
        Send cost alert notifications.
        
        Args:
            violations: List of cost threshold violations
            sns_topic_arn: SNS topic ARN for alerts
        """
        if not violations:
            return
        
        try:
            message_lines = ["GCSE Question Generator - Cost Alert", ""]
            
            for violation in violations:
                message_lines.append(f"• {violation['message']}")
                message_lines.append(f"  Threshold: ${violation['threshold']:.2f}")
                message_lines.append(f"  Actual: ${violation['actual']:.2f}")
                message_lines.append("")
            
            message_lines.append("Please review usage and consider cost optimization measures.")
            message_lines.append(f"Timestamp: {datetime.utcnow().isoformat()}Z")
            
            message = "\n".join(message_lines)
            
            self.sns.publish(
                TopicArn=sns_topic_arn,
                Subject="GCSE Question Generator - Cost Alert",
                Message=message
            )
            
            logger.warning(f"Sent cost alert for {len(violations)} violations")
            
        except Exception as e:
            logger.error(f"Failed to send cost alert: {str(e)}")
    
    def publish_cost_metrics(self, costs: Dict[str, float], efficiency_metrics: Dict[str, float]):
        """
        Publish cost metrics to CloudWatch.
        
        Args:
            costs: Service costs
            efficiency_metrics: Cost efficiency metrics
        """
        try:
            # Publish service costs
            cost_metrics = []
            for service, cost in costs.items():
                cost_metrics.append({
                    'name': 'DailyCost',
                    'value': cost,
                    'unit': 'None',
                    'dimensions': {'Service': service}
                })
            
            if cost_metrics:
                metrics_service.put_multiple_metrics('Costs', cost_metrics)
            
            # Publish efficiency metrics
            metrics_service.record_cost_efficiency(
                efficiency_metrics['cost_per_question'],
                efficiency_metrics['cost_per_user'],
                efficiency_metrics['cost_per_session']
            )
            
            # Publish total cost metric
            total_cost = sum(costs.values())
            metrics_service.put_metric('Costs', 'TotalDailyCost', total_cost, 'None')
            
            logger.debug("Published cost metrics to CloudWatch")
            
        except Exception as e:
            logger.error(f"Failed to publish cost metrics: {str(e)}")
    
    def generate_cost_report(self, days: int = 30) -> Dict:
        """
        Generate a comprehensive cost report.
        
        Args:
            days: Number of days to include in the report
            
        Returns:
            Dict containing cost report data
        """
        try:
            # Get current month costs
            monthly_costs = self.get_current_month_costs()
            
            # Get daily costs
            daily_costs = self.get_daily_costs(days)
            
            # Get Bedrock details
            bedrock_costs = self.get_bedrock_usage_costs()
            
            # Calculate trends
            total_monthly = sum(monthly_costs.values())
            days_in_month = datetime.utcnow().day
            projected_monthly = (total_monthly / days_in_month) * 30
            
            report = {
                'timestamp': datetime.utcnow().isoformat(),
                'current_month': {
                    'total_cost': total_monthly,
                    'projected_monthly': projected_monthly,
                    'days_elapsed': days_in_month,
                    'costs_by_service': monthly_costs
                },
                'bedrock_details': bedrock_costs,
                'daily_trends': daily_costs,
                'budget_status': {
                    'monthly_target': self.monthly_target,
                    'projected_vs_target': projected_monthly / self.monthly_target * 100,
                    'on_track': projected_monthly <= self.monthly_target
                }
            }
            
            logger.info(f"Generated cost report: ${total_monthly:.2f} current, ${projected_monthly:.2f} projected")
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate cost report: {str(e)}")
            return {}
    
    def run_cost_monitoring_cycle(self, sns_topic_arn: str, usage_stats: Dict[str, int] = None):
        """
        Run a complete cost monitoring cycle.
        
        Args:
            sns_topic_arn: SNS topic ARN for alerts
            usage_stats: Optional usage statistics for efficiency calculations
        """
        logger.info("Starting cost monitoring cycle")
        
        try:
            # Get current costs
            daily_costs = self.get_daily_costs(1)  # Get today's costs
            
            # Extract today's costs by service
            today_costs = {}
            for service, cost_data in daily_costs.items():
                if cost_data:
                    today_costs[service] = cost_data[-1][1]  # Get the latest cost
            
            # Check thresholds
            violations = self.check_cost_thresholds(today_costs)
            
            # Send alerts if needed
            if violations:
                self.send_cost_alert(violations, sns_topic_arn)
            
            # Calculate efficiency metrics
            default_usage = {'questions': 100, 'users': 10, 'sessions': 50}
            efficiency_metrics = self.calculate_cost_efficiency_metrics(
                today_costs, usage_stats or default_usage
            )
            
            # Publish metrics
            self.publish_cost_metrics(today_costs, efficiency_metrics)
            
            # Generate and log report
            report = self.generate_cost_report()
            if report:
                logger.info(f"Cost monitoring summary: "
                          f"Current: ${report['current_month']['total_cost']:.2f}, "
                          f"Projected: ${report['current_month']['projected_monthly']:.2f}, "
                          f"Target: ${self.monthly_target:.2f}")
            
            logger.info("Cost monitoring cycle completed successfully")
            
        except Exception as e:
            logger.error(f"Cost monitoring cycle failed: {str(e)}")
            raise


# Global instance
cost_monitoring_service = CostMonitoringService()

if __name__ == "__main__":
    # Run cost monitoring when script is executed directly
    import sys
    
    # Example usage
    sns_topic = "arn:aws:sns:eu-west-2:123456789012:gcse-alerts-dev"
    usage_stats = {'questions': 150, 'users': 12, 'sessions': 75}
    
    cost_monitoring_service.run_cost_monitoring_cycle(sns_topic, usage_stats)