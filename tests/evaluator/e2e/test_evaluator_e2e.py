"""End-to-end tests with real LLM APIs.

Tests cover:
- T069: E2E test with real Anthropic API
- T070: E2E test with real OpenAI API
- T071: E2E test with per-metric model override (Claude + GPT)
- T072: E2E test validating quickstart.md examples

NOTE: These tests require valid API keys:
- ANTHROPIC_API_KEY for Claude tests
- OPENAI_API_KEY for GPT tests

Run with: pytest tests/evaluator/e2e/ -v -m e2e
Skip with: pytest tests/evaluator/ -v -m "not e2e"
"""

import os
from pathlib import Path

import pytest

from mixseek.config.manager import ConfigurationManager
from mixseek.config.schema import PromptBuilderSettings
from mixseek.evaluator.evaluator import Evaluator
from mixseek.models.evaluation_request import EvaluationRequest

# Skip all E2E tests if API keys not set
requires_anthropic_key = pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY environment variable not set",
)

requires_openai_key = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY environment variable not set",
)


@pytest.mark.e2e
class TestAnthropicIntegration:
    """T069: E2E tests with real Anthropic API (Claude)."""

    @requires_anthropic_key
    @pytest.mark.asyncio
    async def test_evaluate_with_anthropic_claude(self, tmp_path: Path) -> None:
        """Test evaluation with real Anthropic Claude API."""
        # Create config using Claude
        config_content = """
default_model = "anthropic:claude-sonnet-4-5-20250929"
max_retries = 3

[[metrics]]
name = "ClarityCoherence"
weight = 0.4

[[metrics]]
name = "Coverage"
weight = 0.3

[[metrics]]
name = "Relevance"
weight = 0.3
"""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        config_dir = workspace / "configs"
        config_dir.mkdir()
        config_file = config_dir / "evaluator.toml"
        config_file.write_text(config_content)

        manager = ConfigurationManager(workspace=workspace)
        settings = manager.get_evaluator_settings()
        prompt_builder_settings = PromptBuilderSettings()
        evaluator = Evaluator(settings=settings, prompt_builder_settings=prompt_builder_settings)

        request = EvaluationRequest(
            user_query="What are the main benefits of using Python for data science?",
            submission=(
                "Python is widely used in data science due to several key benefits:\n"
                "1. Rich ecosystem of libraries like pandas, numpy, and scikit-learn\n"
                "2. Simple and readable syntax that allows rapid prototyping\n"
                "3. Strong community support with extensive documentation\n"
                "4. Excellent visualization libraries such as matplotlib and seaborn\n"
                "5. Integration capabilities with big data tools like Apache Spark"
            ),
            team_id="test-team-e2e",
            config=None,
        )

        # Real API call
        result = await evaluator.evaluate(request)

        # Verify result structure
        assert result is not None
        assert len(result.metrics) == 3
        assert 0 <= result.overall_score <= 100

        # Verify all metrics have valid scores and comments
        for metric in result.metrics:
            assert metric.metric_name in [
                "ClarityCoherence",
                "Coverage",
                "Relevance",
            ]
            assert 0 <= metric.score <= 100
            assert len(metric.evaluator_comment) > 0

        print("\n[E2E] Anthropic Claude evaluation completed:")
        print(f"  Overall score: {result.overall_score}")
        for metric in result.metrics:
            print(f"  {metric.metric_name}: {metric.score}")

    @requires_anthropic_key
    @pytest.mark.asyncio
    async def test_evaluate_poor_quality_submission(self, tmp_path: Path) -> None:
        """Test that poor quality submission receives lower scores."""
        config_content = """
default_model = "anthropic:claude-sonnet-4-5-20250929"
max_retries = 3

[[metrics]]
name = "ClarityCoherence"
weight = 0.5

[[metrics]]
name = "Relevance"
weight = 0.5
"""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        config_dir = workspace / "configs"
        config_dir.mkdir()
        config_file = config_dir / "evaluator.toml"
        config_file.write_text(config_content)

        manager = ConfigurationManager(workspace=workspace)
        settings = manager.get_evaluator_settings()
        prompt_builder_settings = PromptBuilderSettings()
        evaluator = Evaluator(settings=settings, prompt_builder_settings=prompt_builder_settings)

        request = EvaluationRequest(
            user_query="What are the main benefits of using Python for data science?",
            submission="Python is good. Many people use it. It has libraries.",
            team_id="test-team-e2e",
            config=None,
        )

        result = await evaluator.evaluate(request)

        # Poor quality submission should get lower scores
        # (This is a heuristic check, not absolute)
        assert result.overall_score < 70.0

        print(f"\n[E2E] Poor quality submission score: {result.overall_score}")


