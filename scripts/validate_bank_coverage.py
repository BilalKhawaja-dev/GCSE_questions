"""
Question Bank Coverage Validation Script

Validates that all topics have sufficient verified questions
and generates coverage reports.
"""

import json
import logging
import os
import sys
from typing import Dict, List
from datetime import datetime
import boto3
from collections import defaultdict

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

# Configuration
TOPICS = [
    'number', 'algebra', 'ratio_proportion', 
    'geometry', 'probability', 'statistics'
]
GRADES = ['foundation', 'higher']
PAPER_TYPES = ['P1', 'P2', 'P3']

TARGET_COUNT = 50
WARNING_THRESHOLD = 0.8  # 80% of target
CRITICAL_THRESHOLD = 0.5  # 50% of target


def validate_coverage() -> Dict:
    """
    Validate question bank coverage for all combinations.
    
    Returns:
        Coverage report dictionary
    """
    logger.info("Starting coverage validation")
    
    # Initialize inventory service
    inventory_service = InventoryService(
        dynamodb_resource=dynamodb,
        target_count=TARGET_COUNT
    )
    
    # Check each combination
    coverage_data = []
    gaps = []
    warnings = []
    critical = []
    
    for topic in TOPICS:
        for grade in GRADES:
            for paper_type in PAPER_TYPES:
                combination = f"{topic}_{grade}_{paper_type}"
                
                # Get verified count
                verified_count = inventory_service.count_verified_questions(
                    topic=topic,
                    grade=grade,
                    paper_type=paper_type
                )
                
                # Get inventory status
                status = inventory_service.get_inventory_status(
                    topic=topic,
                    grade=grade,
                    paper_type=paper_type
                )
                
                # Calculate coverage percentage
                coverage_pct = (verified_count / TARGET_COUNT) * 100
                
                # Categorize
                if verified_count == 0:
                    gaps.append(combination)
                    status_label = 'EMPTY'
                elif verified_count < TARGET_COUNT * CRITICAL_THRESHOLD:
                    critical.append(combination)
                    status_label = 'CRITICAL'
                elif verified_count < TARGET_COUNT * WARNING_THRESHOLD:
                    warnings.append(combination)
                    status_label = 'WARNING'
                elif verified_count < TARGET_COUNT:
                    status_label = 'BELOW_TARGET'
                else:
                    status_label = 'HEALTHY'
                
                coverage_data.append({
                    'combination': combination,
                    'topic': topic,
                    'grade': grade,
                    'paper_type': paper_type,
                    'verified_count': verified_count,
                    'target_count': TARGET_COUNT,
                    'coverage_percentage': round(coverage_pct, 1),
                    'status': status_label,
                    'last_replenishment': status.get('last_replenishment'),
                    'generation_pass_rate': status.get('generation_pass_rate', 0.0)
                })
                
                logger.info(
                    f"{combination}: {verified_count}/{TARGET_COUNT} "
                    f"({coverage_pct:.1f}%) - {status_label}"
                )
    
    # Calculate summary statistics
    total_combinations = len(coverage_data)
    total_verified = sum(c['verified_count'] for c in coverage_data)
    total_target = TARGET_COUNT * total_combinations
    overall_coverage = (total_verified / total_target) * 100
    
    # Quality distribution
    quality_dist = analyze_quality_distribution(coverage_data)
    
    # Topic-level summary
    topic_summary = analyze_by_topic(coverage_data)
    
    # Grade-level summary
    grade_summary = analyze_by_grade(coverage_data)
    
    # Paper type summary
    paper_summary = analyze_by_paper_type(coverage_data)
    
    # Build report
    report = {
        'timestamp': datetime.utcnow().isoformat(),
        'summary': {
            'total_combinations': total_combinations,
            'total_verified': total_verified,
            'total_target': total_target,
            'overall_coverage_percentage': round(overall_coverage, 1),
            'healthy_count': sum(1 for c in coverage_data if c['status'] == 'HEALTHY'),
            'below_target_count': sum(1 for c in coverage_data if c['status'] == 'BELOW_TARGET'),
            'warning_count': len(warnings),
            'critical_count': len(critical),
            'empty_count': len(gaps)
        },
        'gaps': gaps,
        'warnings': warnings,
        'critical': critical,
        'quality_distribution': quality_dist,
        'topic_summary': topic_summary,
        'grade_summary': grade_summary,
        'paper_type_summary': paper_summary,
        'detailed_coverage': coverage_data
    }
    
    return report


def analyze_quality_distribution(coverage_data: List[Dict]) -> Dict:
    """
    Analyze quality score distribution across verified questions.
    
    Args:
        coverage_data: Coverage data for all combinations
    
    Returns:
        Quality distribution statistics
    """
    # This would query actual verification_confidence scores
    # For now, return placeholder
    return {
        'high_confidence': 0,  # >= 0.9
        'medium_confidence': 0,  # 0.7-0.9
        'low_confidence': 0,  # < 0.7
        'average_confidence': 0.0
    }


