"""
LLM Auditor Service - Semantic validation for GCSE Maths questions.

This service uses Bedrock Claude to perform hostile auditing of questions,
checking for ambiguity, wording issues, and paper constraint violations.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class AuditResult:
    """Result from LLM auditor."""
    verdict: str  # "PASS" or "FAIL"
    solved_answer: str  # A, B, C, or D
    key_answer: str  # The provided answer key
    agreement: bool  # Does solved answer match key?
    ambiguity: str  # "none", "multiple-correct", "unclear-stem", "missing-info"
    issues: List[str]  # List of specific problems found
    confidence: float  # 0.0 to 1.0
    working: Optional[str] = None  # LLM's solution steps
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class LLMAuditor:
    """
    LLM-based auditor for semantic validation of GCSE Maths questions.
    
    Uses Bedrock Claude to:
    - Solve questions independently
    - Check for ambiguity and wording issues
    - Verify paper constraints
    - Provide structured feedback
    """
    
    def __init__(self, bedrock_client, model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"):
        """
        Initialize LLM auditor.
        
        Args:
            bedrock_client: Boto3 Bedrock Runtime client
            model_id: Bedrock model ID to use
        """
        self.bedrock = bedrock_client
        self.model_id = model_id
        self.confidence_threshold = 0.75
        self.max_retries = 3
    
    def audit(self, question: Dict[str, Any]) -> AuditResult:
        """
        Audit a question for semantic correctness.
        
        Args:
            question: Question dictionary with keys:
                - stem: Question text
                - options: List of 4 option strings
                - correct_answer: "A", "B", "C", or "D"
                - paper_type: "P1", "P2", or "P3"
                - topic: Topic name (optional)
                - grade: "foundation" or "higher" (optional)
        
        Returns:
            AuditResult with verdict and detailed feedback
        """
        try:
            # Build prompt
            prompt = self._build_auditor_prompt(question)
            
            # Call Bedrock with retries
            response = self._invoke_bedrock_with_retry(prompt)
            
            # Parse structured output
            result = self._parse_structured_output(response)
            
            # Validate result
            if not self._validate_audit_result(result):
                logger.warning(f"Invalid audit result structure: {result}")
                return self._create_error_result(
                    question,
                    "Invalid audit result structure"
                )
            
            # Apply pass rules
            result.verdict = self._apply_pass_rules(result)
            
            return result
            
        except Exception as e:
            logger.error(f"LLM auditor error: {str(e)}", exc_info=True)
            return self._create_error_result(question, str(e))
    
    def _build_auditor_prompt(self, question: Dict[str, Any]) -> str:
        """Build the hostile auditor prompt."""
        stem = question.get('stem', '')
        options = question.get('options', [])
        correct_answer = question.get('correct_answer', '')
        paper_type = question.get('paper_type', 'P2')
        topic = question.get('topic', 'unknown')
        grade = question.get('grade', 'foundation')
        
        # Format options
        option_labels = ['A', 'B', 'C', 'D']
        formatted_options = '\n'.join([
            f"{label}) {opt}" 
            for label, opt in zip(option_labels, options[:4])
        ])
        
        # Paper type description
        paper_desc = "(NON-CALCULATOR)" if paper_type == "P1" else "(CALCULATOR)"
        
        prompt = f"""You are a hostile auditor for GCSE Maths questions.

Your job: solve this question independently, then check for issues.

QUESTION:
{stem}

OPTIONS:
{formatted_options}

PROVIDED ANSWER KEY: {correct_answer}

PAPER TYPE: {paper_type} {paper_desc}
TOPIC: {topic}
GRADE: {grade}

INSTRUCTIONS:
1. Solve the question from scratch WITHOUT looking at the answer key
2. Show your working
3. State your final answer (A/B/C/D)
4. NOW compare to the provided key
5. Check for ambiguity (could multiple answers be valid?)
6. Check for wording issues (missing info, unclear, diagram-dependent)
7. Check paper constraints (P1 must be doable without calculator)

OUTPUT (strict JSON):
{{
  "solved_answer": "A|B|C|D",
  "working": "your solution steps",
  "key_answer": "{correct_answer}",
  "agreement": true|false,
  "ambiguity": "none|multiple-correct|unclear-stem|missing-info",
  "issues": ["list specific problems or empty array"],
  "confidence": 0.0-1.0,
  "verdict": "PASS|FAIL"
}}

PASS CRITERIA:
- agreement = true
- ambiguity = "none"
- confidence >= 0.75
- issues = [] or minor only
- Paper constraints satisfied

