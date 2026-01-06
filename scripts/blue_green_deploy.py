#!/usr/bin/env python3
"""
Blue-Green Deployment Script for GCSE Question Generator V2

This script implements a blue-green deployment strategy for Lambda functions
to minimize downtime and enable quick rollbacks.
"""

import boto3
import json
import time
import sys
from typing import Dict, List, Optional

class BlueGreenDeployer:
    def __init__(self, region: str = 'eu-west-2'):
        self.lambda_client = boto3.client('lambda', region_name=region)
        self.apigateway_client = boto3.client('apigateway', region_name=region)
        self.cloudwatch = boto3.client('cloudwatch', region_name=region)
        
        self.functions = [
            'gcse-auth-lambda-prod',
            'gcse-interpret-lambda-prod', 
            'gcse-generate-lambda-prod',
            'gcse-session-lambda-prod',
            'gcse-feedback-lambda-prod',
            'gcse-export-lambda-prod',
            'gcse-topic-coverage-lambda-prod',
            'gcse-refinement-lambda-prod'
        ]
    
    def create_function_aliases(self) -> Dict[str, str]:
        """Create BLUE and GREEN aliases for all Lambda functions."""
        aliases = {}
        
        for function_name in self.functions:
            try:
                # Get current version
                response = self.lambda_client.publish_version(
                    FunctionName=function_name,
                    Description=f'Blue-Green deployment version {int(time.time())}'
                )
                new_version = response['Version']
                
                # Create or update GREEN alias to point to new version
                try:
                    self.lambda_client.create_alias(
                        FunctionName=function_name,
                        Name='GREEN',
                        FunctionVersion=new_version,
                        Description='Green environment for blue-green deployment'
                    )
                    print(f"Created GREEN alias for {function_name} -> {new_version}")
                except self.lambda_client.exceptions.ResourceConflictException:
                    # Alias exists, update it
                    self.lambda_client.update_alias(
                        FunctionName=function_name,
                        Name='GREEN',
                        FunctionVersion=new_version
                    )
                    print(f"Updated GREEN alias for {function_name} -> {new_version}")
                
                # Ensure BLUE alias exists (points to previous stable version)
                try:
                    blue_alias = self.lambda_client.get_alias(
                        FunctionName=function_name,
                        Name='BLUE'
                    )
                    print(f"BLUE alias exists for {function_name} -> {blue_alias['FunctionVersion']}")
                except self.lambda_client.exceptions.ResourceNotFoundException:
                    # Create BLUE alias pointing to $LATEST initially
                    self.lambda_client.create_alias(
                        FunctionName=function_name,
                        Name='BLUE',
                        FunctionVersion='$LATEST',
                        Description='Blue environment for blue-green deployment'
                    )
                    print(f"Created BLUE alias for {function_name} -> $LATEST")
                
                aliases[function_name] = new_version
                
            except Exception as e:
                print(f"Error setting up aliases for {function_name}: {e}")
                return {}
        
        return aliases
    
    def run_health_checks(self, alias: str = 'GREEN') -> bool:
        """Run health checks against the specified alias."""
        print(f"Running health checks against {alias} environment...")
        
        failed_functions = []
        
        for function_name in self.functions:
            try:
                # Invoke function with health check payload
                response = self.lambda_client.invoke(
                    FunctionName=f"{function_name}:{alias}",
                    InvocationType='RequestResponse',
                    Payload=json.dumps({
                        'health_check': True,
                        'source': 'blue_green_deployment'
                    })
                )
                
                if response['StatusCode'] == 200:
                    print(f"✓ {function_name} health check passed")
                else:
                    print(f"✗ {function_name} health check failed: {response['StatusCode']}")
                    failed_functions.append(function_name)
                    
            except Exception as e:
                print(f"✗ {function_name} health check error: {e}")
                failed_functions.append(function_name)
        
        if failed_functions:
            print(f"Health checks failed for: {failed_functions}")
            return False
        
        print("All health checks passed!")
        return True
    
    def switch_traffic(self, from_alias: str, to_alias: str) -> bool:
        """Switch traffic from one alias to another."""
        print(f"Switching traffic from {from_alias} to {to_alias}...")
        
        try:
            # Update API Gateway to use new alias
            # This would require API Gateway integration updates
            # For now, we'll update the LIVE alias to point to the target
            
            for function_name in self.functions:
                try:
                    # Get the version that the target alias points to
                    target_alias_info = self.lambda_client.get_alias(
                        FunctionName=function_name,
                        Name=to_alias
                    )
                    target_version = target_alias_info['FunctionVersion']
                    
                    # Update or create LIVE alias to point to target version
                    try:
                        self.lambda_client.update_alias(
                            FunctionName=function_name,
                            Name='LIVE',
                            FunctionVersion=target_version
                        )
                        print(f"✓ Switched {function_name} LIVE -> {target_version}")
                    except self.lambda_client.exceptions.ResourceNotFoundException:
                        self.lambda_client.create_alias(
                            FunctionName=function_name,
                            Name='LIVE',
                            FunctionVersion=target_version
                        )
                        print(f"✓ Created {function_name} LIVE -> {target_version}")
                        
                except Exception as e:
                    print(f"✗ Failed to switch {function_name}: {e}")
                    return False
            
            print("Traffic switch completed successfully!")
            return True
            
        except Exception as e:
            print(f"Traffic switch failed: {e}")
            return False
    
    def monitor_deployment(self, duration_minutes: int = 5) -> bool:
        """Monitor the deployment for errors."""
        print(f"Monitoring deployment for {duration_minutes} minutes...")
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        while time.time() < end_time:
            try:
                # Check CloudWatch metrics for errors
                response = self.cloudwatch.get_metric_statistics(
                    Namespace='AWS/Lambda',
                    MetricName='Errors',
                    Dimensions=[
                        {
                            'Name': 'FunctionName',
                            'Value': 'gcse-generate-lambda-prod'  # Monitor key function
                        }
                    ],
                    StartTime=start_time,
                    EndTime=time.time(),
                    Period=60,
                    Statistics=['Sum']
                )
                
                if response['Datapoints']:
                    total_errors = sum(dp['Sum'] for dp in response['Datapoints'])
                    if total_errors > 5:  # Threshold for rollback
                        print(f"High error rate detected: {total_errors} errors")
                        return False
                
                print(f"Monitoring... {int((end_time - time.time()) / 60)} minutes remaining")
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                print(f"Monitoring error: {e}")
                time.sleep(30)
        
        print("Monitoring completed - no issues detected")
        return True
    
    def rollback(self) -> bool:
        """Rollback to the BLUE environment."""
        print("Initiating rollback to BLUE environment...")
        return self.switch_traffic('GREEN', 'BLUE')
    
    def deploy(self) -> bool:
        """Execute the complete blue-green deployment."""
        print("Starting Blue-Green Deployment for GCSE Question Generator V2")
        print("=" * 60)
        
        # Step 1: Create aliases and deploy to GREEN
        aliases = self.create_function_aliases()
        if not aliases:
            print("Failed to create function aliases")
            return False
        
        # Step 2: Health checks on GREEN environment
        if not self.run_health_checks('GREEN'):
            print("Health checks failed on GREEN environment")
            return False
        
        # Step 3: Switch traffic to GREEN
        if not self.switch_traffic('BLUE', 'GREEN'):
            print("Failed to switch traffic to GREEN")
            return False
        
        # Step 4: Monitor deployment
        if not self.monitor_deployment(5):
            print("Deployment monitoring detected issues - rolling back")
            self.rollback()
            return False
        
        # Step 5: Update BLUE to point to previous GREEN (for next deployment)
        print("Updating BLUE environment for next deployment...")
        for function_name in self.functions:
            try:
                green_alias = self.lambda_client.get_alias(
                    FunctionName=function_name,
                    Name='GREEN'
                )
                self.lambda_client.update_alias(
                    FunctionName=function_name,
                    Name='BLUE',
                    FunctionVersion=green_alias['FunctionVersion']
                )
            except Exception as e:
                print(f"Warning: Could not update BLUE alias for {function_name}: {e}")
        
        print("=" * 60)
        print("Blue-Green Deployment completed successfully!")
        return True

def main():
    """Main deployment function."""
    deployer = BlueGreenDeployer()
    
    if len(sys.argv) > 1 and sys.argv[1] == 'rollback':
        success = deployer.rollback()
        sys.exit(0 if success else 1)
    else:
        success = deployer.deploy()
        sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()