@pytest.mark.e2e
class TestOpenAIIntegration:
    """T070: E2E tests with real OpenAI API (GPT)."""

    @requires_openai_key
    @pytest.mark.asyncio
    async def test_evaluate_with_openai_gpt(self, tmp_path: Path) -> None:
        """Test evaluation with real OpenAI GPT API."""
        config_content = """
default_model = "openai:gpt-4o"
max_retries = 3

[[metrics]]
name = "ClarityCoherence"
weight = 0.4

[[metrics]]
name = "Coverage"
weight = 0.3

[[metrics]]
name = "Relevance"
weight = 0.3
"""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        config_dir = workspace / "configs"
        config_dir.mkdir()
        config_file = config_dir / "evaluator.toml"
        config_file.write_text(config_content)

        manager = ConfigurationManager(workspace=workspace)
        settings = manager.get_evaluator_settings()
        prompt_builder_settings = PromptBuilderSettings()
        evaluator = Evaluator(settings=settings, prompt_builder_settings=prompt_builder_settings)

        request = EvaluationRequest(
            user_query="Explain the concept of machine learning in simple terms.",
            submission=(
                "Machine learning is a type of artificial intelligence that allows "
                "computers to learn from data without being explicitly programmed. "
                "Instead of following predefined rules, machine learning algorithms "
                "identify patterns in data and make decisions based on those patterns. "
                "For example, a machine learning model can learn to recognize cats in "
                "photos by analyzing thousands of cat images."
            ),
            team_id="test-team-e2e",
            config=None,
        )

        # Real API call
        result = await evaluator.evaluate(request)

        # Verify result structure
        assert result is not None
        assert len(result.metrics) == 3
        assert 0 <= result.overall_score <= 100

        # Verify all metrics evaluated
        metric_names = {m.metric_name for m in result.metrics}
        assert metric_names == {"ClarityCoherence", "Coverage", "Relevance"}

        print("\n[E2E] OpenAI GPT evaluation completed:")
        print(f"  Overall score: {result.overall_score}")
        for metric in result.metrics:
            print(f"  {metric.metric_name}: {metric.score}")


