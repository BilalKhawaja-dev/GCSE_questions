"""
Bedrock service for AI model interactions.

This service handles communication with AWS Bedrock models including
Claude Haiku for query interpretation and Claude Sonnet for question generation.
Enhanced with comprehensive error handling, retry logic, and circuit breaker patterns.
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
from src.utils.math_rendering import convert_latex_to_plain_text, validate_no_latex_syntax
from src.utils.error_handling import (
    ErrorHandler, ErrorContext, ErrorType, CircuitBreaker,
    exponential_backoff_retry, with_error_handling, 
    RetryableError, NonRetryableError, validate_question_quality,
    create_timeout_handler
)
from src.services.question_validation_service import QuestionValidationService

logger = logging.getLogger(__name__)


class BedrockService:
    """Service for interacting with AWS Bedrock models with enhanced error handling."""
    
    def __init__(self, region: str = 'eu-west-2'):
        """Initialize Bedrock service with proper client configuration and error handling."""
        self.region = region
        self.client = boto3.client('bedrock-runtime', region_name=region)
        
        # Get model ID from environment variable (different for each Lambda)
        import os
        self.model_id = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-haiku-20240307-v1:0')
        
        # Initialize error handling components
        self.error_handler = ErrorHandler()
        self.circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
        self.validation_service = QuestionValidationService()
    
    def call_bedrock_with_retry(self, prompt: str, request_id: str, max_tokens: int = 4000, temperature: float = 0.1) -> str:
        """
        Public method to call Bedrock API with retry logic.
        
        Args:
            prompt: Input prompt for the model
            request_id: Request ID for logging
            max_tokens: Maximum tokens to generate
            temperature: Model temperature setting
            
        Returns:
            Model response text
        """
        return self._call_bedrock_with_retry(
            model_id=self.model_id,
            prompt=prompt,
            request_id=request_id,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
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
        
        try:
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
            
        except Exception as e:
            logger.error(
                "Query parsing failed",
                extra={
                    "request_id": request_id,
                    "error": str(e),
                    "error_type": type(e).__name__
                },
                exc_info=True
            )
            raise
    
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
4. count: Number of questions requested (1-100)
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

    @exponential_backoff_retry(max_retries=3, base_delay=1.0, max_delay=8.0)
    def _call_bedrock_with_retry(
        self,
        model_id: str,
        prompt: str,
        request_id: str,
        max_tokens: int = 4000,
        temperature: float = 0.1
    ) -> str:
        """
        Call Bedrock API with enhanced retry logic and circuit breaker protection.
        
        Args:
            model_id: Bedrock model identifier
            prompt: Input prompt for the model
            request_id: Request ID for logging
            max_tokens: Maximum tokens to generate
            temperature: Model temperature setting
            
        Returns:
            Model response text
            
        Raises:
            RetryableError: For errors that should be retried
            NonRetryableError: For errors that should not be retried
        """
        def bedrock_call():
            logger.info(
                "Calling Bedrock API with circuit breaker protection",
                extra={
                    "request_id": request_id,
                    "model_id": model_id,
                    "circuit_breaker_state": self.circuit_breaker.state.state
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
            
            try:
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
                        "response_length": len(response_text)
                    }
                )
                
                return response_text
                
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                error_message = e.response.get('Error', {}).get('Message', str(e))
                
                # Create error context for proper handling
                context = ErrorContext(
                    error_type=ErrorType.BEDROCK_API_ERROR,
                    operation="bedrock_api_call",
                    request_id=request_id,
                    attempt=1,
                    max_attempts=3,
                    error_message=error_message,
                    error_code=error_code
                )
                
                # Handle error through error handler
                context = self.error_handler.handle_bedrock_error(e, context)
                
                # Determine if error is retryable
                if error_code in ['ThrottlingException', 'TooManyRequestsException', 
                                'ServiceUnavailableException', 'InternalServerException']:
                    raise RetryableError(f"Retryable Bedrock error: {error_message}")
                else:
                    raise NonRetryableError(f"Non-retryable Bedrock error: {error_message}")
                
            except BotoCoreError as e:
                logger.warning(
                    "Boto3 error in Bedrock call",
                    extra={
                        "request_id": request_id,
                        "error": str(e),
                        "error_type": type(e).__name__
                    }
                )
                raise RetryableError(f"Boto3 error: {str(e)}")
                
            except Exception as e:
                logger.error(
                    "Unexpected error calling Bedrock",
                    extra={
                        "request_id": request_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "model_id": model_id
                    }
                )
                raise RetryableError(f"Unexpected error: {str(e)}")
        
        # Execute with circuit breaker protection
        try:
            return self.circuit_breaker.call(bedrock_call)
        except Exception as e:
            # Convert circuit breaker errors to appropriate types
            if "Circuit breaker is OPEN" in str(e):
                context = ErrorContext(
                    error_type=ErrorType.CIRCUIT_BREAKER_OPEN,
                    operation="bedrock_api_call",
                    request_id=request_id,
                    attempt=1,
                    max_attempts=1,
                    error_message=str(e)
                )
                context.additional_context['user_message'] = (
                    "The AI service is temporarily unavailable due to recent errors. "
                    "Please try again in a few minutes."
                )
                context.additional_context['retry_recommended'] = True
                context.additional_context['retry_delay'] = 60
                
                self.error_handler._log_error(context)
                raise NonRetryableError("Circuit breaker is open - service temporarily unavailable")
            
            raise e
    
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
            # Extract JSON from response - use JSONDecoder to handle extra data
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                raise ValueError("No JSON found in response")
            
            json_str = json_match.group(0)
            
            # Use JSONDecoder.raw_decode to handle extra data after JSON
            try:
                parsed_data = json.loads(json_str)
            except json.JSONDecodeError as e:
                if "Extra data" in str(e):
                    # Extract just the first complete JSON object
                    decoder = json.JSONDecoder()
                    parsed_data, idx = decoder.raw_decode(json_str)
                    logger.warning(f"Extracted first JSON object, ignoring extra data after position {idx}")
                else:
                    raise
            
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
    
    @with_error_handling("question_generation")
    @create_timeout_handler(timeout_seconds=50)
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
        
        # Validate question quality using comprehensive validation service
        validated_question_set = self.validation_service.validate_question_set(
            question_set, generation_request
        )
        
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
        """Construct structured prompt for question generation with enhanced content usage."""
        
        # Format examples for the prompt with detailed analysis
        examples_text = ""
        if examples_content:
            examples_text = "\n\nHigh-Quality Seed Examples (USE THESE AS MODELS):\n"
            for i, example in enumerate(examples_content[:5], 1):  # Use up to 5 examples
                question = example.get('question', {})
                mark_scheme = example.get('mark_scheme', {})
                quality_score = example.get('quality_score', 0)
                
                examples_text += f"""
