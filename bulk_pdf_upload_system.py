#!/usr/bin/env python3
"""
Bulk PDF Content Upload System

This script creates a comprehensive system for processing and uploading
~50 GCSE PDF papers to expand the content library for better question generation.
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import boto3
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import with absolute paths
import sys
import os
sys.path.append(os.path.dirname(__file__))

from src.services.content_processing_service import ContentProcessingService, ProcessedContent
from src.services.content_upload_service import ContentUploadService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
DEFAULT_SPECIFICATIONS_BUCKET = 'gcse-specifications-prod-1a64dc99'
DEFAULT_EXAMPLES_BUCKET = 'gcse-examples-prod-1a64dc99'
AWS_REGION = 'eu-west-2'

class BulkPDFUploadSystem:
    """System for bulk processing and uploading GCSE PDF content."""
    
    def __init__(self, specifications_bucket: str, examples_bucket: str, aws_region: str = AWS_REGION):
        """Initialize the bulk upload system."""
        self.specifications_bucket = specifications_bucket
        self.examples_bucket = examples_bucket
        self.aws_region = aws_region
        
        # Initialize AWS clients
        self.s3_client = boto3.client('s3', region_name=aws_region)
        
        # Initialize services
        self.content_processor = ContentProcessingService(s3_client=self.s3_client)
        self.upload_service = ContentUploadService(
            specifications_bucket=self.specifications_bucket,
            examples_bucket=self.examples_bucket,
            region=self.aws_region
        )
        
        # Statistics tracking
        self.stats = {
            'pdfs_processed': 0,
            'pdfs_failed': 0,
            'content_sections_created': 0,
            'files_uploaded': 0,
            'upload_failures': 0,
            'processing_time': 0,
            'start_time': None
        }
    
    def discover_pdf_files(self, directory: str) -> List[Path]:
        """
        Discover all PDF files in the specified directory and subdirectories.
        
        Args:
            directory: Directory to search for PDF files
            
        Returns:
            List of Path objects for found PDF files
        """
        logger.info(f"Discovering PDF files in: {directory}")
        
        pdf_files = []
        search_path = Path(directory)
        
        if not search_path.exists():
            logger.error(f"Directory does not exist: {directory}")
            return pdf_files
        
        # Search for PDF files recursively
        for pdf_file in search_path.rglob("*.pdf"):
            if pdf_file.is_file():
                pdf_files.append(pdf_file)
        
        logger.info(f"Found {len(pdf_files)} PDF files")
        
        # Sort by name for consistent processing order
        pdf_files.sort(key=lambda x: x.name)
        
        return pdf_files
    
    def categorize_pdfs(self, pdf_files: List[Path]) -> Dict[str, List[Path]]:
        """
        Categorize PDF files by subject/topic based on filename analysis.
        
        Args:
            pdf_files: List of PDF file paths
            
        Returns:
            Dictionary categorizing PDFs by detected topic
        """
        logger.info("Categorizing PDF files by topic...")
        
        categories = {
            'mathematics': [],
            'number': [],
            'algebra': [],
            'geometry': [],
            'statistics': [],
            'probability': [],
            'mixed': [],
            'unknown': []
        }
        
        # Keywords for categorization
        category_keywords = {
            'mathematics': ['math', 'gcse', 'edexcel', 'aqa', 'ocr'],
            'number': ['number', 'fraction', 'decimal', 'percentage', 'ratio'],
            'algebra': ['algebra', 'equation', 'quadratic', 'linear', 'simultaneous'],
            'geometry': ['geometry', 'shape', 'angle', 'trigonometry', 'pythagoras'],
            'statistics': ['statistics', 'data', 'graph', 'chart', 'mean', 'median'],
            'probability': ['probability', 'chance', 'random', 'outcome'],
            'mixed': ['mixed', 'combined', 'paper', 'exam']
        }
        
        for pdf_file in pdf_files:
            filename_lower = pdf_file.name.lower()
            categorized = False
            
            # Check each category
            for category, keywords in category_keywords.items():
                if any(keyword in filename_lower for keyword in keywords):
                    categories[category].append(pdf_file)
                    categorized = True
                    break
            
            # If not categorized, put in unknown
            if not categorized:
                categories['unknown'].append(pdf_file)
        
        # Log categorization results
        for category, files in categories.items():
            if files:
                logger.info(f"  {category}: {len(files)} files")
        
        return categories
    
    def process_pdf_batch(self, pdf_files: List[Path], batch_size: int = 5) -> Dict[str, Any]:
        """
        Process a batch of PDF files in parallel.
        
        Args:
            pdf_files: List of PDF files to process
            batch_size: Number of PDFs to process concurrently
            
        Returns:
            Dictionary containing processing results
        """
        logger.info(f"Processing batch of {len(pdf_files)} PDFs with batch size {batch_size}")
        
        results = {
            'successful': [],
            'failed': [],
            'content_sections': [],
            'processing_errors': []
        }
        
        # Process PDFs in parallel batches
        with ThreadPoolExecutor(max_workers=batch_size) as executor:
            # Submit all PDF processing tasks
            future_to_pdf = {
                executor.submit(self._process_single_pdf, pdf_file): pdf_file
                for pdf_file in pdf_files
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_pdf):
                pdf_file = future_to_pdf[future]
                
                try:
                    result = future.result()
                    if result['success']:
                        results['successful'].append(pdf_file)
                        results['content_sections'].extend(result['content_sections'])
                        self.stats['pdfs_processed'] += 1
                        self.stats['content_sections_created'] += len(result['content_sections'])
                    else:
                        results['failed'].append(pdf_file)
                        results['processing_errors'].append({
                            'file': str(pdf_file),
                            'error': result['error']
                        })
                        self.stats['pdfs_failed'] += 1
                        
                except Exception as e:
                    logger.error(f"Unexpected error processing {pdf_file}: {str(e)}")
                    results['failed'].append(pdf_file)
                    results['processing_errors'].append({
                        'file': str(pdf_file),
                        'error': str(e)
                    })
                    self.stats['pdfs_failed'] += 1
        
        logger.info(f"Batch processing complete: {len(results['successful'])} successful, {len(results['failed'])} failed")
        return results
    
    def _process_single_pdf(self, pdf_file: Path) -> Dict[str, Any]:
        """
        Process a single PDF file.
        
        Args:
            pdf_file: Path to PDF file
            
        Returns:
            Dictionary containing processing result
        """
        logger.info(f"Processing PDF: {pdf_file.name}")
        
        try:
            # Parse the PDF
            content_sections = self.content_processor.parse_edexcel_pdf(str(pdf_file))
            
            if not content_sections:
                return {
                    'success': False,
                    'error': 'No content sections extracted from PDF',
                    'content_sections': []
                }
            
            logger.info(f"Successfully processed {pdf_file.name}: {len(content_sections)} sections")
            
            return {
                'success': True,
                'content_sections': content_sections,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"Error processing {pdf_file.name}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'content_sections': []
            }
    
    def organize_and_deduplicate_content(self, all_content_sections: List[ProcessedContent]) -> Dict[str, Dict[str, ProcessedContent]]:
        """
        Organize content sections and remove duplicates.
        
        Args:
            all_content_sections: List of all processed content sections
            
        Returns:
            Organized and deduplicated content
        """
        logger.info(f"Organizing and deduplicating {len(all_content_sections)} content sections...")
        
        # Use the content processor's organization method
        organized = self.content_processor.organize_content_by_domain(all_content_sections)
        
        # Deduplicate by keeping the most comprehensive content for each domain/subtopic
        deduplicated = {}
        
        for domain, subtopics in organized.items():
            deduplicated[domain] = {}
            
            for subtopic, content in subtopics.items():
                # If we already have content for this domain/subtopic, merge or keep the better one
                existing_key = f"{domain}/{subtopic}"
                
                if subtopic in deduplicated[domain]:
                    # Compare and keep the better content
                    existing_content = deduplicated[domain][subtopic]
                    better_content = self._choose_better_content(existing_content, content)
                    deduplicated[domain][subtopic] = better_content
                else:
                    deduplicated[domain][subtopic] = content
        
        total_sections = sum(len(subtopics) for subtopics in deduplicated.values())
        logger.info(f"After deduplication: {total_sections} unique content sections across {len(deduplicated)} domains")
        
        return deduplicated
    
    def _choose_better_content(self, content1: ProcessedContent, content2: ProcessedContent) -> ProcessedContent:
        """Choose the better content between two options based on quality metrics."""
        
        # Score based on content length and detail
        score1 = (
            len(content1.specification_content) +
            len(content1.learning_objectives) * 50 +
            len(content1.key_concepts) * 30 +
            len(content1.common_misconceptions) * 20
        )
        
        score2 = (
            len(content2.specification_content) +
            len(content2.learning_objectives) * 50 +
            len(content2.key_concepts) * 30 +
            len(content2.common_misconceptions) * 20
        )
        
        return content1 if score1 >= score2 else content2
    
    def generate_comprehensive_content_library(self, organized_content: Dict[str, Dict[str, ProcessedContent]]) -> Dict[str, str]:
        """
        Generate a comprehensive content library with versioning.
        
        Args:
            organized_content: Organized content by domain/subtopic
            
        Returns:
            Dictionary mapping file paths to JSON content
        """
        logger.info("Generating comprehensive content library...")
        
        json_files = {}
        current_version = "2024.2"  # New version for bulk upload
        
        for domain, subtopics in organized_content.items():
            for subtopic, content in subtopics.items():
                # Create both latest and versioned files
                base_path = f"specifications/{domain}/{subtopic}"
                
                # Convert content to dictionary
                content_dict = {
                    'domain': content.domain,
                    'subtopic': content.subtopic,
                    'tier': content.tier,
                    'version': current_version,
                    'learning_objectives': content.learning_objectives,
                    'specification_content': content.specification_content,
                    'key_concepts': content.key_concepts,
                    'common_misconceptions': content.common_misconceptions,
                    'assessment_objectives': content.assessment_objectives,
                    'marks_range': content.marks_range,
                    'version_timestamp': datetime.utcnow().isoformat() + 'Z',
                    'version_metadata': {
                        'source': 'bulk_pdf_upload',
                        'processing_date': datetime.utcnow().isoformat() + 'Z',
                        'content_quality': 'enhanced'
                    }
                }
                
                json_content = json.dumps(content_dict, indent=2, ensure_ascii=False)
                
                # Create both latest and versioned files
                json_files[f"{base_path}_latest.json"] = json_content
                json_files[f"{base_path}_v{current_version}.json"] = json_content
        
        logger.info(f"Generated {len(json_files)} JSON files for content library")
        return json_files
    
    def create_missing_topic_content(self) -> Dict[str, str]:
        """
        Create placeholder content for missing topics to ensure all 6 topics are covered.
        
        Returns:
            Dictionary mapping file paths to JSON content for missing topics
        """
        logger.info("Creating content for missing topics...")
        
        # Define all required topics
        required_topics = {
            'geometry': {
                'angles': {
                    'learning_objectives': [
                        'Calculate angles in triangles and quadrilaterals',
                        'Use angle properties of parallel lines',
                        'Find missing angles using angle facts'
                    ],
                    'key_concepts': ['acute', 'obtuse', 'reflex', 'parallel', 'perpendicular'],
                    'specification_content': 'Students should be able to calculate and use angles in various geometric contexts including triangles, quadrilaterals, and parallel lines.'
                },
                'area-perimeter': {
                    'learning_objectives': [
                        'Calculate area and perimeter of rectangles and triangles',
                        'Find area of compound shapes',
                        'Use area and perimeter in problem solving'
                    ],
                    'key_concepts': ['area', 'perimeter', 'compound shapes', 'units'],
                    'specification_content': 'Students should be able to calculate area and perimeter of basic shapes and apply these skills to solve problems.'
                }
            },
            'statistics': {
                'data-analysis': {
                    'learning_objectives': [
                        'Calculate mean, median, mode and range',
                        'Interpret data from charts and graphs',
                        'Compare data sets using averages'
                    ],
                    'key_concepts': ['mean', 'median', 'mode', 'range', 'frequency'],
                    'specification_content': 'Students should be able to calculate and interpret statistical measures and work with data representations.'
                }
            },
            'probability': {
                'basic-probability': {
                    'learning_objectives': [
                        'Calculate probability of single events',
                        'Use probability scales and language',
                        'Find probability of combined events'
                    ],
                    'key_concepts': ['probability', 'outcome', 'event', 'likelihood', 'sample space'],
                    'specification_content': 'Students should understand probability concepts and be able to calculate probabilities for various scenarios.'
                }
            },
            'ratio': {
                'ratio-proportion': {
                    'learning_objectives': [
                        'Simplify ratios and find equivalent ratios',
                        'Share quantities in given ratios',
                        'Solve proportion problems'
                    ],
                    'key_concepts': ['ratio', 'proportion', 'scale factor', 'direct proportion'],
                    'specification_content': 'Students should be able to work with ratios and proportions in various contexts.'
                }
            }
        }
        
        json_files = {}
        current_version = "2024.2"
        
        for domain, subtopics in required_topics.items():
            for subtopic, content_info in subtopics.items():
                base_path = f"specifications/{domain}/{subtopic}"
                
                content_dict = {
                    'domain': domain,
                    'subtopic': subtopic,
                    'tier': 'both',
                    'version': current_version,
                    'learning_objectives': content_info['learning_objectives'],
                    'specification_content': content_info['specification_content'],
                    'key_concepts': content_info['key_concepts'],
                    'common_misconceptions': [
                        'Common calculation errors',
                        'Misunderstanding of key concepts',
                        'Confusion with similar topics'
                    ],
                    'assessment_objectives': ['AO1', 'AO2'],
                    'marks_range': [1, 4],
                    'version_timestamp': datetime.utcnow().isoformat() + 'Z',
                    'version_metadata': {
                        'source': 'missing_topic_generation',
                        'processing_date': datetime.utcnow().isoformat() + 'Z',
                        'content_quality': 'baseline'
                    }
                }
                
                json_content = json.dumps(content_dict, indent=2, ensure_ascii=False)
                
                # Create both latest and versioned files
                json_files[f"{base_path}_latest.json"] = json_content
                json_files[f"{base_path}_v{current_version}.json"] = json_content
        
        logger.info(f"Created content for {len(json_files)} missing topic files")
        return json_files
    
    def upload_content_library(self, json_files: Dict[str, str]) -> Dict[str, bool]:
        """
        Upload the complete content library to S3.
        
        Args:
            json_files: Dictionary mapping file paths to JSON content
            
        Returns:
            Dictionary mapping file paths to upload success status
        """
        logger.info(f"Uploading {len(json_files)} files to S3...")
        
        upload_results = self.content_processor.upload_to_s3(
            json_files=json_files,
            specifications_bucket=self.specifications_bucket,
            examples_bucket=self.examples_bucket
        )
        
        # Update statistics
        successful_uploads = sum(1 for success in upload_results.values() if success)
        failed_uploads = len(upload_results) - successful_uploads
        
        self.stats['files_uploaded'] += successful_uploads
        self.stats['upload_failures'] += failed_uploads
        
        logger.info(f"Upload complete: {successful_uploads} successful, {failed_uploads} failed")
        return upload_results
    
    def generate_processing_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive processing report.
        
        Returns:
            Dictionary containing processing statistics and results
        """
        if self.stats['start_time']:
            self.stats['processing_time'] = time.time() - self.stats['start_time']
        
        report = {
            'processing_summary': {
                'total_pdfs_found': self.stats['pdfs_processed'] + self.stats['pdfs_failed'],
                'pdfs_processed_successfully': self.stats['pdfs_processed'],
                'pdfs_failed': self.stats['pdfs_failed'],
                'success_rate': (self.stats['pdfs_processed'] / (self.stats['pdfs_processed'] + self.stats['pdfs_failed'])) * 100 if (self.stats['pdfs_processed'] + self.stats['pdfs_failed']) > 0 else 0
            },
            'content_summary': {
                'content_sections_created': self.stats['content_sections_created'],
                'files_uploaded': self.stats['files_uploaded'],
                'upload_failures': self.stats['upload_failures'],
                'upload_success_rate': (self.stats['files_uploaded'] / (self.stats['files_uploaded'] + self.stats['upload_failures'])) * 100 if (self.stats['files_uploaded'] + self.stats['upload_failures']) > 0 else 0
            },
            'performance': {
                'total_processing_time_seconds': self.stats['processing_time'],
                'average_time_per_pdf': self.stats['processing_time'] / self.stats['pdfs_processed'] if self.stats['pdfs_processed'] > 0 else 0
            },
            'infrastructure': {
                'specifications_bucket': self.specifications_bucket,
                'examples_bucket': self.examples_bucket,
                'aws_region': self.aws_region
            },
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        
        return report
    
    def run_bulk_upload(self, pdf_directory: str, batch_size: int = 5, create_missing: bool = True) -> Dict[str, Any]:
        """
        Run the complete bulk PDF upload process.
        
        Args:
            pdf_directory: Directory containing PDF files
            batch_size: Number of PDFs to process concurrently
            create_missing: Whether to create content for missing topics
            
        Returns:
            Complete processing report
        """
        logger.info("Starting bulk PDF upload process...")
        self.stats['start_time'] = time.time()
        
        try:
            # Step 1: Discover PDF files
            pdf_files = self.discover_pdf_files(pdf_directory)
            if not pdf_files:
                logger.error("No PDF files found in the specified directory")
                return self.generate_processing_report()
            
            # Step 2: Categorize PDFs
            categorized_pdfs = self.categorize_pdfs(pdf_files)
            
            # Step 3: Process PDFs in batches
            all_content_sections = []
            
            for category, files in categorized_pdfs.items():
                if files:
                    logger.info(f"Processing {category} PDFs: {len(files)} files")
                    batch_results = self.process_pdf_batch(files, batch_size)
                    all_content_sections.extend(batch_results['content_sections'])
            
            # Step 4: Organize and deduplicate content
            organized_content = self.organize_and_deduplicate_content(all_content_sections)
            
            # Step 5: Generate content library
            json_files = self.generate_comprehensive_content_library(organized_content)
            
            # Step 6: Create missing topic content if requested
            if create_missing:
                missing_content = self.create_missing_topic_content()
                json_files.update(missing_content)
            
            # Step 7: Upload to S3
            upload_results = self.upload_content_library(json_files)
            
            # Step 8: Verify S3 structure
            verification_results = self.content_processor.verify_s3_structure(
                self.specifications_bucket, 
                self.examples_bucket
            )
            
            logger.info("Bulk PDF upload process completed successfully!")
            
            # Generate final report
            report = self.generate_processing_report()
            report['verification_results'] = verification_results
            report['upload_results'] = upload_results
            
            return report
            
        except Exception as e:
            logger.error(f"Bulk upload process failed: {str(e)}")
            report = self.generate_processing_report()
            report['error'] = str(e)
            return report


def main():
    """Main function for bulk PDF upload system."""
    
    parser = argparse.ArgumentParser(description='Bulk PDF Content Upload System for GCSE Question Generator')
    parser.add_argument('pdf_directory', help='Directory containing PDF files to process')
    parser.add_argument('--batch-size', type=int, default=3, help='Number of PDFs to process concurrently (default: 3)')
    parser.add_argument('--specifications-bucket', default=DEFAULT_SPECIFICATIONS_BUCKET, help='S3 bucket for specifications')
    parser.add_argument('--examples-bucket', default=DEFAULT_EXAMPLES_BUCKET, help='S3 bucket for examples')
    parser.add_argument('--aws-region', default=AWS_REGION, help='AWS region')
    parser.add_argument('--no-missing-content', action='store_true', help='Skip creating content for missing topics')
    parser.add_argument('--output-report', help='File path to save processing report (JSON)')
    
    args = parser.parse_args()
    
    # Validate PDF directory
    if not os.path.exists(args.pdf_directory):
        logger.error(f"PDF directory does not exist: {args.pdf_directory}")
        return 1
    
    # Initialize bulk upload system
    upload_system = BulkPDFUploadSystem(
        specifications_bucket=args.specifications_bucket,
        examples_bucket=args.examples_bucket,
        aws_region=args.aws_region
    )
    
    # Run bulk upload process
    report = upload_system.run_bulk_upload(
        pdf_directory=args.pdf_directory,
        batch_size=args.batch_size,
        create_missing=not args.no_missing_content
    )
    
    # Print summary
    print("\n" + "="*80)
    print("BULK PDF UPLOAD SUMMARY")
    print("="*80)
    
    if 'error' in report:
        print(f"❌ Process failed: {report['error']}")
        return 1
    
    processing = report['processing_summary']
    content = report['content_summary']
    
    print(f"📊 Processing Results:")
    print(f"   PDFs processed: {processing['pdfs_processed_successfully']}/{processing['total_pdfs_found']}")
    print(f"   Success rate: {processing['success_rate']:.1f}%")
    print(f"   Content sections: {content['content_sections_created']}")
    print(f"   Files uploaded: {content['files_uploaded']}")
    print(f"   Upload success rate: {content['upload_success_rate']:.1f}%")
    
    performance = report['performance']
    print(f"\n⏱️  Performance:")
    print(f"   Total time: {performance['total_processing_time_seconds']:.1f} seconds")
    print(f"   Average per PDF: {performance['average_time_per_pdf']:.1f} seconds")
    
    # Save report if requested
    if args.output_report:
        with open(args.output_report, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n💾 Report saved to: {args.output_report}")
    
    # Determine exit code
    if processing['success_rate'] >= 80 and content['upload_success_rate'] >= 90:
        print("\n🎉 Bulk PDF upload completed successfully!")
        return 0
    else:
        print("\n⚠️  Bulk PDF upload completed with issues - check logs for details")
        return 1


if __name__ == "__main__":
    exit(main())