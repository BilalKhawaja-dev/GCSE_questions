# Implementation Plan: GCSE Question Generator

## Overview

This implementation plan converts the GCSE Question Generator design into discrete coding tasks for a serverless AWS architecture. The system uses a two-stage AI processing approach with Claude Haiku for query interpretation and Claude Sonnet for question generation, with S3-based content retrieval for cost optimization.

## Tasks

- [x] 1. Set up project structure and core interfaces
  - Create Python project structure with proper packaging
  - Define core data models (QueryIntent, Question, MarkScheme, SpecificationContent)
  - Set up testing framework (pytest + Hypothesis for property-based testing)
  - Create shared utilities module for common functions
  - _Requirements: 17.1, 19.1_

- [x] 1.1 Write property test for data model validation
  - **Property 1: Query Parsing Completeness**
  - **Validates: Requirements 1.1, 1.2, 1.3, 1.4**

- [x] 2. Implement InterpretLambda function
  - [x] 2.1 Create Lambda handler for query interpretation
    - Implement main handler function with error handling
    - Add input validation and sanitization (500 char limit, malicious content detection)
    - Set up CloudWatch logging with structured logging
    - _Requirements: 1.1, 1.5, 13.4_

  - [x] 2.2 Implement Bedrock Claude Haiku integration
    - Create Bedrock client with proper IAM permissions
    - Implement query parsing with structured prompts
    - Add confidence scoring algorithm for parsed intents
    - Handle Bedrock API failures with exponential backoff retry
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 16.1_

  - [x] 2.3 Write property tests for query interpretation
    - **Property 1: Query Parsing Completeness**
    - **Property 2: Error Handling for Invalid Queries**
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5**

  - [x] 2.4 Write unit tests for InterpretLambda
    - Test confidence scoring edge cases
    - Test input validation boundary conditions
    - Test Bedrock integration error scenarios
    - _Requirements: 1.5, 16.1_

- [x] 3. Implement GenerateLambda function
  - [x] 3.1 Create Lambda handler for question generation
    - Implement main handler function with structured error handling
    - Add request validation for generation parameters
    - Set up CloudWatch logging and metrics
    - _Requirements: 4.1, 4.5, 17.1_

  - [x] 3.2 Implement S3 content retrieval system
    - Create topic-to-file mapping dictionary
    - Implement specification content retrieval from S3
    - Implement seed examples retrieval from S3
    - Add S3 error handling with circuit breaker pattern
    - _Requirements: 2.2, 2.6, 16.2_

  - [x] 3.3 Write property test for content retrieval
    - **Property 3: Content Retrieval for Generation**
    - **Property 10: S3 Storage Fallback**
    - **Validates: Requirements 2.2, 16.2**

  - [x] 3.4 Implement Bedrock Claude Sonnet integration
    - Create question generation with specification and examples
    - Implement multi-domain paper generation capability
    - Add question quality validation logic
    - Handle JSON schema validation for responses
    - _Requirements: 4.1, 4.2, 4.3, 17.1, 18.1, 18.2_

  - [x] 3.5 Write property tests for question generation
    - **Property 4: Specification Version Management**
    - **Property 5: Complete Question Generation**
    - **Property 7: Content Alignment Validation**
    - **Validates: Requirements 2.6, 4.1, 4.3, 4.5, 17.1, 4.2, 18.1, 18.2**

  - [x] 3.6 Write unit tests for GenerateLambda
    - Test S3 content retrieval edge cases
    - Test question quality validation logic
    - Test JSON schema compliance
    - _Requirements: 17.1, 18.1, 18.2_