Example {i} (Quality Score: {quality_score:.2f}):
Question: {question.get('question_text', 'N/A')}
Marks: {question.get('marks', 'N/A')}
Difficulty: {question.get('difficulty_score', 'N/A')}/10
Mark Scheme: {mark_scheme.get('marking_criteria', 'N/A')}
Answer: {question.get('answer', mark_scheme.get('answer', 'N/A'))}

ANALYSIS: This example demonstrates {self._analyze_example_quality(question, mark_scheme)}
"""
        
        # Enhanced specification content formatting
        spec_text = f"""
SPECIFICATION REQUIREMENTS (MUST FOLLOW):
Topic: {spec_content.get('subtopic', generation_request.get('topic'))}
Tier: {generation_request.get('tier')}
Learning Objectives: {', '.join(spec_content.get('learning_objectives', []))}
Key Concepts to Test: {', '.join(spec_content.get('key_concepts', []))}
Common Misconceptions to Address: {', '.join(spec_content.get('common_misconceptions', []))}
Assessment Objectives: {', '.join(spec_content.get('assessment_objectives', ['AO1', 'AO2']))}
Marks Range: {spec_content.get('marks_range', [2, 6])}

Detailed Content: {spec_content.get('specification_content', 'No specific content available')}
"""
        
        # Add content-driven instructions
        content_instructions = self._generate_content_instructions(spec_content, examples_content)
        
        return f"""You are an expert GCSE mathematics question writer creating questions based on official Edexcel specifications and high-quality examples.

{spec_text}{examples_text}

CONTENT-DRIVEN INSTRUCTIONS:
{content_instructions}

CRITICAL REQUIREMENTS:
1. Generate exactly {generation_request.get('count')} questions that DIRECTLY test the specification content above
2. Each question MUST align with the learning objectives and key concepts listed
3. Address the common misconceptions identified in the specification
4. Follow the style and quality patterns shown in the seed examples
5. Use the specification content as the PRIMARY source for question contexts and scenarios
6. Ensure mathematical accuracy and appropriate difficulty for {generation_request.get('tier')} tier
7. Include detailed mark schemes that match the assessment objectives
8. CRITICAL: Assign difficulty scores (1-10 scale):
   - Foundation tier: Use scores 1-5 (1=very easy, 5=challenging foundation)
   - Higher tier: Use scores 6-10 (6=easy higher, 10=very challenging)

