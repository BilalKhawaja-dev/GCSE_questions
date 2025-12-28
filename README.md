# GCSE Question Generator

An AI-powered platform that enables teachers and tutors to generate high-quality GCSE exam questions through natural language requests using AWS Bedrock AI models.

## Features

- **Natural Language Processing**: Submit requests in plain English
- **AI-Powered Generation**: Uses Claude Haiku for query interpretation and Claude Sonnet for question generation
- **Curriculum Aligned**: Based on official Edexcel GCSE specifications
- **Complete Question Sets**: Generates questions with detailed mark schemes
- **Cost Optimized**: Serverless architecture with intelligent model selection

## Architecture

- **Frontend**: React/Vue.js web application hosted on CloudFront
- **API**: AWS API Gateway with Lambda functions
- **AI Processing**: AWS Bedrock (Claude Haiku + Claude Sonnet)
- **Storage**: S3 for specifications and examples
- **Infrastructure**: Terraform for Infrastructure as Code

## Project Structure

```
src/
├── models/              # Core data models
│   ├── query_intent.py  # Structured query representation
│   ├── question.py      # Question model
│   ├── mark_scheme.py   # Mark scheme model
│   └── specification_content.py  # Specification content model
├── utils/               # Shared utilities
│   ├── validation.py    # Input validation and sanitization
│   └── constants.py     # Configuration constants
tests/                   # Test suite
├── test_models.py       # Unit tests for models
└── test_utils.py        # Unit tests for utilities
```

## Development Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run tests:
```bash
pytest
```

3. Run with coverage:
```bash
pytest --cov=src --cov-report=html
```

## Testing

The project uses a dual testing approach:

- **Unit Tests**: Specific examples and edge cases using pytest
- **Property-Based Tests**: Universal properties using Hypothesis

Run property-based tests with:
```bash
pytest -m property
```

## Requirements

- Python 3.11+
- AWS Account with Bedrock access
- Terraform for infrastructure deployment

## License

MIT License - see LICENSE file for details.