#!/bin/bash
# Terraform initialization script for GCSE Question Generator

set -e

ENVIRONMENT=${1:-prod}
AWS_REGION="eu-west-2"

echo "Initializing Terraform for GCSE Question Generator..."
echo "Environment: $ENVIRONMENT"
echo "Region: $AWS_REGION"

# Check if AWS CLI is configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "Error: AWS CLI not configured. Please run 'aws configure' first."
    exit 1
fi

# Check if required environment variables are set
if [ -z "$ALERT_EMAIL" ]; then
    echo "Warning: ALERT_EMAIL environment variable not set. Using default."
    export ALERT_EMAIL="admin@example.com"
fi

# Create S3 bucket for Terraform state if it doesn't exist
BUCKET_NAME="gcse-terraform-state"
if ! aws s3 ls "s3://$BUCKET_NAME" > /dev/null 2>&1; then
    echo "Creating Terraform state bucket: $BUCKET_NAME"
    aws s3 mb "s3://$BUCKET_NAME" --region $AWS_REGION
    
    # Enable versioning
    aws s3api put-bucket-versioning \
        --bucket $BUCKET_NAME \
        --versioning-configuration Status=Enabled
    
    # Enable encryption
    aws s3api put-bucket-encryption \
        --bucket $BUCKET_NAME \
        --server-side-encryption-configuration '{
            "Rules": [
                {
                    "ApplyServerSideEncryptionByDefault": {
                        "SSEAlgorithm": "AES256"
                    }
                }
            ]
        }'
    
    # Block public access
    aws s3api put-public-access-block \
        --bucket $BUCKET_NAME \
        --public-access-block-configuration \
        BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
else
    echo "Terraform state bucket already exists: $BUCKET_NAME"
fi

# Create DynamoDB table for state locking if it doesn't exist
TABLE_NAME="terraform-locks"
if ! aws dynamodb describe-table --table-name $TABLE_NAME > /dev/null 2>&1; then
    echo "Creating Terraform state lock table: $TABLE_NAME"
    aws dynamodb create-table \
        --table-name $TABLE_NAME \
        --attribute-definitions AttributeName=LockID,AttributeType=S \
        --key-schema AttributeName=LockID,KeyType=HASH \
        --billing-mode PAY_PER_REQUEST \
        --region $AWS_REGION
    
    # Wait for table to be active
    echo "Waiting for DynamoDB table to be active..."
    aws dynamodb wait table-exists --table-name $TABLE_NAME
else
    echo "Terraform state lock table already exists: $TABLE_NAME"
fi

# Initialize Terraform
echo "Initializing Terraform..."
terraform init \
    -backend-config="bucket=$BUCKET_NAME" \
    -backend-config="key=$ENVIRONMENT/terraform.tfstate" \
    -backend-config="region=$AWS_REGION" \
    -backend-config="dynamodb_table=$TABLE_NAME"

echo "Terraform initialization complete!"
echo ""
echo "Next steps:"
echo "1. Review the configuration: terraform plan -var-file=environments/$ENVIRONMENT.tfvars"
echo "2. Apply the changes: terraform apply -var-file=environments/$ENVIRONMENT.tfvars"
echo ""
echo "Make sure to update the alert_email in environments/$ENVIRONMENT.tfvars before applying!"