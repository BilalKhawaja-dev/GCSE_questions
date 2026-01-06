"""
Content retrieval service for S3-based specification and examples storage.

This service handles deterministic topic-to-file mapping and retrieval of
specification content and seed examples from S3 buckets with comprehensive
fallback mechanisms and error handling.
"""

import json
import logging
import time
from typing import Dict, Any, List, Optional
import boto3
from botocore.exceptions import ClientError, BotoCoreError

from src.models.specification_content import SpecificationContent
from src.services.version_management_service import VersionManagementService
from src.utils.error_handling import (
    ErrorHandler, ErrorContext, ErrorType, CircuitBreaker,
    exponential_backoff_retry, with_error_handling, 
    RetryableError, NonRetryableError, CircuitBreakerOpenError
)

logger = logging.getLogger(__name__)


class ContentRetrievalService:
    """Service for retrieving specification content and examples from S3 with fallback mechanisms."""
    
    # Topic-to-file mapping dictionary
    TOPIC_MAPPING = {
        "number": {
            "fractions": {"domain": "number", "file": "fractions.json"},
            "decimals": {"domain": "number", "file": "decimals.json"},
            "percentages": {"domain": "number", "file": "percentages.json"},
            "integers": {"domain": "number", "file": "integers.json"},
            "indices": {"domain": "number", "file": "indices.json"},
            "surds": {"domain": "number", "file": "surds.json"}
        },
        "algebra": {
            "linear_equations": {"domain": "algebra", "file": "linear-equations.json"},
            "quadratic_equations": {"domain": "algebra", "file": "quadratic-equations.json"},
            "expressions": {"domain": "algebra", "file": "expressions.json"},
            "sequences": {"domain": "algebra", "file": "sequences.json"},
            "graphs": {"domain": "algebra", "file": "graphs.json"},
            "inequalities": {"domain": "algebra", "file": "inequalities.json"}
        },
        "geometry": {
            "angles": {"domain": "geometry", "file": "angles.json"},
            "triangles": {"domain": "geometry", "file": "triangles.json"},
            "circles": {"domain": "geometry", "file": "circles.json"},
            "area_perimeter": {"domain": "geometry", "file": "area-perimeter.json"},
            "volume": {"domain": "geometry", "file": "volume.json"},
            "transformations": {"domain": "geometry", "file": "transformations.json"}
        },
        "statistics": {
            "data_analysis": {"domain": "statistics", "file": "data-analysis.json"},
            "averages": {"domain": "statistics", "file": "averages.json"},
            "graphs_charts": {"domain": "statistics", "file": "graphs-charts.json"},
            "correlation": {"domain": "statistics", "file": "correlation.json"}
        },
        "probability": {
            "basic_probability": {"domain": "probability", "file": "basic-probability.json"},
            "tree_diagrams": {"domain": "probability", "file": "tree-diagrams.json"},
            "conditional": {"domain": "probability", "file": "conditional.json"}
        },
        "ratio": {
            "ratio_proportion": {"domain": "ratio", "file": "ratio-proportion.json"},
            "scale_factors": {"domain": "ratio", "file": "scale-factors.json"},
            "similar_shapes": {"domain": "ratio", "file": "similar-shapes.json"}
        }
    }
    
    # Fallback content for when S3 is unavailable
    FALLBACK_CONTENT = {
        "number": {
            "fractions": {
                "topic": "Number",
                "subtopic": "fractions",
                "tier": "both",
                "learning_objectives": [
                    "Add and subtract fractions with different denominators",
                    "Multiply and divide fractions",
                    "Convert between mixed numbers and improper fractions"
                ],
                "key_concepts": [
                    "Equivalent fractions",
                    "Lowest common multiple",
                    "Reciprocals"
                ],
                "specification_content": "Work with fractions including addition, subtraction, multiplication and division",
                "common_misconceptions": [
                    "Adding denominators when adding fractions",
                    "Confusion between mixed numbers and improper fractions"
                ],
                "assessment_objectives": ["AO1", "AO2", "AO3"],
                "version": "fallback",
                "fallback": True
            }
        },
        "algebra": {
            "linear_equations": {
                "topic": "Algebra",
                "subtopic": "linear_equations",
                "tier": "both",
                "learning_objectives": [
                    "Solve linear equations in one variable",
                    "Rearrange formulae",
                    "Solve simultaneous linear equations"
                ],
                "key_concepts": [
                    "Variables and constants",
                    "Balancing equations",
                    "Substitution"
                ],
                "specification_content": "Solve linear equations and rearrange formulae",
                "common_misconceptions": [
                    "Incorrect sign changes when moving terms",
                    "Confusion with order of operations"
                ],
                "assessment_objectives": ["AO1", "AO2", "AO3"],
                "version": "fallback",
                "fallback": True
            }
        },
        "geometry": {
            "area_perimeter": {
                "topic": "Geometry",
                "subtopic": "area_perimeter",
                "tier": "both",
                "learning_objectives": [
                    "Calculate area and perimeter of rectangles, triangles, and circles",
                    "Apply area and perimeter formulas to solve problems",
                    "Work with compound shapes"
                ],
                "key_concepts": [
                    "Area formulas",
                    "Perimeter formulas",
                    "Units and conversions"
                ],
                "specification_content": "Calculate area and perimeter of 2D shapes",
                "common_misconceptions": [
                    "Confusing area and perimeter",
                    "Incorrect use of π in circle calculations"
                ],
                "assessment_objectives": ["AO1", "AO2", "AO3"],
                "version": "fallback",
                "fallback": True
            }
        }
    }
    
    def __init__(self, specifications_bucket: str, examples_bucket: str, region: str = 'eu-west-2'):
        """Initialize content retrieval service with enhanced error handling.
        
        Args:
            specifications_bucket: S3 bucket name for specifications
            examples_bucket: S3 bucket name for examples
            region: AWS region
        """
        self.specifications_bucket = specifications_bucket
        self.examples_bucket = examples_bucket
        self.region = region
        self.s3_client = boto3.client('s3', region_name=region)
        self.error_handler = ErrorHandler()
        self.version_service = VersionManagementService(self.s3_client)
        
        # Enhanced caching with persistent fallback storage
        self._cache = {}
        self._cache_ttl = 3600  # 1 hour TTL
        self._persistent_cache = {}  # Long-term cache for fallback
        self._persistent_cache_ttl = 86400  # 24 hours TTL
        
    @with_error_handling("specification_content_retrieval")
    @exponential_backoff_retry(max_retries=3, base_delay=1.0, max_delay=8.0)
    def get_specification_content(self, topic: str, subtopic: Optional[str] = None, 
                                tier: str = "both", request_id: str = None) -> Dict[str, Any]:
        """Retrieve specification content from S3 with comprehensive fallback mechanisms.
        
        Args:
            topic: Main topic (e.g., "Number", "Algebra")
            subtopic: Specific subtopic (e.g., "fractions", "linear_equations")
            tier: Difficulty tier filter
            request_id: Request ID for logging
            
        Returns:
            Specification content dictionary
            
        Raises:
            ValueError: If topic/subtopic not found and no fallback available
        """
        logger.info(
            "Retrieving specification content with fallback support",
            extra={
                "request_id": request_id,
                "topic": topic,
                "subtopic": subtopic,
                "tier": tier
            }
        )
        
        # Normalize topic name
        topic_key = topic.lower()
        
        # Determine file mapping
        try:
            if subtopic:
                subtopic_key = subtopic.lower().replace(" ", "_")
                if topic_key not in self.TOPIC_MAPPING:
                    raise ValueError(f"Unknown topic: {topic}")
                if subtopic_key not in self.TOPIC_MAPPING[topic_key]:
                    raise ValueError(f"Unknown subtopic '{subtopic}' for topic '{topic}'")
                mapping = self.TOPIC_MAPPING[topic_key][subtopic_key]
            else:
                # Use first available subtopic for the topic
                if topic_key not in self.TOPIC_MAPPING:
                    raise ValueError(f"Unknown topic: {topic}")
                first_subtopic = list(self.TOPIC_MAPPING[topic_key].keys())[0]
                mapping = self.TOPIC_MAPPING[topic_key][first_subtopic]
                subtopic_key = first_subtopic
                logger.info(
                    f"No subtopic specified, using first available: {first_subtopic}",
                    extra={"request_id": request_id}
                )
        except ValueError as e:
            # Try fallback content if mapping fails
            return self._get_fallback_content(topic_key, subtopic, tier, request_id, str(e))
        
        # Check cache first
        cache_key = f"spec_{mapping['domain']}_{mapping['file']}_{tier}"
        cached_content = self._get_from_cache(cache_key)
        if cached_content:
            logger.info(
                "Retrieved specification content from cache",
                extra={"request_id": request_id, "cache_key": cache_key}
            )
            return cached_content
        
        # Try to retrieve from S3 with fallback mechanisms
        try:
            s3_key = f"specifications/{mapping['domain']}/{mapping['file']}"
            content = self._get_s3_object_with_fallback(
                self.specifications_bucket, s3_key, request_id
            )
            
            # Filter by tier if needed
            if tier != "both" and content.get('tier') == "both":
                # Content supports both tiers, return as-is
                pass
            elif tier != "both" and content.get('tier') != tier:
                logger.warning(
                    f"Content tier mismatch: requested {tier}, found {content.get('tier')}",
                    extra={"request_id": request_id}
                )
            
            # Cache the content (both short-term and persistent)
            self._add_to_cache(cache_key, content)
            self._add_to_persistent_cache(cache_key, content)
            
            logger.info(
                "Retrieved specification content from S3",
                extra={
                    "request_id": request_id,
                    "s3_key": s3_key,
                    "content_size": len(str(content))
                }
            )
            
            return content
            
        except Exception as e:
            # Try fallback mechanisms
            logger.warning(
                "S3 retrieval failed, attempting fallback mechanisms",
                extra={
                    "request_id": request_id,
                    "error": str(e),
                    "s3_key": s3_key
                }
            )
            
            return self._get_fallback_content(topic_key, subtopic_key, tier, request_id, str(e))
    
    def get_specification_content_versioned(self, topic: str, subtopic: Optional[str] = None, 
                                          tier: str = "both", version: str = "latest", 
                                          request_id: str = None) -> Dict[str, Any]:
        """Retrieve versioned specification content from S3 based on topic.
        
        Args:
            topic: Main topic (e.g., "Number", "Algebra")
            subtopic: Specific subtopic (e.g., "fractions", "linear_equations")
            tier: Difficulty tier filter
            version: Specification version to retrieve ("latest" for most recent)
            request_id: Request ID for logging
            
        Returns:
            Specification content dictionary with version information
            
        Raises:
            ValueError: If topic/subtopic not found
            CircuitBreakerOpenError: If S3 service unavailable
            Exception: If retrieval fails
        """
        logger.info(
            "Retrieving versioned specification content",
            extra={
                "request_id": request_id,
                "topic": topic,
                "subtopic": subtopic,
                "tier": tier,
                "version": version
            }
        )
        
        # Normalize topic name
        topic_key = topic.lower()
        
        # Determine file mapping
        if subtopic:
            subtopic_key = subtopic.lower().replace(" ", "_")
            if topic_key not in self.TOPIC_MAPPING:
                raise ValueError(f"Unknown topic: {topic}")
            if subtopic_key not in self.TOPIC_MAPPING[topic_key]:
                raise ValueError(f"Unknown subtopic '{subtopic}' for topic '{topic}'")
            mapping = self.TOPIC_MAPPING[topic_key][subtopic_key]
        else:
            # Use first available subtopic for the topic
            if topic_key not in self.TOPIC_MAPPING:
                raise ValueError(f"Unknown topic: {topic}")
            first_subtopic = list(self.TOPIC_MAPPING[topic_key].keys())[0]
            mapping = self.TOPIC_MAPPING[topic_key][first_subtopic]
            logger.info(
                f"No subtopic specified, using first available: {first_subtopic}",
                extra={"request_id": request_id}
            )
        
        # Check cache first (include version in cache key)
        cache_key = f"spec_{mapping['domain']}_{mapping['file']}_{tier}_{version}"
        cached_content = self._get_from_cache(cache_key)
        if cached_content:
            logger.info(
                "Retrieved versioned specification content from cache",
                extra={"request_id": request_id, "cache_key": cache_key}
            )
            return cached_content
        
        # Retrieve versioned content from S3 with circuit breaker protection
        try:
            base_path = f"specifications/{mapping['domain']}/{mapping['file']}"
            content = self.circuit_breaker.call(
                self.version_service.get_version_content,
                self.specifications_bucket,
                base_path,
                version
            )
            
            if not content:
                raise ValueError(f"Version {version} not found for {base_path}")
            
            # Filter by tier if needed
            if tier != "both" and content.get('tier') == "both":
                # Content supports both tiers, return as-is
                pass
            elif tier != "both" and content.get('tier') != tier:
                logger.warning(
                    f"Content tier mismatch: requested {tier}, found {content.get('tier')}",
                    extra={"request_id": request_id}
                )
            
            # Cache the content
            self._add_to_cache(cache_key, content)
            
            logger.info(
                "Retrieved versioned specification content from S3",
                extra={
                    "request_id": request_id,
                    "base_path": base_path,
                    "version": version,
                    "actual_version": content.get('version', 'unknown'),
                    "content_size": len(str(content))
                }
            )
            
            return content
            
        except CircuitBreakerOpenError:
            logger.error(
                "S3 service unavailable - circuit breaker open",
                extra={"request_id": request_id}
            )
            raise
        except Exception as e:
            logger.error(
                "Failed to retrieve versioned specification content",
                extra={
                    "request_id": request_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "version": version,
                    "base_path": base_path
                }
            )
            raise Exception(f"Failed to retrieve versioned specification content: {str(e)}")
    
    @with_error_handling("examples_content_retrieval")
    def get_examples_content(self, topic: str, subtopic: Optional[str] = None, 
                           tier: str = "both", request_id: str = None) -> List[Dict[str, Any]]:
        """Retrieve seed examples from S3 with graceful fallback to empty list.
        
        Args:
            topic: Main topic (e.g., "Number", "Algebra")
            subtopic: Specific subtopic (e.g., "fractions", "linear_equations")
            tier: Difficulty tier filter
            request_id: Request ID for logging
            
        Returns:
            List of example dictionaries (empty list if unavailable)
        """
        logger.info(
            "Retrieving examples content with fallback support",
            extra={
                "request_id": request_id,
                "topic": topic,
                "subtopic": subtopic,
                "tier": tier
            }
        )
        
        # Normalize topic name
        topic_key = topic.lower()
        
        # Determine file mapping (same logic as specifications)
        try:
            if subtopic:
                subtopic_key = subtopic.lower().replace(" ", "_")
                if topic_key not in self.TOPIC_MAPPING:
                    logger.warning(f"Unknown topic for examples: {topic}", extra={"request_id": request_id})
                    return []
                if subtopic_key not in self.TOPIC_MAPPING[topic_key]:
                    logger.warning(f"Unknown subtopic for examples: {subtopic}", extra={"request_id": request_id})
                    return []
                mapping = self.TOPIC_MAPPING[topic_key][subtopic_key]
            else:
                # Use first available subtopic for the topic
                if topic_key not in self.TOPIC_MAPPING:
                    logger.warning(f"Unknown topic for examples: {topic}", extra={"request_id": request_id})
                    return []
                first_subtopic = list(self.TOPIC_MAPPING[topic_key].keys())[0]
                mapping = self.TOPIC_MAPPING[topic_key][first_subtopic]
                subtopic_key = first_subtopic
        except Exception as e:
            logger.warning(
                f"Failed to determine mapping for examples: {str(e)}",
                extra={"request_id": request_id, "topic": topic, "subtopic": subtopic}
            )
            return []
        
        # Check cache first
        cache_key = f"examples_{mapping['domain']}_{mapping['file']}_{tier}"
        cached_examples = self._get_from_cache(cache_key)
        if cached_examples:
            logger.info(
                "Retrieved examples content from cache",
                extra={"request_id": request_id, "cache_key": cache_key}
            )
            return cached_examples
        
        # Try to retrieve from S3 with fallback to empty list
        try:
            s3_key = f"examples/{mapping['domain']}/{mapping['file']}"
            content = self._get_s3_object_with_fallback(
                self.examples_bucket, s3_key, request_id
            )
            
            # Extract examples array
            examples = content.get('examples', [])
            
            # Filter by tier if specified
            if tier != "both":
                examples = [ex for ex in examples if ex.get('question', {}).get('tier') == tier]
            
            # Cache the examples
            self._add_to_cache(cache_key, examples)
            
            logger.info(
                "Retrieved examples content from S3",
                extra={
                    "request_id": request_id,
                    "s3_key": s3_key,
                    "example_count": len(examples)
                }
            )
            
            return examples
            
        except Exception as e:
            logger.warning(
                "Failed to retrieve examples content, continuing without examples",
                extra={
                    "request_id": request_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "s3_key": s3_key if 's3_key' in locals() else 'unknown'
                }
            )
            
            # For examples, we gracefully degrade to empty list
            # This allows question generation to continue without examples
            return []
    
    def get_multi_domain_content(self, topics: List[Dict[str, Any]], request_id: str = None) -> Dict[str, Any]:
        """Retrieve content for multiple topics/domains for multi-domain paper generation.
        
        Args:
            topics: List of topic requests with topic, subtopic, tier, count
            request_id: Request ID for logging
            
        Returns:
            Dictionary with all content organized by topic
        """
        logger.info(
            "Retrieving multi-domain content",
            extra={
                "request_id": request_id,
                "topic_count": len(topics)
            }
        )
        
        all_content = {}
        
        for topic_request in topics:
            topic = topic_request.get('topic')
            subtopic = topic_request.get('subtopic')
            tier = topic_request.get('tier', 'both')
            
            try:
                # Get specification content
                spec_content = self.get_specification_content(topic, subtopic, tier, request_id)
                
                # Get examples content
                examples_content = self.get_examples_content(topic, subtopic, tier, request_id)
                
                all_content[f"{topic}_{subtopic or 'general'}"] = {
                    'topic': topic,
                    'subtopic': subtopic,
                    'tier': tier,
                    'count': topic_request.get('count', 1),
                    'specification': spec_content,
                    'examples': examples_content
                }
                
            except Exception as e:
                logger.warning(
                    f"Failed to retrieve content for topic {topic}",
                    extra={
                        "request_id": request_id,
                        "topic": topic,
                        "subtopic": subtopic,
                        "error": str(e)
                    }
                )
                # Continue with other topics even if one fails
                continue
        
        logger.info(
            "Multi-domain content retrieval completed",
            extra={
                "request_id": request_id,
                "successful_topics": len(all_content)
            }
        )
        
        return all_content
    
    def _get_fallback_content(self, topic_key: str, subtopic_key: str, tier: str, 
                            request_id: str, original_error: str) -> Dict[str, Any]:
        """
        Get fallback content when S3 retrieval fails.
        
        Args:
            topic_key: Normalized topic key
            subtopic_key: Normalized subtopic key
            tier: Difficulty tier
            request_id: Request ID for logging
            original_error: Original error that triggered fallback
            
        Returns:
            Fallback content dictionary
            
        Raises:
            ValueError: If no fallback content available
        """
        logger.info(
            "Attempting fallback content retrieval",
            extra={
                "request_id": request_id,
                "topic": topic_key,
                "subtopic": subtopic_key,
                "original_error": original_error
            }
        )
        
        # Try persistent cache first (long-term cached content)
        cache_key = f"spec_{topic_key}_{subtopic_key}_{tier}"
        persistent_content = self._get_from_persistent_cache(cache_key)
        if persistent_content:
            logger.info(
                "Retrieved content from persistent cache as fallback",
                extra={"request_id": request_id, "cache_key": cache_key}
            )
            persistent_content['fallback_source'] = 'persistent_cache'
            return persistent_content
        
        # Try built-in fallback content
        if topic_key in self.FALLBACK_CONTENT:
            if subtopic_key in self.FALLBACK_CONTENT[topic_key]:
                fallback_content = self.FALLBACK_CONTENT[topic_key][subtopic_key].copy()
                
                # Adjust for tier if needed
                if tier != "both":
                    fallback_content['tier'] = tier
                
                fallback_content['fallback_source'] = 'built_in'
                fallback_content['fallback_reason'] = original_error
                
                logger.info(
                    "Using built-in fallback content",
                    extra={
                        "request_id": request_id,
                        "topic": topic_key,
                        "subtopic": subtopic_key
                    }
                )
                
                return fallback_content
        
        # Try generic fallback for the topic
        if topic_key in self.FALLBACK_CONTENT:
            # Use first available subtopic as generic fallback
            first_subtopic = list(self.FALLBACK_CONTENT[topic_key].keys())[0]
            fallback_content = self.FALLBACK_CONTENT[topic_key][first_subtopic].copy()
            
            # Update to reflect actual requested subtopic
            fallback_content['subtopic'] = subtopic_key
            fallback_content['fallback_source'] = 'generic'
            fallback_content['fallback_reason'] = original_error
            
            if tier != "both":
                fallback_content['tier'] = tier
            
            logger.warning(
                f"Using generic fallback content for {topic_key}",
                extra={
                    "request_id": request_id,
                    "requested_subtopic": subtopic_key,
                    "fallback_subtopic": first_subtopic
                }
            )
            
            return fallback_content
        
        # Create minimal fallback content as last resort
        minimal_fallback = {
            "topic": topic_key.title(),
            "subtopic": subtopic_key,
            "tier": tier,
            "learning_objectives": [f"Work with {subtopic_key.replace('_', ' ')} problems"],
            "key_concepts": [f"{subtopic_key.replace('_', ' ').title()} fundamentals"],
            "specification_content": f"Basic {subtopic_key.replace('_', ' ')} content",
            "common_misconceptions": ["Common calculation errors"],
            "assessment_objectives": ["AO1", "AO2"],
            "version": "minimal_fallback",
            "fallback": True,
            "fallback_source": "minimal",
            "fallback_reason": original_error
        }
        
        logger.warning(
            "Using minimal fallback content - limited functionality expected",
            extra={
                "request_id": request_id,
                "topic": topic_key,
                "subtopic": subtopic_key
            }
        )
        
        return minimal_fallback
    
    @exponential_backoff_retry(max_retries=2, base_delay=0.5, max_delay=4.0)
    def _get_s3_object_with_fallback(self, bucket: str, key: str, request_id: str) -> Dict[str, Any]:
        """
        Retrieve S3 object with enhanced error handling and fallback strategies.
        
        Args:
            bucket: S3 bucket name
            key: S3 object key
            request_id: Request ID for logging
            
        Returns:
            Parsed JSON content
            
        Raises:
            RetryableError: For errors that should be retried
            NonRetryableError: For errors that should not be retried
        """
        try:
            logger.debug(
                "Attempting S3 object retrieval",
                extra={
                    "request_id": request_id,
                    "bucket": bucket,
                    "key": key
                }
            )
            
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            content = response['Body'].read().decode('utf-8')
            parsed_content = json.loads(content)
            
            logger.debug(
                "S3 object retrieved successfully",
                extra={
                    "request_id": request_id,
                    "key": key,
                    "content_size": len(content)
                }
            )
            
            return parsed_content
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            
            # Create error context for proper handling
            context = ErrorContext(
                error_type=ErrorType.S3_ACCESS_ERROR,
                operation="s3_object_retrieval",
                request_id=request_id,
                attempt=1,
                max_attempts=3,
                error_message=error_message,
                error_code=error_code,
                additional_context={"bucket": bucket, "key": key}
            )
            
            # Handle error through error handler
            context = self.error_handler.handle_s3_error(e, context)
            
            if error_code == 'NoSuchKey':
                logger.warning(
                    f"S3 object not found: {key}",
                    extra={"request_id": request_id, "bucket": bucket, "key": key}
                )
                raise NonRetryableError(f"Content not found: {key}")
            elif error_code == 'NoSuchBucket':
                logger.error(
                    f"S3 bucket not found: {bucket}",
                    extra={"request_id": request_id, "bucket": bucket}
                )
                raise NonRetryableError(f"Bucket not found: {bucket}")
            elif error_code in ['AccessDenied', 'Forbidden']:
                logger.error(
                    f"S3 access denied for {key}",
                    extra={"request_id": request_id, "bucket": bucket, "key": key}
                )
                raise NonRetryableError(f"Access denied: {key}")
            elif error_code in ['ThrottlingException', 'SlowDown', 'ServiceUnavailable']:
                logger.warning(
                    f"S3 service throttling/unavailable for {key}",
                    extra={"request_id": request_id, "error_code": error_code}
                )
                raise RetryableError(f"S3 service temporarily unavailable: {error_message}")
            else:
                logger.warning(
                    f"S3 client error ({error_code}): {error_message}",
                    extra={"request_id": request_id, "bucket": bucket, "key": key}
                )
                raise RetryableError(f"S3 error ({error_code}): {error_message}")
                
        except json.JSONDecodeError as e:
            logger.error(
                f"Invalid JSON in S3 object {key}: {str(e)}",
                extra={"request_id": request_id, "bucket": bucket, "key": key}
            )
            raise NonRetryableError(f"Invalid JSON in S3 object {key}: {str(e)}")
            
        except BotoCoreError as e:
            logger.warning(
                f"Boto3 error retrieving {key}: {str(e)}",
                extra={
                    "request_id": request_id,
                    "error_type": type(e).__name__,
                    "bucket": bucket,
                    "key": key
                }
            )
            raise RetryableError(f"Network error retrieving {key}: {str(e)}")
            
        except Exception as e:
            logger.error(
                f"Unexpected error retrieving S3 object {key}: {str(e)}",
                extra={
                    "request_id": request_id,
                    "error_type": type(e).__name__,
                    "bucket": bucket,
                    "key": key
                }
            )
            raise RetryableError(f"Unexpected error retrieving {key}: {str(e)}")
    
    def _get_from_persistent_cache(self, key: str) -> Optional[Any]:
        """Get content from persistent cache if not expired."""
        if key in self._persistent_cache:
            cached_item = self._persistent_cache[key]
            if time.time() - cached_item['timestamp'] < self._persistent_cache_ttl:
                return cached_item['content']
            else:
                # Remove expired item
                del self._persistent_cache[key]
        return None
    
    def _add_to_persistent_cache(self, key: str, content: Any) -> None:
        """Add content to persistent cache with longer TTL."""
        self._persistent_cache[key] = {
            'content': content,
            'timestamp': time.time()
        }
        
        # Simple cache size management for persistent cache
        if len(self._persistent_cache) > 50:
            oldest_key = min(self._persistent_cache.keys(), 
                           key=lambda k: self._persistent_cache[k]['timestamp'])
            del self._persistent_cache[oldest_key]
    
    def _get_from_cache(self, key: str) -> Optional[Any]:
        """Get content from in-memory cache if not expired."""
        if key in self._cache:
            cached_item = self._cache[key]
            if time.time() - cached_item['timestamp'] < self._cache_ttl:
                return cached_item['content']
            else:
                # Remove expired item
                del self._cache[key]
        return None
    
    def _add_to_cache(self, key: str, content: Any) -> None:
        """Add content to in-memory cache with timestamp."""
        self._cache[key] = {
            'content': content,
            'timestamp': time.time()
        }
        
        # Simple cache size management - remove oldest if cache gets too large
        if len(self._cache) > 100:
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k]['timestamp'])
            del self._cache[oldest_key]