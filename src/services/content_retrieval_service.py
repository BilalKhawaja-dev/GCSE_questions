"""
Content retrieval service for S3-based specification and examples storage.

This service handles deterministic topic-to-file mapping and retrieval of
specification content and seed examples from S3 buckets.
"""

import json
import logging
import time
from typing import Dict, Any, List, Optional
import boto3
from botocore.exceptions import ClientError, BotoCoreError

from src.models.specification_content import SpecificationContent
from src.services.version_management_service import VersionManagementService

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Circuit breaker pattern implementation for S3 resilience."""
    
    def __init__(self, failure_threshold: int = 3, timeout: int = 60):
        """Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds to wait before attempting to close circuit
        """
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: If function fails
        """
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "HALF_OPEN"
                logger.info("Circuit breaker transitioning to HALF_OPEN")
            else:
                raise CircuitBreakerOpenError("S3 service unavailable - circuit breaker open")
        
        try:
            result = func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
                logger.info("Circuit breaker closed - service recovered")
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                logger.error(f"Circuit breaker opened after {self.failure_count} failures")
            raise


class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class ContentRetrievalService:
    """Service for retrieving specification content and examples from S3."""
    
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
    
    def __init__(self, specifications_bucket: str, examples_bucket: str, region: str = 'eu-west-2'):
        """Initialize content retrieval service.
        
        Args:
            specifications_bucket: S3 bucket name for specifications
            examples_bucket: S3 bucket name for examples
            region: AWS region
        """
        self.specifications_bucket = specifications_bucket
        self.examples_bucket = examples_bucket
        self.region = region
        self.s3_client = boto3.client('s3', region_name=region)
        self.circuit_breaker = CircuitBreaker()
        self.version_service = VersionManagementService(self.s3_client)
        
        # In-memory cache for frequently accessed content
        self._cache = {}
        self._cache_ttl = 3600  # 1 hour TTL
        
    def get_specification_content(self, topic: str, subtopic: Optional[str] = None, 
                                tier: str = "both", request_id: str = None) -> Dict[str, Any]:
        """Retrieve specification content from S3 based on topic.
        
        Args:
            topic: Main topic (e.g., "Number", "Algebra")
            subtopic: Specific subtopic (e.g., "fractions", "linear_equations")
            tier: Difficulty tier filter
            request_id: Request ID for logging
            
        Returns:
            Specification content dictionary
            
        Raises:
            ValueError: If topic/subtopic not found
            CircuitBreakerOpenError: If S3 service unavailable
            Exception: If retrieval fails
        """
        logger.info(
            "Retrieving specification content",
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
        
        # Check cache first
        cache_key = f"spec_{mapping['domain']}_{mapping['file']}_{tier}"
        cached_content = self._get_from_cache(cache_key)
        if cached_content:
            logger.info(
                "Retrieved specification content from cache",
                extra={"request_id": request_id, "cache_key": cache_key}
            )
            return cached_content
        
        # Retrieve from S3 with circuit breaker protection
        try:
            s3_key = f"specifications/{mapping['domain']}/{mapping['file']}"
            content = self.circuit_breaker.call(self._get_s3_object, self.specifications_bucket, s3_key)
            
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
                "Retrieved specification content from S3",
                extra={
                    "request_id": request_id,
                    "s3_key": s3_key,
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
                "Failed to retrieve specification content",
                extra={
                    "request_id": request_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "s3_key": s3_key
                }
            )
            raise Exception(f"Failed to retrieve specification content: {str(e)}")
    
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
    
    def get_examples_content(self, topic: str, subtopic: Optional[str] = None, 
                           tier: str = "both", request_id: str = None) -> List[Dict[str, Any]]:
        """Retrieve seed examples from S3 based on topic.
        
        Args:
            topic: Main topic (e.g., "Number", "Algebra")
            subtopic: Specific subtopic (e.g., "fractions", "linear_equations")
            tier: Difficulty tier filter
            request_id: Request ID for logging
            
        Returns:
            List of example dictionaries
            
        Raises:
            ValueError: If topic/subtopic not found
            CircuitBreakerOpenError: If S3 service unavailable
        """
        logger.info(
            "Retrieving examples content",
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
        
        # Check cache first
        cache_key = f"examples_{mapping['domain']}_{mapping['file']}_{tier}"
        cached_examples = self._get_from_cache(cache_key)
        if cached_examples:
            logger.info(
                "Retrieved examples content from cache",
                extra={"request_id": request_id, "cache_key": cache_key}
            )
            return cached_examples
        
        # Retrieve from S3 with circuit breaker protection
        try:
            s3_key = f"examples/{mapping['domain']}/{mapping['file']}"
            content = self.circuit_breaker.call(self._get_s3_object, self.examples_bucket, s3_key)
            
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
            
        except CircuitBreakerOpenError:
            logger.error(
                "S3 service unavailable for examples - circuit breaker open",
                extra={"request_id": request_id}
            )
            return []  # Return empty list for examples if S3 unavailable
        except Exception as e:
            logger.warning(
                "Failed to retrieve examples content, continuing without examples",
                extra={
                    "request_id": request_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "s3_key": s3_key
                }
            )
            return []  # Return empty list rather than failing
    
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
    
    def _get_s3_object(self, bucket: str, key: str) -> Dict[str, Any]:
        """Retrieve and parse JSON object from S3.
        
        Args:
            bucket: S3 bucket name
            key: S3 object key
            
        Returns:
            Parsed JSON content
            
        Raises:
            Exception: If retrieval or parsing fails
        """
        try:
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            content = response['Body'].read().decode('utf-8')
            return json.loads(content)
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == 'NoSuchKey':
                raise ValueError(f"Content not found: {key}")
            elif error_code == 'NoSuchBucket':
                raise ValueError(f"Bucket not found: {bucket}")
            else:
                raise Exception(f"S3 error ({error_code}): {str(e)}")
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON in S3 object {key}: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to retrieve S3 object {key}: {str(e)}")
    
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