- [x] 4. Checkpoint - Core Lambda functions complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Create content processing pipeline
  - [x] 5.1 Implement PDF parsing functionality
    - Create specification PDF parsing with pdfplumber
    - Implement content organization by domain/subtopic
    - Add JSON file generation for S3 storage
    - _Requirements: 2.1, 2.4_

  - [x] 5.2 Create seed examples processing
    - Implement example question parsing and validation
    - Create JSON structure for examples storage
    - Add quality scoring for seed examples
    - _Requirements: 3.1, 3.4_

  - [x] 5.3 Implement specification version management
    - Add version tagging to specification JSON files
    - Implement version selection logic in GenerateLambda
    - Set "latest" as default version
    - Test multi-version support
    - _Requirements: 2.6, 2.7_

  - [x] 5.4 Upload processed content to S3
    - Upload specification JSON files to specifications bucket
    - Upload seed examples JSON files to examples bucket
    - Verify S3 bucket structure and file organization
    - Test content retrieval from GenerateLambda
    - _Requirements: 2.1, 3.1, 9.1_

  - [x] 5.5 Write unit tests for content processing
    - Test PDF parsing accuracy
    - Test JSON structure validation
    - Test content organization logic
    - _Requirements: 2.1, 3.1_

- [x] 6. Set up Terraform backend and infrastructure
  - [x] 6.0 Set up Terraform backend
    - Create S3 bucket for Terraform state (gcse-terraform-state)
    - Create DynamoDB table for state locking (terraform-locks)
    - Configure backend.tf with encryption and versioning
    - Initialize Terraform with remote state
    - _Requirements: 11.5_

  - [x] 6.1 Create S3 buckets and policies
    - Set up frontend assets bucket with CloudFront OAC
    - Create specifications bucket with versioning
    - Create examples bucket with proper IAM policies
    - Configure S3 encryption and lifecycle policies
    - _Requirements: 9.1, 9.4, 11.1, 15.1_

  - [x] 6.2 Create Lambda functions infrastructure
    - Define Lambda function resources with proper runtime
    - Set up IAM roles with least-privilege permissions
    - Configure environment variables and timeouts
    - Set up Lambda deployment from S3 (packages created in Task 11.1)
    - _Requirements: 7.1, 7.2, 11.1, 13.3_

  - [x] 6.3 Set up API Gateway
    - Create REST API with /interpret and /generate endpoints
    - Configure CORS for frontend domain
    - Set up API key authentication and rate limiting
    - Add request validation and error response formatting
    - _Requirements: 6.1, 6.2, 6.4, 13.1, 13.2_

  - [x] 6.4 Create CloudFront distribution
    - Set up CloudFront with S3 origin
    - Configure HTTPS-only with proper caching policies
    - Set up Origin Access Control for security
    - _Requirements: 5.1, 5.3, 13.3_

  - [x] 6.5 Write integration tests for infrastructure
    - Test API Gateway → Lambda integration
    - Test S3 bucket policies and access
    - Test CloudFront distribution functionality
    - _Requirements: 19.2_

- [x] 7. Checkpoint - Infrastructure complete
  - Ensure all infrastructure is deployed and accessible, ask the user if questions arise.

- [-] 8. Implement frontend application
  - [x] 8.1 Create React/Vue project structure
    - Set up project with TypeScript and build tooling
    - Configure routing and state management
    - Set up API client for backend integration
    - _Requirements: 5.1, 5.2_

  - [x] 8.2 Build query input interface
    - Create query form with 500 character limit
    - Add input validation and error display
    - Implement loading states and user feedback
    - _Requirements: 5.2, 5.4_

  - [x] 8.3 Implement question display components
    - Create numbered list format for questions
    - Add collapsible mark scheme sections
    - Implement LaTeX mathematical notation rendering (MathJax)
    - _Requirements: 5.4, 17.3_

  - [x] 8.4 Add error handling and user guidance
    - Display standardized error messages
    - Show user-actionable guidance for errors
    - Implement retry logic for failed requests
    - _Requirements: 1.5, 16.5_

  - [x] 8.5 Write frontend unit tests
    - Test component rendering and interactions
    - Test API integration and error handling
    - Test LaTeX rendering functionality
    - _Requirements: 19.1_

