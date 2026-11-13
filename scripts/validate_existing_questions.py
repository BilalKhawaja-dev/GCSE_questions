"""
Validate Existing Questions Script

Runs verification on a sample of existing questions to analyze
pass/fail distribution and tune thresholds.
"""

import json
import logging
import os
import sys
import random
from typing import Dict, List
from datetime import datetime
import boto3
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.lambda_handlers.verification_lambda import verify_question
from src.models.verification import VerificationResult

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')

# Configuration
SAMPLE_SIZE = 100  # Number of questions to validate
VERIFIED_TABLE = 'verified_question_bank'


def get_sample_questions(sample_size: int) -> List[Dict]:
    """
    Get a random sample of existing questions.
    
    Args:
        sample_size: Number of questions to sample
    
    Returns:
        List of question dictionaries
    """
    logger.info(f"Fetching sample of {sample_size} questions")
    
    try:
        table = dynamodb.Table(VERIFIED_TABLE)
        
        # Scan table (for sampling)
        response = table.scan(Limit=sample_size * 2)
        items = response.get('Items', [])
        
        # Random sample
        if len(items) > sample_size:
            items = random.sample(items, sample_size)
        
        logger.info(f"Retrieved {len(items)} questions")
        return items
        
    except Exception as e:
        logger.error(f"Failed to fetch questions: {e}")
        return []


def analyze_verification_results(results: List[Dict]) -> Dict:
    """
    Analyze verification results to identify patterns.
    
    Args:
        results: List of verification results
    
    Returns:
        Analysis summary
    """
    # Count pass/fail
    passed = sum(1 for r in results if r['verdict'] == 'PASS')
    failed = sum(1 for r in results if r['verdict'] == 'FAIL')
    
    # Analyze failure reasons
    failure_reasons = defaultdict(int)
    for r in results:
        if r['verdict'] == 'FAIL':
            for reason in r.get('failure_reasons', []):
                # Extract layer name
                if ':' in reason:
                    layer = reason.split(':')[0]
                    failure_reasons[layer] += 1
                else:
                    failure_reasons['Unknown'] += 1
    
    # Analyze confidence scores
    confidences = [r['overall_confidence'] for r in results]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
    
    # Confidence distribution
    high_conf = sum(1 for c in confidences if c >= 0.9)
    med_conf = sum(1 for c in confidences if 0.7 <= c < 0.9)
    low_conf = sum(1 for c in confidences if c < 0.7)
    
    # Layer-specific analysis
    layer_stats = analyze_layer_performance(results)
    
    return {
        'total_validated': len(results),
        'passed': passed,
        'failed': failed,
        'pass_rate': (passed / len(results)) * 100 if results else 0.0,
        'average_confidence': avg_confidence,
        'confidence_distribution': {
            'high': high_conf,
            'medium': med_conf,
            'low': low_conf
        },
        'failure_reasons': dict(failure_reasons),
        'layer_performance': layer_stats
    }


def analyze_layer_performance(results: List[Dict]) -> Dict:
    """
    Analyze performance of each verification layer.
    
    Args:
        results: List of verification results
    
    Returns:
        Layer performance statistics
    """
    layers = ['deterministic', 'sympy', 'llm_auditor', 'kb_alignment', 'dedupe']
    layer_stats = {}
    
    for layer in layers:
        applicable = 0
        passed = 0
        failed = 0
        avg_confidence = []
        
        for r in results:
            layer_result = r.get('verification_results', {}).get(layer, {})
            
            if layer == 'sympy':
                if layer_result.get('applicable', False):
                    applicable += 1
                    if layer_result.get('pass', False):
                        passed += 1
                    else:
                        failed += 1
                    if 'confidence' in layer_result:
                        avg_confidence.append(layer_result['confidence'])
            else:
                applicable += 1
                if layer_result.get('pass', False):
                    passed += 1
                else:
                    failed += 1
                if 'confidence' in layer_result:
                    avg_confidence.append(layer_result['confidence'])
        
        layer_stats[layer] = {
            'applicable': applicable,
            'passed': passed,
            'failed': failed,
            'pass_rate': (passed / applicable) * 100 if applicable > 0 else 0.0,
            'average_confidence': sum(avg_confidence) / len(avg_confidence) if avg_confidence else 0.0
        }
    
    return layer_stats


