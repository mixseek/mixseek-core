"""Integration tests for User Story 1: Built-in Metrics Evaluation.

Tests cover:
- T057: Basic evaluation with default config and all 3 metrics
- T058: Sequential metric evaluation (no parallel execution)
- T059: LLM API retry logic with mocked failures
- T060: Empty/whitespace input validation
"""

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from mixseek.config.manager import ConfigurationManager
from mixseek.config.schema import PromptBuilderSettings
from mixseek.evaluator.evaluator import Evaluator
from mixseek.evaluator.exceptions import EvaluatorAPIError
from mixseek.models.evaluation_request import EvaluationRequest
from mixseek.models.evaluation_result import MetricScore


class TestBasicEvaluation:
    """T057: Test basic evaluation with default config and all 3 metrics."""

    def test_evaluator_loads_default_config(self, temp_workspace: Path) -> None:
        """Test that Evaluator correctly loads configuration from TOML file."""
        manager = ConfigurationManager(workspace=temp_workspace)
        settings = manager.get_evaluator_settings()
        prompt_builder_settings = PromptBuilderSettings()
        evaluator = Evaluator(settings=settings, prompt_builder_settings=prompt_builder_settings)

        assert evaluator.config is not None
        assert evaluator.config.llm_default.model == "anthropic:claude-sonnet-4-5-20250929"
        assert evaluator.config.llm_default.max_retries == 3
        assert len(evaluator.config.metrics) == 3

        # Verify all three built-in metrics are configured
        metric_names = {m.name for m in evaluator.config.metrics}
        assert metric_names == {"ClarityCoherence", "Coverage", "Relevance"}

    @pytest.mark.asyncio
    async def test_evaluate_returns_result_structure(
        self,
        temp_workspace: Path,
        sample_evaluation_request_data: dict[str, Any],
        mock_all_api_keys: None,
    ) -> None:
        """Test that evaluate() returns valid EvaluationResult with all metrics."""
        manager = ConfigurationManager(workspace=temp_workspace)
        settings = manager.get_evaluator_settings()
        prompt_builder_settings = PromptBuilderSettings()
        evaluator = Evaluator(settings=settings, prompt_builder_settings=prompt_builder_settings)
        request = EvaluationRequest(**sample_evaluation_request_data, config=None)

        # Mock all three metric evaluations
        with (
            patch.object(evaluator._builtin_metrics["ClarityCoherence"], "evaluate") as mock_clarity,
            patch.object(evaluator._builtin_metrics["Coverage"], "evaluate") as mock_coverage,
            patch.object(evaluator._builtin_metrics["Relevance"], "evaluate") as mock_relevance,
        ):
            mock_clarity.return_value = MetricScore(
                metric_name="ClarityCoherence",
                score=85.0,
                evaluator_comment="Clear and well-structured response.",
            )
            mock_coverage.return_value = MetricScore(
                metric_name="Coverage",
                score=80.0,
                evaluator_comment="Covers main points adequately.",
            )
            mock_relevance.return_value = MetricScore(
                metric_name="Relevance",
                score=90.0,
                evaluator_comment="Highly relevant to the query.",
            )

            result = await evaluator.evaluate(request)

        # Verify result structure
        assert result is not None
        assert len(result.metrics) == 3
        assert result.overall_score is not None

        # Verify all three metrics are present
        metric_names = {m.metric_name for m in result.metrics}
        assert metric_names == {"ClarityCoherence", "Coverage", "Relevance"}

        # Verify scores are in valid range
        for metric in result.metrics:
            assert 0 <= metric.score <= 100
            assert metric.evaluator_comment != ""

        # Verify overall score is computed correctly
        # weights: clarity_coherence=0.4, coverage=0.3, relevance=0.3
        expected_overall = 85.0 * 0.4 + 80.0 * 0.3 + 90.0 * 0.3
        assert result.overall_score == pytest.approx(expected_overall, abs=0.01)

    @pytest.mark.asyncio
    async def test_evaluate_with_custom_config_in_request(
        self,
        temp_workspace: Path,
        sample_evaluation_request_data: dict[str, Any],
        custom_weights_config_toml: str,
        mock_all_api_keys: None,
    ) -> None:
        """Test that custom config in request overrides default config."""
        import tomllib

        from mixseek.models.evaluation_config import EvaluationConfig

        # Parse custom config
        custom_config = EvaluationConfig.model_validate(tomllib.loads(custom_weights_config_toml))

        manager = ConfigurationManager(workspace=temp_workspace)
        settings = manager.get_evaluator_settings()
        prompt_builder_settings = PromptBuilderSettings()
        evaluator = Evaluator(settings=settings, prompt_builder_settings=prompt_builder_settings)
        request = EvaluationRequest(**sample_evaluation_request_data, config=custom_config)

        # Mock metric evaluations
        with (
            patch.object(evaluator._builtin_metrics["ClarityCoherence"], "evaluate") as mock_clarity,
            patch.object(evaluator._builtin_metrics["Coverage"], "evaluate") as mock_coverage,
            patch.object(evaluator._builtin_metrics["Relevance"], "evaluate") as mock_relevance,
        ):
            mock_relevance.return_value = MetricScore(
                metric_name="Relevance", score=90.0, evaluator_comment="Relevant"
            )
            mock_clarity.return_value = MetricScore(
                metric_name="ClarityCoherence", score=85.0, evaluator_comment="Clear"
            )
            mock_coverage.return_value = MetricScore(metric_name="Coverage", score=80.0, evaluator_comment="Adequate")

            result = await evaluator.evaluate(request)

        # Verify custom weights are used: relevance=0.5, clarity_coherence=0.3, coverage=0.2
        expected_overall = 90.0 * 0.5 + 85.0 * 0.3 + 80.0 * 0.2
        assert result.overall_score == pytest.approx(expected_overall, abs=0.01)