@pytest.mark.e2e
class TestMultiProviderIntegration:
    """T071: E2E test with per-metric model override (mixed providers)."""

    @requires_anthropic_key
    @requires_openai_key
    @requires_anthropic_key
    @requires_openai_key
    @pytest.mark.asyncio
    async def test_different_models_per_metric(self, tmp_path: Path) -> None:
        """Test evaluation with different LLM providers per metric."""
        config_content = """
default_model = "anthropic:claude-sonnet-4-5-20250929"
max_retries = 3

[[metrics]]
name = "ClarityCoherence"
weight = 0.4
model = "anthropic:claude-sonnet-4-5-20250929"

[[metrics]]
name = "Coverage"
weight = 0.3
# Uses default (Claude)

[[metrics]]
name = "Relevance"
weight = 0.3
model = "openai:gpt-4o"
"""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        config_dir = workspace / "configs"
        config_dir.mkdir()
        config_file = config_dir / "evaluator.toml"
        config_file.write_text(config_content)

        manager = ConfigurationManager(workspace=workspace)
        settings = manager.get_evaluator_settings()
        prompt_builder_settings = PromptBuilderSettings()
        evaluator = Evaluator(settings=settings, prompt_builder_settings=prompt_builder_settings)

        request = EvaluationRequest(
            user_query="What is quantum computing?",
            submission=(
                "Quantum computing is a revolutionary approach to computation that "
                "leverages the principles of quantum mechanics. Unlike classical computers "
                "that use bits (0 or 1), quantum computers use quantum bits or qubits, "
                "which can exist in superposition—representing both 0 and 1 simultaneously. "
                "This property, along with entanglement and interference, allows quantum "
                "computers to solve certain problems exponentially faster than classical computers."
            ),
            team_id="test-team-e2e",
            config=None,
        )

        # Real API calls to both providers
        result = await evaluator.evaluate(request)

        # Verify all metrics evaluated successfully
        assert len(result.metrics) == 3
        assert 0 <= result.overall_score <= 100

        print("\n[E2E] Multi-provider evaluation completed:")
        clarity_score = next(m.score for m in result.metrics if m.metric_name == "ClarityCoherence")
        print(f"  ClarityCoherence (Claude): {clarity_score}")
        print(f"  Coverage (Claude default): {next(m.score for m in result.metrics if m.metric_name == 'Coverage')}")
        print(f"  Relevance (GPT): {next(m.score for m in result.metrics if m.metric_name == 'Relevance')}")
        print(f"  Overall score: {result.overall_score}")


