# Lessons Learned - Question Verification System

## Overview

This document captures lessons learned during the design, implementation, and deployment of the Question Verification System. The goal is to document what went well, what could be improved, and recommendations for future projects.

## Project Summary

**Duration**: 10 weeks (November 2025 - January 2026)
**Team Size**: 4 engineers
**Outcome**: Successful deployment to production
**Impact**: 65% cost reduction, 55% latency improvement

## What Went Well ✅

### 1. Pre-Generation Architecture Decision

**Decision**: Generate and verify questions offline, serve from pre-verified bank

**Why It Worked**:
- Dramatically reduced user-facing latency (100ms → 45ms)
- Eliminated AI costs for user requests
- Allowed thorough verification without time pressure
- Enabled batch processing for efficiency

**Lesson**: For AI-powered systems, consider pre-generation when:
- Quality is more important than real-time customization
- User requests are predictable
- Verification is expensive/slow
- Cost optimization is a priority

### 2. Multi-Layer Verification Approach

**Decision**: Use 5 independent verification layers (Deterministic, SymPy, LLM, KB, Dedupe)

**Why It Worked**:
- Each layer caught different types of issues
- Redundancy improved overall quality
- Graceful degradation when layers failed
- Easy to tune individual layers

**Lesson**: For quality-critical systems:
- Use multiple independent validation methods
- Start with cheap/fast checks, escalate to expensive ones
- Make layers optional/advisory where appropriate
- Monitor each layer's effectiveness separately

### 3. Gradual Rollout Strategy

**Decision**: Roll out frontend switch gradually (10% → 50% → 100%)

**Why It Worked**:
- Caught issues early with minimal user impact
- Built confidence before full cutover
- Easy to rollback if needed
- Validated performance under real load

**Lesson**: For major system changes:
- Always use gradual rollout
- Monitor metrics closely at each stage
- Have clear rollback criteria
- Don't rush to 100%

### 4. Comprehensive Monitoring

**Decision**: Implement CloudWatch dashboards, alarms, and metrics from day 1

**Why It Worked**:
- Caught issues before users noticed
- Provided visibility into system health
- Enabled data-driven decisions
- Simplified troubleshooting

**Lesson**: Monitoring is not optional:
- Implement before deployment, not after
- Monitor every layer and component
- Set up alarms for critical metrics
- Make dashboards accessible to all team members

### 5. Thorough Documentation

**Decision**: Write comprehensive documentation for architecture, rules, troubleshooting, and API

**Why It Worked**:
- Onboarding new team members was easy
- Troubleshooting was faster
- Users understood the system
- Reduced support burden

**Lesson**: Documentation pays off:
- Write docs as you build, not after
- Include architecture diagrams
- Document troubleshooting procedures
- Keep API docs up-to-date

## What Could Be Improved ⚠️

### 1. Diagram Validation Gap

**Issue**: 10% of questions reference diagrams but don't have them

**Impact**: These questions were auto-rejected, reducing pass rate

**Root Cause**: Didn't prioritize diagram validation in initial scope

**What We'd Do Differently**:
- Include diagram detection in Phase 1
- Either generate diagrams or filter them out earlier
- Add diagram validation to generation prompts

**Lesson**: Identify and address edge cases early, even if they seem minor

### 2. SymPy Coverage Limitations

**Issue**: SymPy only handled 60% of algebra questions

**Impact**: More questions routed to expensive LLM auditor

**Root Cause**: Underestimated complexity of mathematical parsing

**What We'd Do Differently**:
- Invest more time in SymPy parser development
- Add support for more question types upfront
- Consider alternative math libraries (SageMath, Mathematica)

**Lesson**: For specialized domains, invest in specialized tools

### 3. Initial Population Time

**Issue**: Initial population took 22 hours

**Impact**: Delayed cutover by 1 day

**Root Cause**: Sequential processing, conservative concurrency limits

**What We'd Do Differently**:
- Implement batch verification from start
- Use higher Lambda concurrency
- Parallelize across topics
- Target: 8-10 hours for initial population

**Lesson**: Plan for scale from the beginning, even for one-time operations

