# Question Retrieval API Documentation

## Overview

The Question Retrieval API provides fast access to pre-verified GCSE Maths questions from the question bank. This endpoint replaces real-time generation with instant retrieval from a curated database of verified questions.

## Base URL

```
Production: https://api.gcse-question-generator.com
Staging: https://staging-api.gcse-question-generator.com
```

## Authentication

All requests require authentication via JWT token in the Authorization header:

```
Authorization: Bearer <jwt_token>
```

## Endpoint: Retrieve Questions

### `POST /retrieve-questions`

Retrieves verified questions from the question bank based on specified criteria.

### Request Format

```json
{
  "topic": "algebra",
  "grade": "foundation",
  "paper_type": "P1",
  "difficulty_min": 4,
  "difficulty_max": 6,
  "exclude_question_ids": ["uuid1", "uuid2"],
  "count": 5
}
```

### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `topic` | string | Yes | Topic name (e.g., "algebra", "geometry", "statistics") |
| `grade` | string | Yes | Grade level: "foundation" or "higher" |
| `paper_type` | string | Yes | Paper type: "P1" (non-calculator), "P2", or "P3" (calculator) |
| `difficulty_min` | integer | No | Minimum difficulty (1-10). Default: 1 |
| `difficulty_max` | integer | No | Maximum difficulty (1-10). Default: 10 |
| `exclude_question_ids` | array | No | List of question IDs to exclude (avoid repetition) |
| `count` | integer | No | Number of questions to return (1-20). Default: 5 |

### Response Format

#### Success Response (200 OK)

```json
{
  "questions": [
    {
      "question_id": "550e8400-e29b-41d4-a716-446655440000",
      "stem": "Solve the equation: 2x + 5 = 13",
      "options": [
        "x = 4",
        "x = 9",
        "x = 3",
        "x = 8"
      ],
      "correct_answer": "A",
      "rationale": "Subtract 5 from both sides: 2x = 8. Divide by 2: x = 4",
      "topic": "algebra",
      "grade": "foundation",
      "paper_type": "P1",
      "difficulty": 5,
      "tags": ["linear_equations", "solving"],
      "verification_confidence": 0.87,
      "created_at": "2026-01-05T10:00:00Z"
    }
  ],
  "metadata": {
    "total_available": 48,
    "response_time_ms": 45,
    "bank_status": "healthy"
  }
}
```

#### Error Responses

**400 Bad Request** - Invalid parameters
```json
{
  "error": "InvalidParameter",
  "message": "topic is required",
  "details": {
    "parameter": "topic",
    "provided": null,
    "expected": "string"
  }
}
```

**404 Not Found** - No questions available
```json
{
  "error": "NoQuestionsAvailable",
  "message": "No verified questions found matching criteria",
  "details": {
    "topic": "algebra",
    "grade": "foundation",
    "paper_type": "P1",
    "available_count": 0
  },
  "fallback": {
    "use_generation": true,
    "generation_endpoint": "/generate"
  }
}
```

**429 Too Many Requests** - Rate limit exceeded
```json
{
  "error": "RateLimitExceeded",
  "message": "Too many requests. Please try again later.",
  "retry_after": 60
}
```

**500 Internal Server Error** - Server error
```json
{
  "error": "InternalServerError",
  "message": "An unexpected error occurred",
  "request_id": "req-123456"
}
```

## Rate Limits

- **Authenticated users**: 100 requests per minute
- **Premium users**: 500 requests per minute
- **Burst limit**: 20 requests per second

Rate limit headers are included in all responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1641024000
```

## Performance Targets

- **Response time**: < 100ms (p95)
- **Availability**: 99.9%
- **Cache hit rate**: > 80%

## Question Quality Guarantees

All questions returned by this endpoint have been verified through multiple layers:

1. **Deterministic Validation**: Schema, structure, and format checks
2. **Mathematical Verification**: SymPy-based correctness validation
3. **LLM Auditor**: Semantic validation and ambiguity detection
4. **KB Alignment**: Syllabus compliance and source alignment
5. **Deduplication**: Similarity detection to prevent repetition

**Verification Confidence**: Each question includes a `verification_confidence` score (0.0-1.0) indicating the overall confidence in the question's quality. All questions have confidence >= 0.75.

## Fallback Behavior

If the question bank is empty or depleted for a specific topic:

1. The API returns a 404 with `fallback.use_generation = true`
2. Frontend should fall back to the `/generate` endpoint
3. Generated questions will be queued for verification and added to the bank

## Usage Examples

### Example 1: Basic Retrieval

```bash
curl -X POST https://api.gcse-question-generator.com/retrieve-questions \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "algebra",
    "grade": "foundation",
    "paper_type": "P1",
    "count": 5
  }'
```

### Example 2: Filtered by Difficulty

```bash
curl -X POST https://api.gcse-question-generator.com/retrieve-questions \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "geometry",
    "grade": "higher",
    "paper_type": "P2",
    "difficulty_min": 7,
    "difficulty_max": 9,
    "count": 3
  }'
```

### Example 3: Avoid Repetition

```bash
curl -X POST https://api.gcse-question-generator.com/retrieve-questions \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "statistics",
    "grade": "foundation",
    "paper_type": "P1",
    "exclude_question_ids": [
      "550e8400-e29b-41d4-a716-446655440000",
      "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
    ],
    "count": 5
  }'
```

## Frontend Integration

### React Hook Example

```typescript
import { useQuestionRetrieval } from '../hooks/useQuestionRetrieval';

function QuestionPage() {
  const { questions, loading, error, retrieveQuestions } = useQuestionRetrieval();

  const handleRetrieve = async () => {
    await retrieveQuestions({
      topic: 'algebra',
      grade: 'foundation',
      paper_type: 'P1',
      count: 5
    });
  };

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div>
      {questions.map(q => (
        <QuestionDisplay key={q.question_id} question={q} />
      ))}
    </div>
  );
}
```

## Monitoring & Metrics

The following metrics are tracked for this endpoint:

- **Latency**: p50, p95, p99 response times
- **Availability**: Uptime percentage
- **Error rate**: 4xx and 5xx error percentages
- **Cache hit rate**: Percentage of requests served from cache
- **Bank depletion**: Topics with low question counts

## Support

For API issues or questions:
- Email: api-support@gcse-question-generator.com
- Slack: #api-support
- Documentation: https://docs.gcse-question-generator.com

## Changelog

### v1.0.0 (2026-01-13)
- Initial release of retrieval API
- Replaced real-time generation with pre-verified question bank
- Added verification confidence scores
- Implemented fallback to generation endpoint
