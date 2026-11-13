#!/usr/bin/env python3
"""
Lambda packaging script for GCSE Question Generator.

This script creates deployment packages for AWS Lambda functions by:
1. Installing production dependencies in a temporary directory
2. Copying source code to the package directory
3. Creating a zip file for deployment
4. Uploading to S3 deployment bucket
"""

import os
import sys
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import List, Optional

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent
SRC_DIR = PROJECT_ROOT / "src"
REQUIREMENTS_FILE = PROJECT_ROOT / "requirements.txt"
TERRAFORM_DIR = PROJECT_ROOT / "terraform"
LAMBDA_PACKAGE_DIR = TERRAFORM_DIR / "lambda-package"


def run_command(command: List[str], cwd: Optional[Path] = None) -> None:
    """Run a shell command and handle errors."""
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True
        )
        print(f"✓ Command succeeded: {' '.join(command)}")
        if result.stdout:
            print(f"  Output: {result.stdout.strip()}")
    except subprocess.CalledProcessError as e:
        print(f"✗ Command failed: {' '.join(command)}")
        print(f"  Error: {e.stderr}")
        sys.exit(1)


def get_production_requirements() -> List[str]:
    """Extract production dependencies from requirements.txt."""
    production_deps = []
    
    with open(REQUIREMENTS_FILE, 'r') as f:
        lines = f.readlines()
    
    in_production_section = True  # Start assuming production deps
    
    for line in lines:
        line = line.strip()
        
        # Skip comments and empty lines
        if not line or line.startswith('#'):
            # Check for section markers in comments
            if '# Testing dependencies' in line or '# Development dependencies' in line:
                in_production_section = False
            elif '# Core dependencies' in line or '# Mathematical verification' in line:
                in_production_section = True
            continue
        
        # Add production dependencies
        if in_production_section:
            production_deps.append(line)
    
    # Essential production dependencies for Lambda
    essential_deps = [
        'boto3>=1.34.0',
        'botocore>=1.34.0',
        'jsonschema>=4.19.0',
        'requests>=2.31.0'
    ]
    
    # Combine and deduplicate
    all_deps = list(set(production_deps + essential_deps))
    
    print(f"Production dependencies identified: {len(all_deps)}")
    for dep in all_deps:
        print(f"  - {dep}")
    
    return all_deps


def create_lambda_package() -> Path:
    """Create Lambda deployment package with dependencies and source code."""
    print("Creating Lambda deployment package...")
    
    # Create temporary directory for package building
    with tempfile.TemporaryDirectory() as temp_dir:
        package_dir = Path(temp_dir) / "lambda_package"
        package_dir.mkdir()
        
        print(f"Building package in: {package_dir}")
        
        # Step 1: Install production dependencies
        print("Installing production dependencies...")
        production_deps = get_production_requirements()
        
        if production_deps:
            # Create temporary requirements file
            temp_requirements = package_dir / "temp_requirements.txt"
            with open(temp_requirements, 'w') as f:
                for dep in production_deps:
                    f.write(f"{dep}\n")
            
            # Install dependencies to package directory
            run_command([
                sys.executable, "-m", "pip", "install",
                "-r", str(temp_requirements),
                "-t", str(package_dir),
                "--upgrade"
            ])
            
            # Remove temporary requirements file
            temp_requirements.unlink()
        
        # Step 2: Copy source code
        print("Copying source code...")
        src_dest = package_dir / "src"
        shutil.copytree(SRC_DIR, src_dest)
        
        # Step 3: Create __init__.py files if missing
        for root, dirs, files in os.walk(src_dest):
            root_path = Path(root)
            if not (root_path / "__init__.py").exists():
                (root_path / "__init__.py").touch()
        
        # Step 4: Remove unnecessary files
        print("Cleaning up package...")
        cleanup_patterns = [
            "**/__pycache__",
            "**/*.pyc",
            "**/*.pyo",
            "**/.pytest_cache",
            "**/tests",
            "**/*.dist-info",
            "**/*.egg-info"
        ]
        
        for pattern in cleanup_patterns:
            for path in package_dir.glob(pattern):
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
        
        # Step 5: Create zip file
        print("Creating deployment zip file...")
        zip_path = LAMBDA_PACKAGE_DIR / "lambda-functions.zip"
        
        # Ensure lambda-package directory exists
        LAMBDA_PACKAGE_DIR.mkdir(exist_ok=True)
        
        # Remove existing zip if it exists
        if zip_path.exists():
            zip_path.unlink()
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(package_dir):
                for file in files:
                    file_path = Path(root) / file
                    # Calculate relative path from package directory
                    arcname = file_path.relative_to(package_dir)
                    zipf.write(file_path, arcname)
        
        # Get zip file size
        zip_size_mb = zip_path.stat().st_size / (1024 * 1024)
        print(f"✓ Created deployment package: {zip_path}")
        print(f"  Size: {zip_size_mb:.2f} MB")
        
        # Verify zip contents
        print("Package contents:")
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            files = zipf.namelist()
            print(f"  Total files: {len(files)}")
            
            # Show key files
            key_files = [
                'src/lambda_handlers/interpret_lambda.py',
                'src/lambda_handlers/generate_lambda.py',
                'src/models/__init__.py',
                'src/services/__init__.py',
                'src/utils/__init__.py',
                'boto3/__init__.py',
                'botocore/__init__.py'
            ]
            
            for key_file in key_files:
                if key_file in files:
                    print(f"  ✓ {key_file}")
                else:
                    print(f"  ✗ {key_file} (missing)")
        
        return zip_path