def suggest_threshold_adjustments(analysis: Dict) -> List[str]:
    """
    Suggest threshold adjustments based on analysis.
    
    Args:
        analysis: Analysis results
    
    Returns:
        List of suggestions
    """
    suggestions = []
    
    # Check overall pass rate
    pass_rate = analysis['pass_rate']
    if pass_rate < 60:
        suggestions.append(
            "⚠️  Pass rate is low (<60%). Consider relaxing verification thresholds."
        )
    elif pass_rate > 90:
        suggestions.append(
            "✓ Pass rate is high (>90%). Verification may be too lenient."
        )
    
    # Check confidence distribution
    conf_dist = analysis['confidence_distribution']
    if conf_dist['low'] > conf_dist['high']:
        suggestions.append(
            "⚠️  Many low-confidence results. Review LLM auditor prompts."
        )
    
    # Check layer performance
    layer_perf = analysis['layer_performance']
    
    # SymPy
    sympy_stats = layer_perf.get('sympy', {})
    if sympy_stats.get('applicable', 0) > 0:
        sympy_pass_rate = sympy_stats.get('pass_rate', 0)
        if sympy_pass_rate < 70:
            suggestions.append(
                f"⚠️  SymPy pass rate is low ({sympy_pass_rate:.1f}%). "
                "Consider adjusting tolerance levels."
            )
    
    # LLM Auditor
    llm_stats = layer_perf.get('llm_auditor', {})
    llm_pass_rate = llm_stats.get('pass_rate', 0)
    llm_confidence = llm_stats.get('average_confidence', 0)
    
    if llm_pass_rate < 70:
        suggestions.append(
            f"⚠️  LLM auditor pass rate is low ({llm_pass_rate:.1f}%). "
            "Consider lowering confidence threshold (currently 0.75)."
        )
    
    if llm_confidence < 0.75:
        suggestions.append(
            f"⚠️  LLM auditor average confidence is low ({llm_confidence:.2f}). "
            "Review prompts and examples."
        )
    
    # Dedupe
    dedupe_stats = layer_perf.get('dedupe', {})
    dedupe_pass_rate = dedupe_stats.get('pass_rate', 0)
    if dedupe_pass_rate < 95:
        suggestions.append(
            f"⚠️  Dedupe pass rate is low ({dedupe_pass_rate:.1f}%). "
            "Consider adjusting similarity threshold (currently 0.85)."
        )
    
    if not suggestions:
        suggestions.append("✓ All thresholds appear well-calibrated.")
    
    return suggestions


def print_analysis(analysis: Dict, suggestions: List[str]):
    """
    Print analysis results to console.
    
    Args:
        analysis: Analysis results
        suggestions: Threshold adjustment suggestions
    """
    print("\n" + "="*80)
    print("VERIFICATION VALIDATION REPORT")
    print("="*80)
    print()
    
    print("OVERALL RESULTS")
    print("-"*80)
    print(f"Total Validated: {analysis['total_validated']}")
    print(f"Passed: {analysis['passed']}")
    print(f"Failed: {analysis['failed']}")
    print(f"Pass Rate: {analysis['pass_rate']:.1f}%")
    print(f"Average Confidence: {analysis['average_confidence']:.2f}")
    print()
    
    print("CONFIDENCE DISTRIBUTION")
    print("-"*80)
    conf_dist = analysis['confidence_distribution']
    print(f"High (≥0.9): {conf_dist['high']}")
    print(f"Medium (0.7-0.9): {conf_dist['medium']}")
    print(f"Low (<0.7): {conf_dist['low']}")
    print()
    
    if analysis['failure_reasons']:
        print("FAILURE REASONS")
        print("-"*80)
        for reason, count in sorted(
            analysis['failure_reasons'].items(),
            key=lambda x: x[1],
            reverse=True
        ):
            print(f"{reason:30s}: {count:3d}")
        print()
    
    print("LAYER PERFORMANCE")
    print("-"*80)
    for layer, stats in analysis['layer_performance'].items():
        print(f"\n{layer.upper()}")
        print(f"  Applicable: {stats['applicable']}")
        print(f"  Passed: {stats['passed']}")
        print(f"  Failed: {stats['failed']}")
        print(f"  Pass Rate: {stats['pass_rate']:.1f}%")
        if stats['average_confidence'] > 0:
            print(f"  Avg Confidence: {stats['average_confidence']:.2f}")
    print()
    
    print("THRESHOLD ADJUSTMENT SUGGESTIONS")
    print("-"*80)
    for suggestion in suggestions:
        print(f"  {suggestion}")
    print()
    print("="*80)


def main():
    """Main entry point."""
    logger.info("Starting validation of existing questions")
    
    # Get sample questions
    questions = get_sample_questions(SAMPLE_SIZE)
    
    if not questions:
        logger.error("No questions found to validate")
        return 1
    
    # Run verification on each question
    results = []
    for i, question in enumerate(questions):
        logger.info(f"Validating question {i+1}/{len(questions)}")
        
        try:
            result = verify_question(question)
            results.append({
                'question_id': question.get('question_id'),
                'verdict': result.verdict,
                'overall_confidence': result.overall_confidence,
                'verification_results': result.verification_results,
                'failure_reasons': result.failure_reasons
            })
        except Exception as e:
            logger.error(f"Failed to validate question: {e}")
    
    # Analyze results
    analysis = analyze_verification_results(results)
    
    # Generate suggestions
    suggestions = suggest_threshold_adjustments(analysis)
    
    # Print analysis
    print_analysis(analysis, suggestions)
    
    # Save report
    report = {
        'timestamp': datetime.utcnow().isoformat(),
        'sample_size': len(questions),
        'analysis': analysis,
        'suggestions': suggestions,
        'detailed_results': results
    }
    
    report_file = f"validation_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    logger.info(f"Report saved to {report_file}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
