# AI Training Guide for GCSE Question Generator

This guide explains how to train your AI model with custom content like Edexcel exam specifications and sample questions to improve question quality and ensure the AI generates new, relevant questions rather than repeating preconfigured ones.

## Overview

The AI system uses two types of content to generate questions:

1. **Specification Content**: Official exam board specifications (like Edexcel) that define what should be taught and assessed
2. **Seed Examples**: High-quality example questions with mark schemes that serve as templates for the AI

## Quick Start

### 1. Create Example Template
```bash
python scripts/upload_training_content.py --create-template
```

This creates `example_template.json` with the correct format for your examples.

### 2. Add Your Examples
Edit the template file with your own high-quality questions:

```json
{
  "examples": [
    {
      "question": {
        "question_text": "Calculate 3/4 + 1/8. Give your answer as a fraction in its simplest form.",
        "marks": 3,
        "tier": "Foundation",
        "topic": "Number", 
        "subtopic": "fractions",
        "difficulty_score": 3
      },
      "mark_scheme": {
        "marking_criteria": "M1: Convert to common denominator, M1: Add fractions, A1: Correct final answer",
        "method_marks": 2,
        "accuracy_marks": 1,
        "answer": "3/4 + 1/8 = 6/8 + 1/8 = 7/8"
      }
    }
  ]
}
```

### 3. Upload Examples
```bash
python scripts/upload_training_content.py --json example_template.json --type examples
```

### 4. Upload Specifications (if you have PDFs)
```bash
python scripts/upload_training_content.py --pdf edexcel_spec.pdf --type specification
```

### 5. Validate Content
```bash
python scripts/upload_training_content.py --validate-content
```

## How the AI Uses Your Content

### Specification Content
- **Learning Objectives**: The AI ensures questions test specific learning goals
- **Key Concepts**: Questions incorporate the exact mathematical concepts from your specs
- **Common Misconceptions**: The AI designs questions to reveal typical student errors
- **Assessment Objectives**: Questions align with AO1 (knowledge) and AO2 (application) requirements

### Seed Examples
- **Question Style**: The AI mimics the language, structure, and format of your examples
- **Difficulty Calibration**: Uses your difficulty scores to generate appropriately challenging questions
- **Mark Scheme Patterns**: Follows your marking criteria structure (M1, A1, etc.)
- **Mathematical Contexts**: Adapts the real-world contexts from your examples

## Content Quality Guidelines

### High-Quality Examples Should Have:

1. **Clear Question Text** (50+ characters)
   - Unambiguous mathematical language
   - Appropriate context for the tier level
   - Clear instructions (e.g., "Give your answer as a fraction")

2. **Appropriate Marks** (2-6 marks typical)
   - Reflects the complexity of the solution
   - Allows for method and accuracy marks

3. **Accurate Difficulty Scores**
   - Foundation tier: 1-5 (1=very easy, 5=challenging)
   - Higher tier: 6-10 (6=easy higher, 10=very challenging)

4. **Detailed Mark Schemes**
   - Clear method marks (M1, M2, etc.)
   - Accuracy marks (A1, A2, etc.)
   - Step-by-step solution in the answer field

### Example Quality Scoring

The system automatically scores examples based on:
- Question length and clarity
- Mark scheme detail
- Mathematical content richness
- Tier appropriateness

Only examples scoring above 0.7 (70%) are used for training.

## Advanced Training Techniques

### 1. Topic-Specific Training
Organize examples by mathematical domains:
- **Number**: Fractions, decimals, percentages, ratio
- **Algebra**: Linear equations, quadratics, simultaneous equations
- **Geometry**: Angles, area, trigonometry, Pythagoras
- **Statistics**: Data analysis, probability, graphs

### 2. Difficulty Progression
Include examples across difficulty levels:
```json
{
  "question": {
    "difficulty_score": 2,
    "question_text": "Calculate 1/2 + 1/4"
  }
},
{
  "question": {
    "difficulty_score": 4,
    "question_text": "Solve 2x + 3 = 4x - 7"
  }
}
```

