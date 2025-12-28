# Requirements Document

## Introduction

The GCSE Question Generator is an AI-powered platform that enables teachers and tutors to generate high-quality GCSE exam questions through natural language requests. The system interprets user queries, searches relevant specification content and examples, and generates contextually appropriate questions with mark schemes using AWS Bedrock AI models.

## Glossary

- **System**: The complete GCSE Question Generator platform
- **User**: Teachers, tutors, or educators using the platform
- **Query**: Natural language input from users requesting specific questions
- **Intent**: Structured interpretation of user queries (topic, tier, count, marks)
- **Specification_Content**: Official Edexcel GCSE curriculum specifications
- **Seed_Examples**: AI-generated, human-verified example questions
- **Question_Set**: Generated questions with accompanying mark schemes
- **Vector_DB**: OpenSearch Serverless vector database for content retrieval
- **Interpret_Service**: AI service that parses natural language queries
- **Generate_Service**: AI service that creates questions and mark schemes
- **Embedding**: 1536-dimensional vector representation of text content
- **RAG**: Retrieval Augmented Generation pattern for AI content creation
- **OCU**: OpenSearch Compute Unit for serverless capacity measurement
- **Similarity_Score**: Cosine similarity metric (0-1) for vector matching
- **IaC**: Infrastructure as Code using Terraform configurations

## Requirements

### Requirement 1: Natural Language Query Processing

**User Story:** As a teacher, I want to request exam questions using natural language, so that I can quickly specify what I need without learning complex syntax.

#### Acceptance Criteria

1. WHEN a user submits a natural language query, THE Interpret_Service SHALL parse it into structured intent
2. WHEN the query contains topic information, THE System SHALL extract the subject area (Number, Algebra, etc.)
3. WHEN the query contains difficulty level, THE System SHALL identify the tier (Foundation or Higher)
4. WHEN the query is ambiguous or incomplete, THE System SHALL return a descriptive error message with error type, user-actionable guidance, and request ID
5. THE System SHALL validate queries to maximum 500 characters and reject requests containing SQL injection patterns or malicious content

### Requirement 2: Specification Content Retrieval

**User Story:** As a teacher, I want questions based on official GCSE specifications, so that they align with curriculum requirements.

#### Acceptance Criteria

1. THE System SHALL store Edexcel GCSE specification content in the Vector_DB
2. WHEN generating questions, THE Generate_Service SHALL retrieve relevant specification sections
3. WHEN searching specifications, THE System SHALL return top 3 most similar results with similarity score > 0.7
4. THE System SHALL maintain specification content with topic and tier metadata
5. WHEN specification content is updated, THE System SHALL version the update with timestamp and complete re-embedding within 24 hours
6. THE System SHALL support multiple specification versions simultaneously and tag all generated questions with specification version used
7. THE System SHALL allow users to select specification version with latest as default

### Requirement 3: Seed Example Integration

**User Story:** As a teacher, I want generated questions to follow proven patterns, so that they maintain consistent quality and style.

#### Acceptance Criteria

1. THE System SHALL store verified seed examples in the Vector_DB
2. WHEN generating questions, THE Generate_Service SHALL retrieve relevant seed examples
3. THE System SHALL maintain seed examples with topic, tier, and marks metadata
4. WHEN new seed examples are added, THE System SHALL generate embeddings and store them in the Vector_DB
5. THE Generate_Service SHALL use seed examples as templates for question structure and style

### Requirement 4: Question Generation with Mark Schemes

**User Story:** As a teacher, I want complete question sets with mark schemes, so that I can use them directly for assessments.

#### Acceptance Criteria

1. WHEN generating questions, THE Generate_Service SHALL create both questions and corresponding mark schemes
2. THE System SHALL ensure generated questions align with the requested topic and tier
3. THE System SHALL generate the exact number of questions requested by the user
4. WHEN questions require multiple marks, THE System SHALL provide detailed marking criteria
5. THE Generate_Service SHALL format output as structured JSON following the defined schema with questions, mark_scheme, and metadata arrays

### Requirement 5: Web Interface Access

**User Story:** As a teacher, I want to access the system through a web browser, so that I can use it from any device without installing software.

#### Acceptance Criteria

1. THE System SHALL provide a web-based user interface hosted on CloudFront
2. WHEN users access the interface, THE System SHALL display a clean query input form
3. THE System SHALL support HTTPS-only connections using TLS 1.2 or higher
4. WHEN users submit queries, THE System SHALL display generated questions in numbered list format with collapsible mark scheme sections
5. THE System SHALL provide global access through CloudFront's CDN network

