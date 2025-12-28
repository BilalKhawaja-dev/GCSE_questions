#!/usr/bin/env python3
"""
Enhanced AI Integration System

This system integrates the instruction repository with the AI agents
and provides enhanced question generation capabilities.
"""

import json
import boto3
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# AWS Configuration
AWS_REGION = 'eu-west-2'
INSTRUCTIONS_BUCKET = 'gcse-ai-instructions-prod'
LAMBDA_FUNCTIONS = {
    'interpret': 'gcse-interpret-lambda-prod',
    'generate': 'gcse-generate-lambda-prod'
}

class EnhancedAIIntegration:
    """Enhanced AI integration with instruction repository"""
    
    def __init__(self):
        """Initialize the integration system"""
        self.s3_client = boto3.client('s3', region_name=AWS_REGION)
        self.lambda_client = boto3.client('lambda', region_name=AWS_REGION)
        self.instructions_bucket = INSTRUCTIONS_BUCKET
        
    def load_ai_instructions(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Load instructions for a specific AI agent"""
        
        try:
            s3_key = f"instructions/{agent_name}_lambda_instructions.json"
            
            response = self.s3_client.get_object(
                Bucket=self.instructions_bucket,
                Key=s3_key
            )
            
            instructions = json.loads(response['Body'].read().decode('utf-8'))
            logger.info(f"✅ Loaded instructions for {agent_name}")
            return instructions
            
        except Exception as e:
            logger.error(f"❌ Failed to load instructions for {agent_name}: {str(e)}")
            return None
    
    def update_lambda_with_instructions(self, function_name: str, instructions: Dict[str, Any]) -> bool:
        """Update Lambda function with AI instructions"""
        
        try:
            # Get current environment variables
            response = self.lambda_client.get_function_configuration(FunctionName=function_name)
            current_env = response.get('Environment', {}).get('Variables', {})
            
            # Add instruction-related environment variables
            current_env['AI_INSTRUCTIONS_BUCKET'] = self.instructions_bucket
            current_env['AI_INSTRUCTIONS_VERSION'] = instructions.get('version', '1.0')
            current_env['AI_INSTRUCTIONS_UPDATED'] = datetime.now().isoformat()
            
            # Add specific instruction flags
            if 'interpret' in function_name:
                current_env['ENABLE_ENHANCED_PARSING'] = 'true'
                current_env['CONFIDENCE_THRESHOLD'] = '0.7'
                current_env['MAX_QUESTION_COUNT'] = '10'
            elif 'generate' in function_name:
                current_env['ENABLE_ENHANCED_GENERATION'] = 'true'
                current_env['QUALITY_THRESHOLD'] = '0.8'
                current_env['USE_INSTRUCTION_CONTEXT'] = 'true'
            
            # Update function configuration
            self.lambda_client.update_function_configuration(
                FunctionName=function_name,
                Environment={'Variables': current_env}
            )
            
            logger.info(f"✅ Updated {function_name} with enhanced instructions")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update {function_name}: {str(e)}")
            return False
    
    def create_instruction_retrieval_code(self) -> str:
        """Create code snippet for Lambda functions to retrieve instructions"""
        
        code_snippet = '''
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
'''
        
        return code_snippet
    
    def create_question_bank_enhancer(self) -> Dict[str, str]:
        """Create enhanced question bank processing"""
        
        enhancer_code = {
            "question_bank_processor.py": '''#!/usr/bin/env python3
"""
Question Bank Processor

This script processes large collections of GCSE questions to create
a comprehensive question bank for AI reference.
"""

import json
import re
from typing import Dict, List, Any
from pathlib import Path

class QuestionBankProcessor:
    """Process and enhance question banks for AI reference"""
    
    def __init__(self):
        self.question_patterns = {
            'calculation': r'calculate|work out|find|determine',
            'explanation': r'explain|describe|show|justify',
            'application': r'use|apply|solve|model',
            'analysis': r'compare|analyse|evaluate|assess'
        }
    
    def categorize_question(self, question_text: str) -> Dict[str, Any]:
        """Categorize question by type and complexity"""
        
        question_lower = question_text.lower()
        
        # Determine question type
        question_type = 'calculation'  # default
        for qtype, pattern in self.question_patterns.items():
            if re.search(pattern, question_lower):
                question_type = qtype
                break
        
        # Estimate complexity
        complexity_indicators = {
            'simple': ['add', 'subtract', 'multiply', 'divide', 'find'],
            'medium': ['solve', 'calculate', 'work out', 'determine'],
            'complex': ['analyse', 'evaluate', 'justify', 'compare', 'model']
        }
        
        complexity = 'simple'
        for level, indicators in complexity_indicators.items():
            if any(indicator in question_lower for indicator in indicators):
                complexity = level
        
        return {
            'type': question_type,
            'complexity': complexity,
            'word_count': len(question_text.split()),
            'has_diagram': 'diagram' in question_lower or 'figure' in question_lower,
            'mathematical_content': bool(re.search(r'[+\-×÷=<>()\\[\\]{}]', question_text))
        }
    
    def enhance_question_metadata(self, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enhance questions with additional metadata"""
        
        enhanced_questions = []
        
        for question in questions:
            question_text = question.get('question_text', '')
            
            # Add categorization
            categorization = self.categorize_question(question_text)
            
            # Add enhanced metadata
            enhanced_question = {
                **question,
                'metadata': {
                    **categorization,
                    'enhanced_timestamp': datetime.now().isoformat(),
                    'ai_reference_quality': self.calculate_ai_reference_quality(question),
                    'topic_keywords': self.extract_topic_keywords(question_text),
                    'difficulty_indicators': self.extract_difficulty_indicators(question)
                }
            }
            
            enhanced_questions.append(enhanced_question)
        
        return enhanced_questions
    
    def calculate_ai_reference_quality(self, question: Dict[str, Any]) -> float:
        """Calculate quality score for AI reference purposes"""
        
        score = 1.0
        
        # Check for complete mark scheme
        mark_scheme = question.get('mark_scheme', {})
        if not mark_scheme:
            score -= 0.3
        
        # Check for clear question text
        question_text = question.get('question_text', '')
        if len(question_text) < 20:
            score -= 0.2
        
        # Check for appropriate marks
        marks = question.get('marks', 0)
        if marks <= 0 or marks > 10:
            score -= 0.2
        
        # Bonus for mathematical content
        if re.search(r'[+\-×÷=<>()\\[\\]{}]', question_text):
            score += 0.1
        
        return max(0.0, min(1.0, score))
    
    def extract_topic_keywords(self, question_text: str) -> List[str]:
        """Extract topic-specific keywords from question text"""
        
        topic_keywords = {
            'number': ['fraction', 'decimal', 'percentage', 'ratio', 'proportion'],
            'algebra': ['equation', 'solve', 'x', 'y', 'formula', 'expression'],
            'geometry': ['angle', 'triangle', 'circle', 'area', 'perimeter', 'volume'],
            'statistics': ['mean', 'median', 'mode', 'range', 'data', 'graph'],
            'probability': ['probability', 'chance', 'likely', 'outcome', 'event']
        }
        
        found_keywords = []
        question_lower = question_text.lower()
        
        for topic, keywords in topic_keywords.items():
            for keyword in keywords:
                if keyword in question_lower:
                    found_keywords.append(keyword)
        
        return list(set(found_keywords))
    
    def extract_difficulty_indicators(self, question: Dict[str, Any]) -> Dict[str, Any]:
        """Extract indicators of question difficulty"""
        
        question_text = question.get('question_text', '')
        marks = question.get('marks', 0)
        
        indicators = {
            'mark_allocation': marks,
            'text_complexity': len(question_text.split()),
            'mathematical_operations': len(re.findall(r'[+\-×÷=<>]', question_text)),
            'multi_step': 'then' in question_text.lower() or 'next' in question_text.lower(),
            'requires_explanation': any(word in question_text.lower() for word in ['explain', 'show', 'justify']),
            'contextual': any(word in question_text.lower() for word in ['shop', 'school', 'garden', 'recipe'])
        }
        
        return indicators

# Usage example:
if __name__ == "__main__":
    processor = QuestionBankProcessor()
    
    # Load questions from JSON file
    with open('questions.json', 'r') as f:
        questions = json.load(f)
    
    # Enhance questions
    enhanced_questions = processor.enhance_question_metadata(questions)
    
    # Save enhanced questions
    with open('enhanced_questions.json', 'w') as f:
        json.dump(enhanced_questions, f, indent=2)
    
    print(f"Enhanced {len(enhanced_questions)} questions")
''',
            
            "ai_context_manager.py": '''#!/usr/bin/env python3
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
'''
        }
        
        return enhancer_code
    
    def run_integration_setup(self) -> Dict[str, Any]:
        """Run the complete enhanced AI integration setup"""
        
        logger.info("🚀 Setting up Enhanced AI Integration")
        
        results = {
            'instructions_loaded': {},
            'lambdas_updated': {},
            'code_snippets_created': False,
            'question_bank_tools_created': False,
            'setup_complete': False
        }
        
        try:
            # Step 1: Load instructions for each agent
            logger.info("Step 1: Loading AI instructions")
            for agent in ['interpret', 'generate']:
                instructions = self.load_ai_instructions(agent)
                results['instructions_loaded'][agent] = instructions is not None
                
                if instructions:
                    logger.info(f"✅ Loaded instructions for {agent}")
                else:
                    logger.warning(f"⚠️ Failed to load instructions for {agent}")
            
            # Step 2: Update Lambda functions
            logger.info("Step 2: Updating Lambda functions with instructions")
            for agent, function_name in LAMBDA_FUNCTIONS.items():
                instructions = self.load_ai_instructions(agent)
                if instructions:
                    success = self.update_lambda_with_instructions(function_name, instructions)
                    results['lambdas_updated'][agent] = success
                else:
                    results['lambdas_updated'][agent] = False
            
            # Step 3: Create code snippets
            logger.info("Step 3: Creating instruction retrieval code")
            code_snippet = self.create_instruction_retrieval_code()
            
            with open('lambda_instruction_integration.py', 'w') as f:
                f.write(code_snippet)
            
            results['code_snippets_created'] = True
            logger.info("✅ Created lambda_instruction_integration.py")
            
            # Step 4: Create question bank enhancement tools
            logger.info("Step 4: Creating question bank enhancement tools")
            enhancer_code = self.create_question_bank_enhancer()
            
            for filename, code in enhancer_code.items():
                with open(filename, 'w') as f:
                    f.write(code)
                logger.info(f"✅ Created {filename}")
            
            results['question_bank_tools_created'] = True
            
            # Determine overall success
            results['setup_complete'] = (
                all(results['instructions_loaded'].values()) and
                all(results['lambdas_updated'].values()) and
                results['code_snippets_created'] and
                results['question_bank_tools_created']
            )
            
            if results['setup_complete']:
                logger.info("🎉 Enhanced AI integration setup complete!")
            else:
                logger.warning("⚠️ Setup completed with some issues")
            
        except Exception as e:
            logger.error(f"💥 Integration setup failed: {str(e)}")
            results['error'] = str(e)
        
        return results

def main():
    """Main function"""
    
    print("🤖 ENHANCED AI INTEGRATION SETUP")
    print("=" * 60)
    
    try:
        integration = EnhancedAIIntegration()
        results = integration.run_integration_setup()
        
        print(f"\\n📊 Integration Results:")
        print(f"   Instructions loaded: {results['instructions_loaded']}")
        print(f"   Lambdas updated: {results['lambdas_updated']}")
        print(f"   Code snippets created: {results['code_snippets_created']}")
        print(f"   Question bank tools created: {results['question_bank_tools_created']}")
        print(f"   Setup complete: {results['setup_complete']}")
        
        if results['setup_complete']:
            print(f"\\n🎉 Enhanced AI integration successful!")
            print(f"\\n📚 Your AI agents now have access to:")
            print(f"   • Detailed instruction documents")
            print(f"   • Topic-specific guidance")
            print(f"   • Enhanced question generation capabilities")
            print(f"   • Dynamic context loading")
            
            print(f"\\n🔧 Tools created:")
            print(f"   • lambda_instruction_integration.py - Code for Lambda functions")
            print(f"   • question_bank_processor.py - Question enhancement tool")
            print(f"   • ai_context_manager.py - Dynamic context management")
            
            return True
        else:
            print(f"\\n⚠️ Integration had issues. Check the logs above.")
            return False
            
    except Exception as e:
        print(f"\\n💥 Integration failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)