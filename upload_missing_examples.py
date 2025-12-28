#!/usr/bin/env python3
"""
Upload missing example content for GCSE topics.
This script creates and uploads example questions for topics that are missing from the examples bucket.
"""

import json
import boto3
import logging
from datetime import datetime
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# AWS Configuration
EXAMPLES_BUCKET = 'gcse-examples-prod-1a64dc99'
AWS_REGION = 'eu-west-2'

def create_geometry_examples() -> Dict[str, Any]:
    """Create example questions for geometry topics."""
    return {
        "domain": "geometry",
        "subtopic": "angles",
        "tier": "foundation",
        "total_examples": 4,
        "average_quality_score": 0.91,
        "examples": [
            {
                "question": {
                    "id": "geo_f001",
                    "question_text": "Find the missing angle in this triangle. Two angles are 45° and 60°.",
                    "marks": 2,
                    "tier": "foundation",
                    "topic": "geometry"
                },
                "mark_scheme": {
                    "answer": "75°",
                    "method": ["Sum of angles in triangle = 180°", "180° - 45° - 60° = 75°"],
                    "marks_breakdown": [
                        {"step": "Identify triangle angle sum", "marks": 1},
                        {"step": "Calculate missing angle", "marks": 1}
                    ]
                },
                "quality_score": 0.92
            },
            {
                "question": {
                    "id": "geo_f002", 
                    "question_text": "Calculate angle x when two parallel lines are cut by a transversal. One angle is 65°.",
                    "marks": 2,
                    "tier": "foundation",
                    "topic": "geometry"
                },
                "mark_scheme": {
                    "answer": "65°",
                    "method": ["Corresponding angles are equal", "x = 65°"],
                    "marks_breakdown": [
                        {"step": "Identify angle relationship", "marks": 1},
                        {"step": "State angle value", "marks": 1}
                    ]
                },
                "quality_score": 0.89
            },
            {
                "question": {
                    "id": "geo_f003",
                    "question_text": "Find the area of a rectangle with length 8 cm and width 5 cm.",
                    "marks": 2,
                    "tier": "foundation", 
                    "topic": "geometry"
                },
                "mark_scheme": {
                    "answer": "40 cm²",
                    "method": ["Area = length × width", "Area = 8 × 5 = 40 cm²"],
                    "marks_breakdown": [
                        {"step": "Use correct formula", "marks": 1},
                        {"step": "Calculate correctly", "marks": 1}
                    ]
                },
                "quality_score": 0.93
            },
            {
                "question": {
                    "id": "geo_f004",
                    "question_text": "Calculate the perimeter of a square with side length 7 cm.",
                    "marks": 2,
                    "tier": "foundation",
                    "topic": "geometry"
                },
                "mark_scheme": {
                    "answer": "28 cm",
                    "method": ["Perimeter = 4 × side length", "Perimeter = 4 × 7 = 28 cm"],
                    "marks_breakdown": [
                        {"step": "Use correct formula", "marks": 1},
                        {"step": "Calculate correctly", "marks": 1}
                    ]
                },
                "quality_score": 0.90
            }
        ]
    }

