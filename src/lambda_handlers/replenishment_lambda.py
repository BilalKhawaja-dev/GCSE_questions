"""
Replenishment Lambda - Cron-based Question Bank Replenishment

Triggered by EventBridge schedule (weekly) to check inventory and trigger
batch generation for depleted topics.
"""

import json
import logging
import os
import boto3
from typing import Dict, List, Any

from src.services.inventory_service import InventoryService

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
lambda_client = boto3.client('lambda')

# Environment variables
VERIFIED_TABLE = os.environ.get('VERIFIED_QUESTION_BANK_TABLE', 'verified_question_bank')
INVENTORY_TABLE = os.environ.get('QUESTION_BANK_INVENTORY_TABLE', 'question_bank_inventory')
BATCH_GENERATION_LAMBDA = os.environ.get('BATCH_GENERATION_LAMBDA', 'batch_generation_lambda')
TARGET_COUNT = int(os.environ.get('TARGET_QUESTION_COUNT', '50'))

# Initialize inventory service
inventory_service = InventoryService(
    dynamodb_resource=dynamodb,
    verified_table_name=VERIFIED_TABLE,
    inventory_table_name=INVENTORY_TABLE,
    target_count=TARGET_COUNT
)

# Edexcel GCSE topics (from gradeBasedTopics.ts)
TOPICS = [
    'number', 'algebra', 'ratio_proportion', 'geometry', 'probability', 'statistics'
]

GRADES = ['foundation', 'higher']
PAPER_TYPES = ['P1', 'P2', 'P3']


def handler(event, context):
    """
    Replenishment Lambda handler.
    
    Checks inventory for all topic/grade/paper combinations and triggers
    batch generation for depleted topics.
    
    Args:
        event: EventBridge event (cron trigger)
        context: Lambda context
    
    Returns:
        Response with replenishment summary
    """
    logger.info("Starting question bank replenishment check")
    logger.info(f"Target count per combination: {TARGET_COUNT}")
    
    try:
        # Get depleted topics (below target threshold)
        depleted_topics = inventory_service.get_depleted_topics(
            threshold_percentage=1.0  # 100% of target
        )
        
        logger.info(f"Found {len(depleted_topics)} depleted topic combinations")
        
        if not depleted_topics:
            logger.info("No depleted topics found. Question bank is healthy!")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'No replenishment needed',
                    'depleted_count': 0,
                    'triggered_batches': 0
                })
            }
        
        # Trigger batch generation for each depleted topic
        triggered_batches = []
        failed_batches = []
        
        for depleted in depleted_topics:
            try:
                # Parse topic_grade_paper
                parts = depleted['topic_grade_paper'].split('_')
                if len(parts) < 3:
                    logger.error(f"Invalid topic_grade_paper format: {depleted['topic_grade_paper']}")
                    continue
                
                # Handle topics with underscores (e.g., ratio_proportion)
                paper_type = parts[-1]
                grade = parts[-2]
                topic = '_'.join(parts[:-2])
                
                deficit = depleted['deficit']
                
                # Generate 1.5x deficit to account for verification failures
                # Minimum 10, maximum 50 per batch
                batch_size = max(10, min(50, int(deficit * 1.5)))
                
                logger.info(
                    f"Triggering batch generation for {topic}/{grade}/{paper_type}: "
                    f"deficit={deficit}, batch_size={batch_size}"
                )
                
                # Invoke batch generation lambda
                response = trigger_batch_generation(
                    topic=topic,
                    grade=grade,
                    paper_type=paper_type,
                    count=batch_size
                )
                
                triggered_batches.append({
                    'topic': topic,
                    'grade': grade,
                    'paper_type': paper_type,
                    'batch_size': batch_size,
                    'deficit': deficit
                })
                
                # Update replenishment timestamp
                inventory_service.update_replenishment_timestamp(
                    topic=topic,
                    grade=grade,
                    paper_type=paper_type
                )
                
            except Exception as e:
                logger.error(
                    f"Failed to trigger batch for {depleted['topic_grade_paper']}: {str(e)}",
                    exc_info=True
                )
                failed_batches.append({
                    'topic_grade_paper': depleted['topic_grade_paper'],
                    'error': str(e)
                })
        
        # Log summary
        logger.info(
            f"Replenishment complete: "
            f"triggered={len(triggered_batches)}, "
            f"failed={len(failed_batches)}"
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Replenishment triggered',
                'depleted_count': len(depleted_topics),
                'triggered_batches': len(triggered_batches),
                'failed_batches': len(failed_batches),
                'batches': triggered_batches,
                'failures': failed_batches
            })
        }
        
    except Exception as e:
        logger.error(f"Replenishment lambda failed: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }


def trigger_batch_generation(
    topic: str,
    grade: str,
    paper_type: str,
    count: int
) -> Dict[str, Any]:
    """
    Trigger batch generation lambda for a topic combination.
    
    Args:
        topic: Question topic
        grade: Grade level
        paper_type: Paper type
        count: Number of questions to generate
    
    Returns:
        Lambda invocation response
    """
    payload = {
        'topic': topic,
        'grade': grade,
        'paper_type': paper_type,
        'count': count
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName=BATCH_GENERATION_LAMBDA,
            InvocationType='Event',  # Async invocation
            Payload=json.dumps(payload)
        )
        
        logger.info(
            f"Triggered batch generation: {topic}/{grade}/{paper_type} "
            f"(count={count})"
        )
        
        return {
            'statusCode': response['StatusCode'],
            'payload': payload
        }
        
    except Exception as e:
        logger.error(f"Failed to invoke batch generation lambda: {str(e)}")
        raise
