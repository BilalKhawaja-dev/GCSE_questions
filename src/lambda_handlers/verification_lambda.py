"""
Verification Lambda - Orchestrates Question Verification Pipeline

Processes questions from verification queue through all verification layers:
1. Deterministic checks
2. SymPy verification (if applicable)
3. LLM auditor
4. KB alignment
5. Dedupe check

PASS questions → verified_question_bank
FAIL questions → rejected_questions
"""

import json
import logging
import os
import boto3
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime
from decimal import Decimal

from src.services.deterministic_verifier_service import DeterministicVerifier
from src.services.sympy_verifier_service import SymPyVerifier, MCQQuestion
from src.services.llm_auditor_service import LLMAuditor
from src.services.kb_alignment_service import KBAlignmentService
from src.services.dedupe_service import DedupeService
from src.services.inventory_service import InventoryService
from src.models.verification import VerificationResult


def convert_floats_to_decimal(obj):
    """Convert all floats in a dict/list to Decimal for DynamoDB."""
    if isinstance(obj, list):
        return [convert_floats_to_decimal(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: convert_floats_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, float):
        return Decimal(str(obj))
    else:
        return obj

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
bedrock_runtime = boto3.client('bedrock-runtime', region_name='eu-west-2')
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name='eu-west-2')

# Environment variables
VERIFIED_TABLE = os.environ.get('VERIFIED_QUESTION_BANK_TABLE', 'verified_question_bank')
REJECTED_TABLE = os.environ.get('REJECTED_QUESTIONS_TABLE', 'rejected_questions')
INVENTORY_TABLE = os.environ.get('QUESTION_BANK_INVENTORY_TABLE', 'question_bank_inventory')
KNOWLEDGE_BASE_ID = os.environ.get('KNOWLEDGE_BASE_ID')

# Initialize verification services
deterministic_verifier = DeterministicVerifier()
sympy_verifier = SymPyVerifier()
llm_auditor = LLMAuditor(bedrock_runtime)
kb_alignment_service = KBAlignmentService(
    knowledge_base_id=KNOWLEDGE_BASE_ID,
    region='eu-west-2'
)
dedupe_service = DedupeService(
    bedrock_client=bedrock_runtime,
    dynamodb_client=dynamodb,
    table_name=VERIFIED_TABLE
)
inventory_service = InventoryService(
    dynamodb_resource=dynamodb,
    verified_table_name=VERIFIED_TABLE,
    inventory_table_name=INVENTORY_TABLE
)


def handler(event, context):
    """
    Verification Lambda handler.
    
    Processes questions from SQS verification queue through all verification layers.
    
    Args:
        event: SQS event with question messages
        context: Lambda context
    
    Returns:
        Batch processing results
    """
    logger.info(f"Processing {len(event.get('Records', []))} messages from verification queue")
    
    results = {
        'passed': 0,
        'failed': 0,
        'errors': 0
    }
    
    for record in event.get('Records', []):
        try:
            # Parse message
            message_body = json.loads(record['body'])
            question_data = message_body
            
            question_id = question_data.get('question_id', 'unknown')
            logger.info(f"Verifying question {question_id}")
            
            # Run verification pipeline
            verification_result = verify_question(question_data)
            
            # Store result
            if verification_result.verdict == "PASS":
                store_verified_question(question_data, verification_result)
                results['passed'] += 1
                logger.info(f"Question {question_id} PASSED verification")
            else:
                store_rejected_question(question_data, verification_result)
                results['failed'] += 1
                logger.info(
                    f"Question {question_id} FAILED verification: "
                    f"{verification_result.failure_reasons}"
                )
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            results['errors'] += 1
    
    logger.info(
        f"Verification batch complete: "
        f"passed={results['passed']}, "
        f"failed={results['failed']}, "
        f"errors={results['errors']}"
    )
    
    return {
        'statusCode': 200,
        'body': json.dumps(results)
    }


