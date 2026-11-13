#!/usr/bin/env python3
import boto3
import json

lambda_client = boto3.client('lambda')

# Get current env vars
response = lambda_client.get_function_configuration(FunctionName='gcse-async-worker-lambda-prod')
current_env = response['Environment']['Variables']

# Add KB variables
updated_env = {
    **current_env,
    'KNOWLEDGE_BASE_ID': 'LGKVLOAVEZ',
    'KNOWLEDGE_BASE_ENABLED': 'true'
}

# Update Lambda
lambda_client.update_function_configuration(
    FunctionName='gcse-async-worker-lambda-prod',
    Environment={'Variables': updated_env}
)

print("✅ Updated gcse-async-worker-lambda-prod with KB ID: LGKVLOAVEZ")
print("✅ Knowledge Base is now ENABLED")
print("\n🎉 The AI will now use your uploaded June 2017 QP PDF!")
print("   Try generating questions - they should match Edexcel style!")
