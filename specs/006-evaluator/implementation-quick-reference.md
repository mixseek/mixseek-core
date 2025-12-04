# LLM-as-a-Judge Implementation Quick Reference

**Last Updated**: 2025-10-22

## Quick Decision Summary

| Aspect | Decision |
|--------|----------|
| **Prompting Strategy** | Chain-of-Thought (CoT) with explicit rubrics |
| **Output Format** | Pydantic models with structured output (Tool Output mode) |
| **Scoring Method** | Additive scoring (0-100 scale, broken into sub-criteria) |
| **Temperature** | 0.0 (deterministic) |
| **Seed** | 42 (when supported) |
| **Recommended Model** | Anthropic Claude 3.5 Sonnet |
| **Expected Variance** | < 5% (target: 2-4%) |
| **Retry Logic** | 3 attempts max per metric |

## Core Implementation Pattern

```python
from pydantic_ai import model_request_sync
from pydantic_ai.models import ModelRequestParameters

# 1. Define structured output model
class ClarityCoherenceEvaluation(BaseModel):
    metric_name: str = "clarity_coherence"
    reasoning: str  # CoT reasoning
    sub_scores: dict[str, float]  # Additive scoring
    score: float  # 0-100

# 2. Create prompt with explicit rubric
prompt = f"""
Evaluate CLARITY_COHERENCE (0-100):

USER QUERY: {user_query}
AI RESPONSE: {submission}

CRITERIA:
1. Structure (25 pts)
2. Language (25 pts)
3. Sentences (25 pts)
4. Readability (25 pts)

Write reasoning, then calculate score.
"""

# 3. Call with temperature=0
result = model_request_sync(
    model="anthropic:claude-4-5-sonnet",
    messages=[
        {"role": "system", "content": "Impartial evaluator. Avoid verbosity bias."},
        {"role": "user", "content": prompt}
    ],
    output_type=ClarityCoherenceEvaluation,
    model_request_parameters=ModelRequestParameters(
        temperature=0.0,
        seed=42,
        max_tokens=1000
    )
)
```

## Three Metrics Breakdown

### ClarityCoherence (明瞭性/一貫性)

**Sub-criteria** (25 points each):
- Structure and organization
- Language simplicity
- Sentence construction
- Readability

**Focus**: How easy is it to understand?

### Coverage (網羅性)

**Sub-criteria**:
- Topic coverage: 30 points
- Depth of detail: 30 points
- Completeness: 20 points
- Context: 20 points

**Focus**: Does it cover everything needed?

### Relevance (関連性)

**Sub-criteria**:
- Query alignment: 40 points
- Focus and precision: 30 points
- Requirement addressing: 30 points

**Focus**: Does it answer the actual question?

## Bias Mitigation Checklist

Include in system prompt:
- [ ] "Evaluate based on content quality, not response length"
- [ ] "Do not favor longer or more verbose responses"
- [ ] "Focus on whether the answer addresses criteria, not word count"
- [ ] "Be objective and consistent in your scoring"

## Error Handling Pattern

```python
for attempt in range(max_retries):
    try:
        result = evaluate_metric(...)

        # Validate score matches sub-scores
        if result.score != sum(result.sub_scores.values()):
            raise ModelRetry("Score mismatch")

        return result

    except ValidationError as e:
        if attempt == max_retries - 1:
            raise EvaluationError(f"Failed after {max_retries} attempts")
        # Tell model what's wrong
        raise ModelRetry(f"Fix: {e}")
```

## Testing for < 5% Variance

```python
# Run same evaluation 5 times
scores = [evaluate(query, response).score for _ in range(5)]

# Calculate variance
mean = sum(scores) / len(scores)
variance_percent = (max(abs(s - mean) for s in scores) / mean) * 100

# Verify < 5%
assert variance_percent < 5.0
```

## Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Single evaluation latency | 2-5s | Claude 3.5 Sonnet |
| Three metrics (sequential) | 6-15s | Meets SC-001 (< 30s) |
| Variance | < 5% | SC-002 requirement |
| Success rate | > 95% | With 3 retries |

## Configuration Template (TOML)

```toml
default_model = "anthropic:claude-4-5-sonnet"

[evaluation_settings]
temperature = 0.0
seed = 42
max_retries = 3
max_tokens = 1000

[[metric]]
name = "clarity_coherence"
weight = 0.4

[[metric]]
name = "coverage"
weight = 0.3

[[metric]]
name = "relevance"
weight = 0.3
```

## Common Pitfalls to Avoid

1. **Don't use high temperature** - Breaks consistency
2. **Don't skip CoT reasoning** - Reduces accuracy
3. **Don't use vague rubrics** - Increases variance
4. **Don't ignore bias instructions** - Leads to length bias
5. **Don't use simple 1-5 scale** - Loses granularity
6. **Don't skip validation** - Invalid scores cause errors

## Model Selection Guide

**First choice**: Claude 3.5 Sonnet
- Best reasoning quality
- Supports temperature=0
- Good consistency

**Alternative**: GPT-4 / GPT-4-turbo
- Supports seed parameter
- Good consistency
- Slightly faster

**Budget option**: Gemini 1.5 Pro
- Lower cost
- Good performance
- May have slightly higher variance

## When to Use Multiple Runs

**Default**: Single evaluation (temperature=0)
- Variance: 2-5%
- Cost: 1x
- Latency: 2-5s

**High-stakes**: 3 evaluations + median
- Variance: 1-3%
- Cost: 3x
- Latency: 6-15s

Only use multiple runs if:
- Critical decisions depend on scores
- Budget allows 3x cost
- Variance must be < 3%

## Monitoring What to Track

```python
# Log these metrics
{
    "metric_name": "clarity_coherence",
    "score": 85.0,
    "duration_ms": 3200,
    "model": "claude-3-5-sonnet-20241022",
    "tokens": {"input": 850, "output": 180},
    "retry_count": 0,
    "variance_check": 2.3,  # % variance if running multiple times
}
```

## Integration with Pydantic AI

**Key imports**:
```python
from pydantic_ai import model_request_sync  # FR-005: Use direct API
from pydantic_ai.models import ModelRequestParameters
from pydantic_ai.exceptions import ModelRetry, UnexpectedModelBehavior
from pydantic import BaseModel, Field, field_validator
```

**Documentation reference**:
- `/specs/006-evaluator/assets/docs/pydantic-ai/direct.md`
- `/specs/006-evaluator/assets/docs/pydantic-ai/output.md`

## File Structure

```
src/mixseek/
├── models/
│   └── evaluation.py           # EvaluationRequest, EvaluationResult, MetricScore
├── evaluator/
│   ├── __init__.py
│   ├── core.py                 # Main Evaluator class
│   ├── metrics/
│   │   ├── __init__.py
│   │   ├── clarity_coherence.py          # ClarityCoherence evaluation
│   │   ├── coverage.py
│   │   └── relevance.py
│   ├── prompts.py              # Prompt templates
│   └── config.py               # Load TOML config

configs/
└── evaluator.toml              # Metric weights, models
```

## Next Steps

1. **Implement Pydantic models** in `src/mixseek/models/evaluation.py`
2. **Create prompt templates** in `src/mixseek/evaluator/prompts.py`
3. **Implement metric evaluators** in `src/mixseek/evaluator/metrics/`
4. **Write tests** for consistency validation
5. **Benchmark variance** on test dataset

## References

- Full research findings: `/specs/006-evaluator/llm-judge-research-findings.md`
- Spec: `/specs/006-evaluator/spec.md`
- Pydantic AI docs: `/specs/006-evaluator/assets/docs/pydantic-ai/`
