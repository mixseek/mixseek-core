# Quick Start Guide: AI Agent Output Evaluator

**Branch**: `022-mixseek-core-evaluator`
**Date**: 2025-10-22
**Phase**: Phase 1 - Design

## Overview

This quick start guide provides step-by-step instructions for integrating the AI Agent Output Evaluator into your MixSeek-Core application. The Evaluator component assesses AI agent responses using LLM-as-a-Judge with three built-in metrics (clarity_coherence, coverage, relevance) and returns structured evaluation results.

---

## Prerequisites

1. **Python Version**: Python 3.13.9 or compatible
2. **Package Manager**: uv (installed and configured)
3. **API Keys**: Environment variables for LLM providers:
   - `ANTHROPIC_API_KEY` for Anthropic models
   - `OPENAI_API_KEY` for OpenAI models
4. **Workspace**: MixSeek-Core workspace directory with `configs/` folder

---

## Installation

### Option 1: Install from PyPI (Future)

```bash
# Install mixseek-core package
uv pip install mixseek-core

# Or add to pyproject.toml
[project]
dependencies = [
    "mixseek-core>=0.1.0",
]
```

### Option 2: Development Installation

```bash
# Clone repository
git clone https://github.com/your-org/mixseek_core.git
cd mixseek_core

# Install dependencies with uv
uv sync

# Verify installation
python -c "from mixseek.evaluator import Evaluator; print('✓ Evaluator imported successfully')"
```

---

## Configuration

### Step 1: Set Environment Variables

Export API keys for your LLM providers:

```bash
# For Anthropic (Claude)
export ANTHROPIC_API_KEY="sk-ant-..."

# For OpenAI (GPT-4)
export OPENAI_API_KEY="sk-..."
```

**Security Note**: Never commit API keys to version control. Use environment variables or secure secret management.

### Step 2: Create Configuration File

Create `{workspace}/configs/evaluator.toml`:

```toml
# Evaluator Configuration
# File location: {workspace}/configs/evaluator.toml

# Default LLM model (fallback for metrics without explicit model)
default_model = "anthropic:claude-4-5-sonnet"

# Maximum retry attempts for LLM API calls
max_retries = 3

# Built-in evaluation metrics
[[metric]]
name = "clarity_coherence"
weight = 0.4
model = "anthropic:claude-4-5-sonnet"

[[metric]]
name = "coverage"
weight = 0.3
# Uses default_model

[[metric]]
name = "relevance"
weight = 0.3
model = "openai:gpt-5"  # Optional: Different model per metric
```

**Configuration Rules**:
- Metric weights must sum to 1.0 (±0.001 tolerance)
- Each metric name must be unique
- Model format: `"provider:model-name"`

---

## Basic Usage

### Example 1: Evaluate with Default Configuration

```python
from pathlib import Path
from mixseek.config.manager import ConfigurationManager
from mixseek.evaluator import Evaluator
from mixseek.models.evaluation_request import EvaluationRequest

# Initialize Evaluator with workspace path
workspace = Path("/path/to/workspace")
manager = ConfigurationManager(workspace=workspace)
settings = manager.get_evaluator_settings()
evaluator = Evaluator(settings=settings)

# Create evaluation request
request = EvaluationRequest(
    user_query="What are the benefits of Python?",
    submission=(
        "Python is a versatile programming language known for its simplicity and readability. "
        "It has an extensive ecosystem of libraries for data science, web development, and automation. "
        "Python's syntax is clear and beginner-friendly, making it ideal for both learning and production."
    ),
    team_id="team-alpha-001"
)

# Evaluate
result = evaluator.evaluate(request)

# Access results
print(f"Overall Score: {result.overall_score:.2f}")
for metric in result.metrics:
    print(f"{metric.metric_name}: {metric.score:.2f}")
    print(f"  Comment: {metric.evaluator_comment}\n")
```

**Expected Output**:
```
Overall Score: 87.25
clarity_coherence: 85.50
  Comment: The response is well-structured with clear language. Technical terms are explained adequately.

coverage: 78.00
  Comment: Covers main points but some depth is missing in the explanation.

relevance: 92.00
  Comment: Highly relevant to the user's query, directly addresses the question.
```

### Example 2: Evaluate with Custom Configuration