def validate_package(zip_path: Path) -> bool:
    """Validate the Lambda package contains required components."""
    print("Validating Lambda package...")
    
    required_files = [
        'src/lambda_handlers/interpret_lambda.py',
        'src/lambda_handlers/generate_lambda.py',
        'src/models/query_intent.py',
        'src/models/question.py',
        'src/models/mark_scheme.py',
        'src/services/bedrock_service.py',
        'src/utils/validation.py',
        'src/utils/security.py',
        'src/utils/constants.py'
    ]
    
    required_dependencies = [
        'boto3',
        'botocore',
        'jsonschema'
    ]
    
    with zipfile.ZipFile(zip_path, 'r') as zipf:
        files = zipf.namelist()
        
        # Check required source files
        missing_files = []
        for required_file in required_files:
            if required_file not in files:
                missing_files.append(required_file)
        
        if missing_files:
            print("✗ Missing required source files:")
            for file in missing_files:
                print(f"  - {file}")
            return False
        
        # Check required dependencies
        missing_deps = []
        for dep in required_dependencies:
            dep_found = any(f.startswith(f"{dep}/") or f.startswith(f"{dep}-") for f in files)
            if not dep_found:
                missing_deps.append(dep)
        
        if missing_deps:
            print("✗ Missing required dependencies:")
            for dep in missing_deps:
                print(f"  - {dep}")
            return False
    
    print("✓ Package validation successful")
    return True


def main():
    """Main packaging function."""
    print("GCSE Question Generator - Lambda Packaging")
    print("=" * 50)
    
    # Verify project structure
    if not SRC_DIR.exists():
        print(f"✗ Source directory not found: {SRC_DIR}")
        sys.exit(1)
    
    if not REQUIREMENTS_FILE.exists():
        print(f"✗ Requirements file not found: {REQUIREMENTS_FILE}")
        sys.exit(1)
    
    print(f"✓ Project root: {PROJECT_ROOT}")
    print(f"✓ Source directory: {SRC_DIR}")
    print(f"✓ Requirements file: {REQUIREMENTS_FILE}")
    
    # Create deployment package
    try:
        zip_path = create_lambda_package()
        
        # Validate package
        if not validate_package(zip_path):
            print("✗ Package validation failed")
            sys.exit(1)
        
        print("\n" + "=" * 50)
        print("✓ Lambda packaging completed successfully!")
        print(f"✓ Deployment package: {zip_path}")
        print(f"✓ Ready for Terraform deployment")
        
        # Next steps
        print("\nNext steps:")
        print("1. Run 'terraform plan' to preview infrastructure changes")
        print("2. Run 'terraform apply' to deploy the Lambda functions")
        print("3. Test the deployed functions with integration tests")
        
    except Exception as e:
        print(f"✗ Packaging failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()