#!/usr/bin/env python3
"""
Question Bank System Deployment Script

This script deploys the entire Question Verification System to AWS,
including all Terraform modules, Lambda functions, and initial setup.

Usage:
    python scripts/deploy_question_bank_system.py --environment prod
    python scripts/deploy_question_bank_system.py --environment staging --skip-tests
"""

import argparse
import subprocess
import sys
import time
import json
import boto3
from pathlib import Path
from typing import Dict, List, Tuple

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(message: str):
    """Print a formatted header message."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{message.center(80)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}\n")

def print_success(message: str):
    """Print a success message."""
    print(f"{Colors.OKGREEN}✓ {message}{Colors.ENDC}")

def print_error(message: str):
    """Print an error message."""
    print(f"{Colors.FAIL}✗ {message}{Colors.ENDC}")

def print_warning(message: str):
    """Print a warning message."""
    print(f"{Colors.WARNING}⚠ {message}{Colors.ENDC}")

def print_info(message: str):
    """Print an info message."""
    print(f"{Colors.OKBLUE}ℹ {message}{Colors.ENDC}")

def run_command(command: List[str], cwd: str = None, check: bool = True) -> Tuple[int, str, str]:
    """
    Run a shell command and return the result.
    
    Args:
        command: Command to run as list of strings
        cwd: Working directory
        check: Whether to raise exception on failure
        
    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    print_info(f"Running: {' '.join(command)}")
    
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=check
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return e.returncode, e.stdout, e.stderr

def check_prerequisites() -> bool:
    """Check that all required tools are installed."""
    print_header("Checking Prerequisites")
    
    required_tools = {
        'terraform': ['terraform', '--version'],
        'aws': ['aws', '--version'],
        'python': ['python3', '--version'],
        'npm': ['npm', '--version']
    }
    
    all_present = True
    for tool, command in required_tools.items():
        returncode, stdout, stderr = run_command(command, check=False)
        if returncode == 0:
            version = stdout.strip().split('\n')[0]
            print_success(f"{tool}: {version}")
        else:
            print_error(f"{tool}: Not found")
            all_present = False
    
    return all_present

def package_lambda_functions() -> bool:
    """Package Lambda functions for deployment."""
    print_header("Packaging Lambda Functions")
    
    try:
        # Run the package script
        returncode, stdout, stderr = run_command([
            'python3', 'scripts/package_lambda.py'
        ])
        
        if returncode == 0:
            print_success("Lambda functions packaged successfully")
            return True
        else:
            print_error(f"Failed to package Lambda functions: {stderr}")
            return False
    except Exception as e:
        print_error(f"Error packaging Lambda functions: {str(e)}")
        return False

def deploy_terraform(environment: str) -> bool:
    """Deploy Terraform infrastructure."""
    print_header(f"Deploying Terraform Infrastructure ({environment})")
    
    terraform_dir = Path('terraform')
    
    # Initialize Terraform
    print_info("Initializing Terraform...")
    returncode, stdout, stderr = run_command(
        ['terraform', 'init'],
        cwd=str(terraform_dir)
    )
    
    if returncode != 0:
        print_error(f"Terraform init failed: {stderr}")
        return False
    
    print_success("Terraform initialized")
    
    # Select workspace
    print_info(f"Selecting workspace: {environment}")
    returncode, stdout, stderr = run_command(
        ['terraform', 'workspace', 'select', environment],
        cwd=str(terraform_dir),
        check=False
    )
    
    if returncode != 0:
        # Workspace doesn't exist, create it
        print_info(f"Creating workspace: {environment}")
        returncode, stdout, stderr = run_command(
            ['terraform', 'workspace', 'new', environment],
            cwd=str(terraform_dir)
        )
        
        if returncode != 0:
            print_error(f"Failed to create workspace: {stderr}")
            return False
    
    print_success(f"Workspace selected: {environment}")
    
    # Plan
    print_info("Planning Terraform changes...")
    var_file = f"environments/{environment}.tfvars"
    returncode, stdout, stderr = run_command(
        ['terraform', 'plan', '-var-file', var_file, '-out', 'tfplan'],
        cwd=str(terraform_dir)
    )
    
    if returncode != 0:
        print_error(f"Terraform plan failed: {stderr}")
        return False
    
    print_success("Terraform plan completed")
    print(stdout)
    
    # Ask for confirmation
    response = input(f"\n{Colors.WARNING}Do you want to apply these changes? (yes/no): {Colors.ENDC}")
    if response.lower() != 'yes':
        print_warning("Deployment cancelled by user")
        return False
    
    # Apply
    print_info("Applying Terraform changes...")
    returncode, stdout, stderr = run_command(
        ['terraform', 'apply', 'tfplan'],
        cwd=str(terraform_dir)
    )
    
    if returncode != 0:
        print_error(f"Terraform apply failed: {stderr}")
        return False
    
    print_success("Terraform infrastructure deployed")
    
    return True

