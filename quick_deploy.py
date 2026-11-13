#!/usr/bin/env python3
"""
Quick deployment script for updating Lambda function code.
"""

import boto3
import zipfile
import tempfile
import shutil
from pathlib import Path

def create_lambda_package():
    """Create Lambda deployment package."""
    
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
        zip_path = Path("lambda-update-package.zip")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in package_dir.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(package_dir)
                    zipf.write(file_path, arcname)
        
        return zip_path

def update_async_worker():
    """Update the async worker Lambda function."""
    
    try:
        # Create package
        print("📦 Creating Lambda package...")
        zip_path = create_lambda_package()
        
        # Update function
        lambda_client = boto3.client('lambda')
        
        with open(zip_path, 'rb') as f:
            zip_content = f.read()
        
        response = lambda_client.update_function_code(
            FunctionName='gcse-async-worker-lambda-prod',
            ZipFile=zip_content
        )
        
        print(f"✅ Updated gcse-async-worker-lambda-prod")
        print(f"   Version: {response['Version']}")
        print(f"   Last Modified: {response['LastModified']}")
        
        # Clean up
        zip_path.unlink()
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to update: {str(e)}")
        return False

if __name__ == "__main__":
    if update_async_worker():
        print("\n🎉 Parallel optimization deployed!")
        print("The async worker now has parallel processing capabilities.")
    else:
        print("\n❌ Deployment failed.")