Be strict. If unsure, FAIL with low confidence.

IMPORTANT: Return ONLY the JSON object, no other text."""
        
        return prompt
    
    def _invoke_bedrock_with_retry(self, prompt: str) -> str:
        """
        Invoke Bedrock with retry logic.
        
        Args:
            prompt: The prompt to send
            
        Returns:
            Response text from the model
        """
        import time
        
        for attempt in range(self.max_retries):
            try:
                response = self.bedrock.invoke_model(
                    modelId=self.model_id,
                    body=json.dumps({
                        "anthropic_version": "bedrock-2023-05-31",
                        "messages": [{
                            "role": "user",
                            "content": prompt
                        }],
                        "max_tokens": 2000,
                        "temperature": 0.1  # Low temp for consistency
                    })
                )
                
                # Parse response
                response_body = json.loads(response['body'].read())
                content = response_body.get('content', [])
                
                if content and len(content) > 0:
                    return content[0].get('text', '')
                
                logger.warning(f"Empty response from Bedrock on attempt {attempt + 1}")
                
            except Exception as e:
                logger.warning(f"Bedrock invocation failed on attempt {attempt + 1}: {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise
        
        raise Exception("Failed to get response from Bedrock after retries")
    
    def _parse_structured_output(self, response_text: str) -> AuditResult:
        """
        Parse structured JSON output from LLM.
        
        Args:
            response_text: Raw text response from LLM
            
        Returns:
            AuditResult object
        """
        try:
            # Try to extract JSON from response
            # Sometimes LLM adds extra text, so we need to find the JSON
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in response")
            
            json_str = response_text[json_start:json_end]
            data = json.loads(json_str)
            
            # Create AuditResult
            return AuditResult(
                verdict=data.get('verdict', 'FAIL'),
                solved_answer=data.get('solved_answer', ''),
                key_answer=data.get('key_answer', ''),
                agreement=data.get('agreement', False),
                ambiguity=data.get('ambiguity', 'unclear-stem'),
                issues=data.get('issues', []),
                confidence=float(data.get('confidence', 0.0)),
                working=data.get('working', '')
            )
            
        except Exception as e:
            logger.error(f"Failed to parse LLM output: {str(e)}")
            logger.error(f"Response text: {response_text}")
            raise ValueError(f"Failed to parse structured output: {str(e)}")
    
    def _validate_audit_result(self, result: AuditResult) -> bool:
        """
        Validate that audit result has required fields.
        
        Args:
            result: AuditResult to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Check required fields
        if not result.solved_answer or result.solved_answer not in ['A', 'B', 'C', 'D']:
            return False
        
        if not result.key_answer or result.key_answer not in ['A', 'B', 'C', 'D']:
            return False
        
        if result.ambiguity not in ['none', 'multiple-correct', 'unclear-stem', 'missing-info']:
            return False
        
        if not isinstance(result.issues, list):
            return False
        
        if not (0.0 <= result.confidence <= 1.0):
            return False
        
        return True
    
    def _apply_pass_rules(self, result: AuditResult) -> str:
        """
        Apply pass/fail rules to audit result.
        
        Args:
            result: AuditResult to evaluate
            
        Returns:
            "PASS" or "FAIL"
        """
        # Pass criteria:
        # 1. Agreement = true
        # 2. Ambiguity = "none"
        # 3. Confidence >= threshold
        # 4. Issues empty or minor only
        
        if not result.agreement:
            return "FAIL"
        
        if result.ambiguity != "none":
            return "FAIL"
        
        if result.confidence < self.confidence_threshold:
            return "FAIL"
        
        # Check for major issues
        major_issue_keywords = [
            'calculator', 'diagram', 'missing', 'unclear',
            'ambiguous', 'multiple correct', 'insufficient'
        ]
        
        for issue in result.issues:
            issue_lower = issue.lower()
            if any(keyword in issue_lower for keyword in major_issue_keywords):
                return "FAIL"
        
        return "PASS"
    
    def _create_error_result(self, question: Dict[str, Any], error_msg: str) -> AuditResult:
        """
        Create an error result when auditing fails.
        
        Args:
            question: Original question
            error_msg: Error message
            
        Returns:
            AuditResult with FAIL verdict
        """
        return AuditResult(
            verdict="FAIL",
            solved_answer="",
            key_answer=question.get('correct_answer', ''),
            agreement=False,
            ambiguity="unclear-stem",
            issues=[f"Audit error: {error_msg}"],
            confidence=0.0,
            working=None
        )
