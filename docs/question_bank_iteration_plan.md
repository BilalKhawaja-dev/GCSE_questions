# Question Bank System - Iteration Plan

## Overview

This document outlines the planned improvements and iterations for the Question Verification System based on initial deployment feedback and monitoring data.

## Current Status (Post-Deployment)

### Metrics Summary
- **Question Bank Size**: 30,000+ verified questions
- **Verification Pass Rate**: 65-75%
- **Retrieval Latency**: 45ms (p95)
- **User Satisfaction**: 4.2/5.0
- **Issue Report Rate**: 3.5%

### Known Issues
1. Some topics have lower question counts (< 30)
2. SymPy verification limited to basic algebra
3. Diagram-dependent questions not fully validated
4. Occasional false positives in dedupe layer

## Iteration Roadmap

### Phase 1: Immediate Improvements (Week 1-2)

#### Priority 1: Address Low-Inventory Topics
**Problem**: Some topics have < 30 verified questions
**Solution**:
- Identify low-inventory topics
- Increase generation batch size for these topics
- Adjust verification thresholds if too strict
- Target: All topics with 50+ questions

**Implementation**:
```python
# In replenishment_lambda.py
LOW_INVENTORY_THRESHOLD = 30
HIGH_PRIORITY_BATCH_SIZE = 50  # Generate more for low topics
```

**Success Criteria**: All topics have 50+ questions within 2 weeks

#### Priority 2: Reduce False Positive Rate
**Problem**: 3.5% of verified questions reported as issues
**Solution**:
- Analyze common false positive patterns
- Adjust LLM confidence threshold: 0.75 → 0.78
- Add additional wording checks
- Improve distractor validation

**Implementation**:
- Review rejected questions with high confidence
- Update LLM auditor prompts
- Add new validation rules

**Success Criteria**: Issue report rate < 2%

#### Priority 3: Optimize Retrieval Performance
**Problem**: Some queries take > 100ms
**Solution**:
- Enable API Gateway caching (5 min TTL)
- Optimize DynamoDB queries
- Add Lambda provisioned concurrency
- Implement response compression

**Implementation**:
```terraform
# In api_gateway.tf
resource "aws_api_gateway_method_settings" "retrieval" {
  cache_enabled = true
  cache_ttl_in_seconds = 300
}
```

**Success Criteria**: p95 latency < 50ms

### Phase 2: Feature Enhancements (Week 3-6)

#### Feature 1: Diagram Validation
**Description**: Validate questions that reference diagrams
**Motivation**: 10% of questions mention diagrams but don't have them

**Implementation Plan**:
1. Add diagram detection to deterministic verifier
2. Flag diagram-dependent questions
3. Integrate with diagram generation service (future)
4. For now: Auto-reject diagram-dependent questions

**Estimated Effort**: 2 weeks
**Priority**: High

#### Feature 2: Advanced SymPy Support
**Description**: Extend SymPy verification to more question types
**Motivation**: Currently only handles 60% of algebra questions

**New Question Types**:
- Inequalities: `2x + 5 > 13`
- Systems of inequalities
- Quadratic inequalities
- Absolute value equations
- Piecewise functions

**Estimated Effort**: 3 weeks
**Priority**: Medium

#### Feature 3: Proof-Style Question Validation
**Description**: Validate proof and reasoning questions
**Motivation**: 5% of questions are proof-style, currently skipped

**Implementation Plan**:
1. Identify proof-style questions
2. Use LLM for step-by-step validation
3. Check logical flow and completeness
4. Validate conclusion

**Estimated Effort**: 4 weeks
**Priority**: Low

#### Feature 4: User Feedback Loop
**Description**: Use user feedback to improve verification
**Motivation**: Learn from false positives/negatives

**Implementation Plan**:
1. Collect user feedback on questions
2. Analyze patterns in reported issues
3. Automatically adjust thresholds
4. Retrain verification models

**Estimated Effort**: 3 weeks
**Priority**: High

### Phase 3: Optimization (Week 7-10)

#### Optimization 1: Batch Verification
**Description**: Verify multiple questions in parallel
**Motivation**: Reduce verification latency

**Implementation Plan**:
1. Modify verification Lambda to accept batches
2. Parallelize independent verification layers
3. Aggregate results efficiently
4. Target: 5s for batch of 10 questions

**Estimated Effort**: 2 weeks
**Priority**: Medium

#### Optimization 2: Intelligent Caching
**Description**: Cache verification results for similar questions
**Motivation**: Reduce redundant AI calls

**Implementation Plan**:
1. Generate embeddings for questions
2. Check cache for similar questions
3. Reuse verification results if similarity > 0.95
4. Update cache with new results

**Estimated Effort**: 2 weeks
**Priority**: Low

#### Optimization 3: Cost Reduction
**Description**: Reduce Bedrock API costs
**Motivation**: Current cost: $200/month, target: $100/month

