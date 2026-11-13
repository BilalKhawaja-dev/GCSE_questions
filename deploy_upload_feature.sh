#!/bin/bash

echo "📤 Deploying Upload Feature"
echo "============================"

# 1. Package and deploy upload Lambda
echo "📦 Packaging upload Lambda..."
python scripts/deploy_parallel_optimization.py

# 2. Apply Terraform changes for upload endpoint
echo ""
echo "🔧 Applying Terraform changes..."
cd terraform
terraform apply -target=module.api.aws_api_gateway_resource.upload_resource \
                -target=module.api.aws_api_gateway_resource.upload_presigned_resource \
                -target=module.api.aws_lambda_function.upload_lambda \
                -target=module.api.aws_api_gateway_method.upload_presigned_post \
                -target=module.api.aws_api_gateway_method.upload_presigned_options \
                -target=module.api.aws_api_gateway_integration.upload_presigned_integration \
                -auto-approve

if [ $? -eq 0 ]; then
    echo "✅ Terraform applied successfully"
else
    echo "❌ Terraform apply failed"
    exit 1
fi

# 3. Redeploy API Gateway
echo ""
echo "🔄 Redeploying API Gateway..."
terraform apply -target=module.api.aws_api_gateway_deployment.gcse_api_deployment -auto-approve

echo ""
echo "============================"
echo "✅ Upload Feature Deployed!"
echo ""
echo "Test it at: https://your-app.com/upload"
echo ""