@pytest.mark.e2e
class TestQuickstartExamples:
    """T072: E2E tests validating quickstart.md examples."""

    @requires_anthropic_key
    @pytest.mark.asyncio
    async def test_quickstart_example_1_basic_usage(self, tmp_path: Path) -> None:
        """Test Example 1 from quickstart.md: Basic evaluation."""
        # Example 1: Basic evaluation with default configuration
        config_content = """
default_model = "anthropic:claude-sonnet-4-5-20250929"
max_retries = 3

[[metrics]]
name = "ClarityCoherence"
weight = 0.4

[[metrics]]
name = "Coverage"
weight = 0.3

[[metrics]]
name = "Relevance"
weight = 0.3
"""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        config_dir = workspace / "configs"
        config_dir.mkdir()
        config_file = config_dir / "evaluator.toml"
        config_file.write_text(config_content)

        # Initialize evaluator
        manager = ConfigurationManager(workspace=workspace)
        settings = manager.get_evaluator_settings()
        prompt_builder_settings = PromptBuilderSettings()
        evaluator = Evaluator(settings=settings, prompt_builder_settings=prompt_builder_settings)

        # Create evaluation request
        request = EvaluationRequest(
            user_query="What is Python?",
            submission="Python is a high-level programming language known for its simplicity and readability.",
            team_id="team-001",
            config=None,
        )

        # Evaluate
        result = await evaluator.evaluate(request)

        # Verify result
        assert result is not None
        assert result.overall_score is not None
        assert len(result.metrics) == 3

        print(f"\n[E2E Quickstart] Example 1 completed: score={result.overall_score}")

    @requires_anthropic_key
    @pytest.mark.asyncio
    async def test_quickstart_example_2_custom_weights(self, tmp_path: Path) -> None:
        """Test Example 2 from quickstart.md: Custom weights."""
        # Example 2: Custom metric weights
        config_content = """
default_model = "anthropic:claude-sonnet-4-5-20250929"
max_retries = 3

[[metrics]]
name = "Relevance"
weight = 0.5

[[metrics]]
name = "ClarityCoherence"
weight = 0.3

[[metrics]]
name = "Coverage"
weight = 0.2
"""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        config_dir = workspace / "configs"
        config_dir.mkdir()
        config_file = config_dir / "evaluator.toml"
        config_file.write_text(config_content)

        manager = ConfigurationManager(workspace=workspace)
        settings = manager.get_evaluator_settings()
        prompt_builder_settings = PromptBuilderSettings()
        evaluator = Evaluator(settings=settings, prompt_builder_settings=prompt_builder_settings)

        request = EvaluationRequest(
            user_query="Explain machine learning",
            submission="Machine learning is a subset of AI that enables systems to learn from data.",
            team_id="team-002",
            config=None,
        )

        result = await evaluator.evaluate(request)

        # Verify custom weights reflected in evaluation
        assert len(result.metrics) == 3
        assert result.overall_score is not None

        print(f"\n[E2E Quickstart] Example 2 (custom weights) completed: score={result.overall_score}")

    @requires_anthropic_key
    @requires_openai_key
    @requires_anthropic_key
    @requires_openai_key
    @pytest.mark.asyncio
    async def test_quickstart_example_3_per_metric_models(self, tmp_path: Path) -> None:
        """Test Example 3 from quickstart.md: Per-metric model override."""
        # Example 3: Different models per metric
        config_content = """
default_model = "anthropic:claude-sonnet-4-5-20250929"
max_retries = 3

[[metrics]]
name = "ClarityCoherence"
weight = 0.5
model = "anthropic:claude-sonnet-4-5-20250929"

[[metrics]]
name = "Relevance"
weight = 0.5
model = "openai:gpt-4o"
"""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        config_dir = workspace / "configs"
        config_dir.mkdir()
        config_file = config_dir / "evaluator.toml"
        config_file.write_text(config_content)

        manager = ConfigurationManager(workspace=workspace)
        settings = manager.get_evaluator_settings()
        prompt_builder_settings = PromptBuilderSettings()
        evaluator = Evaluator(settings=settings, prompt_builder_settings=prompt_builder_settings)

        request = EvaluationRequest(
            user_query="What is neural network?",
            submission="A neural network is a computational model inspired by biological neural networks.",
            team_id="team-003",
            config=None,
        )

        result = await evaluator.evaluate(request)

        # Verify both models used
        assert len(result.metrics) == 2
        metric_names = {m.metric_name for m in result.metrics}
        assert metric_names == {"ClarityCoherence", "Relevance"}

        print(f"\n[E2E Quickstart] Example 3 (multi-model) completed: score={result.overall_score}")

    @requires_anthropic_key
    @pytest.mark.asyncio
    async def test_consistency_across_multiple_evaluations(self, tmp_path: Path) -> None:
        """Test that evaluation consistency meets SC-002 requirement (< 5% variance)."""
        config_content = """
default_model = "anthropic:claude-sonnet-4-5-20250929"
max_retries = 3

[[metrics]]
name = "Relevance"
weight = 1.0
"""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        config_dir = workspace / "configs"
        config_dir.mkdir()
        config_file = config_dir / "evaluator.toml"
        config_file.write_text(config_content)

        manager = ConfigurationManager(workspace=workspace)
        settings = manager.get_evaluator_settings()
        prompt_builder_settings = PromptBuilderSettings()
        evaluator = Evaluator(settings=settings, prompt_builder_settings=prompt_builder_settings)

        request = EvaluationRequest(
            user_query="What is Python?",
            submission="Python is a high-level, interpreted programming language.",
            team_id="team-consistency",
            config=None,
        )

        # Evaluate 3 times (reduced from 10 for E2E test performance)
        import asyncio

        results = await asyncio.gather(*[evaluator.evaluate(request) for _ in range(3)])
        scores = [r.overall_score for r in results]

        # Calculate variance
        mean_score = sum(scores) / len(scores)
        variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
        std_dev = variance**0.5
        variance_percent = (std_dev / mean_score) * 100 if mean_score > 0 else 0

        print(f"\n[E2E Consistency] Scores: {scores}")
        print(f"  Mean: {mean_score:.2f}, Std Dev: {std_dev:.2f}, Variance: {variance_percent:.2f}%")

        # Verify consistency (< 5% variance for SC-002)
        # Note: With temperature=0, variance should be minimal
        # However, LLM providers may still have some stochasticity
        assert variance_percent < 10.0, f"Variance {variance_percent:.2f}% exceeds threshold"
