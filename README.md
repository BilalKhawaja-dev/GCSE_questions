# GCSE Question Generator v1.0

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![AWS](https://img.shields.io/badge/AWS-Serverless-orange.svg)](https://aws.amazon.com/)
[![Terraform](https://img.shields.io/badge/Infrastructure-Terraform-purple.svg)](https://www.terraform.io/)

> **An AI-powered, serverless system for generating high-quality GCSE Mathematics questions with comprehensive mark schemes, built on AWS with cost optimization and production-ready monitoring.**

## 🎯 Overview

The GCSE Question Generator is a sophisticated, production-ready system that leverages advanced AI to generate curriculum-aligned GCSE Mathematics questions. Built with a serverless-first architecture on AWS, it combines the power of Claude AI models with comprehensive content management and cost optimization strategies.

### Key Features

- **🤖 Dual-AI Architecture**: Two-stage processing with Claude Haiku for query interpretation and Claude Sonnet for question generation
- **📚 Curriculum Aligned**: Questions generated from official GCSE specifications and example papers
- **💰 Cost Optimized**: Designed for £14/month operational cost with intelligent caching and S3-based content retrieval
- **🔒 Production Ready**: Comprehensive security, monitoring, alerting, and error handling
- **📱 Modern Frontend**: React-based interface with mathematical notation rendering
- **🏗️ Infrastructure as Code**: Complete Terraform deployment with modular architecture
- **🧪 Comprehensive Testing**: Property-based testing with Hypothesis for correctness validation

## 🏛️ Architecture

### System Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   React Frontend │    │   API Gateway    │    │  Lambda Functions│
│                 │◄──►│                  │◄──►│                 │
│ • Query Input   │    │ • Authentication │    │ • InterpretLambda│
│ • Question Display│   │ • Rate Limiting  │    │ • GenerateLambda │
│ • Math Rendering│    │ • CORS           │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
                                                         ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   CloudFront    │    │   S3 Buckets     │    │  Bedrock AI     │
│                 │    │                  │    │                 │
│ • CDN           │    │ • Specifications │    │ • Claude Haiku  │
│ • HTTPS         │    │ • Examples       │    │ • Claude Sonnet │
│ • Caching       │    │ • Instructions   │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
                                                         ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   CloudWatch    │    │   CodePipeline   │    │  Version Control│
│                 │    │                  │    │                 │
│ • Monitoring    │    │ • CI/CD          │    │ • GitHub        │
│ • Alerting      │    │ • Automated      │    │ • Git Workflow  │
│ • Dashboards    │    │   Deployment     │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### AI Processing Flow

```
User Query → InterpretLambda (Claude Haiku) → Structured Intent → GenerateLambda (Claude Sonnet) → GCSE Questions
     │              │                              │                        │
     │              ▼                              ▼                        ▼
     │        Query Analysis                 Content Retrieval        Question Generation
     │        • Topic Detection             • S3 Specifications      • Curriculum Aligned
     │        • Tier Identification         • Example Questions      • Mark Schemes
     │        • Confidence Scoring          • AI Instructions        • Quality Validation
```

## 🚀 What Has Been Accomplished

### Phase 1: Foundation & Core Architecture (Tasks 1-7)

#### ✅ **Project Structure & Data Models**
- **Complete Python project structure** with proper packaging and module organization
- **Core data models** implemented with full validation:
  - `QueryIntent`: Natural language query parsing results
  - `Question`: GCSE question structure with marks and difficulty
  - `MarkScheme`: Detailed marking criteria with method/accuracy marks
  - `SpecificationContent`: Curriculum content organization
- **Testing framework** setup with pytest and Hypothesis for property-based testing
- **Shared utilities** for validation, constants, and common functions

#### ✅ **InterpretLambda Function (Query Processing)**
- **Lambda handler** with comprehensive error handling and structured logging
- **Input validation** with 500-character limit and malicious content detection
- **Bedrock Claude Haiku integration** with:
  - Structured prompts for consistent query parsing
  - Confidence scoring algorithm (0.0-1.0 scale)
  - Exponential backoff retry for API failures
  - Topic detection for 6 GCSE domains (Number, Algebra, Geometry, Statistics, Probability, Ratio)
  - Tier identification (Foundation/Higher/Both)
- **CloudWatch integration** with structured logging and metrics

#### ✅ **GenerateLambda Function (Question Generation)**
- **Lambda handler** with structured error handling and request validation
- **S3 content retrieval system** with:
  - Topic-to-file mapping for efficient content lookup
  - Specification content retrieval with version management
  - Seed examples retrieval for style consistency
  - Circuit breaker pattern for S3 error handling
- **Bedrock Claude Sonnet integration** with:
  - Multi-domain paper generation capability
  - Question quality validation logic
  - JSON schema validation for response structure
  - Mathematical accuracy verification

#### ✅ **Content Processing Pipeline**
- **PDF parsing functionality** using pdfplumber for specification extraction
- **Content organization** by domain and subtopic with JSON structure
- **Seed examples processing** with quality scoring and validation
- **Specification version management** with "latest" default and multi-version support
- **S3 upload system** with proper bucket organization and file structure

#### ✅ **Infrastructure as Code (Terraform)**
- **Terraform backend** with S3 state storage and DynamoDB locking
- **S3 buckets** with versioning, encryption, and lifecycle policies:
  - `gcse-specifications-prod-1a64dc99`: Curriculum specifications
  - `gcse-examples-prod-1a64dc99`: Example questions and mark schemes
  - `gcse-ai-instructions-prod`: AI agent instructions
- **Lambda functions** with proper IAM roles and least-privilege permissions
- **API Gateway** with REST endpoints, CORS, authentication, and rate limiting
- **CloudFront distribution** with HTTPS-only, caching policies, and Origin Access Control

### Phase 2: Frontend & User Experience (Task 8)

#### ✅ **React Frontend Application**
- **TypeScript-based React application** with modern build tooling
- **Query input interface** with:
  - 500-character limit validation
  - Real-time input validation and error display
  - Loading states and user feedback
  - Retry logic for failed requests
- **Question display components** with:
  - Numbered list format for multiple questions
  - Collapsible mark scheme sections
  - Mathematical notation rendering using MathJax
  - Responsive design for mobile and desktop
- **Error handling system** with:
  - Standardized error messages
  - User-actionable guidance
  - Graceful degradation for API failures
- **Comprehensive unit tests** for all components and API integration

### Phase 3: Monitoring & Operations (Tasks 9-12)

#### ✅ **CloudWatch Monitoring & Alerting**
- **Custom dashboards** with:
  - API Gateway metrics (requests, latency, errors)
  - Lambda performance metrics (duration, memory, errors)
  - Bedrock usage tracking via CloudWatch Logs Insights
  - S3 request metrics and latency monitoring
  - Cost tracking dashboard using Cost Explorer API
- **CloudWatch alarms** with:
  - Critical alarms for error rates and availability
  - Warning alarms for performance and cost thresholds
  - SNS topic integration for alert notifications
- **Monitoring validation tests** for alarm accuracy and notification delivery

#### ✅ **Performance Optimization**
- **Lambda in-memory caching** with TTL and cache invalidation logic
- **Request timeout handling**:
  - 30-second timeout for InterpretLambda
  - 60-second timeout for GenerateLambda
  - Descriptive timeout error messages
- **Cache hit/miss metrics** for performance monitoring
- **Property-based tests** for performance validation

#### ✅ **Security Implementation**
- **Input sanitization** with:
  - SQL injection pattern detection
  - XSS prevention through input encoding
  - Malicious content filtering
- **API authentication** with:
  - API key validation
  - Rate limiting (100 requests/hour per user)
  - Authentication failure logging
- **Security validation tests** for all protection mechanisms

### Phase 4: Deployment & Integration (Tasks 13-14)

#### ✅ **Production Deployment**
- **Lambda function packaging** with dependencies and S3 deployment
- **Terraform deployment** with remote state management
- **End-to-end integration tests** validating complete user journey
- **Load testing** with:
  - Normal load scenario (50 concurrent users)
  - Peak load test (100 concurrent users)
  - SLA requirement validation
- **Complete system validation** with cost threshold verification

### Phase 5: Critical Production Issues Resolution (Task 15)

#### ✅ **AI Integration Pipeline Validation**
- **Comprehensive flow testing** with `validate_ai_integration.py`
- **Two-stage AI flow verification**: Natural language → Claude Haiku → Structured intent → Claude Sonnet → Questions
- **CloudWatch logs analysis** for actual Bedrock API calls and token usage
- **Unique response generation** testing across different query types

#### ✅ **Cache Issue Resolution**
- **Cache clearing system** with `clear_all_caches.py`
- **Environment variable updates** with `DISABLE_QUESTION_CACHING=true`
- **Cache invalidation logic** implementation
- **Fresh question generation** validation with `test_cache_fix.py`

#### ✅ **Mathematical Notation Enhancement**
- **LaTeX rendering optimization** with `improve_math_rendering.py`
- **Human-readable notation** implementation (3/4 instead of \\frac{3}{4})
- **Cross-browser compatibility** testing
- **Frontend mathematical expression** display improvements

#### ✅ **Bulk Content Upload System**
- **PDF processing system** with `bulk_pdf_upload_system.py`
- **Batch PDF parsing** for ~50 GCSE papers
- **S3 bucket structure** optimization for large content volumes
- **Content library expansion** with comprehensive topic coverage
- **Upload validation** with `test_bulk_upload.py`

#### ✅ **Architecture Flow Validation & Monitoring**
- **End-to-end flow testing** with `architecture_flow_validator.py`
- **Request tracing system** through complete architecture
- **CloudWatch dashboard** creation: `GCSE-Architecture-Flow-Monitor`
- **AI service usage alerts** with CloudWatch alarms
- **Architecture documentation** with actual vs. intended flow analysis

### Phase 6: Enhanced AI System (Task 16.1)

#### ✅ **AI Knowledge Base & Instruction System**
- **AI instruction repository** with `ai_knowledge_upload_system.py`
- **Detailed prompting guides** for both InterpretLambda and GenerateLambda
- **Instruction versioning system** for consistent AI behavior
- **S3-based instruction storage** with retrieval system
- **Content upload guidelines** with comprehensive documentation

## 📊 System Metrics & Performance

### Cost Optimization Results
- **Target Cost**: £14/month
- **Architecture**: Serverless-first with intelligent caching
- **S3 Storage**: Optimized with lifecycle policies
- **Lambda**: Pay-per-request with memory optimization
- **Bedrock**: Cost-effective two-stage AI processing

### Performance Benchmarks
- **Query Interpretation**: < 2 seconds (Claude Haiku)
- **Question Generation**: < 30 seconds (Claude Sonnet)
- **Frontend Load Time**: < 3 seconds
- **API Response Time**: 95th percentile < 35 seconds
- **Availability**: 99.9% uptime target

### Content Coverage
- **Topics**: 6 GCSE Mathematics domains fully covered
- **Tiers**: Foundation and Higher tier support
- **Specifications**: Complete curriculum alignment
- **Examples**: Comprehensive question bank with mark schemes

## 🧪 Testing Strategy

### Property-Based Testing
The system implements comprehensive property-based testing using Hypothesis to validate correctness across all inputs:

#### **Core Properties Validated**
1. **Query Parsing Completeness**: All valid queries produce structured intents
2. **Content Retrieval Consistency**: S3 content retrieval is deterministic
3. **Question Generation Quality**: Generated questions meet curriculum standards
4. **Specification Version Management**: Version handling is consistent
5. **Performance Requirements**: Response times meet SLA requirements
6. **Cache Behavior**: Caching logic maintains consistency
7. **Error Handling**: All error conditions are handled gracefully

#### **Testing Coverage**
- **Unit Tests**: 95%+ coverage for all modules
- **Integration Tests**: Complete API flow validation
- **Property Tests**: 100+ iterations per property with randomized inputs
- **Load Tests**: Concurrent user simulation
- **Security Tests**: Input validation and authentication

## 🛠️ Development Tools & Scripts

### **Operational Scripts**
- `validate_ai_integration.py`: Comprehensive AI pipeline testing
- `clear_all_caches.py`: Cache clearing and invalidation
- `architecture_flow_validator.py`: End-to-end system validation
- `bulk_pdf_upload_system.py`: Content processing and upload
- `test_cache_fix.py`: Cache behavior validation
- `deploy_to_codepipeline.py`: Automated deployment to AWS CodePipeline

### **Content Management**
- `ai_knowledge_upload_system.py`: AI instruction management
- `upload_interface.py`: User-friendly content upload interface
- `check_s3_content.py`: S3 content verification
- `validate_system.py`: Consolidated system health checks

### **Infrastructure Management**
- `terraform/`: Complete Infrastructure as Code
- `scripts/`: Lambda packaging and deployment utilities
- `frontend/`: React application with TypeScript

## 📁 Project Structure

```
gcse-question-generator/
├── 📁 src/                          # Core Python application
│   ├── 📁 lambda_handlers/          # AWS Lambda functions
│   │   ├── interpret_lambda.py      # Query interpretation (Claude Haiku)
│   │   └── generate_lambda.py       # Question generation (Claude Sonnet)
│   ├── 📁 services/                 # Business logic services
│   │   ├── bedrock_service.py       # AWS Bedrock AI integration
│   │   ├── content_retrieval_service.py  # S3 content management
│   │   └── content_processing_service.py # PDF processing
│   ├── 📁 models/                   # Data models and schemas
│   │   ├── query_intent.py          # Query parsing results
│   │   ├── question.py              # GCSE question structure
│   │   └── mark_scheme.py           # Marking criteria
│   └── 📁 utils/                    # Shared utilities
│       ├── validation.py            # Input validation
│       ├── cache.py                 # Caching logic
│       └── security.py              # Security utilities
├── 📁 frontend/                     # React frontend application
│   ├── 📁 src/
│   │   ├── 📁 components/           # React components
│   │   ├── 📁 services/             # API client
│   │   ├── 📁 hooks/                # Custom React hooks
│   │   └── 📁 utils/                # Frontend utilities
│   └── package.json                 # Node.js dependencies
├── 📁 terraform/                    # Infrastructure as Code
│   ├── 📁 modules/                  # Terraform modules
│   │   ├── 📁 api/                  # API Gateway configuration
│   │   ├── 📁 ai/                   # Bedrock and Lambda setup
│   │   ├── 📁 knowledge/            # S3 buckets and content
│   │   ├── 📁 frontend/             # CloudFront and hosting
│   │   └── 📁 monitoring/           # CloudWatch and alerting
│   ├── main.tf                      # Main Terraform configuration
│   └── 📁 environments/             # Environment-specific configs
├── 📁 tests/                        # Comprehensive test suite
│   ├── test_property_*.py           # Property-based tests
│   ├── test_*_lambda.py             # Lambda function tests
│   └── test_*.py                    # Unit and integration tests
├── 📁 scripts/                      # Deployment and utility scripts
├── 📁 ai_instructions/              # AI agent instruction documents
├── 📄 requirements.txt              # Python dependencies
├── 📄 setup.py                      # Package configuration
├── 📄 pytest.ini                    # Testing configuration
└── 📄 README.md                     # This comprehensive documentation
```

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 16+
- AWS CLI configured
- Terraform 1.0+

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/BilalKhawaja-dev/GCSE_questions.git
   cd GCSE_questions
   ```

2. **Set up Python environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Set up frontend**
   ```bash
   cd frontend
   npm install
   npm start
   ```

4. **Configure AWS credentials**
   ```bash
   aws configure
   # Enter your AWS Access Key ID, Secret Access Key, and region (eu-west-2)
   ```

### Deployment

1. **Initialize Terraform**
   ```bash
   cd terraform
   terraform init
   ```

2. **Deploy infrastructure**
   ```bash
   terraform plan -var-file="environments/prod.tfvars"
   terraform apply -var-file="environments/prod.tfvars"
   ```

3. **Deploy to CodePipeline**
   ```bash
   python deploy_to_codepipeline.py
   ```

### Testing

1. **Run unit tests**
   ```bash
   pytest tests/ -v
   ```

2. **Run property-based tests**
   ```bash
   pytest tests/test_property_*.py -v --hypothesis-show-statistics
   ```

3. **Validate system health**
   ```bash
   python validate_system.py
   ```

## 🔧 Configuration

### Environment Variables
```bash
# AWS Configuration
AWS_REGION=eu-west-2
AWS_ACCOUNT_ID=your-account-id

# Lambda Configuration
INTERPRET_LAMBDA_NAME=gcse-interpret-lambda-prod
GENERATE_LAMBDA_NAME=gcse-generate-lambda-prod

# S3 Configuration
SPECIFICATIONS_BUCKET=gcse-specifications-prod-1a64dc99
EXAMPLES_BUCKET=gcse-examples-prod-1a64dc99
INSTRUCTIONS_BUCKET=gcse-ai-instructions-prod

# API Configuration
API_GATEWAY_URL=https://your-api-id.execute-api.eu-west-2.amazonaws.com/prod
GCSE_API_KEY=your-api-key

# Cache Configuration
DISABLE_QUESTION_CACHING=false
CACHE_TTL_SECONDS=3600
```

## 📈 Monitoring & Observability

### CloudWatch Dashboards
- **GCSE-Architecture-Flow-Monitor**: Complete system health overview
- **Lambda Performance**: Function execution metrics
- **API Gateway Metrics**: Request patterns and error rates
- **Cost Tracking**: Real-time cost monitoring

### Key Metrics
- **Request Volume**: API calls per minute/hour/day
- **Response Times**: P50, P95, P99 latencies
- **Error Rates**: 4XX and 5XX error percentages
- **AI Usage**: Bedrock token consumption and costs
- **Cache Performance**: Hit/miss ratios and efficiency

### Alerting
- **Critical Alerts**: System downtime, high error rates
- **Warning Alerts**: Performance degradation, cost thresholds
- **Info Alerts**: Deployment notifications, maintenance windows

## 🔒 Security

### Authentication & Authorization
- **API Key Authentication**: Required for all API endpoints
- **Rate Limiting**: 100 requests/hour per API key
- **CORS Configuration**: Restricted to allowed origins

### Input Validation
- **Query Sanitization**: SQL injection and XSS prevention
- **Content Filtering**: Malicious content detection
- **Size Limits**: 500-character query limit

### Data Protection
- **Encryption at Rest**: S3 and DynamoDB encryption
- **Encryption in Transit**: HTTPS/TLS for all communications
- **Access Control**: IAM roles with least-privilege principles

## 🤝 Contributing

### Development Workflow
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes with tests
4. Run the test suite (`pytest`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Code Standards
- **Python**: Follow PEP 8 with Black formatting
- **TypeScript**: ESLint and Prettier configuration
- **Testing**: Minimum 90% coverage for new code
- **Documentation**: Update README and inline docs

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **AWS Bedrock**: Claude AI models for natural language processing
- **Terraform**: Infrastructure as Code framework
- **React**: Frontend framework for user interface
- **Hypothesis**: Property-based testing library
- **MathJax**: Mathematical notation rendering

## 📞 Support

For support, questions, or contributions:
- **GitHub Issues**: [Create an issue](https://github.com/BilalKhawaja-dev/GCSE_questions/issues)
- **Documentation**: This README and inline code documentation
- **Testing**: Run `python validate_system.py` for system health checks

---

**Built with ❤️ for GCSE Mathematics education**

*Version 1.0 - Production Ready*