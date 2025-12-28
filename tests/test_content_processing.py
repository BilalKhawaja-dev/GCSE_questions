"""
Unit tests for content processing services.

Tests cover:
1. PDF parsing accuracy
2. JSON structure validation
3. Content organization logic
4. Seed examples processing
5. Version management
6. Content upload functionality
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO
import tempfile
import os

from src.services.content_processing_service import ContentProcessingService, ProcessedContent
from src.services.seed_examples_processor import SeedExamplesProcessor, ValidatedSeedExample
from src.services.version_management_service import VersionManagementService
from src.services.content_upload_service import ContentUploadService


class TestContentProcessingService:
    """Test cases for ContentProcessingService"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_s3_client = Mock()
        self.service = ContentProcessingService(self.mock_s3_client)
    
    def test_topic_mapping_exists(self):
        """Test that topic mapping is properly defined"""
        assert hasattr(self.service, 'TOPIC_MAPPING')
        assert isinstance(self.service.TOPIC_MAPPING, dict)
        assert 'fractions' in self.service.TOPIC_MAPPING
        assert 'algebra' in self.service.TOPIC_MAPPING
    
    def test_detect_topic_header(self):
        """Test topic header detection from text lines"""
        # Test number topic detection
        assert self.service._detect_topic_header("Number and Fractions") == "number"
        assert self.service._detect_topic_header("FRACTIONS AND DECIMALS") == "number"
        
        # Test algebra topic detection
        assert self.service._detect_topic_header("Algebra and Equations") == "algebra"
        assert self.service._detect_topic_header("Linear Equations") == "algebra"
        
        # Test geometry topic detection
        assert self.service._detect_topic_header("Geometry and Angles") == "geometry"
        assert self.service._detect_topic_header("Trigonometry") == "geometry"
        
        # Test statistics topic detection
        assert self.service._detect_topic_header("Statistics and Data") == "statistics"
        assert self.service._detect_topic_header("Probability") == "statistics"
        
        # Test no match
        assert self.service._detect_topic_header("Random text") is None
    
    def test_detect_tier(self):
        """Test tier detection from text lines"""
        assert self.service._detect_tier("Foundation Tier") == "Foundation"
        assert self.service._detect_tier("Higher Tier") == "Higher"
        assert self.service._detect_tier("Foundation and Higher") == "both"
        assert self.service._detect_tier("Random text") is None
    
    def test_determine_subtopic(self):
        """Test subtopic determination from content"""
        # Test number subtopics
        assert self.service._determine_subtopic("number", "fractions and decimals") == "fractions"
        assert self.service._determine_subtopic("number", "decimal places") == "decimals"
        assert self.service._determine_subtopic("number", "percentage calculations") == "percentages"
        
        # Test algebra subtopics
        assert self.service._determine_subtopic("algebra", "quadratic equations") == "quadratics"
        assert self.service._determine_subtopic("algebra", "simultaneous equations") == "simultaneous"
        assert self.service._determine_subtopic("algebra", "linear expressions") == "algebra"
        
        # Test default case
        assert self.service._determine_subtopic("unknown", "content") == "unknown"
    
    def test_extract_learning_objectives(self):
        """Test learning objectives extraction"""
        content_lines = [
            "Students should be able to calculate fractions",
            "Calculate the sum of two fractions",
            "Random text that doesn't match",
            "Solve problems involving fractions",
            "Find the equivalent fraction"
        ]
        
        objectives = self.service._extract_learning_objectives(content_lines)
        
        assert len(objectives) <= 5  # Should limit to 5 objectives
        assert any("students should" in obj.lower() for obj in objectives)
        assert any("calculate" in obj.lower() for obj in objectives)
    
    def test_extract_key_concepts(self):
        """Test key concepts extraction by topic"""
        # Test number concepts
        concepts = self.service._extract_key_concepts([], "number")
        assert "numerator" in concepts
        assert "denominator" in concepts
        
        # Test algebra concepts
        concepts = self.service._extract_key_concepts([], "algebra")
        assert "variable" in concepts
        assert "equation" in concepts
        
        # Test unknown topic
        concepts = self.service._extract_key_concepts([], "unknown")
        assert len(concepts) == 3  # Should return default concepts
    
    def test_create_processed_content(self):
        """Test ProcessedContent object creation"""
        content_lines = [
            "Students should calculate fractions",
            "Add and subtract fractions with same denominator"
        ]
        
        processed = self.service._create_processed_content(
            topic="number",
            content_lines=content_lines,
            tier="Foundation",
            page_num=1
        )
        
        assert processed is not None
        assert processed.domain == "number"
        assert processed.tier == "Foundation"
        assert processed.version == "2024.1"
        assert len(processed.learning_objectives) > 0
        assert len(processed.key_concepts) > 0
    
    def test_organize_content_by_domain(self):
        """Test content organization by domain and subtopic"""
        processed_content = [
            ProcessedContent(
                domain="number",
                subtopic="fractions",
                tier="Foundation",
                version="2024.1",
                learning_objectives=["Test objective"],
                specification_content="Test content",
                key_concepts=["concept1"],
                common_misconceptions=["misconception1"],
                assessment_objectives=["AO1"],
                marks_range=[1, 3]
            ),
            ProcessedContent(
                domain="algebra",
                subtopic="linear-equations",
                tier="Higher",
                version="2024.1",
                learning_objectives=["Test objective 2"],
                specification_content="Test content 2",
                key_concepts=["concept2"],
                common_misconceptions=["misconception2"],
                assessment_objectives=["AO2"],
                marks_range=[2, 4]
            )
        ]
        
        organized = self.service.organize_content_by_domain(processed_content)
        
        assert "number" in organized
        assert "algebra" in organized
        assert "fractions" in organized["number"]
        assert "linear-equations" in organized["algebra"]
    
    def test_generate_json_files(self):
        """Test JSON file generation"""
        organized_content = {
            "number": {
                "fractions": ProcessedContent(
                    domain="number",
                    subtopic="fractions",
                    tier="Foundation",
                    version="2024.1",
                    learning_objectives=["Test objective"],
                    specification_content="Test content",
                    key_concepts=["concept1"],
                    common_misconceptions=["misconception1"],
                    assessment_objectives=["AO1"],
                    marks_range=[1, 3]
                )
            }
        }
        
        json_files = self.service.generate_json_files(organized_content)
        
        assert "specifications/number/fractions.json" in json_files
        
        # Validate JSON structure
        json_content = json_files["specifications/number/fractions.json"]
        parsed = json.loads(json_content)
        
        assert parsed["domain"] == "number"
        assert parsed["subtopic"] == "fractions"
        assert parsed["version"] == "2024.1"
        assert "learning_objectives" in parsed
        assert "specification_content" in parsed


