#!/usr/bin/env python3
"""Quick deploy upload Lambda and configure API Gateway."""

import boto3
import json
import zipfile
import tempfile
import shutil
from pathlib import Path

def create_upload_lambda_package():
    """Create Lambda package."""
    with tempfile.TemporaryDirectory() as temp_dir:
        package_dir = Path(temp_dir) / "package"
        package_dir.mkdir()
        
        # Copy source files
        shutil.copytree("src", package_dir / "src")
        
        # Create zip
        zip_path = Path("upload-lambda.zip")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in package_dir.rglob("*"):
                if file_path.is_file():
                    zipf.write(file_path, file_path.relative_to(package_dir))
        
        return zip_path

def deploy_upload_lambda():
    """Deploy or update upload Lambda."""
    lambda_client = boto3.client('lambda')
    
    print("📦 Creating Lambda package...")
    zip_path = create_upload_lambda_package()
    
    function_name = "gcse-upload-lambda-prod"
    
    try:
        # Check if function exists
        lambda_client.get_function(FunctionName=function_name)
        
        # Update existing function
        print(f"🔄 Updating {function_name}...")
        with open(zip_path, 'rb') as f:
            lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=f.read()
            )
        print(f"✅ Updated {function_name}")
        
    except lambda_client.exceptions.ResourceNotFoundException:
        # Create new function
        print(f"🆕 Creating {function_name}...")
        
        # Get IAM role (reuse existing Lambda role)
        role_arn = "arn:aws:iam::981686514879:role/gcse-generate-lambda-role-prod"
        
        with open(zip_path, 'rb') as f:
            lambda_client.create_function(
                FunctionName=function_name,
                Runtime='python3.11',
                Role=role_arn,
                Handler='src.lambda_handlers.upload_lambda.lambda_handler',
                Code={'ZipFile': f.read()},
                Timeout=30,
                MemorySize=512,
                Environment={
                    'Variables': {
                        'ENVIRONMENT': 'prod',
                        'REGION': 'eu-west-2',
                        'KNOWLEDGE_BUCKET_NAME': 'gcse-knowledge-base-prod'
                    }
                }
            )
        print(f"✅ Created {function_name}")
    
    # Clean up
    zip_path.unlink()
    
    return function_name

def configure_api_gateway(function_name):
    """Add upload endpoint to API Gateway."""
    apigw = boto3.client('apigateway')
    lambda_client = boto3.client('lambda')
    
    # Get API Gateway ID
    apis = apigw.get_rest_apis()
    api = next((a for a in apis['items'] if 'gcse' in a['name'].lower()), None)
    
    if not api:
        print("❌ Could not find GCSE API Gateway")
        return False
    
    api_id = api['id']
    print(f"✅ Found API: {api['name']} ({api_id})")
    
    # Get root resource
    resources = apigw.get_resources(restApiId=api_id)
    root = next(r for r in resources['items'] if r['path'] == '/')
    
    # Create /upload resource
    try:
        upload_resource = apigw.create_resource(
            restApiId=api_id,
            parentId=root['id'],
            pathPart='upload'
        )
        print(f"✅ Created /upload resource")
    except apigw.exceptions.ConflictException:
        upload_resource = next(r for r in resources['items'] if r['path'] == '/upload')
        print(f"✅ /upload resource already exists")
    
    # Create /upload/presigned resource
    try:
        presigned_resource = apigw.create_resource(
            restApiId=api_id,
            parentId=upload_resource['id'],
            pathPart='presigned'
        )
        print(f"✅ Created /upload/presigned resource")
    except apigw.exceptions.ConflictException:
        presigned_resource = next(r for r in resources['items'] if r['path'] == '/upload/presigned')
        print(f"✅ /upload/presigned resource already exists")
    
    # Create POST method
    try:
        apigw.put_method(
            restApiId=api_id,
            resourceId=presigned_resource['id'],
            httpMethod='POST',
            authorizationType='NONE'
        )
        print(f"✅ Created POST method")
    except apigw.exceptions.ConflictException:
        print(f"✅ POST method already exists")
    
    # Create OPTIONS method for CORS
    try:
        apigw.put_method(
            restApiId=api_id,
            resourceId=presigned_resource['id'],
            httpMethod='OPTIONS',
            authorizationType='NONE'
        )
        print(f"✅ Created OPTIONS method")
    except apigw.exceptions.ConflictException:
        print(f"✅ OPTIONS method already exists")
    
    # Configure Lambda integration
    lambda_arn = lambda_client.get_function(FunctionName=function_name)['Configuration']['FunctionArn']
    region = boto3.session.Session().region_name
    
    apigw.put_integration(
        restApiId=api_id,
        resourceId=presigned_resource['id'],
        httpMethod='POST',
        type='AWS_PROXY',
        integrationHttpMethod='POST',
        uri=f'arn:aws:apigateway:{region}:lambda:path/2015-03-31/functions/{lambda_arn}/invocations'
    )
    print(f"✅ Configured Lambda integration")
    
    # Configure CORS for OPTIONS
    apigw.put_integration(
        restApiId=api_id,
        resourceId=presigned_resource['id'],
        httpMethod='OPTIONS',
        type='MOCK',
        requestTemplates={'application/json': '{"statusCode": 200}'}
    )
    
    try:
        apigw.put_method_response(
            restApiId=api_id,
            resourceId=presigned_resource['id'],
            httpMethod='OPTIONS',
            statusCode='200',
            responseParameters={
                'method.response.header.Access-Control-Allow-Headers': True,
                'method.response.header.Access-Control-Allow-Methods': True,
                'method.response.header.Access-Control-Allow-Origin': True
            }
        )
    except apigw.exceptions.ConflictException:
        pass
    
    try:
        apigw.put_integration_response(
            restApiId=api_id,
            resourceId=presigned_resource['id'],
            httpMethod='OPTIONS',
            statusCode='200',
            responseParameters={
                'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Api-Key'",
                'method.response.header.Access-Control-Allow-Methods': "'POST,OPTIONS'",
                'method.response.header.Access-Control-Allow-Origin': "'https://d2ckebo851nz2l.cloudfront.net'"
            }
        )
    except apigw.exceptions.ConflictException:
        pass
    
    print(f"✅ Configured CORS")
    
    # Add Lambda permission
    account_id = boto3.client('sts').get_caller_identity()['Account']
    try:
        lambda_client.add_permission(
            FunctionName=function_name,
            StatementId='AllowAPIGatewayInvoke',
            Action='lambda:InvokeFunction',
            Principal='apigateway.amazonaws.com',
            SourceArn=f'arn:aws:execute-api:{region}:{account_id}:{api_id}/*/*'
        )
        print(f"✅ Added Lambda permission")
    except lambda_client.exceptions.ResourceConflictException:
        print(f"✅ Lambda permission already exists")
    
    # Deploy API
    deployment = apigw.create_deployment(
        restApiId=api_id,
        stageName='prod'
    )
    print(f"✅ Deployed API Gateway")
    
    return True

def main():
    print("🚀 Deploying Upload Feature")
    print("=" * 50)
    
    # Deploy Lambda
    function_name = deploy_upload_lambda()
    
    # Configure API Gateway
    print("\n🔧 Configuring API Gateway...")
    if configure_api_gateway(function_name):
        print("\n" + "=" * 50)
        print("✅ Upload Feature Deployed!")
        print("\n📤 Users can now upload PDFs at:")
        print("   https://your-app.com/upload")
        print("\n💡 The web interface is ready for resource gathering!")
    else:
        print("\n❌ API Gateway configuration failed")

if __name__ == "__main__":
    main()
