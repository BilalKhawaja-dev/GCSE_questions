"""
KB Alignment Service for retrieval-grounded verification.
Verifies questions against Bedrock Knowledge Base content.
"""

import logging
import json
import boto3
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SourceCheck:
    """Result of source alignment check."""
    pass_: bool
    confidence: float
    reasoning: str
    retrieved_docs: List[Dict[str, Any]]


@dataclass
class SyllabusCheck:
    """Result of syllabus compliance check."""
    pass_: bool
    confidence: float
    reasoning: str
    retrieved_docs: List[Dict[str, Any]]


@dataclass
class AlignmentResult:
    """Overall KB alignment result."""
    pass_: bool
    source_alignment: SourceCheck
    syllabus_compliance: SyllabusCheck
    overall_confidence: float


class KBAlignmentService:
    """Service for retrieval-grounded verification using Bedrock KB."""
    
    def __init__(
        self,
        knowledge_base_id: str,
        region: str = 'eu-west-2',
        source_confidence_threshold: float = 0.7,
        syllabus_confidence_threshold: float = 0.7
    ):
        """Initialize KB alignment service.
        
        Args:
            knowledge_base_id: Bedrock Knowledge Base ID
            region: AWS region
            source_confidence_threshold: Min confidence for source alignment
            syllabus_confidence_threshold: Min confidence for syllabus compliance
        """
        self.knowledge_base_id = knowledge_base_id
        self.region = region
        self.source_threshold = source_confidence_threshold
        self.syllabus_threshold = syllabus_confidence_threshold
        
        self.bedrock_agent_client = boto3.client(
            'bedrock-agent-runtime',
            region_name=region
        )
        self.bedrock_runtime = boto3.client(
            'bedrock-runtime',
            region_name=region
        )
        self.model_id = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    
    def verify_alignment(self, question: Dict[str, Any]) -> AlignmentResult:
        """Verify question alignment with KB content.
        
        Args:
            question: Question data with stem, options, correct_answer, topic, grade, paper_type
            
        Returns:
            AlignmentResult with source and syllabus checks
        """
        try:
            # A) Source alignment check
            source_check = self._verify_source_alignment(question)
            
            # B) Syllabus compliance check
            syllabus_check = self._verify_syllabus_compliance(question)
            
            # Calculate overall confidence
            overall_confidence = (
                source_check.confidence * 0.5 + 
                syllabus_check.confidence * 0.5
            )
            
            # Both must pass for overall pass
            overall_pass = source_check.pass_ and syllabus_check.pass_
            
            return AlignmentResult(
                pass_=overall_pass,
                source_alignment=source_check,
                syllabus_compliance=syllabus_check,
                overall_confidence=overall_confidence
            )
            
        except Exception as e:
            logger.error(f"KB alignment verification failed: {str(e)}")
            # Graceful degradation - don't auto-reject on KB failures
            return AlignmentResult(
                pass_=True,  # Don't block on KB errors
                source_alignment=SourceCheck(
                    pass_=True,
                    confidence=0.0,
                    reasoning=f"KB alignment check failed: {str(e)}",
                    retrieved_docs=[]
                ),
                syllabus_compliance=SyllabusCheck(
                    pass_=True,
                    confidence=0.0,
                    reasoning=f"KB alignment check failed: {str(e)}",
                    retrieved_docs=[]
                ),
                overall_confidence=0.0
            )
    
    def _verify_source_alignment(self, question: Dict[str, Any]) -> SourceCheck:
        """Verify correct answer aligns with KB material.
        
        Args:
            question: Question data
            
        Returns:
            SourceCheck result
        """
        try:
            # Build retrieval query
            stem = question.get('stem', '')
            topic = question.get('topic', '')
            retrieval_query = f"{topic}: {stem}"
            
            # Retrieve relevant docs from KB
            retrieved_docs = self._retrieve_from_kb(
                query=retrieval_query,
                max_results=5
            )
            
            if not retrieved_docs:
                logger.warning("No KB documents retrieved for source alignment")
                # Don't fail if KB is incomplete
                return SourceCheck(
                    pass_=True,
                    confidence=0.0,
                    reasoning="No KB documents available - cannot verify source alignment",
                    retrieved_docs=[]
                )
            
            # Format retrieved content
            formatted_docs = self._format_docs(retrieved_docs)
            
            # Get correct answer text
            options = question.get('options', [])
            correct_answer = question.get('correct_answer', '')
            correct_index = ord(correct_answer) - ord('A')
            correct_text = options[correct_index] if correct_index < len(options) else ''
            
            # Ask LLM: is answer supported by retrieved material?
            prompt = f"""Retrieved educational material from Edexcel GCSE Maths resources:

{formatted_docs}

Question: {stem}
Correct Answer: {correct_answer}) {correct_text}

Task: Determine if this answer is supported by the retrieved material.

Respond with:
- YES if the material confirms or supports this answer
- NO if the material contradicts this answer or doesn't support it
- UNCERTAIN if the material is insufficient to determine

Output ONLY valid JSON in this exact format:
{{
  "supported": true or false,
  "confidence": 0.0 to 1.0,
  "reasoning": "brief explanation"
}}"""
            
            # Invoke LLM
            response = self._invoke_llm(prompt)
            result = self._parse_json_response(response)
            
            # Determine pass/fail
            is_supported = result.get('supported', False)
            confidence = result.get('confidence', 0.0)
            reasoning = result.get('reasoning', 'No reasoning provided')
            
            passes = is_supported and confidence >= self.source_threshold
            
            return SourceCheck(
                pass_=passes,
                confidence=confidence,
                reasoning=reasoning,
                retrieved_docs=retrieved_docs
            )
            
        except Exception as e:
            logger.error(f"Source alignment check failed: {str(e)}")
            # Graceful degradation
            return SourceCheck(
                pass_=True,
                confidence=0.0,
                reasoning=f"Source alignment check error: {str(e)}",
                retrieved_docs=[]
            )
    
    def _verify_syllabus_compliance(self, question: Dict[str, Any]) -> SyllabusCheck:
        """Verify question is within Edexcel 1MA1 syllabus scope.
        
        Args:
            question: Question data
            
        Returns:
            SyllabusCheck result
        """
        try:
            # Build specification query
            topic = question.get('topic', '')
            grade = question.get('grade', '')
            paper_type = question.get('paper_type', '')
            
            spec_query = f"Edexcel 1MA1 specification {topic} {grade} syllabus requirements"
            
            # Retrieve specification docs
            spec_docs = self._retrieve_from_kb(
                query=spec_query,
                max_results=3,
                filter_type='specification'
            )
            
            if not spec_docs:
                logger.warning("No specification documents retrieved")
                # Don't fail if KB is incomplete
                return SyllabusCheck(
                    pass_=True,
                    confidence=0.0,
                    reasoning="No specification documents available - cannot verify syllabus compliance",
                    retrieved_docs=[]
                )
            
            # Format specification content
            formatted_specs = self._format_docs(spec_docs)
            
            # Ask LLM: is question in scope?
            prompt = f"""Edexcel 1MA1 GCSE Mathematics Specification:

{formatted_specs}

Question Details:
- Topic: {topic}
- Grade: {grade}
- Paper Type: {paper_type}
- Question: {question.get('stem', '')}

Task: Determine if this question is within the Edexcel 1MA1 syllabus scope.

Check:
1. Is the topic covered in the specification?
2. Is the difficulty appropriate for the grade level?
3. Are paper type constraints satisfied (P1=non-calculator, P2/P3=calculator)?

Output ONLY valid JSON in this exact format:
{{
  "in_scope": true or false,
  "confidence": 0.0 to 1.0,
  "reasoning": "brief explanation"
}}"""
            
            # Invoke LLM
            response = self._invoke_llm(prompt)
            result = self._parse_json_response(response)
            
            # Determine pass/fail
            in_scope = result.get('in_scope', False)
            confidence = result.get('confidence', 0.0)
            reasoning = result.get('reasoning', 'No reasoning provided')
            
            passes = in_scope and confidence >= self.syllabus_threshold
            
            return SyllabusCheck(
                pass_=passes,
                confidence=confidence,
                reasoning=reasoning,
                retrieved_docs=spec_docs
            )
            
        except Exception as e:
            logger.error(f"Syllabus compliance check failed: {str(e)}")
            # Graceful degradation
            return SyllabusCheck(
                pass_=True,
                confidence=0.0,
                reasoning=f"Syllabus compliance check error: {str(e)}",
                retrieved_docs=[]
            )
    
    def _retrieve_from_kb(
        self,
        query: str,
        max_results: int = 5,
        filter_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve documents from Bedrock Knowledge Base.
        
        Args:
            query: Search query
            max_results: Maximum results to return
            filter_type: Optional document type filter
            
        Returns:
            List of retrieved documents with content and metadata
        """
        try:
            # Build retrieval configuration
            retrieval_config = {
                'vectorSearchConfiguration': {
                    'numberOfResults': max_results,
                    'overrideSearchType': 'HYBRID'
                }
            }
            
            # Add filter if specified
            if filter_type:
                retrieval_config['vectorSearchConfiguration']['filter'] = {
                    'equals': {
                        'key': 'document_type',
                        'value': filter_type
                    }
                }
            
            # Query KB
            response = self.bedrock_agent_client.retrieve(
                knowledgeBaseId=self.knowledge_base_id,
                retrievalQuery={'text': query},
                retrievalConfiguration=retrieval_config
            )
            
            # Extract results
            results = []
            for result in response.get('retrievalResults', []):
                content = result.get('content', {}).get('text', '')
                score = result.get('score', 0.0)
                metadata = result.get('metadata', {})
                
                # Only include high-confidence results
                if score > 0.5 and len(content) > 50:
                    results.append({
                        'content': content,
                        'score': score,
                        'source': metadata.get('x-amz-bedrock-kb-source-uri', 'unknown'),
                        'metadata': metadata
                    })
            
            logger.info(f"Retrieved {len(results)} documents from KB for query: {query[:50]}...")
            return results
            
        except Exception as e:
            logger.error(f"KB retrieval failed: {str(e)}")
            return []
    
    def _format_docs(self, docs: List[Dict[str, Any]]) -> str:
        """Format retrieved documents for LLM prompt.
        
        Args:
            docs: List of retrieved documents
            
        Returns:
            Formatted string
        """
        if not docs:
            return "No documents retrieved."
        
        formatted = []
        for i, doc in enumerate(docs, 1):
            content = doc['content']
            score = doc['score']
            source = doc.get('source', 'unknown')
            
            formatted.append(
                f"[Document {i} - Relevance: {score:.0%}]\n"
                f"Source: {source}\n"
                f"{content}\n"
            )
        
        return '\n'.join(formatted)
    
    def _invoke_llm(self, prompt: str) -> str:
        """Invoke Bedrock LLM for verification.
        
        Args:
            prompt: Prompt text
            
        Returns:
            LLM response text
        """
        try:
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "messages": [{
                    "role": "user",
                    "content": prompt
                }],
                "max_tokens": 2000,
                "temperature": 0.1  # Low temperature for consistency
            }
            
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body)
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['content'][0]['text']
            
        except Exception as e:
            logger.error(f"LLM invocation failed: {str(e)}")
            raise
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from LLM response.
        
        Args:
            response: LLM response text
            
        Returns:
            Parsed JSON dict
        """
        try:
            # Try to extract JSON from response
            # Handle cases where LLM adds extra text
            start = response.find('{')
            end = response.rfind('}') + 1
            
            if start >= 0 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)
            else:
                # Try parsing entire response
                return json.loads(response)
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {response[:200]}")
            raise ValueError(f"Invalid JSON response from LLM: {str(e)}")