def verify_question(question_data: Dict[str, Any]) -> VerificationResult:
    """
    Run complete verification pipeline on a question.
    
    Args:
        question_data: Question to verify
    
    Returns:
        VerificationResult with verdict and details
    """
    question_id = question_data.get('question_id', str(uuid.uuid4()))
    verification_results = {}
    failure_reasons = []
    confidences = []
    
    try:
        # 1. Deterministic checks (fast, rule-based)
        logger.debug(f"Running deterministic checks for {question_id}")
        deterministic_result = deterministic_verifier.verify(question_data)
        verification_results['deterministic'] = {
            'pass': deterministic_result.pass_,
            'issues': deterministic_result.issues,
            'checks_performed': deterministic_result.checks_performed
        }
        
        if not deterministic_result.pass_:
            failure_reasons.extend(deterministic_result.issues)
            # Fail fast on deterministic checks
            return VerificationResult(
                question_id=question_id,
                verdict="FAIL",
                verification_results=verification_results,
                overall_confidence=0.0,
                timestamp=datetime.utcnow().isoformat(),
                failure_reasons=failure_reasons
            )
        
        confidences.append(1.0)  # Deterministic checks have 100% confidence
        
        # 2. SymPy verification (mathematical correctness)
        logger.debug(f"Running SymPy verification for {question_id}")
        try:
            mcq_question = MCQQuestion(
                stem=question_data.get('stem', ''),
                options=question_data.get('options', []),
                correct_answer=question_data.get('correct_answer', ''),
                topic=question_data.get('topic', ''),
                difficulty=question_data.get('difficulty', 5),
                paper_type=question_data.get('paper_type', 'P2'),
                grade=question_data.get('grade', 'foundation'),
                rationale=question_data.get('rationale')
            )
            
            sympy_result = sympy_verifier.verify(mcq_question)
            verification_results['sympy'] = {
                'applicable': sympy_result.applicable,
                'pass': sympy_result.pass_,
                'confidence': sympy_result.confidence,
                'solved_answer': sympy_result.solved_answer,
                'reason': sympy_result.reason,
                'distractor_quality': sympy_result.distractor_quality
            }
            
            if sympy_result.applicable:
                if not sympy_result.pass_:
                    failure_reasons.append(f"SymPy: {sympy_result.reason}")
                confidences.append(sympy_result.confidence)
        except Exception as e:
            logger.warning(f"SymPy verification error: {str(e)}")
            verification_results['sympy'] = {
                'applicable': False,
                'error': str(e)
            }
        
        # 3. LLM Auditor (semantic validation)
        logger.debug(f"Running LLM auditor for {question_id}")
        try:
            audit_result = llm_auditor.audit(question_data)
            verification_results['llm_auditor'] = {
                'verdict': audit_result.verdict,
                'solved_answer': audit_result.solved_answer,
                'agreement': audit_result.agreement,
                'ambiguity': audit_result.ambiguity,
                'issues': audit_result.issues,
                'confidence': audit_result.confidence
            }
            
            if audit_result.verdict == "FAIL":
                failure_reasons.append(f"LLM Auditor: {', '.join(audit_result.issues)}")
            
            confidences.append(audit_result.confidence)
        except Exception as e:
            logger.error(f"LLM auditor error: {str(e)}")
            verification_results['llm_auditor'] = {
                'verdict': 'FAIL',
                'error': str(e)
            }
            failure_reasons.append(f"LLM Auditor error: {str(e)}")
            confidences.append(0.0)
        
        # 4. KB Alignment (retrieval-grounded verification)
        logger.debug(f"Running KB alignment for {question_id}")
        try:
            alignment_result = kb_alignment_service.verify_alignment(question_data)
            verification_results['kb_alignment'] = {
                'pass': alignment_result.pass_,
                'source_alignment': {
                    'pass': alignment_result.source_alignment.pass_,
                    'confidence': alignment_result.source_alignment.confidence,
                    'reasoning': alignment_result.source_alignment.reasoning
                },
                'syllabus_compliance': {
                    'pass': alignment_result.syllabus_compliance.pass_,
                    'confidence': alignment_result.syllabus_compliance.confidence,
                    'reasoning': alignment_result.syllabus_compliance.reasoning
                }
            }
            
            if not alignment_result.pass_:
                if not alignment_result.source_alignment.pass_:
                    failure_reasons.append(
                        f"KB Source Alignment: {alignment_result.source_alignment.reasoning}"
                    )
                if not alignment_result.syllabus_compliance.pass_:
                    failure_reasons.append(
                        f"KB Syllabus Compliance: {alignment_result.syllabus_compliance.reasoning}"
                    )
            
            confidences.append(alignment_result.overall_confidence)
        except Exception as e:
            logger.warning(f"KB alignment error (graceful degradation): {str(e)}")
            verification_results['kb_alignment'] = {
                'pass': True,  # Graceful degradation
                'error': str(e)
            }
            confidences.append(0.0)
        
        # 5. Dedupe check (similarity detection)
        logger.debug(f"Running dedupe check for {question_id}")
        try:
            dedupe_result = dedupe_service.check_duplicate(question_data)
            verification_results['dedupe'] = {
                'pass': dedupe_result.pass_,
                'max_similarity': dedupe_result.max_similarity,
                'similar_question_id': dedupe_result.similar_question_id
            }
            
            if not dedupe_result.pass_:
                failure_reasons.append(
                    f"Duplicate detected: {dedupe_result.max_similarity:.2%} similarity "
                    f"with {dedupe_result.similar_question_id}"
                )
            
            # Store embedding for future dedupe checks
            if dedupe_result.embedding:
                question_data['embedding'] = dedupe_result.embedding
        except Exception as e:
            logger.warning(f"Dedupe check error: {str(e)}")
            verification_results['dedupe'] = {
                'pass': True,  # Don't fail on dedupe errors
                'error': str(e)
            }
        
        # Calculate overall confidence
        overall_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        # Determine final verdict
        verdict = "PASS" if len(failure_reasons) == 0 else "FAIL"
        
        return VerificationResult(
            question_id=question_id,
            verdict=verdict,
            verification_results=verification_results,
            overall_confidence=overall_confidence,
            timestamp=datetime.utcnow().isoformat(),
            failure_reasons=failure_reasons
        )
        
    except Exception as e:
        logger.error(f"Verification pipeline error: {str(e)}", exc_info=True)
        return VerificationResult(
            question_id=question_id,
            verdict="FAIL",
            verification_results=verification_results,
            overall_confidence=0.0,
            timestamp=datetime.utcnow().isoformat(),
            failure_reasons=[f"Pipeline error: {str(e)}"]
        )