def analyze_by_topic(coverage_data: List[Dict]) -> Dict:
    """
    Analyze coverage by topic.
    
    Args:
        coverage_data: Coverage data for all combinations
    
    Returns:
        Topic-level summary
    """
    topic_stats = defaultdict(lambda: {
        'verified_count': 0,
        'target_count': 0,
        'combinations': 0
    })
    
    for item in coverage_data:
        topic = item['topic']
        topic_stats[topic]['verified_count'] += item['verified_count']
        topic_stats[topic]['target_count'] += item['target_count']
        topic_stats[topic]['combinations'] += 1
    
    # Calculate percentages
    for topic, stats in topic_stats.items():
        stats['coverage_percentage'] = round(
            (stats['verified_count'] / stats['target_count']) * 100, 1
        )
    
    return dict(topic_stats)


def analyze_by_grade(coverage_data: List[Dict]) -> Dict:
    """
    Analyze coverage by grade level.
    
    Args:
        coverage_data: Coverage data for all combinations
    
    Returns:
        Grade-level summary
    """
    grade_stats = defaultdict(lambda: {
        'verified_count': 0,
        'target_count': 0,
        'combinations': 0
    })
    
    for item in coverage_data:
        grade = item['grade']
        grade_stats[grade]['verified_count'] += item['verified_count']
        grade_stats[grade]['target_count'] += item['target_count']
        grade_stats[grade]['combinations'] += 1
    
    # Calculate percentages
    for grade, stats in grade_stats.items():
        stats['coverage_percentage'] = round(
            (stats['verified_count'] / stats['target_count']) * 100, 1
        )
    
    return dict(grade_stats)


def analyze_by_paper_type(coverage_data: List[Dict]) -> Dict:
    """
    Analyze coverage by paper type.
    
    Args:
        coverage_data: Coverage data for all combinations
    
    Returns:
        Paper type summary
    """
    paper_stats = defaultdict(lambda: {
        'verified_count': 0,
        'target_count': 0,
        'combinations': 0
    })
    
    for item in coverage_data:
        paper_type = item['paper_type']
        paper_stats[paper_type]['verified_count'] += item['verified_count']
        paper_stats[paper_type]['target_count'] += item['target_count']
        paper_stats[paper_type]['combinations'] += 1
    
    # Calculate percentages
    for paper_type, stats in paper_stats.items():
        stats['coverage_percentage'] = round(
            (stats['verified_count'] / stats['target_count']) * 100, 1
        )
    
    return dict(paper_stats)


def print_report(report: Dict):
    """
    Print coverage report to console.
    
    Args:
        report: Coverage report dictionary
    """
    print("\n" + "="*80)
    print("QUESTION BANK COVERAGE REPORT")
    print("="*80)
    print(f"Generated: {report['timestamp']}")
    print()
    
    summary = report['summary']
    print("OVERALL SUMMARY")
    print("-"*80)
    print(f"Total Combinations: {summary['total_combinations']}")
    print(f"Total Verified: {summary['total_verified']:,}")
    print(f"Total Target: {summary['total_target']:,}")
    print(f"Overall Coverage: {summary['overall_coverage_percentage']}%")
    print()
    print(f"Healthy: {summary['healthy_count']}")
    print(f"Below Target: {summary['below_target_count']}")
    print(f"Warnings: {summary['warning_count']}")
    print(f"Critical: {summary['critical_count']}")
    print(f"Empty: {summary['empty_count']}")
    print()
    
    if report['gaps']:
        print("EMPTY COMBINATIONS (No Questions)")
        print("-"*80)
        for gap in report['gaps']:
            print(f"  - {gap}")
        print()
    
    if report['critical']:
        print("CRITICAL COMBINATIONS (< 50% of target)")
        print("-"*80)
        for crit in report['critical']:
            print(f"  - {crit}")
        print()
    
    if report['warnings']:
        print("WARNING COMBINATIONS (< 80% of target)")
        print("-"*80)
        for warn in report['warnings']:
            print(f"  - {warn}")
        print()
    
    print("TOPIC SUMMARY")
    print("-"*80)
    for topic, stats in report['topic_summary'].items():
        print(
            f"{topic:20s}: {stats['verified_count']:4d}/{stats['target_count']:4d} "
            f"({stats['coverage_percentage']:5.1f}%)"
        )
    print()
    
    print("GRADE SUMMARY")
    print("-"*80)
    for grade, stats in report['grade_summary'].items():
        print(
            f"{grade:20s}: {stats['verified_count']:4d}/{stats['target_count']:4d} "
            f"({stats['coverage_percentage']:5.1f}%)"
        )
    print()
    
    print("PAPER TYPE SUMMARY")
    print("-"*80)
    for paper_type, stats in report['paper_type_summary'].items():
        print(
            f"{paper_type:20s}: {stats['verified_count']:4d}/{stats['target_count']:4d} "
            f"({stats['coverage_percentage']:5.1f}%)"
        )
    print()
    print("="*80)


def main():
    """Main entry point."""
    # Run validation
    report = validate_coverage()
    
    # Print to console
    print_report(report)
    
    # Save to file
    report_file = f"coverage_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    logger.info(f"Report saved to {report_file}")
    
    # Exit with error if critical gaps found
    if report['gaps'] or report['critical']:
        logger.error("Critical gaps found in question bank!")
        return 1
    
    if report['warnings']:
        logger.warning("Warnings found in question bank")
        return 0
    
    logger.info("Question bank coverage is healthy!")
    return 0


if __name__ == '__main__':
    sys.exit(main())
