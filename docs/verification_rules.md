# Verification Rules Documentation

## Overview

This document details the verification rules applied to each question before it enters the verified question bank. Questions must pass all applicable layers to be accepted.

## Verification Layers

### Layer 1: Deterministic Verifier

**Purpose**: Fast, rule-based checks to catch obvious issues before expensive AI processing.

**Performance Target**: < 100ms per question

#### Rule 1.1: JSON Schema Validation

**Criteria**:
- Question must be valid JSON
- All required fields present: `stem`, `options`, `correct_answer`, `rationale`, `topic`, `grade`, `paper_type`, `difficulty`
- Field types must match schema

**Pass Condition**: All fields present and valid

**Failure Examples**:
- Missing `stem` field
- `options` is not an array
- `difficulty` is not a number

#### Rule 1.2: MCQ Structure Validation

**Criteria**:
- Exactly 4 options (A, B, C, D)
- Exactly 1 option marked as correct
- No duplicate options (string equality)
- All options are non-empty strings

**Pass Condition**: All structure rules satisfied

**Failure Examples**:
- Only 3 options provided
- Two options marked as correct
- Options A and C have identical text

#### Rule 1.3: Answer Format Validation

**Criteria**:
- `correct_answer` must be one of: "A", "B", "C", "D"
- Answer must reference a valid option
- Rationale must be non-empty

**Pass Condition**: Answer format valid

**Failure Examples**:
- `correct_answer` is "E"
- `correct_answer` is "1" instead of "A"
- Empty rationale

#### Rule 1.4: Paper Constraint Validation

**Criteria for Paper 1 (Non-Calculator)**:
- Stem must not mention "calculator"
- Avoid phrases like "give answer to 3 s.f." with decimals
- Arithmetic must be reasonable by hand
- Prefer exact forms (surds, fractions, π)

**Criteria for Paper 2 & 3 (Calculator)**:
- Can include complex calculations
- Decimal answers acceptable
- Can reference calculator-dependent methods

**Pass Condition**: Paper constraints satisfied

**Failure Examples** (P1):
- "Use your calculator to find..."
- "Give your answer to 3 significant figures" with ugly decimal
- "Calculate 347 × 892"

### Layer 2: SymPy Verifier

**Purpose**: Programmatic mathematical correctness validation.

**Performance Target**: < 500ms per question

**Applicability**: Only for algebra/arithmetic questions that can be parsed by SymPy.

#### Rule 2.1: Correct Answer Validation

**Criteria**:
- Parse question and solve independently
- Compare solution to provided answer
- Use symbolic equality for exact forms
- Use numeric tolerance for decimals

**Pass Condition**:
- Symbolic: `simplify(solution - key) == 0`
- Numeric: `abs(solution - key) <= 1e-10`

**Tolerance Values**:
- Exact forms: 0 (must be symbolically equal)
- Decimals: 1e-10
- Percentages: 0.01
- Angles: 0.1 degrees

**Failure Examples**:
- Key says "x = 4" but solution is "x = 5"
- Key says "√50" but solution is "5√2" (these should pass - symbolic equality)
- Key says "3.14" but solution is "π" (numeric tolerance check)

#### Rule 2.2: Distractor Validation

**Criteria**:
- Parse all wrong options
- Verify they don't equal the correct answer
- Check for multiple-correct scenarios

**Pass Condition**: All wrong options are actually wrong

**Failure Examples**:
- Option A: "x = 4" (correct)
- Option B: "4" (also correct - missing variable)
- Option C: "2 + 2" (also correct - simplifies to 4)

#### Rule 2.3: Domain Restriction Validation

**Criteria**:
- Check for division by zero
- Check for negative square roots
- Check for log of negative numbers
- Verify domain restrictions stated in question

**Pass Condition**: No domain violations

**Failure Examples**:
- "Solve: 1/(x-2) = 0" (no solution, division by zero)
- "Find √(-4)" without mentioning complex numbers
- "Calculate log(-5)"

### Layer 3: LLM Auditor

**Purpose**: Semantic validation for questions SymPy can't handle.

**Performance Target**: < 5s per question

**Model**: Claude 3.5 Sonnet v2 (anthropic.claude-3-5-sonnet-20241022-v2:0)

#### Rule 3.1: Independent Solve Agreement

**Criteria**:
- LLM solves question without seeing answer key
- Compare LLM's answer to provided key
- Check for agreement

**Pass Condition**: 
- `agreement = true`
- LLM's answer matches key

**Failure Examples**:
- LLM solves to "B" but key says "A"
- LLM cannot solve question (unclear stem)

#### Rule 3.2: Ambiguity Detection

