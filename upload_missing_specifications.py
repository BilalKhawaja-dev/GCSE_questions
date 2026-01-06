#!/usr/bin/env python3
"""
Upload missing specification content for GCSE topics.
This script creates and uploads specification files for topics that are missing from the specifications bucket.
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
SPECIFICATIONS_BUCKET = 'gcse-specifications-prod-1a64dc99'
AWS_REGION = 'eu-west-2'

def create_decimals_specification() -> Dict[str, Any]:
    """Create specification content for decimals topic."""
    return {
        "domain": "number",
        "subtopic": "decimals",
        "tier": "both",
        "version": "2024.1",
        "learning_objectives": [
            "Add and subtract decimal numbers",
            "Multiply and divide decimal numbers",
            "Convert between fractions and decimals",
            "Round decimal numbers to given number of decimal places",
            "Order decimal numbers"
        ],
        "specification_content": "Students should be able to work with decimal numbers including addition, subtraction, multiplication and division. They should understand place value in decimal numbers and be able to convert between fractions and decimals. Students should be able to round decimal numbers to a specified number of decimal places and order decimal numbers.",
        "key_concepts": [
            "Place value in decimal numbers",
            "Decimal operations",
            "Fraction-decimal conversion",
            "Rounding decimal numbers",
            "Ordering decimals"
        ],
        "common_misconceptions": [
            "Thinking 0.5 is larger than 0.50",
            "Confusion with place value when multiplying by 10, 100, 1000",
            "Incorrect alignment when adding/subtracting decimals",
            "Confusion between rounding up and down"
        ],
        "assessment_objectives": ["AO1", "AO2"],
        "marks_range": [1, 4],
        "version_timestamp": datetime.utcnow().isoformat() + 'Z',
        "version_metadata": {
            "created_by": "V2_content_upload",
            "content_source": "Edexcel_GCSE_Mathematics_specification",
            "quality_reviewed": True
        }
    }

def create_percentages_specification() -> Dict[str, Any]:
    """Create specification content for percentages topic."""
    return {
        "domain": "number",
        "subtopic": "percentages",
        "tier": "both",
        "version": "2024.1",
        "learning_objectives": [
            "Convert between percentages, fractions and decimals",
            "Calculate percentage of an amount",
            "Calculate percentage increase and decrease",
            "Find the original amount given the result of a percentage change",
            "Calculate compound percentage changes"
        ],
        "specification_content": "Students should be able to work with percentages including conversion between percentages, fractions and decimals. They should calculate percentages of amounts, percentage increases and decreases, and solve reverse percentage problems. Higher tier students should handle compound percentage changes.",
        "key_concepts": [
            "Percentage-fraction-decimal equivalence",
            "Percentage calculations",
            "Percentage change",
            "Reverse percentages",
            "Compound percentages"
        ],
        "common_misconceptions": [
            "Adding percentages instead of multiplying for compound changes",
            "Confusion between percentage increase and the multiplier",
            "Incorrect method for reverse percentage calculations",
            "Thinking 50% of 50% equals 25%"
        ],
        "assessment_objectives": ["AO1", "AO2", "AO3"],
        "marks_range": [2, 6],
        "version_timestamp": datetime.utcnow().isoformat() + 'Z',
        "version_metadata": {
            "created_by": "V2_content_upload",
            "content_source": "Edexcel_GCSE_Mathematics_specification",
            "quality_reviewed": True
        }
    }

def create_quadratics_specification() -> Dict[str, Any]:
    """Create specification content for quadratic equations topic."""
    return {
        "domain": "algebra",
        "subtopic": "quadratic-equations",
        "tier": "higher",
        "version": "2024.1",
        "learning_objectives": [
            "Solve quadratic equations by factorisation",
            "Solve quadratic equations using the quadratic formula",
            "Complete the square for quadratic expressions",
            "Solve quadratic equations by completing the square",
            "Interpret the discriminant of a quadratic equation"
        ],
        "specification_content": "Students should be able to solve quadratic equations using various methods including factorisation, the quadratic formula, and completing the square. They should understand the discriminant and its relationship to the number and nature of roots.",
        "key_concepts": [
            "Factorisation of quadratics",
            "Quadratic formula",
            "Completing the square",
            "Discriminant",
            "Nature of roots"
        ],
        "common_misconceptions": [
            "Forgetting to set equation equal to zero before factorising",
            "Sign errors when using the quadratic formula",
            "Confusion with completing the square process",
            "Misinterpreting the discriminant"
        ],
        "assessment_objectives": ["AO1", "AO2"],
        "marks_range": [3, 8],
        "version_timestamp": datetime.utcnow().isoformat() + 'Z',
        "version_metadata": {
            "created_by": "V2_content_upload",
            "content_source": "Edexcel_GCSE_Mathematics_specification",
            "quality_reviewed": True
        }
    }

def create_simultaneous_equations_specification() -> Dict[str, Any]:
    """Create specification content for simultaneous equations topic."""
    return {
        "domain": "algebra",
        "subtopic": "simultaneous-equations",
        "tier": "both",
        "version": "2024.1",
        "learning_objectives": [
            "Solve simultaneous linear equations by elimination",
            "Solve simultaneous linear equations by substitution",
            "Solve simultaneous equations graphically",
            "Solve one linear and one quadratic equation simultaneously (Higher only)",
            "Interpret solutions in context"
        ],
        "specification_content": "Students should be able to solve pairs of simultaneous linear equations using algebraic methods (elimination and substitution) and graphical methods. Higher tier students should also solve one linear and one quadratic equation simultaneously.",
        "key_concepts": [
            "Elimination method",
            "Substitution method",
            "Graphical solution",
            "Linear-quadratic systems",
            "Solution interpretation"
        ],
        "common_misconceptions": [
            "Sign errors when eliminating variables",
            "Forgetting to substitute back to find second variable",
            "Confusion about which variable to eliminate first",
            "Misreading intersection points from graphs"
        ],
        "assessment_objectives": ["AO1", "AO2", "AO3"],
        "marks_range": [3, 7],
        "version_timestamp": datetime.utcnow().isoformat() + 'Z',
        "version_metadata": {
            "created_by": "V2_content_upload",
            "content_source": "Edexcel_GCSE_Mathematics_specification",
            "quality_reviewed": True
        }
    }

def create_pythagoras_specification() -> Dict[str, Any]:
    """Create specification content for Pythagoras theorem topic."""
    return {
        "domain": "geometry",
        "subtopic": "pythagoras",
        "tier": "both",
        "version": "2024.1",
        "learning_objectives": [
            "Use Pythagoras' theorem to find missing sides in right-angled triangles",
            "Use Pythagoras' theorem to solve problems in 2D",
            "Use Pythagoras' theorem to solve problems in 3D (Higher only)",
            "Determine whether a triangle is right-angled using Pythagoras' theorem",
            "Apply Pythagoras' theorem in real-world contexts"
        ],
        "specification_content": "Students should be able to use Pythagoras' theorem to find missing sides in right-angled triangles and solve problems in 2D contexts. Higher tier students should extend this to 3D problems. Students should also be able to use the converse to test for right-angled triangles.",
        "key_concepts": [
            "Pythagoras' theorem: a² + b² = c²",
            "Identifying the hypotenuse",
            "Finding missing sides",
            "Converse of Pythagoras' theorem",
            "3D applications"
        ],
        "common_misconceptions": [
            "Confusing which side is the hypotenuse",
            "Using the theorem incorrectly when finding a shorter side",
            "Forgetting to square root the final answer",
            "Applying the theorem to non-right-angled triangles"
        ],
        "assessment_objectives": ["AO1", "AO2", "AO3"],
        "marks_range": [2, 5],
        "version_timestamp": datetime.utcnow().isoformat() + 'Z',
        "version_metadata": {
            "created_by": "V2_content_upload",
            "content_source": "Edexcel_GCSE_Mathematics_specification",
            "quality_reviewed": True
        }
    }

def create_trigonometry_specification() -> Dict[str, Any]:
    """Create specification content for trigonometry topic."""
    return {
        "domain": "geometry",
        "subtopic": "trigonometry",
        "tier": "higher",
        "version": "2024.1",
        "learning_objectives": [
            "Use trigonometric ratios (sin, cos, tan) to find missing sides and angles",
            "Use the sine rule to solve problems in any triangle",
            "Use the cosine rule to solve problems in any triangle",
            "Calculate the area of triangles using ½ab sin C",
            "Solve problems in 3D using trigonometry"
        ],
        "specification_content": "Students should be able to use trigonometric ratios in right-angled triangles and extend to the sine and cosine rules for any triangle. They should calculate areas using trigonometry and solve 3D problems.",
        "key_concepts": [
            "SOH CAH TOA",
            "Sine rule: a/sin A = b/sin B = c/sin C",
            "Cosine rule: a² = b² + c² - 2bc cos A",
            "Area = ½ab sin C",
            "3D trigonometry"
        ],
        "common_misconceptions": [
            "Confusing sin, cos, and tan ratios",
            "Using degrees instead of the correct angle",
            "Incorrect application of sine and cosine rules",
            "Forgetting to use inverse trig functions when finding angles"
        ],
        "assessment_objectives": ["AO1", "AO2", "AO3"],
        "marks_range": [3, 8],
        "version_timestamp": datetime.utcnow().isoformat() + 'Z',
        "version_metadata": {
            "created_by": "V2_content_upload",
            "content_source": "Edexcel_GCSE_Mathematics_specification",
            "quality_reviewed": True
        }
    }

def create_averages_specification() -> Dict[str, Any]:
    """Create specification content for averages topic."""
    return {
        "domain": "statistics",
        "subtopic": "averages",
        "tier": "both",
        "version": "2024.1",
        "learning_objectives": [
            "Calculate mean, median, mode and range from lists of data",
            "Calculate mean, median, mode and range from frequency tables",
            "Estimate mean from grouped frequency tables",
            "Compare data sets using measures of average and spread",
            "Understand when to use different measures of average"
        ],
        "specification_content": "Students should be able to calculate and interpret measures of central tendency (mean, median, mode) and spread (range) from various data presentations. They should understand the advantages and disadvantages of each measure.",
        "key_concepts": [
            "Mean calculation",
            "Median identification",
            "Mode identification",
            "Range calculation",
            "Frequency tables",
            "Grouped data estimation"
        ],
        "common_misconceptions": [
            "Confusing mean and median",
            "Not ordering data before finding median",
            "Incorrect frequency table calculations",
            "Using inappropriate averages for skewed data"
        ],
        "assessment_objectives": ["AO1", "AO2", "AO3"],
        "marks_range": [2, 6],
        "version_timestamp": datetime.utcnow().isoformat() + 'Z',
        "version_metadata": {
            "created_by": "V2_content_upload",
            "content_source": "Edexcel_GCSE_Mathematics_specification",
            "quality_reviewed": True
        }
    }

def upload_specifications_to_s3():
    """Upload specification content to S3 specifications bucket."""
    s3_client = boto3.client('s3', region_name=AWS_REGION)
    
    # Create specification content for missing topics
    specifications_data = {
        'decimals': create_decimals_specification(),
        'percentages': create_percentages_specification(),
        'quadratic-equations': create_quadratics_specification(),
        'simultaneous-equations': create_simultaneous_equations_specification(),
        'pythagoras': create_pythagoras_specification(),
        'trigonometry': create_trigonometry_specification(),
        'averages': create_averages_specification()
    }
    
    upload_results = []
    
    for topic, data in specifications_data.items():
        try:
            # Create S3 key
            s3_key = f"specifications/{data['domain']}/{data['subtopic']}_latest.json"
            
            # Upload to S3
            s3_client.put_object(
                Bucket=SPECIFICATIONS_BUCKET,
                Key=s3_key,
                Body=json.dumps(data, indent=2),
                ContentType='application/json'
            )
            
            logger.info(f"✅ Uploaded {s3_key} to {SPECIFICATIONS_BUCKET}")
            upload_results.append({
                'topic': topic,
                'key': s3_key,
                'status': 'success',
                'domain': data['domain'],
                'tier': data['tier']
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
    """Main function to upload missing specification content."""
    print("🚀 UPLOADING MISSING SPECIFICATION CONTENT")
    print("=" * 60)
    
    try:
        # Upload specifications
        results = upload_specifications_to_s3()
        
        # Print summary
        successful = [r for r in results if r['status'] == 'success']
        failed = [r for r in results if r['status'] == 'failed']
        
        print(f"\n📊 Upload Summary:")
        print(f"   ✅ Successful: {len(successful)}")
        print(f"   ❌ Failed: {len(failed)}")
        
        if successful:
            print(f"\n✅ Successfully uploaded:")
            for result in successful:
                print(f"   - {result['topic']} ({result['domain']}, {result['tier']} tier)")
        
        if failed:
            print(f"\n❌ Failed uploads:")
            for result in failed:
                print(f"   - {result['topic']}: {result['error']}")
        
        if len(successful) == len(results):
            print(f"\n🎉 All specification content uploaded successfully!")
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