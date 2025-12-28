# GCSE Question Generator - Deployment Scripts

This directory contains scripts for packaging and deploying the Lambda functions for the GCSE Question Generator.

## Scripts Overview

### 1. `package_lambda.py`
Creates a deployment package for AWS Lambda functions.

**What it does:**
- Installs production dependencies in a temporary directory
- Copies source code to the package directory
- Creates a zip file for deployment
- Validates the package contents

**Usage:**
```bash
python3 scripts/package_lambda.py
```

**Output:**
- Creates `terraform/lambda-package/lambda-functions.zip`
- Package size: ~14MB (includes boto3, botocore, jsonschema, and source code)

### 2. `test_lambda_package.py`
Tests the Lambda deployment package locally.

**What it does:**
- Extracts and validates the deployment package
- Tests imports of Lambda handlers and dependencies
- Runs basic functionality tests without AWS calls

**Usage:**
```bash
python3 scripts/test_lambda_package.py
```

### 3. `upload_lambda_package.py`
Uploads the Lambda package to S3 deployment bucket.

**What it does:**
- Gets deployment bucket name from Terraform outputs
- Uploads the package to S3 with encryption
- Verifies the upload was successful

**Usage:**
```bash
# Automatic (uses Terraform outputs)
python3 scripts/upload_lambda_package.py

# Manual bucket specification
python3 scripts/upload_lambda_package.py <bucket-name>
```

### 4. `deploy_lambda.sh`
Complete deployment script that orchestrates the entire process.

**What it does:**
- Packages Lambda functions
- Validates Terraform configuration
- Plans and applies infrastructure changes
- Uploads Lambda package to S3
- Updates Lambda functions with new code
- Verifies deployment

**Usage:**
```bash
./scripts/deploy_lambda.sh
```

## Deployment Process

### Prerequisites
1. AWS credentials configured (`aws configure` or environment variables)
2. Terraform installed and initialized
3. Python 3.11+ with required dependencies

### Step-by-Step Deployment

1. **Package Lambda functions:**
   ```bash
   python3 scripts/package_lambda.py
   ```

2. **Test the package (optional but recommended):**
   ```bash
   python3 scripts/test_lambda_package.py
   ```

3. **Deploy infrastructure and Lambda functions:**
   ```bash
   ./scripts/deploy_lambda.sh
   ```

   This script will:
   - Show you a Terraform plan
   - Ask for confirmation before applying changes
   - Deploy infrastructure and upload Lambda code
   - Verify the deployment

### Manual Deployment (Alternative)

If you prefer manual control:

1. **Package functions:**
   ```bash
   python3 scripts/package_lambda.py
   ```

2. **Apply Terraform (creates S3 bucket):**
   ```bash
   cd terraform
   terraform plan -var-file="environments/dev.tfvars"
   terraform apply -var-file="environments/dev.tfvars"
   ```

3. **Upload package:**
   ```bash
   python3 scripts/upload_lambda_package.py
   ```

4. **Update Lambda functions:**
   ```bash
   cd terraform
   terraform apply -target=module.api.aws_lambda_function.interpret_lambda \
                   -target=module.api.aws_lambda_function.generate_lambda \
                   -var-file="environments/dev.tfvars" \
                   -auto-approve
   ```

## Package Contents

The Lambda deployment package includes:

### Production Dependencies
- `boto3` - AWS SDK for Python
- `botocore` - Low-level AWS service access
- `jsonschema` - JSON schema validation
- `requests` - HTTP library

### Source Code Structure
```
src/
├── lambda_handlers/
│   ├── interpret_lambda.py    # Query interpretation handler
│   └── generate_lambda.py     # Question generation handler
├── models/
│   ├── query_intent.py        # Query intent data model
│   ├── question.py            # Question data model
│   ├── mark_scheme.py         # Mark scheme data model
│   └── specification_content.py
├── services/
│   ├── bedrock_service.py     # AWS Bedrock integration
│   ├── content_retrieval_service.py
│   └── version_management_service.py
└── utils/
    ├── validation.py          # Input validation
    ├── security.py            # Security utilities
    ├── cache.py               # Caching utilities
    └── constants.py           # Application constants
```

## Troubleshooting

### Common Issues

1. **Package too large (>50MB)**
   - The current package is ~14MB, well within Lambda limits
   - If it grows, consider using Lambda layers for dependencies

2. **Import errors in Lambda**
   - Run `test_lambda_package.py` to validate imports locally
   - Check that all required dependencies are in `requirements.txt`

3. **S3 upload fails**
   - Verify AWS credentials are configured
   - Check that Terraform has been applied (creates S3 bucket)
   - Ensure you have S3 permissions

4. **Terraform apply fails**
   - Check that the Lambda package exists in S3
   - Verify IAM permissions for Lambda and S3
   - Review Terraform plan for resource conflicts

### Validation Commands

```bash
# Test package locally
python3 scripts/test_lambda_package.py

# Check Terraform configuration
cd terraform && terraform validate

# Verify S3 upload
aws s3 ls s3://your-bucket-name/lambda-functions.zip

# Test Lambda function (after deployment)
aws lambda invoke --function-name gcse-interpret-lambda-dev \
                  --payload '{"body": "{\"query\": \"test\"}"}' \
                  response.json
```

## Next Steps

After successful deployment:

1. **Run integration tests** (Task 13.3)
2. **Perform load testing** (Task 13.4)
3. **Monitor CloudWatch logs** for any issues
4. **Test API endpoints** with sample requests

## Security Notes

- Lambda packages are encrypted at rest in S3 (AES256)
- IAM roles follow least-privilege principle
- API Gateway has rate limiting and authentication
- All logs are retained for 30 days in CloudWatch