```python
from pathlib import Path
from mixseek.config.manager import ConfigurationManager
from mixseek.config.schema import EvaluatorSettings
from mixseek.evaluator import Evaluator
from mixseek.models.evaluation_request import EvaluationRequest
from mixseek.models.evaluation_config import EvaluationConfig, MetricConfig

# Option 1: Use custom EvaluatorSettings directly
custom_settings = EvaluatorSettings(
    default_model="anthropic:claude-sonnet-4-5-20250929",
    max_retries=5,  # More retries for critical evaluations
    metrics=[
        {"name": "ClarityCoherence", "weight": 0.5},
        {"name": "Relevance", "weight": 0.5}
    ]
)
evaluator = Evaluator(settings=custom_settings)

# Option 2: Load custom configuration from file
# manager = ConfigurationManager(workspace=Path("/workspace"))
# settings = manager.get_evaluator_settings("configs/custom_evaluator.toml")
# evaluator = Evaluator(settings=settings)

# Create request
request = EvaluationRequest(
    user_query="Explain quantum computing.",
    submission="Quantum computing uses quantum bits (qubits) that can be in superposition...",
    team_id="team-beta-002"
)

# Evaluate
result = evaluator.evaluate(request)

print(f"Custom evaluation: {result.overall_score:.2f}")
```

### Example 3: Batch Evaluation

```python
from pathlib import Path
from mixseek.config.manager import ConfigurationManager
from mixseek.evaluator import Evaluator
from mixseek.models.evaluation_request import EvaluationRequest

# Initialize Evaluator
manager = ConfigurationManager(workspace=Path("/workspace"))
settings = manager.get_evaluator_settings()
evaluator = Evaluator(settings=settings)

# Multiple query-response pairs
queries_and_responses = [
    ("What is Python?", "Python is a high-level programming language..."),
    ("Explain machine learning.", "Machine learning is a subset of AI..."),
    ("What is Docker?", "Docker is a containerization platform..."),
]

# Evaluate all
results = []
for user_query, submission in queries_and_responses:
    request = EvaluationRequest(
        user_query=user_query,
        submission=submission,
        team_id="batch-evaluation-001"
    )
    result = evaluator.evaluate(request)
    results.append(result)

# Analyze results
average_score = sum(r.overall_score for r in results) / len(results)
print(f"Average Score: {average_score:.2f}")
```

---

## Integration with MixSeek-Core

### Integration Point: Round Controller

The Evaluator is called by the Round Controller internally during round execution.

**Note**: RoundController is typically used through the Orchestrator, not directly. The evaluation process is automatically handled internally:

```python
# Internal implementation (automatically handled by RoundController)
# RoundController receives evaluator_settings from Orchestrator

from mixseek.config.schema import EvaluatorSettings
from mixseek.evaluator import Evaluator
from mixseek.models.evaluation_request import EvaluationRequest

# During round execution, RoundController creates Evaluator
evaluator = Evaluator(settings=evaluator_settings)

# After leader agent completes
request = EvaluationRequest(
    user_query=user_prompt,
    submission=submission_content,
    team_id=team_id
)

# Evaluate submission
evaluation_result = await evaluator.evaluate(request)

# Store result in leader_board table (DuckDB)
```

For direct usage, see the Orchestrator integration example instead.

### Integration Point: Leader Board

The Leader Board uses evaluation scores to rank submissions:

```python
from mixseek.leader_board import LeaderBoard
from mixseek.models.evaluation_result import EvaluationResult

leader_board = LeaderBoard(workspace_path=workspace)

# Add evaluation result to leader board
leader_board.add_submission(
    team_id="team-001",
    round_number=3,
    submission=submission,
    evaluation_result=evaluation_result
)

# Query top submissions
top_submissions = leader_board.get_top_submissions(limit=10)
for rank, entry in enumerate(top_submissions, start=1):
    print(f"{rank}. {entry.team_name}: {entry.evaluation_result.overall_score:.2f}")
```

---

## Error Handling

### Handling Input Validation Errors

```python
from mixseek.evaluator import Evaluator
from mixseek.models.evaluation_request import EvaluationRequest
from pydantic import ValidationError

try:
    request = EvaluationRequest(
        user_query="",  # Invalid: empty query
        submission="Response text",
        team_id="team-001"
    )
except ValidationError as e:
    print(f"Input validation error: {e}")
    # Handle error appropriately
```

