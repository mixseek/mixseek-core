"""Integration tests for User Story 3: Custom Metrics Integration.

Tests cover:
- T065: Custom metric registration and usage
- T066: Custom metric validation
- T067: Mixed built-in and custom metrics
- T068: Rule-based custom metrics (without LLM)
"""

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from mixseek.config.manager import ConfigurationManager
from mixseek.config.schema import PromptBuilderSettings
from mixseek.evaluator.evaluator import Evaluator
from mixseek.evaluator.metrics.base import BaseMetric
from mixseek.models.evaluation_request import EvaluationRequest
from mixseek.models.evaluation_result import MetricScore


# Custom metric implementations for testing
class TechnicalAccuracyMetric(BaseMetric):
    """Example custom metric for testing."""

    async def evaluate(
        self,
        user_query: str,
        submission: str,
        **kwargs: object,
    ) -> MetricScore:
        """Evaluate technical accuracy (mocked for testing)."""
        return MetricScore(
            metric_name="technical_accuracy",
            score=88.0,
            evaluator_comment="Technical accuracy is good with minor issues.",
        )


class LengthBasedMetric(BaseMetric):
    """Rule-based custom metric that doesn't use LLM."""

    async def evaluate(
        self,
        user_query: str,
        submission: str,
        **kwargs: object,
    ) -> MetricScore:
        """Evaluate based on response length (deterministic, no LLM)."""
        # Simple rule: score based on submission length
        length = len(submission)
        if length < 50:
            score = 30.0
            comment = "Response too short"
        elif length < 200:
            score = 70.0
            comment = "Response adequate length"
        else:
            score = 95.0
            comment = "Response comprehensive length"

        return MetricScore(metric_name="length_based", score=score, evaluator_comment=comment)


class InvalidMetricNoInheritance:
    """Invalid metric that doesn't inherit from BaseMetric."""

    def evaluate(
        self,
        user_query,
        submission,
    ):
        return MetricScore(
            metric_name="invalid",
            score=50.0,
            evaluator_comment="This should not work",
        )


class InvalidMetricNoEvaluate(BaseMetric):
    """Invalid metric that doesn't implement evaluate()."""

    # Provide a minimal implementation to allow instantiation
    def evaluate(
        self,
        user_query: Any,
        submission: Any,
        **kwargs: object,
    ) -> Any:
        """Dummy implementation."""
        pass


class TestCustomMetricRegistration:
    """T065: Test custom metric registration and usage."""

    @pytest.mark.asyncio
    async def test_register_and_use_custom_metric(
        self,
        tmp_path: Path,
        sample_evaluation_request_data: dict[str, Any],
        mock_all_api_keys: None,
    ) -> None:
        """Test registering a custom metric and using it in evaluation."""
        # Create config with custom metric
        config_content = """
default_model = "anthropic:claude-sonnet-4-5-20250929"
max_retries = 3

[[metrics]]
name = "technical_accuracy"
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

        # Register custom metric
        custom_metric = TechnicalAccuracyMetric()
        evaluator.register_custom_metric("technical_accuracy", custom_metric)

        # Create request
        request = EvaluationRequest(**sample_evaluation_request_data, config=None)

        # Evaluate
        result = await evaluator.evaluate(request)

        # Verify custom metric was used
        assert len(result.metrics) == 1
        assert result.metrics[0].metric_name == "technical_accuracy"
        assert result.metrics[0].score == 88.0
        assert "Technical accuracy" in result.metrics[0].evaluator_comment

    @pytest.mark.asyncio
    async def test_custom_metric_appears_in_results(
        self,
        tmp_path: Path,
        sample_evaluation_request_data: dict[str, Any],
        mock_all_api_keys: None,
    ) -> None:
        """Test that custom metric results appear alongside built-in metrics."""
        config_content = """
default_model = "anthropic:claude-sonnet-4-5-20250929"
max_retries = 3

[[metrics]]
name = "ClarityCoherence"
weight = 0.5

[[metrics]]
name = "technical_accuracy"
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
        evaluator.register_custom_metric("technical_accuracy", TechnicalAccuracyMetric())

        request = EvaluationRequest(**sample_evaluation_request_data, config=None)

        # Mock built-in metric
        with patch.object(
            evaluator._builtin_metrics["ClarityCoherence"],
            "evaluate",
            return_value=MetricScore(
                metric_name="ClarityCoherence",
                score=85.0,
                evaluator_comment="Clear",
            ),
        ):
            result = await evaluator.evaluate(request)

        # Verify both metrics in results
        assert len(result.metrics) == 2
        metric_names = {m.metric_name for m in result.metrics}
        assert metric_names == {"ClarityCoherence", "technical_accuracy"}