### 3. Misconception Targeting
Include examples that address common errors:
```json
{
  "mark_scheme": {
    "common_errors": [
      "Adding denominators instead of finding common denominator",
      "Forgetting to simplify the final answer"
    ]
  }
}
```

## Monitoring AI Performance

### Content Validation
Regular validation ensures your content is being used effectively:

```bash
# Check current content status
python scripts/upload_training_content.py --validate-content

# Expected output:
# ✅ Specifications: 12 files
#    Domains: number, algebra, geometry, statistics
# ✅ Examples: 8 files
# Status: healthy
```

### Quality Metrics
The AI tracks how well it uses your content:
- **Specification Alignment**: How well questions match learning objectives
- **Example Similarity**: How closely generated questions follow your templates
- **Misconception Coverage**: Whether questions address common errors

## Troubleshooting

### "AI is repeating similar questions"
**Solution**: Add more diverse examples across different subtopics and difficulty levels.

```bash
# Check current example coverage
python scripts/upload_training_content.py --validate-content
```

### "Questions don't match my specification"
**Solution**: Upload your specific exam board specifications.

```bash
# Upload Edexcel specification PDF
python scripts/upload_training_content.py --pdf edexcel_gcse_math_spec.pdf --type specification
```

### "Difficulty levels seem wrong"
**Solution**: Review and adjust difficulty scores in your examples.

Foundation tier should use scores 1-5:
- 1-2: Basic recall and simple procedures
- 3-4: Multi-step problems with some reasoning
- 5: Complex problems requiring multiple concepts

Higher tier should use scores 6-10:
- 6-7: Standard higher tier problems
- 8-9: Challenging problems requiring insight
- 10: Very demanding problems with multiple steps

## Best Practices

### 1. Start Small
Begin with 10-15 high-quality examples per topic before expanding.

### 2. Regular Updates
Update your content as exam specifications change:
```bash
# Upload new version
python scripts/upload_training_content.py --pdf new_spec.pdf --type specification --version 2024.2
```

### 3. Quality Over Quantity
Better to have 5 excellent examples than 20 mediocre ones.

### 4. Test and Iterate
Generate questions after each content update to see improvements:
1. Upload new content
2. Generate sample questions
3. Evaluate quality
4. Refine content based on results

## Content Organization

The system organizes your content hierarchically:

```
specifications/
├── number/
│   ├── fractions.json
│   ├── decimals.json
│   └── percentages.json
├── algebra/
│   ├── linear-equations.json
│   └── quadratics.json
└── geometry/
    ├── angles.json
    └── trigonometry.json

examples/
├── number/
│   └── fractions.json
├── algebra/
│   └── linear-equations.json
└── geometry/
    └── angles.json
```

This organization allows the AI to:
- Find relevant content quickly
- Combine concepts appropriately
- Maintain topic coherence

## Support and Maintenance

### Regular Maintenance Tasks

1. **Monthly Content Review**
   ```bash
   python scripts/upload_training_content.py --validate-content
   ```

2. **Quality Assessment**
   - Generate test questions
   - Review for specification alignment
   - Check difficulty appropriateness

3. **Content Updates**
   - Add new examples based on student needs
   - Update specifications for new exam requirements
   - Remove outdated or low-quality content

### Getting Help

If you encounter issues:
1. Check the validation output for missing content
2. Review example quality scores
3. Ensure specification content is comprehensive
4. Contact support with specific error messages

## Conclusion

Training your AI with high-quality, specification-aligned content is key to generating relevant, varied questions that truly test student understanding. The system is designed to learn from your expertise and replicate the quality and style of your best examples while ensuring full coverage of the curriculum requirements.

Regular content updates and validation will keep your AI performing at its best, generating fresh questions that align with your teaching goals and assessment requirements.