### Handling Configuration Errors

```python
from mixseek.evaluator import Evaluator
from mixseek.exceptions import EvaluatorConfigError

try:
    evaluator = Evaluator(workspace_path=Path("/invalid/workspace"))
except FileNotFoundError as e:
    print(f"Configuration file not found: {e}")
    # Provide default config or prompt user to create one

except EvaluatorConfigError as e:
    print(f"Configuration error: {e}")
    # Fix configuration (e.g., weights don't sum to 1.0)
```

### Handling LLM API Errors

```python
from mixseek.evaluator import Evaluator
from mixseek.exceptions import EvaluatorAPIError

evaluator = Evaluator(workspace_path=workspace)

try:
    result = evaluator.evaluate(request)
except EvaluatorAPIError as e:
    print(f"LLM API error after {e.retry_count} retries: {e}")
    print(f"Provider: {e.provider}, Metric: {e.metric_name}")
    # Check API key, network connectivity, or LLM service status
```

---

## Advanced Configuration

### Custom Evaluation Metrics

Add custom Python functions for domain-specific evaluation:

```python
from mixseek.evaluator.metrics.base import BaseMetric
from mixseek.models.evaluation_result import MetricScore

class TechnicalAccuracyMetric(BaseMetric):
    """Custom metric for evaluating technical accuracy."""

    def evaluate(
        self,
        user_query: str,
        submission: str,
        model: str
    ) -> MetricScore:
        """
        Evaluate technical accuracy using domain-specific rules.

        Args:
            user_query: User's original query
            submission: AI agent's response
            model: LLM model identifier

        Returns:
            MetricScore with score and comment
        """
        # Custom evaluation logic
        # Option 1: Rule-based evaluation
        # Option 2: LLM-as-a-Judge with domain-specific prompt

        return MetricScore(
            metric_name="technical_accuracy",
            score=88.5,
            evaluator_comment="Technically accurate with minor omissions."
        )

# Register custom metric
evaluator = Evaluator(workspace_path=workspace)
evaluator.register_custom_metric("technical_accuracy", TechnicalAccuracyMetric())

# Update configuration to include custom metric
# In evaluator.toml:
# [[metric]]
# name = "technical_accuracy"
# weight = 0.25
```

### Per-Metric LLM Models

Use different LLM models for different metrics to optimize cost/performance:

```toml
# evaluator.toml

default_model = "anthropic:claude-3-5-haiku-latest"  # Fast, cheap default

[[metric]]
name = "clarity_coherence"
weight = 0.4
model = "anthropic:claude-3-5-haiku-latest"  # Fast model for simple metric

[[metric]]
name = "coverage"
weight = 0.3
model = "anthropic:claude-4-5-sonnet"  # Stronger model for complex reasoning

[[metric]]
name = "relevance"
weight = 0.3
model = "openai:gpt-5"  # Alternative provider for diversity
```

**Cost Optimization Strategy**:
- Use Haiku for simple metrics (clarity_coherence)
- Use Sonnet for complex reasoning (coverage)
- Use GPT-4 for alternative perspective (relevance)

---

## Performance Tuning

### Latency Expectations

| Metric Count | Expected Latency | Notes |
|--------------|------------------|-------|
| 1 metric | 2-5 seconds | Single LLM API call |
| 3 metrics (sequential) | 6-15 seconds | Default configuration (SC-001) |
| 3 metrics (parallel)* | 3-7 seconds | Future optimization |

*Parallel evaluation not implemented in v1.0

### Cost Optimization

**Per evaluation cost** (3 metrics, < 2000 chars):
- Claude 3.5 Sonnet: ~$0.01
- Claude 3.5 Haiku: ~$0.003
- GPT-4: ~$0.015

**Monthly cost estimates** (10,000 evaluations):
- All Sonnet: ~$95
- All Haiku: ~$30
- Mixed (Haiku + Sonnet): ~$50

### Caching Strategy

Implement response caching for frequently evaluated content:

```python
from functools import lru_cache
from mixseek.evaluator import Evaluator

class CachedEvaluator(Evaluator):
    """Evaluator with response caching."""

    @lru_cache(maxsize=1000)
    def _evaluate_cached(
        self,
        user_query: str,
        submission: str,
        team_id: str
    ) -> EvaluationResult:
        """Cache evaluation results by content hash."""
        request = EvaluationRequest(
            user_query=user_query,
            submission=submission,
            team_id=team_id
        )
        return super().evaluate(request)

# Use cached evaluator
cached_evaluator = CachedEvaluator(workspace_path=workspace)
```