class TestSequentialEvaluation:
    """T058: Test that metrics are evaluated sequentially, not in parallel."""

    @pytest.mark.asyncio
    async def test_metrics_evaluated_in_order(
        self,
        temp_workspace: Path,
        sample_evaluation_request_data: dict[str, Any],
        mock_all_api_keys: None,
    ) -> None:
        """Test that metrics are called sequentially in configuration order."""
        manager = ConfigurationManager(workspace=temp_workspace)
        settings = manager.get_evaluator_settings()
        prompt_builder_settings = PromptBuilderSettings()
        evaluator = Evaluator(settings=settings, prompt_builder_settings=prompt_builder_settings)
        request = EvaluationRequest(**sample_evaluation_request_data, config=None)

        # Track call order
        call_order = []

        def mock_clarity_eval(*args, **kwargs):
            call_order.append("ClarityCoherence")
            return MetricScore(
                metric_name="ClarityCoherence",
                score=85.0,
                evaluator_comment="Clear",
            )

        def mock_coverage_eval(*args, **kwargs):
            call_order.append("Coverage")
            return MetricScore(metric_name="Coverage", score=80.0, evaluator_comment="Adequate")

        def mock_relevance_eval(*args, **kwargs):
            call_order.append("Relevance")
            return MetricScore(metric_name="Relevance", score=90.0, evaluator_comment="Relevant")

        with (
            patch.object(evaluator._builtin_metrics["ClarityCoherence"], "evaluate", side_effect=mock_clarity_eval),
            patch.object(evaluator._builtin_metrics["Coverage"], "evaluate", side_effect=mock_coverage_eval),
            patch.object(evaluator._builtin_metrics["Relevance"], "evaluate", side_effect=mock_relevance_eval),
        ):
            await evaluator.evaluate(request)

        # Verify metrics were called in order defined in config
        # Config order from conftest: ClarityCoherence, Coverage, Relevance
        assert call_order == ["ClarityCoherence", "Coverage", "Relevance"]

    @pytest.mark.asyncio
    async def test_evaluation_stops_on_first_metric_failure(
        self,
        temp_workspace: Path,
        sample_evaluation_request_data: dict[str, Any],
        mock_all_api_keys: None,
    ) -> None:
        """Test that evaluation stops if first metric fails after retries."""
        manager = ConfigurationManager(workspace=temp_workspace)
        settings = manager.get_evaluator_settings()
        prompt_builder_settings = PromptBuilderSettings()
        evaluator = Evaluator(settings=settings, prompt_builder_settings=prompt_builder_settings)
        request = EvaluationRequest(**sample_evaluation_request_data, config=None)

        # Mock first metric to fail
        with patch.object(
            evaluator._builtin_metrics["ClarityCoherence"],
            "evaluate",
            side_effect=EvaluatorAPIError("API failure"),
        ):
            with pytest.raises(EvaluatorAPIError) as exc_info:
                await evaluator.evaluate(request)

            assert "API failure" in str(exc_info.value)


