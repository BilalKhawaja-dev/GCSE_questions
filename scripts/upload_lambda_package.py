#!/usr/bin/env python3
"""
Upload Lambda deployment package to S3.

This script uploads the Lambda deployment package to the S3 bucket
that will be created by Terraform.
"""

import os
import sys
import boto3
import json
from pathlib import Path
from botocore.exceptions import ClientError, NoCredentialsError

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
TERRAFORM_DIR = PROJECT_ROOT / "terraform"
LAMBDA_PACKAGE_PATH = TERRAFORM_DIR / "lambda-package" / "lambda-functions.zip"


def get_terraform_outputs() -> dict:
    """Get Terraform outputs to find the deployment bucket name."""
    try:
        # Change to terraform directory
        os.chdir(TERRAFORM_DIR)
        
        # Run terraform output to get bucket names
        import subprocess
        result = subprocess.run(
            ["terraform", "output", "-json"],
            capture_output=True,
            text=True,
            check=True
        )
        
        outputs = json.loads(result.stdout)
        return outputs
        
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to get Terraform outputs: {e.stderr}")
        print("Make sure Terraform has been applied and outputs are available")
        return None
    except Exception as e:
        print(f"✗ Error getting Terraform outputs: {str(e)}")
        return None


def upload_to_s3(bucket_name: str, file_path: Path, key: str) -> bool:
    """Upload file to S3 bucket."""
    try:
        # Initialize S3 client
        s3_client = boto3.client('s3', region_name='eu-west-2')
        
        # Check if bucket exists
        try:
            s3_client.head_bucket(Bucket=bucket_name)
            print(f"✓ Found S3 bucket: {bucket_name}")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                print(f"✗ S3 bucket not found: {bucket_name}")
                print("Make sure Terraform has been applied to create the bucket")
                return False
            else:
                print(f"✗ Error accessing bucket {bucket_name}: {str(e)}")
                return False
        
        # Get file size
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        print(f"Uploading {file_path.name} ({file_size_mb:.2f} MB) to s3://{bucket_name}/{key}")
        
        # Upload file
        s3_client.upload_file(
            str(file_path),
            bucket_name,
            key,
            ExtraArgs={
                'ServerSideEncryption': 'AES256',
                'Metadata': {
                    'uploaded-by': 'gcse-deployment-script',
                    'package-version': '1.0.0'
                }
            }
        )
        
        print(f"✓ Successfully uploaded to s3://{bucket_name}/{key}")
        
        # Verify upload
        try:
            response = s3_client.head_object(Bucket=bucket_name, Key=key)
            uploaded_size = response['ContentLength']
            original_size = file_path.stat().st_size
            
            if uploaded_size == original_size:
                print(f"✓ Upload verified - size matches ({uploaded_size} bytes)")
                return True
            else:
                print(f"✗ Upload verification failed - size mismatch")
                print(f"  Original: {original_size} bytes")
                print(f"  Uploaded: {uploaded_size} bytes")
                return False
                
        except ClientError as e:
            print(f"✗ Failed to verify upload: {str(e)}")
            return False
            
    except NoCredentialsError:
        print("✗ AWS credentials not found")
        print("Please configure AWS credentials using:")
        print("  - AWS CLI: aws configure")
        print("  - Environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY")
        print("  - IAM role (if running on EC2)")
        return False
    except Exception as e:
        print(f"✗ Upload failed: {str(e)}")
        return False


def main():
    """Main upload function."""
    print("GCSE Question Generator - Lambda Package Upload")
    print("=" * 50)
    
    # Check if package exists
    if not LAMBDA_PACKAGE_PATH.exists():
        print(f"✗ Lambda package not found: {LAMBDA_PACKAGE_PATH}")
        print("Run 'python3 scripts/package_lambda.py' first to create the package")
        sys.exit(1)
    
    print(f"✓ Found Lambda package: {LAMBDA_PACKAGE_PATH}")
    
    # Get Terraform outputs
    print("Getting deployment bucket name from Terraform...")
    outputs = get_terraform_outputs()
    
    if not outputs:
        print("✗ Could not get Terraform outputs")
        print("\nAlternative: You can manually specify the bucket name")
        print("Usage: python3 scripts/upload_lambda_package.py <bucket-name>")
        sys.exit(1)
    
    # Extract bucket name
    try:
        bucket_name = outputs['lambda_packages_bucket_name']['value']
        print(f"✓ Deployment bucket: {bucket_name}")
    except KeyError:
        print("✗ Lambda packages bucket name not found in Terraform outputs")
        print("Make sure the knowledge module has been applied")
        sys.exit(1)
    
    # Upload package
    success = upload_to_s3(
        bucket_name=bucket_name,
        file_path=LAMBDA_PACKAGE_PATH,
        key="lambda-functions.zip"
    )
    
    if success:
        print("\n" + "=" * 50)
        print("✓ Lambda package upload completed successfully!")
        print(f"✓ Package location: s3://{bucket_name}/lambda-functions.zip")
        print("✓ Ready for Lambda deployment")
        
        print("\nNext steps:")
        print("1. Run 'terraform plan' to see Lambda function updates")
        print("2. Run 'terraform apply' to deploy the updated functions")
        print("3. Test the deployed functions")
    else:
        print("\n" + "=" * 50)
        print("✗ Lambda package upload failed")
        sys.exit(1)


if __name__ == "__main__":
    # Allow manual bucket specification
    if len(sys.argv) > 1:
        bucket_name = sys.argv[1]
        print(f"Using manually specified bucket: {bucket_name}")
        
        if not LAMBDA_PACKAGE_PATH.exists():
            print(f"✗ Lambda package not found: {LAMBDA_PACKAGE_PATH}")
            sys.exit(1)
        
        success = upload_to_s3(
            bucket_name=bucket_name,
            file_path=LAMBDA_PACKAGE_PATH,
            key="lambda-functions.zip"
        )
        
        if not success:
            sys.exit(1)
    else:
        main()