### Requirement 6: API Gateway Integration

**User Story:** As a system administrator, I want secure API endpoints, so that the system can handle requests reliably and securely.

#### Acceptance Criteria

1. THE System SHALL expose two REST API endpoints: /interpret and /generate
2. WHEN receiving requests, THE API_Gateway SHALL validate input format and reject malformed requests with 400 status and validation errors
3. THE System SHALL implement CORS configuration for frontend access
4. WHEN API limits are exceeded, THE System SHALL return 429 status with rate limiting responses
5. THE API_Gateway SHALL log all requests for monitoring and debugging without exposing internal system details

### Requirement 7: Serverless Processing Architecture

**User Story:** As a system administrator, I want automatic scaling and cost optimization, so that the system handles varying loads efficiently.

#### Acceptance Criteria

1. THE Interpret_Service SHALL run on AWS Lambda with Claude Haiku model
2. THE Generate_Service SHALL run on AWS Lambda with Claude Sonnet model
3. WHEN processing requests, THE System SHALL automatically scale Lambda functions based on demand
4. THE System SHALL complete interpretation requests within 30 seconds OR return timeout error with descriptive message
5. THE System SHALL complete generation requests within 60 seconds OR return timeout error with descriptive message

### Requirement 8: Vector Database Operations

**User Story:** As a system administrator, I want efficient content retrieval, so that question generation uses the most relevant specification content and examples.

#### Acceptance Criteria

1. THE System SHALL use OpenSearch Serverless as the Vector_DB
2. WHEN storing content, THE System SHALL generate 1536-dimensional embeddings using Bedrock Titan
3. THE Vector_DB SHALL maintain separate indices for specification content and seed examples
4. WHEN searching, THE System SHALL return content ranked by vector similarity with minimum threshold of 0.7
5. WHEN no results meet similarity threshold, THE System SHALL retry with similarity threshold of 0.5 OR return descriptive error message suggesting alternative query phrasing

### Requirement 9: Content Management and Storage

**User Story:** As a system administrator, I want organized content storage, so that specifications and examples are properly managed and accessible.

#### Acceptance Criteria

1. THE System SHALL store specification documents in dedicated S3 buckets
2. THE System SHALL store seed examples in separate S3 buckets with JSON format
3. WHEN storing content, THE System SHALL apply appropriate access policies for security
4. THE System SHALL enable versioning on content buckets for rollback capability
5. THE System SHALL encrypt all stored content at rest using SSE-S3

### Requirement 10: Monitoring and Observability

**User Story:** As a system administrator, I want comprehensive monitoring, so that I can track system performance and troubleshoot issues.

#### Acceptance Criteria

1. THE System SHALL log all Lambda function executions to CloudWatch with 30-day retention
2. THE System SHALL track API Gateway request metrics including latency and error rates
3. WHEN errors occur, THE System SHALL capture detailed error information for debugging
4. THE System SHALL create CloudWatch alarms for Lambda error rates > 5% and API Gateway 5xx errors > 1%
5. THE System SHALL track and report daily Bedrock token usage with weekly cost reports

### Requirement 11: Regional Deployment and Infrastructure

**User Story:** As a system administrator, I want all resources deployed in the London region, so that we comply with data residency requirements and optimize latency for UK users.

#### Acceptance Criteria

1. THE System SHALL deploy all resources in the eu-west-2 (London) AWS region
2. WHEN deploying infrastructure, THE System SHALL use eu-west-2 for Lambda, API Gateway, OpenSearch, S3, and Bedrock services
3. THE System SHALL configure CloudFront to use global edge locations with eu-west-2 as origin
4. THE System SHALL define all infrastructure using Terraform with version-controlled configurations
5. THE System SHALL use Terraform remote state in S3 with DynamoDB locking, encryption at rest, and versioning enabled

### Requirement 12: Performance Standards and Scalability

**User Story:** As a system administrator, I want defined performance targets, so that the system meets user expectations and scales appropriately.

#### Acceptance Criteria

1. THE System SHALL process 95% of interpret requests within 5 seconds
2. THE System SHALL process 95% of generate requests within 30 seconds
3. THE API_Gateway SHALL support minimum 100 concurrent requests with queueing for additional requests
4. THE System SHALL maintain 99.5% uptime during UK business hours (9 AM - 5 PM GMT/BST accounting for daylight saving)
5. THE System SHALL maintain 99% uptime outside business hours and limit question count requests to 1-50 questions per request

