"""
Scaling Monitoring Service for GCSE Question Generator V2

This service monitors auto-scaling behavior and provides insights
into scaling patterns and optimization opportunities.
"""

import boto3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from src.services.metrics_service import metrics_service
from src.utils.logging_service import logger

class ScalingMonitoringService:
    """Service for monitoring and analyzing auto-scaling behavior."""
    
    def __init__(self, region: str = 'eu-west-2'):
        """
        Initialize the scaling monitoring service.
        
        Args:
            region: AWS region for services
        """
        self.region = region
        self.cloudwatch = boto3.client('cloudwatch', region_name=region)
        self.application_autoscaling = boto3.client('application-autoscaling', region_name=region)
        self.dynamodb = boto3.client('dynamodb', region_name=region)
        
    def get_dynamodb_scaling_activities(self, table_name: str, 
                                      hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get DynamoDB scaling activities for a table.
        
        Args:
            table_name: Name of the DynamoDB table
            hours: Number of hours to look back
            
        Returns:
            List of scaling activities
        """
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)
            
            # Get scaling activities for read capacity
            read_activities = self.application_autoscaling.describe_scaling_activities(
                ServiceNamespace='dynamodb',
                ResourceId=f'table/{table_name}',
                ScalableDimension='dynamodb:table:ReadCapacityUnits',
                MaxResults=50
            )
            
            # Get scaling activities for write capacity
            write_activities = self.application_autoscaling.describe_scaling_activities(
                ServiceNamespace='dynamodb',
                ResourceId=f'table/{table_name}',
                ScalableDimension='dynamodb:table:WriteCapacityUnits',
                MaxResults=50
            )
            
            # Combine and filter activities
            all_activities = []
            
            for activity in read_activities.get('ScalingActivities', []):
                if activity['StartTime'] >= start_time:
                    activity['CapacityType'] = 'Read'
                    all_activities.append(activity)
            
            for activity in write_activities.get('ScalingActivities', []):
                if activity['StartTime'] >= start_time:
                    activity['CapacityType'] = 'Write'
                    all_activities.append(activity)
            
            # Sort by start time
            all_activities.sort(key=lambda x: x['StartTime'], reverse=True)
            
            logger.debug(f"Retrieved {len(all_activities)} scaling activities for {table_name}")
            return all_activities
            
        except Exception as e:
            logger.error(f"Failed to get scaling activities for {table_name}: {str(e)}")
            return []
    
    def get_capacity_utilization_metrics(self, table_name: str, 
                                       hours: int = 24) -> Dict[str, Any]:
        """
        Get capacity utilization metrics for a DynamoDB table.
        
        Args:
            table_name: Name of the DynamoDB table
            hours: Number of hours to analyze
            
        Returns:
            Dict with utilization metrics
        """
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)
            
            # Get consumed capacity metrics
            read_consumed = self._get_cloudwatch_metric_data(
                'AWS/DynamoDB', 'ConsumedReadCapacityUnits',
                {'TableName': table_name}, start_time, end_time, 'Average'
            )
            
            write_consumed = self._get_cloudwatch_metric_data(
                'AWS/DynamoDB', 'ConsumedWriteCapacityUnits',
                {'TableName': table_name}, start_time, end_time, 'Average'
            )
            
            # Get provisioned capacity metrics
            read_provisioned = self._get_cloudwatch_metric_data(
                'AWS/DynamoDB', 'ProvisionedReadCapacityUnits',
                {'TableName': table_name}, start_time, end_time, 'Average'
            )
            
            write_provisioned = self._get_cloudwatch_metric_data(
                'AWS/DynamoDB', 'ProvisionedWriteCapacityUnits',
                {'TableName': table_name}, start_time, end_time, 'Average'
            )
            
            # Calculate utilization percentages
            read_utilization = []
            write_utilization = []
            
            for i, consumed in enumerate(read_consumed):
                if i < len(read_provisioned) and read_provisioned[i] > 0:
                    utilization = (consumed / read_provisioned[i]) * 100
                    read_utilization.append(utilization)
            
            for i, consumed in enumerate(write_consumed):
                if i < len(write_provisioned) and write_provisioned[i] > 0:
                    utilization = (consumed / write_provisioned[i]) * 100
                    write_utilization.append(utilization)
            
            metrics = {
                'table_name': table_name,
                'time_period_hours': hours,
                'read_metrics': {
                    'avg_consumed': sum(read_consumed) / len(read_consumed) if read_consumed else 0,
                    'max_consumed': max(read_consumed) if read_consumed else 0,
                    'avg_provisioned': sum(read_provisioned) / len(read_provisioned) if read_provisioned else 0,
                    'avg_utilization_percent': sum(read_utilization) / len(read_utilization) if read_utilization else 0,
                    'max_utilization_percent': max(read_utilization) if read_utilization else 0
                },
                'write_metrics': {
                    'avg_consumed': sum(write_consumed) / len(write_consumed) if write_consumed else 0,
                    'max_consumed': max(write_consumed) if write_consumed else 0,
                    'avg_provisioned': sum(write_provisioned) / len(write_provisioned) if write_provisioned else 0,
                    'avg_utilization_percent': sum(write_utilization) / len(write_utilization) if write_utilization else 0,
                    'max_utilization_percent': max(write_utilization) if write_utilization else 0
                }
            }
            
            logger.debug(f"Calculated utilization metrics for {table_name}")
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get utilization metrics for {table_name}: {str(e)}")
            return {
                'table_name': table_name,
                'error': str(e),
                'read_metrics': {},
                'write_metrics': {}
            }
    
    def analyze_scaling_patterns(self, table_names: List[str], 
                               hours: int = 168) -> Dict[str, Any]:  # 7 days default
        """
        Analyze scaling patterns across multiple tables.
        
        Args:
            table_names: List of DynamoDB table names
            hours: Number of hours to analyze
            
        Returns:
            Dict with scaling pattern analysis
        """
        logger.info(f"Analyzing scaling patterns for {len(table_names)} tables over {hours} hours")
        
        analysis = {
            'analysis_period_hours': hours,
            'tables_analyzed': len(table_names),
            'table_analyses': {},
            'overall_patterns': {
                'total_scaling_events': 0,
                'scale_out_events': 0,
                'scale_in_events': 0,
                'most_active_table': '',
                'avg_utilization_percent': 0
            }
        }
        
        total_scaling_events = 0
        scale_out_events = 0
        scale_in_events = 0
        most_active_table = ''
        max_activities = 0
        total_utilization = 0
        
        for table_name in table_names:
            try:
                # Get scaling activities
                activities = self.get_dynamodb_scaling_activities(table_name, hours)
                
                # Get utilization metrics
                utilization = self.get_capacity_utilization_metrics(table_name, hours)
                
                # Analyze activities
                table_scale_out = 0
                table_scale_in = 0
                
                for activity in activities:
                    if 'scale out' in activity.get('Description', '').lower():
                        table_scale_out += 1
                    elif 'scale in' in activity.get('Description', '').lower():
                        table_scale_in += 1
                
                table_analysis = {
                    'total_activities': len(activities),
                    'scale_out_events': table_scale_out,
                    'scale_in_events': table_scale_in,
                    'utilization_metrics': utilization,
                    'scaling_efficiency': self._calculate_scaling_efficiency(activities, utilization),
                    'recommendations': self._generate_scaling_recommendations(activities, utilization)
                }
                
                analysis['table_analyses'][table_name] = table_analysis
                
                # Update overall statistics
                total_scaling_events += len(activities)
                scale_out_events += table_scale_out
                scale_in_events += table_scale_in
                
                if len(activities) > max_activities:
                    max_activities = len(activities)
                    most_active_table = table_name
                
                # Add to total utilization
                read_util = utilization.get('read_metrics', {}).get('avg_utilization_percent', 0)
                write_util = utilization.get('write_metrics', {}).get('avg_utilization_percent', 0)
                total_utilization += (read_util + write_util) / 2
                
            except Exception as e:
                logger.error(f"Failed to analyze scaling for {table_name}: {str(e)}")
                analysis['table_analyses'][table_name] = {'error': str(e)}
        
        # Calculate overall patterns
        analysis['overall_patterns']['total_scaling_events'] = total_scaling_events
        analysis['overall_patterns']['scale_out_events'] = scale_out_events
        analysis['overall_patterns']['scale_in_events'] = scale_in_events
        analysis['overall_patterns']['most_active_table'] = most_active_table
        analysis['overall_patterns']['avg_utilization_percent'] = total_utilization / len(table_names) if table_names else 0
        
        logger.info(f"Scaling pattern analysis completed: {total_scaling_events} total events")
        return analysis
    
    def _calculate_scaling_efficiency(self, activities: List[Dict], 
                                    utilization: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate scaling efficiency metrics.
        
        Args:
            activities: List of scaling activities
            utilization: Utilization metrics
            
        Returns:
            Dict with efficiency metrics
        """
        if not activities:
            return {'efficiency_score': 100.0, 'unnecessary_scaling_events': 0}
        
        # Simple efficiency calculation based on utilization
        read_util = utilization.get('read_metrics', {}).get('avg_utilization_percent', 0)
        write_util = utilization.get('write_metrics', {}).get('avg_utilization_percent', 0)
        avg_util = (read_util + write_util) / 2
        
        # Efficiency score: higher utilization = more efficient
        # Target utilization is 70%, so score based on how close we are
        target_utilization = 70.0
        efficiency_score = 100 - abs(avg_util - target_utilization)
        efficiency_score = max(0, min(100, efficiency_score))
        
        # Count potentially unnecessary scaling events (rapid scale out/in)
        unnecessary_events = 0
        for i in range(1, len(activities)):
            current = activities[i]
            previous = activities[i-1]
            
            # If scale out followed quickly by scale in (within 1 hour)
            time_diff = abs((current['StartTime'] - previous['StartTime']).total_seconds())
            if time_diff < 3600:  # 1 hour
                if ('scale out' in current.get('Description', '').lower() and 
                    'scale in' in previous.get('Description', '').lower()) or \
                   ('scale in' in current.get('Description', '').lower() and 
                    'scale out' in previous.get('Description', '').lower()):
                    unnecessary_events += 1
        
        return {
            'efficiency_score': efficiency_score,
            'unnecessary_scaling_events': unnecessary_events
        }
    
    def _generate_scaling_recommendations(self, activities: List[Dict], 
                                        utilization: Dict[str, Any]) -> List[str]:
        """
        Generate scaling optimization recommendations.
        
        Args:
            activities: List of scaling activities
            utilization: Utilization metrics
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        read_util = utilization.get('read_metrics', {}).get('avg_utilization_percent', 0)
        write_util = utilization.get('write_metrics', {}).get('avg_utilization_percent', 0)
        
        # Low utilization recommendations
        if read_util < 30:
            recommendations.append("Consider reducing minimum read capacity - current utilization is low")
        
        if write_util < 30:
            recommendations.append("Consider reducing minimum write capacity - current utilization is low")
        
        # High utilization recommendations
        if read_util > 85:
            recommendations.append("Consider increasing maximum read capacity - utilization is high")
        
        if write_util > 85:
            recommendations.append("Consider increasing maximum write capacity - utilization is high")
        
        # Scaling frequency recommendations
        if len(activities) > 20:  # More than 20 scaling events
            recommendations.append("High scaling frequency detected - consider adjusting scaling thresholds")
        
        # Efficiency recommendations
        efficiency = self._calculate_scaling_efficiency(activities, utilization)
        if efficiency['efficiency_score'] < 70:
            recommendations.append("Scaling efficiency is low - review target utilization settings")
        
        if efficiency['unnecessary_scaling_events'] > 5:
            recommendations.append("Multiple rapid scale out/in events detected - consider longer cooldown periods")
        
        if not recommendations:
            recommendations.append("Scaling configuration appears optimal")
        
        return recommendations
    
    def _get_cloudwatch_metric_data(self, namespace: str, metric_name: str,
                                  dimensions: Dict[str, str], start_time: datetime,
                                  end_time: datetime, statistic: str) -> List[float]:
        """
        Get CloudWatch metric data points.
        
        Args:
            namespace: CloudWatch namespace
            metric_name: Name of the metric
            dimensions: Metric dimensions
            start_time: Start time for the query
            end_time: End time for the query
            statistic: Statistic to retrieve
            
        Returns:
            List of metric values
        """
        try:
            response = self.cloudwatch.get_metric_statistics(
                Namespace=namespace,
                MetricName=metric_name,
                Dimensions=[
                    {'Name': key, 'Value': value}
                    for key, value in dimensions.items()
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,  # 1 hour periods
                Statistics=[statistic]
            )
            
            datapoints = response.get('Datapoints', [])
            return [dp[statistic] for dp in sorted(datapoints, key=lambda x: x['Timestamp'])]
            
        except Exception as e:
            logger.error(f"Failed to get CloudWatch metric {metric_name}: {str(e)}")
            return []
    
    def publish_scaling_metrics(self, analysis: Dict[str, Any]):
        """
        Publish scaling analysis metrics to CloudWatch.
        
        Args:
            analysis: Scaling analysis results
        """
        try:
            # Overall scaling metrics
            metrics_service.put_metric(
                'AutoScaling',
                'TotalScalingEvents',
                analysis['overall_patterns']['total_scaling_events'],
                'Count'
            )
            
            metrics_service.put_metric(
                'AutoScaling',
                'ScaleOutEvents',
                analysis['overall_patterns']['scale_out_events'],
                'Count'
            )
            
            metrics_service.put_metric(
                'AutoScaling',
                'ScaleInEvents',
                analysis['overall_patterns']['scale_in_events'],
                'Count'
            )
            
            metrics_service.put_metric(
                'AutoScaling',
                'AverageUtilization',
                analysis['overall_patterns']['avg_utilization_percent'],
                'Percent'
            )
            
            # Per-table metrics
            for table_name, table_analysis in analysis.get('table_analyses', {}).items():
                if 'error' in table_analysis:
                    continue
                
                table_short_name = table_name.split('-')[-1] if '-' in table_name else table_name
                
                metrics_service.put_metric(
                    'AutoScaling',
                    'ScalingEvents',
                    table_analysis['total_activities'],
                    'Count',
                    dimensions={'Table': table_short_name}
                )
                
                efficiency = table_analysis.get('scaling_efficiency', {})
                if 'efficiency_score' in efficiency:
                    metrics_service.put_metric(
                        'AutoScaling',
                        'EfficiencyScore',
                        efficiency['efficiency_score'],
                        'Percent',
                        dimensions={'Table': table_short_name}
                    )
            
            logger.debug("Published scaling metrics to CloudWatch")
            
        except Exception as e:
            logger.error(f"Failed to publish scaling metrics: {str(e)}")
    
    def run_scaling_analysis(self, environment: str = 'dev') -> Dict[str, Any]:
        """
        Run a complete scaling analysis for the environment.
        
        Args:
            environment: Environment name
            
        Returns:
            Dict with analysis results
        """
        logger.info(f"Starting scaling analysis for {environment} environment")
        
        # Define table names for the environment
        table_names = [
            f"{environment}-users",
            f"{environment}-sessions",
            f"{environment}-question-feedback",
            f"{environment}-quality-scores",
            f"{environment}-topic-coverage"
        ]
        
        try:
            # Run analysis
            analysis = self.analyze_scaling_patterns(table_names, hours=168)  # 7 days
            
            # Publish metrics
            self.publish_scaling_metrics(analysis)
            
            logger.info(f"Scaling analysis completed for {environment}: "
                       f"{analysis['overall_patterns']['total_scaling_events']} total events")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Scaling analysis failed for {environment}: {str(e)}")
            raise


# Global scaling monitoring service instance
scaling_monitoring_service = ScalingMonitoringService()

if __name__ == "__main__":
    # Example usage
    import sys
    environment = sys.argv[1] if len(sys.argv) > 1 else 'dev'
    
    analysis = scaling_monitoring_service.run_scaling_analysis(environment)
    print(json.dumps(analysis, indent=2, default=str))