class TestCustomMetricValidation:
    """T066: Test validation of custom metrics."""

    def test_invalid_metric_no_inheritance_raises_error(self, temp_workspace: Path) -> None:
        """Test that metric not inheriting from BaseMetric raises TypeError."""
        manager = ConfigurationManager(workspace=temp_workspace)
        settings = manager.get_evaluator_settings()
        prompt_builder_settings = PromptBuilderSettings()
        evaluator = Evaluator(settings=settings, prompt_builder_settings=prompt_builder_settings)

        with pytest.raises(TypeError) as exc_info:
            evaluator.register_custom_metric("invalid", InvalidMetricNoInheritance())  # type: ignore[arg-type]

        assert "BaseMetric" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invalid_metric_no_evaluate_method_raises_error(self, temp_workspace: Path) -> None:
        """Test that metric without proper evaluate() implementation fails on use."""
        manager = ConfigurationManager(workspace=temp_workspace)
        settings = manager.get_evaluator_settings()
        prompt_builder_settings = PromptBuilderSettings()
        evaluator = Evaluator(settings=settings, prompt_builder_settings=prompt_builder_settings)

        # Registration should succeed (has evaluate method)
        evaluator.register_custom_metric("invalid", InvalidMetricNoEvaluate())

        # But evaluation should fail because evaluate() returns None, not MetricScore
        config_content = """
default_model = "anthropic:claude-sonnet-4-5-20250929"
max_retries = 3

[[metrics]]
name = "invalid"
weight = 1.0
"""
        config_dir = temp_workspace / "configs"
        config_dir.mkdir(exist_ok=True)
        config_file = config_dir / "evaluator.toml"
        config_file.write_text(config_content)

        manager = ConfigurationManager(workspace=temp_workspace)
        settings = manager.get_evaluator_settings()
        prompt_builder_settings = PromptBuilderSettings()
        evaluator = Evaluator(settings=settings, prompt_builder_settings=prompt_builder_settings)
        evaluator.register_custom_metric("invalid", InvalidMetricNoEvaluate())

        from mixseek.models.evaluation_request import EvaluationRequest

        request = EvaluationRequest(user_query="test", submission="test", team_id="test", config=None)

        # Should fail when trying to use the invalid metric
        with pytest.raises((AttributeError, TypeError)):
            await evaluator.evaluate(request)

    @pytest.mark.asyncio
    async def test_unregistered_custom_metric_raises_error(
        self,
        tmp_path: Path,
        sample_evaluation_request_data: dict[str, Any],
        mock_all_api_keys: None,
    ) -> None:
        """Test that using unregistered custom metric raises ValueError."""
        config_content = """
default_model = "anthropic:claude-sonnet-4-5-20250929"
max_retries = 3

[[metrics]]
name = "technical_accuracy"
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
        # Note: NOT registering the custom metric

        request = EvaluationRequest(**sample_evaluation_request_data, config=None)

        with pytest.raises(ValueError) as exc_info:
            await evaluator.evaluate(request)

        assert "technical_accuracy" in str(exc_info.value)
        assert "not found" in str(exc_info.value).lower()


class TestMixedMetrics:
    """T067: Test mixed built-in and custom metrics."""

    @pytest.mark.asyncio
    async def test_built_in_and_custom_metrics_together(
        self,
        tmp_path: Path,
        sample_evaluation_request_data: dict[str, Any],
        mock_all_api_keys: None,
    ) -> None:
        """Test evaluation with both built-in and custom metrics."""
        config_content = """
default_model = "anthropic:claude-sonnet-4-5-20250929"
max_retries = 3

[[metrics]]
name = "ClarityCoherence"
weight = 0.3

[[metrics]]
name = "Relevance"
weight = 0.3

[[metrics]]
name = "technical_accuracy"
weight = 0.4
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
        evaluator.register_custom_metric("technical_accuracy", TechnicalAccuracyMetric())

        request = EvaluationRequest(**sample_evaluation_request_data, config=None)

        # Mock built-in metrics
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
                evaluator._builtin_metrics["Relevance"],
                "evaluate",
                return_value=MetricScore(metric_name="Relevance", score=90.0, evaluator_comment="Relevant"),
            ),
        ):
            result = await evaluator.evaluate(request)

        # Verify all three metrics evaluated
        assert len(result.metrics) == 3
        metric_names = {m.metric_name for m in result.metrics}
        assert metric_names == {
            "ClarityCoherence",
            "Relevance",
            "technical_accuracy",
        }

        # Verify overall score calculation with mixed weights
        expected_overall = 85.0 * 0.3 + 90.0 * 0.3 + 88.0 * 0.4
        assert result.overall_score == pytest.approx(expected_overall, abs=0.01)

    @pytest.mark.asyncio
    async def test_custom_metric_overrides_built_in_name(
        self,
        tmp_path: Path,
        sample_evaluation_request_data: dict[str, Any],
        mock_all_api_keys: None,
    ) -> None:
        """Test that custom metric with same name as built-in overrides it."""
        config_content = """
default_model = "anthropic:claude-sonnet-4-5-20250929"
max_retries = 3

[[metrics]]
name = "ClarityCoherence"
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

        # Register custom metric with same name as built-in
        class CustomClarityMetric(BaseMetric):
            async def evaluate(
                self,
                user_query: Any,
                submission: Any,
                **kwargs: object,
            ) -> Any:
                return MetricScore(
                    metric_name="ClarityCoherence",
                    score=99.0,  # Different score to verify it's the custom one
                    evaluator_comment="Custom clarity evaluation",
                )

        evaluator.register_custom_metric("ClarityCoherence", CustomClarityMetric())

        request = EvaluationRequest(**sample_evaluation_request_data, config=None)
        result = await evaluator.evaluate(request)

        # Verify custom metric was used (score 99.0, not built-in)
        assert result.metrics[0].score == 99.0
        assert "Custom clarity" in result.metrics[0].evaluator_comment


class TestRuleBasedMetrics:
    """T068: Test rule-based custom metrics without LLM."""

    @pytest.mark.asyncio
    async def test_deterministic_rule_based_metric(
        self,
        tmp_path: Path,
        sample_evaluation_request_data: dict[str, Any],
        mock_all_api_keys: None,
    ) -> None:
        """Test custom metric using deterministic rules without LLM."""
        config_content = """
