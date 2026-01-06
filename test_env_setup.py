#!/usr/bin/env python3
"""Set up environment variables for testing."""

import os

# Set required environment variables for testing
test_env_vars = {
    'SESSIONS_TABLE_NAME': 'gcse-generator-v2-sessions-test',
    'USERS_TABLE_NAME': 'gcse-generator-v2-users-test',
    'QUESTION_FEEDBACK_TABLE_NAME': 'gcse-generator-v2-question-feedback-test',
    'QUALITY_SCORES_TABLE_NAME': 'gcse-generator-v2-quality-scores-test',
    'TOPIC_COVERAGE_TABLE_NAME': 'gcse-generator-v2-topic-coverage-test',
    'SPECIFICATIONS_BUCKET_NAME': 'gcse-generator-v2-specifications-test',
    'QUESTION_BANK_BUCKET_NAME': 'gcse-generator-v2-question-bank-test',
    'AWS_REGION': 'eu-west-2',
    'AWS_DEFAULT_REGION': 'eu-west-2',
    'BEDROCK_MODEL_ID_HAIKU': 'anthropic.claude-3-haiku-20240307-v1:0',
    'BEDROCK_MODEL_ID_SONNET': 'anthropic.claude-3-sonnet-20240229-v1:0',
    'ENVIRONMENT': 'test',
    'LOG_LEVEL': 'INFO'
}

def setup_test_environment():
    """Set up all required environment variables for testing."""
    for key, value in test_env_vars.items():
        os.environ[key] = value
        print(f"Set {key}={value}")

if __name__ == "__main__":
    setup_test_environment()
    print("Test environment variables set successfully!")