def store_verified_question(
    question_data: Dict[str, Any],
    verification_result: VerificationResult
) -> bool:
    """
    Store verified question in verified_question_bank table.
    
    Args:
        question_data: Question data
        verification_result: Verification result
    
    Returns:
        True if successful
    """
    try:
        table = dynamodb.Table(VERIFIED_TABLE)
        
        # Build composite key for GSI
        topic = question_data.get('topic', '')
        grade = question_data.get('grade', '')
        paper_type = question_data.get('paper_type', '')
        topic_grade_paper = f"{topic}_{grade}_{paper_type}"
        
        # Prepare item
        item = {
            'question_id': question_data['question_id'],
            'topic_grade_paper': topic_grade_paper,
            'stem': question_data.get('stem', ''),
            'options': question_data.get('options', []),
            'correct_answer': question_data.get('correct_answer', ''),
            'rationale': question_data.get('rationale', ''),
            'topic': topic,
            'grade': grade,
            'paper_type': paper_type,
            'difficulty': question_data.get('difficulty', 5),
            'verification_status': 'VERIFIED',
            'verification_timestamp': verification_result.timestamp,
            'verification_confidence': verification_result.overall_confidence,
            'verification_results': verification_result.verification_results,
            'embedding': question_data.get('embedding', []),
            'times_served': 0,
            'created_at': question_data.get('created_at', datetime.utcnow().isoformat()),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        # Convert floats to Decimal for DynamoDB
        item = convert_floats_to_decimal(item)
        
        # Store in DynamoDB
        table.put_item(Item=item)
        
        # Update inventory count
        inventory_service.update_inventory_count(
            topic=topic,
            grade=grade,
            paper_type=paper_type,
            increment=1
        )
        
        logger.info(f"Stored verified question {question_data['question_id']}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to store verified question: {str(e)}")
        return False


def store_rejected_question(
    question_data: Dict[str, Any],
    verification_result: VerificationResult
) -> bool:
    """
    Store rejected question in rejected_questions table for analysis.
    
    Args:
        question_data: Question data
        verification_result: Verification result
    
    Returns:
        True if successful
    """
    try:
        table = dynamodb.Table(REJECTED_TABLE)
        
        # Prepare item
        item = {
            'question_id': question_data['question_id'],
            'topic': question_data.get('topic', ''),
            'grade': question_data.get('grade', ''),
            'paper_type': question_data.get('paper_type', ''),
            'stem': question_data.get('stem', ''),
            'options': question_data.get('options', []),
            'correct_answer': question_data.get('correct_answer', ''),
            'verification_status': 'REJECTED',
            'failure_reasons': verification_result.failure_reasons,
            'verification_results': verification_result.verification_results,
            'verification_confidence': verification_result.overall_confidence,
            'rejected_at': verification_result.timestamp,
            'created_at': question_data.get('created_at', datetime.utcnow().isoformat())
        }
        
        # Convert floats to Decimal for DynamoDB
        item = convert_floats_to_decimal(item)
        
        # Store in DynamoDB
        table.put_item(Item=item)
        
        logger.info(
            f"Stored rejected question {question_data['question_id']}: "
            f"{verification_result.failure_reasons}"
        )
        return True
        
    except Exception as e:
        logger.error(f"Failed to store rejected question: {str(e)}")
        return False
