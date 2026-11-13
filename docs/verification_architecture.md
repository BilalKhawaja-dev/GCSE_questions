# Question Verification System - Architecture Documentation

## System Overview

The Question Verification System is a multi-layer verification pipeline that ensures GCSE Maths questions meet Edexcel standards before entering the question bank. The system operates on a **pre-generation model** where questions are generated and verified offline, then served instantly to users.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│  OFFLINE GENERATION (Cron-Based Replenishment)              │
└─────────────────────────────────────────────────────────────┘
                          ↓
    ┌──────────────────────────────────────────┐
    │  EventBridge Schedule (Weekly)           │
    │  Triggers: Replenishment Lambda          │
    └──────────────────────────────────────────┘
                          ↓
    ┌──────────────────────────────────────────┐
    │  Replenishment Lambda                    │
    │  - Check inventory per topic             │
    │  - Identify depleted topics (<50 Qs)     │
    │  - Trigger batch generation              │
    └──────────────────────────────────────────┘
                          ↓
    ┌──────────────────────────────────────────┐
    │  Batch Generation Lambda                 │
    │  - Generate 20-30 questions              │
    │  - Send to verification queue            │
    └──────────────────────────────────────────┘
                          ↓
    ┌──────────────────────────────────────────┐
    │  SQS Verification Queue                  │
    │  - Async processing                      │
    │  - Dead letter queue for failures        │
    └──────────────────────────────────────────┘
                          ↓
    ┌──────────────────────────────────────────┐
    │  Verification Lambda (Orchestrator)      │
    │  - Runs all verification layers          │
    │  - Aggregates results                    │
    └──────────────────────────────────────────┘
                          ↓
         ┌────────────────┴────────────────┐
         ↓                                  ↓
    [PASS: Store in                   [FAIL: Store in
     verified_question_bank]           rejected_questions]

═══════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────┐
│  ONLINE RETRIEVAL (Real-Time User Requests)                 │
└─────────────────────────────────────────────────────────────┘
                          ↓
    ┌──────────────────────────────────────────┐
    │  User Request → API Gateway              │
    │  POST /retrieve-questions                │
    └──────────────────────────────────────────┘
                          ↓
    ┌──────────────────────────────────────────┐
    │  Retrieval Lambda                        │
    │  - Query DynamoDB (GSI)                  │
    │  - Random selection                      │
    │  - Return instantly (<100ms)             │
    └──────────────────────────────────────────┘
                          ↓
    ┌──────────────────────────────────────────┐
    │  Frontend (React)                        │
    │  - Display questions                     │
    │  - Track usage                           │
    └──────────────────────────────────────────┘
