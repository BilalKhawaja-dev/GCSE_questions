"""
Question Bank Population Script

Generates and verifies questions for all topic/grade/paper combinations
to populate the verified question bank.

Target: 50 verified questions per combination (~30,000 total)
Accounts for verification failures by generating 1.5x
"""

import json
import logging
import os
import sys
import time
import boto3
from typing import Dict, List, Tuple
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.inventory_service import InventoryService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
lambda_client = boto3.client('lambda')

# Configuration
TOPICS = [
    'number', 'algebra', 'ratio_proportion', 
    'geometry', 'probability', 'statistics'
]
GRADES = ['foundation', 'higher']
PAPER_TYPES = ['P1', 'P2', 'P3']

TARGET_COUNT = 50
GENERATION_MULTIPLIER = 1.5  # Generate 1.5x to account for failures
BATCH_SIZE = 30  # Questions per batch
MAX_WORKERS = 5  # Parallel batch generation
CHECKPOINT_FILE = 'population_checkpoint.json'


class PopulationProgress:
    """Track population progress with checkpoint capability."""
    
    def __init__(self, checkpoint_file: str):
        self.checkpoint_file = checkpoint_file
        self.progress = self._load_checkpoint()
    
    def _load_checkpoint(self) -> Dict:
        """Load progress from checkpoint file."""
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load checkpoint: {e}")
        
        return {
            'completed_combinations': [],
            'failed_combinations': [],
            'total_generated': 0,
            'total_verified': 0,
            'start_time': datetime.utcnow().isoformat()
        }
    
    def save_checkpoint(self):
        """Save progress to checkpoint file."""
        try:
            with open(self.checkpoint_file, 'w') as f:
                json.dump(self.progress, f, indent=2)
            logger.debug("Checkpoint saved")
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
    
    def mark_completed(self, combination: str, generated: int, verified: int):
        """Mark a combination as completed."""
        self.progress['completed_combinations'].append({
            'combination': combination,
            'generated': generated,
            'verified': verified,
            'timestamp': datetime.utcnow().isoformat()
        })
        self.progress['total_generated'] += generated
        self.progress['total_verified'] += verified
        self.save_checkpoint()
    
    def mark_failed(self, combination: str, error: str):
        """Mark a combination as failed."""
        self.progress['failed_combinations'].append({
            'combination': combination,
            'error': error,
            'timestamp': datetime.utcnow().isoformat()
        })
        self.save_checkpoint()
    
    def is_completed(self, combination: str) -> bool:
        """Check if combination is already completed."""
        return any(
            c['combination'] == combination 
            for c in self.progress['completed_combinations']
        )


def populate_combination(
    topic: str,
    grade: str,
    paper_type: str,
    inventory_service: InventoryService,
    progress: PopulationProgress,
    dry_run: bool = False
) -> Tuple[int, int]:
    """
    Populate questions for a single topic/grade/paper combination.
    
    Args:
        topic: Question topic
        grade: Grade level
        paper_type: Paper type
        inventory_service: Inventory service instance
        progress: Progress tracker
        dry_run: If True, don't actually generate questions
    
    Returns:
        Tuple of (generated_count, verified_count)
    """
    combination = f"{topic}_{grade}_{paper_type}"
    
    # Check if already completed
    if progress.is_completed(combination):
        logger.info(f"Skipping {combination} (already completed)")
        return (0, 0)
    
    logger.info(f"Processing {combination}")
    
    try:
        # Check current inventory
        current_count = inventory_service.count_verified_questions(
            topic=topic,
            grade=grade,
            paper_type=paper_type
        )
        
        logger.info(f"{combination}: Current count = {current_count}")
        
        if current_count >= TARGET_COUNT:
            logger.info(f"{combination}: Already at target ({current_count}/{TARGET_COUNT})")
            progress.mark_completed(combination, 0, current_count)
            return (0, current_count)
        
        # Calculate how many to generate
        deficit = TARGET_COUNT - current_count
        to_generate = int(deficit * GENERATION_MULTIPLIER)
        
        logger.info(
            f"{combination}: Deficit = {deficit}, "
            f"Generating {to_generate} questions"
        )
        
        if dry_run:
            logger.info(f"DRY RUN: Would generate {to_generate} questions")
            return (to_generate, 0)
        
        # Generate in batches
        total_generated = 0
        batches = (to_generate + BATCH_SIZE - 1) // BATCH_SIZE
        
        for batch_num in range(batches):
            batch_count = min(BATCH_SIZE, to_generate - total_generated)
            
            logger.info(
                f"{combination}: Batch {batch_num + 1}/{batches} "
                f"({batch_count} questions)"
            )
            
            # Trigger batch generation
            success = trigger_batch_generation(
                topic=topic,
                grade=grade,
                paper_type=paper_type,
                count=batch_count
            )
            
            if success:
                total_generated += batch_count
            else:
                logger.error(f"{combination}: Batch {batch_num + 1} failed")
            
            # Small delay between batches
            time.sleep(2)
        
        # Wait for verification to complete (polling)
        logger.info(f"{combination}: Waiting for verification...")
        verified_count = wait_for_verification(
            topic=topic,
            grade=grade,
            paper_type=paper_type,
            inventory_service=inventory_service,
            initial_count=current_count,
            timeout_seconds=300
        )
        
        logger.info(
            f"{combination}: Complete - "
            f"Generated {total_generated}, Verified {verified_count}"
        )
        
        progress.mark_completed(combination, total_generated, verified_count)
        return (total_generated, verified_count)
        
    except Exception as e:
        logger.error(f"{combination}: Failed - {str(e)}", exc_info=True)
        progress.mark_failed(combination, str(e))
        return (0, 0)


