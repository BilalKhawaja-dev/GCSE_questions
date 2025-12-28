#!/usr/bin/env python3
"""
AI Knowledge Base Upload System

This system provides a clear upload destination for PDFs and creates
an instruction repository for the AI agents to access.
"""

import os
import sys
import json
import boto3
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# AWS Configuration
AWS_REGION = 'eu-west-2'
SPECIFICATIONS_BUCKET = 'gcse-specifications-prod-1a64dc99'
EXAMPLES_BUCKET = 'gcse-examples-prod-1a64dc99'
INSTRUCTIONS_BUCKET = 'gcse-ai-instructions-prod'  # New bucket for AI instructions

class AIKnowledgeUploadSystem:
    """System for uploading content and instructions for AI agents"""
    
    def __init__(self):
        """Initialize the upload system"""
        self.s3_client = boto3.client('s3', region_name=AWS_REGION)
        self.specifications_bucket = SPECIFICATIONS_BUCKET
        self.examples_bucket = EXAMPLES_BUCKET
        self.instructions_bucket = INSTRUCTIONS_BUCKET
        
    def create_ai_instruction_documents(self) -> Dict[str, str]:
        """Create comprehensive instruction documents for AI agents"""
        
        instructions = {}
        
        # InterpretLambda Instructions
        interpret_instructions = {
            "agent_name": "InterpretLambda",
            "role": "Query Interpretation Specialist",
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "instructions": {
                "primary_task": "Parse natural language queries into structured intents for GCSE question generation",
                "parsing_guidelines": [
                    "Extract topic (Number, Algebra, Geometry, Statistics, Probability, Ratio)",
                    "Identify tier (Foundation, Higher, or both)",
                    "Determine question count (default: 3, max: 10)",
                    "Assess confidence level (0.0-1.0)",
                    "Handle ambiguous queries by asking for clarification"
                ],
                "topic_keywords": {
                    "Number": ["fraction", "decimal", "percentage", "number", "arithmetic", "calculation"],
                    "Algebra": ["equation", "algebra", "solve", "quadratic", "linear", "simultaneous", "formula"],
                    "Geometry": ["angle", "shape", "area", "perimeter", "trigonometry", "pythagoras", "geometry"],
                    "Statistics": ["mean", "median", "mode", "range", "data", "graph", "chart", "statistics"],
                    "Probability": ["probability", "chance", "random", "outcome", "likely", "event"],
                    "Ratio": ["ratio", "proportion", "scale", "share", "divide"]
                },
                "tier_detection": {
                    "Foundation": ["foundation", "basic", "simple", "easy", "grade 1-5"],
                    "Higher": ["higher", "advanced", "complex", "difficult", "grade 6-9"],
                    "both": ["mixed", "all levels", "any tier"]
                },
                "confidence_scoring": {
                    "high_confidence": "Clear topic and tier identification with specific keywords",
                    "medium_confidence": "Topic clear but tier ambiguous, or vice versa",
                    "low_confidence": "Ambiguous query requiring clarification"
                },
                "error_handling": [
                    "For unclear queries, return confidence < 0.7 and suggest clarification",
                    "For invalid topics, suggest closest valid topic",
                    "For excessive question counts, cap at 10 and warn user"
                ],
                "response_format": {
                    "topic": "One of: Number, Algebra, Geometry, Statistics, Probability, Ratio",
                    "tier": "One of: Foundation, Higher, both",
                    "count": "Integer between 1-10",
                    "confidence": "Float between 0.0-1.0",
                    "clarification_needed": "Boolean - true if query is ambiguous"
                }
            },
            "examples": [
                {
                    "query": "Generate 3 Foundation fractions questions",
                    "expected_output": {
                        "topic": "Number",
                        "tier": "Foundation", 
                        "count": 3,
                        "confidence": 0.95
                    }
                },
                {
                    "query": "I need some algebra questions",
                    "expected_output": {
                        "topic": "Algebra",
                        "tier": "both",
                        "count": 3,
                        "confidence": 0.7,
                        "clarification_needed": True
                    }
                }
            ]
        }
        
        instructions["interpret_lambda_instructions.json"] = json.dumps(interpret_instructions, indent=2)
        
        # GenerateLambda Instructions
        generate_instructions = {
            "agent_name": "GenerateLambda",
            "role": "GCSE Question Generation Specialist",
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "instructions": {
                "primary_task": "Generate high-quality GCSE mathematics questions based on specifications and examples",
                "generation_principles": [
                    "Use specification content to ensure curriculum alignment",
                    "Reference example questions for style and difficulty",
                    "Generate unique questions - avoid copying examples directly",
                    "Ensure mathematical accuracy and clear language",
                    "Include appropriate mark schemes with detailed criteria"
                ],
                "question_structure": {
                    "question_text": "Clear, unambiguous mathematical problem",
                    "marks": "Appropriate mark allocation (1-6 marks typical)",
                    "tier": "Foundation (grades 1-5) or Higher (grades 6-9)",
                    "topic": "Aligned with curriculum specifications",
                    "difficulty_progression": "Start easier, build complexity"
                },
                "mark_scheme_requirements": [
                    "Method marks (M) for correct approach",
                    "Accuracy marks (A) for correct answers", 
                    "Communication marks (C) for clear explanations when needed",
                    "Alternative methods where applicable",
                    "Common error anticipation"
                ],
                "quality_standards": {
                    "mathematical_accuracy": "All calculations must be correct",
                    "language_clarity": "Use clear, accessible language appropriate for age group",
                    "curriculum_alignment": "Questions must match specification requirements",
                    "difficulty_appropriateness": "Match tier expectations (Foundation vs Higher)",
                    "uniqueness": "Generate fresh questions, not copies of examples"
                },
                "content_utilization": {
                    "specifications": "Use for learning objectives and key concepts",
                    "examples": "Reference for style, format, and difficulty level",
                    "mark_schemes": "Follow established marking patterns",
                    "misconceptions": "Address common student errors"
                },
                "mathematical_notation": [
                    "Use clear fraction notation: 3/4 instead of \\frac{3}{4}",
                    "Simple exponents: x² instead of x^2 where possible",
                    "Clear decimal notation: 0.75 not .75",
                    "Proper units and measurements",
                    "Consistent mathematical symbols"
                ],
                "question_types_by_topic": {
                    "Number": ["Fraction operations", "Decimal calculations", "Percentage problems", "Ratio and proportion"],
                    "Algebra": ["Linear equations", "Quadratic equations", "Formula manipulation", "Simultaneous equations"],
                    "Geometry": ["Angle calculations", "Area and perimeter", "Trigonometry", "Pythagoras theorem"],
                    "Statistics": ["Averages", "Data representation", "Probability calculations", "Data analysis"],
                    "Probability": ["Single events", "Combined events", "Tree diagrams", "Conditional probability"],
                    "Ratio": ["Simplifying ratios", "Sharing in ratios", "Scale factors", "Direct proportion"]
                }
            },
            "examples": [
                {
                    "topic": "Number",
                    "tier": "Foundation",
                    "sample_question": {
                        "question_text": "Simplify the fraction 12/18",
                        "marks": 1,
                        "mark_scheme": {
                            "method": "Find common factors",
                            "answer": "2/3",
                            "marking": "A1 for correct simplified fraction"
                        }
                    }
                }
            ]
        }
        
        instructions["generate_lambda_instructions.json"] = json.dumps(generate_instructions, indent=2)
        
        # Content Upload Guidelines
        upload_guidelines = {
            "title": "Content Upload Guidelines for GCSE Question Generator",
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "upload_destinations": {
                "specifications": {
                    "bucket": SPECIFICATIONS_BUCKET,
                    "purpose": "Curriculum specifications and learning objectives",
                    "format": "JSON files organized by domain/subtopic",
                    "path_structure": "specifications/{domain}/{subtopic}_latest.json"
                },
                "examples": {
                    "bucket": EXAMPLES_BUCKET,
                    "purpose": "Example questions and mark schemes for AI reference",
                    "format": "JSON files with question arrays",
                    "path_structure": "examples/{domain}/{subtopic}.json"
                },
                "instructions": {
                    "bucket": INSTRUCTIONS_BUCKET,
                    "purpose": "AI agent instructions and prompting guides",
                    "format": "JSON instruction documents",
                    "path_structure": "instructions/{agent_name}_instructions.json"
                }
            },
            "pdf_processing_workflow": [
                "1. Collect PDFs from official sources (Edexcel, AQA, OCR)",
                "2. Organize in local directory structure",
                "3. Run: python bulk_pdf_upload_system.py /path/to/pdfs",
                "4. System automatically processes and uploads to correct S3 buckets",
                "5. Verify upload with: python check_s3_content.py",
                "6. Test AI integration with: python validate_ai_integration.py"
            ],
            "content_requirements": {
                "specifications": [
                    "Learning objectives for each topic",
                    "Key concepts and terminology",
                    "Assessment objectives (AO1, AO2, AO3)",
                    "Common misconceptions",
                    "Mark ranges and difficulty indicators"
                ],
                "examples": [
                    "Variety of question types per topic",
                    "Both Foundation and Higher tier questions",
                    "Complete mark schemes with method/accuracy marks",
                    "Quality scoring for AI reference",
                    "Verification status for reliability"
                ]
            },
            "quality_standards": {
                "mathematical_accuracy": "All content must be mathematically correct",
                "curriculum_alignment": "Must match current GCSE specifications",
                "accessibility": "Clear language appropriate for target age group",
                "completeness": "Include all required components (questions, marks, schemes)",
                "uniqueness": "Avoid duplicate content across uploads"
            }
        }
        
        instructions["content_upload_guidelines.json"] = json.dumps(upload_guidelines, indent=2)
        
        return instructions
    
    def upload_instructions_to_s3(self, instructions: Dict[str, str]) -> Dict[str, bool]:
        """Upload instruction documents to S3"""
        
        logger.info(f"Uploading {len(instructions)} instruction documents to S3")
        
        # Create instructions bucket if it doesn't exist
        try:
            self.s3_client.head_bucket(Bucket=self.instructions_bucket)
        except:
            logger.info(f"Creating instructions bucket: {self.instructions_bucket}")
            self.s3_client.create_bucket(
                Bucket=self.instructions_bucket,
                CreateBucketConfiguration={'LocationConstraint': AWS_REGION}
            )
        
        upload_results = {}
        
        for filename, content in instructions.items():
            try:
                s3_key = f"instructions/{filename}"
                
                self.s3_client.put_object(
                    Bucket=self.instructions_bucket,
                    Key=s3_key,
                    Body=content.encode('utf-8'),
                    ContentType='application/json',
                    ServerSideEncryption='AES256'
                )
                
                upload_results[filename] = True
                logger.info(f"✅ Uploaded: {s3_key}")
                
            except Exception as e:
                logger.error(f"❌ Failed to upload {filename}: {str(e)}")
                upload_results[filename] = False
        
        return upload_results
    
    def create_upload_interface(self) -> str:
        """Create a simple upload interface script"""
        
        interface_script = '''#!/usr/bin/env python3
"""
Simple Upload Interface for GCSE Content

This script provides an easy way to upload your PDFs and content
to the AI knowledge base.
"""

import os
import sys
from pathlib import Path

def main():
    print("🎓 GCSE AI Knowledge Base Upload Interface")
    print("=" * 60)
    
    print("\\n📁 Where to put your PDFs:")
    print("   1. Create a folder: mkdir ~/gcse_content")
    print("   2. Organize your PDFs in subfolders:")
    print("      ~/gcse_content/")
    print("      ├── specifications/")
    print("      ├── past_papers/")
    print("      └── mark_schemes/")
    
    print("\\n🚀 How to upload:")
    print("   1. Basic upload:")
    print("      python bulk_pdf_upload_system.py ~/gcse_content")
    print("   2. With progress tracking:")
    print("      python bulk_pdf_upload_system.py ~/gcse_content --output-report report.json")
    
    print("\\n📊 S3 Upload Destinations:")
    print(f"   • Specifications: {SPECIFICATIONS_BUCKET}")
    print(f"   • Examples: {EXAMPLES_BUCKET}")
    print(f"   • AI Instructions: {INSTRUCTIONS_BUCKET}")
    
    print("\\n✅ Verify Upload:")
    print("   python check_s3_content.py")
    print("   python validate_ai_integration.py")
    
    print("\\n💡 Need help? Check:")
    print("   • pdf_collection_guide.md - Where to find PDFs")
    print("   • content_upload_guidelines.json - Detailed instructions")
    
    # Interactive upload option
    pdf_dir = input("\\n📂 Enter path to your PDF directory (or press Enter to skip): ").strip()
    
    if pdf_dir and os.path.exists(pdf_dir):
        print(f"\\n🔄 Starting upload from: {pdf_dir}")
        os.system(f"python bulk_pdf_upload_system.py {pdf_dir} --output-report upload_report.json")
        print("\\n✅ Upload complete! Check upload_report.json for details.")
    else:
        print("\\n👋 No upload performed. Run this script again when ready!")

if __name__ == "__main__":
    main()
'''
        
        return interface_script
    
    def run_setup(self) -> Dict[str, Any]:
        """Run the complete AI knowledge base setup"""
        
        logger.info("🚀 Setting up AI Knowledge Base Upload System")
        
        results = {
            'instructions_created': False,
            'instructions_uploaded': False,
            'interface_created': False,
            'upload_results': {},
            'setup_complete': False
        }
        
        try:
            # Step 1: Create instruction documents
            logger.info("Step 1: Creating AI instruction documents")
            instructions = self.create_ai_instruction_documents()
            results['instructions_created'] = True
            logger.info(f"✅ Created {len(instructions)} instruction documents")
            
            # Step 2: Upload instructions to S3
            logger.info("Step 2: Uploading instructions to S3")
            upload_results = self.upload_instructions_to_s3(instructions)
            results['upload_results'] = upload_results
            results['instructions_uploaded'] = all(upload_results.values())
            
            # Step 3: Create upload interface
            logger.info("Step 3: Creating upload interface")
            interface_script = self.create_upload_interface()
            
            with open('upload_interface.py', 'w') as f:
                f.write(interface_script)
            
            os.chmod('upload_interface.py', 0o755)  # Make executable
            results['interface_created'] = True
            logger.info("✅ Created upload_interface.py")
            
            # Step 4: Save local copies of instructions
            logger.info("Step 4: Saving local instruction copies")
            os.makedirs('ai_instructions', exist_ok=True)
            
            for filename, content in instructions.items():
                with open(f'ai_instructions/{filename}', 'w') as f:
                    f.write(content)
            
            results['setup_complete'] = all([
                results['instructions_created'],
                results['instructions_uploaded'],
                results['interface_created']
            ])
            
            if results['setup_complete']:
                logger.info("🎉 AI Knowledge Base setup complete!")
            else:
                logger.warning("⚠️ Setup completed with some issues")
            
        except Exception as e:
            logger.error(f"💥 Setup failed: {str(e)}")
            results['error'] = str(e)
        
        return results