def create_statistics_examples() -> Dict[str, Any]:
    """Create example questions for statistics topics."""
    return {
        "domain": "statistics",
        "subtopic": "data-analysis", 
        "tier": "foundation",
        "total_examples": 3,
        "average_quality_score": 0.88,
        "examples": [
            {
                "question": {
                    "id": "stat_f001",
                    "question_text": "Find the mean of these numbers: 4, 7, 9, 12, 8",
                    "marks": 2,
                    "tier": "foundation",
                    "topic": "statistics"
                },
                "mark_scheme": {
                    "answer": "8",
                    "method": ["Sum = 4 + 7 + 9 + 12 + 8 = 40", "Mean = 40 ÷ 5 = 8"],
                    "marks_breakdown": [
                        {"step": "Calculate sum correctly", "marks": 1},
                        {"step": "Divide by number of values", "marks": 1}
                    ]
                },
                "quality_score": 0.91
            },
            {
                "question": {
                    "id": "stat_f002",
                    "question_text": "Find the median of these numbers: 3, 8, 5, 12, 7, 9, 6",
                    "marks": 3,
                    "tier": "foundation",
                    "topic": "statistics"
                },
                "mark_scheme": {
                    "answer": "7",
                    "method": ["Arrange in order: 3, 5, 6, 7, 8, 9, 12", "Middle value = 7"],
                    "marks_breakdown": [
                        {"step": "Arrange in ascending order", "marks": 2},
                        {"step": "Identify middle value", "marks": 1}
                    ]
                },
                "quality_score": 0.87
            },
            {
                "question": {
                    "id": "stat_f003",
                    "question_text": "Find the range of these test scores: 65, 78, 82, 59, 91, 73",
                    "marks": 2,
                    "tier": "foundation",
                    "topic": "statistics"
                },
                "mark_scheme": {
                    "answer": "32",
                    "method": ["Highest = 91, Lowest = 59", "Range = 91 - 59 = 32"],
                    "marks_breakdown": [
                        {"step": "Identify highest and lowest", "marks": 1},
                        {"step": "Calculate difference", "marks": 1}
                    ]
                },
                "quality_score": 0.86
            }
        ]
    }

def create_probability_examples() -> Dict[str, Any]:
    """Create example questions for probability topics."""
    return {
        "domain": "probability",
        "subtopic": "basic-probability",
        "tier": "foundation", 
        "total_examples": 3,
        "average_quality_score": 0.89,
        "examples": [
            {
                "question": {
                    "id": "prob_f001",
                    "question_text": "A fair dice is rolled. What is the probability of getting an even number?",
                    "marks": 2,
                    "tier": "foundation",
                    "topic": "probability"
                },
                "mark_scheme": {
                    "answer": "1/2 or 0.5",
                    "method": ["Even numbers: 2, 4, 6 (3 outcomes)", "Total outcomes: 6", "P(even) = 3/6 = 1/2"],
                    "marks_breakdown": [
                        {"step": "Identify favorable outcomes", "marks": 1},
                        {"step": "Calculate probability", "marks": 1}
                    ]
                },
                "quality_score": 0.92
            },
            {
                "question": {
                    "id": "prob_f002",
                    "question_text": "A bag contains 5 red balls and 3 blue balls. What is the probability of drawing a red ball?",
                    "marks": 2,
                    "tier": "foundation",
                    "topic": "probability"
                },
                "mark_scheme": {
                    "answer": "5/8",
                    "method": ["Red balls: 5", "Total balls: 5 + 3 = 8", "P(red) = 5/8"],
                    "marks_breakdown": [
                        {"step": "Count total outcomes", "marks": 1},
                        {"step": "Calculate probability", "marks": 1}
                    ]
                },
                "quality_score": 0.88
            },
            {
                "question": {
                    "id": "prob_f003",
                    "question_text": "A spinner has 4 equal sections: red, blue, green, yellow. What is the probability of NOT getting red?",
                    "marks": 2,
                    "tier": "foundation",
                    "topic": "probability"
                },
                "mark_scheme": {
                    "answer": "3/4",
                    "method": ["Non-red sections: blue, green, yellow (3 sections)", "P(not red) = 3/4"],
                    "marks_breakdown": [
                        {"step": "Identify non-red outcomes", "marks": 1},
                        {"step": "Calculate probability", "marks": 1}
                    ]
                },
                "quality_score": 0.87
            }
        ]
    }