- [x] 9. Implement monitoring and alerting
  - [x] 9.1 Set up CloudWatch dashboards
    - Create dashboard widgets for API Gateway metrics
    - Add Lambda performance and error metrics
    - Include Bedrock usage tracking (token counts via CloudWatch Logs Insights)
    - Add S3 request metrics and latency
    - Create cost tracking dashboard using Cost Explorer API
    - _Requirements: 10.1, 10.2, 10.5, 14.5_

  - [x] 9.2 Configure CloudWatch alarms
    - Set up critical alarms for error rates and availability
    - Create warning alarms for performance and cost thresholds
    - Configure SNS topics for alert notifications
    - _Requirements: 10.4, 14.2, 14.3_

  - [x] 9.3 Write monitoring validation tests
    - Test alarm triggering conditions
    - Validate dashboard metric accuracy
    - Test SNS notification delivery
    - _Requirements: 10.4_

- [x] 10. Implement caching layer
  - [x] 10.1 Add Lambda in-memory caching
    - Implement query result caching with TTL
    - Add cache invalidation logic
    - Create cache hit/miss metrics
    - _Requirements: 14.4_

  - [x] 10.2 Write property tests for caching
    - Test cache consistency and TTL behavior
    - Validate cache invalidation scenarios
    - _Requirements: 14.4_

- [x] 11. Implement performance optimizations
  - [x] 11.1 Add request timeout handling
    - Implement 30-second timeout for InterpretLambda
    - Implement 60-second timeout for GenerateLambda
    - Add descriptive timeout error messages
    - _Requirements: 7.4, 7.5_

  - [x] 11.2 Write property tests for performance
    - **Property 6: Interpretation Performance**
    - **Property 8: Generation Performance**
    - **Validates: Requirements 7.4, 7.5**

- [x] 12. Implement security measures
  - [x] 12.1 Add input sanitization
    - Implement SQL injection pattern detection
    - Add XSS prevention through input encoding
    - Create malicious content filtering
    - _Requirements: 1.5, 13.4, 13.5_

  - [x] 12.2 Set up API authentication
    - Implement API key validation
    - Add rate limiting per user (100 requests/hour)
    - Create authentication failure logging
    - _Requirements: 13.1, 13.2, 13.5_

  - [x] 12.3 Write security validation tests
    - Test input sanitization effectiveness
    - Test rate limiting behavior
    - Test authentication failure scenarios
    - _Requirements: 13.4, 13.5_

- [x] 13. Final integration and deployment
  - [x] 13.1 Package Lambda functions
    - Create deployment packages with dependencies
    - Upload to S3 deployment bucket
    - Update Terraform to reference deployment packages
    - _Requirements: 11.4, 11.5_

  - [x] 13.2 Deploy infrastructure with Terraform
    - Initialize Terraform backend with remote state
    - Apply infrastructure changes to AWS
    - Verify all resources are created correctly
    - _Requirements: 11.1, 11.5_

  - [x] 13.3 Run end-to-end integration tests
    - Test complete user journey from query to response
    - Validate API Gateway → Lambda → Bedrock flow
    - Test error handling across all components
    - _Requirements: 19.2_

  - [x] 13.4 Perform load testing
    - Execute normal load scenario (50 concurrent users)
    - Run peak load test (100 concurrent users)
    - Validate performance meets SLA requirements
    - _Requirements: 19.3_

- [x] 14. Final checkpoint - Complete system validation
  - Ensure all tests pass, verify cost thresholds, ask the user if questions arise.

