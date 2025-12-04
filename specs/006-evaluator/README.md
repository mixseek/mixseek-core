# 022-mixseek-core-evaluator Documentation

**Feature**: AIエージェント出力評価器 (AI Agent Output Evaluator)
**Status**: Research Complete, Implementation Pending
**Last Updated**: 2025-10-22

## Overview

This directory contains the complete specification and research for implementing an LLM-as-a-Judge evaluation system with three built-in metrics: clarity_coherence (明瞭性/一貫性), coverage (網羅性), and relevance (関連性).

## Documentation Structure

### Core Specification Documents

1. **[spec.md](spec.md)** (19KB)
   - Complete feature specification
   - User stories and acceptance criteria
   - Functional requirements (FR-001 through FR-018)
   - Success criteria (< 5% variance requirement)
   - Data models and entity definitions

2. **[plan.md](plan.md)** (13KB)
   - Implementation plan
   - Task breakdown and dependencies
   - Technical design decisions
   - Timeline and milestones

### Research and Decision Documents

3. **[llm-judge-research-findings.md](llm-judge-research-findings.md)** (31KB) ⭐
   - **Comprehensive research on LLM-as-a-Judge patterns**
   - Decision: Chain-of-Thought with structured output
   - Rationale: Why this approach achieves < 5% variance
   - Complete prompt templates for all three metrics
   - Output structure (Pydantic models)
   - Consistency techniques (temperature=0, seed, etc.)
   - Error handling patterns
   - Alternatives considered and why they were rejected
   - Performance estimates and cost analysis

4. **[implementation-quick-reference.md](implementation-quick-reference.md)** (7KB) ⭐
   - **Quick lookup guide for developers**
   - Decision summary table
   - Core implementation pattern (copy-paste ready)
   - Three metrics breakdown
   - Bias mitigation checklist
   - Testing patterns
   - Common pitfalls to avoid

5. **[evaluation-flow-diagram.md](evaluation-flow-diagram.md)** (28KB)
   - Visual architecture diagrams
   - Data flow illustrations
   - Error handling flow
   - Prompt template structure
   - Metrics comparison table
   - Configuration flow

### Supporting Documentation

6. **[assets/docs/pydantic-ai/](assets/docs/pydantic-ai/)**
   - Pydantic AI documentation for implementation reference
   - `direct.md`: Direct Model Request API
   - `output.md`: Structured output patterns
   - `message-history.md`: Message handling

7. **[assets/prompts/](assets/prompts/)**
   - Template prompts for development

## Quick Start for Implementation

### 1. Understand the Approach

Read in this order:
1. **spec.md** - Understand what we're building
2. **implementation-quick-reference.md** - See how to build it (15 min read)
3. **llm-judge-research-findings.md** - Deep dive into why (when needed)

### 2. Key Decisions Made

| Aspect | Decision |
|--------|----------|
| Prompting Strategy | Chain-of-Thought (CoT) with explicit rubrics |
| Output Format | Pydantic structured output (Tool Output mode) |
| Scoring Method | Additive (0-100 scale, sub-criteria breakdown) |
| Temperature | 0.0 (deterministic) |
| Model | Claude 3.5 Sonnet (default) |
| Expected Variance | < 5% (target: 2-4%) |
| API | Pydantic AI `model_request_sync` |

### 3. Implementation Pattern

```python
# Core pattern (see implementation-quick-reference.md for full code)
from pydantic_ai import model_request_sync

result = model_request_sync(
    model="anthropic:claude-4-5-sonnet",
    messages=[...],
    output_type=ClarityCoherenceEvaluation,  # Pydantic model
    model_request_parameters={
        "temperature": 0.0,
        "seed": 42
    }
)
```

## Key Requirements

### Functional Requirements (FR)

- **FR-001**: Three built-in metrics (clarity_coherence, coverage, relevance)
- **FR-002**: Scores 0-100 for each metric
- **FR-003**: TOML configuration support
- **FR-005**: Use Pydantic AI Direct Model Request API (`model_request_sync`)
- **FR-010**: Retry logic (max 3 attempts)
- **FR-015**: Per-metric LLM model configuration
- **FR-018**: Immediate error on unavailable LLM provider

### Success Criteria (SC)

- **SC-001**: < 30 seconds for inputs < 2000 characters
- **SC-002**: **< 5% variance for same input** (key requirement)
- **SC-003**: TOML changes take effect without restart
- **SC-005**: Retry mechanism recovers from temporary failures

## Three Metrics Explained

### ClarityCoherence (明瞭性/一貫性)
**Question**: Is it clear and easy to understand?

**Sub-criteria** (25 points each):
- Structure and organization
- Language simplicity
- Sentence construction
- Readability

### Coverage (網羅性)
**Question**: Does it cover everything needed?

