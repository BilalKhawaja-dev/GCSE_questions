
# AI Instruction Retrieval Code
# Add this to your Lambda functions to access AI instructions

import json
import boto3
from typing import Dict, Any, Optional

def get_ai_instructions(agent_name: str) -> Optional[Dict[str, Any]]:
    """Retrieve AI instructions from S3"""
    
    try:
        s3_client = boto3.client('s3')
        instructions_bucket = os.environ.get('AI_INSTRUCTIONS_BUCKET', 'gcse-ai-instructions-prod')
        
        s3_key = f"instructions/{agent_name}_lambda_instructions.json"
        
        response = s3_client.get_object(
            Bucket=instructions_bucket,
            Key=s3_key
        )
        
        instructions = json.loads(response['Body'].read().decode('utf-8'))
        return instructions
        
    except Exception as e:
        print(f"Failed to load AI instructions: {str(e)}")
        return None

def enhance_prompt_with_instructions(base_prompt: str, instructions: Dict[str, Any]) -> str:
    """Enhance base prompt with AI instructions"""
    
    if not instructions:
        return base_prompt
    
    instruction_text = instructions.get('instructions', {})
    
    enhanced_prompt = f"""
{base_prompt}

IMPORTANT INSTRUCTIONS:
{json.dumps(instruction_text, indent=2)}

Follow these instructions precisely to ensure high-quality responses.
"""
    
    return enhanced_prompt

# Usage in InterpretLambda:
def lambda_handler(event, context):
    # Load instructions
    instructions = get_ai_instructions('interpret')
    
    # Get base prompt
    base_prompt = "Parse this query into structured intent..."
    
    # Enhance with instructions
    enhanced_prompt = enhance_prompt_with_instructions(base_prompt, instructions)
    
    # Use enhanced prompt with Bedrock
    # ... rest of your code

# Usage in GenerateLambda:
def lambda_handler(event, context):
    # Load instructions
    instructions = get_ai_instructions('generate')
    
    # Get base prompt
    base_prompt = "Generate GCSE questions based on..."
    
    # Enhance with instructions
    enhanced_prompt = enhance_prompt_with_instructions(base_prompt, instructions)
    
    # Use enhanced prompt with Bedrock
    # ... rest of your code