**Criteria**:
- Check for multiple-correct scenarios
- Check for unclear stem
- Check for missing information
- Check for interpretation variance

**Pass Condition**: `ambiguity = "none"`

**Ambiguity Types**:
- `multiple-correct`: Two or more options could be valid
- `unclear-stem`: Question wording is ambiguous
- `missing-info`: Insufficient information to solve
- `diagram-dependent`: Requires diagram not provided

**Failure Examples**:
- "Find the angle" (which angle? multiple angles in diagram)
- "Calculate the area" (missing dimensions)
- "Solve for x" (multiple valid solutions, not specified)

#### Rule 3.3: Wording Validation

**Criteria**:
- Check for missing units
- Check for insufficient information
- Check for diagram-dependent questions without diagrams
- Check for unclear phrasing

**Pass Condition**: `issues = []` or minor issues only

**Issue Severity**:
- **Critical**: Auto-reject (missing info, ambiguous)
- **Major**: Review required (unclear wording)
- **Minor**: Accept with note (style issues)

**Failure Examples**:
- "The speed is 50" (missing units: m/s? km/h?)
- "Calculate the perimeter" (no dimensions given)
- "As shown in the diagram" (no diagram provided)

#### Rule 3.4: Confidence Threshold

**Criteria**:
- LLM provides confidence score (0.0-1.0)
- Confidence must meet threshold

**Pass Condition**: `confidence >= 0.75`

**Confidence Interpretation**:
- 0.90-1.00: Very confident (clear question, obvious answer)
- 0.75-0.89: Confident (good question, minor ambiguity)
- 0.50-0.74: Uncertain (reject - needs review)
- 0.00-0.49: Very uncertain (reject - major issues)

**Tuning Guidelines**:
- If pass rate too low (< 50%): Lower threshold to 0.70
- If user reports high (> 10%): Raise threshold to 0.80
- Monitor false positive/negative rates weekly

### Layer 4: KB Alignment

**Purpose**: Retrieval-grounded verification using Bedrock Knowledge Base.

**Performance Target**: < 3s per question

#### Rule 4.1: Source Alignment Check

**Criteria**:
- Retrieve relevant educational material from KB (5 docs)
- Verify correct answer aligns with retrieved content
- Check for hallucinated facts

**Pass Condition**: 
- `source_support = true`
- `confidence >= 0.7`

**Retrieval Strategy**:
- Query: "{topic}: {stem}"
- Max results: 5
- Filter: Educational content only

**Failure Examples**:
- Question: "The capital of France is Paris" (correct)
- KB material: "Paris is a city in France" (supports answer)
- **PASS**

- Question: "The capital of France is London" (incorrect)
- KB material: "Paris is the capital of France" (contradicts answer)
- **FAIL**

**Graceful Degradation**:
- If KB returns no results: Don't auto-reject
- If KB confidence low: Advisory signal only
- Log KB gaps for improvement

#### Rule 4.2: Syllabus Compliance Check

**Criteria**:
- Retrieve Edexcel 1MA1 specification for topic
- Verify question is within syllabus scope
- Check difficulty appropriate for grade
- Validate paper type constraints

**Pass Condition**:
- `in_scope = true`
- `confidence >= 0.7`

**Retrieval Strategy**:
- Query: "Edexcel 1MA1 specification {topic} {grade}"
- Max results: 3
- Filter: Specification documents only

**Failure Examples**:
- Topic: "Calculus" for Foundation tier (out of scope)
- Topic: "Complex numbers" for GCSE (A-level content)
- P1 question requiring calculator (paper constraint violation)

**Syllabus Boundaries**:
- Foundation: Topics 1-15 (basic algebra, geometry, statistics)
- Higher: Topics 1-25 (includes advanced algebra, trig, probability)
- P1: Non-calculator topics only
- P2/P3: All topics allowed

### Layer 5: Deduplication

**Purpose**: Prevent repetitive questions in the bank.

**Performance Target**: < 1s per question

#### Rule 5.1: Embedding Similarity Check

**Criteria**:
- Generate embedding for new question (Titan Embed v2)
- Calculate cosine similarity with existing questions
- Check against threshold

**Pass Condition**: `max_similarity <= 0.85`

**Embedding Generation**:
- Input: "{stem} {option_A} {option_B} {option_C} {option_D}"
- Model: amazon.titan-embed-text-v2:0
- Dimensions: 1024

**Similarity Calculation**:
```python
similarity = dot(embedding_a, embedding_b) / (norm(embedding_a) * norm(embedding_b))
```

**Threshold Tuning**:
- 0.95+: Nearly identical (definitely reject)
- 0.85-0.94: Very similar (reject by default)
- 0.70-0.84: Similar (accept but flag)
- < 0.70: Different (accept)

