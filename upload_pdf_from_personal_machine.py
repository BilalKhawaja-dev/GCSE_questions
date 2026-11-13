#!/usr/bin/env python3
"""
Upload PDFs to GCSE Question Generator from your personal machine.
No dev desktop needed - just AWS credentials!
"""

import boto3
import sys
import os
from pathlib import Path

# Configuration
BUCKET_NAME = "gcse-knowledge-base-prod"  # Update if different
REGION = "eu-west-2"

def upload_pdf(file_path: str):
    """Upload a PDF file to S3 knowledge base."""
    
    file_path = Path(file_path)
    
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return False
    
    if file_path.suffix.lower() not in ['.pdf', '.json']:
        print(f"❌ Only PDF and JSON files supported")
        return False
    
    print(f"📤 Uploading {file_path.name}...")
    
    try:
        s3_client = boto3.client('s3', region_name=REGION)
        
        # Determine folder based on file type
        if 'mark' in file_path.name.lower() or 'scheme' in file_path.name.lower():
            folder = 'mark-schemes'
        elif 'spec' in file_path.name.lower():
            folder = 'specifications'
        elif 'paper' in file_path.name.lower() or 'exam' in file_path.name.lower():
            folder = 'past-papers'
        else:
            folder = 'general'
        
        # Upload to S3
        key = f"{folder}/{file_path.name}"
        
        s3_client.upload_file(
            str(file_path),
            BUCKET_NAME,
            key,
            ExtraArgs={'ContentType': 'application/pdf' if file_path.suffix == '.pdf' else 'application/json'}
        )
        
        print(f"✅ Uploaded successfully!")
        print(f"   Bucket: {BUCKET_NAME}")
        print(f"   Key: {key}")
        print(f"   The AI will use this content for future questions.")
        
        return True
        
    except Exception as e:
        print(f"❌ Upload failed: {str(e)}")
        return False

def main():
    """Main function."""
    
    print("🎓 GCSE Question Generator - PDF Upload Tool")
    print("=" * 50)
    
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python upload_pdf_from_personal_machine.py <file.pdf>")
        print("\nExamples:")
        print("  python upload_pdf_from_personal_machine.py edexcel-paper-1.pdf")
        print("  python upload_pdf_from_personal_machine.py mark-scheme.pdf")
        print("  python upload_pdf_from_personal_machine.py specification.pdf")
        print("\nMultiple files:")
        print("  python upload_pdf_from_personal_machine.py file1.pdf file2.pdf file3.pdf")
        return
    
    # Check AWS credentials
    try:
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print(f"✅ AWS Account: {identity['Account']}")
        print()
    except Exception as e:
        print(f"❌ AWS credentials not configured")
        print(f"   Run: aws configure")
        print(f"   Or set: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY")
        return
    
    # Upload all files
    files = sys.argv[1:]
    success_count = 0
    
    for file_path in files:
        if upload_pdf(file_path):
            success_count += 1
        print()
    
    print("=" * 50)
    print(f"✅ Uploaded {success_count}/{len(files)} files successfully")
    
    if success_count > 0:
        print("\n💡 The AI will now use this content to generate better questions!")
        print("   Try generating questions and see the improved quality.")

if __name__ == "__main__":
    main()
