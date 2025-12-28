#!/usr/bin/env python3
"""
AI Context Manager

This system manages context loading for AI agents based on query type
and provides dynamic instruction enhancement.
"""

import json
import boto3
from typing import Dict, List, Any, Optional

class AIContextManager:
    """Manage AI context and instructions dynamically"""
    
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.instructions_bucket = 'gcse-ai-instructions-prod'
        self.examples_bucket = 'gcse-examples-prod-1a64dc99'
        self.specifications_bucket = 'gcse-specifications-prod-1a64dc99'
    
    def get_context_for_query(self, topic: str, tier: str, query_type: str = 'generation') -> Dict[str, Any]:
        """Get comprehensive context for AI query processing"""
        
        context = {
            'instructions': self.load_instructions(query_type),
            'specifications': self.load_specifications(topic, tier),
            'examples': self.load_examples(topic, tier),
            'topic_guidance': self.get_topic_specific_guidance(topic),
            'tier_guidance': self.get_tier_specific_guidance(tier)
        }
        
        return context
    
    def load_instructions(self, agent_type: str) -> Optional[Dict[str, Any]]:
        """Load instructions for specific agent type"""
        
        try:
            s3_key = f"instructions/{agent_type}_lambda_instructions.json"
            
            response = self.s3_client.get_object(
                Bucket=self.instructions_bucket,
                Key=s3_key
            )
            
            return json.loads(response['Body'].read().decode('utf-8'))
            
        except Exception as e:
            print(f"Failed to load instructions: {str(e)}")
            return None
    
    def load_specifications(self, topic: str, tier: str) -> Optional[Dict[str, Any]]:
        """Load specification content for topic and tier"""
        
        try:
            # Try to find topic-specific specification
            topic_lower = topic.lower()
            s3_key = f"specifications/{topic_lower}/latest.json"
            
            response = self.s3_client.get_object(
                Bucket=self.specifications_bucket,
                Key=s3_key
            )
            
            spec_data = json.loads(response['Body'].read().decode('utf-8'))
            
            # Filter by tier if specified
            if tier.lower() != 'both':
                spec_data = self.filter_by_tier(spec_data, tier)
            
            return spec_data
            
        except Exception as e:
            print(f"Failed to load specifications: {str(e)}")
            return None
    
    def load_examples(self, topic: str, tier: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Load example questions for topic and tier"""
        
        try:
            topic_lower = topic.lower()
            s3_key = f"examples/{topic_lower}/examples.json"
            
            response = self.s3_client.get_object(
                Bucket=self.examples_bucket,
                Key=s3_key
            )
            
            examples_data = json.loads(response['Body'].read().decode('utf-8'))
            examples = examples_data.get('examples', [])
            
            # Filter by tier
            if tier.lower() != 'both':
                examples = [ex for ex in examples if ex.get('question', {}).get('tier', '').lower() == tier.lower()]
            
            # Limit number of examples
            return examples[:limit]
            
        except Exception as e:
            print(f"Failed to load examples: {str(e)}")
            return []
    
    def get_topic_specific_guidance(self, topic: str) -> Dict[str, Any]:
        """Get topic-specific guidance for AI agents"""
        
        guidance = {
            'Number': {
                'focus_areas': ['Fractions', 'Decimals', 'Percentages', 'Ratio'],
                'common_mistakes': ['Adding denominators', 'Decimal place errors'],
                'key_skills': ['Simplification', 'Conversion', 'Calculation']
            },
            'Algebra': {
                'focus_areas': ['Linear equations', 'Quadratics', 'Simultaneous equations'],
                'common_mistakes': ['Sign errors', 'Not balancing equations'],
                'key_skills': ['Substitution', 'Rearrangement', 'Factorization']
            },
            'Geometry': {
                'focus_areas': ['Angles', 'Area/Perimeter', 'Trigonometry'],
                'common_mistakes': ['Angle sum errors', 'Unit confusion'],
                'key_skills': ['Angle calculation', 'Formula application', 'Theorem use']
            },
            'Statistics': {
                'focus_areas': ['Averages', 'Data representation', 'Interpretation'],
                'common_mistakes': ['Mean vs median confusion', 'Scale reading errors'],
                'key_skills': ['Calculation', 'Graph reading', 'Data analysis']
            },
            'Probability': {
                'focus_areas': ['Single events', 'Combined events', 'Tree diagrams'],
                'common_mistakes': ['Adding instead of multiplying', 'Forgetting complementary events'],
                'key_skills': ['Probability calculation', 'Tree diagrams', 'Conditional probability']
            },
            'Ratio': {
                'focus_areas': ['Simplification', 'Sharing', 'Scale factors'],
                'common_mistakes': ['Incorrect sharing', 'Scale factor errors'],
                'key_skills': ['Ratio simplification', 'Proportional reasoning', 'Scale calculations']
            }
        }
        
        return guidance.get(topic, {})
    
    def get_tier_specific_guidance(self, tier: str) -> Dict[str, Any]:
        """Get tier-specific guidance for AI agents"""
        
        guidance = {
            'Foundation': {
                'target_grades': '1-5',
                'complexity_level': 'Basic to intermediate',
                'typical_marks': '1-4 marks per question',
                'language_level': 'Clear, simple language',
                'context': 'Familiar, everyday contexts'
            },
            'Higher': {
                'target_grades': '6-9',
                'complexity_level': 'Intermediate to advanced',
                'typical_marks': '2-6 marks per question',
                'language_level': 'More sophisticated mathematical language',
                'context': 'Abstract and complex contexts'
            }
        }
        
        return guidance.get(tier, guidance.get('Foundation', {}))
    
    def filter_by_tier(self, data: Dict[str, Any], tier: str) -> Dict[str, Any]:
        """Filter data by tier requirements"""
        
        # This would implement tier-specific filtering logic
        # For now, return the data as-is
        return data
    
    def create_enhanced_prompt(self, base_prompt: str, context: Dict[str, Any]) -> str:
        """Create enhanced prompt with full context"""
        
        enhanced_prompt = f"""
{base_prompt}

CONTEXT AND INSTRUCTIONS:

Instructions: {json.dumps(context.get('instructions', {}), indent=2)}

Topic Guidance: {json.dumps(context.get('topic_guidance', {}), indent=2)}

Tier Guidance: {json.dumps(context.get('tier_guidance', {}), indent=2)}

Example Questions: {json.dumps(context.get('examples', [])[:3], indent=2)}

Specifications: {json.dumps(context.get('specifications', {}), indent=2)}

Use this context to provide the highest quality response possible.
"""
        
        return enhanced_prompt

# Usage in Lambda functions:
def enhanced_lambda_handler(event, context):
    context_manager = AIContextManager()
    
    # Extract query parameters
    topic = event.get('topic', 'Number')
    tier = event.get('tier', 'Foundation')
    
    # Get comprehensive context
    ai_context = context_manager.get_context_for_query(topic, tier, 'generation')
    
    # Create enhanced prompt
    base_prompt = "Generate GCSE questions..."
    enhanced_prompt = context_manager.create_enhanced_prompt(base_prompt, ai_context)
    
    # Use enhanced prompt with Bedrock
    # ... rest of your code