**Strategies**:
1. Use cheaper models for simple checks
2. Implement result caching
3. Batch API calls where possible
4. Use SymPy more aggressively

**Estimated Effort**: 1 week
**Priority**: Medium

### Phase 4: Advanced Features (Week 11+)

#### Feature 5: Multi-Region Deployment
**Description**: Deploy to multiple AWS regions
**Motivation**: Reduce latency for global users

**Implementation Plan**:
1. Deploy to us-east-1, eu-west-1, ap-southeast-1
2. Use Route53 for geo-routing
3. Replicate question bank across regions
4. Sync verification results

**Estimated Effort**: 4 weeks
**Priority**: Low

#### Feature 6: A/B Testing Framework
**Description**: Test verification rule changes safely
**Motivation**: Validate improvements before full rollout

**Implementation Plan**:
1. Implement feature flags
2. Route percentage of traffic to new rules
3. Compare metrics between variants
4. Gradual rollout of improvements

**Estimated Effort**: 3 weeks
**Priority**: Medium

#### Feature 7: ML-Based Confidence Calibration
**Description**: Train ML model to predict question quality
**Motivation**: Improve confidence scoring accuracy

**Implementation Plan**:
1. Collect training data (verified questions + user feedback)
2. Train classification model
3. Use model to calibrate confidence scores
4. Continuous learning from new data

**Estimated Effort**: 6 weeks
**Priority**: Low

## Monitoring & Success Metrics

### Key Performance Indicators (KPIs)

**Question Bank Health**:
- Inventory per topic: Target 50+
- Verification pass rate: Target 65-75%
- Generation rate: Target 1000+ questions/week

**User Experience**:
- Retrieval latency: Target < 50ms (p95)
- Issue report rate: Target < 2%
- User satisfaction: Target 4.5/5.0

**System Performance**:
- Verification latency: Target < 8s per question
- Error rate: Target < 1%
- Cost per question: Target < $0.01

### Weekly Review Process

**Every Monday**:
1. Review CloudWatch dashboards
2. Analyze user feedback
3. Check inventory levels
4. Review verification pass rates
5. Identify issues and prioritize

**Every Month**:
1. Comprehensive metrics analysis
2. Review iteration progress
3. Adjust priorities based on data
4. Plan next month's work

## Risk Management

### Risk 1: Verification Too Strict
**Impact**: Low pass rate, insufficient questions
**Mitigation**: Monitor pass rates, adjust thresholds weekly
**Contingency**: Temporarily lower thresholds, increase generation

### Risk 2: Verification Too Lenient
**Impact**: High issue report rate, poor user experience
**Mitigation**: Monitor user feedback, tighten thresholds
**Contingency**: Remove problematic questions, improve rules

### Risk 3: Cost Overrun
**Impact**: Budget exceeded
**Mitigation**: Monitor costs daily, optimize API usage
**Contingency**: Reduce generation frequency, use cheaper models

### Risk 4: Performance Degradation
**Impact**: High latency, poor user experience
**Mitigation**: Monitor latency metrics, optimize queries
**Contingency**: Scale up resources, enable caching

## Resource Allocation

### Team Composition
- 1 Backend Engineer (verification system)
- 1 Frontend Engineer (user experience)
- 1 DevOps Engineer (infrastructure)
- 1 Data Scientist (ML improvements)

### Time Allocation
- 40% New features
- 30% Bug fixes and improvements
- 20% Monitoring and maintenance
- 10% Documentation and testing

## Communication Plan

### Stakeholder Updates
- **Weekly**: Email summary to team
- **Bi-weekly**: Demo to stakeholders
- **Monthly**: Comprehensive report to leadership

### User Communication
- **Release notes**: For each deployment
- **Blog posts**: For major features
- **Email**: For breaking changes

## Success Criteria

### Phase 1 Success (Week 2)
- [ ] All topics have 50+ questions
- [ ] Issue report rate < 2%
- [ ] p95 latency < 50ms

### Phase 2 Success (Week 6)
- [ ] Diagram validation implemented
- [ ] SymPy supports 80%+ of algebra questions
- [ ] User feedback loop operational

### Phase 3 Success (Week 10)
- [ ] Batch verification reduces latency by 50%
- [ ] Cost reduced to < $150/month
- [ ] Caching improves performance by 30%

### Phase 4 Success (Week 16)
- [ ] Multi-region deployment complete
- [ ] A/B testing framework operational
- [ ] ML-based confidence calibration deployed

## Conclusion

This iteration plan provides a roadmap for continuous improvement of the Question Verification System. Priorities will be adjusted based on monitoring data and user feedback. The focus is on maintaining high question quality while improving performance and reducing costs.

## References

- [Verification Architecture](./verification_architecture.md)
- [Verification Rules](./verification_rules.md)
- [Troubleshooting Guide](./troubleshooting_guide.md)
- [Lessons Learned](./lessons_learned.md)
