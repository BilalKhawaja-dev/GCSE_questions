#!/usr/bin/env python3
"""
Simple Upload Interface for GCSE Content

This script provides an easy way to upload your PDFs and content
to the AI knowledge base.
"""

import os
import sys
from pathlib import Path

def main():
    print("🎓 GCSE AI Knowledge Base Upload Interface")
    print("=" * 60)
    
    print("\n📁 Where to put your PDFs:")
    print("   1. Create a folder: mkdir ~/gcse_content")
    print("   2. Organize your PDFs in subfolders:")
    print("      ~/gcse_content/")
    print("      ├── specifications/")
    print("      ├── past_papers/")
    print("      └── mark_schemes/")
    
    print("\n🚀 How to upload:")
    print("   1. Basic upload:")
    print("      python bulk_pdf_upload_system.py ~/gcse_content")
    print("   2. With progress tracking:")
    print("      python bulk_pdf_upload_system.py ~/gcse_content --output-report report.json")
    
    print("\n📊 S3 Upload Destinations:")
    print("   • Specifications: gcse-specifications-prod-1a64dc99")
    print("   • Examples: gcse-examples-prod-1a64dc99")
    print("   • AI Instructions: gcse-ai-instructions-prod")
    
    print("\n✅ Verify Upload:")
    print("   python check_s3_content.py")
    print("   python validate_ai_integration.py")
    
    print("\n💡 Need help? Check:")
    print("   • pdf_collection_guide.md - Where to find PDFs")
    print("   • content_upload_guidelines.json - Detailed instructions")
    
    # Interactive upload option
    pdf_dir = input("\n📂 Enter path to your PDF directory (or press Enter to skip): ").strip()
    
    if pdf_dir and os.path.exists(pdf_dir):
        print(f"\n🔄 Starting upload from: {pdf_dir}")
        os.system(f"python bulk_pdf_upload_system.py {pdf_dir} --output-report upload_report.json")
        print("\n✅ Upload complete! Check upload_report.json for details.")
    else:
        print("\n👋 No upload performed. Run this script again when ready!")

if __name__ == "__main__":
    main()
