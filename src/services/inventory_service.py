"""
Inventory Service for Question Bank Management

Tracks verified question counts per topic/grade/paper combination
and manages inventory thresholds for replenishment.
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import boto3
from boto3.dynamodb.conditions import Key, Attr

logger = logging.getLogger(__name__)


class InventoryService:
    """Service for managing question bank inventory."""
    
    def __init__(
        self,
        dynamodb_resource,
        verified_table_name: str = "verified_question_bank",
        inventory_table_name: str = "question_bank_inventory",
        target_count: int = 50
    ):
        """
        Initialize inventory service.
        
        Args:
            dynamodb_resource: Boto3 DynamoDB resource
            verified_table_name: Name of verified questions table
            inventory_table_name: Name of inventory tracking table
            target_count: Target number of verified questions per combination
        """
        self.dynamodb = dynamodb_resource
        self.verified_table_name = verified_table_name
        self.inventory_table_name = inventory_table_name
        self.target_count = target_count
        
        logger.info(
            f"Initialized InventoryService with target_count={target_count}"
        )
    
    def count_verified_questions(
        self,
        topic: str,
        grade: str,
        paper_type: str
    ) -> int:
        """
        Count verified questions for a specific combination.
        
        Args:
            topic: Question topic
            grade: Grade level (foundation/higher)
            paper_type: Paper type (P1/P2/P3)
        
        Returns:
            Count of verified questions
        """
        try:
            table = self.dynamodb.Table(self.verified_table_name)
            
            # Query using composite key
            topic_grade_paper = f"{topic}_{grade}_{paper_type}"
            
            # Count items with this combination
            response = table.query(
                IndexName='TopicGradePaperDifficultyIndex',
                KeyConditionExpression=Key('topic_grade_paper').eq(topic_grade_paper),
                Select='COUNT'
            )
            
            count = response.get('Count', 0)
            
            logger.debug(
                f"Counted {count} verified questions for "
                f"{topic}/{grade}/{paper_type}"
            )
            
            return count
            
        except Exception as e:
            logger.error(
                f"Failed to count verified questions: {str(e)}",
                exc_info=True
            )
            return 0
    
    def get_inventory_status(
        self,
        topic: str,
        grade: str,
        paper_type: str
    ) -> Dict:
        """
        Get inventory status for a combination.
        
        Args:
            topic: Question topic
            grade: Grade level
            paper_type: Paper type
        
        Returns:
            Dictionary with inventory details
        """
        try:
            table = self.dynamodb.Table(self.inventory_table_name)
            
            topic_grade_paper = f"{topic}_{grade}_{paper_type}"
            
            response = table.get_item(
                Key={'topic_grade_paper': topic_grade_paper}
            )
            
            if 'Item' in response:
                return response['Item']
            else:
                # No inventory record yet, create one
                return {
                    'topic_grade_paper': topic_grade_paper,
                    'verified_count': 0,
                    'target_count': self.target_count,
                    'last_replenishment': None,
                    'next_replenishment': None,
                    'generation_pass_rate': 0.0,
                    'updated_at': datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to get inventory status: {str(e)}")
            return {}
    
    def update_inventory_count(
        self,
        topic: str,
        grade: str,
        paper_type: str,
        increment: int = 1
    ) -> bool:
        """
        Update inventory count after verification.
        
        Args:
            topic: Question topic
            grade: Grade level
            paper_type: Paper type
            increment: Amount to increment (can be negative)
        
        Returns:
            True if successful
        """
        try:
            table = self.dynamodb.Table(self.inventory_table_name)
            
            topic_grade_paper = f"{topic}_{grade}_{paper_type}"
            
            # Update count
            table.update_item(
                Key={'topic_grade_paper': topic_grade_paper},
                UpdateExpression=(
                    'ADD verified_count :inc '
                    'SET updated_at = :now'
                ),
                ExpressionAttributeValues={
                    ':inc': increment,
                    ':now': datetime.utcnow().isoformat()
                }
            )
            
            logger.info(
                f"Updated inventory for {topic_grade_paper}: "
                f"increment={increment}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update inventory: {str(e)}")
            return False
    
    def get_depleted_topics(
        self,
        threshold_percentage: float = 1.0
    ) -> List[Dict]:
        """
        Get list of topic combinations below target threshold.
        
        Args:
            threshold_percentage: Percentage of target (1.0 = 100%)
        
        Returns:
            List of depleted topic combinations with details
        """
        try:
            table = self.dynamodb.Table(self.inventory_table_name)
            
            # Scan inventory table
            response = table.scan()
            items = response.get('Items', [])
            
            # Handle pagination
            while 'LastEvaluatedKey' in response:
                response = table.scan(
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                items.extend(response.get('Items', []))
            
            # Filter depleted topics
            depleted = []
            threshold = self.target_count * threshold_percentage
            
            for item in items:
                verified_count = item.get('verified_count', 0)
                target = item.get('target_count', self.target_count)
                
                if verified_count < threshold:
                    deficit = target - verified_count
                    depleted.append({
                        'topic_grade_paper': item['topic_grade_paper'],
                        'verified_count': verified_count,
                        'target_count': target,
                        'deficit': deficit,
                        'last_replenishment': item.get('last_replenishment'),
                        'generation_pass_rate': item.get('generation_pass_rate', 0.0)
                    })
            
            logger.info(
                f"Found {len(depleted)} depleted topics "
                f"(threshold={threshold})"
            )
            
            return depleted
            
        except Exception as e:
            logger.error(f"Failed to get depleted topics: {str(e)}")
            return []
    
    def update_replenishment_timestamp(
        self,
        topic: str,
        grade: str,
        paper_type: str
    ) -> bool:
        """
        Update last replenishment timestamp.
        
        Args:
            topic: Question topic
            grade: Grade level
            paper_type: Paper type
        
        Returns:
            True if successful
        """
        try:
            table = self.dynamodb.Table(self.inventory_table_name)
            
            topic_grade_paper = f"{topic}_{grade}_{paper_type}"
            now = datetime.utcnow().isoformat()
            
            table.update_item(
                Key={'topic_grade_paper': topic_grade_paper},
                UpdateExpression=(
                    'SET last_replenishment = :now, '
                    'updated_at = :now'
                ),
                ExpressionAttributeValues={
                    ':now': now
                }
            )
            
            logger.info(
                f"Updated replenishment timestamp for {topic_grade_paper}"
            )
            
            return True
            
        except Exception as e:
            logger.error(
                f"Failed to update replenishment timestamp: {str(e)}"
            )
            return False
    
    def update_pass_rate(
        self,
        topic: str,
        grade: str,
        paper_type: str,
        pass_rate: float
    ) -> bool:
        """
        Update generation pass rate for a combination.
        
        Args:
            topic: Question topic
            grade: Grade level
            paper_type: Paper type
            pass_rate: Pass rate (0.0 to 1.0)
        
        Returns:
            True if successful
        """
        try:
            table = self.dynamodb.Table(self.inventory_table_name)
            
            topic_grade_paper = f"{topic}_{grade}_{paper_type}"
            
            table.update_item(
                Key={'topic_grade_paper': topic_grade_paper},
                UpdateExpression=(
                    'SET generation_pass_rate = :rate, '
                    'updated_at = :now'
                ),
                ExpressionAttributeValues={
                    ':rate': pass_rate,
                    ':now': datetime.utcnow().isoformat()
                }
            )
            
            logger.info(
                f"Updated pass rate for {topic_grade_paper}: {pass_rate:.2%}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update pass rate: {str(e)}")
            return False
    
    def initialize_inventory(
        self,
        topics: List[str],
        grades: List[str],
        paper_types: List[str]
    ) -> int:
        """
        Initialize inventory records for all combinations.
        
        Args:
            topics: List of topics
            grades: List of grades
            paper_types: List of paper types
        
        Returns:
            Number of records created
        """
        try:
            table = self.dynamodb.Table(self.inventory_table_name)
            
            created = 0
            now = datetime.utcnow().isoformat()
            
            for topic in topics:
                for grade in grades:
                    for paper_type in paper_types:
                        topic_grade_paper = f"{topic}_{grade}_{paper_type}"
                        
                        # Check if exists
                        response = table.get_item(
                            Key={'topic_grade_paper': topic_grade_paper}
                        )
                        
                        if 'Item' not in response:
                            # Create new record
                            table.put_item(
                                Item={
                                    'topic_grade_paper': topic_grade_paper,
                                    'verified_count': 0,
                                    'target_count': self.target_count,
                                    'last_replenishment': None,
                                    'next_replenishment': None,
                                    'generation_pass_rate': 0.0,
                                    'updated_at': now
                                }
                            )
                            created += 1
            
            logger.info(f"Initialized {created} inventory records")
            return created
            
        except Exception as e:
            logger.error(f"Failed to initialize inventory: {str(e)}")
            return 0
