# Question Verification System - Troubleshooting Guide

## Overview

This guide provides step-by-step troubleshooting procedures for common issues with the Question Verification System.

## Quick Reference

| Issue | Severity | First Action |
|-------|----------|--------------|
| Low question bank inventory | High | Check replenishment cron |
| High retrieval latency | High | Check DynamoDB performance |
| Low verification pass rate | Medium | Review verification metrics |
| Generation failures | Medium | Check Bedrock service status |
| User-reported issues | Medium | Review specific questions |
| Verification queue backlog | Low | Check Lambda concurrency |

## Common Issues

### Issue 1: Low Question Bank Inventory

**Symptoms**:
- CloudWatch alarm: "LowInventoryAlarm" triggered
- Retrieval API returns 404 for specific topics
- Users falling back to generation endpoint

**Diagnosis**:

1. Check inventory table:
```bash
aws dynamodb scan \
  --table-name question_bank_inventory \
  --filter-expression "verified_count < :threshold" \
  --expression-attribute-values '{":threshold": {"N": "20"}}'
```

2. Check replenishment cron status:
```bash
aws events list-rules --name-prefix "replenishment"
aws lambda get-function --function-name replenishment_lambda
```

3. Check recent replenishment runs:
```bash
aws logs tail /aws/lambda/replenishment_lambda --since 7d
```

**Resolution**:

**Option A: Trigger Manual Replenishment**
```bash
aws lambda invoke \
  --function-name replenishment_lambda \
  --payload '{}' \
  response.json
```

**Option B: Increase Target Threshold**
```bash
# Update environment variable
aws lambda update-function-configuration \
  --function-name replenishment_lambda \
  --environment Variables={TARGET_QUESTIONS_PER_TOPIC=100}
```

**Option C: Increase Generation Frequency**
```bash
# Update EventBridge schedule from weekly to daily
aws events put-rule \
  --name replenishment-schedule \
  --schedule-expression "rate(1 day)"
```

**Prevention**:
- Monitor inventory metrics daily
- Set up alerts for inventory < 30
- Increase target threshold for high-traffic topics

---

### Issue 2: High Retrieval Latency

**Symptoms**:
- CloudWatch alarm: "HighRetrievalLatency" triggered
- API response times > 200ms
- User complaints about slow question loading

**Diagnosis**:

1. Check CloudWatch metrics:
```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=retrieval_lambda \
  --start-time 2026-01-13T00:00:00Z \
  --end-time 2026-01-13T23:59:59Z \
  --period 3600 \
  --statistics Average,Maximum
```

2. Check DynamoDB performance:
```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name SuccessfulRequestLatency \
  --dimensions Name=TableName,Value=verified_question_bank \
  --start-time 2026-01-13T00:00:00Z \
  --end-time 2026-01-13T23:59:59Z \
  --period 3600 \
  --statistics Average,Maximum
```

3. Check Lambda cold starts:
```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/retrieval_lambda \
  --filter-pattern "REPORT" \
  --start-time $(date -d '1 hour ago' +%s)000
```

**Resolution**:

**Option A: Increase Lambda Memory**
```bash
aws lambda update-function-configuration \
  --function-name retrieval_lambda \
  --memory-size 1024  # Increase from 512 MB
```

**Option B: Enable Provisioned Concurrency**
```bash
aws lambda put-provisioned-concurrency-config \
  --function-name retrieval_lambda \
  --provisioned-concurrent-executions 10
```

**Option C: Enable DynamoDB DAX**
```bash
# Create DAX cluster for caching
aws dax create-cluster \
  --cluster-name question-bank-cache \
  --node-type dax.t3.small \
  --replication-factor 3
```

**Option D: Optimize Query**
- Review GSI usage
- Add caching layer (API Gateway cache)
- Reduce response payload size

**Prevention**:
- Monitor p95/p99 latency metrics
- Set up alerts for latency > 150ms
- Regular performance testing

---

### Issue 3: Low Verification Pass Rate

**Symptoms**:
- CloudWatch alarm: "LowVerificationPassRate" triggered
- Pass rate < 50%
- Many questions in rejected_questions table

**Diagnosis**:

1. Check pass rate by layer:
```bash
aws cloudwatch get-metric-statistics \
  --namespace QuestionVerification \
  --metric-name PassRate \
  --dimensions Name=Layer,Value=LLMAuditor \
  --start-time 2026-01-13T00:00:00Z \
  --end-time 2026-01-13T23:59:59Z \
  --period 3600 \
  --statistics Average
```

2. Analyze rejected questions:
```bash
aws dynamodb scan \
  --table-name rejected_questions \
  --filter-expression "rejected_at > :timestamp" \
  --expression-attribute-values '{":timestamp": {"S": "2026-01-13T00:00:00Z"}}'
```

3. Check common failure reasons:
```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/verification_lambda \
  --filter-pattern "FAIL" \
  --start-time $(date -d '1 day ago' +%s)000 | \
  jq '.events[].message' | sort | uniq -c | sort -rn
```

