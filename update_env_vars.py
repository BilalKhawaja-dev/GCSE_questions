#!/usr/bin/env python3
import boto3
import json

def update_lambda_env_vars():
    lambda_client = boto3.client('lambda')
    
    # Update async worker
    try:
        response = lambda_client.get_function_configuration(FunctionName='gcse-async-worker-lambda-prod')
        current_env = response.get('Environment', {}).get('Variables', {})
        
        # Add parallel processing variables
        updated_env = {
            **current_env,
            'PARALLEL_PROCESSING_ENABLED': 'true',
            'PARALLEL_ASYNC_QUEUE_URL': 'https://sqs.eu-west-2.amazonaws.com/981686514879/gcse-async-generation-queue-prod',
            'MAX_PARALLEL_WORKERS': '5'
        }
        
        lambda_client.update_function_configuration(
            FunctionName='gcse-async-worker-lambda-prod',
            Environment={'Variables': updated_env}
        )
        print("✅ Updated gcse-async-worker-lambda-prod environment variables")
        
    except Exception as e:
        print(f"❌ Failed to update async worker: {e}")
    
    # Update generate lambda
    try:
        response = lambda_client.get_function_configuration(FunctionName='gcse-generate-lambda-prod')
        current_env = response.get('Environment', {}).get('Variables', {})
        
        # Add parallel processing variables
        updated_env = {
            **current_env,
            'PARALLEL_PROCESSING_ENABLED': 'true',
            'PARALLEL_ASYNC_QUEUE_URL': 'https://sqs.eu-west-2.amazonaws.com/981686514879/gcse-async-generation-queue-prod'
        }
        
        lambda_client.update_function_configuration(
            FunctionName='gcse-generate-lambda-prod',
            Environment={'Variables': updated_env}
        )
        print("✅ Updated gcse-generate-lambda-prod environment variables")
        
    except Exception as e:
        print(f"❌ Failed to update generate lambda: {e}")

if __name__ == "__main__":
    update_lambda_env_vars()