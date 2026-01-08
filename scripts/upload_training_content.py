#!/usr/bin/env python3
"""
Training Content Upload Tool for GCSE Question Generator

This script helps you upload and process PDFs (like Edexcel exam specifications)
to train the AI model with your specific content requirements.

Usage:
    python scripts/upload_training_content.py --pdf path/to/edexcel_spec.pdf --type specification
    python scripts/upload_training_content.py --pdf path/to/sample_questions.pdf --type examples
    python scripts/upload_training_content.py --validate-content
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

import boto3
from botocore.exceptions import ClientError

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from src.services.content_processing_service import ContentProcessingService
from src.services.content_upload_service import ContentUploadService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TrainingContentUploader:
    """Tool for uploading and processing training content for the AI model."""
    
    def __init__(self, environment: str = "dev"):
        """Initialize the uploader with AWS configuration."""
        self.environment = environment
        self.s3_client = boto3.client('s3')
        self.content_processor = ContentProcessingService(self.s3_client)
        self.content_uploader = ContentUploadService()
        
        # Get bucket names from environment or use defaults
        self.specifications_bucket = os.environ.get(
            'SPECIFICATIONS_BUCKET', 
            f'gcse-specifications-{environment}'
        )
        self.examples_bucket = os.environ.get(
            'EXAMPLES_BUCKET', 
            f'gcse-examples-{environment}'
        )
    
    def upload_specification_pdf(self, pdf_path: str, version: str = "2024.1") -> Dict[str, Any]:
        """
        Upload and process an Edexcel specification PDF.
        
        Args:
            pdf_path: Path to the PDF file
            version: Version tag for the specification
            
        Returns:
            Dictionary with upload results and processing summary
        """
        logger.info(f"Processing specification PDF: {pdf_path}")
        
        if not Path(pdf_path).exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        try:
            # Step 1: Parse the PDF
            logger.info("Step 1: Parsing PDF content...")
            processed_content = self.content_processor.parse_edexcel_pdf(pdf_path)
            
            if not processed_content:
                logger.warning("No content extracted from PDF")
                return {"success": False, "error": "No content extracted"}
            
            logger.info(f"Extracted {len(processed_content)} content sections")
            
            # Step 2: Organize content by domain/subtopic
            logger.info("Step 2: Organizing content by domain...")
            organized_content = self.content_processor.organize_content_by_domain(processed_content)
            
            # Step 3: Generate JSON files
            logger.info("Step 3: Generating JSON files...")
            json_files = self.content_processor.generate_json_files(organized_content)
            
            # Step 4: Add version tagging
            logger.info("Step 4: Adding version tags...")
            versioned_files = {}
            for file_path, json_content in json_files.items():
                versioned_content = self.content_processor.add_version_tagging(json_content, version)
                versioned_files[file_path] = versioned_content
            
            # Step 5: Upload to S3
            logger.info("Step 5: Uploading to S3...")
            upload_results = self.content_processor.upload_to_s3(
                versioned_files, 
                self.specifications_bucket
            )
            
            # Step 6: Verify upload
            logger.info("Step 6: Verifying upload...")
            verification = self.content_processor.verify_s3_structure(self.specifications_bucket)
            
            successful_uploads = sum(1 for success in upload_results.values() if success)
            
            result = {
                "success": successful_uploads > 0,
                "processed_sections": len(processed_content),
                "organized_domains": len(organized_content),
                "generated_files": len(json_files),
                "successful_uploads": successful_uploads,
                "total_files": len(json_files),
                "upload_results": upload_results,
                "verification": verification,
                "version": version
            }
            
            logger.info(f"Specification upload completed: {successful_uploads}/{len(json_files)} files uploaded")
            return result
            
        except Exception as e:
            logger.error(f"Error processing specification PDF: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def upload_examples_pdf(self, pdf_path: str, quality_threshold: float = 0.7) -> Dict[str, Any]:
        """
        Upload and process a PDF containing example questions.
        
        Args:
            pdf_path: Path to the PDF file
            quality_threshold: Minimum quality score for examples (0.0-1.0)
            
        Returns:
            Dictionary with upload results and processing summary
        """
        logger.info(f"Processing examples PDF: {pdf_path}")
        
        if not Path(pdf_path).exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        try:
            # For now, we'll create a placeholder for PDF example extraction
            # In a full implementation, you'd parse the PDF to extract questions and mark schemes
            logger.warning("PDF example extraction not yet implemented. Using manual JSON input method.")
            
            # Suggest manual approach
            suggestion = {
                "success": False,
                "message": "PDF example extraction not implemented yet",
                "suggested_approach": {
                    "method": "manual_json",
                    "description": "Create a JSON file with your examples",
                    "format": {
                        "examples": [
                            {
                                "question": {
                                    "question_text": "Your question text here",
                                    "marks": 4,
                                    "tier": "Foundation",
                                    "topic": "Number",
                                    "subtopic": "fractions",
                                    "difficulty_score": 3
                                },
                                "mark_scheme": {
                                    "marking_criteria": "M1: Method mark, A1: Accuracy mark",
                                    "method_marks": 3,
                                    "accuracy_marks": 1,
                                    "answer": "Step-by-step solution"
                                }
                            }
                        ]
                    },
                    "upload_command": f"python {__file__} --json examples.json --type examples"
                }
            }
            
            return suggestion
            
        except Exception as e:
            logger.error(f"Error processing examples PDF: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def upload_examples_json(self, json_path: str, quality_threshold: float = 0.7) -> Dict[str, Any]:
        """
        Upload examples from a JSON file.
        
        Args:
            json_path: Path to the JSON file containing examples
            quality_threshold: Minimum quality score for examples
            
        Returns:
            Dictionary with upload results
        """
        logger.info(f"Processing examples JSON: {json_path}")
        
        if not Path(json_path).exists():
            raise FileNotFoundError(f"JSON file not found: {json_path}")
        
        try:
            # Load JSON data
            with open(json_path, 'r', encoding='utf-8') as f:
                examples_data = json.load(f)
            
            if 'examples' not in examples_data:
                raise ValueError("JSON must contain 'examples' array")
            
            # Process examples
            logger.info(f"Processing {len(examples_data['examples'])} examples...")
            organized_examples = self.content_processor.process_seed_examples(examples_data['examples'])
            
            # Filter by quality threshold
            filtered_examples = {}
            total_examples = 0
            quality_examples = 0
            
            for domain_subtopic, examples in organized_examples.items():
                filtered_list = [ex for ex in examples if ex.quality_score >= quality_threshold]
                if filtered_list:
                    filtered_examples[domain_subtopic] = filtered_list
                    quality_examples += len(filtered_list)
                total_examples += len(examples)
            
            logger.info(f"Quality filter: {quality_examples}/{total_examples} examples meet threshold {quality_threshold}")
            
            # Generate JSON files
            json_files = self.content_processor.generate_examples_json(filtered_examples)
            
            # Upload to S3
            upload_results = self.content_processor.upload_to_s3(
                json_files, 
                self.specifications_bucket,  # Use same bucket for now
                self.examples_bucket
            )
            
            successful_uploads = sum(1 for success in upload_results.values() if success)
            
            result = {
                "success": successful_uploads > 0,
                "total_examples": total_examples,
                "quality_examples": quality_examples,
                "quality_threshold": quality_threshold,
                "organized_topics": len(filtered_examples),
                "generated_files": len(json_files),
                "successful_uploads": successful_uploads,
                "upload_results": upload_results
            }
            
            logger.info(f"Examples upload completed: {successful_uploads}/{len(json_files)} files uploaded")
            return result
            
        except Exception as e:
            logger.error(f"Error processing examples JSON: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def validate_content(self) -> Dict[str, Any]:
        """
        Validate the current content in S3 buckets.
        
        Returns:
            Dictionary with validation results
        """
        logger.info("Validating content in S3 buckets...")
        
        try:
            verification = self.content_processor.verify_s3_structure(
                self.specifications_bucket, 
                self.examples_bucket
            )
            
            # Additional validation
            spec_files = verification['specifications_bucket']['files']
            examples_files = verification['examples_bucket']['files']
            
            # Count content by domain
            domains = set()
            for file_path in spec_files:
                if file_path.startswith('specifications/'):
                    parts = file_path.split('/')
                    if len(parts) >= 2:
                        domains.add(parts[1])
            
            # Check for required domains
            required_domains = ['number', 'algebra', 'geometry', 'statistics']
            missing_domains = [d for d in required_domains if d not in domains]
            
            validation_result = {
                "specifications_bucket": {
                    "exists": verification['specifications_bucket']['exists'],
                    "file_count": len(spec_files),
                    "domains_found": list(domains),
                    "missing_domains": missing_domains
                },
                "examples_bucket": {
                    "exists": verification['examples_bucket']['exists'],
                    "file_count": len(examples_files)
                },
                "overall_status": "healthy" if not missing_domains else "incomplete",
                "recommendations": []
            }
            
            # Generate recommendations
            if missing_domains:
                validation_result["recommendations"].append(
                    f"Upload specifications for missing domains: {', '.join(missing_domains)}"
                )
            
            if len(examples_files) == 0:
                validation_result["recommendations"].append(
                    "Upload example questions to improve AI training"
                )
            
            if len(spec_files) < 10:
                validation_result["recommendations"].append(
                    "Consider uploading more detailed specifications for better coverage"
                )
            
            logger.info(f"Validation completed: {validation_result['overall_status']}")
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating content: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def create_example_template(self, output_path: str = "example_template.json") -> str:
        """
        Create a template JSON file for manual example entry.
        
        Args:
            output_path: Path where to save the template
            
        Returns:
            Path to the created template file
        """
        template = {
            "metadata": {
                "description": "Template for uploading example questions to train the AI",
                "version": "1.0",
                "instructions": [
                    "Fill in the examples array with your questions",
                    "Ensure each question has all required fields",
                    "Use appropriate difficulty scores (1-5 for Foundation, 6-10 for Higher)",
                    "Upload using: python scripts/upload_training_content.py --json this_file.json --type examples"
                ]
            },
            "examples": [
                {
                    "question": {
                        "question_text": "Calculate 3/4 + 1/8. Give your answer as a fraction in its simplest form.",
                        "marks": 3,
                        "tier": "Foundation",
                        "topic": "Number",
                        "subtopic": "fractions",
                        "difficulty_score": 3
                    },
                    "mark_scheme": {
                        "marking_criteria": "M1: Convert to common denominator (6/8 + 1/8), M1: Add fractions (7/8), A1: Correct final answer",
                        "method_marks": 2,
                        "accuracy_marks": 1,
                        "answer": "3/4 + 1/8 = 6/8 + 1/8 = 7/8"
                    }
                },
                {
                    "question": {
                        "question_text": "Solve the equation 2x + 5 = 17",
                        "marks": 2,
                        "tier": "Foundation", 
                        "topic": "Algebra",
                        "subtopic": "linear-equations",
                        "difficulty_score": 4
                    },
                    "mark_scheme": {
                        "marking_criteria": "M1: Subtract 5 from both sides (2x = 12), A1: Divide by 2 (x = 6)",
                        "method_marks": 1,
                        "accuracy_marks": 1,
                        "answer": "2x + 5 = 17, 2x = 12, x = 6"
                    }
                }
            ]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(template, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Template created: {output_path}")
        return output_path


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(
        description="Upload and process training content for GCSE Question Generator AI"
    )
    
    parser.add_argument(
        '--pdf', 
        type=str, 
        help='Path to PDF file to process'
    )
    
    parser.add_argument(
        '--json', 
        type=str, 
        help='Path to JSON file containing examples'
    )
    
    parser.add_argument(
        '--type', 
        choices=['specification', 'examples'], 
        help='Type of content to upload'
    )
    
    parser.add_argument(
        '--version', 
        type=str, 
        default='2024.1', 
        help='Version tag for specifications'
    )
    
    parser.add_argument(
        '--quality-threshold', 
        type=float, 
        default=0.7, 
        help='Minimum quality score for examples (0.0-1.0)'
    )
    
    parser.add_argument(
        '--validate-content', 
        action='store_true', 
        help='Validate existing content in S3'
    )
    
    parser.add_argument(
        '--create-template', 
        action='store_true', 
        help='Create example template JSON file'
    )
    
    parser.add_argument(
        '--environment', 
        type=str, 
        default='dev', 
        help='Environment (dev/prod)'
    )
    
    args = parser.parse_args()
    
    # Initialize uploader
    uploader = TrainingContentUploader(args.environment)
    
    try:
        if args.create_template:
            template_path = uploader.create_example_template()
            print(f"✅ Template created: {template_path}")
            print("📝 Edit the template with your examples, then upload with:")
            print(f"   python {__file__} --json {template_path} --type examples")
            return
        
        if args.validate_content:
            result = uploader.validate_content()
            print("\n📊 Content Validation Results:")
            print(f"Status: {result.get('overall_status', 'unknown')}")
            
            if result.get('specifications_bucket', {}).get('exists'):
                spec_info = result['specifications_bucket']
                print(f"📚 Specifications: {spec_info['file_count']} files")
                print(f"   Domains: {', '.join(spec_info['domains_found'])}")
                if spec_info['missing_domains']:
                    print(f"   ⚠️  Missing: {', '.join(spec_info['missing_domains'])}")
            
            if result.get('examples_bucket', {}).get('exists'):
                examples_info = result['examples_bucket']
                print(f"📝 Examples: {examples_info['file_count']} files")
            
            if result.get('recommendations'):
                print("\n💡 Recommendations:")
                for rec in result['recommendations']:
                    print(f"   • {rec}")
            
            return
        
        if args.pdf and args.type:
            if args.type == 'specification':
                result = uploader.upload_specification_pdf(args.pdf, args.version)
            elif args.type == 'examples':
                result = uploader.upload_examples_pdf(args.pdf, args.quality_threshold)
            
            if result['success']:
                print(f"✅ Successfully processed {args.pdf}")
                if 'successful_uploads' in result:
                    print(f"📤 Uploaded {result['successful_uploads']}/{result.get('total_files', 0)} files")
            else:
                print(f"❌ Failed to process {args.pdf}")
                if 'error' in result:
                    print(f"Error: {result['error']}")
                if 'suggested_approach' in result:
                    print("\n💡 Suggested approach:")
                    print(f"   Method: {result['suggested_approach']['method']}")
                    print(f"   Description: {result['suggested_approach']['description']}")
            
            return
        
        if args.json and args.type == 'examples':
            result = uploader.upload_examples_json(args.json, args.quality_threshold)
            
            if result['success']:
                print(f"✅ Successfully processed {args.json}")
                print(f"📝 Quality examples: {result['quality_examples']}/{result['total_examples']}")
                print(f"📤 Uploaded {result['successful_uploads']}/{result['generated_files']} files")
            else:
                print(f"❌ Failed to process {args.json}")
                if 'error' in result:
                    print(f"Error: {result['error']}")
            
            return
        
        # Show help if no valid arguments
        parser.print_help()
        print("\n💡 Quick start:")
        print("1. Create template:     python scripts/upload_training_content.py --create-template")
        print("2. Upload examples:     python scripts/upload_training_content.py --json example_template.json --type examples")
        print("3. Upload specification: python scripts/upload_training_content.py --pdf edexcel_spec.pdf --type specification")
        print("4. Validate content:    python scripts/upload_training_content.py --validate-content")
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        print(f"❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()