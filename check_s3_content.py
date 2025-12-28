#!/usr/bin/env python3
"""
S3 Content Analysis Script

This script checks the S3 buckets to understand what content is available
and why content retrieval is failing for certain topics.
"""

import boto3
import json
from typing import Dict, Any, List
from datetime import datetime

# Configuration
AWS_REGION = 'eu-west-2'
SPECIFICATIONS_BUCKET = 'gcse-specifications-prod-1a64dc99'
EXAMPLES_BUCKET = 'gcse-examples-prod-1a64dc99'

class S3ContentAnalyzer:
    """Analyzes S3 bucket content for GCSE question generation."""
    
    def __init__(self, region: str = AWS_REGION):
        self.region = region
        self.s3_client = boto3.client('s3', region_name=region)
    
    def list_bucket_contents(self, bucket_name: str) -> List[Dict[str, Any]]:
        """
        List all objects in an S3 bucket.
        
        Args:
            bucket_name: Name of the S3 bucket
            
        Returns:
            List of objects in the bucket
        """
        try:
            print(f"🔍 Listing contents of bucket: {bucket_name}")
            
            objects = []
            paginator = self.s3_client.get_paginator('list_objects_v2')
            
            for page in paginator.paginate(Bucket=bucket_name):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        objects.append({
                            'key': obj['Key'],
                            'size': obj['Size'],
                            'last_modified': obj['LastModified'],
                            'storage_class': obj.get('StorageClass', 'STANDARD')
                        })
            
            print(f"   📊 Found {len(objects)} objects")
            return objects
            
        except Exception as e:
            print(f"   ❌ Error listing bucket {bucket_name}: {str(e)}")
            return []
    
    def analyze_content_structure(self, objects: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze the structure of content in the bucket.
        
        Args:
            objects: List of S3 objects
            
        Returns:
            Analysis of content structure
        """
        structure = {
            'total_objects': len(objects),
            'directories': set(),
            'file_types': {},
            'topics': set(),
            'tiers': set(),
            'total_size': 0
        }
        
        for obj in objects:
            key = obj['key']
            size = obj['size']
            
            structure['total_size'] += size
            
            # Analyze directory structure
            if '/' in key:
                directory = '/'.join(key.split('/')[:-1])
                structure['directories'].add(directory)
            
            # Analyze file types
            if '.' in key:
                file_ext = key.split('.')[-1].lower()
                structure['file_types'][file_ext] = structure['file_types'].get(file_ext, 0) + 1
            
            # Try to extract topic information from path
            parts = key.split('/')
            if len(parts) >= 2:
                potential_topic = parts[1] if parts[0] in ['specifications', 'examples'] else parts[0]
                structure['topics'].add(potential_topic)
            
            # Look for tier information in filename
            if 'foundation' in key.lower():
                structure['tiers'].add('Foundation')
            if 'higher' in key.lower():
                structure['tiers'].add('Higher')
        
        # Convert sets to lists for JSON serialization
        structure['directories'] = sorted(list(structure['directories']))
        structure['topics'] = sorted(list(structure['topics']))
        structure['tiers'] = sorted(list(structure['tiers']))
        
        return structure
    
    def check_topic_coverage(self, bucket_name: str, objects: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Check which topics have content available.
        
        Args:
            bucket_name: Name of the bucket
            objects: List of S3 objects
            
        Returns:
            Topic coverage analysis
        """
        # Expected topics based on the system design
        expected_topics = [
            'number', 'algebra', 'geometry', 'statistics', 'probability', 'ratio'
        ]
        
        topic_coverage = {}
        
        for topic in expected_topics:
            topic_files = [obj for obj in objects if topic.lower() in obj['key'].lower()]
            topic_coverage[topic] = {
                'files_found': len(topic_files),
                'files': [obj['key'] for obj in topic_files],
                'total_size': sum(obj['size'] for obj in topic_files)
            }
        
        # Check for unexpected topics
        other_files = []
        for obj in objects:
            key_lower = obj['key'].lower()
            if not any(topic in key_lower for topic in expected_topics):
                other_files.append(obj['key'])
        
        topic_coverage['other'] = {
            'files_found': len(other_files),
            'files': other_files,
            'total_size': sum(obj['size'] for obj in objects if obj['key'] in other_files)
        }
        
        return topic_coverage
    
    def sample_file_content(self, bucket_name: str, key: str) -> Dict[str, Any]:
        """
        Sample content from a specific file.
        
        Args:
            bucket_name: Name of the bucket
            key: S3 object key
            
        Returns:
            Sample of file content
        """
        try:
            response = self.s3_client.get_object(Bucket=bucket_name, Key=key)
            content = response['Body'].read()
            
            # Try to parse as JSON
            try:
                json_content = json.loads(content)
                return {
                    'key': key,
                    'type': 'json',
                    'size': len(content),
                    'structure': list(json_content.keys()) if isinstance(json_content, dict) else 'array',
                    'sample': str(json_content)[:500] + "..." if len(str(json_content)) > 500 else str(json_content)
                }
            except json.JSONDecodeError:
                # Not JSON, treat as text
                try:
                    text_content = content.decode('utf-8')
                    return {
                        'key': key,
                        'type': 'text',
                        'size': len(content),
                        'sample': text_content[:500] + "..." if len(text_content) > 500 else text_content
                    }
                except UnicodeDecodeError:
                    return {
                        'key': key,
                        'type': 'binary',
                        'size': len(content),
                        'sample': f"Binary file, {len(content)} bytes"
                    }
                    
        except Exception as e:
            return {
                'key': key,
                'type': 'error',
                'error': str(e)
            }
    
    def analyze_bucket(self, bucket_name: str, bucket_type: str) -> Dict[str, Any]:
        """
        Analyze a specific S3 bucket.
        
        Args:
            bucket_name: Name of the bucket
            bucket_type: Type of bucket (specifications/examples)
            
        Returns:
            Complete bucket analysis
        """
        print(f"\n{'='*80}")
        print(f"📊 ANALYZING {bucket_type.upper()} BUCKET")
        print(f"{'='*80}")
        print(f"Bucket: {bucket_name}")
        
        # List bucket contents
        objects = self.list_bucket_contents(bucket_name)
        
        if not objects:
            return {
                'bucket_name': bucket_name,
                'bucket_type': bucket_type,
                'status': 'empty_or_inaccessible',
                'objects': []
            }
        
        # Analyze structure
        structure = self.analyze_content_structure(objects)
        
        print(f"\n📈 Bucket Structure:")
        print(f"   Total objects: {structure['total_objects']}")
        print(f"   Total size: {structure['total_size']:,} bytes")
        print(f"   Directories: {len(structure['directories'])}")
        print(f"   File types: {structure['file_types']}")
        print(f"   Topics found: {structure['topics']}")
        print(f"   Tiers found: {structure['tiers']}")
        
        # Check topic coverage
        topic_coverage = self.check_topic_coverage(bucket_name, objects)
        
        print(f"\n🎯 Topic Coverage:")
        for topic, info in topic_coverage.items():
            if info['files_found'] > 0:
                print(f"   ✅ {topic}: {info['files_found']} files ({info['total_size']:,} bytes)")
            else:
                print(f"   ❌ {topic}: No files found")
        
        # Sample some files
        sample_files = []
        if objects:
            # Sample up to 3 files
            for obj in objects[:3]:
                sample = self.sample_file_content(bucket_name, obj['key'])
                sample_files.append(sample)
                
                print(f"\n📄 Sample: {obj['key']}")
                print(f"   Type: {sample.get('type', 'unknown')}")
                print(f"   Size: {sample.get('size', 0):,} bytes")
                if sample.get('type') == 'json' and sample.get('structure'):
                    print(f"   Structure: {sample['structure']}")
                if sample.get('sample'):
                    print(f"   Content preview: {sample['sample'][:200]}...")
        
        return {
            'bucket_name': bucket_name,
            'bucket_type': bucket_type,
            'status': 'accessible',
            'objects': objects,
            'structure': structure,
            'topic_coverage': topic_coverage,
            'sample_files': sample_files
        }
    
    def run_comprehensive_analysis(self) -> Dict[str, Any]:
        """
        Run comprehensive analysis of both S3 buckets.
        
        Returns:
            Complete analysis results
        """
        print(f"\n{'='*100}")
        print(f"🗂️  S3 CONTENT ANALYSIS")
        print(f"{'='*100}")
        print(f"Analyzing S3 buckets to understand content availability and structure")
        
        # Analyze specifications bucket
        specifications_analysis = self.analyze_bucket(SPECIFICATIONS_BUCKET, 'specifications')
        
        # Analyze examples bucket
        examples_analysis = self.analyze_bucket(EXAMPLES_BUCKET, 'examples')
        
        # Generate overall summary
        summary = self.generate_overall_summary(specifications_analysis, examples_analysis)
        
        return {
            'specifications_analysis': specifications_analysis,
            'examples_analysis': examples_analysis,
            'summary': summary,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def generate_overall_summary(self, specs_analysis: Dict, examples_analysis: Dict) -> Dict[str, Any]:
        """
        Generate overall summary of S3 content analysis.
        
        Args:
            specs_analysis: Specifications bucket analysis
            examples_analysis: Examples bucket analysis
            
        Returns:
            Overall summary
        """
        print(f"\n{'='*100}")
        print(f"📋 OVERALL S3 CONTENT SUMMARY")
        print(f"{'='*100}")
        
        # Check bucket accessibility
        specs_accessible = specs_analysis['status'] == 'accessible'
        examples_accessible = examples_analysis['status'] == 'accessible'
        
        print(f"🔍 Bucket Status:")
        print(f"   Specifications bucket: {'✅ Accessible' if specs_accessible else '❌ Inaccessible'}")
        print(f"   Examples bucket: {'✅ Accessible' if examples_accessible else '❌ Inaccessible'}")
        
        if specs_accessible:
            specs_objects = len(specs_analysis['objects'])
            specs_topics = len([t for t, info in specs_analysis['topic_coverage'].items() 
                              if info['files_found'] > 0 and t != 'other'])
            print(f"   Specifications: {specs_objects} files, {specs_topics} topics covered")
        
        if examples_accessible:
            examples_objects = len(examples_analysis['objects'])
            examples_topics = len([t for t, info in examples_analysis['topic_coverage'].items() 
                                 if info['files_found'] > 0 and t != 'other'])
            print(f"   Examples: {examples_objects} files, {examples_topics} topics covered")
        
        # Identify missing topics
        expected_topics = ['number', 'algebra', 'geometry', 'statistics', 'probability', 'ratio']
        missing_specs = []
        missing_examples = []
        
        if specs_accessible:
            missing_specs = [topic for topic in expected_topics 
                           if specs_analysis['topic_coverage'][topic]['files_found'] == 0]
        
        if examples_accessible:
            missing_examples = [topic for topic in expected_topics 
                              if examples_analysis['topic_coverage'][topic]['files_found'] == 0]
        
        print(f"\n⚠️  Missing Content:")
        if missing_specs:
            print(f"   Missing specifications: {', '.join(missing_specs)}")
        if missing_examples:
            print(f"   Missing examples: {', '.join(missing_examples)}")
        
        # Determine overall content status
        content_sufficient = (
            specs_accessible and examples_accessible and
            len(missing_specs) <= 2 and len(missing_examples) <= 2
        )
        
        print(f"\n🎯 Overall Assessment:")
        if content_sufficient:
            print(f"   ✅ Content appears sufficient for basic operation")
        else:
            print(f"   ❌ Insufficient content - this explains generation failures")
            
        issues = []
        if not specs_accessible:
            issues.append("Specifications bucket inaccessible")
        if not examples_accessible:
            issues.append("Examples bucket inaccessible")
        if len(missing_specs) > 2:
            issues.append(f"Many missing specification topics: {missing_specs}")
        if len(missing_examples) > 2:
            issues.append(f"Many missing example topics: {missing_examples}")
        
        return {
            'specifications_accessible': specs_accessible,
            'examples_accessible': examples_accessible,
            'specifications_objects': specs_objects if specs_accessible else 0,
            'examples_objects': examples_objects if examples_accessible else 0,
            'missing_specifications': missing_specs,
            'missing_examples': missing_examples,
            'content_sufficient': content_sufficient,
            'issues': issues
        }


def main():
    """Main function to run S3 content analysis."""
    
    try:
        # Initialize analyzer
        analyzer = S3ContentAnalyzer()
        
        # Run comprehensive analysis
        results = analyzer.run_comprehensive_analysis()
        
        # Save results to file
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        results_file = f"s3_content_analysis_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n💾 Results saved to: {results_file}")
        
        # Return exit code based on analysis
        if results['summary']['content_sufficient']:
            print("\n🎉 S3 Content Analysis: Sufficient Content Available")
            return 0
        else:
            print("\n💥 S3 Content Analysis: Insufficient Content - This Explains Generation Failures")
            return 1
            
    except Exception as e:
        print(f"\n💥 Analysis failed: {str(e)}")
        return 1


if __name__ == "__main__":
    exit(main())