QUESTION GENERATION STRATEGY:
- Use real-world contexts from the specification content
- Test multiple key concepts per question where appropriate
- Create questions that reveal common misconceptions
- Vary question types (calculation, problem-solving, reasoning)
- Ensure each question has clear mathematical progression

Return your response as a JSON object with this exact structure:
{{
    "questions": [
        {{
            "id": "q1",
            "question_text": "Question text based on specification content",
            "marks": 3,
            "tier": "{generation_request.get('tier')}",
            "topic": "{generation_request.get('topic')}",
            "subtopic": "{generation_request.get('subtopic', '')}",
            "difficulty_score": 4,
            "specification_alignment": "Brief note on how this tests the specification",
            "key_concepts_tested": ["concept1", "concept2"]
        }}
    ],
    "mark_scheme": [
        {{
            "question_id": "q1",
            "marking_criteria": "M1: Method mark description based on specification, A1: Accuracy mark description",
            "method_marks": 2,
            "accuracy_marks": 1,
            "common_errors": ["error1", "error2"]
        }}
    ],
    "metadata": {{
        "generated_at": "{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}",
        "model_version": "claude-3-sonnet-20240229",
        "total_marks": 0,
        "specification_version": "{generation_request.get('specification_version', 'latest')}",
        "content_utilization": {{
            "specification_concepts_used": [],
            "examples_referenced": {len(examples_content)},
            "misconceptions_addressed": []
        }}
    }}
}}

