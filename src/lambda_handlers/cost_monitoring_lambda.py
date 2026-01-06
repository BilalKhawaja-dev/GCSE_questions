"""
Cost Monitoring Lambda for GCSE Question Generator V2

This Lambda function runs periodically to monitor costs and send alerts
when thresholds are exceeded.
"""

import json
import os
from datetime import datetime
from src.services.cost_monitoring_service import cost_monitoring_service
from src.utils.logging_service import logger
from src.utils.error_handling import handle_lambda_error

def lambda_handler(event, context):
    """
    Lambda handler for cost monitoring.
    
    Args:
        event: Lambda event (can contain usage statistics)
        context: Lambda context
        
    Returns:
        Dict with monitoring results
    """
    try:
        logger.info("Starting cost monitoring Lambda execution")
        
        # Get configuration from environment variables
        sns_topic_arn = os.environ.get('SNS_TOPIC_ARN')
        if not sns_topic_arn:
            raise ValueError("SNS_TOPIC_ARN environment variable not set")
        
        # Extract usage statistics from event if provided
        usage_stats = event.get('usage_stats', {
            'questions': 100,  # Default values
            'users': 10,
            'sessions': 50
        })
        
        # Run cost monitoring cycle
        cost_monitoring_service.run_cost_monitoring_cycle(sns_topic_arn, usage_stats)
        
        # Generate cost report
        cost_report = cost_monitoring_service.generate_cost_report()
        
        response = {
            'statusCode': 200,
            'body': {
                'message': 'Cost monitoring completed successfully',
                'timestamp': datetime.utcnow().isoformat(),
                'cost_report': cost_report
            }
        }
        
        logger.info("Cost monitoring Lambda execution completed successfully")
        return response
        
    except Exception as e:
        logger.error(f"Cost monitoring Lambda failed: {str(e)}")
        return handle_lambda_error(e, "CostMonitoringError")

def scheduled_handler(event, context):
    """
    Handler for scheduled EventBridge executions.
    
    Args:
        event: EventBridge event
        context: Lambda context
        
    Returns:
        Dict with monitoring results
    """
    try:
        logger.info("Starting scheduled cost monitoring")
        
        # For scheduled executions, we need to get usage stats from DynamoDB
        usage_stats = _get_usage_statistics()
        
        # Add usage stats to event and call main handler
        event['usage_stats'] = usage_stats
        return lambda_handler(event, context)
        
    except Exception as e:
        logger.error(f"Scheduled cost monitoring failed: {str(e)}")
        return handle_lambda_error(e, "ScheduledCostMonitoringError")

def _get_usage_statistics() -> dict:
    """
    Get usage statistics from DynamoDB for cost efficiency calculations.
    
    Returns:
        Dict with usage statistics
    """
    try:
        import boto3
        from datetime import timedelta
        
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-2')
        environment = os.environ.get('ENVIRONMENT', 'dev')
        
        # Get yesterday's date for statistics
        yesterday = datetime.utcnow() - timedelta(days=1)
        date_str = yesterday.strftime('%Y-%m-%d')
        
        usage_stats = {
            'questions': 0,
            'users': 0,
            'sessions': 0
        }
        
        # Count questions generated (from sessions table)
        try:
            sessions_table = dynamodb.Table(f"{environment}-sessions")
            
            # Scan for sessions from yesterday (this is expensive but runs infrequently)
            response = sessions_table.scan(
                FilterExpression='begins_with(SK, :date)',
                ExpressionAttributeValues={':date': f'TIMESTAMP#{date_str}'}
            )
            
            total_questions = 0
            unique_users = set()
            
            for item in response['Items']:
                # Count questions in this session
                questions = item.get('generated_questions', [])
                total_questions += len(questions)
                
                # Track unique users
                user_id = item.get('user_id', '')
                if user_id:
                    unique_users.add(user_id)
            
            usage_stats['questions'] = total_questions
            usage_stats['users'] = len(unique_users)
            usage_stats['sessions'] = len(response['Items'])
            
            logger.info(f"Retrieved usage statistics: {usage_stats}")
            
        except Exception as e:
            logger.warning(f"Failed to get usage statistics from DynamoDB: {str(e)}")
            # Use default values
            usage_stats = {'questions': 100, 'users': 10, 'sessions': 50}
        
        return usage_stats
        
    except Exception as e:
        logger.error(f"Failed to get usage statistics: {str(e)}")
        return {'questions': 100, 'users': 10, 'sessions': 50}

# Handler aliases for different trigger types
handler = lambda_handler  # For manual invocations
scheduled = scheduled_handler  # For EventBridge scheduled triggers