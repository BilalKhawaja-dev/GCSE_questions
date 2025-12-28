"""
Bedrock service for AI model interactions.

This service handles communication with AWS Bedrock models including
Claude Haiku for query interpretation and Claude Sonnet for question generation.
"""

import json
import logging
import re
import time
from typing import Dict, Any, Optional, List
import boto3
from botocore.exceptions import ClientError, BotoCoreError

from src.models.query_intent import QueryIntent
from src.models.question import Question
from src.models.mark_scheme import MarkScheme
from src.utils.constants import VALID_TOPICS, VALID_TIERS

logger = logging.getLogger(__name__)


class BedrockService:
    """Service for interacting with AWS Bedrock models."""
    
    def __init__(self, region: str = 'eu-west-2'):
        """Initialize Bedrock service with proper client configuration."""
        self.region = region
        self.client = boto3.client('bedrock-runtime', region_name=region)
        
        # Get model ID from environment variable (different for each Lambda)
        import os
        self.model_id = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-haiku-20240307-v1:0')
        
    def parse_query_with_haiku(self, query: str, request_id: str) -> QueryIntent:
        """
        Parse natural language query using Claude Haiku.
        
        Args:
            query: Sanitized natural language query
            request_id: Request ID for logging
            
        Returns:
            QueryIntent with parsed components
            
        Raises:
            Exception: If parsing fails after retries
        """
        logger.info(
            "Starting query parsing with Claude Haiku",
            extra={"request_id": request_id, "query_length": len(query)}
        )
        
        prompt = self._construct_interpretation_prompt(query)
        
        # Call Bedrock with retry logic
        response = self._call_bedrock_with_retry(
            model_id=self.model_id,
            prompt=prompt,
            request_id=request_id,
            max_tokens=1000,
            temperature=0.1
        )
        
        # Parse the response into QueryIntent
        intent = self._parse_haiku_response(response, query, request_id)
        
        logger.info(
            "Query parsing completed",
            extra={
                "request_id": request_id,
                "topic": intent.topic,
                "tier": intent.tier,
                "count": intent.count,
                "confidence": intent.confidence
            }
        )
        
        return intent
    
    def _construct_interpretation_prompt(self, query: str) -> str:
        """Construct structured prompt for query interpretation."""
        return f"""You are an expert at parsing natural language queries about GCSE mathematics questions.

Your task is to extract structured information from the user's query and return it as JSON.

Valid topics: {', '.join(VALID_TOPICS)}
Valid tiers: Foundation, Higher

Extract the following information:
1. topic: The main GCSE math topic (must be one of the valid topics above)
2. subtopic: More specific subtopic if mentioned (e.g., "fractions", "linear equations")
3. tier: Difficulty level (Foundation or Higher)
4. count: Number of questions requested (1-50)
5. marks: Total marks if specified (optional)

User query: "{query}"

Rules:
- If tier is not explicitly mentioned, infer from context or default to "Foundation"
- If count is not specified, default to 5
- If topic cannot be determined, use "Number" as default
- Be conservative with confidence scoring

Return ONLY a JSON object with this exact structure:
{{
    "topic": "string",
    "subtopic": "string or null",
    "tier": "Foundation or Higher",
    "count": number,
    "marks": number or null,
    "confidence": number between 0.0 and 1.0
}}"""

    def _call_bedrock_with_retry(
        self,
        model_id: str,
        prompt: str,
        request_id: str,
        max_tokens: int = 4000,
        temperature: float = 0.1,
        max_retries: int = 3
    ) -> str:
        """
        Call Bedrock API with exponential backoff retry logic.
        
        Args:
            model_id: Bedrock model identifier
            prompt: Input prompt for the model
            request_id: Request ID for logging
            max_tokens: Maximum tokens to generate
            temperature: Model temperature setting
            max_retries: Maximum number of retry attempts
            
        Returns:
            Model response text
            
        Raises:
            Exception: If all retries fail
        """
        for attempt in range(max_retries + 1):
            try:
                logger.info(
                    f"Calling Bedrock API (attempt {attempt + 1})",
                    extra={
                        "request_id": request_id,
                        "model_id": model_id,
                        "attempt": attempt + 1
                    }
                )
                
                # Prepare request body for InvokeModel API
                request_body = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "top_p": 0.9,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                }
                
                response = self.client.invoke_model(
                    modelId=model_id,
                    body=json.dumps(request_body),
                    contentType='application/json',
                    accept='application/json'
                )
                
                # Parse response
                response_body = json.loads(response['body'].read())
                response_text = response_body['content'][0]['text']
                
                logger.info(
                    "Bedrock API call successful",
                    extra={
                        "request_id": request_id,
                        "response_length": len(response_text),
                        "attempt": attempt + 1
                    }
                )
                
                return response_text
                
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                error_message = e.response.get('Error', {}).get('Message', str(e))
                
                logger.warning(
                    f"Bedrock API error (attempt {attempt + 1})",
                    extra={
                        "request_id": request_id,
                        "error_code": error_code,
                        "error_message": error_message,
                        "attempt": attempt + 1,
                        "full_error": str(e)
                    }
                )
                
                if attempt == max_retries:
                    raise Exception(f"Bedrock API failed after {max_retries + 1} attempts: {error_message}")
                
                # Exponential backoff with jitter
                wait_time = (2 ** attempt) + (time.time() % 1)
                time.sleep(wait_time)
                
            except BotoCoreError as e:
                logger.warning(
                    f"Boto3 error (attempt {attempt + 1})",
                    extra={
                        "request_id": request_id,
                        "error": str(e),
                        "attempt": attempt + 1,
                        "error_type": type(e).__name__
                    }
                )
                
                if attempt == max_retries:
                    raise Exception(f"Boto3 error after {max_retries + 1} attempts: {str(e)}")
                
                wait_time = (2 ** attempt) + (time.time() % 1)
                time.sleep(wait_time)
                
            except Exception as e:
                logger.error(
                    f"Unexpected error calling Bedrock (attempt {attempt + 1})",
                    extra={
                        "request_id": request_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "attempt": attempt + 1,
                        "model_id": model_id
                    }
                )
                
                if attempt == max_retries:
                    raise Exception(f"Unexpected error after {max_retries + 1} attempts: {str(e)}")
                
                wait_time = (2 ** attempt) + (time.time() % 1)
                time.sleep(wait_time)
    
    def _parse_haiku_response(self, response: str, original_query: str, request_id: str) -> QueryIntent:
        """
        Parse Claude Haiku response into QueryIntent object.
        
        Args:
            response: Raw response from Claude Haiku
            original_query: Original user query for confidence calculation
            request_id: Request ID for logging
            
        Returns:
            QueryIntent object with parsed data
            
        Raises:
            Exception: If response cannot be parsed
        """
        try:
            # Extract JSON from response (handle potential markdown formatting)
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                raise ValueError("No JSON found in response")
            
            json_str = json_match.group(0)
            parsed_data = json.loads(json_str)
            
            # Validate required fields
            required_fields = ['topic', 'tier', 'count', 'confidence']
            for field in required_fields:
                if field not in parsed_data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Validate topic
            topic = parsed_data['topic']
            if topic not in VALID_TOPICS:
                logger.warning(
                    f"Invalid topic '{topic}' returned by model, defaulting to 'Number'",
                    extra={"request_id": request_id}
                )
                topic = "Number"
            
            # Validate tier
            tier = parsed_data['tier']
            if tier not in VALID_TIERS:
                logger.warning(
                    f"Invalid tier '{tier}' returned by model, defaulting to 'Foundation'",
                    extra={"request_id": request_id}
                )
                tier = "Foundation"
            
            # Validate count
            count = int(parsed_data['count'])
            if not (1 <= count <= 50):
                logger.warning(
                    f"Invalid count '{count}' returned by model, defaulting to 5",
                    extra={"request_id": request_id}
                )
                count = 5
            
            # Calculate final confidence score
            model_confidence = float(parsed_data['confidence'])
            final_confidence = self._calculate_confidence_score(
                topic, tier, count, original_query, model_confidence
            )
            
            # Create QueryIntent
            intent = QueryIntent(
                topic=topic,
                tier=tier,
                count=count,
                confidence=final_confidence,
                subtopic=parsed_data.get('subtopic'),
                marks=parsed_data.get('marks'),
                specification_version="latest"
            )
            
            logger.info(
                "Successfully parsed Haiku response",
                extra={
                    "request_id": request_id,
                    "parsed_topic": topic,
                    "parsed_tier": tier,
                    "parsed_count": count,
                    "final_confidence": final_confidence
                }
            )
            
            return intent
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(
                "Failed to parse Haiku response",
                extra={
                    "request_id": request_id,
                    "error": str(e),
                    "response_preview": response[:200] + "..." if len(response) > 200 else response
                }
            )
            raise Exception(f"Failed to parse model response: {str(e)}")
    
    def _calculate_confidence_score(
        self,
        topic: str,
        tier: str,
        count: int,
        original_query: str,
        model_confidence: float
    ) -> float:
        """
        Calculate final confidence score based on parsing quality.
        
        Args:
            topic: Parsed topic
            tier: Parsed tier
            count: Parsed count
            original_query: Original user query
            model_confidence: Confidence from model
            
        Returns:
            Final confidence score (0.0-1.0)
        """
        confidence = model_confidence
        query_lower = original_query.lower()
        
        # Reduce confidence if topic not mentioned in query
        topic_keywords = {
            "Number": ["number", "fraction", "decimal", "percentage", "integer"],
            "Algebra": ["algebra", "equation", "expression", "formula", "solve"],
            "Geometry": ["geometry", "angle", "shape", "area", "perimeter", "triangle"],
            "Statistics": ["statistics", "data", "graph", "chart", "mean", "median"],
            "Probability": ["probability", "chance", "likely", "random"],
            "Ratio": ["ratio", "proportion", "scale"]
        }
        
        topic_found = any(keyword in query_lower for keyword in topic_keywords.get(topic, []))
        if not topic_found:
            confidence -= 0.2
        
        # Reduce confidence if tier not explicitly mentioned
        tier_keywords = ["foundation", "higher", "basic", "advanced"]
        tier_found = any(keyword in query_lower for keyword in tier_keywords)
        if not tier_found:
            confidence -= 0.1
        
        # Reduce confidence if count not mentioned
        if not re.search(r'\d+', original_query):
            confidence -= 0.1
        
        # Ensure confidence is within valid range
        return max(0.0, min(1.0, confidence))
    
    def generate_questions_with_sonnet(self, generation_request: Dict[str, Any], 
                                     spec_content: Dict[str, Any], 
                                     examples_content: List[Dict[str, Any]], 
                                     request_id: str) -> Dict[str, Any]:
        """
        Generate questions and mark schemes using Claude Sonnet.
        
        Args:
            generation_request: Validated generation request
            spec_content: Specification content from S3
            examples_content: Seed examples from S3
            request_id: Request ID for logging
            
        Returns:
            Generated question set with questions, mark schemes, and metadata
            
        Raises:
            Exception: If generation fails after retries
        """
        logger.info(
            "Starting question generation with Claude Sonnet",
            extra={
                "request_id": request_id,
                "topic": generation_request.get('topic'),
                "tier": generation_request.get('tier'),
                "count": generation_request.get('count'),
                "examples_count": len(examples_content)
            }
        )
        
        prompt = self._construct_generation_prompt(
            generation_request, spec_content, examples_content
        )
        
        # Call Bedrock with retry logic
        response = self._call_bedrock_with_retry(
            model_id=self.model_id,
            prompt=prompt,
            request_id=request_id,
            max_tokens=4000,
            temperature=0.1
        )
        
        # Parse the response into structured question set
        question_set = self._parse_sonnet_response(response, generation_request, request_id)
        
        # Validate question quality
        validated_question_set = self._validate_question_quality(question_set, generation_request, request_id)
        
        logger.info(
            "Question generation completed",
            extra={
                "request_id": request_id,
                "generated_count": len(validated_question_set['questions']),
                "total_marks": validated_question_set['metadata']['total_marks']
            }
        )
        
        return validated_question_set
    
    def _construct_generation_prompt(self, generation_request: Dict[str, Any], 
                                   spec_content: Dict[str, Any], 
                                   examples_content: List[Dict[str, Any]]) -> str:
        """Construct structured prompt for question generation."""
        
        # Format examples for the prompt
        examples_text = ""
        if examples_content:
            examples_text = "\n\nSeed Examples:\n"
            for i, example in enumerate(examples_content[:3], 1):  # Limit to 3 examples
                question = example.get('question', {})
                mark_scheme = example.get('mark_scheme', {})
                examples_text += f"""
Example {i}:
Question: {question.get('question_text', 'N/A')}
Marks: {question.get('marks', 'N/A')}
Mark Scheme: {mark_scheme.get('marking_criteria', 'N/A')}
"""
        
        # Format specification content
        spec_text = f"""
Specification Content:
Topic: {spec_content.get('subtopic', generation_request.get('topic'))}
Tier: {generation_request.get('tier')}
Learning Objectives: {', '.join(spec_content.get('learning_objectives', []))}
Key Concepts: {', '.join(spec_content.get('key_concepts', []))}
Content: {spec_content.get('specification_content', 'No specific content available')}
"""
        
        return f"""You are an expert GCSE mathematics question writer. Generate {generation_request.get('count')} high-quality exam questions based on the specification and examples provided.

{spec_text}{examples_text}

Requirements:
1. Generate exactly {generation_request.get('count')} questions
2. Each question must be appropriate for {generation_request.get('tier')} tier
3. Questions must align with the specification content and learning objectives
4. Include detailed mark schemes with method and accuracy marks
5. Use clear mathematical notation: fractions as 3/4 or (3/4), powers as x² or x^2, square roots as √16 or sqrt(16)
- For complex expressions, use LaTeX only when necessary: \\frac{3}{4}, x^2, \\sqrt{16}
- Prioritize human readability over LaTeX formatting
6. Ensure questions test the key concepts listed in the specification
7. Vary question difficulty within the tier level
8. Make questions realistic and practical where possible

Return your response as a JSON object with this exact structure:
{{
    "questions": [
        {{
            "id": "q1",
            "question_text": "Question text with LaTeX notation",
            "marks": 3,
            "tier": "{generation_request.get('tier')}",
            "topic": "{generation_request.get('topic')}",
            "subtopic": "{generation_request.get('subtopic', '')}"
        }}
    ],
    "mark_scheme": [
        {{
            "question_id": "q1",
            "marking_criteria": "M1: Method mark description, A1: Accuracy mark description",
            "method_marks": 2,
            "accuracy_marks": 1
        }}
    ],
    "metadata": {{
        "generated_at": "{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}",
        "model_version": "claude-3-sonnet-20240229",
        "total_marks": 0,
        "specification_version": "{generation_request.get('specification_version', 'latest')}"
    }}
}}

Ensure the JSON is valid and complete. The total_marks in metadata should equal the sum of all question marks."""
    
    def _parse_sonnet_response(self, response: str, generation_request: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """
        Parse Claude Sonnet response into structured question set.
        
        Args:
            response: Raw response from Claude Sonnet
            generation_request: Original generation request
            request_id: Request ID for logging
            
        Returns:
            Structured question set dictionary
            
        Raises:
            Exception: If response cannot be parsed
        """
        try:
            # Extract JSON from response (handle potential markdown formatting)
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                raise ValueError("No JSON found in response")
            
            json_str = json_match.group(0)
            parsed_data = json.loads(json_str)
            
            # Validate required top-level fields
            required_fields = ['questions', 'mark_scheme', 'metadata']
            for field in required_fields:
                if field not in parsed_data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Validate questions structure
            questions = parsed_data['questions']
            if not isinstance(questions, list):
                raise ValueError("Questions must be a list")
            
            if len(questions) != generation_request.get('count', 0):
                logger.warning(
                    f"Generated {len(questions)} questions, expected {generation_request.get('count')}",
                    extra={"request_id": request_id}
                )
            
            # Validate each question
            for i, question in enumerate(questions):
                required_q_fields = ['id', 'question_text', 'marks', 'tier', 'topic']
                for field in required_q_fields:
                    if field not in question:
                        raise ValueError(f"Question {i+1} missing required field: {field}")
                
                # Validate marks is positive integer
                if not isinstance(question['marks'], int) or question['marks'] < 1:
                    raise ValueError(f"Question {i+1} has invalid marks: {question['marks']}")
            
            # Validate mark schemes
            mark_schemes = parsed_data['mark_scheme']
            if not isinstance(mark_schemes, list):
                raise ValueError("Mark scheme must be a list")
            
            if len(mark_schemes) != len(questions):
                raise ValueError(f"Mark scheme count ({len(mark_schemes)}) doesn't match question count ({len(questions)})")
            
            # Validate each mark scheme
            for i, mark_scheme in enumerate(mark_schemes):
                required_ms_fields = ['question_id', 'marking_criteria', 'method_marks', 'accuracy_marks']
                for field in required_ms_fields:
                    if field not in mark_scheme:
                        raise ValueError(f"Mark scheme {i+1} missing required field: {field}")
                
                # Validate marks are non-negative integers
                method_marks = mark_scheme['method_marks']
                accuracy_marks = mark_scheme['accuracy_marks']
                
                if not isinstance(method_marks, int) or method_marks < 0:
                    raise ValueError(f"Mark scheme {i+1} has invalid method marks: {method_marks}")
                
                if not isinstance(accuracy_marks, int) or accuracy_marks < 0:
                    raise ValueError(f"Mark scheme {i+1} has invalid accuracy marks: {accuracy_marks}")
                
                # Check total marks consistency
                total_marks = method_marks + accuracy_marks
                corresponding_question = next((q for q in questions if q['id'] == mark_scheme['question_id']), None)
                if corresponding_question and corresponding_question['marks'] != total_marks:
                    logger.warning(
                        f"Mark scheme total ({total_marks}) doesn't match question marks ({corresponding_question['marks']}) for question {mark_scheme['question_id']}",
                        extra={"request_id": request_id}
                    )
            
            # Calculate and update total marks in metadata
            total_marks = sum(q['marks'] for q in questions)
            parsed_data['metadata']['total_marks'] = total_marks
            parsed_data['metadata']['request_id'] = request_id
            
            logger.info(
                "Successfully parsed Sonnet response",
                extra={
                    "request_id": request_id,
                    "question_count": len(questions),
                    "total_marks": total_marks
                }
            )
            
            return parsed_data
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(
                "Failed to parse Sonnet response",
                extra={
                    "request_id": request_id,
                    "error": str(e),
                    "response_preview": response[:500] + "..." if len(response) > 500 else response
                }
            )
            raise Exception(f"Failed to parse model response: {str(e)}")
    
    def _validate_question_quality(self, question_set: Dict[str, Any], 
                                 generation_request: Dict[str, Any], 
                                 request_id: str) -> Dict[str, Any]:
        """
        Validate generated question quality and alignment with requirements.
        
        Args:
            question_set: Generated question set
            generation_request: Original generation request
            request_id: Request ID for logging
            
        Returns:
            Validated question set with quality metrics
        """
        logger.info(
            "Validating question quality",
            extra={"request_id": request_id, "question_count": len(question_set['questions'])}
        )
        
        validation_results = []
        
        for question in question_set['questions']:
            result = self._validate_single_question(question, generation_request, request_id)
            validation_results.append(result)
        
        # Add quality metrics to metadata
        question_set['metadata']['quality_validation'] = {
            'average_confidence': sum(r['confidence'] for r in validation_results) / len(validation_results),
            'validation_errors': [r['errors'] for r in validation_results if r['errors']],
            'all_questions_valid': all(r['is_valid'] for r in validation_results)
        }
        
        logger.info(
            "Question quality validation completed",
            extra={
                "request_id": request_id,
                "average_confidence": question_set['metadata']['quality_validation']['average_confidence'],
                "all_valid": question_set['metadata']['quality_validation']['all_questions_valid']
            }
        )
        
        return question_set
    
    def _validate_single_question(self, question: Dict[str, Any], 
                                generation_request: Dict[str, Any], 
                                request_id: str) -> Dict[str, Any]:
        """
        Validate a single question for quality and alignment.
        
        Args:
            question: Question dictionary
            generation_request: Original generation request
            request_id: Request ID for logging
            
        Returns:
            Validation result with confidence score and errors
        """
        errors = []
        confidence = 1.0
        
        # Check for required mathematical elements based on topic
        required_elements = self._get_required_elements(generation_request.get('topic', ''))
        question_text = question.get('question_text', '').lower()
        
        missing_elements = [elem for elem in required_elements if elem not in question_text]
        if missing_elements:
            errors.append(f"Missing required mathematical elements: {', '.join(missing_elements)}")
            confidence -= 0.3
        
        # Check tier-appropriate difficulty
        tier = generation_request.get('tier', 'Foundation')
        difficulty_score = self._assess_difficulty(question.get('question_text', ''))
        
        if tier == "Foundation" and difficulty_score > 0.7:
            errors.append("Question may be too difficult for Foundation tier")
            confidence -= 0.3
        elif tier == "Higher" and difficulty_score < 0.3:
            errors.append("Question may be too easy for Higher tier")
            confidence -= 0.2
        
        # Check for LaTeX mathematical notation
        if not re.search(r'\\[a-zA-Z]+\{.*?\}|\\[a-zA-Z]+|\$.*?\$', question.get('question_text', '')):
            # Only warn if the question likely contains mathematical content
            if any(indicator in question_text for indicator in ['calculate', 'solve', 'find', 'work out']):
                errors.append("Question may be missing LaTeX mathematical notation")
                confidence -= 0.1
        
        # Check question length (should be substantial but not too long)
        text_length = len(question.get('question_text', ''))
        if text_length < 20:
            errors.append("Question text may be too short")
            confidence -= 0.2
        elif text_length > 500:
            errors.append("Question text may be too long")
            confidence -= 0.1
        
        return {
            'is_valid': len(errors) == 0,
            'confidence': max(0.0, confidence),
            'errors': errors
        }
    
    def _get_required_elements(self, topic: str) -> List[str]:
        """Get required mathematical elements for a topic."""
        topic_elements = {
            "Number": ["fraction", "decimal", "percentage", "calculate"],
            "Algebra": ["equation", "expression", "solve", "x", "y"],
            "Geometry": ["angle", "area", "perimeter", "triangle", "circle"],
            "Statistics": ["data", "mean", "median", "graph", "chart"],
            "Probability": ["probability", "chance", "outcome", "event"],
            "Ratio": ["ratio", "proportion", "scale"]
        }
        return topic_elements.get(topic, ["calculate", "find"])
    
    def _assess_difficulty(self, question_text: str) -> float:
        """
        Assess question difficulty based on complexity indicators.
        
        Args:
            question_text: Question text to analyze
            
        Returns:
            Difficulty score (0.0-1.0, higher = more difficult)
        """
        difficulty_score = 0.0
        text_lower = question_text.lower()
        
        # Complex mathematical operations increase difficulty
        complex_operations = ['square root', 'quadratic', 'simultaneous', 'trigonometry', 'logarithm']
        difficulty_score += 0.2 * sum(1 for op in complex_operations if op in text_lower)
        
        # Multiple steps increase difficulty
        step_indicators = ['then', 'next', 'finally', 'also', 'calculate', 'find']
        step_count = sum(1 for indicator in step_indicators if indicator in text_lower)
        difficulty_score += min(0.3, step_count * 0.1)
        
        # Advanced vocabulary increases difficulty
        advanced_terms = ['coefficient', 'gradient', 'intercept', 'discriminant', 'factorize']
        difficulty_score += 0.1 * sum(1 for term in advanced_terms if term in text_lower)
        
        # LaTeX complexity increases difficulty
        latex_complexity = len(re.findall(r'\\[a-zA-Z]+\{.*?\}', question_text))
        difficulty_score += min(0.2, latex_complexity * 0.05)
        
        return min(1.0, difficulty_score)