def get_terraform_outputs(environment: str) -> Dict:
    """Get Terraform outputs."""
    print_info("Retrieving Terraform outputs...")
    
    terraform_dir = Path('terraform')
    returncode, stdout, stderr = run_command(
        ['terraform', 'output', '-json'],
        cwd=str(terraform_dir)
    )
    
    if returncode != 0:
        print_error(f"Failed to get Terraform outputs: {stderr}")
        return {}
    
    try:
        outputs = json.loads(stdout)
        print_success("Terraform outputs retrieved")
        return outputs
    except json.JSONDecodeError as e:
        print_error(f"Failed to parse Terraform outputs: {str(e)}")
        return {}

def run_smoke_tests(environment: str, outputs: Dict) -> bool:
    """Run smoke tests to verify deployment."""
    print_header("Running Smoke Tests")
    
    # Test 1: Check DynamoDB tables exist
    print_info("Test 1: Checking DynamoDB tables...")
    dynamodb = boto3.client('dynamodb')
    
    required_tables = [
        'verified_question_bank',
        'rejected_questions',
        'question_bank_inventory'
    ]
    
    for table_name in required_tables:
        try:
            response = dynamodb.describe_table(TableName=f"{environment}-{table_name}")
            print_success(f"Table exists: {table_name}")
        except Exception as e:
            print_error(f"Table not found: {table_name} - {str(e)}")
            return False
    
    # Test 2: Check Lambda functions exist
    print_info("Test 2: Checking Lambda functions...")
    lambda_client = boto3.client('lambda')
    
    required_functions = [
        'replenishment_lambda',
        'batch_generation_lambda',
        'verification_lambda',
        'retrieval_lambda'
    ]
    
    for function_name in required_functions:
        try:
            response = lambda_client.get_function(FunctionName=f"{environment}-{function_name}")
            print_success(f"Function exists: {function_name}")
        except Exception as e:
            print_error(f"Function not found: {function_name} - {str(e)}")
            return False
    
    # Test 3: Check SQS queues exist
    print_info("Test 3: Checking SQS queues...")
    sqs = boto3.client('sqs')
    
    try:
        queues = sqs.list_queues(QueueNamePrefix=f"{environment}-verification")
        if queues.get('QueueUrls'):
            print_success(f"Verification queue exists")
        else:
            print_error("Verification queue not found")
            return False
    except Exception as e:
        print_error(f"Failed to check SQS queues: {str(e)}")
        return False
    
    # Test 4: Check EventBridge rule exists
    print_info("Test 4: Checking EventBridge schedule...")
    events = boto3.client('events')
    
    try:
        response = events.describe_rule(Name=f"{environment}-replenishment-schedule")
        print_success("EventBridge schedule exists")
    except Exception as e:
        print_error(f"EventBridge schedule not found: {str(e)}")
        return False
    
    # Test 5: Test retrieval Lambda
    print_info("Test 5: Testing retrieval Lambda...")
    try:
        test_payload = {
            'topic': 'algebra',
            'grade': 'foundation',
            'paper_type': 'P1',
            'count': 1
        }
        
        response = lambda_client.invoke(
            FunctionName=f"{environment}-retrieval_lambda",
            InvocationType='RequestResponse',
            Payload=json.dumps(test_payload)
        )
        
        if response['StatusCode'] == 200:
            print_success("Retrieval Lambda invoked successfully")
        else:
            print_warning(f"Retrieval Lambda returned status: {response['StatusCode']}")
    except Exception as e:
        print_warning(f"Retrieval Lambda test failed (expected if bank empty): {str(e)}")
    
    print_success("All smoke tests passed")
    return True

def deploy_frontend(environment: str) -> bool:
    """Deploy frontend to S3/CloudFront."""
    print_header("Deploying Frontend")
    
    try:
        returncode, stdout, stderr = run_command([
            'python3', 'scripts/deploy_frontend.py',
            '--environment', environment
        ])
        
        if returncode == 0:
            print_success("Frontend deployed successfully")
            return True
        else:
            print_error(f"Frontend deployment failed: {stderr}")
            return False
    except Exception as e:
        print_error(f"Error deploying frontend: {str(e)}")
        return False

def trigger_initial_replenishment(environment: str) -> bool:
    """Trigger initial replenishment to populate question bank."""
    print_header("Triggering Initial Replenishment")
    
    print_warning("This will trigger the replenishment Lambda to start populating the question bank.")
    print_warning("This process may take several hours to complete.")
    
    response = input(f"\n{Colors.WARNING}Do you want to trigger initial replenishment? (yes/no): {Colors.ENDC}")
    if response.lower() != 'yes':
        print_info("Skipping initial replenishment")
        return True
    
    try:
        lambda_client = boto3.client('lambda')
        
        response = lambda_client.invoke(
            FunctionName=f"{environment}-replenishment_lambda",
            InvocationType='Event',  # Async invocation
            Payload=json.dumps({})
        )
        
        if response['StatusCode'] == 202:
            print_success("Initial replenishment triggered")
            print_info("Monitor progress in CloudWatch Logs: /aws/lambda/replenishment_lambda")
            return True
        else:
            print_error(f"Failed to trigger replenishment: {response}")
            return False
    except Exception as e:
        print_error(f"Error triggering replenishment: {str(e)}")
        return False

