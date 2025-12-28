"""Setup configuration for GCSE Question Generator."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="gcse-question-generator",
    version="0.1.0",
    author="GCSE Question Generator Team",
    description="AI-powered GCSE exam question generator using AWS Bedrock",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Education",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.11",
    install_requires=[
        "boto3>=1.34.0",
        "botocore>=1.34.0",
        "jsonschema>=4.19.0",
        "requests>=2.31.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "hypothesis>=6.88.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.5.0",
        ],
        "lambda": [
            "awslambdaric>=2.0.0",
        ],
        "content": [
            "pdfplumber>=0.9.0",
        ]
    },
)