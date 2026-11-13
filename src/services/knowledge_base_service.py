"""
Knowledge Base Service for querying Bedrock Knowledge Base.
Retrieves relevant Edexcel content from uploaded PDFs.
"""

import logging
import time
import boto3
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class KnowledgeBaseService:
    """Service for querying Bedrock Knowledge Base to retrieve PDF content."""
    
    def __init__(self, knowledge_base_id: str, region: str = 'eu-west-2'):
        """Initialize KB service.
        
        Args:
            knowledge_base_id: Bedrock Knowledge Base ID
            region: AWS region
        """
        self.knowledge_base_id = knowledge_base_id
        self.region = region
        self.bedrock_agent_client = boto3.client(
            'bedrock-agent-runtime',
            region_name=region
        )
        self._cache = {}
        self._cache_ttl = 3600  # 1 hour cache
    
    def retrieve_relevant_content(
        self,
        query: str,
        topic: str,
        tier: str,
        max_results: int = 5,
        request_id: str = None
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant Edexcel content from knowledge base.
        
        Args:
            query: Search query
            topic: Topic filter
            tier: Tier filter
            max_results: Max results to return
            request_id: Request ID for logging
            
        Returns:
            List of content chunks with scores
        """
        cache_key = f"{query}_{topic}_{tier}_{max_results}"
        
        # Check cache
        if cache_key in self._cache:
            cached_data, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                logger.info(f"KB cache hit for: {query}")
                return cached_data
        
        try:
            # Build search query
            search_query = f"{topic} {tier} {query}"
            
            logger.info(f"Querying KB: {search_query} (request: {request_id})")
            
            # Query knowledge base
            response = self.bedrock_agent_client.retrieve(
                knowledgeBaseId=self.knowledge_base_id,
                retrievalQuery={'text': search_query},
                retrievalConfiguration={
                    'vectorSearchConfiguration': {
                        'numberOfResults': max_results,
                        'overrideSearchType': 'HYBRID'
                    }
                }
            )
            
            # Extract results
            results = []
            for result in response.get('retrievalResults', []):
                content = result.get('content', {}).get('text', '')
                score = result.get('score', 0.0)
                metadata = result.get('metadata', {})
                
                # Only high-confidence results
                if score > 0.5 and len(content) > 50:
                    results.append({
                        'content': content,
                        'score': score,
                        'source': metadata.get('x-amz-bedrock-kb-source-uri', 'unknown'),
                        'metadata': metadata
                    })
            
            logger.info(f"KB returned {len(results)} relevant chunks")
            
            # Cache results
            self._cache[cache_key] = (results, time.time())
            
            return results
            
        except Exception as e:
            logger.error(f"KB query failed: {str(e)}")
            return []  # Graceful degradation
    
    def build_enriched_context(
        self,
        retrieved_content: List[Dict[str, Any]],
        max_length: int = 2000
    ) -> str:
        """Build formatted context from KB results.
        
        Args:
            retrieved_content: KB query results
            max_length: Max context length
            
        Returns:
            Formatted context string
        """
        if not retrieved_content:
            return ""
        
        parts = [
            "AUTHENTIC EDEXCEL EXAM CONTENT:",
            "The following is from real Edexcel past papers and mark schemes:",
            ""
        ]
        
        current_len = len('\n'.join(parts))
        
        for i, item in enumerate(retrieved_content, 1):
            content = item['content']
            score = item['score']
            
            chunk = f"[Example {i} - Confidence: {score:.0%}]\n{content}\n"
            
            if current_len + len(chunk) > max_length:
                break
            
            parts.append(chunk)
            current_len += len(chunk)
        
        parts.append(
            "\nIMPORTANT: Generate questions that match the EXACT style, "
            "wording, and format of the Edexcel content above."
        )
        
        return '\n'.join(parts)