**Resolution**:

**Option A: Adjust LLM Confidence Threshold**
```python
# In llm_auditor_service.py
CONFIDENCE_THRESHOLD = 0.70  # Lower from 0.75
```

**Option B: Adjust SymPy Tolerance**
```python
# In sympy_verifier_service.py
NUMERIC_TOLERANCE = 1e-8  # Increase from 1e-10
```

**Option C: Relax Dedupe Threshold**
```python
# In dedupe_service.py
SIMILARITY_THRESHOLD = 0.90  # Increase from 0.85
```

**Option D: Improve Generation Prompts**
- Review common failure patterns
- Update generation prompts to avoid issues
- Add examples of good questions

**Prevention**:
- Monitor pass rates daily
- Weekly review of rejected questions
- Continuous prompt improvement

---

### Issue 4: Generation Failures

**Symptoms**:
- CloudWatch alarm: "HighGenerationFailureRate" triggered
- Batch generation lambda errors
- Empty verification queue

**Diagnosis**:

1. Check Lambda errors:
```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/batch_generation_lambda \
  --filter-pattern "ERROR" \
  --start-time $(date -d '1 hour ago' +%s)000
```

2. Check Bedrock service status:
```bash
aws bedrock get-model-invocation-logging-configuration
```

3. Check Lambda throttling:
```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Throttles \
  --dimensions Name=FunctionName,Value=batch_generation_lambda \
  --start-time 2026-01-13T00:00:00Z \
  --end-time 2026-01-13T23:59:59Z \
  --period 3600 \
  --statistics Sum
```

**Resolution**:

**Option A: Check Bedrock Quotas**
```bash
aws service-quotas get-service-quota \
  --service-code bedrock \
  --quota-code L-12345678
```

**Option B: Increase Lambda Timeout**
```bash
aws lambda update-function-configuration \
  --function-name batch_generation_lambda \
  --timeout 900  # 15 minutes
```

**Option C: Reduce Batch Size**
```python
# In batch_generation_lambda.py
BATCH_SIZE = 10  # Reduce from 20-30
```

**Option D: Add Retry Logic**
```python
# In batch_generation_lambda.py
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def generate_question(...):
    ...
```

**Prevention**:
- Monitor Bedrock API errors
- Set up alerts for throttling
- Implement exponential backoff

---

### Issue 5: Verification Queue Backlog

**Symptoms**:
- SQS queue depth increasing
- Verification latency increasing
- Questions not appearing in bank

**Diagnosis**:

1. Check queue depth:
```bash
aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/123456789/verification_queue \
  --attribute-names ApproximateNumberOfMessages,ApproximateNumberOfMessagesNotVisible
```

2. Check Lambda concurrency:
```bash
aws lambda get-function-concurrency \
  --function-name verification_lambda
```

3. Check dead letter queue:
```bash
aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/123456789/verification_dlq \
  --attribute-names ApproximateNumberOfMessages
```

**Resolution**:

**Option A: Increase Lambda Concurrency**
```bash
aws lambda put-function-concurrency \
  --function-name verification_lambda \
  --reserved-concurrent-executions 100  # Increase from 50
```

**Option B: Increase Batch Size**
```bash
aws lambda update-event-source-mapping \
  --uuid <mapping-uuid> \
  --batch-size 10  # Process more messages per invocation
```

**Option C: Optimize Verification Layers**
- Profile slow layers
- Add caching where beneficial
- Parallelize independent checks

**Prevention**:
- Monitor queue depth metrics
- Set up alerts for depth > 100
- Regular performance optimization

---

### Issue 6: User-Reported Issues

**Symptoms**:
- Users reporting incorrect questions
- Feedback widget showing high issue rate
- False positive rate > 10%

**Diagnosis**:

1. Check user feedback:
```bash
aws dynamodb query \
  --table-name user_feedback \
  --key-condition-expression "feedback_type = :type" \
  --expression-attribute-values '{":type": {"S": "issue_report"}}'
```

2. Review specific questions:
```bash
aws dynamodb get-item \
  --table-name verified_question_bank \
  --key '{"question_id": {"S": "<question-id>"}}'
```

3. Check verification results:
```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/verification_lambda \
  --filter-pattern "<question-id>"
```

**Resolution**:

**Option A: Remove Problematic Question**
```bash
aws dynamodb delete-item \
  --table-name verified_question_bank \
  --key '{"question_id": {"S": "<question-id>"}}'
```

**Option B: Adjust Verification Thresholds**
- If false positives high: Raise thresholds
- If false negatives high: Lower thresholds
- Document threshold changes

**Option C: Improve Verification Rules**
- Add new validation rules
- Update LLM prompts
- Enhance SymPy checks

**Prevention**:
- Monitor user feedback daily
- Weekly review of reported issues
- Continuous improvement of verification

---

## Debug Procedures

### Procedure 1: Trace Question Through Pipeline

**Purpose**: Follow a specific question through the entire verification pipeline.

**Steps**:

