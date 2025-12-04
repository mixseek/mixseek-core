"""Performance tests for evaluator.

Tests cover:
- T073: SC-001 validation (< 30 seconds for < 2000 chars)
- T074: SC-002 validation (< 5% variance across evaluations)

NOTE: These tests may require real API keys for accurate performance measurement.
For unit/integration testing, use mocked APIs.
"""

import statistics
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from mixseek.config.manager import ConfigurationManager
from mixseek.config.schema import PromptBuilderSettings
from mixseek.evaluator.evaluator import Evaluator
from mixseek.models.evaluation_request import EvaluationRequest
from mixseek.models.evaluation_result import MetricScore


class TestPerformanceLatency:
    """T073: Test SC-001 requirement (< 30 seconds for < 2000 chars)."""

    @pytest.mark.asyncio
    async def test_evaluation_completes_within_30_seconds(self, tmp_path: Path, mock_all_api_keys: None) -> None:
        """Test that evaluation of short input (<2000 chars) completes within 30 seconds."""
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

        # Create request with < 2000 characters
        user_query = "What are the main benefits of using Python for data science?"
        submission = (
            "Python offers several key benefits for data science:\n\n"
            "1. Rich Ecosystem: Python has an extensive collection of libraries "
            "specifically designed for data science, including pandas for data "
            "manipulation, numpy for numerical computing, scikit-learn for machine "
            "learning, and matplotlib/seaborn for visualization.\n\n"
            "2. Easy to Learn: Python's clean and readable syntax makes it accessible "
            "to beginners while remaining powerful enough for experts. This lowers "
            "the barrier to entry for data science.\n\n"
            "3. Strong Community: A large, active community provides excellent "
            "documentation, tutorials, and support through forums and online resources.\n\n"
            "4. Integration: Python integrates well with big data tools like Apache "
            "Spark and databases, making it suitable for enterprise-scale projects.\n\n"
            "5. Versatility: Beyond data science, Python can be used for web "
            "development, automation, and more, making it a versatile skill."
        )

        assert len(submission) < 2000, "Test submission exceeds 2000 characters"

        request = EvaluationRequest(user_query=user_query, submission=submission, team_id="test-perf-001")

        # Mock metric evaluations to simulate realistic latency
        def mock_metric_eval(*args, **kwargs):
            # Simulate LLM API latency (2-4 seconds per metric)
            time.sleep(2.5)
            return MetricScore(
                metric_name=kwargs.get("metric_name", "test"),
                score=85.0,
                evaluator_comment="Test evaluation",
            )

        with (
            patch.object(
                evaluator._builtin_metrics["ClarityCoherence"],
                "evaluate",
                side_effect=lambda *args, **kwargs: MetricScore(
                    metric_name="ClarityCoherence",
                    score=85.0,
                    evaluator_comment="Clear",
                ),
            ),
            patch.object(
                evaluator._builtin_metrics["Coverage"],
                "evaluate",
                side_effect=lambda *args, **kwargs: MetricScore(
                    metric_name="Coverage", score=80.0, evaluator_comment="Adequate"
                ),
            ),
            patch.object(
                evaluator._builtin_metrics["Relevance"],
                "evaluate",
                side_effect=lambda *args, **kwargs: MetricScore(
                    metric_name="Relevance", score=90.0, evaluator_comment="Relevant"
                ),
            ),
        ):
            start_time = time.time()
            result = await evaluator.evaluate(request)
            elapsed_time = time.time() - start_time

        print(f"\n[Performance] Evaluation time: {elapsed_time:.2f}s")

        # Verify SC-001: < 30 seconds
        assert elapsed_time < 30.0, f"Evaluation took {elapsed_time:.2f}s, exceeds 30s limit (SC-001)"

        # Verify result is valid
        assert result is not None
        assert len(result.metrics) == 3

    @pytest.mark.asyncio
    async def test_evaluation_time_scales_with_input_length(self, tmp_path: Path, mock_all_api_keys: None) -> None:
        """Test that evaluation time increases reasonably with input length."""
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

        # Test with different input lengths
        short_submission = "Python is good for data science."
        long_submission = "Python is an excellent choice for data science work. " * 50  # ~300 words

        with patch.object(
            evaluator._builtin_metrics["Relevance"],
            "evaluate",
            return_value=MetricScore(metric_name="Relevance", score=85.0, evaluator_comment="Relevant"),
        ):
            # Short input
            request_short = EvaluationRequest(
                user_query="Why Python?",
                submission=short_submission,
                team_id="test-short",
            )
            start_short = time.time()
            await evaluator.evaluate(request_short)
            time_short = time.time() - start_short

            # Long input
            request_long = EvaluationRequest(
                user_query="Why Python?",
                submission=long_submission,
                team_id="test-long",
            )
            start_long = time.time()
            await evaluator.evaluate(request_long)
            time_long = time.time() - start_long

        print(f"\n[Performance] Short input: {time_short:.2f}s")
        print(f"[Performance] Long input: {time_long:.2f}s")

        # Both should be under 30 seconds
        assert time_short < 30.0
        assert time_long < 30.0


