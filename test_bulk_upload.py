#!/usr/bin/env python3
"""
Test Bulk PDF Upload System

This script tests the bulk upload system by creating sample content
and uploading it to expand the content library.
"""

import os
import sys
import json
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from bulk_pdf_upload_system import BulkPDFUploadSystem

def create_sample_content_files():
    """Create sample content files to test the upload system."""
    
    print("🔧 Creating sample content for missing topics...")
    
    # Create a temporary directory for sample content
    temp_dir = tempfile.mkdtemp(prefix="gcse_sample_content_")
    temp_path = Path(temp_dir)
    
    # Sample content for missing topics
    sample_content = {
        'geometry': {
            'angles': {
                'learning_objectives': [
                    'Calculate angles in triangles and quadrilaterals',
                    'Use angle properties of parallel lines',
                    'Find missing angles using angle facts',
                    'Apply angle relationships in problem solving'
                ],
                'key_concepts': ['acute', 'obtuse', 'reflex', 'parallel', 'perpendicular', 'corresponding', 'alternate'],
                'specification_content': '''Students should be able to calculate and use angles in various geometric contexts. 
                This includes understanding angle properties in triangles (angles sum to 180°), quadrilaterals (angles sum to 360°), 
                and parallel lines (corresponding angles are equal, alternate angles are equal, co-interior angles sum to 180°).
                Students should be able to find missing angles using these properties and solve multi-step angle problems.''',
                'common_misconceptions': [
                    'Confusing corresponding and alternate angles',
                    'Not recognizing when lines are parallel',
                    'Incorrectly applying angle sum properties'
                ]
            },
            'area-perimeter': {
                'learning_objectives': [
                    'Calculate area and perimeter of rectangles and triangles',
                    'Find area of compound shapes',
                    'Use area and perimeter in problem solving',
                    'Convert between different units of area'
                ],
                'key_concepts': ['area', 'perimeter', 'compound shapes', 'units', 'square units'],
                'specification_content': '''Students should be able to calculate area and perimeter of basic shapes including rectangles, 
                triangles, and compound shapes made from these. They should understand that area is measured in square units and 
                perimeter in linear units. Students should be able to break down compound shapes into simpler shapes to calculate 
                total area and apply these skills to solve real-world problems.''',
                'common_misconceptions': [
                    'Confusing area and perimeter formulas',
                    'Incorrect unit conversions',
                    'Not breaking down compound shapes correctly'
                ]
            }
        },
        'statistics': {
            'data-analysis': {
                'learning_objectives': [
                    'Calculate mean, median, mode and range',
                    'Interpret data from charts and graphs',
                    'Compare data sets using averages',
                    'Draw and interpret frequency tables'
                ],
                'key_concepts': ['mean', 'median', 'mode', 'range', 'frequency', 'average', 'data set'],
                'specification_content': '''Students should be able to calculate and interpret statistical measures including mean 
                (average), median (middle value), mode (most frequent value), and range (difference between highest and lowest values). 
                They should be able to work with data representations including bar charts, pie charts, and frequency tables. 
                Students should compare data sets using these measures and make informed conclusions.''',
                'common_misconceptions': [
                    'Confusing mean, median, and mode',
                    'Incorrect calculation of mean from frequency tables',
                    'Not ordering data before finding median'
                ]
            }
        },
        'probability': {
            'basic-probability': {
                'learning_objectives': [
                    'Calculate probability of single events',
                    'Use probability scales and language',
                    'Find probability of combined events',
                    'Use tree diagrams for probability calculations'
                ],
                'key_concepts': ['probability', 'outcome', 'event', 'likelihood', 'sample space', 'tree diagram'],
                'specification_content': '''Students should understand probability concepts and be able to calculate probabilities 
                for various scenarios. Probability is expressed as a fraction, decimal, or percentage between 0 and 1. 
                Students should be able to list all possible outcomes, calculate probability of single events, and use tree diagrams 
                to find probabilities of combined events. They should understand probability language (impossible, unlikely, even chance, likely, certain).''',
                'common_misconceptions': [
                    'Thinking probability can be greater than 1',
                    'Confusing theoretical and experimental probability',
                    'Incorrect use of tree diagrams'
                ]
            }
        },
        'ratio': {
            'ratio-proportion': {
                'learning_objectives': [
                    'Simplify ratios and find equivalent ratios',
                    'Share quantities in given ratios',
                    'Solve proportion problems',
                    'Use ratio in scale drawings and maps'
                ],
                'key_concepts': ['ratio', 'proportion', 'scale factor', 'direct proportion', 'unitary method'],
                'specification_content': '''Students should be able to work with ratios and proportions in various contexts. 
                This includes simplifying ratios to their lowest terms, sharing quantities in given ratios, and solving proportion problems. 
                Students should understand the relationship between ratios and fractions, and be able to use the unitary method to solve 
                proportion problems. They should apply these skills to real-world contexts including recipes, maps, and scale drawings.''',
                'common_misconceptions': [
                    'Not simplifying ratios to lowest terms',
                    'Confusing ratio and proportion',
                    'Incorrect application of scale factors'
                ]
            }
        }
    }
    
    # Create JSON files for each topic
    files_created = []
    
    for domain, subtopics in sample_content.items():
        domain_dir = temp_path / domain
        domain_dir.mkdir(exist_ok=True)
        
        for subtopic, content_info in subtopics.items():
            # Create content structure
            content_dict = {
                'domain': domain,
                'subtopic': subtopic,
                'tier': 'both',
                'version': '2024.2',
                'learning_objectives': content_info['learning_objectives'],
                'specification_content': content_info['specification_content'],
                'key_concepts': content_info['key_concepts'],
                'common_misconceptions': content_info['common_misconceptions'],
                'assessment_objectives': ['AO1', 'AO2'],
                'marks_range': [1, 4],
                'version_timestamp': '2024-12-28T18:00:00Z',
                'version_metadata': {
                    'source': 'sample_content_generation',
                    'processing_date': '2024-12-28T18:00:00Z',
                    'content_quality': 'enhanced'
                }
            }
            
            # Write JSON file
            json_file = domain_dir / f"{subtopic}.json"
            with open(json_file, 'w') as f:
                json.dump(content_dict, f, indent=2, ensure_ascii=False)
            
            files_created.append(json_file)
    
    print(f"   ✅ Created {len(files_created)} sample content files in {temp_dir}")
    return temp_dir, files_created