1. Find question in generation logs:
```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/batch_generation_lambda \
  --filter-pattern "<question-id>"
```

2. Check verification queue:
```bash
aws sqs receive-message \
  --queue-url https://sqs.us-east-1.amazonaws.com/123456789/verification_queue \
  --max-number-of-messages 10 | \
  jq '.Messages[] | select(.Body | contains("<question-id>"))'
```

3. Check verification logs:
```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/verification_lambda \
  --filter-pattern "<question-id>"
```

4. Check final storage:
```bash
# Check verified bank
aws dynamodb get-item \
  --table-name verified_question_bank \
  --key '{"question_id": {"S": "<question-id>"}}'

# Check rejected table
aws dynamodb get-item \
  --table-name rejected_questions \
  --key '{"question_id": {"S": "<question-id>"}}'
```

### Procedure 2: Analyze Verification Layer Performance

**Purpose**: Identify slow verification layers.

**Steps**:

1. Enable X-Ray tracing:
```bash
aws lambda update-function-configuration \
  --function-name verification_lambda \
  --tracing-config Mode=Active
```

2. Run sample verifications:
```bash
aws lambda invoke \
  --function-name verification_lambda \
  --payload file://test_question.json \
  response.json
```

3. Analyze X-Ray traces:
```bash
aws xray get-trace-summaries \
  --start-time 2026-01-13T00:00:00Z \
  --end-time 2026-01-13T23:59:59Z \
  --filter-expression 'service("verification_lambda")'
```

4. Identify bottlenecks:
- Look for subsegments with high duration
- Check for sequential vs parallel execution
- Identify optimization opportunities

### Procedure 3: Test Verification Rules

**Purpose**: Validate verification rules with test questions.

**Steps**:

1. Create test question:
```json
{
  "stem": "Solve 2x + 5 = 13",
  "options": ["x = 4", "x = 9", "x = 3", "x = 8"],
  "correct_answer": "A",
  "rationale": "Subtract 5 from both sides: 2x = 8. Divide by 2: x = 4",
  "topic": "algebra",
  "grade": "foundation",
  "paper_type": "P1",
  "difficulty": 5
}
```

2. Run through verification:
```bash
python scripts/test_verification.py test_question.json
```

3. Review results:
```bash
cat verification_results.json | jq '.'
```

4. Adjust rules as needed

---

## Log Locations

### Lambda Logs
- Replenishment: `/aws/lambda/replenishment_lambda`
- Batch Generation: `/aws/lambda/batch_generation_lambda`
- Verification: `/aws/lambda/verification_lambda`
- Retrieval: `/aws/lambda/retrieval_lambda`

### CloudWatch Metrics
- Namespace: `QuestionVerification`
- Metrics: `PassRate`, `Latency`, `ErrorRate`, `QueueDepth`

### DynamoDB Tables
- Verified Bank: `verified_question_bank`
- Rejected Questions: `rejected_questions`
- Inventory: `question_bank_inventory`

### SQS Queues
- Verification Queue: `verification_queue`
- Dead Letter Queue: `verification_dlq`

---

## Metric Interpretation

### Pass Rate Metrics

**Healthy Range**: 60-80%

- **< 50%**: Too strict - adjust thresholds
- **50-60%**: Low but acceptable - monitor
- **60-80%**: Healthy - optimal range
- **80-90%**: High - may be too lenient
- **> 90%**: Too lenient - tighten thresholds

### Latency Metrics

**Target**: < 100ms (retrieval), < 10s (verification)

- **p50**: Median latency (should be < 50ms for retrieval)
- **p95**: 95th percentile (should be < 100ms for retrieval)
- **p99**: 99th percentile (should be < 200ms for retrieval)

### Error Rate Metrics

**Target**: < 1%

- **< 1%**: Healthy
- **1-5%**: Elevated - investigate
- **> 5%**: Critical - immediate action

---

## Escalation Paths

### Severity Levels

**P1 (Critical)**: System down, no questions available
- **Response Time**: 15 minutes
- **Escalate To**: On-call engineer
- **Action**: Immediate investigation and fix

**P2 (High)**: Degraded performance, high error rate
- **Response Time**: 1 hour
- **Escalate To**: Team lead
- **Action**: Investigation and resolution within 4 hours

**P3 (Medium)**: Low pass rate, user reports
- **Response Time**: 4 hours
- **Escalate To**: Team member
- **Action**: Investigation and resolution within 1 day

**P4 (Low)**: Minor issues, optimization opportunities
- **Response Time**: 1 day
- **Escalate To**: Team backlog
- **Action**: Plan for next sprint

---

## Contact Information

- **On-Call Engineer**: Slack #on-call-verification
- **Team Lead**: Slack #verification-team
- **AWS Support**: support.aws.amazon.com
- **Documentation**: https://docs.gcse-question-generator.com

---

## References

- [Verification Architecture](./verification_architecture.md)
- [Verification Rules](./verification_rules.md)
- [Verification Runbook](./verification_runbook.md)
- [Retrieval API Documentation](./retrieval_api.md)