Ensure the JSON is valid and complete. The total_marks in metadata should equal the sum of all question marks."""
    
    def _analyze_example_quality(self, question: Dict[str, Any], mark_scheme: Dict[str, Any]) -> str:
        """Analyze what makes an example high quality."""
        analysis_points = []
        
        question_text = question.get('question_text', '')
        marks = question.get('marks', 0)
        
        # Analyze question structure
        if len(question_text) > 50:
            analysis_points.append("appropriate question length")
        
        if marks >= 3:
            analysis_points.append("multi-step problem requiring method marks")
        
        # Analyze mathematical content
        if any(char in question_text for char in '+-×÷=<>()[]{}'):
            analysis_points.append("clear mathematical notation")
        
        # Analyze mark scheme
        marking_criteria = mark_scheme.get('marking_criteria', '')
        if 'M1' in marking_criteria or 'method' in marking_criteria.lower():
            analysis_points.append("structured marking with method and accuracy marks")
        
        if len(analysis_points) == 0:
            return "basic question structure"
        
        return ", ".join(analysis_points)
    
    def _generate_content_instructions(self, spec_content: Dict[str, Any], examples_content: List[Dict[str, Any]]) -> str:
        """Generate specific instructions based on available content."""
        instructions = []
        
        # Instructions based on specification content
        learning_objectives = spec_content.get('learning_objectives', [])
        if learning_objectives:
            instructions.append(f"- Test these specific learning objectives: {'; '.join(learning_objectives[:3])}")
        
        key_concepts = spec_content.get('key_concepts', [])
        if key_concepts:
            instructions.append(f"- Incorporate these key concepts: {', '.join(key_concepts[:5])}")
        
        misconceptions = spec_content.get('common_misconceptions', [])
        if misconceptions:
            instructions.append(f"- Design questions to reveal these misconceptions: {'; '.join(misconceptions[:2])}")
        
        # Instructions based on examples
        if examples_content:
            example_topics = set()
            example_difficulties = []
            
            for example in examples_content[:3]:
                question = example.get('question', {})
                if 'subtopic' in question:
                    example_topics.add(question['subtopic'])
                if 'difficulty_score' in question:
                    example_difficulties.append(question['difficulty_score'])
            
            if example_topics:
                instructions.append(f"- Follow the style patterns from examples covering: {', '.join(example_topics)}")
            
            if example_difficulties:
                avg_difficulty = sum(example_difficulties) / len(example_difficulties)
                instructions.append(f"- Target similar difficulty level as examples (average: {avg_difficulty:.1f}/10)")
        
        # Default instruction if no specific content
        if not instructions:
            instructions.append("- Create questions that test fundamental understanding of the topic")
            instructions.append("- Ensure questions are appropriate for the specified tier level")
        
        return "\n".join(instructions)
    
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
                
                # Apply LaTeX to plain text conversion to question text
                original_question_text = question['question_text']
                question['question_text'] = convert_latex_to_plain_text(original_question_text)
                
                # Validate that LaTeX conversion was successful
                if not validate_no_latex_syntax(question['question_text']):
                    logger.warning(
                        f"Question {i+1} still contains LaTeX syntax after conversion",
                        extra={
                            "request_id": request_id,
                            "original_text": original_question_text[:100] + "..." if len(original_question_text) > 100 else original_question_text,
                            "converted_text": question['question_text'][:100] + "..." if len(question['question_text']) > 100 else question['question_text']
                        }
                    )
                    # Reject questions that still contain LaTeX syntax
                    raise ValueError(f"Question {i+1} contains unconverted LaTeX syntax: {question['question_text']}")
                
                # Validate marks is positive integer
                if not isinstance(question['marks'], int) or question['marks'] < 1:
                    raise ValueError(f"Question {i+1} has invalid marks: {question['marks']}")
                
                # Validate difficulty score
                if 'difficulty_score' not in question:
                    # Auto-assign difficulty score if missing
                    tier = question.get('tier', generation_request.get('tier', 'Foundation'))
                    question['difficulty_score'] = self._assign_difficulty_score(question, tier)
                    logger.info(
                        f"Auto-assigned difficulty_score {question['difficulty_score']} to question {i+1}",
                        extra={"request_id": request_id}
                    )
                else:
                    difficulty_score = question['difficulty_score']
                    if not isinstance(difficulty_score, int) or not (1 <= difficulty_score <= 10):
                        # Auto-assign if invalid
                        tier = question.get('tier', generation_request.get('tier', 'Foundation'))
                        question['difficulty_score'] = self._assign_difficulty_score(question, tier)
                        logger.warning(
                            f"Invalid difficulty_score {difficulty_score} for question {i+1}, auto-assigned {question['difficulty_score']}",
                            extra={"request_id": request_id}
                        )
                    else:
                        # Validate difficulty score matches tier
                        tier = question.get('tier', generation_request.get('tier', ''))
                        if tier == "Foundation" and difficulty_score > 5:
                            logger.warning(
                                f"Question {i+1} difficulty_score {difficulty_score} too high for Foundation tier, adjusting to 5",
                                extra={"request_id": request_id}
                            )
                            question['difficulty_score'] = 5
                        elif tier == "Higher" and difficulty_score < 6:
                            logger.warning(
                                f"Question {i+1} difficulty_score {difficulty_score} too low for Higher tier, adjusting to 6",
                                extra={"request_id": request_id}
                            )
                            question['difficulty_score'] = 6
            
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
                
                # Apply LaTeX to plain text conversion to marking criteria
                original_marking_criteria = mark_scheme['marking_criteria']
                mark_scheme['marking_criteria'] = convert_latex_to_plain_text(original_marking_criteria)
                
                # Validate that LaTeX conversion was successful for mark scheme
                if not validate_no_latex_syntax(mark_scheme['marking_criteria']):
                    logger.warning(
                        f"Mark scheme {i+1} still contains LaTeX syntax after conversion",
                        extra={
                            "request_id": request_id,
                            "original_criteria": original_marking_criteria[:100] + "..." if len(original_marking_criteria) > 100 else original_marking_criteria,
                            "converted_criteria": mark_scheme['marking_criteria'][:100] + "..." if len(mark_scheme['marking_criteria']) > 100 else mark_scheme['marking_criteria']
                        }
                    )
                    # Reject mark schemes that still contain LaTeX syntax
                    raise ValueError(f"Mark scheme {i+1} contains unconverted LaTeX syntax: {mark_scheme['marking_criteria']}")
                
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
    
    def _validate_question_quality_enhanced(self, question_set: Dict[str, Any], 
                                           generation_request: Dict[str, Any], 
                                           request_id: str) -> Dict[str, Any]:
        """
        Enhanced question quality validation with comprehensive error handling.
        
        Args:
            question_set: Generated question set
            generation_request: Original generation request
            request_id: Request ID for logging
            
        Returns:
            Validated question set with quality metrics
            
        Raises:
            NonRetryableError: If questions fail validation and cannot be fixed
        """
        logger.info(
            "Validating question quality with enhanced validation",
            extra={"request_id": request_id, "question_count": len(question_set['questions'])}
        )
        
        validation_results = []
        valid_questions = []
        valid_mark_schemes = []
        
        for i, question in enumerate(question_set['questions']):
            try:
                # Use the enhanced validation function
                validation_result = validate_question_quality(question)
                validation_results.append(validation_result)
                
                if validation_result['is_valid']:
                    valid_questions.append(question)
                    # Find corresponding mark scheme
                    mark_scheme = next(
                        (ms for ms in question_set['mark_scheme'] if ms['question_id'] == question['id']),
                        None
                    )
                    if mark_scheme:
                        valid_mark_schemes.append(mark_scheme)
                else:
                    logger.warning(
                        f"Question {i+1} failed validation",
                        extra={
                            "request_id": request_id,
                            "question_id": question.get('id', f'q{i+1}'),
                            "errors": validation_result['errors'],
                            "confidence": validation_result['confidence']
                        }
                    )
                    
            except NonRetryableError as e:
                logger.error(
                    f"Question {i+1} has critical validation errors",
                    extra={
                        "request_id": request_id,
                        "question_id": question.get('id', f'q{i+1}'),
                        "error": str(e)
                    }
                )
                # Skip this question entirely
                continue
        
        # Check if we have enough valid questions
        requested_count = generation_request.get('count', 5)
        valid_count = len(valid_questions)
        
        if valid_count == 0:
            raise NonRetryableError("No valid questions generated - all questions failed quality validation")
        
        if valid_count < requested_count * 0.5:  # Less than 50% success rate
            logger.warning(
                f"Low question validation success rate: {valid_count}/{requested_count}",
                extra={"request_id": request_id}
            )
        
        # Update question set with only valid questions
        question_set['questions'] = valid_questions
        question_set['mark_scheme'] = valid_mark_schemes
        
        # Recalculate metadata
        total_marks = sum(q['marks'] for q in valid_questions)
        question_set['metadata']['total_marks'] = total_marks
        question_set['metadata']['generated_count'] = valid_count
        question_set['metadata']['requested_count'] = requested_count
        
        # Add enhanced quality metrics
        if validation_results:
            question_set['metadata']['quality_validation'] = {
                'average_confidence': sum(r['confidence'] for r in validation_results) / len(validation_results),
                'validation_errors': [r['errors'] for r in validation_results if r['errors']],
                'all_questions_valid': all(r['is_valid'] for r in validation_results),
                'success_rate': valid_count / len(validation_results),
                'total_validated': len(validation_results)
            }
        
        logger.info(
            "Enhanced question quality validation completed",
            extra={
                "request_id": request_id,
                "valid_questions": valid_count,
                "requested_questions": requested_count,
                "success_rate": valid_count / requested_count if requested_count > 0 else 0,
                "average_confidence": question_set['metadata']['quality_validation'].get('average_confidence', 0)
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
        
        # Check that LaTeX has been properly converted to plain text
        question_text_content = question.get('question_text', '')
        if not validate_no_latex_syntax(question_text_content):
            errors.append("Question contains unconverted LaTeX syntax")
            confidence -= 0.5  # This is a critical error
        
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
    
    def _assign_difficulty_score(self, question: Dict[str, Any], tier: str) -> int:
        """
        Assign difficulty score to a question based on content analysis.
        
        Args:
            question: Question dictionary
            tier: Tier level (Foundation or Higher)
            
        Returns:
            Difficulty score (1-10)
        """
        question_text = question.get('question_text', '').lower()
        marks = question.get('marks', 1)
        
        # Base score based on tier
        if tier == "Foundation":
            base_score = 3  # Middle of 1-5 range
            min_score, max_score = 1, 5
        else:
            base_score = 8  # Middle of 6-10 range  
            min_score, max_score = 6, 10
        
        difficulty_adjustments = 0
        
        # Adjust based on marks (more marks = higher difficulty)
        if marks >= 6:
            difficulty_adjustments += 2
        elif marks >= 4:
            difficulty_adjustments += 1
        elif marks <= 1:
            difficulty_adjustments -= 1
        
        # Adjust based on mathematical complexity
        complex_operations = ['quadratic', 'simultaneous', 'trigonometry', 'logarithm', 'differentiate', 'integrate']
        difficulty_adjustments += sum(0.5 for op in complex_operations if op in question_text)
        
        # Adjust based on multi-step indicators
        step_indicators = ['then', 'next', 'finally', 'also', 'calculate', 'find', 'hence']
        step_count = sum(1 for indicator in step_indicators if indicator in question_text)
        if step_count >= 3:
            difficulty_adjustments += 1
        elif step_count >= 2:
            difficulty_adjustments += 0.5
        
        # Adjust based on advanced vocabulary
        advanced_terms = ['coefficient', 'gradient', 'intercept', 'discriminant', 'factorize', 'rationalize']
        difficulty_adjustments += sum(0.3 for term in advanced_terms if term in question_text)
        
        # Calculate final score
        final_score = base_score + int(difficulty_adjustments)
        
        # Ensure score is within valid range for tier
        return max(min_score, min(max_score, final_score))