**Failure Examples**:
- Question A: "Solve 2x + 5 = 13"
- Question B: "Solve 2x + 5 = 13" (identical - similarity 1.0)
- **FAIL**

- Question A: "Solve 2x + 5 = 13"
- Question B: "Solve 2x + 3 = 11" (very similar - similarity 0.92)
- **FAIL**

- Question A: "Solve 2x + 5 = 13"
- Question B: "Factorise x² + 7x + 12" (different - similarity 0.35)
- **PASS**

**Scope**:
- Only compare within same topic/grade
- Don't compare across different topics
- Store embeddings in DynamoDB for efficiency

## Overall Pass Criteria

A question must pass ALL applicable layers to be accepted:

1. **Deterministic**: MUST pass (critical)
2. **SymPy**: MUST pass if applicable (not all questions are SymPy-solvable)
3. **LLM Auditor**: MUST pass (critical)
4. **KB Alignment**: SHOULD pass (advisory if KB incomplete)
5. **Dedupe**: MUST pass (critical)

**Overall Confidence Score**:
```python
overall_confidence = min(
    sympy_confidence if applicable else 1.0,
    llm_confidence,
    kb_confidence if available else 1.0
)
```

**Final Verdict**:
- `overall_confidence >= 0.75` → PASS
- `overall_confidence < 0.75` → FAIL

## Verification Metrics

### Target Pass Rates

- **Deterministic**: 90-95% (most questions should pass basic checks)
- **SymPy**: 60-70% (only applicable to algebra/arithmetic)
- **LLM Auditor**: 70-80% (semantic validation)
- **KB Alignment**: 80-90% (depends on KB completeness)
- **Dedupe**: 95-98% (most questions should be unique)

**Overall Pass Rate**: 60-80% (target range)

### Performance Targets

- **Deterministic**: < 100ms
- **SymPy**: < 500ms
- **LLM Auditor**: < 5s
- **KB Alignment**: < 3s
- **Dedupe**: < 1s
- **Total**: < 10s per question

## Threshold Tuning Guidelines

### When to Adjust Thresholds

**Pass Rate Too Low (< 50%)**:
- Lower LLM confidence threshold: 0.75 → 0.70
- Increase SymPy tolerance: 1e-10 → 1e-8
- Relax dedupe threshold: 0.85 → 0.90

**Pass Rate Too High (> 90%)**:
- Raise LLM confidence threshold: 0.75 → 0.80
- Decrease SymPy tolerance: 1e-10 → 1e-12
- Tighten dedupe threshold: 0.85 → 0.80

**User Reports High (> 10%)**:
- Investigate common failure patterns
- Adjust specific layer thresholds
- Add new validation rules

### Monitoring & Iteration

**Weekly Review**:
- Check pass rates by layer
- Analyze rejected questions
- Review user feedback
- Adjust thresholds as needed

**Monthly Review**:
- Comprehensive analysis of verification quality
- Update rules based on patterns
- Document threshold changes
- Retrain/update models if needed

## Common Failure Patterns

### Pattern 1: Ambiguous Wording
**Frequency**: 15-20% of failures
**Example**: "Find the angle" (which angle?)
**Fix**: Add clarification to stem

### Pattern 2: Missing Units
**Frequency**: 10-15% of failures
**Example**: "The speed is 50" (m/s? km/h?)
**Fix**: Add units to answer options

### Pattern 3: Calculator Dependency (P1)
**Frequency**: 5-10% of failures
**Example**: "Calculate 347 × 892" on P1
**Fix**: Simplify arithmetic or move to P2/P3

### Pattern 4: Out of Syllabus
**Frequency**: 5-10% of failures
**Example**: Calculus on Foundation tier
**Fix**: Adjust generation prompts

### Pattern 5: Near-Duplicates
**Frequency**: 2-5% of failures
**Example**: "Solve 2x + 5 = 13" vs "Solve 2x + 3 = 11"
**Fix**: Increase variety in generation

## Error Handling

### Transient Failures
- Retry up to 3 times with exponential backoff
- Log failure for analysis
- Continue with other layers

### Permanent Failures
- Mark question as "VERIFICATION_ERROR"
- Store in rejected_questions table
- Alert for manual review

### Graceful Degradation
- If SymPy fails: Continue with LLM auditor
- If KB unavailable: Skip KB alignment (advisory only)
- If dedupe fails: Log error but don't auto-reject

## References

- [Verification Architecture](./verification_architecture.md)
- [Troubleshooting Guide](./troubleshooting_guide.md)
- [Verification Runbook](./verification_runbook.md)
