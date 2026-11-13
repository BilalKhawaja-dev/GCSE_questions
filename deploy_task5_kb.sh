#!/bin/bash

echo "🚀 Task 5: Deploying Bedrock Knowledge Base Integration"
echo "========================================================"

# Step 1: Deploy updated Lambda with KB integration
echo ""
echo "📦 Step 1: Deploying Lambda with KB integration..."
python scripts/deploy_parallel_optimization.py

if [ $? -ne 0 ]; then
    echo "❌ Lambda deployment failed"
    exit 1
fi

# Step 2: Update Lambda environment variables
echo ""
echo "🔧 Step 2: Configuring Lambda environment..."

# Note: KB_ID will be added after Terraform creates the KB
python -c "
import boto3

lambda_client = boto3.client('lambda')

# Update async worker
lambda_client.update_function_configuration(
    FunctionName='gcse-async-worker-lambda-prod',
    Environment={
        'Variables': {
            **lambda_client.get_function_configuration(
                FunctionName='gcse-async-worker-lambda-prod'
            )['Environment']['Variables'],
            'KNOWLEDGE_BASE_ENABLED': 'false'  # Will enable after KB is created
        }
    }
)

print('✅ Lambda environment configured')
"

echo ""
echo "========================================================"
echo "✅ Code Deployment Complete!"
echo ""
echo "📋 Next Steps:"
echo "1. Deploy Terraform infrastructure:"
echo "   cd terraform && terraform apply"
echo ""
echo "2. After Terraform completes, get the KB ID:"
echo "   terraform output knowledge_base_id"
echo ""
echo "3. Update Lambda with KB ID:"
echo "   aws lambda update-function-configuration \\"
echo "     --function-name gcse-async-worker-lambda-prod \\"
echo "     --environment Variables='{...KNOWLEDGE_BASE_ID=<kb-id>,KNOWLEDGE_BASE_ENABLED=true}'"
echo ""
echo "4. Test by generating questions - they should use PDF content!"
echo ""