```

## Component Architecture

### 1. Replenishment System (Offline)

#### Replenishment Lambda
**File**: `src/lambda_handlers/replenishment_lambda.py`

**Responsibilities**:
- Triggered by EventBridge schedule (weekly)
- Checks question bank inventory for all topic/grade/paper combinations
- Identifies topics below target threshold (50 verified questions)
- Triggers batch generation for depleted topics
- Monitors verification pass rates
- Sends alerts if generation/verification failing

**Configuration**:
- Schedule: Every 7 days (configurable)
- Timeout: 15 minutes
- Memory: 512 MB
- Environment variables:
  - `TARGET_QUESTIONS_PER_TOPIC`: 50
  - `INVENTORY_TABLE`: question_bank_inventory
  - `BATCH_GENERATION_LAMBDA`: batch_generation_lambda

#### Batch Generation Lambda
**File**: `src/lambda_handlers/batch_generation_lambda.py`

**Responsibilities**:
- Generates 20-30 questions per invocation
- Uses existing Bedrock generation logic
- Sends each question to verification queue
- Tracks batch progress and success rate
- Handles generation failures gracefully
- Parallel generation where possible

**Configuration**:
- Timeout: 15 minutes
- Memory: 1024 MB
- Concurrency: 10 (parallel batches)
- Environment variables:
  - `VERIFICATION_QUEUE_URL`: SQS queue URL
  - `BEDROCK_MODEL_ID`: anthropic.claude-3-5-sonnet-20241022-v2:0

#### Verification Lambda (Orchestrator)
**File**: `src/lambda_handlers/verification_lambda.py`

**Responsibilities**:
- Picks up questions from SQS verification queue
- Orchestrates all verification layers in sequence
- Aggregates results and calculates overall confidence
- Stores PASS questions in verified_question_bank
- Stores FAIL questions in rejected_questions
- Updates question_bank_inventory counts
- Sends to DLQ on repeated failures

**Configuration**:
- Timeout: 5 minutes
- Memory: 2048 MB
- Reserved concurrency: 50
- Environment variables:
  - `VERIFIED_BANK_TABLE`: verified_question_bank
  - `REJECTED_TABLE`: rejected_questions
  - `INVENTORY_TABLE`: question_bank_inventory

### 2. Verification Layers

#### Layer 1: Deterministic Verifier
**File**: `src/services/deterministic_verifier_service.py`

**Fast checks (< 100ms)**:
- JSON schema validation
- MCQ structure rules (4 options, 1 correct, no duplicates)
- Answer format validation
- Paper constraint checks (P1 non-calc rules)

**Pass Criteria**: All checks must pass

#### Layer 2: SymPy Verifier
**File**: `src/services/sympy_verifier_service.py`

**Mathematical verification (< 500ms)**:
- Symbolic equation solving
- Expression simplification and canonical forms
- Distractor validation (ensure wrong answers are wrong)
- Multiple-correct detection

**Supported Question Types**:
- Linear equations, quadratic equations
- Simultaneous equations
- Factorising, expanding
- Surds, fractions, percentages
- Pythagoras, basic trig

**Pass Criteria**: 
- Exact answers: `simplify(answer - key) == 0`
- Numeric answers: `abs(answer - key) <= tolerance`
- No multiple-correct scenarios

#### Layer 3: LLM Auditor
**File**: `src/services/llm_auditor_service.py`

**Semantic validation (< 5s)**:
- Independent solve (without seeing answer key)
- Ambiguity detection
- Wording checks (missing units, insufficient info)
- Paper constraint verification

**Pass Criteria**:
- Confidence >= 0.75
- Agreement = true
- Ambiguity = "none"
- Issues array empty or minor

#### Layer 4: KB Alignment
**File**: `src/services/kb_alignment_service.py`

**Retrieval-grounded verification (< 3s)**:
- Source alignment check (answer aligns with KB material)
- Syllabus compliance check (within Edexcel 1MA1 scope)

**Pass Criteria**:
- Source support confidence >= 0.7
- Syllabus compliance confidence >= 0.7

#### Layer 5: Deduplication
**File**: `src/services/dedupe_service.py`

**Similarity detection (< 1s)**:
- Embedding generation (Titan Embed v2)
- Cosine similarity calculation
- Threshold: reject if similarity > 0.85

**Pass Criteria**: Max similarity <= 0.85

### 3. Retrieval System (Online)

#### Retrieval Lambda
**File**: `src/lambda_handlers/retrieval_lambda.py`

**Responsibilities**:
- Handle user requests for questions
- Query DynamoDB with GSI (topic_grade_paper-difficulty-index)
- Random selection from matching questions
- Track usage (increment times_served)
- Fast response (<100ms target)

**Configuration**:
- Timeout: 30 seconds
- Memory: 512 MB
- Reserved concurrency: 100
- Environment variables:
  - `VERIFIED_BANK_TABLE`: verified_question_bank
  - `CACHE_TTL`: 300 (5 minutes)

### 4. Data Storage

#### DynamoDB Tables

**verified_question_bank** (Main Table)
- Partition key: `question_id` (UUID)
- Sort key: `topic_grade_paper` (composite)
- GSI: `topic_grade_paper-difficulty-index` for fast queries
- Stores: Question content, verification metadata, embeddings, usage tracking

**rejected_questions** (Analysis Table)
- Partition key: `question_id` (UUID)
- Stores: Failed questions with failure reasons for analysis

**question_bank_inventory** (Monitoring Table)
- Partition key: `topic_grade_paper` (composite)
- Stores: Verified count, target count, generation pass rate

#### SQS Queues

**verification_queue**
- Visibility timeout: 60 seconds
- Message retention: 14 days
- Dead letter queue: verification_dlq
- Max receive count: 3

**verification_dlq** (Dead Letter Queue)
- Stores failed verifications for manual review
- Retention: 14 days

### 5. Monitoring & Observability

#### CloudWatch Metrics
- `VerificationPassRate` by layer
- `VerificationLatency` by layer
- `QuestionBankInventory` per topic
- `RetrievalLatency` (p50, p95, p99)
- `GenerationBatchSuccessRate`

#### CloudWatch Dashboards
- Question Bank Health Dashboard
- Verification Quality Dashboard
- User Experience Dashboard

#### CloudWatch Alarms
- Low inventory alarm (< 20 questions per topic)
- Low verification pass rate (< 50%)
- High retrieval latency (> 200ms)
- Generation failure rate (> 20%)

## Data Flow

### Offline Generation Flow

```
1. EventBridge triggers replenishment_lambda (weekly)
   ↓