class TestSeedExamplesProcessor:
    """Test cases for SeedExamplesProcessor"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.processor = SeedExamplesProcessor()
    
    def test_parse_example_question_valid(self):
        """Test parsing valid question data"""
        question_data = {
            "question_text": "Calculate 3/4 + 1/8",
            "marks": 2,
            "tier": "Foundation",
            "topic": "Fractions"
        }
        
        question = self.processor.parse_example_question(question_data)
        
        assert question is not None
        assert question.question_text == "Calculate 3/4 + 1/8"
        assert question.marks == 2
        assert question.tier == "Foundation"
        assert question.topic == "Fractions"
        assert question.subtopic == "fractions"
        assert "arithmetic" in question.mathematical_elements
    
    def test_parse_example_question_missing_fields(self):
        """Test parsing question data with missing required fields"""
        question_data = {
            "question_text": "Calculate something",
            "marks": 2
            # Missing tier and topic
        }
        
        question = self.processor.parse_example_question(question_data)
        assert question is None
    
    def test_parse_example_mark_scheme_valid(self):
        """Test parsing valid mark scheme data"""
        mark_scheme_data = {
            "marking_criteria": "M1: Convert to common denominator, A1: Correct answer",
            "method_marks": 1,
            "accuracy_marks": 1
        }
        
        mark_scheme = self.processor.parse_example_mark_scheme(mark_scheme_data)
        
        assert mark_scheme is not None
        assert mark_scheme.marking_criteria == "M1: Convert to common denominator, A1: Correct answer"
        assert mark_scheme.method_marks == 1
        assert mark_scheme.accuracy_marks == 1
        assert mark_scheme.total_marks == 2
    
    def test_extract_mathematical_elements(self):
        """Test mathematical elements extraction"""
        # Test arithmetic elements
        elements = self.processor._extract_mathematical_elements("Calculate 3 + 4 = 7")
        assert "arithmetic" in elements
        
        # Test fractions
        elements = self.processor._extract_mathematical_elements("Calculate 3/4 + 1/8")
        assert "fractions" in elements
        assert "arithmetic" in elements
        
        # Test decimals
        elements = self.processor._extract_mathematical_elements("Calculate 3.14 + 2.86")
        assert "decimals" in elements
        
        # Test percentages
        elements = self.processor._extract_mathematical_elements("Find 25% of 80")
        assert "percentages" in elements
    
    def test_determine_subtopic_from_question(self):
        """Test subtopic determination from question content"""
        # Test number subtopics
        assert self.processor._determine_subtopic_from_question("Calculate 3/4", "Number") == "number"  # Default case
        assert self.processor._determine_subtopic_from_question("Calculate fraction 3/4", "Number") == "fractions"
        assert self.processor._determine_subtopic_from_question("Find 25%", "Number") == "percentages"
        
        # Test algebra subtopics
        assert self.processor._determine_subtopic_from_question("Solve x² = 9", "Algebra") == "quadratics"
        assert self.processor._determine_subtopic_from_question("Solve 2x + 3 = 7", "Algebra") == "linear-equations"
    
    def test_calculate_comprehensive_quality_score(self):
        """Test comprehensive quality score calculation"""
        from src.services.seed_examples_processor import ExampleQuestion, ExampleMarkScheme
        
        question = ExampleQuestion(
            id="test_1",
            question_text="Calculate 3/4 + 1/8. Show your working clearly.",  # Good length
            marks=2,
            tier="Foundation",
            topic="Fractions",
            mathematical_elements=["arithmetic", "fractions"]  # Good mathematical content
        )
        
        mark_scheme = ExampleMarkScheme(
            question_id="test_1",
            marking_criteria="M1: Convert to common denominator (6/8 + 1/8), A1: Correct answer 7/8",  # Good detail
            method_marks=1,
            accuracy_marks=1,
            total_marks=2
        )
        
        score = self.processor._calculate_comprehensive_quality_score(question, mark_scheme)
        
        assert 0.0 <= score <= 1.0
        assert score > 0.7  # Should be high quality
    
    def test_validate_seed_example(self):
        """Test seed example validation"""
        from src.services.seed_examples_processor import ExampleQuestion, ExampleMarkScheme
        
        question = ExampleQuestion(
            id="test_1",
            question_text="Calculate 3/4 + 1/8.",
            marks=2,
            tier="Foundation",
            topic="Fractions"
        )
        
        mark_scheme = ExampleMarkScheme(
            question_id="test_1",
            marking_criteria="M1: Convert to common denominator, A1: Correct answer",
            method_marks=1,
            accuracy_marks=1,
            total_marks=2
        )
        
        validated = self.processor.validate_seed_example(question, mark_scheme)
        
        assert isinstance(validated, ValidatedSeedExample)
        assert validated.question == question
        assert validated.mark_scheme == mark_scheme
        assert validated.domain == "number"
        assert validated.subtopic == "fractions"
        assert validated.verification_status == "verified"  # No validation errors
    
    def test_create_examples_json_structure(self):
        """Test examples JSON structure creation"""
        from src.services.seed_examples_processor import ExampleQuestion, ExampleMarkScheme
        
        question = ExampleQuestion(
            id="test_1",
            question_text="Calculate 3/4 + 1/8.",
            marks=2,
            tier="Foundation",
            topic="Fractions"
        )
        
        mark_scheme = ExampleMarkScheme(
            question_id="test_1",
            marking_criteria="M1: Convert to common denominator, A1: Correct answer",
            method_marks=1,
            accuracy_marks=1,
            total_marks=2
        )
        
        validated = ValidatedSeedExample(
            question=question,
            mark_scheme=mark_scheme,
            quality_score=0.9,
            verification_status="verified",
            domain="number",
            subtopic="fractions",
            validation_errors=[]
        )
        
        json_structure = self.processor.create_examples_json_structure(
            [validated], "number", "fractions"
        )
        
        assert json_structure["domain"] == "number"
        assert json_structure["subtopic"] == "fractions"
        assert json_structure["total_examples"] == 1
        assert json_structure["average_quality_score"] == 0.9
        assert len(json_structure["examples"]) == 1


class TestVersionManagementService:
    """Test cases for VersionManagementService"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_s3_client = Mock()
        self.service = VersionManagementService(self.mock_s3_client)
    
    def test_add_version_tag(self):
        """Test version tag addition to content"""
        content = {"domain": "number", "subtopic": "fractions"}
        version = "2024.1"
        
        with patch.object(self.service, '_get_current_timestamp', return_value='2024-01-01T00:00:00Z'):
            versioned_content = self.service.add_version_tag(content, version)
        
        assert versioned_content["version"] == version
        assert versioned_content["version_timestamp"] == '2024-01-01T00:00:00Z'
        assert "version_metadata" in versioned_content
        assert versioned_content["version_metadata"]["status"] == "active"
    
    def test_create_versioned_file_path(self):
        """Test versioned file path creation"""
        base_path = "specifications/number/fractions.json"
        version = "2024.1"
        
        versioned_path = self.service.create_versioned_file_path(base_path, version)
        
        assert versioned_path == "specifications/number/fractions_v2024.1.json"
    
    def test_create_latest_symlink(self):
        """Test latest version symlink creation"""
        base_path = "specifications/number/fractions.json"
        version = "2024.1"
        
        latest_path = self.service.create_latest_symlink(base_path, version)
        
        assert latest_path == "specifications/number/fractions_latest.json"
    
    def test_get_version_selection_logic(self):
        """Test version selection logic"""
        # Test default (None) -> latest
        assert self.service.get_version_selection_logic(None) == "latest"
        
        # Test explicit latest
        assert self.service.get_version_selection_logic("latest") == "latest"
        
        # Test valid version
        assert self.service.get_version_selection_logic("2024.1") == "2024.1"
        
        # Test invalid version format -> latest
        assert self.service.get_version_selection_logic("invalid") == "latest"
    
    def test_parse_version(self):
        """Test version string parsing for sorting"""
        # Test semantic versioning
        assert self.service._parse_version("2024.1.0") == (2024, 1, 0)
        assert self.service._parse_version("2023.12.5") == (2023, 12, 5)
        
        # Test invalid version
        assert self.service._parse_version("invalid") == (0, 0, 0)
    
    def test_is_valid_version_format(self):
        """Test version format validation"""
        # Valid formats
        assert self.service._is_valid_version_format("2024.1")
        assert self.service._is_valid_version_format("2024.1.0")
        assert self.service._is_valid_version_format("1.0")
        
        # Invalid formats
        assert not self.service._is_valid_version_format("invalid")
        assert not self.service._is_valid_version_format("2024.1.a")
        assert not self.service._is_valid_version_format("")


