#!/usr/bin/env python3
"""
Deploy frontend build to S3 and invalidate CloudFront cache.
"""

import boto3
import os
import sys
import mimetypes
from pathlib import Path

def get_content_type(file_path):
    """Get the content type for a file"""
    content_type, _ = mimetypes.guess_type(file_path)
    return content_type or 'application/octet-stream'

def upload_directory_to_s3(local_directory, bucket_name, s3_prefix=''):
    """Upload a directory to S3"""
    s3_client = boto3.client('s3')
    
    local_path = Path(local_directory)
    uploaded_files = []
    
    for file_path in local_path.rglob('*'):
        if file_path.is_file():
            # Calculate relative path
            relative_path = file_path.relative_to(local_path)
            s3_key = str(relative_path).replace('\\', '/')
            
            if s3_prefix:
                s3_key = f"{s3_prefix}/{s3_key}"
            
            # Get content type
            content_type = get_content_type(str(file_path))
            
            # Upload file
            extra_args = {
                'ContentType': content_type
            }
            
            # Add cache control headers
            if '/static/' in s3_key:
                # Static assets - cache for 1 year
                extra_args['CacheControl'] = 'public, max-age=31536000, immutable'
            else:
                # HTML files - shorter cache
                extra_args['CacheControl'] = 'public, max-age=3600'
            
            print(f"Uploading {relative_path} to s3://{bucket_name}/{s3_key}")
            s3_client.upload_file(
                str(file_path),
                bucket_name,
                s3_key,
                ExtraArgs=extra_args
            )
            uploaded_files.append(s3_key)
    
    return uploaded_files

def invalidate_cloudfront(distribution_id, paths=['/*']):
    """Invalidate CloudFront cache"""
    cloudfront_client = boto3.client('cloudfront')
    
    print(f"Creating CloudFront invalidation for distribution {distribution_id}")
    response = cloudfront_client.create_invalidation(
        DistributionId=distribution_id,
        InvalidationBatch={
            'Paths': {
                'Quantity': len(paths),
                'Items': paths
            },
            'CallerReference': str(int(os.times()[4] * 1000))
        }
    )
    
    invalidation_id = response['Invalidation']['Id']
    print(f"Invalidation created: {invalidation_id}")
    return invalidation_id

def get_terraform_outputs():
    """Get Terraform outputs"""
    import subprocess
    import json
    
    try:
        result = subprocess.run(
            ['terraform', 'output', '-json'],
            cwd='terraform',
            capture_output=True,
            text=True,
            check=True
        )
        outputs = json.loads(result.stdout)
        return outputs
    except Exception as e:
        print(f"Error getting Terraform outputs: {e}")
        return None

def main():
    """Main deployment function"""
    print("Frontend Deployment Script")
    print("=" * 50)
    
    # Check if build directory exists
    build_dir = 'frontend/build'
    if not os.path.exists(build_dir):
        print(f"Error: Build directory not found: {build_dir}")
        print("Please run 'npm run build' in the frontend directory first")
        return 1
    
    # Get Terraform outputs
    print("Getting Terraform outputs...")
    outputs = get_terraform_outputs()
    
    if not outputs:
        print("Error: Could not get Terraform outputs")
        print("Please ensure Terraform has been applied successfully")
        return 1
    
    # Extract bucket name and CloudFront distribution ID
    try:
        bucket_name = outputs['frontend_bucket_name']['value']
        distribution_id = outputs['cloudfront_distribution_id']['value']
        cloudfront_url = outputs.get('cloudfront_url', {}).get('value') or \
                        f"https://{outputs['cloudfront_domain_name']['value']}"
    except KeyError as e:
        print(f"Error: Missing Terraform output: {e}")
        print("Available outputs:", list(outputs.keys()))
        return 1
    
    print(f"S3 Bucket: {bucket_name}")
    print(f"CloudFront Distribution: {distribution_id}")
    print(f"CloudFront URL: {cloudfront_url}")
    
    # Upload files to S3
    print("\nUploading files to S3...")
    try:
        uploaded_files = upload_directory_to_s3(build_dir, bucket_name)
        print(f"\n✅ Uploaded {len(uploaded_files)} files to S3")
    except Exception as e:
        print(f"❌ Error uploading files: {e}")
        return 1
    
    # Invalidate CloudFront cache
    print("\nInvalidating CloudFront cache...")
    try:
        invalidation_id = invalidate_cloudfront(distribution_id)
        print(f"✅ CloudFront cache invalidation created: {invalidation_id}")
    except Exception as e:
        print(f"❌ Error invalidating CloudFront cache: {e}")
        return 1
    
    print("\n" + "=" * 50)
    print("✅ Frontend deployment completed successfully!")
    print(f"\nYour application is available at:")
    print(f"  {cloudfront_url}")
    print("\nNote: CloudFront cache invalidation may take a few minutes to complete.")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