2. Check inventory for each topic/grade/paper
   ↓
3. For topics < 50 verified questions:
   Trigger batch_generation_lambda
   ↓
4. Generate 20-30 questions
   Send each to verification_queue
   ↓
5. Verification Lambda processes each:
   - Deterministic checks
   - SymPy verification
   - LLM auditor
   - KB alignment
   - Dedupe check
   ↓
6. Aggregate results:
   - PASS: Store in verified_question_bank
   - FAIL: Store in rejected_questions
   ↓
7. Update question_bank_inventory
```

### Online Retrieval Flow

```
1. User requests questions via API
   ↓
2. API Gateway → Retrieval Lambda
   ↓
3. Query DynamoDB:
   - Filter: topic, grade, paper_type, difficulty
   - Use GSI for fast lookup
   ↓
4. Random selection from matching questions
   ↓
5. Return questions instantly (<100ms)
   ↓
6. Frontend displays questions
```

## Scaling Considerations

### Horizontal Scaling

**Lambda Concurrency**:
- Replenishment Lambda: 1 (single cron job)
- Batch Generation Lambda: 10 (parallel batches)
- Verification Lambda: 50 (parallel verifications)
- Retrieval Lambda: 100 (high user traffic)

**DynamoDB Capacity**:
- On-demand pricing for variable load
- Auto-scaling for predictable patterns
- GSI for efficient queries

### Vertical Scaling

**Memory Allocation**:
- Replenishment: 512 MB (lightweight)
- Batch Generation: 1024 MB (Bedrock calls)
- Verification: 2048 MB (multiple AI layers)
- Retrieval: 512 MB (simple queries)

### Performance Optimization

**Caching**:
- API Gateway cache (5 min TTL)
- Lambda function cache (warm starts)
- DynamoDB DAX (optional for high traffic)

**Batch Processing**:
- Generate 20-30 questions per batch
- Parallel verification (50 concurrent)
- Efficient embedding generation

## Security Architecture

### Authentication & Authorization
- JWT-based authentication
- IAM roles for Lambda execution
- VPC endpoints for private communication

### Data Protection
- Encryption at rest (DynamoDB, S3)
- Encryption in transit (TLS 1.2+)
- No PII in question content

### Network Security
- API Gateway with WAF
- Lambda in VPC (optional)
- Security groups and NACLs

## Disaster Recovery

### Backup Strategy
- DynamoDB point-in-time recovery (enabled)
- Daily snapshots of question bank
- S3 versioning for embeddings

### Failover Strategy
- Multi-AZ deployment
- Fallback to generation endpoint if bank empty
- Dead letter queue for failed verifications

### Recovery Procedures
1. Restore DynamoDB from snapshot
2. Replay failed verifications from DLQ
3. Trigger emergency replenishment
4. Monitor metrics for recovery

## Cost Optimization

### Cost Breakdown (Monthly)

**Compute**:
- Lambda executions: ~$50
- Bedrock API calls: ~$200
- Total compute: ~$250

**Storage**:
- DynamoDB storage: ~$30
- S3 embeddings: ~$10
- Total storage: ~$40

**Data Transfer**:
- API Gateway: ~$20
- CloudWatch logs: ~$10
- Total transfer: ~$30

**Total Monthly Cost**: ~$320

### Cost Savings vs Real-Time Generation

**Before (Real-Time)**:
- Every user request triggers Bedrock call
- 10,000 requests/day × $0.003 = $30/day = $900/month

**After (Pre-Generation)**:
- Weekly batch generation: ~$20/week = $80/month
- User requests: $0 AI cost (just DynamoDB)
- **Savings**: $820/month (91% reduction)

## Future Enhancements

1. **Diagram Validation**: OCR + geometric reasoning
2. **Proof-Style Questions**: More sophisticated LLM reasoning
3. **Active Learning**: Use user feedback to improve verification
4. **Batch Verification**: Verify multiple questions in parallel
5. **Confidence Calibration**: ML model to predict user satisfaction
6. **Multi-Region Deployment**: Global distribution for lower latency
7. **Advanced Caching**: Redis/ElastiCache for hot questions

## References

- [Retrieval API Documentation](./retrieval_api.md)
- [Verification Rules](./verification_rules.md)
- [Troubleshooting Guide](./troubleshooting_guide.md)
- [Verification Runbook](./verification_runbook.md)