---

## Testing

### Unit Testing

```python
import pytest
from mixseek.evaluator import Evaluator
from mixseek.models.evaluation_request import EvaluationRequest
from pydantic import ValidationError

def test_evaluate_valid_request(evaluator: Evaluator):
    """Test evaluation with valid request."""
    request = EvaluationRequest(
        user_query="What is Python?",
        submission="Python is a programming language.",
        team_id="test-team"
    )

    result = evaluator.evaluate(request)

    assert 0 <= result.overall_score <= 100
    assert len(result.metrics) == 3  # clarity_coherence, coverage, relevance

def test_evaluate_empty_query_raises_error():
    """Test that empty query raises ValidationError."""
    with pytest.raises(ValidationError, match="cannot be empty"):
        EvaluationRequest(
            user_query="",
            submission="Response",
            team_id="test-team"
        )

def test_weights_sum_to_one(evaluator: Evaluator):
    """Test that metric weights sum to 1.0."""
    config = evaluator.config
    total_weight = sum(m.weight for m in config.metric)
    assert 0.999 <= total_weight <= 1.001  # Floating-point tolerance
```

### Integration Testing

```python
import pytest
from pathlib import Path
from mixseek.evaluator import Evaluator
from mixseek.models.evaluation_request import EvaluationRequest

@pytest.mark.integration
def test_evaluate_with_real_llm(tmp_path: Path):
    """Integration test with actual LLM API."""
    # Create test configuration
    config_file = tmp_path / "configs" / "evaluator.toml"
    config_file.parent.mkdir(parents=True)
    config_file.write_text("""
default_model = "anthropic:claude-4-5-sonnet"
max_retries = 3

[[metric]]
name = "clarity_coherence"
weight = 1.0
""")

    evaluator = Evaluator(workspace_path=tmp_path)

    request = EvaluationRequest(
        user_query="What is Python?",
        submission="Python is a high-level, interpreted programming language.",
        team_id="integration-test"
    )

    result = evaluator.evaluate(request)

    assert 0 <= result.overall_score <= 100
    assert len(result.metrics) == 1
    assert result.metrics[0].metric_name == "clarity_coherence"
```

---

## Troubleshooting

### Problem: "Configuration file not found"

**Error**:
```
FileNotFoundError: Evaluator configuration not found: /workspace/configs/evaluator.toml
```

**Solution**:
1. Create `{workspace}/configs/` directory
2. Create `evaluator.toml` file with valid configuration
3. Verify file path and permissions

### Problem: "Metric weights must sum to 1.0"

**Error**:
```
ValueError: Metric weights must sum to 1.0, got: 0.8000.
Current weights: clarity_coherence=0.4, relevance=0.4
```

**Solution**:
Adjust weights in `evaluator.toml` to sum to 1.0:
```toml
[[metric]]
name = "clarity_coherence"
weight = 0.4

[[metric]]
name = "relevance"
weight = 0.6  # Changed from 0.4
```

### Problem: "Invalid model format"

**Error**:
```
ValueError: Invalid model format: 'claude-3-5-sonnet'.
Expected format: 'provider:model-name'
```

**Solution**:
Use correct format with provider prefix:
```toml
model = "anthropic:claude-4-5-sonnet"  # Correct
```

### Problem: API Key Not Found

**Error**:
```
ValueError: API key not found: ANTHROPIC_API_KEY environment variable must be set
```

**Solution**:
Export environment variable:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

---

## Next Steps

1. **Read Data Model Documentation**: `data-model.md` for detailed Pydantic model specifications
2. **Review API Contracts**: `contracts/` directory for JSON schemas
3. **Explore Research**: `research.md` for LLM-as-a-Judge implementation details
4. **Check Implementation Plan**: `plan.md` for architecture and design decisions

---

## Support

- **Documentation**: `/specs/006-evaluator/`
- **Issues**: GitHub Issues (https://github.com/your-org/mixseek_core/issues)
- **Discord**: MixSeek-Core Community Server

---

**Document Version**: 1.0
**Status**: Complete
**Last Updated**: 2025-10-22