def rollback_deployment(environment: str) -> bool:
    """Rollback deployment in case of failure."""
    print_header("Rolling Back Deployment")
    
    print_warning("This will destroy all deployed infrastructure.")
    response = input(f"\n{Colors.WARNING}Are you sure you want to rollback? (yes/no): {Colors.ENDC}")
    if response.lower() != 'yes':
        print_info("Rollback cancelled")
        return False
    
    terraform_dir = Path('terraform')
    
    print_info("Destroying Terraform infrastructure...")
    var_file = f"environments/{environment}.tfvars"
    returncode, stdout, stderr = run_command(
        ['terraform', 'destroy', '-var-file', var_file, '-auto-approve'],
        cwd=str(terraform_dir)
    )
    
    if returncode != 0:
        print_error(f"Rollback failed: {stderr}")
        return False
    
    print_success("Deployment rolled back successfully")
    return True

def print_deployment_summary(environment: str, outputs: Dict):
    """Print deployment summary."""
    print_header("Deployment Summary")
    
    print(f"{Colors.BOLD}Environment:{Colors.ENDC} {environment}")
    print(f"{Colors.BOLD}Status:{Colors.ENDC} {Colors.OKGREEN}Deployed{Colors.ENDC}")
    
    if outputs:
        print(f"\n{Colors.BOLD}Outputs:{Colors.ENDC}")
        for key, value in outputs.items():
            if isinstance(value, dict) and 'value' in value:
                print(f"  {key}: {value['value']}")
            else:
                print(f"  {key}: {value}")
    
    print(f"\n{Colors.BOLD}Next Steps:{Colors.ENDC}")
    print("  1. Monitor replenishment progress in CloudWatch")
    print("  2. Check question bank inventory")
    print("  3. Test retrieval endpoint")
    print("  4. Switch frontend to retrieval mode")
    print("  5. Monitor user feedback")
    
    print(f"\n{Colors.BOLD}Useful Commands:{Colors.ENDC}")
    print(f"  Check inventory: aws dynamodb scan --table-name {environment}-question_bank_inventory")
    print(f"  View logs: aws logs tail /aws/lambda/{environment}-replenishment_lambda --follow")
    print(f"  Test retrieval: curl -X POST <api-url>/retrieve-questions")

def main():
    """Main deployment function."""
    parser = argparse.ArgumentParser(description='Deploy Question Bank System')
    parser.add_argument('--environment', required=True, choices=['staging', 'prod'],
                       help='Deployment environment')
    parser.add_argument('--skip-tests', action='store_true',
                       help='Skip smoke tests')
    parser.add_argument('--skip-frontend', action='store_true',
                       help='Skip frontend deployment')
    parser.add_argument('--rollback', action='store_true',
                       help='Rollback deployment')
    
    args = parser.parse_args()
    
    print_header(f"Question Bank System Deployment - {args.environment.upper()}")
    
    # Rollback if requested
    if args.rollback:
        success = rollback_deployment(args.environment)
        sys.exit(0 if success else 1)
    
    # Check prerequisites
    if not check_prerequisites():
        print_error("Prerequisites check failed. Please install missing tools.")
        sys.exit(1)
    
    # Package Lambda functions
    if not package_lambda_functions():
        print_error("Failed to package Lambda functions")
        sys.exit(1)
    
    # Deploy Terraform infrastructure
    if not deploy_terraform(args.environment):
        print_error("Terraform deployment failed")
        sys.exit(1)
    
    # Get Terraform outputs
    outputs = get_terraform_outputs(args.environment)
    
    # Run smoke tests
    if not args.skip_tests:
        if not run_smoke_tests(args.environment, outputs):
            print_error("Smoke tests failed")
            response = input(f"\n{Colors.WARNING}Do you want to rollback? (yes/no): {Colors.ENDC}")
            if response.lower() == 'yes':
                rollback_deployment(args.environment)
            sys.exit(1)
    
    # Deploy frontend
    if not args.skip_frontend:
        if not deploy_frontend(args.environment):
            print_warning("Frontend deployment failed, but infrastructure is deployed")
    
    # Trigger initial replenishment
    trigger_initial_replenishment(args.environment)
    
    # Print summary
    print_deployment_summary(args.environment, outputs)
    
    print_success("\nDeployment completed successfully!")

if __name__ == '__main__':
    main()