### Requirement 13: Security and Access Control

**User Story:** As a system administrator, I want comprehensive security measures, so that the system protects against unauthorized access and malicious attacks.

#### Acceptance Criteria

1. THE System SHALL implement API key authentication for all API endpoints
2. THE System SHALL rate limit requests to 100 per user per hour
3. THE System SHALL implement least-privilege IAM roles for all AWS services
4. THE System SHALL sanitize all user inputs to prevent injection attacks
5. THE System SHALL log all authentication failures for security monitoring

### Requirement 14: Cost Control and Resource Management

**User Story:** As a system administrator, I want cost controls in place, so that the system operates within budget constraints.

#### Acceptance Criteria

1. THE System SHALL limit Bedrock token usage to 100K tokens per request
2. THE System SHALL implement configurable cost thresholds with defaults of £50 daily and £500 monthly limits
3. THE System SHALL alert administrators when cost thresholds are exceeded
4. THE System SHALL cache frequently requested question types to reduce Bedrock API calls
5. THE System SHALL provide weekly cost reports via email to administrators

### Requirement 15: Data Retention and Backup

**User Story:** As a system administrator, I want data protection and recovery capabilities, so that content is preserved and can be restored if needed.

#### Acceptance Criteria

1. THE System SHALL enable S3 versioning on all content buckets
2. THE System SHALL retain deleted content for 30 days before permanent deletion
3. THE System SHALL backup Vector_DB indices daily with 7-day retention
4. THE System SHALL maintain previous specification versions for 90 days
5. THE System SHALL document disaster recovery procedures with RTO < 4 hours

### Requirement 16: Error Handling and Resilience

**User Story:** As a system administrator, I want robust error handling, so that the system gracefully handles failures and provides useful feedback.

#### Acceptance Criteria

1. WHEN Bedrock API fails, THE System SHALL retry up to 3 times with exponential backoff
2. WHEN Vector_DB is unavailable, THE System SHALL return cached responses OR descriptive error message
3. WHEN Lambda execution fails, THE System SHALL log error details and return user-friendly message
4. THE System SHALL use standard HTTP status codes (400, 429, 500, 503) for all error responses
5. THE System SHALL include error type, user-actionable guidance, and request ID in all error messages

### Requirement 17: JSON Schema and Data Format

**User Story:** As a developer, I want standardized data formats, so that API responses are consistent and predictable.

#### Acceptance Criteria

1. THE Generate_Service SHALL return JSON in the following format:
   ```json
   {
     "questions": [
       {
         "id": "string",
         "question_text": "string", 
         "marks": integer,
         "tier": "Foundation|Higher",
         "topic": "string"
       }
     ],
     "mark_scheme": [
       {
         "question_id": "string",
         "marking_criteria": "string",
         "method_marks": integer,
         "accuracy_marks": integer
       }
     ],
     "metadata": {
       "generated_at": "ISO8601 timestamp",
       "model_version": "string",
       "total_marks": integer
     }
   }
   ```
2. THE System SHALL validate all JSON responses against the defined schema
3. THE System SHALL format mathematical notation in LaTeX format for frontend rendering
4. THE System SHALL ensure all timestamps use ISO8601 format
5. THE System SHALL include API version information in response headers

### Requirement 18: Question Quality Assurance

**User Story:** As a teacher, I want confidence that generated questions are accurate and appropriate, so that I can use them without extensive review.

#### Acceptance Criteria

1. THE System SHALL validate generated questions contain required mathematical elements for the specified topic
2. THE System SHALL verify mark schemes align with question difficulty and tier level
3. THE System SHALL reject questions with mathematical errors or ambiguous wording
4. THE System SHALL log quality metrics for continuous improvement and monitoring
5. THE System SHALL provide confidence scores for generated content based on specification alignment

### Requirement 19: Testing and Validation

**User Story:** As a developer, I want comprehensive testing, so that the system is reliable and maintainable.

#### Acceptance Criteria

1. THE System SHALL maintain minimum 80% unit test coverage for Lambda functions
2. THE System SHALL include integration tests for API Gateway → Lambda → Bedrock flow
3. THE System SHALL perform load testing for 100 concurrent users before production deployment
4. THE System SHALL validate generated questions against specification requirements in automated tests
5. THE System SHALL document all test procedures and results with continuous integration pipeline