### 4. Dedupe False Positives

**Issue**: 2% of unique questions flagged as duplicates

**Impact**: Reduced question variety, user complaints

**Root Cause**: Similarity threshold too strict (0.85)

**What We'd Do Differently**:
- Test threshold with real data before deployment
- Use different thresholds for different question types
- Implement manual review for borderline cases

**Lesson**: Tune ML thresholds with production data, not just test data

### 5. KB Alignment Timeouts

**Issue**: 5% of KB alignment checks timed out

**Impact**: Questions auto-rejected or routed to manual review

**Root Cause**: KB retrieval slow for some topics, timeout too short

**What We'd Do Differently**:
- Load test KB before deployment
- Set realistic timeouts based on testing
- Implement caching for KB results
- Add retry logic from start

**Lesson**: Test external dependencies thoroughly, plan for failures

## Technical Insights 💡

### 1. Lambda Cold Starts Matter

**Observation**: Cold starts added 2-3s to verification latency

**Solution**: Implemented provisioned concurrency for critical functions

**Lesson**: For latency-sensitive functions:
- Use provisioned concurrency
- Keep functions warm with scheduled pings
- Optimize package size
- Consider Lambda SnapStart

### 2. DynamoDB GSI Design Critical

**Observation**: Initial GSI design didn't support all query patterns

**Solution**: Added composite sort key (topic_grade_paper-difficulty)

**Lesson**: Design GSIs carefully:
- Identify all query patterns upfront
- Use composite keys for complex queries
- Test with production-scale data
- GSI changes are expensive after deployment

### 3. SQS Visibility Timeout Tuning

**Observation**: Initial 60s timeout too short for verification

**Solution**: Increased to 300s (5 minutes)

**Lesson**: Set SQS timeouts based on actual processing time:
- Measure p99 processing time
- Add 50% buffer
- Monitor DLQ for timeout issues
- Adjust based on production data

### 4. Bedrock Rate Limits

**Observation**: Hit rate limits during initial population

**Solution**: Implemented exponential backoff and batch processing

**Lesson**: Plan for API rate limits:
- Check quotas before deployment
- Implement retry logic from start
- Use batch APIs where available
- Request quota increases proactively

### 5. Cost Optimization Opportunities

**Observation**: 30% of Bedrock costs were for simple questions

**Solution**: Route simple questions to SymPy, skip LLM auditor

**Lesson**: Optimize AI usage:
- Use cheapest method that works
- Route intelligently based on question type
- Cache results aggressively
- Monitor costs per operation

## Process Insights 🔄

### 1. Spec-Driven Development Worked Well

**Approach**: Created detailed requirements, design, and task documents before coding

**Benefits**:
- Clear scope and expectations
- Easy to track progress
- Reduced rework
- Better team coordination

**Lesson**: Invest time in planning:
- Write specs before coding
- Get stakeholder buy-in early
- Use specs as living documents
- Update as you learn

### 2. Weekly Reviews Essential

**Approach**: Weekly team reviews of metrics, issues, and progress

**Benefits**:
- Caught issues early
- Adjusted priorities based on data
- Kept team aligned
- Built shared understanding

**Lesson**: Regular reviews are critical:
- Schedule weekly at minimum
- Review metrics, not just tasks
- Make data-driven decisions
- Document decisions and rationale

### 3. Staging Environment Invaluable

**Approach**: Full staging environment with smaller scale

**Benefits**:
- Caught issues before production
- Validated deployment process
- Tested at scale
- Built confidence

**Lesson**: Staging is not optional:
- Mirror production as closely as possible
- Test with realistic data
- Validate entire deployment process
- Don't skip staging to save time

### 4. Gradual Feature Rollout

**Approach**: Implemented features in phases, not all at once

**Benefits**:
- Reduced risk
- Easier to debug issues
- Validated each component
- Maintained momentum

**Lesson**: Break large projects into phases:
- Each phase should deliver value
- Validate before moving to next phase
- Don't try to do everything at once
- Celebrate small wins

## Recommendations for Future Projects 📋

### 1. Architecture & Design

