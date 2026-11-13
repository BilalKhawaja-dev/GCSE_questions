# Question Verification System - Operations Runbook

## Overview

This runbook provides procedures for responding to alerts, troubleshooting common issues, and maintaining the Question Verification System.

## Table of Contents

1. [Alert Response Procedures](#alert-response-procedures)
2. [Common Issues and Resolutions](#common-issues-and-resolutions)
3. [Escalation Paths](#escalation-paths)
4. [Manual Intervention Procedures](#manual-intervention-procedures)
5. [Monitoring and Diagnostics](#monitoring-and-diagnostics)

---

## Alert Response Procedures

### Low Inventory Alert (< 20 questions per topic)

**Severity:** High  
**Alert Condition:** Any topic/grade/paper combination has fewer than 20 verified questions

**Immediate Actions:**
1. Check CloudWatch dashboard for affected topics
2. Verify replenishment cron job is running (check last execution time)
3. Check verification pass rate for affected topics
4. If pass rate is normal (>60%), trigger manual replenishment
5. If pass rate is low (<50%), investigate verification failures

**Investigation Steps:**
```bash
# Check inventory for specific topic
aws dynamodb get-item \
  --table-name question_bank_inventory \
  --key '{"topic_grade_paper": {"S": "algebra_foundation_P1"}}'

# Check recent replenishment executions
aws logs filter-log-events \
  --log-group-name /aws/lambda/replenishment-lambda \
  --start-time $(date -d '24 hours ago' +%s)000 \
  --filter-pattern "replenishment_triggered"
```

**Resolution:**
- Trigger manual replenishment: `aws lambda invoke --function-name replenishment-lambda`
- If verification is failing, see "Low Verification Pass Rate" section

---

### Low Verification Pass Rate (< 50%)

**Severity:** High  
**Alert Condition:** Overall verification pass rate drops below 50%

**Immediate Actions:**
1. Check which verification layer is failing most
2. Review recent failure reasons in CloudWatch Logs
3. Check if issue is specific to certain topics or widespread
4. Verify all verification services are operational

**Investigation Steps:**
```bash
# Check verification failures by layer
aws cloudwatch get-metric-statistics \
  --namespace GCSE/QuestionVerification \
  --metric-name VerificationPassRate \
  --dimensions Name=Layer,Value=Deterministic \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average

# Check recent verification failures
aws logs filter-log-events \
  --log-group-name /aws/lambda/verification-lambda \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --filter-pattern "FAIL"
```

**Common Causes:**
- **Deterministic layer failing:** Generation quality issue, check generate_lambda
- **SymPy layer failing:** Math parsing issues, may need tolerance adjustment
- **LLM auditor failing:** Low confidence, check Bedrock service status
- **KB alignment failing:** Knowledge base incomplete or unavailable
- **Dedupe failing:** Similarity threshold too strict

**Resolution:**
- Adjust verification thresholds if appropriate (requires code change)
- Investigate generation quality if deterministic checks failing
- Check Bedrock service status if LLM auditor failing
- Temporarily disable non-critical layers if needed (KB alignment)

---

### High Retrieval Latency (> 200ms)

**Severity:** Medium  
**Alert Condition:** Average retrieval latency exceeds 200ms

**Immediate Actions:**
1. Check DynamoDB table performance metrics
2. Verify GSI (Global Secondary Index) is being used
3. Check for hot partitions in DynamoDB
4. Review Lambda function performance

**Investigation Steps:**
```bash
# Check DynamoDB metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name ConsumedReadCapacityUnits \
  --dimensions Name=TableName,Value=verified_question_bank \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum

# Check Lambda execution time
aws logs filter-log-events \
  --log-group-name /aws/lambda/retrieval-lambda \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --filter-pattern "[timestamp, request_id, level=REPORT]"
```

**Resolution:**
- Increase DynamoDB read capacity if throttling
- Optimize query patterns (ensure GSI usage)
- Add caching layer if needed (ElastiCache)
- Review Lambda memory allocation

---

### Generation Failure Rate (> 20%)

**Severity:** High  
**Alert Condition:** Batch generation pass rate drops below 80%

**Immediate Actions:**
1. Check Bedrock service status
2. Review generation prompts and parameters
3. Check for specific topics with high failure rates
4. Verify Knowledge Base is accessible

**Investigation Steps:**
```bash
# Check batch generation logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/batch-generation-lambda \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --filter-pattern "ERROR"

# Check Bedrock API errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/generate-lambda \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --filter-pattern "BedrockError"
```

**Resolution:**
- Check Bedrock service limits and quotas
- Review and adjust generation prompts if needed
- Verify Knowledge Base sync status
- Increase retry logic if transient failures

---

### High User Issue Reports (> 5%)

**Severity:** Medium  
**Alert Condition:** False positive rate exceeds 5%

**Immediate Actions:**
1. Review recent issue reports in DynamoDB
2. Identify common patterns in reported issues
3. Check if specific verification layer is causing false positives
4. Analyze affected question types

**Investigation Steps:**
```bash
# Query recent issue reports
aws dynamodb query \
  --table-name question_feedback \
  --index-name issue-reported-index \
  --key-condition-expression "issue_reported = :true" \
  --expression-attribute-values '{":true": {"BOOL": true}}' \
  --limit 50

# Check issue types distribution
aws logs filter-log-events \
  --log-group-name /aws/lambda/feedback-lambda \
  --start-time $(date -d '24 hours ago' +%s)000 \
  --filter-pattern "issue_reported=true"
```

**Resolution:**
- Adjust verification thresholds if systematic false positives
- Review specific questions being reported
- Update verification rules based on patterns
- Consider manual review process for borderline cases

---

### Replenishment Failure

**Severity:** Critical  
**Alert Condition:** Replenishment cron job hasn't executed in 7 days

**Immediate Actions:**
1. Check EventBridge rule status
2. Verify Lambda function is not disabled
3. Check for Lambda execution errors
4. Manually trigger replenishment if needed

**Investigation Steps:**
```bash
# Check EventBridge rule status
aws events describe-rule --name replenishment-schedule

# Check recent Lambda invocations
aws lambda get-function --function-name replenishment-lambda

# Check for execution errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/replenishment-lambda \
  --start-time $(date -d '7 days ago' +%s)000 \
  --filter-pattern "ERROR"
```

**Resolution:**
- Re-enable EventBridge rule if disabled
- Fix Lambda function errors if present
- Manually invoke replenishment: `aws lambda invoke --function-name replenishment-lambda`
- Check IAM permissions for EventBridge → Lambda

---

## Common Issues and Resolutions

### Issue: Questions Not Being Served

**Symptoms:**
- Users report no questions available
- Retrieval lambda returning empty results
- No questions served metric drops to zero

**Diagnosis:**
```bash
# Check question bank inventory
aws dynamodb scan \
  --table-name verified_question_bank \
  --select COUNT

# Check retrieval lambda logs
aws logs tail /aws/lambda/retrieval-lambda --follow
```

**Resolution:**
1. Verify question bank has questions: `aws dynamodb scan --table-name verified_question_bank --select COUNT`
2. Check retrieval lambda for errors
3. Verify DynamoDB table permissions
4. Trigger manual replenishment if bank is empty

---

### Issue: Verification Taking Too Long

**Symptoms:**
- Verification latency > 15 seconds
- SQS queue backing up
- Questions not appearing in bank

**Diagnosis:**
```bash
# Check SQS queue depth
aws sqs get-queue-attributes \
  --queue-url <verification-queue-url> \
  --attribute-names ApproximateNumberOfMessages

# Check verification lambda duration
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=verification-lambda \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average,Maximum
```

**Resolution:**
1. Increase Lambda timeout if needed (current: 60s)
2. Increase Lambda memory allocation for better performance
3. Optimize verification layers (disable non-critical ones temporarily)
4. Increase SQS visibility timeout
5. Add more Lambda concurrency

---

### Issue: Duplicate Questions Appearing

**Symptoms:**
- Users report seeing similar questions
- Dedupe layer not catching duplicates
- High similarity scores in logs

**Diagnosis:**
```bash
# Check dedupe service logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/verification-lambda \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --filter-pattern "dedupe"

# Check similarity threshold
aws logs filter-log-events \
  --log-group-name /aws/lambda/verification-lambda \
  --filter-pattern "similarity"
```

**Resolution:**
1. Verify embeddings are being generated correctly
2. Check similarity threshold (default: 0.85)
3. Regenerate embeddings for existing questions if needed
4. Adjust threshold if too lenient

---

## Escalation Paths

### Level 1: On-Call Engineer
- **Responsibility:** Initial response, basic troubleshooting
- **Escalate to Level 2 if:**
  - Issue persists after 30 minutes
  - Multiple critical alarms firing
  - Requires code changes or infrastructure updates

### Level 2: Senior Engineer / Team Lead
- **Responsibility:** Complex troubleshooting, code fixes, infrastructure changes
- **Escalate to Level 3 if:**
  - AWS service outage suspected
  - Requires architectural changes
  - Security incident

### Level 3: Engineering Manager / AWS Support
- **Responsibility:** Architectural decisions, AWS support engagement
- **Contact:** AWS Support (Enterprise tier)

---

## Manual Intervention Procedures

### Manually Trigger Replenishment

```bash
# Invoke replenishment lambda
aws lambda invoke \
  --function-name replenishment-lambda \
  --payload '{}' \
  response.json

# Check response
cat response.json
```

### Manually Verify a Question

```bash
# Send question to verification queue
aws sqs send-message \
  --queue-url <verification-queue-url> \
  --message-body '{
    "question_id": "uuid",
    "question_data": {...}
  }'
```

### Manually Add Question to Verified Bank

```bash
# Add question directly to verified bank (use with caution)
aws dynamodb put-item \
  --table-name verified_question_bank \
  --item file://question.json
```

### Clear Verification Queue

```bash
# Purge verification queue (use with extreme caution)
aws sqs purge-queue --queue-url <verification-queue-url>
```

### Regenerate Embeddings

```bash
# Run embedding generation script
python scripts/generate_embeddings.py --batch-size 100
```

---

## Monitoring and Diagnostics

### Key Dashboards

1. **Question Bank Health Dashboard**
   - URL: CloudWatch → Dashboards → question-bank-health
   - Monitors: Inventory levels, verified count, replenishment frequency

2. **Verification Quality Dashboard**
   - URL: CloudWatch → Dashboards → verification-quality
   - Monitors: Pass rates, failure reasons, confidence scores

3. **User Experience Dashboard**
   - URL: CloudWatch → Dashboards → user-experience
   - Monitors: Retrieval latency, questions served, user feedback

### Key Metrics to Watch

- **TotalVerifiedQuestions:** Should be growing over time
- **AveragePassRate:** Should stay above 60%
- **RetrievalLatency:** Should stay below 100ms (target)
- **FalsePositiveRate:** Should stay below 5%
- **ReplenishmentExecutionCount:** Should be 1 per week

### Log Groups

- `/aws/lambda/replenishment-lambda` - Replenishment cron job
- `/aws/lambda/batch-generation-lambda` - Batch generation
- `/aws/lambda/verification-lambda` - Verification pipeline
- `/aws/lambda/retrieval-lambda` - Question retrieval
- `/aws/lambda/feedback-lambda` - User feedback

### Useful CloudWatch Insights Queries

**Find verification failures:**
```
fields @timestamp, @message
| filter @message like /FAIL/
| sort @timestamp desc
| limit 100
```

**Find slow verifications:**
```
fields @timestamp, @message, duration
| filter @type = "REPORT"
| filter duration > 10000
| sort duration desc
| limit 50
```

**Find high similarity duplicates:**
```
fields @timestamp, @message
| filter @message like /similarity/
| parse @message /similarity: (?<sim>[0-9.]+)/
| filter sim > 0.85
| sort @timestamp desc
```

---

## Contact Information

- **On-Call Engineer:** PagerDuty rotation
- **Team Lead:** [Name] - [Email]
- **Engineering Manager:** [Name] - [Email]
- **AWS Support:** Enterprise Support Portal

---

## Revision History

| Date | Version | Changes | Author |
|------|---------|---------|--------|
| 2026-01-13 | 1.0 | Initial runbook creation | System |