**Sub-criteria**:
- Topic coverage: 30 points
- Depth of detail: 30 points
- Completeness: 20 points
- Context: 20 points

### Relevance (関連性)
**Question**: Does it answer the actual question?

**Sub-criteria**:
- Query alignment: 40 points
- Focus and precision: 30 points
- Requirement addressing: 30 points

## Research Methodology

This research involved:

1. **Web search on LLM-as-a-Judge best practices** (2025 sources)
   - G-Eval framework analysis
   - Bias mitigation strategies
   - Consistency techniques

2. **Structured output research**
   - JSON schema enforcement benefits
   - Variance reduction through structured generation
   - Pydantic AI capabilities

3. **Chain-of-Thought evaluation patterns**
   - CoT for transparent reasoning
   - Additive scoring approaches
   - Rubric design

4. **Temperature and seed settings**
   - Reproducibility techniques
   - Expected variance levels
   - Model selection criteria

5. **Bias mitigation**
   - Position bias
   - Verbosity bias
   - Self-enhancement bias

## Implementation Structure

```
src/mixseek/
├── models/
│   └── evaluation.py           # Pydantic models
├── evaluator/
│   ├── __init__.py
│   ├── core.py                 # Main Evaluator class
│   ├── metrics/
│   │   ├── clarity_coherence.py
│   │   ├── coverage.py
│   │   └── relevance.py
│   ├── prompts.py              # Prompt templates
│   └── config.py               # TOML loader

configs/
└── evaluator.toml              # Metric weights, models
```

## Performance Expectations

| Metric | Target | Notes |
|--------|--------|-------|
| Single evaluation | 2-5s | Claude 3.5 Sonnet |
| Three metrics (sequential) | 6-15s | Meets < 30s requirement |
| Variance | < 5% | Research-backed approach |
| Success rate | > 95% | With 3 retries |
| Cost (per evaluation) | ~$0.01 | All three metrics |

## Testing Strategy

### Consistency Validation

```python
# Run same evaluation 5 times
scores = [evaluate(query, response).score for _ in range(5)]

# Verify < 5% variance
mean = sum(scores) / len(scores)
variance_percent = (max(abs(s - mean) for s in scores) / mean) * 100
assert variance_percent < 5.0
```

### Test Coverage

1. **Unit tests**: Individual metric evaluators
2. **Integration tests**: End-to-end evaluation flow
3. **Consistency tests**: Variance validation
4. **Error handling tests**: Retry logic, invalid scores
5. **Config tests**: TOML validation

## Dependencies

- **Pydantic AI** (`pydantic-ai >= 0.1.0`)
- **Anthropic API** (Claude 3.5 Sonnet recommended)
- **OpenAI API** (alternative model)
- **Python 3.13.9**
- **TOML** parsing (`tomli` or `tomllib`)

## Environment Variables Required

```bash
# At least one of these (based on configured models)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
```

## Configuration Example

```toml
# configs/evaluator.toml

default_model = "anthropic:claude-4-5-sonnet"

[evaluation_settings]
temperature = 0.0
seed = 42
max_retries = 3

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

## Next Steps

1. **Phase 1**: Implement Pydantic models (`src/mixseek/models/evaluation.py`)
2. **Phase 2**: Create prompt templates (`src/mixseek/evaluator/prompts.py`)
3. **Phase 3**: Implement metric evaluators (`src/mixseek/evaluator/metrics/`)
4. **Phase 4**: Write consistency tests
5. **Phase 5**: Benchmark variance on test dataset
6. **Phase 6**: Optimize for performance and cost

## References

### External Research
- G-Eval: NLG Evaluation using GPT-4 with Better Human Alignment
- LLM-as-a-Judge: Complete Guide (EvidentlyAI)
- Structured Output Generation in LLMs (Medium)
- Justice or Prejudice? Quantifying Biases in LLM-as-a-Judge (arXiv)

### Internal Documentation
- Parent spec: `/specs/001-specs/spec.md`
- Pydantic AI docs: `assets/docs/pydantic-ai/`
- Project guidelines: `/CLAUDE.md`

## Questions or Issues?

For questions about:
- **What to build**: See `spec.md`
- **How to build it**: See `implementation-quick-reference.md`
- **Why this approach**: See `llm-judge-research-findings.md`
- **Data flow**: See `evaluation-flow-diagram.md`

## Document Status

- ✅ Specification complete (spec.md)
- ✅ Research complete (llm-judge-research-findings.md)
- ✅ Implementation guide complete (implementation-quick-reference.md)
- ✅ Architecture diagrams complete (evaluation-flow-diagram.md)
- ⏳ Implementation in progress
- ⏳ Testing pending
- ⏳ Documentation (Sphinx) pending

---

**Last Research Date**: 2025-10-22
**Researcher**: Claude (Sonnet 4.5)
**Research Sources**: 15+ web sources, Pydantic AI docs, academic papers
