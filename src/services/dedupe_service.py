"""
Deduplication Service for Question Verification System

Prevents repetitive questions using embedding-based similarity detection.
Uses Amazon Bedrock Titan Embed v2 for generating embeddings and cosine similarity
for detecting near-duplicate questions.
"""

import json
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from boto3.dynamodb.conditions import Key

from src.models.verification import VerificationResult

logger = logging.getLogger(__name__)


@dataclass
class DedupeResult:
    """Result of deduplication check"""
    pass_: bool
    max_similarity: float
    similar_question_id: Optional[str] = None
    similar_question_stem: Optional[str] = None
    embedding: Optional[List[float]] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        return {
            "pass": self.pass_,
            "max_similarity": self.max_similarity,
            "similar_question_id": self.similar_question_id,
            "similar_question_stem": self.similar_question_stem
        }


class DedupeService:
    """
    Deduplication service using embedding-based similarity detection.
    
    Uses Amazon Bedrock Titan Embed v2 to generate 1024-dimensional embeddings
    from question text and calculates cosine similarity to detect near-duplicates.
    """
    
    def __init__(
        self,
        bedrock_client,
        dynamodb_client,
        table_name: str = "verified_question_bank",
        embedding_model: str = "amazon.titan-embed-text-v2:0",
        similarity_threshold: float = 0.85
    ):
        """
        Initialize dedupe service.
        
        Args:
            bedrock_client: Boto3 Bedrock Runtime client
            dynamodb_client: Boto3 DynamoDB resource
            table_name: Name of DynamoDB table with questions
            embedding_model: Bedrock embedding model ID
            similarity_threshold: Threshold above which questions are considered duplicates
        """
        self.bedrock = bedrock_client
        self.dynamodb = dynamodb_client
        self.table_name = table_name
        self.embedding_model = embedding_model
        self.similarity_threshold = similarity_threshold
        
        logger.info(
            f"Initialized DedupeService with model={embedding_model}, "
            f"threshold={similarity_threshold}"
        )
    
    def check_duplicate(
        self,
        question,  # Can be Question, MCQQuestion, or dict
        existing_embedding: Optional[List[float]] = None
    ) -> DedupeResult:
        """
        Check if question is a duplicate of existing questions.
        
        Args:
            question: Question to check (Question, MCQQuestion, or dict with 'stem' and 'options')
            existing_embedding: Pre-computed embedding (optional, for efficiency)
        
        Returns:
            DedupeResult with pass/fail and similarity details
        """
        try:
            # Generate embedding for new question
            if existing_embedding:
                new_embedding = existing_embedding
                logger.debug("Using pre-computed embedding")
            else:
                new_embedding = self.generate_embedding(question)
                logger.debug(f"Generated new embedding: {len(new_embedding)} dimensions")
            
            # Get topic and grade from question
            topic = getattr(question, 'topic', question.get('topic', 'unknown') if isinstance(question, dict) else 'unknown')
            grade = getattr(question, 'grade', question.get('grade', 'foundation') if isinstance(question, dict) else 'foundation')
            
            # Query existing questions in same topic/grade
            existing_questions = self._get_topic_questions(topic, grade)
            
            logger.info(
                f"Checking against {len(existing_questions)} existing questions "
                f"for topic={topic}, grade={grade}"
            )
            
            # Calculate similarities
            max_similarity = 0.0
            most_similar_id = None
            most_similar_stem = None
            
            for existing in existing_questions:
                # Skip if no embedding stored
                if not existing.get('embedding'):
                    continue
                
                similarity = self._cosine_similarity(
                    new_embedding,
                    existing['embedding']
                )
                
                if similarity > max_similarity:
                    max_similarity = similarity
                    most_similar_id = existing.get('question_id')
                    most_similar_stem = existing.get('stem', '')[:100]  # First 100 chars
            
            is_duplicate = max_similarity > self.similarity_threshold
            
            if is_duplicate:
                logger.warning(
                    f"Duplicate detected! Similarity={max_similarity:.3f} "
                    f"with question {most_similar_id}"
                )
            else:
                logger.info(f"No duplicate found. Max similarity={max_similarity:.3f}")
            
            return DedupeResult(
                pass_=not is_duplicate,
                max_similarity=max_similarity,
                similar_question_id=most_similar_id if is_duplicate else None,
                similar_question_stem=most_similar_stem if is_duplicate else None,
                embedding=new_embedding
            )
            
        except Exception as e:
            logger.error(f"Dedupe check failed: {str(e)}", exc_info=True)
            # Don't fail verification on dedupe errors - return pass with low confidence
            return DedupeResult(
                pass_=True,
                max_similarity=0.0,
                embedding=None
            )
    
    def generate_embedding(self, question) -> List[float]:
        """
        Generate embedding from question text.
        
        Combines stem + options into single text for embedding generation.
        
        Args:
            question: Question to generate embedding for (Question, MCQQuestion, or dict)
        
        Returns:
            1024-dimensional embedding vector
        """
        # Extract stem and options from question (handle different types)
        if isinstance(question, dict):
            stem = question.get('stem', '')
            options = question.get('options', [])
        else:
            stem = getattr(question, 'stem', getattr(question, 'question_text', ''))
            options = getattr(question, 'options', [])
        
        # Combine stem and options into single text
        text_parts = [stem]
        
        if options:
            text_parts.extend(options)
        
        text = " ".join(text_parts)
        
        # Truncate if too long (Titan Embed has token limits)
        max_chars = 8000
        if len(text) > max_chars:
            text = text[:max_chars]
            logger.warning(f"Truncated text to {max_chars} chars for embedding")
        
        try:
            # Call Bedrock Titan Embed
            response = self.bedrock.invoke_model(
                modelId=self.embedding_model,
                body=json.dumps({
                    "inputText": text
                })
            )
            
            response_body = json.loads(response['body'].read())
            embedding = response_body.get('embedding')
            
            if not embedding:
                raise ValueError("No embedding in response")
            
            logger.debug(f"Generated embedding: {len(embedding)} dimensions")
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {str(e)}", exc_info=True)
            raise
    
    def _get_topic_questions(
        self,
        topic: str,
        grade: str,
        limit: int = 1000
    ) -> List[Dict]:
        """
        Retrieve existing questions for topic/grade from DynamoDB.
        
        Args:
            topic: Question topic
            grade: Question grade (foundation/higher)
            limit: Maximum questions to retrieve
        
        Returns:
            List of question dictionaries with embeddings
        """
        try:
            table = self.dynamodb.Table(self.table_name)
            
            # Query using GSI if available, otherwise scan with filter
            # For now, use scan with filter (can optimize with GSI later)
            response = table.scan(
                FilterExpression='topic = :topic AND grade = :grade',
                ExpressionAttributeValues={
                    ':topic': topic,
                    ':grade': grade
                },
                Limit=limit,
                ProjectionExpression='question_id,stem,embedding'
            )
            
            items = response.get('Items', [])
            
            # Handle pagination if needed
            while 'LastEvaluatedKey' in response and len(items) < limit:
                response = table.scan(
                    FilterExpression='topic = :topic AND grade = :grade',
                    ExpressionAttributeValues={
                        ':topic': topic,
                        ':grade': grade
                    },
                    Limit=limit - len(items),
                    ProjectionExpression='question_id,stem,embedding',
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                items.extend(response.get('Items', []))
            
            logger.debug(f"Retrieved {len(items)} questions from DynamoDB")
            return items
            
        except Exception as e:
            logger.error(f"Failed to retrieve questions: {str(e)}", exc_info=True)
            return []
    
    def _cosine_similarity(
        self,
        embedding_a: List[float],
        embedding_b: List[float]
    ) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding_a: First embedding vector
            embedding_b: Second embedding vector
        
        Returns:
            Cosine similarity score (0.0 to 1.0)
        """
        try:
            a = np.array(embedding_a)
            b = np.array(embedding_b)
            
            # Calculate cosine similarity
            dot_product = np.dot(a, b)
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            
            if norm_a == 0 or norm_b == 0:
                return 0.0
            
            similarity = dot_product / (norm_a * norm_b)
            
            # Clamp to [0, 1] range (should already be, but just in case)
            similarity = max(0.0, min(1.0, float(similarity)))
            
            return similarity
            
        except Exception as e:
            logger.error(f"Failed to calculate similarity: {str(e)}", exc_info=True)
            return 0.0
    
    def batch_generate_embeddings(
        self,
        questions: List,  # Can be Question, MCQQuestion, or dict objects
        batch_size: int = 10
    ) -> Dict[str, List[float]]:
        """
        Generate embeddings for multiple questions in batches.
        
        Args:
            questions: List of questions to generate embeddings for
            batch_size: Number of questions to process at once
        
        Returns:
            Dictionary mapping question_id to embedding
        """
        embeddings = {}
        
        for i in range(0, len(questions), batch_size):
            batch = questions[i:i + batch_size]
            
            for question in batch:
                try:
                    # Get question ID
                    if isinstance(question, dict):
                        question_id = question.get('question_id', question.get('id', f'q{i}'))
                    else:
                        question_id = getattr(question, 'question_id', getattr(question, 'id', f'q{i}'))
                    
                    embedding = self.generate_embedding(question)
                    embeddings[question_id] = embedding
                    logger.debug(f"Generated embedding for {question_id}")
                except Exception as e:
                    logger.error(
                        f"Failed to generate embedding for question: {str(e)}"
                    )
                    continue
            
            logger.info(f"Processed batch {i//batch_size + 1}: {len(batch)} questions")
        
        logger.info(f"Generated {len(embeddings)} embeddings total")
        return embeddings
    
    def store_embedding(
        self,
        question_id: str,
        embedding: List[float]
    ) -> bool:
        """
        Store embedding in DynamoDB for a question.
        
        Args:
            question_id: Question ID
            embedding: Embedding vector to store
        
        Returns:
            True if successful, False otherwise
        """
        try:
            table = self.dynamodb.Table(self.table_name)
            
            table.update_item(
                Key={'question_id': question_id},
                UpdateExpression='SET embedding = :emb',
                ExpressionAttributeValues={
                    ':emb': embedding
                }
            )
            
            logger.debug(f"Stored embedding for {question_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store embedding: {str(e)}", exc_info=True)
            return False