class TestContentUploadService:
    """Test cases for ContentUploadService"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_s3_client = Mock()
        
        with patch('src.services.content_upload_service.boto3.client', return_value=self.mock_s3_client):
            self.service = ContentUploadService(
                specifications_bucket="test-specs-bucket",
                examples_bucket="test-examples-bucket"
            )
    
    def test_create_sample_content(self):
        """Test sample content creation"""
        spec_files, example_files = self.service.create_sample_content()
        
        # Check specifications
        assert len(spec_files) >= 2
        assert any("fractions.json" in path for path in spec_files.keys())
        assert any("linear-equations.json" in path for path in spec_files.keys())
        
        # Check examples
        assert len(example_files) >= 2
        assert any("fractions.json" in path for path in example_files.keys())
        assert any("linear-equations.json" in path for path in example_files.keys())
        
        # Validate JSON structure
        for json_content in spec_files.values():
            parsed = json.loads(json_content)
            assert "domain" in parsed
            assert "subtopic" in parsed
            assert "learning_objectives" in parsed
        
        for json_content in example_files.values():
            parsed = json.loads(json_content)
            assert "domain" in parsed
            assert "subtopic" in parsed
            assert "examples" in parsed
    
    @patch('src.services.content_upload_service.VersionManagementService')
    def test_upload_specification_files_success(self, mock_version_service):
        """Test successful specification files upload"""
        # Mock version service
        mock_version_service.return_value.upload_versioned_content.return_value = True
        
        json_files = {
            "specifications/number/fractions.json": '{"domain": "number", "subtopic": "fractions"}'
        }
        
        results = self.service.upload_specification_files(json_files, "2024.1")
        
        assert results["specifications/number/fractions.json"] is True
    
    def test_upload_examples_files_success(self):
        """Test successful examples files upload"""
        # Mock S3 put_object success
        self.mock_s3_client.put_object.return_value = {}
        
        json_files = {
            "examples/number/fractions.json": '{"domain": "number", "examples": []}'
        }
        
        results = self.service.upload_examples_files(json_files)
        
        assert results["examples/number/fractions.json"] is True
        self.mock_s3_client.put_object.assert_called_once()
    
    def test_verify_bucket_structure_success(self):
        """Test successful bucket structure verification"""
        # Mock S3 responses
        self.mock_s3_client.head_bucket.return_value = {}
        self.mock_s3_client.list_objects_v2.side_effect = [
            {  # Specifications bucket
                'Contents': [
                    {'Key': 'specifications/number/fractions.json'},
                    {'Key': 'specifications/algebra/linear-equations.json'}
                ]
            },
            {  # Examples bucket
                'Contents': [
                    {'Key': 'examples/number/fractions.json'},
                    {'Key': 'examples/algebra/linear-equations.json'}
                ]
            }
        ]
        
        # Mock version service
        with patch.object(self.service.version_service, 'list_all_versions', return_value={}):
            results = self.service.verify_bucket_structure()
        
        assert results['specifications_bucket']['exists'] is True
        assert results['specifications_bucket']['structure_valid'] is True
        assert results['examples_bucket']['exists'] is True
        assert results['examples_bucket']['structure_valid'] is True
        assert results['overall_valid'] is True


# Integration test for the full content processing pipeline
class TestContentProcessingIntegration:
    """Integration tests for content processing pipeline"""
    
    def test_full_processing_pipeline(self):
        """Test the complete content processing pipeline"""
        # This test would require actual PDF files and S3 setup
        # For now, we'll test the component integration
        
        mock_s3_client = Mock()
        processor = ContentProcessingService(mock_s3_client)
        
        # Test that all components work together
        sample_content = [
            ProcessedContent(
                domain="number",
                subtopic="fractions",
                tier="Foundation",
                version="2024.1",
                learning_objectives=["Test objective"],
                specification_content="Test content",
                key_concepts=["concept1"],
                common_misconceptions=["misconception1"],
                assessment_objectives=["AO1"],
                marks_range=[1, 3]
            )
        ]
        
        # Test organization
        organized = processor.organize_content_by_domain(sample_content)
        assert len(organized) == 1
        
        # Test JSON generation
        json_files = processor.generate_json_files(organized)
        assert len(json_files) == 1
        
        # Validate JSON structure
        json_content = list(json_files.values())[0]
        parsed = json.loads(json_content)
        assert parsed["domain"] == "number"
        assert parsed["subtopic"] == "fractions"