def main():
    """Main function"""
    
    print("🤖 AI KNOWLEDGE BASE UPLOAD SYSTEM")
    print("=" * 60)
    
    try:
        system = AIKnowledgeUploadSystem()
        results = system.run_setup()
        
        print(f"\\n📊 Setup Results:")
        print(f"   Instructions created: {results['instructions_created']}")
        print(f"   Instructions uploaded: {results['instructions_uploaded']}")
        print(f"   Interface created: {results['interface_created']}")
        print(f"   Setup complete: {results['setup_complete']}")
        
        if results['setup_complete']:
            print(f"\\n🎉 Setup successful!")
            print(f"\\n📁 Your upload destinations:")
            print(f"   • Specifications: s3://{SPECIFICATIONS_BUCKET}")
            print(f"   • Examples: s3://{EXAMPLES_BUCKET}")
            print(f"   • Instructions: s3://{INSTRUCTIONS_BUCKET}")
            
            print(f"\\n🚀 To upload your PDFs:")
            print(f"   1. Run: python upload_interface.py")
            print(f"   2. Or directly: python bulk_pdf_upload_system.py /path/to/pdfs")
            
            print(f"\\n📚 AI Instructions available at:")
            print(f"   • Local: ./ai_instructions/")
            print(f"   • S3: s3://{INSTRUCTIONS_BUCKET}/instructions/")
            
            return True
        else:
            print(f"\\n⚠️ Setup had issues. Check the logs above.")
            return False
            
    except Exception as e:
        print(f"\\n💥 Setup failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)