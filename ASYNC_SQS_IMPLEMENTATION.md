# Async SQS Implementation for Large Question Generation

## Overview

Implemented SQS-based async processing for large question generation requests (>10 questions) to overcome API Gateway's 29-second timeout limitation.

## Architecture

### Components

1. **SQS Queue** (`gcse-async-generation-queue`)
   - Receives async generation requests
   - 15-minute visibility timeout (3x Lambda timeout)
   - 1-hour message retention
   - Long polling enabled (20 seconds)

2. **AsyncWorkerLambda** (`async_worker_lambda.py`)
   - Processes SQS messages
   - Generates questions using Bedrock
   - Updates job status in DynamoDB
   - Records topic coverage
   - 5-minute timeout, 1024MB memory

3. **GenerateLambda** (updated)
   - Routes requests >10 questions to SQS
   - Creates initial job record in DynamoDB
   - Returns 202 Accepted with job ID and polling info
   - Synchronous processing for ≤10 questions

4. **Frontend Polling** (updated)
   - Polls session endpoint for job status
   - 5-second poll interval
   - 5-minute max wait time
   - Displays progress updates
   - Handles completion and failure states

### Workflow

```
User Request (>10 questions)
    ↓
GenerateLambda
    ↓
Create Session (status: pending)
    ↓
Send Message to SQS
    ↓
Return 202 Accepted (job_id, session_id, polling_info)
    ↓
Frontend Polls Session Endpoint
    ↓
AsyncWorkerLambda (triggered by SQS)
    ↓
Update Status: processing (progress: 10%)
    ↓
Generate Questions (batch processing)
    ↓
Update Status: completed (progress: 100%)
    ↓
Frontend Receives Completed Questions
```

## Implementation Details

### Terraform Changes

**New Resources:**
- `aws_sqs_queue.async_generation_queue` - Main processing queue
- `aws_sqs_queue.async_generation_dlq` - Dead letter queue for failures
- `aws_lambda_function.async_worker_lambda` - Background worker
- `aws_lambda_event_source_mapping.async_worker_sqs_trigger` - SQS trigger
- IAM policies for SQS access

**Updated Resources:**
- `aws_lambda_function.generate_lambda` - Added ASYNC_QUEUE_URL environment variable
- IAM policies for GenerateLambda to send SQS messages

### Backend Changes

**New Files:**
- `src/lambda_handlers/async_worker_lambda.py` - Worker Lambda handler

**Updated Files:**
- `src/lambda_handlers/generate_lambda.py`:
  - Added `handle_async_generation_sqs()` function
  - Routes requests >10 questions to SQS
  - Creates job tracking in DynamoDB

### Frontend Changes

**Updated Files:**
- `frontend/src/services/apiClient.ts`:
  - Updated `pollAsyncGeneration()` with better logging
  - 5-second poll interval (reduced from 10s)
  - Enhanced error handling

- `frontend/src/hooks/useQuestionGeneration.ts`:
  - Updated to handle async responses
  - Shows progress during polling
  - Displays completion status

## Job Status Tracking

### DynamoDB Session Metadata

```json
{
  "job_id": "job_<uuid>",
  "status": "pending|processing|completed|failed",
  "progress": 0-100,
  "topic": "Algebra",
  "tier": "Foundation",
  "count": 20,
  "created_at": "2026-01-08T...",
  "started_at": "2026-01-08T...",
  "completed_at": "2026-01-08T...",
  "question_count": 20,
  "total_marks": 80,
  "generation_time": 45.5,
  "error": "error message if failed"
}
```

### Status Progression

1. **pending** (progress: 0%) - Job created, waiting for worker
2. **processing** (progress: 10-99%) - Worker generating questions
3. **completed** (progress: 100%) - Questions generated successfully
4. **failed** (progress: varies) - Generation failed with error

## Testing

### Property-Based Tests

**test_property_async_sqs.py:**
- Property 32: SQS messages contain all required job parameters
- Property 33: Job status updates persist correctly to DynamoDB
- 6 tests, 100 examples each

**test_property_async_polling.py:**
- Property 34: Frontend polling retrieves correct job status
- Property 35: Polling stops when job completes or fails
- 8 tests, 50-100 examples each

All tests passed successfully.

## Configuration

### Environment Variables

**GenerateLambda:**
- `ASYNC_QUEUE_URL` - SQS queue URL for async requests

**AsyncWorkerLambda:**
- `BEDROCK_MODEL_ID` - Claude Sonnet model ID
- `SESSIONS_TABLE_NAME` - DynamoDB sessions table
- `TOPIC_COVERAGE_TABLE_NAME` - DynamoDB topic coverage table
- `SPECIFICATIONS_BUCKET` - S3 bucket for specifications
- `EXAMPLES_BUCKET` - S3 bucket for examples

### Polling Configuration

```json
{
  "recommended_poll_interval_seconds": 5,
  "max_wait_time_minutes": 5,
  "check_status_endpoint": "/user/sessions/{session_id}"
}
```

## Benefits

1. **No Timeout Limitations** - Can generate 50+ questions without API Gateway timeout
2. **Better User Experience** - Progress updates during generation
3. **Scalability** - Up to 5 concurrent workers processing requests
4. **Reliability** - DLQ for failed messages, retry logic
5. **Cost Efficient** - Only pay for actual processing time

## Testing Recommendations

1. Test with 20, 30, and 50 question requests
2. Verify polling behavior in frontend
3. Test failure scenarios (Bedrock errors, timeouts)
4. Monitor SQS queue metrics
5. Check DynamoDB for job status updates

## Deployment

1. Deploy Terraform changes to create SQS queue and AsyncWorkerLambda
2. Deploy updated GenerateLambda with SQS integration
3. Deploy frontend changes for polling
4. Test with small async request (11 questions)
5. Gradually increase to larger requests (20, 30, 50 questions)

## Monitoring

**CloudWatch Metrics:**
- SQS queue depth
- AsyncWorkerLambda invocations
- AsyncWorkerLambda duration
- AsyncWorkerLambda errors
- DLQ message count

**CloudWatch Logs:**
- `/aws/lambda/gcse-async-worker-lambda-{env}`
- `/aws/lambda/gcse-generate-lambda-{env}`

## Future Enhancements

1. Add progress updates during batch processing (currently only 10% and 100%)
2. Implement job cancellation
3. Add retry logic for partial failures
4. Implement priority queue for urgent requests
5. Add metrics dashboard for async processing