**Do**:
- ✅ Design for scale from day 1
- ✅ Use multiple validation layers for quality-critical systems
- ✅ Implement monitoring before deployment
- ✅ Plan for graceful degradation
- ✅ Document architecture decisions

**Don't**:
- ❌ Assume external dependencies are fast/reliable
- ❌ Skip load testing
- ❌ Hardcode thresholds without tuning
- ❌ Ignore edge cases
- ❌ Optimize prematurely

### 2. Implementation

**Do**:
- ✅ Write comprehensive tests
- ✅ Implement retry logic from start
- ✅ Use feature flags for gradual rollout
- ✅ Log everything
- ✅ Handle errors gracefully

**Don't**:
- ❌ Skip error handling
- ❌ Assume happy path only
- ❌ Ignore performance from start
- ❌ Hardcode configuration
- ❌ Skip code reviews

### 3. Deployment

**Do**:
- ✅ Use infrastructure as code (Terraform)
- ✅ Automate deployment process
- ✅ Test in staging first
- ✅ Roll out gradually
- ✅ Have rollback plan ready

**Don't**:
- ❌ Deploy directly to production
- ❌ Skip smoke tests
- ❌ Rush to 100% traffic
- ❌ Deploy on Friday
- ❌ Ignore monitoring during rollout

### 4. Operations

**Do**:
- ✅ Monitor everything
- ✅ Set up alerts
- ✅ Write runbooks
- ✅ Review metrics weekly
- ✅ Iterate based on data

**Don't**:
- ❌ Ignore alarms
- ❌ Skip post-mortems
- ❌ Assume everything is fine
- ❌ Neglect documentation
- ❌ Stop improving after launch

## Metrics That Mattered 📊

### Most Useful Metrics

1. **Verification Pass Rate**: Early indicator of quality
2. **Retrieval Latency (p95)**: User experience metric
3. **Issue Report Rate**: Quality validation
4. **Question Bank Inventory**: Operational health
5. **Cost per Question**: Efficiency metric

### Metrics We Wish We Had

1. **User Engagement**: Time spent per question
2. **Question Difficulty Accuracy**: Actual vs predicted
3. **Verification Layer Effectiveness**: Which layers catch most issues
4. **False Positive/Negative Rates**: Quality calibration
5. **User Satisfaction by Topic**: Identify weak areas

## Key Takeaways 🎯

### For Technical Leaders

1. **Invest in quality upfront**: Verification system paid for itself in reduced support burden
2. **Monitor everything**: Can't improve what you don't measure
3. **Plan for scale**: Easier to scale down than scale up
4. **Document decisions**: Future you will thank present you
5. **Celebrate wins**: Team morale matters

### For Engineers

1. **Test thoroughly**: Unit tests, integration tests, load tests
2. **Handle errors gracefully**: Assume everything will fail
3. **Log everything**: Debugging is easier with good logs
4. **Optimize based on data**: Don't guess, measure
5. **Ask for help**: No one knows everything

### For Product Managers

1. **Define success criteria**: Clear metrics prevent scope creep
2. **Prioritize ruthlessly**: Can't do everything at once
3. **Listen to users**: They'll tell you what matters
4. **Iterate quickly**: Perfect is the enemy of good
5. **Communicate clearly**: Keep stakeholders informed

## Conclusion

The Question Verification System project was a success, but not without challenges. The key lessons are:

1. **Architecture matters**: Pre-generation model was the right choice
2. **Quality takes time**: Multi-layer verification was worth the investment
3. **Monitoring is critical**: Can't operate what you can't see
4. **Gradual rollout works**: Reduced risk and built confidence
5. **Documentation pays off**: Made everything easier

These lessons will inform future projects and help us build better systems faster.

## References

- [Verification Architecture](./verification_architecture.md)
- [Cutover Report](./cutover_report.md)
- [Iteration Plan](./question_bank_iteration_plan.md)
- [Troubleshooting Guide](./troubleshooting_guide.md)

---

**Document Version**: 1.0
**Last Updated**: January 13, 2026
**Contributors**: Entire verification team