def trigger_batch_generation(
    topic: str,
    grade: str,
    paper_type: str,
    count: int
) -> bool:
    """
    Trigger batch generation lambda.
    
    Args:
        topic: Question topic
        grade: Grade level
        paper_type: Paper type
        count: Number of questions to generate
    
    Returns:
        True if successful
    """
    try:
        payload = {
            'topic': topic,
            'grade': grade,
            'paper_type': paper_type,
            'count': count
        }
        
        response = lambda_client.invoke(
            FunctionName='batch_generation_lambda',
            InvocationType='Event',  # Async
            Payload=json.dumps(payload)
        )
        
        return response['StatusCode'] == 202
        
    except Exception as e:
        logger.error(f"Failed to trigger batch generation: {e}")
        return False


def wait_for_verification(
    topic: str,
    grade: str,
    paper_type: str,
    inventory_service: InventoryService,
    initial_count: int,
    timeout_seconds: int = 300
) -> int:
    """
    Wait for verification to complete by polling inventory.
    
    Args:
        topic: Question topic
        grade: Grade level
        paper_type: Paper type
        inventory_service: Inventory service instance
        initial_count: Initial verified count
        timeout_seconds: Maximum wait time
    
    Returns:
        Final verified count
    """
    start_time = time.time()
    last_count = initial_count
    
    while time.time() - start_time < timeout_seconds:
        current_count = inventory_service.count_verified_questions(
            topic=topic,
            grade=grade,
            paper_type=paper_type
        )
        
        if current_count > last_count:
            logger.info(
                f"Verification progress: {current_count - initial_count} new questions verified"
            )
            last_count = current_count
        
        # Check if we've reached target
        if current_count >= TARGET_COUNT:
            logger.info("Target reached!")
            return current_count
        
        # Wait before next poll
        time.sleep(10)
    
    logger.warning(f"Verification timeout after {timeout_seconds}s")
    return last_count


def populate_all(
    parallel: bool = True,
    max_workers: int = MAX_WORKERS,
    dry_run: bool = False
) -> Dict:
    """
    Populate questions for all combinations.
    
    Args:
        parallel: If True, process combinations in parallel
        max_workers: Maximum parallel workers
        dry_run: If True, don't actually generate questions
    
    Returns:
        Summary statistics
    """
    logger.info("Starting question bank population")
    logger.info(f"Target: {TARGET_COUNT} questions per combination")
    logger.info(f"Total combinations: {len(TOPICS) * len(GRADES) * len(PAPER_TYPES)}")
    logger.info(f"Parallel: {parallel}, Workers: {max_workers}")
    logger.info(f"Dry run: {dry_run}")
    
    # Initialize services
    inventory_service = InventoryService(
        dynamodb_resource=dynamodb,
        target_count=TARGET_COUNT
    )
    
    progress = PopulationProgress(CHECKPOINT_FILE)
    
    # Generate all combinations
    combinations = [
        (topic, grade, paper_type)
        for topic in TOPICS
        for grade in GRADES
        for paper_type in PAPER_TYPES
    ]
    
    logger.info(f"Processing {len(combinations)} combinations")
    
    results = []
    
    if parallel:
        # Parallel processing
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    populate_combination,
                    topic, grade, paper_type,
                    inventory_service, progress, dry_run
                ): (topic, grade, paper_type)
                for topic, grade, paper_type in combinations
            }
            
            for future in as_completed(futures):
                combination = futures[future]
                try:
                    generated, verified = future.result()
                    results.append({
                        'combination': '_'.join(combination),
                        'generated': generated,
                        'verified': verified
                    })
                except Exception as e:
                    logger.error(f"Combination {combination} failed: {e}")
    else:
        # Sequential processing
        for topic, grade, paper_type in combinations:
            generated, verified = populate_combination(
                topic, grade, paper_type,
                inventory_service, progress, dry_run
            )
            results.append({
                'combination': f"{topic}_{grade}_{paper_type}",
                'generated': generated,
                'verified': verified
            })
    
    # Calculate summary
    summary = {
        'total_combinations': len(combinations),
        'completed': len(progress.progress['completed_combinations']),
        'failed': len(progress.progress['failed_combinations']),
        'total_generated': progress.progress['total_generated'],
        'total_verified': progress.progress['total_verified'],
        'target_total': TARGET_COUNT * len(combinations),
        'completion_percentage': (
            progress.progress['total_verified'] / 
            (TARGET_COUNT * len(combinations)) * 100
        ),
        'results': results
    }
    
    logger.info("Population complete!")
    logger.info(f"Total generated: {summary['total_generated']}")
    logger.info(f"Total verified: {summary['total_verified']}")
    logger.info(f"Completion: {summary['completion_percentage']:.1f}%")
    
    return summary


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Populate question bank with verified questions'
    )
    parser.add_argument(
        '--parallel',
        action='store_true',
        help='Process combinations in parallel'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=MAX_WORKERS,
        help=f'Maximum parallel workers (default: {MAX_WORKERS})'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run mode (no actual generation)'
    )
    parser.add_argument(
        '--reset-checkpoint',
        action='store_true',
        help='Reset checkpoint file'
    )
    
    args = parser.parse_args()
    
    # Reset checkpoint if requested
    if args.reset_checkpoint:
        if os.path.exists(CHECKPOINT_FILE):
            os.remove(CHECKPOINT_FILE)
            logger.info("Checkpoint file reset")
    
    # Run population
    summary = populate_all(
        parallel=args.parallel,
        max_workers=args.workers,
        dry_run=args.dry_run
    )
    
    # Save summary report
    report_file = f"population_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"Report saved to {report_file}")
    
    return 0 if summary['failed'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
