"""
Lambda Warming Function for GCSE Question Generator V2

This Lambda function runs on a schedule to warm other Lambda functions
and reduce cold start times.
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, List
from src.services.lambda_warming_service import lambda_warming_service
from src.services.metrics_service import metrics_service
from src.utils.logging_service import logger
from src.utils.error_handling import handle_lambda_error

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for warming other Lambda functions.
    
    Args:
        event: Lambda event (can contain function list and configuration)
        context: Lambda context
        
    Returns:
        Dict with warming results
    """
    try:
        logger.info("Starting Lambda warming cycle")
        
        # Get environment configuration
        environment = os.environ.get('ENVIRONMENT', 'dev')
        
        # Get function list from event or use default
        functions_to_warm = event.get('functions', _get_default_functions(environment))
        concurrent_executions = event.get('concurrent_executions', 2)
        
        logger.info(f"Warming {len(functions_to_warm)} functions with {concurrent_executions} concurrent executions each")
        
        # Warm the functions
        warming_results = lambda_warming_service.warm_multiple_functions(
            functions_to_warm, 
            concurrent_executions
        )
        
        # Publish metrics
        _publish_warming_metrics(warming_results)
        
        # Analyze effectiveness if requested
        analysis = None
        if event.get('analyze_effectiveness', False):
            analysis = lambda_warming_service.analyze_warming_effectiveness(functions_to_warm)
            _publish_effectiveness_metrics(analysis)
        
        response = {
            'statusCode': 200,
            'body': {
                'message': 'Lambda warming completed successfully',
                'timestamp': datetime.utcnow().isoformat(),
                'warming_results': warming_results,
                'effectiveness_analysis': analysis
            }
        }
        
        logger.info(f"Lambda warming completed: "
                   f"{warming_results['successful_functions']}/{warming_results['total_functions']} functions warmed successfully")
        
        return response
        
    except Exception as e:
        logger.error(f"Lambda warming failed: {str(e)}")
        return handle_lambda_error(e, "LambdaWarmingError")

def scheduled_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handler for scheduled EventBridge executions.
    
    Args:
        event: EventBridge event
        context: Lambda context
        
    Returns:
        Dict with warming results
    """
    try:
        logger.info("Starting scheduled Lambda warming")
        
        # Add default configuration for scheduled runs
        event.update({
            'concurrent_executions': 2,
            'analyze_effectiveness': False  # Skip analysis for regular warming
        })
        
        return lambda_handler(event, context)
        
    except Exception as e:
        logger.error(f"Scheduled Lambda warming failed: {str(e)}")
        return handle_lambda_error(e, "ScheduledLambdaWarmingError")

def analysis_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handler for warming effectiveness analysis (runs less frequently).
    
    Args:
        event: Lambda event
        context: Lambda context
        
    Returns:
        Dict with analysis results
    """
    try:
        logger.info("Starting Lambda warming effectiveness analysis")
        
        environment = os.environ.get('ENVIRONMENT', 'dev')
        functions_to_analyze = event.get('functions', _get_default_functions(environment))
        analysis_hours = event.get('hours', 24)
        
        # Analyze effectiveness
        analysis = lambda_warming_service.analyze_warming_effectiveness(
            functions_to_analyze, 
            analysis_hours
        )
        
        # Publish effectiveness metrics
        _publish_effectiveness_metrics(analysis)
        
        response = {
            'statusCode': 200,
            'body': {
                'message': 'Lambda warming analysis completed successfully',
                'timestamp': datetime.utcnow().isoformat(),
                'analysis': analysis
            }
        }
        
        logger.info(f"Lambda warming analysis completed: "
                   f"{analysis['effectiveness_score']:.1f}% effectiveness score")
        
        return response
        
    except Exception as e:
        logger.error(f"Lambda warming analysis failed: {str(e)}")
        return handle_lambda_error(e, "LambdaWarmingAnalysisError")

