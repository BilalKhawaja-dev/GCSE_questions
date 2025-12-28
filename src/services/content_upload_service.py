"""
Content Upload Service for GCSE Question Generator

This service handles:
1. Uploading specification JSON files to S3 specifications bucket
2. Uploading seed examples JSON files to S3 examples bucket
3. Verifying S3 bucket structure and file organization
4. Testing content retrieval from GenerateLambda
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
import boto3
from botocore.exceptions import ClientError
from pathlib import Path

from src.services.content_processing_service import ContentProcessingService
from src.services.seed_examples_processor import SeedExamplesProcessor
from src.services.version_management_service import VersionManagementService
from src.services.content_retrieval_service import ContentRetrievalService

logger = logging.getLogger(__name__)


class ContentUploadService:
    """Service for uploading and managing content in S3 buckets"""
    
    def __init__(self, specifications_bucket: str, examples_bucket: str, region: str = 'eu-west-2'):
        """Initialize the content upload service"""
        self.specifications_bucket = specifications_bucket
        self.examples_bucket = examples_bucket
        self.region = region
        self.s3_client = boto3.client('s3', region_name=region)
        
        # Initialize related services
        self.content_processor = ContentProcessingService(self.s3_client)
        self.examples_processor = SeedExamplesProcessor()
        self.version_service = VersionManagementService(self.s3_client)
        self.retrieval_service = ContentRetrievalService(
            specifications_bucket, examples_bucket, region
        )
    
    def upload_specification_files(
        self, 
        json_files: Dict[str, str], 
        version: str = "2024.1"
    ) -> Dict[str, bool]:
        """
        Upload specification JSON files to S3 specifications bucket.
        
        Args:
            json_files: Dictionary mapping file paths to JSON content
            version: Version string for the specifications
            
        Returns:
            Dictionary mapping file paths to upload success status
        """
        logger.info(f"Starting upload of {len(json_files)} specification files")
        
        upload_results = {}
        
        for file_path, json_content in json_files.items():
            if not file_path.startswith('specifications/'):
                logger.warning(f"Skipping non-specification file: {file_path}")
                upload_results[file_path] = False
                continue
            
            try:
                # Parse JSON content to add version information
                content_dict = json.loads(json_content)
                
                # Upload versioned content
                success = self.version_service.upload_versioned_content(
                    bucket=self.specifications_bucket,
                    base_path=file_path,
                    content=content_dict,
                    version=version,
                    set_as_latest=True
                )
                
                upload_results[file_path] = success
                
                if success:
                    logger.info(f"Successfully uploaded specification: {file_path} (version {version})")
                else:
                    logger.error(f"Failed to upload specification: {file_path}")
                    
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in file {file_path}: {str(e)}")
                upload_results[file_path] = False
            except Exception as e:
                logger.error(f"Error uploading {file_path}: {str(e)}")
                upload_results[file_path] = False
        
        successful_uploads = sum(1 for success in upload_results.values() if success)
        logger.info(f"Specification upload completed: {successful_uploads}/{len(json_files)} successful")
        
        return upload_results
    
    def upload_examples_files(self, json_files: Dict[str, str]) -> Dict[str, bool]:
        """
        Upload seed examples JSON files to S3 examples bucket.
        
        Args:
            json_files: Dictionary mapping file paths to JSON content
            
        Returns:
            Dictionary mapping file paths to upload success status
        """
        logger.info(f"Starting upload of {len(json_files)} examples files")
        
        upload_results = {}
        
        for file_path, json_content in json_files.items():
            if not file_path.startswith('examples/'):
                logger.warning(f"Skipping non-examples file: {file_path}")
                upload_results[file_path] = False
                continue
            
            try:
                # Upload to S3
                self.s3_client.put_object(
                    Bucket=self.examples_bucket,
                    Key=file_path,
                    Body=json_content.encode('utf-8'),
                    ContentType='application/json',
                    ServerSideEncryption='AES256'
                )
                
                upload_results[file_path] = True
                logger.info(f"Successfully uploaded examples: {file_path}")
                
            except ClientError as e:
                logger.error(f"Failed to upload examples {file_path}: {str(e)}")
                upload_results[file_path] = False
            except Exception as e:
                logger.error(f"Unexpected error uploading {file_path}: {str(e)}")
                upload_results[file_path] = False
        
        successful_uploads = sum(1 for success in upload_results.values() if success)
        logger.info(f"Examples upload completed: {successful_uploads}/{len(json_files)} successful")
        
        return upload_results
    
    def verify_bucket_structure(self) -> Dict[str, Any]:
        """
        Verify S3 bucket structure and file organization.
        
        Returns:
            Dictionary containing verification results
        """
        logger.info("Starting S3 bucket structure verification")
        
        verification_results = {
            'specifications_bucket': {
                'exists': False,
                'accessible': False,
                'files': [],
                'structure_valid': False,
                'versions_found': {}
            },
            'examples_bucket': {
                'exists': False,
                'accessible': False,
                'files': [],
                'structure_valid': False
            },
            'overall_valid': False,
            'errors': []
        }
        
        # Verify specifications bucket
        try:
            # Check bucket existence and accessibility
            self.s3_client.head_bucket(Bucket=self.specifications_bucket)
            verification_results['specifications_bucket']['exists'] = True
            verification_results['specifications_bucket']['accessible'] = True
            
            # List objects in specifications bucket
            response = self.s3_client.list_objects_v2(Bucket=self.specifications_bucket)
            
            if 'Contents' in response:
                files = [obj['Key'] for obj in response['Contents']]
                verification_results['specifications_bucket']['files'] = files
                
                # Check structure (should have specifications/ prefix)
                spec_files = [f for f in files if f.startswith('specifications/')]
                verification_results['specifications_bucket']['structure_valid'] = len(spec_files) > 0
                
                # Check for versions
                versions_info = self.version_service.list_all_versions(self.specifications_bucket)
                verification_results['specifications_bucket']['versions_found'] = {
                    path: len(versions) for path, versions in versions_info.items()
                }
                
                logger.info(f"Found {len(files)} files in specifications bucket, {len(spec_files)} with correct structure")
            
        except ClientError as e:
            error_msg = f"Error accessing specifications bucket: {str(e)}"
            verification_results['errors'].append(error_msg)
            logger.error(error_msg)
        
        # Verify examples bucket
        try:
            # Check bucket existence and accessibility
            self.s3_client.head_bucket(Bucket=self.examples_bucket)
            verification_results['examples_bucket']['exists'] = True
            verification_results['examples_bucket']['accessible'] = True
            
            # List objects in examples bucket
            response = self.s3_client.list_objects_v2(Bucket=self.examples_bucket)
            
            if 'Contents' in response:
                files = [obj['Key'] for obj in response['Contents']]
                verification_results['examples_bucket']['files'] = files
                
                # Check structure (should have examples/ prefix)
                example_files = [f for f in files if f.startswith('examples/')]
                verification_results['examples_bucket']['structure_valid'] = len(example_files) > 0
                
                logger.info(f"Found {len(files)} files in examples bucket, {len(example_files)} with correct structure")
            
        except ClientError as e:
            error_msg = f"Error accessing examples bucket: {str(e)}"
            verification_results['errors'].append(error_msg)
            logger.error(error_msg)
        
        # Overall validation
        verification_results['overall_valid'] = (
            verification_results['specifications_bucket']['structure_valid'] and
            verification_results['examples_bucket']['structure_valid'] and
            len(verification_results['errors']) == 0
        )
        
        logger.info(f"Bucket structure verification completed. Overall valid: {verification_results['overall_valid']}")
        
        return verification_results
    
    def test_content_retrieval(self, test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Test content retrieval from GenerateLambda perspective.
        
        Args:
            test_cases: List of test cases with topic, subtopic, tier
            
        Returns:
            Dictionary containing test results
        """
        logger.info(f"Starting content retrieval testing with {len(test_cases)} test cases")
        
        test_results = {
            'total_tests': len(test_cases),
            'successful_tests': 0,
            'failed_tests': 0,
            'test_details': [],
            'errors': []
        }
        
        for i, test_case in enumerate(test_cases):
            test_id = f"test_{i+1}"
            topic = test_case.get('topic')
            subtopic = test_case.get('subtopic')
            tier = test_case.get('tier', 'both')
            version = test_case.get('version', 'latest')
            
            test_detail = {
                'test_id': test_id,
                'topic': topic,
                'subtopic': subtopic,
                'tier': tier,
                'version': version,
                'specification_retrieved': False,
                'examples_retrieved': False,
                'success': False,
                'error': None
            }
            
            try:
                # Test specification retrieval
                spec_content = self.retrieval_service.get_specification_content_versioned(
                    topic=topic,
                    subtopic=subtopic,
                    tier=tier,
                    version=version,
                    request_id=test_id
                )
                
                if spec_content:
                    test_detail['specification_retrieved'] = True
                    logger.info(f"Test {test_id}: Successfully retrieved specification content")
                
                # Test examples retrieval
                examples_content = self.retrieval_service.get_examples_content(
                    topic=topic,
                    subtopic=subtopic,
                    tier=tier,
                    request_id=test_id
                )
                
                if examples_content is not None:  # Can be empty list
                    test_detail['examples_retrieved'] = True
                    logger.info(f"Test {test_id}: Successfully retrieved examples content ({len(examples_content)} examples)")
                
                # Test is successful if at least specification was retrieved
                test_detail['success'] = test_detail['specification_retrieved']
                
                if test_detail['success']:
                    test_results['successful_tests'] += 1
                else:
                    test_results['failed_tests'] += 1
                
            except Exception as e:
                test_detail['error'] = str(e)
                test_detail['success'] = False
                test_results['failed_tests'] += 1
                logger.error(f"Test {test_id} failed: {str(e)}")
            
            test_results['test_details'].append(test_detail)
        
        logger.info(f"Content retrieval testing completed: {test_results['successful_tests']}/{test_results['total_tests']} successful")
        
        return test_results
    
    def create_sample_content(self) -> Tuple[Dict[str, str], Dict[str, str]]:
        """
        Create sample specification and examples content for testing.
        
        Returns:
            Tuple of (specification_files, examples_files) dictionaries
        """
        logger.info("Creating sample content for testing")
        
        # Sample specification content
        sample_specifications = {
            "specifications/number/fractions.json": json.dumps({
                "domain": "number",
                "subtopic": "fractions",
                "tier": "both",
                "version": "2024.1",
                "learning_objectives": [
                    "Add and subtract fractions with same denominator",
                    "Convert between mixed numbers and improper fractions",
                    "Multiply and divide fractions"
                ],
                "specification_content": "Students should be able to work confidently with fractions, including adding, subtracting, multiplying and dividing fractions. They should understand the relationship between fractions, decimals and percentages.",
                "key_concepts": ["numerator", "denominator", "equivalent fractions", "simplification"],
                "common_misconceptions": [
                    "Adding denominators when adding fractions",
                    "Confusion between mixed numbers and improper fractions"
                ],
                "assessment_objectives": ["AO1", "AO2"],
                "marks_range": [1, 4]
            }, indent=2),
            
            "specifications/algebra/linear-equations.json": json.dumps({
                "domain": "algebra",
                "subtopic": "linear-equations",
                "tier": "both",
                "version": "2024.1",
                "learning_objectives": [
                    "Solve linear equations with one unknown",
                    "Rearrange formulae to change the subject",
                    "Set up and solve equations from word problems"
                ],
                "specification_content": "Students should be able to solve linear equations in one unknown, including those with brackets and fractions. They should be able to rearrange formulae and set up equations from contextual problems.",
                "key_concepts": ["variable", "coefficient", "equation", "solution", "substitution"],
                "common_misconceptions": [
                    "Not applying operations to both sides of equation",
                    "Sign errors when moving terms across equals sign"
                ],
                "assessment_objectives": ["AO1", "AO2", "AO3"],
                "marks_range": [2, 6]
            }, indent=2)
        }
        
        # Sample examples content
        sample_examples = {
            "examples/number/fractions.json": json.dumps({
                "domain": "number",
                "subtopic": "fractions",
                "total_examples": 2,
                "average_quality_score": 0.9,
                "examples": [
                    {
                        "question": {
                            "id": "frac_001",
                            "question_text": "Calculate 3/4 + 1/8. Show your working.",
                            "marks": 2,
                            "tier": "Foundation",
                            "topic": "Fractions"
                        },
                        "mark_scheme": {
                            "question_id": "frac_001",
                            "marking_criteria": "M1: Convert to common denominator (6/8 + 1/8), A1: Correct answer 7/8",
                            "method_marks": 1,
                            "accuracy_marks": 1,
                            "total_marks": 2
                        },
                        "quality_score": 0.95,
                        "verification_status": "verified"
                    },
                    {
                        "question": {
                            "id": "frac_002",
                            "question_text": "Convert 2 3/5 to an improper fraction.",
                            "marks": 1,
                            "tier": "Foundation",
                            "topic": "Fractions"
                        },
                        "mark_scheme": {
                            "question_id": "frac_002",
                            "marking_criteria": "A1: Correct answer 13/5",
                            "method_marks": 0,
                            "accuracy_marks": 1,
                            "total_marks": 1
                        },
                        "quality_score": 0.85,
                        "verification_status": "verified"
                    }
                ]
            }, indent=2),
            
            "examples/algebra/linear-equations.json": json.dumps({
                "domain": "algebra",
                "subtopic": "linear-equations",
                "total_examples": 1,
                "average_quality_score": 0.92,
                "examples": [
                    {
                        "question": {
                            "id": "alg_001",
                            "question_text": "Solve the equation 3x + 7 = 22",
                            "marks": 2,
                            "tier": "Foundation",
                            "topic": "Algebra"
                        },
                        "mark_scheme": {
                            "question_id": "alg_001",
                            "marking_criteria": "M1: Subtract 7 from both sides (3x = 15), A1: Divide by 3 (x = 5)",
                            "method_marks": 1,
                            "accuracy_marks": 1,
                            "total_marks": 2
                        },
                        "quality_score": 0.92,
                        "verification_status": "verified"
                    }
                ]
            }, indent=2)
        }
        
        logger.info(f"Created {len(sample_specifications)} specification files and {len(sample_examples)} examples files")
        
        return sample_specifications, sample_examples
    
    def run_full_upload_and_test(self, version: str = "2024.1") -> Dict[str, Any]:
        """
        Run full upload and testing workflow.
        
        Args:
            version: Version string for specifications
            
        Returns:
            Dictionary containing complete results
        """
        logger.info("Starting full upload and test workflow")
        
        results = {
            'sample_content_created': False,
            'specifications_uploaded': False,
            'examples_uploaded': False,
            'bucket_structure_valid': False,
            'content_retrieval_working': False,
            'upload_results': {},
            'verification_results': {},
            'test_results': {},
            'errors': []
        }
        
        try:
            # Step 1: Create sample content
            spec_files, example_files = self.create_sample_content()
            results['sample_content_created'] = True
            logger.info("Sample content created successfully")
            
            # Step 2: Upload specifications
            spec_upload_results = self.upload_specification_files(spec_files, version)
            results['upload_results']['specifications'] = spec_upload_results
            results['specifications_uploaded'] = all(spec_upload_results.values())
            
            # Step 3: Upload examples
            example_upload_results = self.upload_examples_files(example_files)
            results['upload_results']['examples'] = example_upload_results
            results['examples_uploaded'] = all(example_upload_results.values())
            
            # Step 4: Verify bucket structure
            verification_results = self.verify_bucket_structure()
            results['verification_results'] = verification_results
            results['bucket_structure_valid'] = verification_results['overall_valid']
            
            # Step 5: Test content retrieval
            test_cases = [
                {'topic': 'Number', 'subtopic': 'fractions', 'tier': 'Foundation', 'version': version},
                {'topic': 'Number', 'subtopic': 'fractions', 'tier': 'both', 'version': 'latest'},
                {'topic': 'Algebra', 'subtopic': 'linear_equations', 'tier': 'Foundation', 'version': version}
            ]
            
            test_results = self.test_content_retrieval(test_cases)
            results['test_results'] = test_results
            results['content_retrieval_working'] = test_results['successful_tests'] == test_results['total_tests']
            
            logger.info("Full upload and test workflow completed successfully")
            
        except Exception as e:
            error_msg = f"Error in full upload and test workflow: {str(e)}"
            results['errors'].append(error_msg)
            logger.error(error_msg)
        
        return results