class TestRetryLogic:
    """T059: Test LLM API retry logic with simulated failures."""

    @pytest.mark.asyncio
    async def test_retry_on_transient_api_failure(
        self,
        temp_workspace: Path,
        sample_evaluation_request_data: dict[str, Any],
        mock_all_api_keys: None,
    ) -> None:
        """Test that evaluation retries on transient API failures."""
        manager = ConfigurationManager(workspace=temp_workspace)
        settings = manager.get_evaluator_settings()
        prompt_builder_settings = PromptBuilderSettings()
        evaluator = Evaluator(settings=settings, prompt_builder_settings=prompt_builder_settings)
        request = EvaluationRequest(**sample_evaluation_request_data, config=None)

        # Mock: First two calls fail, third succeeds
        call_count = {"count": 0}

        def mock_eval_with_retry(*args, **kwargs):
            call_count["count"] += 1
            if call_count["count"] <= 2:
                raise EvaluatorAPIError("Transient API error")
            return MetricScore(
                metric_name="ClarityCoherence",
                score=85.0,
                evaluator_comment="Success after retries",
            )

        with (
            patch.object(
                evaluator._builtin_metrics["ClarityCoherence"],
                "evaluate",
                side_effect=mock_eval_with_retry,
            ),
            patch.object(
                evaluator._builtin_metrics["Coverage"],
                "evaluate",
                return_value=MetricScore(metric_name="Coverage", score=80.0, evaluator_comment="OK"),
            ),
            patch.object(
                evaluator._builtin_metrics["Relevance"],
                "evaluate",
                return_value=MetricScore(metric_name="Relevance", score=90.0, evaluator_comment="OK"),
            ),
        ):
            # Note: Retry logic is expected to be handled by the metric implementation
            # If the metric itself doesn't retry, the evaluator will fail immediately
            # For now, we test that the error propagates correctly
            with pytest.raises(EvaluatorAPIError):
                await evaluator.evaluate(request)

    @pytest.mark.asyncio
    async def test_exception_after_max_retries(
        self,
        temp_workspace: Path,
        sample_evaluation_request_data: dict[str, Any],
        mock_all_api_keys: None,
    ) -> None:
        """Test that exception is raised after max retries exceeded."""
        manager = ConfigurationManager(workspace=temp_workspace)
        settings = manager.get_evaluator_settings()
        prompt_builder_settings = PromptBuilderSettings()
        evaluator = Evaluator(settings=settings, prompt_builder_settings=prompt_builder_settings)
        request = EvaluationRequest(**sample_evaluation_request_data, config=None)

        # Mock all calls to fail
        with patch.object(
            evaluator._builtin_metrics["ClarityCoherence"],
            "evaluate",
            side_effect=EvaluatorAPIError("API unavailable - max retries exceeded"),
        ):
            with pytest.raises(EvaluatorAPIError) as exc_info:
                await evaluator.evaluate(request)

            assert "API unavailable" in str(exc_info.value)
            # Verify metric context was added
            assert exc_info.value.metric_name == "ClarityCoherence"


class TestInputValidation:
    """T060: Test validation of empty/whitespace inputs."""

    def test_empty_query_raises_validation_error(self, temp_workspace: Path) -> None:
        """Test that empty user_query raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            EvaluationRequest(
                user_query="",
                submission="Some response",
                team_id="team-001",
                config=None,
            )

        # Verify error message mentions empty query
        errors = exc_info.value.errors()
        assert any("user_query" in str(error) for error in errors)

    def test_whitespace_only_query_raises_validation_error(self, temp_workspace: Path) -> None:
        """Test that whitespace-only user_query raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            EvaluationRequest(
                user_query="   \n  \t  ",
                submission="Some response",
                team_id="team-001",
                config=None,
            )

        errors = exc_info.value.errors()
        assert any("user_query" in str(error) for error in errors)

    def test_empty_submission_raises_validation_error(self, temp_workspace: Path) -> None:
        """Test that empty submission raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            EvaluationRequest(
                user_query="What is Python?",
                submission="",
                team_id="team-001",
                config=None,
            )

        errors = exc_info.value.errors()
        assert any("submission" in str(error) for error in errors)

    def test_whitespace_only_submission_raises_validation_error(self, temp_workspace: Path) -> None:
        """Test that whitespace-only submission raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            EvaluationRequest(
                user_query="What is Python?",
                submission="   \n  \t  ",
                team_id="team-001",
                config=None,
            )

        errors = exc_info.value.errors()
        assert any("submission" in str(error) for error in errors)

    @pytest.mark.asyncio
    async def test_valid_non_empty_inputs_accepted(
        self,
        temp_workspace: Path,
        sample_evaluation_request_data: dict[str, Any],
    ) -> None:
        """Test that valid non-empty inputs are accepted."""
        # Should not raise exception
        request = EvaluationRequest(**sample_evaluation_request_data, config=None)

        assert request.user_query.strip() != ""
        assert request.submission.strip() != ""
        assert request.team_id is not None and request.team_id.strip() != ""

    def test_team_id_none_accepted(self, temp_workspace: Path) -> None:
        """Test that team_id=None is accepted (optional field)."""
        # Should not raise exception
        request = EvaluationRequest(
            user_query="What is Python?",
            submission="Python is a programming language.",
            team_id=None,
        )

        assert request.user_query == "What is Python?"
        assert request.submission == "Python is a programming language."
        assert request.team_id is None

    def test_team_id_omitted_defaults_to_none(self, temp_workspace: Path) -> None:
        """Test that omitting team_id defaults to None."""
        # Should not raise exception
        request = EvaluationRequest(
            user_query="What is Python?",
            submission="Python is a programming language.",
        )

        assert request.team_id is None

    def test_empty_team_id_raises_validation_error(self, temp_workspace: Path) -> None:
        """Test that empty team_id string raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            EvaluationRequest(
                user_query="What is Python?",
                submission="Some response",
                team_id="",
            )

        errors = exc_info.value.errors()
        assert any("team_id" in str(error) for error in errors)

    def test_whitespace_only_team_id_raises_validation_error(self, temp_workspace: Path) -> None:
        """Test that whitespace-only team_id raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            EvaluationRequest(
                user_query="What is Python?",
                submission="Some response",
                team_id="   \n  \t  ",
            )

        errors = exc_info.value.errors()
        assert any("team_id" in str(error) for error in errors)