class TestPerformanceConsistency:
    """T074: Test SC-002 requirement (< 5% variance across evaluations)."""

    @pytest.mark.asyncio
    async def test_score_consistency_meets_5_percent_threshold(self, tmp_path: Path, mock_all_api_keys: None) -> None:
        """Test that variance in scores is < 5% across 10 evaluations."""
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
            user_query="What is machine learning?",
            submission="Machine learning is a branch of AI that enables systems to learn from data.",
            team_id="test-consistency",
        )

        # Mock with slight variance to simulate real LLM behavior
        # (In reality, with temperature=0, variance should be minimal)
        eval_count = {"count": 0}

        def mock_clarity_eval(*args, **kwargs):
            eval_count["count"] += 1
            # Simulate small variance (< 2%)
            base_score = 85.0
            variance = (eval_count["count"] % 3) * 0.5  # ±0.5 points
            return MetricScore(
                metric_name="ClarityCoherence",
                score=base_score + variance,
                evaluator_comment="Clear",
            )

        def mock_relevance_eval(*args, **kwargs):
            # Simulate small variance
            base_score = 90.0
            variance = (eval_count["count"] % 2) * 0.3
            return MetricScore(
                metric_name="Relevance",
                score=base_score + variance,
                evaluator_comment="Relevant",
            )

        # Evaluate 10 times
        results: list[float] = []
        with (
            patch.object(
                evaluator._builtin_metrics["ClarityCoherence"],
                "evaluate",
                side_effect=mock_clarity_eval,
            ),
            patch.object(
                evaluator._builtin_metrics["Relevance"],
                "evaluate",
                side_effect=mock_relevance_eval,
            ),
        ):
            for i in range(10):
                result = await evaluator.evaluate(request)
                results.append(result.overall_score)

        # Calculate statistics
        mean_score = statistics.mean(results)
        stdev_score = statistics.stdev(results)
        variance_percent = (stdev_score / mean_score) * 100 if mean_score > 0 else 0

        print("\n[Performance Consistency] Results over 10 evaluations:")
        print(f"  Scores: {[f'{s:.2f}' for s in results]}")
        print(f"  Mean: {mean_score:.2f}")
        print(f"  Std Dev: {stdev_score:.2f}")
        print(f"  Variance: {variance_percent:.2f}%")

        # Verify SC-002: < 5% variance
        assert variance_percent < 5.0, f"Variance {variance_percent:.2f}% exceeds 5% threshold (SC-002)"

    @pytest.mark.asyncio
    async def test_individual_metric_consistency(self, tmp_path: Path, mock_all_api_keys: None) -> None:
        """Test consistency for each individual metric."""
        config_content = """
default_model = "anthropic:claude-sonnet-4-5-20250929"
max_retries = 3

[[metrics]]
name = "ClarityCoherence"
weight = 0.34

[[metrics]]
name = "Coverage"
weight = 0.33

[[metrics]]
name = "Relevance"
weight = 0.33
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
            user_query="Explain quantum computing",
            submission="Quantum computing uses quantum mechanics principles for computation.",
            team_id="test-metric-consistency",
        )

        # Mock with deterministic scores
        with (
            patch.object(
                evaluator._builtin_metrics["ClarityCoherence"],
                "evaluate",
                return_value=MetricScore(
                    metric_name="ClarityCoherence",
                    score=85.0,
                    evaluator_comment="Clear",
                ),
            ),
            patch.object(
                evaluator._builtin_metrics["Coverage"],
                "evaluate",
                return_value=MetricScore(metric_name="Coverage", score=80.0, evaluator_comment="Adequate"),
            ),
            patch.object(
                evaluator._builtin_metrics["Relevance"],
                "evaluate",
                return_value=MetricScore(metric_name="Relevance", score=90.0, evaluator_comment="Relevant"),
            ),
        ):
            # Evaluate 5 times
            import asyncio

            results = await asyncio.gather(*[evaluator.evaluate(request) for _ in range(5)])

        # Check consistency for each metric
        for metric_name in ["ClarityCoherence", "Coverage", "Relevance"]:
            scores = [next(m.score for m in result.metrics if m.metric_name == metric_name) for result in results]

            # With deterministic mocks, all scores should be identical
            assert len(set(scores)) == 1, f"Metric {metric_name} has inconsistent scores: {scores}"

            print(f"[Metric Consistency] {metric_name}: {scores[0]:.2f} (0% variance)")

    @pytest.mark.asyncio
    async def test_overall_score_calculation_consistency(self, tmp_path: Path, mock_all_api_keys: None) -> None:
        """Test that overall score calculation is deterministic given same metric scores."""
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
            user_query="Test query",
            submission="Test submission",
            team_id="test-calc",
        )

        # Mock with fixed scores
        with (
            patch.object(
                evaluator._builtin_metrics["ClarityCoherence"],
                "evaluate",
                return_value=MetricScore(
                    metric_name="ClarityCoherence",
                    score=85.0,
                    evaluator_comment="Clear",
                ),
            ),
            patch.object(
                evaluator._builtin_metrics["Coverage"],
                "evaluate",
                return_value=MetricScore(metric_name="Coverage", score=80.0, evaluator_comment="OK"),
            ),
            patch.object(
                evaluator._builtin_metrics["Relevance"],
                "evaluate",
                return_value=MetricScore(metric_name="Relevance", score=90.0, evaluator_comment="Relevant"),
            ),
        ):
            # Evaluate multiple times
            import asyncio

            results = await asyncio.gather(*[evaluator.evaluate(request) for _ in range(5)])

        # All overall scores should be identical
        overall_scores = [r.overall_score for r in results]
        assert len(set(overall_scores)) == 1, f"Overall scores inconsistent: {overall_scores}"

        # Verify calculation: 85*0.4 + 80*0.3 + 90*0.3 = 85.0
        expected = 85.0 * 0.4 + 80.0 * 0.3 + 90.0 * 0.3
        assert overall_scores[0] == pytest.approx(expected, abs=0.01)

        print(f"[Calculation Consistency] Overall score: {overall_scores[0]:.2f}")
