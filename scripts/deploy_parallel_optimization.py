#!/usr/bin/env python3
"""
Deploy parallel optimization for faster question generation.
"""

import boto3
import json
import os
import sys
import zipfile
import tempfile
import shutil
from pathlib import Path

def create_lambda_package():
    """Create Lambda deployment package with parallel worker."""
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        package_dir = Path(temp_dir) / "package"
        package_dir.mkdir()
        
        # Copy source files
        src_dir = Path("src")
        if not src_dir.exists():
            raise FileNotFoundError("src directory not found")
        
        # Copy all source files
        shutil.copytree(src_dir, package_dir / "src")
        
        # Create zip file
        zip_path = Path("lambda-parallel-package.zip")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in package_dir.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(package_dir)
                    zipf.write(file_path, arcname)
        
        return zip_path

def update_lambda_function(function_name: str, zip_path: Path):
    """Update Lambda function with new code."""
    
    lambda_client = boto3.client('lambda')
    
    try:
        # Read the zip file
        with open(zip_path, 'rb') as f:
            zip_content = f.read()
        
        # Update function code
        response = lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=zip_content
        )
        
        print(f"✅ Updated {function_name}")
        print(f"   Version: {response['Version']}")
        print(f"   Last Modified: {response['LastModified']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to update {function_name}: {str(e)}")
        return False

def update_environment_variables(function_name: str, env_vars: dict):
    """Update Lambda environment variables."""
    
    lambda_client = boto3.client('lambda')
    
    try:
        # Get current environment variables
        response = lambda_client.get_function_configuration(FunctionName=function_name)
        current_env = response.get('Environment', {}).get('Variables', {})
        
        # Merge with new variables
        updated_env = {**current_env, **env_vars}
        
        # Update environment
        lambda_client.update_function_configuration(
            FunctionName=function_name,
            Environment={'Variables': updated_env}
        )
        
        print(f"✅ Updated environment variables for {function_name}")
        for key, value in env_vars.items():
            print(f"   {key}: {value}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to update environment for {function_name}: {str(e)}")
        return False

def create_parallel_queue():
    """Create SQS queue for parallel processing if it doesn't exist."""
    
    sqs_client = boto3.client('sqs')
    
    queue_name = "gcse-parallel-async-queue"
    
    try:
        # Check if queue exists
        try:
            response = sqs_client.get_queue_url(QueueName=queue_name)
            queue_url = response['QueueUrl']
            print(f"✅ Parallel queue already exists: {queue_url}")
            return queue_url
        except sqs_client.exceptions.QueueDoesNotExist:
            pass
        
        # Create queue with optimized settings for parallel processing
        response = sqs_client.create_queue(
            QueueName=queue_name,
            Attributes={
                'VisibilityTimeoutSeconds': '300',  # 5 minutes
                'MessageRetentionPeriod': '1209600',  # 14 days
                'ReceiveMessageWaitTimeSeconds': '0'  # No long polling for faster processing
            }
        )
        
        queue_url = response['QueueUrl']
        print(f"✅ Created parallel queue: {queue_url}")
        return queue_url
        
    except Exception as e:
        print(f"❌ Failed to create parallel queue: {str(e)}")
        return None

def main():
    """Main deployment function."""
    
    print("🚀 Deploying parallel optimization for GCSE question generation...")
    
    # Check AWS credentials
    try:
        sts_client = boto3.client('sts')
        identity = sts_client.get_caller_identity()
        print(f"✅ AWS Account: {identity['Account']}")
    except Exception as e:
        print(f"❌ AWS credentials not configured: {str(e)}")
        return False
    
    # Create Lambda package
    print("\n📦 Creating Lambda deployment package...")
    try:
        zip_path = create_lambda_package()
        print(f"✅ Package created: {zip_path}")
    except Exception as e:
        print(f"❌ Failed to create package: {str(e)}")
        return False
    
    # Create parallel queue
    print("\n🔄 Setting up parallel processing queue...")
    parallel_queue_url = create_parallel_queue()
    
    # Lambda functions to update
    functions_to_update = [
        "gcse-async-worker-lambda-prod",  # Main async worker
        "gcse-generate-lambda-prod"  # Generate lambda
    ]
    
    # Update Lambda functions
    print("\n🔄 Updating Lambda functions...")
    success_count = 0
    
    for function_name in functions_to_update:
        if update_lambda_function(function_name, zip_path):
            success_count += 1
            
            # Update environment variables for async worker
            if "async-worker" in function_name and parallel_queue_url:
                env_vars = {
                    'PARALLEL_PROCESSING_ENABLED': 'true',
                    'PARALLEL_ASYNC_QUEUE_URL': parallel_queue_url,
                    'MAX_PARALLEL_WORKERS': '5'
                }
                update_environment_variables(function_name, env_vars)
            
            # Update environment variables for generate lambda
            elif "generate" in function_name and parallel_queue_url:
                env_vars = {
                    'PARALLEL_ASYNC_QUEUE_URL': parallel_queue_url,
                    'PARALLEL_PROCESSING_ENABLED': 'true'
                }
                update_environment_variables(function_name, env_vars)
    
    # Clean up
    if zip_path.exists():
        zip_path.unlink()
    
    print(f"\n✅ Deployment completed: {success_count}/{len(functions_to_update)} functions updated")
    
    if success_count == len(functions_to_update):
        print("\n🎉 Parallel optimization deployed successfully!")
        print("\nExpected improvements:")
        print("• 3-4x faster generation for requests >8 questions")
        print("• Parallel processing of question batches")
        print("• Reduced latency through concurrent Bedrock calls")
        print("• Better progress tracking")
        
        print("\nTo test:")
        print("• Try generating 15-20 questions")
        print("• Monitor the faster completion times")
        print("• Check CloudWatch logs for parallel processing")
        
        return True
    else:
        print("\n⚠️  Some functions failed to update. Check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)