- [-] 15. Critical Production Issues Investigation and Resolution
  - [x] 15.1 Validate AI Integration Pipeline
    - Investigate if InterpretLambda is actually processing queries or returning cached responses
    - Verify two-stage AI flow: natural language → Claude Haiku → structured intent → Claude Sonnet → questions
    - Test with different queries to ensure unique responses are generated
    - Check CloudWatch logs for actual Bedrock API calls and token usage
    - _Requirements: 1.1, 4.1, 16.1_
    - _Reference: deployment-status-summary.md_

  - [x] 15.2 Fix Question Caching Issue
    - Identify why same 5 questions appear regardless of user input
    - Remove inappropriate caching of generated questions
    - Ensure each query generates fresh, unique questions
    - Implement proper cache invalidation if caching is needed for performance
    - _Requirements: 4.1, 4.5, 14.4_
    - _Reference: deployment-status-summary.md_

  - [x] 15.3 Improve Mathematical Notation Rendering
    - Investigate current LaTeX rendering issues in frontend
    - Consider switching from LaTeX to Markdown for better human readability
    - Test mathematical expression display across different browsers
    - Ensure fractions, equations, and symbols render clearly
    - Update question generation to use optimal notation format
    - _Requirements: 5.4, 17.3_
    - _Reference: deployment-status-summary.md_

  - [x] 15.4 Implement Bulk PDF Content Upload System
    - Create script to process and upload ~50 GCSE PDF papers
    - Implement batch PDF parsing for specification content
    - Update S3 bucket structure to handle large content volumes
    - Ensure content retrieval system can handle expanded content library
    - Test question generation improvement with expanded content
    - _Requirements: 2.1, 2.4, 3.1, 9.1_
    - _Reference: deployment-status-summary.md_

  - [x] 15.5 Architecture Flow Validation and Monitoring
    - ✅ Created comprehensive end-to-end flow testing (`architecture_flow_validator.py`)
    - ✅ Implemented detailed logging to trace request flow through system
    - ✅ Added monitoring dashboards to verify AI service usage (CloudWatch Dashboard: GCSE-Architecture-Flow-Monitor)
    - ✅ Created alerts for when AI services are not being called (CloudWatch Alarms)
    - ✅ Documented actual vs. intended architecture flow with validation results
    - ✅ Successfully cleared Lambda function caches with `DISABLE_QUESTION_CACHING=true`
    - ✅ Created `test_cache_fix.py` for API-level validation (requires API key configuration)
    - _Requirements: 10.1, 10.2, 19.2_
    - _Reference: deployment-status-summary.md_

- [ ] 16. Enhanced AI Knowledge Base and Instruction System
  - [x] 16.1 Create AI Instruction Repository
    - Set up S3 bucket for AI instruction documents
    - Create detailed prompting guides for InterpretLambda
    - Implement instruction retrieval system for consistent AI behavior
    - Add versioning for instruction updates
    - _Requirements: 1.1, 4.1, 16.1_

  - [ ] 16.2 Implement Comprehensive Question Bank Upload
    - Create dedicated upload system for GCSE PDF papers
    - Process and categorize thousands of example questions
    - Build searchable question database for AI reference
    - Implement question similarity detection to avoid duplicates
    - _Requirements: 2.1, 3.1, 4.1_

  - [ ] 16.3 Enhance AI Context System
    - Expand specification content with detailed examples
    - Create topic-specific instruction sets for better question generation
    - Implement dynamic context loading based on query type
    - Add quality scoring for generated content
    - _Requirements: 4.1, 4.2, 17.1_

  - [ ] 16.4 Build Content Management Interface
    - Create admin interface for uploading and managing content
    - Implement bulk PDF processing with progress tracking
    - Add content validation and quality checks
    - Create content analytics and usage reporting
    - _Requirements: 2.1, 9.1, 10.1_

- [ ] 17. Final Production Readiness Checkpoint
  - Verify all critical issues resolved
  - Confirm AI integration working with unique question generation
  - Validate mathematical notation rendering quality
  - Test with expanded content library and instruction system
  - Ensure system ready for production use

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- Focus on cost optimization throughout implementation (target: £14/month total cost)