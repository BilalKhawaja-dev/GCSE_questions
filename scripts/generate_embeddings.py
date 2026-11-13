#!/usr/bin/env python3
"""
Script to generate embeddings for existing questions in the question bank.

This script:
1. Scans the verified_question_bank DynamoDB table
2. Identifies questions without embeddings
3. Generates embeddings using Bedrock Titan Embed v2
4. Stores embeddings back in DynamoDB

Usage:
    python scripts/generate_embeddings.py [--batch-size 10] [--limit 1000] [--dry-run]
"""

import argparse
import json
import logging
import sys
import time
from typing import List, Dict
import boto3
from botocore.exceptions import ClientError

# Add parent directory to path for imports
sys.path.insert(0, '.')

from src.models.question import Question
from src.services.dedupe_service import DedupeService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generate embeddings for existing questions"""
    
    def __init__(
        self,
        table_name: str = "verified_question_bank",
        batch_size: int = 10,
        dry_run: bool = False
    ):
        """
        Initialize embedding generator.
        
        Args:
            table_name: DynamoDB table name
            batch_size: Number of questions to process at once
            dry_run: If True, don't actually store embeddings
        """
        self.table_name = table_name
        self.batch_size = batch_size
        self.dry_run = dry_run
        
        # Initialize AWS clients
        self.bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
        self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        # Initialize dedupe service
        self.dedupe_service = DedupeService(
            bedrock_client=self.bedrock,
            dynamodb_client=self.dynamodb,
            table_name=table_name
        )
        
        # Statistics
        self.stats = {
            'total_scanned': 0,
            'missing_embeddings': 0,
            'embeddings_generated': 0,
            'embeddings_stored': 0,
            'errors': 0
        }
    
    def scan_questions(self, limit: int = None) -> List[Dict]:
        """
        Scan DynamoDB table for questions.
        
        Args:
            limit: Maximum number of questions to scan
        
        Returns:
            List of question dictionaries
        """
        logger.info(f"Scanning {self.table_name} for questions...")
        
        table = self.dynamodb.Table(self.table_name)
        questions = []
        
        try:
            # Initial scan
            scan_kwargs = {
                'ProjectionExpression': 'question_id,stem,options,correct_answer,rationale,topic,grade,paper_type,difficulty,embedding'
            }
            
            if limit:
                scan_kwargs['Limit'] = limit
            
            response = table.scan(**scan_kwargs)
            questions.extend(response.get('Items', []))
            self.stats['total_scanned'] = len(questions)
            
            # Handle pagination
            while 'LastEvaluatedKey' in response:
                if limit and len(questions) >= limit:
                    break
                
                scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
                if limit:
                    scan_kwargs['Limit'] = limit - len(questions)
                
                response = table.scan(**scan_kwargs)
                questions.extend(response.get('Items', []))
                self.stats['total_scanned'] = len(questions)
                
                logger.info(f"Scanned {len(questions)} questions so far...")
            
            logger.info(f"Total questions scanned: {len(questions)}")
            return questions
            
        except ClientError as e:
            logger.error(f"Error scanning table: {e}")
            raise
    
    def filter_missing_embeddings(self, questions: List[Dict]) -> List[Dict]:
        """
        Filter questions that don't have embeddings.
        
        Args:
            questions: List of question dictionaries
        
        Returns:
            List of questions without embeddings
        """
        missing = [q for q in questions if 'embedding' not in q or not q['embedding']]
        self.stats['missing_embeddings'] = len(missing)
        
        logger.info(
            f"Found {len(missing)} questions without embeddings "
            f"({len(missing)/len(questions)*100:.1f}%)"
        )
        
        return missing
    
    def generate_embeddings(self, questions: List[Dict]) -> Dict[str, List[float]]:
        """
        Generate embeddings for questions.
        
        Args:
            questions: List of question dictionaries
        
        Returns:
            Dictionary mapping question_id to embedding
        """
        logger.info(f"Generating embeddings for {len(questions)} questions...")
        
        # Convert to Question objects
        question_objects = []
        for q in questions:
            try:
                question = Question(
                    question_id=q['question_id'],
                    stem=q['stem'],
                    options=q.get('options', []),
                    correct_answer=q.get('correct_answer', 'A'),
                    rationale=q.get('rationale', ''),
                    topic=q.get('topic', 'unknown'),
                    grade=q.get('grade', 'foundation'),
                    paper_type=q.get('paper_type', 'P1'),
                    difficulty=q.get('difficulty', 5)
                )
                question_objects.append(question)
            except Exception as e:
                logger.error(f"Error converting question {q.get('question_id')}: {e}")
                self.stats['errors'] += 1
                continue
        
        # Generate embeddings in batches
        embeddings = self.dedupe_service.batch_generate_embeddings(
            question_objects,
            batch_size=self.batch_size
        )
        
        self.stats['embeddings_generated'] = len(embeddings)
        logger.info(f"Generated {len(embeddings)} embeddings")
        
        return embeddings
    
    def store_embeddings(self, embeddings: Dict[str, List[float]]) -> int:
        """
        Store embeddings in DynamoDB.
        
        Args:
            embeddings: Dictionary mapping question_id to embedding
        
        Returns:
            Number of embeddings successfully stored
        """
        if self.dry_run:
            logger.info(f"DRY RUN: Would store {len(embeddings)} embeddings")
            return len(embeddings)
        
        logger.info(f"Storing {len(embeddings)} embeddings...")
        
        stored_count = 0
        for question_id, embedding in embeddings.items():
            try:
                success = self.dedupe_service.store_embedding(question_id, embedding)
                if success:
                    stored_count += 1
                else:
                    self.stats['errors'] += 1
                
                # Progress update every 10 embeddings
                if stored_count % 10 == 0:
                    logger.info(f"Stored {stored_count}/{len(embeddings)} embeddings...")
                
                # Rate limiting - avoid throttling
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error storing embedding for {question_id}: {e}")
                self.stats['errors'] += 1
                continue
        
        self.stats['embeddings_stored'] = stored_count
        logger.info(f"Successfully stored {stored_count} embeddings")
        
        return stored_count
    
    def run(self, limit: int = None):
        """
        Run the embedding generation process.
        
        Args:
            limit: Maximum number of questions to process
        """
        logger.info("=" * 60)
        logger.info("Starting Embedding Generation")
        logger.info("=" * 60)
        logger.info(f"Table: {self.table_name}")
        logger.info(f"Batch size: {self.batch_size}")
        logger.info(f"Dry run: {self.dry_run}")
        if limit:
            logger.info(f"Limit: {limit}")
        logger.info("=" * 60)
        
        start_time = time.time()
        
        try:
            # Step 1: Scan questions
            questions = self.scan_questions(limit=limit)
            
            if not questions:
                logger.warning("No questions found in table")
                return
            
            # Step 2: Filter questions without embeddings
            missing = self.filter_missing_embeddings(questions)
            
            if not missing:
                logger.info("All questions already have embeddings!")
                return
            
            # Step 3: Generate embeddings
            embeddings = self.generate_embeddings(missing)
            
            if not embeddings:
                logger.warning("No embeddings were generated")
                return
            
            # Step 4: Store embeddings
            stored = self.store_embeddings(embeddings)
            
            # Print summary
            elapsed = time.time() - start_time
            self._print_summary(elapsed)
            
        except KeyboardInterrupt:
            logger.warning("\nProcess interrupted by user")
            self._print_summary(time.time() - start_time)
            sys.exit(1)
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            self._print_summary(time.time() - start_time)
            sys.exit(1)
    
    def _print_summary(self, elapsed_time: float):
        """Print summary statistics"""
        logger.info("=" * 60)
        logger.info("Embedding Generation Summary")
        logger.info("=" * 60)
        logger.info(f"Total questions scanned: {self.stats['total_scanned']}")
        logger.info(f"Questions missing embeddings: {self.stats['missing_embeddings']}")
        logger.info(f"Embeddings generated: {self.stats['embeddings_generated']}")
        logger.info(f"Embeddings stored: {self.stats['embeddings_stored']}")
        logger.info(f"Errors: {self.stats['errors']}")
        logger.info(f"Elapsed time: {elapsed_time:.1f} seconds")
        
        if self.stats['embeddings_generated'] > 0:
            rate = self.stats['embeddings_generated'] / elapsed_time
            logger.info(f"Generation rate: {rate:.2f} embeddings/second")
        
        logger.info("=" * 60)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Generate embeddings for existing questions"
    )
    parser.add_argument(
        '--table-name',
        default='verified_question_bank',
        help='DynamoDB table name (default: verified_question_bank)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=10,
        help='Number of questions to process at once (default: 10)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Maximum number of questions to process (default: all)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Generate embeddings but don\'t store them'
    )
    
    args = parser.parse_args()
    
    # Create generator
    generator = EmbeddingGenerator(
        table_name=args.table_name,
        batch_size=args.batch_size,
        dry_run=args.dry_run
    )
    
    # Run
    generator.run(limit=args.limit)


if __name__ == '__main__':
    main()
