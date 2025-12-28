# GCSE PDF Collection and Upload Guide

## Overview
This guide explains how to collect GCSE PDF papers and use the bulk upload system to expand your content library.

## Step 1: Collect GCSE PDF Papers

### Recommended Sources
1. **Edexcel/Pearson Official Site**
   - Visit: https://qualifications.pearson.com/en/qualifications/edexcel-gcse/mathematics-2015.html
   - Download past papers, mark schemes, and specifications
   - Look for: "Past papers and mark schemes"

2. **AQA Official Site**
   - Visit: https://www.aqa.org.uk/subjects/mathematics/gcse/mathematics-8300/past-papers-and-mark-schemes
   - Download recent papers (2019-2024)

3. **OCR Official Site**
   - Visit: https://www.ocr.org.uk/qualifications/gcse/mathematics-j560-from-2015/
   - Download past papers and specifications

4. **Educational Resource Sites**
   - MathsGenie: https://www.mathsgenie.co.uk/gcse.html
   - ExamSolutions: https://www.examsolutions.net/gcse-maths/
   - TES Resources: https://www.tes.com/teaching-resources/gcse-maths

### What to Collect
- **Specification Documents**: Core curriculum content
- **Past Papers**: Foundation and Higher tier
- **Mark Schemes**: Detailed marking criteria
- **Sample Assessment Materials**: Official examples
- **Topic-Specific Papers**: If available

### Recommended File Organization
Create a directory structure like this:
```
gcse_pdfs/
├── edexcel/
│   ├── specifications/
│   ├── past_papers/
│   └── mark_schemes/
├── aqa/
│   ├── specifications/
│   ├── past_papers/
│   └── mark_schemes/
└── ocr/
    ├── specifications/
    ├── past_papers/
    └── mark_schemes/
```

## Step 2: Prepare Your Local Directory

1. **Create a dedicated folder**:
   ```bash
   mkdir ~/gcse_pdfs
   cd ~/gcse_pdfs
   ```

2. **Download PDFs into organized subfolders**:
   - Group by exam board (Edexcel, AQA, OCR)
   - Separate specifications from past papers
   - Use descriptive filenames

3. **Verify PDF quality**:
   - Ensure PDFs are text-searchable (not just scanned images)
   - Check that mathematical notation is clear
   - Remove any corrupted or incomplete files

## Step 3: Use the Bulk Upload System

### Basic Usage
```bash
# Upload all PDFs from a directory
python bulk_pdf_upload_system.py ~/gcse_pdfs

# With custom settings
python bulk_pdf_upload_system.py ~/gcse_pdfs \
  --batch-size 3 \
  --output-report upload_report.json
```

### Advanced Options
```bash
# Full command with all options
python bulk_pdf_upload_system.py ~/gcse_pdfs \
  --batch-size 5 \
  --specifications-bucket gcse-specifications-prod-1a64dc99 \
  --examples-bucket gcse-examples-prod-1a64dc99 \
  --aws-region eu-west-2 \
  --output-report detailed_report.json
```

### What the System Does
1. **Discovers PDFs**: Recursively finds all PDF files in your directory
2. **Categorizes Content**: Organizes by topic (Number, Algebra, Geometry, etc.)
3. **Processes in Parallel**: Handles multiple PDFs simultaneously
4. **Extracts Content**: Parses text and structures it for the AI system
5. **Uploads to S3**: Stores processed content in the correct buckets
6. **Validates**: Ensures content is accessible to the question generator

## Step 4: Verify Upload Success

### Check Upload Results
```bash
# Check S3 content after upload
python check_s3_content.py

# Validate AI integration with new content
python validate_ai_integration.py
```

### Expected Improvements
After successful upload, you should see:
- More topic coverage (all 6 topics: Number, Algebra, Geometry, Statistics, Probability, Ratio)
- Increased content variety within each topic
- Better question generation success rates
- Reduced reliance on cached responses

## Step 5: Test the System

### Test Different Topics
Try generating questions for various topics to ensure the new content is working:

```bash
# Test via API or frontend
curl -X POST "https://your-api-gateway-url/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Geometry",
    "tier": "Foundation", 
    "count": 3
  }'
```

## Troubleshooting

### Common Issues
1. **PDF Parsing Errors**
   - Ensure PDFs contain searchable text
   - Check for password-protected files
   - Verify file integrity

2. **Upload Failures**
   - Check AWS credentials
   - Verify S3 bucket permissions
   - Ensure sufficient storage quota

3. **Content Not Appearing**
   - Run cache clearing script: `python clear_all_caches.py`
   - Check S3 bucket structure
   - Verify Lambda function permissions

### Getting Help
- Check the upload report JSON file for detailed error information
- Review CloudWatch logs for Lambda function errors
- Use the validation scripts to identify specific issues

## Recommended Workflow

1. **Start Small**: Begin with 10-15 high-quality PDFs
2. **Test Upload**: Verify the system works with your sample
3. **Scale Up**: Gradually add more PDFs in batches
4. **Monitor Performance**: Check question generation quality
5. **Iterate**: Refine your PDF collection based on results

## File Naming Best Practices

Use descriptive filenames that help with categorization:
- `edexcel_gcse_maths_specification_2024.pdf`
- `aqa_foundation_paper1_june2023.pdf`
- `ocr_higher_statistics_markscheme_nov2022.pdf`

This helps the system automatically categorize content correctly.