#!/usr/bin/env python3
"""
Test population script - Generate 300 verified questions
Cost estimate: ~$1.86
"""

import boto3
import json
import time
from datetime import datetime

# Initialize clients
lambda_client = boto3.client('lambda', region_name='eu-west-2')
dynamodb = boto3.resource('dynamodb', region_name='eu-west-2')

# Configuration
BATCH_GENERATION_LAMBDA = 'gcse-question-generator-batch-generation'
TOTAL_QUESTIONS = 300
BATCH_SIZE = 10  # Generate 10 questions per batch
NUM_BATCHES = TOTAL_QUESTIONS // BATCH_SIZE

# Test topics (3 topics × 2 grades × 2 papers = 12 combinations)
TEST_COMBINATIONS = [
    ('number', 'foundation', 'P1'),
    ('number', 'foundation', 'P2'),
    ('number', 'higher', 'P1'),
    ('number', 'higher', 'P2'),
    ('algebra', 'foundation', 'P1'),
    ('algebra', 'foundation', 'P2'),
    ('algebra', 'higher', 'P1'),
    ('algebra', 'higher', 'P2'),
    ('geometry', 'foundation', 'P1'),
    ('geometry', 'foundation', 'P2'),
    ('geometry', 'higher', 'P1'),
    ('geometry', 'higher', 'P2'),
]

# 300 questions / 12 combinations = 25 questions per combination
QUESTIONS_PER_COMBO = 25

print("=" * 80)
print("Question Bank Population Test - 300 Questions")
print("=" * 80)
print(f"\nConfiguration:")
print(f"  Total questions: {TOTAL_QUESTIONS}")
print(f"  Combinations: {len(TEST_COMBINATIONS)}")
print(f"  Questions per combination: {QUESTIONS_PER_COMBO}")
print(f"  Batch size: {BATCH_SIZE}")
print(f"  Estimated cost: ~$1.86")
print(f"\nStarting population at {datetime.now().strftime('%H:%M:%S')}")
print("=" * 80)

batches_triggered = 0
start_time = time.time()

for topic, grade, paper_type in TEST_COMBINATIONS:
    print(f"\n[{topic}/{grade}/{paper_type}] Generating {QUESTIONS_PER_COMBO} questions...")
    
    # Calculate number of batches needed for this combination
    num_batches_for_combo = (QUESTIONS_PER_COMBO + BATCH_SIZE - 1) // BATCH_SIZE
    
    for batch_num in range(num_batches_for_combo):
        # Calculate how many questions in this batch
        remaining = QUESTIONS_PER_COMBO - (batch_num * BATCH_SIZE)
        batch_count = min(BATCH_SIZE, remaining)
        
        payload = {
            'topic': topic,
            'grade': grade,
            'paper_type': paper_type,
            'count': batch_count
        }
        
        try:
            response = lambda_client.invoke(
                FunctionName=BATCH_GENERATION_LAMBDA,
                InvocationType='Event',  # Async
                Payload=json.dumps(payload)
            )
            
            if response['StatusCode'] == 202:
                batches_triggered += 1
                print(f"  ✓ Batch {batch_num + 1}/{num_batches_for_combo} triggered ({batch_count} questions)")
            else:
                print(f"  ✗ Batch {batch_num + 1} failed: {response}")
        
        except Exception as e:
            print(f"  ✗ Error triggering batch: {str(e)}")
        
        # Small delay to avoid throttling
        time.sleep(0.5)

elapsed = time.time() - start_time

print("\n" + "=" * 80)
print("Population Triggered")
print("=" * 80)
print(f"  Batches triggered: {batches_triggered}")
print(f"  Total questions requested: {TOTAL_QUESTIONS}")
print(f"  Time elapsed: {elapsed:.1f}s")
print(f"\nVerification will take 5-10 minutes.")
print(f"Monitor progress:")
print(f"  aws logs tail /aws/lambda/gcse-question-generator-batch-generation --follow")
print(f"  aws logs tail /aws/lambda/gcse-question-generator-verification --follow")
print(f"\nCheck results:")
print(f"  aws dynamodb scan --table-name gcse-generator-v2-verified-questions-prod --select COUNT")
print(f"  aws dynamodb scan --table-name gcse-generator-v2-rejected-questions-prod --select COUNT")
