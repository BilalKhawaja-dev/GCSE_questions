"""
Content Processing Service for GCSE Question Generator

This service handles:
1. PDF parsing of Edexcel specifications
2. Content organization by domain/subtopic
3. JSON file generation for S3 storage
4. Seed examples processing and validation
5. Specification version management
"""

import json
import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import pdfplumber
import boto3
from botocore.exceptions import ClientError

from models.specification_content import SpecificationContent
from models.question import Question
from models.mark_scheme import MarkScheme

logger = logging.getLogger(__name__)


@dataclass
class ProcessedContent:
    """Represents processed specification content ready for S3 storage"""
    domain: str
    subtopic: str
    tier: str
    version: str
    learning_objectives: List[str]
    specification_content: str
    key_concepts: List[str]
    common_misconceptions: List[str]
    assessment_objectives: List[str]
    marks_range: List[int]


@dataclass
class SeedExample:
    """Represents a seed example with quality scoring"""
    question: Dict[str, Any]
    mark_scheme: Dict[str, Any]
    quality_score: float
    verification_status: str


class ContentProcessingService:
    """Service for processing specification PDFs and seed examples"""
    
    # Topic mapping for organizing content
    TOPIC_MAPPING = {
        "fractions": {"domain": "number", "subtopic": "fractions"},
        "decimals": {"domain": "number", "subtopic": "decimals"},
        "percentages": {"domain": "number", "subtopic": "percentages"},
        "ratio": {"domain": "number", "subtopic": "ratio"},
        "proportion": {"domain": "number", "subtopic": "proportion"},
        "algebra": {"domain": "algebra", "subtopic": "linear-equations"},
        "quadratics": {"domain": "algebra", "subtopic": "quadratics"},
        "simultaneous": {"domain": "algebra", "subtopic": "simultaneous-equations"},
        "geometry": {"domain": "geometry", "subtopic": "angles"},
        "trigonometry": {"domain": "geometry", "subtopic": "trigonometry"},
        "pythagoras": {"domain": "geometry", "subtopic": "pythagoras"},
        "statistics": {"domain": "statistics", "subtopic": "data-analysis"},
        "probability": {"domain": "statistics", "subtopic": "probability"}
    }
    
    def __init__(self, s3_client=None):
        """Initialize the content processing service"""
        self.s3_client = s3_client or boto3.client('s3')
        
    def parse_edexcel_pdf(self, pdf_path: str) -> List[ProcessedContent]:
        """
        Extract structured content from Edexcel specification PDF.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of ProcessedContent objects organized by domain/subtopic
        """
        logger.info(f"Starting PDF parsing for: {pdf_path}")
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                sections = []
                current_section = None
                
                for page_num, page in enumerate(pdf.pages):
                    text = page.extract_text()
                    if not text:
                        continue
                        
                    # Parse section structure from page text
                    parsed_sections = self._parse_section_structure(text, page_num + 1)
                    sections.extend(parsed_sections)
                    
                logger.info(f"Successfully parsed {len(sections)} sections from PDF")
                return sections
                
        except Exception as e:
            logger.error(f"Error parsing PDF {pdf_path}: {str(e)}")
            raise
    
    def _parse_section_structure(self, text: str, page_num: int) -> List[ProcessedContent]:
        """
        Parse section structure from page text.
        
        Args:
            text: Raw text from PDF page
            page_num: Page number for logging
            
        Returns:
            List of ProcessedContent objects found on this page
        """
        sections = []
        
        # Split text into lines for processing
        lines = text.split('\n')
        current_content = []
        current_topic = None
        current_tier = "both"  # Default to both tiers
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Detect topic headers (e.g., "Number", "Algebra", etc.)
            topic_match = self._detect_topic_header(line)
            if topic_match:
                # Save previous section if exists
                if current_topic and current_content:
                    section = self._create_processed_content(
                        current_topic, current_content, current_tier, page_num
                    )
                    if section:
                        sections.append(section)
                
                current_topic = topic_match
                current_content = []
                continue
            
            # Detect tier information
            tier_match = self._detect_tier(line)
            if tier_match:
                current_tier = tier_match
                continue
                
            # Collect content lines
            if current_topic:
                current_content.append(line)
        
        # Don't forget the last section
        if current_topic and current_content:
            section = self._create_processed_content(
                current_topic, current_content, current_tier, page_num
            )
            if section:
                sections.append(section)
        
        return sections
    
    def _detect_topic_header(self, line: str) -> Optional[str]:
        """Detect if line contains a topic header"""
        # Common topic patterns in GCSE specifications
        topic_patterns = [
            r'\b(number|fractions?|decimals?|percentages?)\b',
            r'\b(algebra|equations?|quadratics?)\b',
            r'\b(geometry|angles?|trigonometry|pythagoras)\b',
            r'\b(statistics?|probability|data)\b'
        ]
        
        line_lower = line.lower()
        for pattern in topic_patterns:
            if re.search(pattern, line_lower):
                # Extract the main topic
                if 'number' in line_lower or 'fraction' in line_lower or 'decimal' in line_lower:
                    return 'number'
                elif 'algebra' in line_lower or 'equation' in line_lower:
                    return 'algebra'
                elif 'geometry' in line_lower or 'angle' in line_lower or 'trigonometry' in line_lower:
                    return 'geometry'
                elif 'statistic' in line_lower or 'probability' in line_lower or 'data' in line_lower:
                    return 'statistics'
        
        return None
    
    def _detect_tier(self, line: str) -> Optional[str]:
        """Detect tier information from line"""
        line_lower = line.lower()
        if 'foundation' in line_lower and 'higher' not in line_lower:
            return 'Foundation'
        elif 'higher' in line_lower and 'foundation' not in line_lower:
            return 'Higher'
        elif 'foundation' in line_lower and 'higher' in line_lower:
            return 'both'
        return None
    
    def _create_processed_content(
        self, 
        topic: str, 
        content_lines: List[str], 
        tier: str, 
        page_num: int
    ) -> Optional[ProcessedContent]:
        """Create ProcessedContent object from parsed information"""
        
        if not content_lines:
            return None
            
        # Join content lines
        content_text = ' '.join(content_lines)
        
        # Extract learning objectives
        learning_objectives = self._extract_learning_objectives(content_lines)
        
        # Extract key concepts
        key_concepts = self._extract_key_concepts(content_lines, topic)
        
        # Extract common misconceptions
        misconceptions = self._extract_misconceptions(content_lines)
        
        # Determine subtopic based on content
        subtopic = self._determine_subtopic(topic, content_text)
        
        # Get domain from topic mapping
        domain_info = self.TOPIC_MAPPING.get(subtopic, {"domain": topic, "subtopic": subtopic})
        
        return ProcessedContent(
            domain=domain_info["domain"],
            subtopic=subtopic,
            tier=tier,
            version="2024.1",  # Default version
            learning_objectives=learning_objectives,
            specification_content=content_text,
            key_concepts=key_concepts,
            common_misconceptions=misconceptions,
            assessment_objectives=["AO1", "AO2"],  # Default assessment objectives
            marks_range=[1, 4]  # Default marks range
        )
    
    def _extract_learning_objectives(self, content_lines: List[str]) -> List[str]:
        """Extract learning objectives from content"""
        objectives = []
        
        for line in content_lines:
            # Look for lines that start with action verbs or "Students should"
            line_lower = line.lower().strip()
            if (line_lower.startswith(('calculate', 'solve', 'find', 'determine', 'work out', 'students should')) or
                'able to' in line_lower):
                objectives.append(line.strip())
        
        return objectives[:5]  # Limit to 5 objectives
    
    def _extract_key_concepts(self, content_lines: List[str], topic: str) -> List[str]:
        """Extract key concepts based on topic"""
        concept_mapping = {
            'number': ['numerator', 'denominator', 'equivalent', 'simplification', 'decimal places'],
            'algebra': ['variable', 'coefficient', 'equation', 'expression', 'substitution'],
            'geometry': ['angle', 'parallel', 'perpendicular', 'congruent', 'similar'],
            'statistics': ['mean', 'median', 'mode', 'range', 'frequency']
        }
        
        return concept_mapping.get(topic, ['concept1', 'concept2', 'concept3'])
    
    def _extract_misconceptions(self, content_lines: List[str]) -> List[str]:
        """Extract common misconceptions from content"""
        misconceptions = []
        
        for line in content_lines:
            line_lower = line.lower()
            if any(word in line_lower for word in ['common error', 'mistake', 'misconception', 'confusion']):
                misconceptions.append(line.strip())
        
        # Default misconceptions if none found
        if not misconceptions:
            misconceptions = ["Common calculation errors", "Misunderstanding of key concepts"]
        
        return misconceptions
    
    def _determine_subtopic(self, topic: str, content: str) -> str:
        """Determine subtopic based on content analysis"""
        content_lower = content.lower()
        
        if topic == 'number':
            if 'fraction' in content_lower:
                return 'fractions'
            elif 'decimal' in content_lower:
                return 'decimals'
            elif 'percentage' in content_lower:
                return 'percentages'
            elif 'ratio' in content_lower:
                return 'ratio'
            else:
                return 'number'
        elif topic == 'algebra':
            if 'quadratic' in content_lower:
                return 'quadratics'
            elif 'simultaneous' in content_lower:
                return 'simultaneous'
            else:
                return 'algebra'
        elif topic == 'geometry':
            if 'trigonometry' in content_lower:
                return 'trigonometry'
            elif 'pythagoras' in content_lower:
                return 'pythagoras'
            else:
                return 'geometry'
        elif topic == 'statistics':
            if 'probability' in content_lower:
                return 'probability'
            else:
                return 'statistics'
        
        return topic
    
    def organize_content_by_domain(self, processed_content: List[ProcessedContent]) -> Dict[str, Dict[str, ProcessedContent]]:
        """
        Organize processed content by domain and subtopic.
        
        Args:
            processed_content: List of ProcessedContent objects
            
        Returns:
            Dictionary organized as {domain: {subtopic: ProcessedContent}}
        """
        organized = {}
        
        for content in processed_content:
            if content.domain not in organized:
                organized[content.domain] = {}
            
            organized[content.domain][content.subtopic] = content
        
        logger.info(f"Organized content into {len(organized)} domains")
        return organized
    
    def generate_json_files(self, organized_content: Dict[str, Dict[str, ProcessedContent]]) -> Dict[str, str]:
        """
        Generate JSON files for S3 storage.
        
        Args:
            organized_content: Content organized by domain/subtopic
            
        Returns:
            Dictionary mapping file paths to JSON content
        """
        json_files = {}
        
        for domain, subtopics in organized_content.items():
            for subtopic, content in subtopics.items():
                # Create file path
                file_path = f"specifications/{domain}/{subtopic}.json"
                
                # Convert to dictionary for JSON serialization
                content_dict = asdict(content)
                
                # Generate JSON content
                json_content = json.dumps(content_dict, indent=2, ensure_ascii=False)
                json_files[file_path] = json_content
        
        logger.info(f"Generated {len(json_files)} JSON files")
        return json_files
    def process_seed_examples(self, examples_data: List[Dict[str, Any]]) -> Dict[str, List[SeedExample]]:
        """
        Process and validate seed examples.
        
        Args:
            examples_data: List of raw example data
            
        Returns:
            Dictionary organized by domain/subtopic containing validated examples
        """
        logger.info(f"Processing {len(examples_data)} seed examples")
        
        organized_examples = {}
        
        for example_data in examples_data:
            try:
                # Validate and process the example
                processed_example = self._process_single_example(example_data)
                if processed_example:
                    # Organize by domain
                    domain = self._determine_example_domain(processed_example)
                    subtopic = self._determine_example_subtopic(processed_example)
                    
                    key = f"{domain}/{subtopic}"
                    if key not in organized_examples:
                        organized_examples[key] = []
                    
                    organized_examples[key].append(processed_example)
                    
            except Exception as e:
                logger.warning(f"Failed to process example: {str(e)}")
                continue
        
        logger.info(f"Successfully processed examples for {len(organized_examples)} topics")
        return organized_examples
    
    def _process_single_example(self, example_data: Dict[str, Any]) -> Optional[SeedExample]:
        """Process a single seed example with validation"""
        
        # Extract question data
        question_data = example_data.get('question', {})
        mark_scheme_data = example_data.get('mark_scheme', {})
        
        if not question_data or not mark_scheme_data:
            logger.warning("Example missing question or mark scheme data")
            return None
        
        # Validate required fields
        required_question_fields = ['question_text', 'marks', 'tier', 'topic']
        required_mark_scheme_fields = ['marking_criteria']
        
        if not all(field in question_data for field in required_question_fields):
            logger.warning("Question data missing required fields")
            return None
            
        if not all(field in mark_scheme_data for field in required_mark_scheme_fields):
            logger.warning("Mark scheme data missing required fields")
            return None
        
        # Calculate quality score
        quality_score = self._calculate_quality_score(question_data, mark_scheme_data)
        
        # Create seed example
        seed_example = SeedExample(
            question=question_data,
            mark_scheme=mark_scheme_data,
            quality_score=quality_score,
            verification_status="processed"  # Default status
        )
        
        return seed_example
    
    def _calculate_quality_score(self, question_data: Dict[str, Any], mark_scheme_data: Dict[str, Any]) -> float:
        """Calculate quality score for a seed example (0.0-1.0)"""
        score = 1.0
        
        # Check question text quality
        question_text = question_data.get('question_text', '')
        if len(question_text) < 10:
            score -= 0.3
        if not question_text.endswith(('?', '.')):
            score -= 0.1
        
        # Check marks alignment
        question_marks = question_data.get('marks', 0)
        if question_marks <= 0:
            score -= 0.4
        
        # Check mark scheme quality
        marking_criteria = mark_scheme_data.get('marking_criteria', '')
        if len(marking_criteria) < 20:
            score -= 0.2
        
        # Check for mathematical content (basic heuristic)
        if any(char in question_text for char in '+-×÷=<>()[]{}'):
            score += 0.1  # Bonus for mathematical content
        
        return max(0.0, min(1.0, score))
    
    def _determine_example_domain(self, example: SeedExample) -> str:
        """Determine domain for an example based on topic"""
        topic = example.question.get('topic', '').lower()
        
        if any(word in topic for word in ['number', 'fraction', 'decimal', 'percentage']):
            return 'number'
        elif any(word in topic for word in ['algebra', 'equation', 'quadratic']):
            return 'algebra'
        elif any(word in topic for word in ['geometry', 'angle', 'trigonometry']):
            return 'geometry'
        elif any(word in topic for word in ['statistics', 'probability', 'data']):
            return 'statistics'
        
        return 'general'
    
    def _determine_example_subtopic(self, example: SeedExample) -> str:
        """Determine subtopic for an example"""
        topic = example.question.get('topic', '').lower()
        question_text = example.question.get('question_text', '').lower()
        
        # Use content analysis to determine subtopic
        combined_text = f"{topic} {question_text}"
        
        for subtopic_key, mapping in self.TOPIC_MAPPING.items():
            if subtopic_key in combined_text:
                return mapping['subtopic']
        
        # Default based on domain
        domain = self._determine_example_domain(example)
        return f"{domain}-general"
    
    def generate_examples_json(self, organized_examples: Dict[str, List[SeedExample]]) -> Dict[str, str]:
        """
        Generate JSON files for seed examples.
        
        Args:
            organized_examples: Examples organized by domain/subtopic
            
        Returns:
            Dictionary mapping file paths to JSON content
        """
        json_files = {}
        
        for domain_subtopic, examples in organized_examples.items():
            domain, subtopic = domain_subtopic.split('/', 1)
            
            # Create file path
            file_path = f"examples/{domain}/{subtopic}.json"
            
            # Create examples structure
            examples_structure = {
                "domain": domain,
                "subtopic": subtopic,
                "examples": [
                    {
                        "question": example.question,
                        "mark_scheme": example.mark_scheme,
                        "quality_score": example.quality_score,
                        "verification_status": example.verification_status
                    }
                    for example in examples
                ]
            }
            
            # Generate JSON content
            json_content = json.dumps(examples_structure, indent=2, ensure_ascii=False)
            json_files[file_path] = json_content
        
        logger.info(f"Generated {len(json_files)} example JSON files")
        return json_files
    
    def add_version_tagging(self, json_content: str, version: str) -> str:
        """
        Add version tagging to specification JSON files.
        
        Args:
            json_content: Original JSON content
            version: Version string to add
            
        Returns:
            Updated JSON content with version tag
        """
        try:
            data = json.loads(json_content)
            data['version'] = version
            data['version_timestamp'] = self._get_current_timestamp()
            
            return json.dumps(data, indent=2, ensure_ascii=False)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON for version tagging: {str(e)}")
            raise
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime
        return datetime.utcnow().isoformat() + 'Z'
    
    def upload_to_s3(
        self, 
        json_files: Dict[str, str], 
        specifications_bucket: str, 
        examples_bucket: Optional[str] = None
    ) -> Dict[str, bool]:
        """
        Upload processed JSON files to S3.
        
        Args:
            json_files: Dictionary mapping file paths to JSON content
            specifications_bucket: S3 bucket for specifications
            examples_bucket: S3 bucket for examples (optional)
            
        Returns:
            Dictionary mapping file paths to upload success status
        """
        upload_results = {}
        
        for file_path, json_content in json_files.items():
            try:
                # Determine target bucket
                if file_path.startswith('specifications/'):
                    bucket = specifications_bucket
                elif file_path.startswith('examples/') and examples_bucket:
                    bucket = examples_bucket
                else:
                    logger.warning(f"No bucket specified for file path: {file_path}")
                    upload_results[file_path] = False
                    continue
                
                # Upload to S3
                self.s3_client.put_object(
                    Bucket=bucket,
                    Key=file_path,
                    Body=json_content.encode('utf-8'),
                    ContentType='application/json',
                    ServerSideEncryption='AES256'
                )
                
                upload_results[file_path] = True
                logger.info(f"Successfully uploaded {file_path} to {bucket}")
                
            except ClientError as e:
                logger.error(f"Failed to upload {file_path}: {str(e)}")
                upload_results[file_path] = False
            except Exception as e:
                logger.error(f"Unexpected error uploading {file_path}: {str(e)}")
                upload_results[file_path] = False
        
        successful_uploads = sum(1 for success in upload_results.values() if success)
        logger.info(f"Upload completed: {successful_uploads}/{len(json_files)} files successful")
        
        return upload_results
    
    def verify_s3_structure(self, specifications_bucket: str, examples_bucket: Optional[str] = None) -> Dict[str, Any]:
        """
        Verify S3 bucket structure and file organization.
        
        Args:
            specifications_bucket: S3 bucket for specifications
            examples_bucket: S3 bucket for examples (optional)
            
        Returns:
            Dictionary containing verification results
        """
        verification_results = {
            'specifications_bucket': {'exists': False, 'files': []},
            'examples_bucket': {'exists': False, 'files': []},
            'structure_valid': False
        }
        
        # Check specifications bucket
        try:
            response = self.s3_client.list_objects_v2(Bucket=specifications_bucket)
            verification_results['specifications_bucket']['exists'] = True
            
            if 'Contents' in response:
                files = [obj['Key'] for obj in response['Contents']]
                verification_results['specifications_bucket']['files'] = files
                logger.info(f"Found {len(files)} files in specifications bucket")
            
        except ClientError as e:
            logger.error(f"Error accessing specifications bucket: {str(e)}")
        
        # Check examples bucket if provided
        if examples_bucket:
            try:
                response = self.s3_client.list_objects_v2(Bucket=examples_bucket)
                verification_results['examples_bucket']['exists'] = True
                
                if 'Contents' in response:
                    files = [obj['Key'] for obj in response['Contents']]
                    verification_results['examples_bucket']['files'] = files
                    logger.info(f"Found {len(files)} files in examples bucket")
                
            except ClientError as e:
                logger.error(f"Error accessing examples bucket: {str(e)}")
        
        # Validate structure
        spec_files = verification_results['specifications_bucket']['files']
        examples_files = verification_results['examples_bucket']['files']
        
        # Check for expected directory structure
        has_spec_structure = any(file.startswith('specifications/') for file in spec_files)
        has_examples_structure = any(file.startswith('examples/') for file in examples_files) if examples_bucket else True
        
        verification_results['structure_valid'] = has_spec_structure and has_examples_structure
        
        return verification_results