default_model = "anthropic:claude-sonnet-4-5-20250929"
max_retries = 3

[[metrics]]
name = "length_based"
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
        evaluator.register_custom_metric("length_based", LengthBasedMetric())

        # Test with different submission lengths
        short_request = EvaluationRequest(
            user_query="Test query",
            submission="Short",  # < 50 chars
            team_id="team-001",
            config=None,
        )

        result_short = await evaluator.evaluate(short_request)
        assert result_short.metrics[0].score == 30.0
        assert "too short" in result_short.metrics[0].evaluator_comment

        # Medium length
        medium_request = EvaluationRequest(
            user_query="Test query",
            submission="This is a medium-length response that falls between 50 and 200 characters in total length.",
            team_id="team-001",
            config=None,
        )

        result_medium = await evaluator.evaluate(medium_request)
        assert result_medium.metrics[0].score == 70.0
        assert "adequate" in result_medium.metrics[0].evaluator_comment

        # Long
        long_request = EvaluationRequest(
            user_query="Test query",
            submission="This is a much longer response that exceeds 200 characters. " * 10,
            team_id="team-001",
            config=None,
        )

        result_long = await evaluator.evaluate(long_request)
        assert result_long.metrics[0].score == 95.0
        assert "comprehensive" in result_long.metrics[0].evaluator_comment

    @pytest.mark.asyncio
    async def test_rule_based_metric_consistent_results(
        self,
        tmp_path: Path,
        sample_evaluation_request_data: dict[str, Any],
        mock_all_api_keys: None,
    ) -> None:
        """Test that rule-based metric returns consistent results (no variance)."""
        config_content = """
default_model = "anthropic:claude-sonnet-4-5-20250929"
max_retries = 3

[[metrics]]
name = "length_based"
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
        evaluator.register_custom_metric("length_based", LengthBasedMetric())

        request = EvaluationRequest(**sample_evaluation_request_data, config=None)

        # Evaluate 10 times
        import asyncio

        results = await asyncio.gather(*[evaluator.evaluate(request) for _ in range(10)])

        # Verify all results are identical (0% variance for rule-based)
        first_score = results[0].overall_score
        for result in results[1:]:
            assert result.overall_score == first_score

    @pytest.mark.asyncio
    async def test_mixed_llm_and_rule_based_metrics(
        self,
        tmp_path: Path,
        sample_evaluation_request_data: dict[str, Any],
        mock_all_api_keys: None,
    ) -> None:
        """Test evaluation with both LLM-based and rule-based metrics."""
        config_content = """
default_model = "anthropic:claude-sonnet-4-5-20250929"
max_retries = 3

[[metrics]]
name = "ClarityCoherence"
weight = 0.5

[[metrics]]
name = "length_based"
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
        evaluator.register_custom_metric("length_based", LengthBasedMetric())

        request = EvaluationRequest(**sample_evaluation_request_data, config=None)

        # Mock LLM-based metric
        with patch.object(
            evaluator._builtin_metrics["ClarityCoherence"],
            "evaluate",
            return_value=MetricScore(
                metric_name="ClarityCoherence",
                score=85.0,
                evaluator_comment="Clear",
            ),
        ):
            result = await evaluator.evaluate(request)

        # Verify both metrics evaluated
        assert len(result.metrics) == 2
        metric_names = {m.metric_name for m in result.metrics}
        assert metric_names == {"ClarityCoherence", "length_based"}

        # Verify overall score combines both
        length_score = next(m.score for m in result.metrics if m.metric_name == "length_based")
        expected_overall = 85.0 * 0.5 + length_score * 0.5
        assert result.overall_score == pytest.approx(expected_overall, abs=0.01)