def test_bulk_upload_system():
    """Test the bulk upload system with sample content."""
    
    print("🧪 TESTING BULK PDF UPLOAD SYSTEM")
    print("="*60)
    print("Testing content upload for missing GCSE topics")
    
    # Create sample content
    temp_dir, sample_files = create_sample_content_files()
    
    try:
        # Initialize the upload system
        upload_system = BulkPDFUploadSystem(
            specifications_bucket='gcse-specifications-prod-1a64dc99',
            examples_bucket='gcse-examples-prod-1a64dc99'
        )
        
        # Create content library from sample files
        print("\n🔧 Processing sample content...")
        
        json_files = {}
        
        for sample_file in sample_files:
            with open(sample_file, 'r') as f:
                content = f.read()
            
            # Create file paths for S3
            domain = sample_file.parent.name
            subtopic = sample_file.stem
            
            base_path = f"specifications/{domain}/{subtopic}"
            json_files[f"{base_path}_latest.json"] = content
            json_files[f"{base_path}_v2024.2.json"] = content
        
        print(f"   ✅ Prepared {len(json_files)} files for upload")
        
        # Upload to S3
        print("\n📤 Uploading content to S3...")
        upload_results = upload_system.upload_content_library(json_files)
        
        # Check results
        successful_uploads = sum(1 for success in upload_results.values() if success)
        failed_uploads = len(upload_results) - successful_uploads
        
        print(f"   📊 Upload results: {successful_uploads} successful, {failed_uploads} failed")
        
        # Verify S3 structure
        print("\n🔍 Verifying S3 structure...")
        verification_results = upload_system.content_processor.verify_s3_structure(
            upload_system.specifications_bucket,
            upload_system.examples_bucket
        )
        
        specs_files = len(verification_results['specifications_bucket']['files'])
        examples_files = len(verification_results['examples_bucket']['files'])
        
        print(f"   📊 S3 verification: {specs_files} specification files, {examples_files} example files")
        
        # Generate report
        report = upload_system.generate_processing_report()
        report['test_results'] = {
            'sample_files_created': len(sample_files),
            'files_uploaded': successful_uploads,
            'upload_failures': failed_uploads,
            'verification_results': verification_results
        }
        
        # Save test report
        report_file = "bulk_upload_test_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n💾 Test report saved to: {report_file}")
        
        # Summary
        print(f"\n📋 Test Summary:")
        print(f"   Sample content files created: {len(sample_files)}")
        print(f"   Files prepared for upload: {len(json_files)}")
        print(f"   Successful uploads: {successful_uploads}")
        print(f"   Upload success rate: {(successful_uploads/len(json_files)*100):.1f}%")
        
        if successful_uploads >= len(json_files) * 0.8:  # 80% success rate
            print(f"\n🎉 Bulk upload system test: PASSED")
            return True
        else:
            print(f"\n💥 Bulk upload system test: FAILED")
            return False
            
    except Exception as e:
        print(f"\n💥 Test failed with error: {str(e)}")
        return False
    
    finally:
        # Clean up temporary directory
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
        print(f"   🧹 Cleaned up temporary files")


def main():
    """Main function to run the bulk upload test."""
    
    success = test_bulk_upload_system()
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())