def _get_default_functions(environment: str) -> List[str]:
    """
    Get the default list of functions to warm for the environment.
    
    Args:
        environment: Environment name (dev, prod, etc.)
        
    Returns:
        List of Lambda function names
    """
    return [
        f"gcse-interpret-lambda-{environment}",
        f"gcse-generate-lambda-{environment}",
        f"gcse-auth-lambda-{environment}",
        f"gcse-feedback-lambda-{environment}",
        f"gcse-session-lambda-{environment}",
        f"gcse-export-lambda-{environment}",
        f"gcse-topic-coverage-lambda-{environment}"
        # Note: Don't warm refinement-lambda as it runs infrequently
        # Note: Don't warm warming-lambda (this function) to avoid recursion
    ]

def _publish_warming_metrics(warming_results: Dict[str, Any]):
    """
    Publish warming metrics to CloudWatch.
    
    Args:
        warming_results: Results from warming operation
    """
    try:
        # Overall warming metrics
        metrics_service.put_metric(
            'LambdaWarming', 
            'SuccessfulFunctions', 
            warming_results['successful_functions'], 
            'Count'
        )
        
        metrics_service.put_metric(
            'LambdaWarming', 
            'FailedFunctions', 
            warming_results['failed_functions'], 
            'Count'
        )
        
        metrics_service.put_metric(
            'LambdaWarming', 
            'WarmingDuration', 
            warming_results['total_duration_ms'] / 1000, 
            'Seconds'
        )
        
        # Per-function metrics
        for function_name, result in warming_results.get('function_results', {}).items():
            function_short_name = function_name.split('-')[-2] if '-' in function_name else function_name
            
            metrics_service.put_metric(
                'LambdaWarming',
                'SuccessfulInvocations',
                result['successful_invocations'],
                'Count',
                dimensions={'Function': function_short_name}
            )
            
            metrics_service.put_metric(
                'LambdaWarming',
                'FailedInvocations',
                result['failed_invocations'],
                'Count',
                dimensions={'Function': function_short_name}
            )
        
        logger.debug("Published warming metrics to CloudWatch")
        
    except Exception as e:
        logger.error(f"Failed to publish warming metrics: {str(e)}")

def _publish_effectiveness_metrics(analysis: Dict[str, Any]):
    """
    Publish warming effectiveness metrics to CloudWatch.
    
    Args:
        analysis: Effectiveness analysis results
    """
    try:
        # Overall effectiveness metrics
        metrics_service.put_metric(
            'LambdaWarming',
            'EffectivenessScore',
            analysis['effectiveness_score'],
            'Percent'
        )
        
        metrics_service.put_metric(
            'LambdaWarming',
            'TotalColdStarts',
            analysis['overall_metrics']['total_cold_starts'],
            'Count'
        )
        
        metrics_service.put_metric(
            'LambdaWarming',
            'FunctionsWithColdStarts',
            analysis['overall_metrics']['functions_with_cold_starts'],
            'Count'
        )
        
        if analysis['overall_metrics']['avg_init_duration_ms'] > 0:
            metrics_service.put_metric(
                'LambdaWarming',
                'AverageInitDuration',
                analysis['overall_metrics']['avg_init_duration_ms'],
                'Milliseconds'
            )
        
        # Per-function cold start metrics
        for function_name, metrics in analysis.get('function_metrics', {}).items():
            function_short_name = function_name.split('-')[-2] if '-' in function_name else function_name
            
            metrics_service.put_metric(
                'LambdaWarming',
                'ColdStarts',
                metrics['cold_starts'],
                'Count',
                dimensions={'Function': function_short_name}
            )
            
            if metrics['avg_init_duration_ms'] > 0:
                metrics_service.put_metric(
                    'LambdaWarming',
                    'InitDuration',
                    metrics['avg_init_duration_ms'],
                    'Milliseconds',
                    dimensions={'Function': function_short_name}
                )
        
        logger.debug("Published effectiveness metrics to CloudWatch")
        
    except Exception as e:
        logger.error(f"Failed to publish effectiveness metrics: {str(e)}")

# Handler aliases for different trigger types
handler = lambda_handler  # For manual invocations
scheduled = scheduled_handler  # For EventBridge scheduled triggers
analysis = analysis_handler  # For effectiveness analysis