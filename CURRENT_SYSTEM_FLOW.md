# Current System Flow - GCSE Question Generator

**Last Updated**: January 13, 2026

## System Architecture Overview

The system has TWO distinct flows:

### Flow 1: EXISTING PRODUCTION FLOW (Currently Deployed)
**Real-time generation with Knowledge Base**

```
User Request
    ↓
API Gateway
    ↓
Generate Lambda
    ↓
Bedrock Service (with KB integration)
    ├─→ Knowledge Base Retrieval (Edexcel content)
    │   └─→ Enriches generation prompt
    ↓
Claude Sonnet generates questions
    ↓
Return to user (30s response time)
```

**Key Points**:
- ✅ **Currently deployed and running in production**
- ✅ Uses Bedrock Knowledge Base for content retrieval
- ✅ Generates questions in real-time per user request
- ✅ Response time: ~30 seconds
- ✅ Cost: ~$1,140/month (high due to real-time AI calls)

### Flow 2: NEW VERIFICATION SYSTEM (Code Complete, Not Yet Deployed)
**Pre-generation with multi-layer verification**

#### Offline Generation (Cron Job - Weekly)
```
EventBridge Schedule (Weekly)
    ↓
Replenishment Lambda
    ├─→ Check inventory per topic
    └─→ Trigger batch generation for depleted topics
        ↓
Batch Generation Lambda
    ├─→ Generate 20-30 questions
    └─→ Send to verification_queue (SQS)
        ↓
Verification Lambda (processes queue)
    ├─→ Layer 1: Deterministic checks (< 100ms)
    ├─→ Layer 2: SymPy verification (< 500ms)
    ├─→ Layer 3: LLM Auditor (< 5s)
    ├─→ Layer 4: KB Alignment (< 3s)
    │   └─→ Uses Bedrock Knowledge Base
    └─→ Layer 5: Dedupe (< 1s)
        ↓
    ┌───┴───┐
    ↓       ↓
PASS    FAIL
    ↓       ↓
verified_question_bank    rejected_questions
```

#### Online Retrieval (Real-Time User Requests)
```
User Request
    ↓
API Gateway
    ↓
Retrieval Lambda
    ↓
DynamoDB Query (verified_question_bank)
    ├─→ Filter: topic, grade, paper_type, difficulty
    └─→ Random selection
        ↓
Return questions instantly (< 100ms)
```

**Key Points**:
- ⚠️ **Code complete but NOT YET DEPLOYED**
- ✅ Uses Bedrock Knowledge Base in verification (Layer 4)
- ✅ Pre-generates and verifies questions offline
- ✅ Serves from verified bank instantly
- ✅ Response time: < 100ms (vs 30s)
- ✅ Cost: ~$402/month (65% reduction)

## Current Production Status

### What's Deployed NOW:
1. ✅ Generate Lambda (real-time generation)
2. ✅ Bedrock Knowledge Base integration
3. ✅ S3 content buckets (specifications, examples)
4. ✅ API Gateway with authentication
5. ✅ Frontend (React app)
6. ✅ DynamoDB tables (users, sessions, feedback)
7. ✅ CloudWatch monitoring

### What's NOT Deployed Yet:
1. ❌ Verification Lambda
2. ❌ Replenishment Lambda
3. ❌ Batch Generation Lambda
4. ❌ Retrieval Lambda
5. ❌ New DynamoDB tables (verified_question_bank, rejected_questions, question_bank_inventory)
6. ❌ SQS verification queue
7. ❌ EventBridge replenishment schedule
8. ❌ Verification dashboards and alarms

## Bedrock Knowledge Base Usage

### Current Production (Flow 1):
**Knowledge Base is used for GENERATION**
- Location: `bedrock_service.py` → `enrich_prompt_with_kb()`
- Purpose: Retrieve Edexcel content to enrich generation prompts
- When: Every user request (real-time)
- Impact: Better question quality, aligned with curriculum

### New Verification System (Flow 2):
**Knowledge Base is used for VERIFICATION**
- Location: `kb_alignment_service.py` → `verify_alignment()`
- Purpose: Verify questions against Edexcel syllabus
- When: During offline verification (weekly cron)
- Impact: Ensures syllabus compliance, catches out-of-scope questions

**Both systems use the same Bedrock Knowledge Base, but for different purposes:**
- Flow 1: KB → Generation (currently deployed)
- Flow 2: KB → Verification (not yet deployed)

## Why Not Deployed Yet?

The verification system is **code-complete and tested**, but deployment is a separate operational step that requires:

1. **Manual deployment execution**:
   ```bash
   python scripts/deploy_question_bank_system.py --environment prod
   ```

2. **Infrastructure provisioning**:
   - Terraform creates new AWS resources
   - DynamoDB tables, Lambda functions, SQS queues
   - EventBridge schedules, CloudWatch alarms

3. **Initial population**:
   - Generate 30,000+ questions
   - Verify through pipeline
   - Populate question bank
   - Takes ~22 hours

4. **Frontend cutover**:
   - Switch from generation to retrieval
   - Gradual rollout (10% → 50% → 100%)
   - Monitor metrics

5. **Validation**:
   - Smoke tests
   - Performance validation
   - User acceptance

**The code is ready - deployment is waiting for you to execute it.**

## Deployment Readiness Checklist

### ✅ Code Complete
- [x] All Lambda functions written
- [x] All services implemented
- [x] All tests passing
- [x] All Terraform modules defined

### ✅ Documentation Complete
- [x] API documentation
- [x] Architecture documentation
- [x] Verification rules
- [x] Troubleshooting guide
- [x] Deployment script

### ⏳ Deployment Pending
- [ ] Run deployment script
- [ ] Provision AWS infrastructure
- [ ] Run initial population
- [ ] Switch frontend to retrieval
- [ ] Monitor and validate

## Next Steps to Deploy

1. **Review deployment plan**: Check `docs/cutover_report.md`
2. **Run deployment script**: `python scripts/deploy_question_bank_system.py --environment staging`
3. **Test in staging**: Validate all components work
4. **Deploy to production**: `python scripts/deploy_question_bank_system.py --environment prod`
5. **Monitor**: Watch CloudWatch dashboards
6. **Iterate**: Follow `docs/question_bank_iteration_plan.md`

## Summary

**Current State**:
- ✅ Production system running (Flow 1: real-time generation with KB)
- ✅ Verification system code complete (Flow 2: pre-generation with verification)
- ⏳ Verification system deployment pending (manual step)

**Bedrock Knowledge Base**:
- ✅ Currently used for generation (Flow 1)
- ✅ Will also be used for verification (Flow 2 when deployed)
- ✅ Same KB, different purposes

**To Deploy**: Run `python scripts/deploy_question_bank_system.py --environment prod`
