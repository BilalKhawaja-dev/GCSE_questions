#!/bin/bash

# GCSE Question Generator - Lambda Deployment Script
# This script packages Lambda functions and updates Terraform configuration

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project paths
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TERRAFORM_DIR="$PROJECT_ROOT/terraform"
SCRIPTS_DIR="$PROJECT_ROOT/scripts"

echo -e "${BLUE}GCSE Question Generator - Lambda Deployment${NC}"
echo "=================================================="
echo "Project root: $PROJECT_ROOT"
echo "Terraform dir: $TERRAFORM_DIR"
echo ""

# Function to print status messages
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Step 1: Package Lambda functions
print_info "Step 1: Packaging Lambda functions..."
cd "$PROJECT_ROOT"

if ! python3 "$SCRIPTS_DIR/package_lambda.py"; then
    print_error "Lambda packaging failed"
    exit 1
fi

print_status "Lambda functions packaged successfully"
echo ""

# Step 2: Check if Terraform is initialized
print_info "Step 2: Checking Terraform initialization..."
cd "$TERRAFORM_DIR"

if [ ! -d ".terraform" ]; then
    print_warning "Terraform not initialized. Running terraform init..."
    if ! terraform init; then
        print_error "Terraform initialization failed"
        exit 1
    fi
    print_status "Terraform initialized"
else
    print_status "Terraform already initialized"
fi
echo ""

# Step 3: Validate Terraform configuration
print_info "Step 3: Validating Terraform configuration..."
if ! terraform validate; then
    print_error "Terraform validation failed"
    exit 1
fi
print_status "Terraform configuration is valid"
echo ""

# Step 4: Plan Terraform changes
print_info "Step 4: Planning Terraform changes..."
if ! terraform plan -var-file="environments/dev.tfvars" -out=tfplan; then
    print_error "Terraform planning failed"
    exit 1
fi
print_status "Terraform plan created successfully"
echo ""

# Step 5: Ask user for confirmation
print_warning "Review the Terraform plan above."
read -p "Do you want to apply these changes? (y/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_info "Deployment cancelled by user"
    exit 0
fi

# Step 6: Apply Terraform changes
print_info "Step 6: Applying Terraform changes..."
if ! terraform apply tfplan; then
    print_error "Terraform apply failed"
    exit 1
fi
print_status "Infrastructure deployed successfully"
echo ""

# Step 7: Upload Lambda package to S3
print_info "Step 7: Uploading Lambda package to S3..."
cd "$PROJECT_ROOT"

if ! python3 "$SCRIPTS_DIR/upload_lambda_package.py"; then
    print_error "Lambda package upload failed"
    exit 1
fi
print_status "Lambda package uploaded successfully"
echo ""

# Step 8: Update Lambda functions with new code
print_info "Step 8: Updating Lambda functions..."
cd "$TERRAFORM_DIR"

# Get the bucket name from Terraform outputs
BUCKET_NAME=$(terraform output -raw lambda_packages_bucket_name 2>/dev/null || echo "")

if [ -z "$BUCKET_NAME" ]; then
    print_error "Could not get Lambda packages bucket name from Terraform outputs"
    exit 1
fi

print_info "Using deployment bucket: $BUCKET_NAME"

# Update Lambda functions to use the new package
print_info "Triggering Lambda function updates..."

# Force Lambda functions to update by touching the Terraform resources
if ! terraform apply -target=module.api.aws_lambda_function.interpret_lambda -target=module.api.aws_lambda_function.generate_lambda -var-file="environments/dev.tfvars" -auto-approve; then
    print_error "Lambda function update failed"
    exit 1
fi

print_status "Lambda functions updated successfully"
echo ""

# Step 9: Verify deployment
print_info "Step 9: Verifying deployment..."

# Get Lambda function names
INTERPRET_LAMBDA=$(terraform output -raw interpret_lambda_name 2>/dev/null || echo "")
GENERATE_LAMBDA=$(terraform output -raw generate_lambda_name 2>/dev/null || echo "")

if [ -n "$INTERPRET_LAMBDA" ]; then
    print_status "InterpretLambda deployed: $INTERPRET_LAMBDA"
else
    print_warning "Could not verify InterpretLambda deployment"
fi

if [ -n "$GENERATE_LAMBDA" ]; then
    print_status "GenerateLambda deployed: $GENERATE_LAMBDA"
else
    print_warning "Could not verify GenerateLambda deployment"
fi

# Get API Gateway URL
API_URL=$(terraform output -raw api_gateway_url 2>/dev/null || echo "")
if [ -n "$API_URL" ]; then
    print_status "API Gateway URL: $API_URL"
else
    print_warning "Could not get API Gateway URL"
fi

echo ""
echo "=================================================="
print_status "Lambda deployment completed successfully!"
echo ""
print_info "Deployment Summary:"
echo "  • Lambda package size: $(ls -lh $PROJECT_ROOT/terraform/lambda-package/lambda-functions.zip | awk '{print $5}')"
echo "  • Deployment bucket: $BUCKET_NAME"
echo "  • InterpretLambda: $INTERPRET_LAMBDA"
echo "  • GenerateLambda: $GENERATE_LAMBDA"
if [ -n "$API_URL" ]; then
    echo "  • API Gateway: $API_URL"
fi
echo ""
print_info "Next steps:"
echo "  1. Run integration tests to verify functionality"
echo "  2. Test API endpoints with sample requests"
echo "  3. Monitor CloudWatch logs for any issues"
echo "  4. Proceed with task 13.3 (End-to-end integration tests)"