def create_ratio_examples() -> Dict[str, Any]:
    """Create example questions for ratio topics."""
    return {
        "domain": "ratio",
        "subtopic": "ratio-proportion",
        "tier": "foundation",
        "total_examples": 3,
        "average_quality_score": 0.90,
        "examples": [
            {
                "question": {
                    "id": "ratio_f001",
                    "question_text": "Share £60 in the ratio 2:3. How much does each person get?",
                    "marks": 3,
                    "tier": "foundation",
                    "topic": "ratio"
                },
                "mark_scheme": {
                    "answer": "£24 and £36",
                    "method": ["Total parts = 2 + 3 = 5", "Each part = £60 ÷ 5 = £12", "Person 1: 2 × £12 = £24", "Person 2: 3 × £12 = £36"],
                    "marks_breakdown": [
                        {"step": "Find total parts", "marks": 1},
                        {"step": "Calculate value per part", "marks": 1},
                        {"step": "Calculate each share", "marks": 1}
                    ]
                },
                "quality_score": 0.91
            },
            {
                "question": {
                    "id": "ratio_f002",
                    "question_text": "The ratio of boys to girls in a class is 3:4. If there are 12 boys, how many girls are there?",
                    "marks": 2,
                    "tier": "foundation",
                    "topic": "ratio"
                },
                "mark_scheme": {
                    "answer": "16 girls",
                    "method": ["3 parts = 12 boys", "1 part = 12 ÷ 3 = 4", "Girls = 4 parts = 4 × 4 = 16"],
                    "marks_breakdown": [
                        {"step": "Find value of one part", "marks": 1},
                        {"step": "Calculate number of girls", "marks": 1}
                    ]
                },
                "quality_score": 0.89
            },
            {
                "question": {
                    "id": "ratio_f003",
                    "question_text": "A recipe uses flour and sugar in the ratio 5:2. If 250g of flour is used, how much sugar is needed?",
                    "marks": 2,
                    "tier": "foundation",
                    "topic": "ratio"
                },
                "mark_scheme": {
                    "answer": "100g",
                    "method": ["5 parts flour = 250g", "1 part = 250 ÷ 5 = 50g", "Sugar = 2 parts = 2 × 50 = 100g"],
                    "marks_breakdown": [
                        {"step": "Find value of one part", "marks": 1},
                        {"step": "Calculate sugar amount", "marks": 1}
                    ]
                },
                "quality_score": 0.90
            }
        ]
    }

def upload_examples_to_s3():
    """Upload example content to S3 examples bucket."""
    s3_client = boto3.client('s3', region_name=AWS_REGION)
    
    # Create example content for missing topics
    examples_data = {
        'geometry': create_geometry_examples(),
        'statistics': create_statistics_examples(), 
        'probability': create_probability_examples(),
        'ratio': create_ratio_examples()
    }
    
    upload_results = []
    
    for topic, data in examples_data.items():
        try:
            # Create S3 key
            s3_key = f"examples/{data['domain']}/{data['subtopic']}.json"
            
            # Upload to S3
            s3_client.put_object(
                Bucket=EXAMPLES_BUCKET,
                Key=s3_key,
                Body=json.dumps(data, indent=2),
                ContentType='application/json'
            )
            
            logger.info(f"✅ Uploaded {s3_key} to {EXAMPLES_BUCKET}")
            upload_results.append({
                'topic': topic,
                'key': s3_key,
                'status': 'success',
                'examples_count': data['total_examples']
            })
            
        except Exception as e:
            logger.error(f"❌ Failed to upload {topic}: {e}")
            upload_results.append({
                'topic': topic,
                'status': 'failed',
                'error': str(e)
            })
    
    return upload_results

def main():
    """Main function to upload missing example content."""
    print("🚀 UPLOADING MISSING EXAMPLE CONTENT")
    print("=" * 60)
    
    try:
        # Upload examples
        results = upload_examples_to_s3()
        
        # Print summary
        successful = [r for r in results if r['status'] == 'success']
        failed = [r for r in results if r['status'] == 'failed']
        
        print(f"\n📊 Upload Summary:")
        print(f"   ✅ Successful: {len(successful)}")
        print(f"   ❌ Failed: {len(failed)}")
        
        if successful:
            print(f"\n✅ Successfully uploaded:")
            for result in successful:
                print(f"   - {result['topic']}: {result['examples_count']} examples")
        
        if failed:
            print(f"\n❌ Failed uploads:")
            for result in failed:
                print(f"   - {result['topic']}: {result['error']}")
        
        if len(successful) == len(results):
            print(f"\n🎉 All example content uploaded successfully!")
            return True
        else:
            print(f"\n⚠️  Some uploads failed")
            return False
            
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        print(f"\n💥 Upload failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)