#!/usr/bin/env python3
"""
Deploy to CodePipeline

This script packages and deploys the cleaned codebase to the existing CodePipeline.
"""

import os
import sys
import json
import boto3
import zipfile
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# AWS Configuration
AWS_REGION = 'eu-west-2'
PIPELINE_NAME = 'aws-learning-platform-pipeline-dev'
SOURCE_BUCKET = 'aws-learning-platform-source-dev'
SOURCE_KEY = 'source.zip'

class CodePipelineDeployer:
    """Deploy cleaned codebase to CodePipeline"""
    
    def __init__(self):
        """Initialize the deployer"""
        self.s3_client = boto3.client('s3', region_name=AWS_REGION)
        self.codepipeline_client = boto3.client('codepipeline', region_name=AWS_REGION)
        self.workspace_root = Path('.')
        
    def get_files_to_include(self) -> List[Path]:
        """Get list of files to include in deployment package"""
        
        # Essential directories and files
        include_patterns = [
            'src/**/*',
            'frontend/**/*',
            'terraform/**/*',
            'tests/**/*',
            'scripts/**/*',
            '.kiro/**/*',
            '*.py',
            '*.md',
            '*.json',
            '*.txt',
            '*.ini',
            '*.yml',
            '*.yaml',
            '.gitignore'
        ]
        
        # Files to exclude
        exclude_patterns = [
            '__pycache__',
            '*.pyc',
            '.pytest_cache',
            'node_modules',
            '.git',
            '*.log',
            'temp_*',
            '*_temp.*',
            '.DS_Store',
            '.vscode',
            '.idea'
        ]
        
        files_to_include = []
        
        # Get all files matching include patterns
        for pattern in include_patterns:
            if '**' in pattern:
                # Recursive pattern
                base_pattern = pattern.replace('/**/*', '')
                if base_pattern == '*':
                    # All files in root
                    for file_path in self.workspace_root.glob(pattern):
                        if file_path.is_file():
                            files_to_include.append(file_path)
                else:
                    # Specific directory recursive
                    for file_path in self.workspace_root.rglob(pattern.replace('**/*', '*')):
                        if file_path.is_file():
                            files_to_include.append(file_path)
            else:
                # Simple pattern
                for file_path in self.workspace_root.glob(pattern):
                    if file_path.is_file():
                        files_to_include.append(file_path)
        
        # Filter out excluded files
        filtered_files = []
        for file_path in files_to_include:
            file_str = str(file_path)
            should_exclude = False
            
            for exclude_pattern in exclude_patterns:
                if exclude_pattern in file_str:
                    should_exclude = True
                    break
            
            if not should_exclude:
                filtered_files.append(file_path)
        
        # Remove duplicates and sort
        filtered_files = list(set(filtered_files))
        filtered_files.sort()
        
        logger.info(f"Selected {len(filtered_files)} files for deployment")
        return filtered_files
    
    def create_deployment_package(self, files: List[Path]) -> str:
        """Create deployment ZIP package"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"gcse_deployment_{timestamp}.zip"
        
        logger.info(f"Creating deployment package: {zip_filename}")
        
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in files:
                # Use relative path in ZIP
                arcname = str(file_path.relative_to(self.workspace_root))
                zipf.write(file_path, arcname)
                logger.debug(f"Added to ZIP: {arcname}")
        
        # Get ZIP file size
        zip_size = os.path.getsize(zip_filename)
        logger.info(f"✅ Created deployment package: {zip_filename} ({zip_size:,} bytes)")
        
        return zip_filename
    
    def upload_to_source_bucket(self, zip_filename: str) -> bool:
        """Upload deployment package to CodePipeline source bucket"""
        
        logger.info(f"Uploading {zip_filename} to S3 source bucket")
        
        try:
            # Upload to S3
            with open(zip_filename, 'rb') as f:
                self.s3_client.put_object(
                    Bucket=SOURCE_BUCKET,
                    Key=SOURCE_KEY,
                    Body=f,
                    ServerSideEncryption='AES256',
                    Metadata={
                        'deployment_timestamp': datetime.now().isoformat(),
                        'deployment_type': 'enhanced_ai_system',
                        'version': '1.1.0'
                    }
                )
            
            logger.info(f"✅ Successfully uploaded to s3://{SOURCE_BUCKET}/{SOURCE_KEY}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to upload to S3: {str(e)}")
            return False
    
    def trigger_pipeline(self) -> bool:
        """Trigger the CodePipeline execution"""
        
        logger.info(f"Triggering CodePipeline: {PIPELINE_NAME}")
        
        try:
            response = self.codepipeline_client.start_pipeline_execution(
                name=PIPELINE_NAME
            )
            
            execution_id = response['pipelineExecutionId']
            logger.info(f"✅ Pipeline triggered successfully")
            logger.info(f"   Execution ID: {execution_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to trigger pipeline: {str(e)}")
            return False
    
    def monitor_pipeline_status(self, timeout_minutes: int = 30) -> Dict[str, Any]:
        """Monitor pipeline execution status"""
        
        logger.info(f"Monitoring pipeline status (timeout: {timeout_minutes} minutes)")
        
        import time
        start_time = time.time()
        timeout_seconds = timeout_minutes * 60
        
        while time.time() - start_time < timeout_seconds:
            try:
                response = self.codepipeline_client.get_pipeline_state(name=PIPELINE_NAME)
                
                stage_states = response.get('stageStates', [])
                
                # Check overall status
                pipeline_status = 'InProgress'
                failed_stages = []
                completed_stages = []
                
                for stage in stage_states:
                    stage_name = stage['stageName']
                    stage_status = stage.get('latestExecution', {}).get('status', 'Unknown')
                    
                    if stage_status == 'Failed':
                        failed_stages.append(stage_name)
                        pipeline_status = 'Failed'
                    elif stage_status == 'Succeeded':
                        completed_stages.append(stage_name)
                
                # Log current status
                logger.info(f"Pipeline status: {pipeline_status}")
                logger.info(f"Completed stages: {completed_stages}")
                if failed_stages:
                    logger.error(f"Failed stages: {failed_stages}")
                
                # Check if pipeline is complete
                if pipeline_status == 'Failed':
                    return {
                        'status': 'Failed',
                        'failed_stages': failed_stages,
                        'completed_stages': completed_stages
                    }
                
                # Check if all stages are complete
                all_succeeded = all(
                    stage.get('latestExecution', {}).get('status') == 'Succeeded'
                    for stage in stage_states
                )
                
                if all_succeeded:
                    return {
                        'status': 'Succeeded',
                        'completed_stages': completed_stages,
                        'execution_time': time.time() - start_time
                    }
                
                # Wait before next check
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"Error monitoring pipeline: {str(e)}")
                time.sleep(30)
        
        # Timeout reached
        return {
            'status': 'Timeout',
            'message': f'Pipeline monitoring timed out after {timeout_minutes} minutes'
        }
    
    def cleanup_local_files(self, zip_filename: str):
        """Clean up local deployment files"""
        
        try:
            if os.path.exists(zip_filename):
                os.remove(zip_filename)
                logger.info(f"✅ Cleaned up local file: {zip_filename}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to cleanup {zip_filename}: {str(e)}")
    
    def run_deployment(self, monitor: bool = True) -> Dict[str, Any]:
        """Run complete deployment process"""
        
        logger.info("🚀 Starting CodePipeline deployment")
        
        results = {
            'files_selected': 0,
            'package_created': False,
            'uploaded_to_s3': False,
            'pipeline_triggered': False,
            'pipeline_status': None,
            'deployment_successful': False
        }
        
        zip_filename = None
        
        try:
            # Step 1: Select files for deployment
            logger.info("Step 1: Selecting files for deployment")
            files = self.get_files_to_include()
            results['files_selected'] = len(files)
            
            if not files:
                raise Exception("No files selected for deployment")
            
            # Step 2: Create deployment package
            logger.info("Step 2: Creating deployment package")
            zip_filename = self.create_deployment_package(files)
            results['package_created'] = True
            
            # Step 3: Upload to S3 source bucket
            logger.info("Step 3: Uploading to S3 source bucket")
            upload_success = self.upload_to_source_bucket(zip_filename)
            results['uploaded_to_s3'] = upload_success
            
            if not upload_success:
                raise Exception("Failed to upload to S3")
            
            # Step 4: Trigger pipeline
            logger.info("Step 4: Triggering CodePipeline")
            trigger_success = self.trigger_pipeline()
            results['pipeline_triggered'] = trigger_success
            
            if not trigger_success:
                raise Exception("Failed to trigger pipeline")
            
            # Step 5: Monitor pipeline (optional)
            if monitor:
                logger.info("Step 5: Monitoring pipeline execution")
                pipeline_result = self.monitor_pipeline_status()
                results['pipeline_status'] = pipeline_result
                
                if pipeline_result['status'] == 'Succeeded':
                    results['deployment_successful'] = True
                    logger.info("🎉 Deployment completed successfully!")
                else:
                    logger.error(f"💥 Pipeline execution failed: {pipeline_result}")
            else:
                results['deployment_successful'] = True
                logger.info("🎉 Deployment triggered successfully!")
            
        except Exception as e:
            logger.error(f"💥 Deployment failed: {str(e)}")
            results['error'] = str(e)
        
        finally:
            # Cleanup
            if zip_filename:
                self.cleanup_local_files(zip_filename)
        
        return results

def main():
    """Main deployment function"""
    
    print("🚀 CODEPIPELINE DEPLOYMENT")
    print("=" * 60)
    print("Deploying cleaned codebase to existing CodePipeline")
    
    try:
        deployer = CodePipelineDeployer()
        results = deployer.run_deployment(monitor=True)
        
        print(f"\\n📊 Deployment Results:")
        print(f"   Files selected: {results['files_selected']}")
        print(f"   Package created: {results['package_created']}")
        print(f"   Uploaded to S3: {results['uploaded_to_s3']}")
        print(f"   Pipeline triggered: {results['pipeline_triggered']}")
        print(f"   Deployment successful: {results['deployment_successful']}")
        
        if results.get('pipeline_status'):
            status = results['pipeline_status']
            print(f"\\n📈 Pipeline Status: {status.get('status', 'Unknown')}")
            if status.get('completed_stages'):
                print(f"   Completed stages: {status['completed_stages']}")
            if status.get('failed_stages'):
                print(f"   Failed stages: {status['failed_stages']}")
        
        if results['deployment_successful']:
            print(f"\\n🎉 Deployment successful!")
            print(f"\\n📋 What was deployed:")
            print(f"   • Enhanced AI knowledge base system")
            print(f"   • Cache clearing and fixing tools")
            print(f"   • PDF upload and processing system")
            print(f"   • Mathematical notation improvements")
            print(f"   • Consolidated validation tools")
            print(f"   • Updated Lambda functions and infrastructure")
            
            print(f"\\n🔗 Monitor pipeline at:")
            print(f"   https://console.aws.amazon.com/codesuite/codepipeline/pipelines/{PIPELINE_NAME}/view")
            
            return True
        else:
            print(f"\\n⚠️ Deployment had issues. Check logs above.")
            return False
            
    except Exception as e:
        print(f"\\n💥 Deployment failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)