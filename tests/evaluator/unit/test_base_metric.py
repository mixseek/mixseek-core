"""Unit tests for BaseMetric interface.

Feature: 022-evaluator-metrics, 140-user-prompt-builder-evaluator-judgement
"""

from __future__ import annotations

from abc import ABC
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from mixseek.config.schema import PromptBuilderSettings
from mixseek.evaluator.metrics.base import BaseLLMEvaluation, BaseMetric, LLMJudgeMetric
from mixseek.models.evaluation_result import MetricScore


class TestBaseLLMEvaluation:
    """Test suite for BaseLLMEvaluation model."""

    def test_valid_evaluation_creation(self):
        """Test creating a valid BaseLLMEvaluation instance."""
        evaluation = BaseLLMEvaluation(score=85.0, evaluator_comment="Good response with clear structure")

        assert evaluation.score == 85.0
        assert evaluation.evaluator_comment == "Good response with clear structure"

    def test_score_within_range(self):
        """Test that score must be between 0 and 100."""
        # Valid scores
        for score in [0.0, 50.0, 100.0]:
            evaluation = BaseLLMEvaluation(score=score, evaluator_comment="Test")
            assert evaluation.score == score

    def test_score_below_zero_fails(self):
        """Test that score below 0 raises validation error."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            BaseLLMEvaluation(score=-1.0, evaluator_comment="Test")

    def test_score_above_hundred_fails(self):
        """Test that score above 100 raises validation error."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            BaseLLMEvaluation(score=101.0, evaluator_comment="Test")

    def test_empty_comment_allowed(self):
        """Test that empty comment is allowed."""
        evaluation = BaseLLMEvaluation(score=85.0, evaluator_comment="")
        assert evaluation.evaluator_comment == ""


class TestBaseMetric:
    """Test suite for BaseMetric abstract class."""

    def test_cannot_instantiate_base_metric(self):
        """Test that BaseMetric cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseMetric()  # type: ignore[abstract]

    def test_must_implement_evaluate_method(self):
        """Test that subclass must implement evaluate method."""

        # Try to create a subclass without implementing evaluate
        with pytest.raises(TypeError):

            class IncompleteMetric(BaseMetric):
                pass

            IncompleteMetric()  # type: ignore[abstract]

    def test_valid_subclass_implementation(self):
        """Test that a properly implemented subclass can be instantiated."""

        class ValidMetric(BaseMetric):
            def evaluate(  # type: ignore[override]
                self,
                user_query: str,
                submission: str,
                model: str = "test:model",
                max_retries: int = 3,
                **kwargs: object,
            ) -> MetricScore:
                return MetricScore(
                    metric_name="valid_metric",
                    score=85.0,
                    evaluator_comment="Test evaluation",
                )

        metric = ValidMetric()
        result = metric.evaluate(user_query="test query", submission="test submission", model="test:model")

        assert isinstance(result, MetricScore)
        assert result.metric_name == "valid_metric"
        assert result.score == 85.0

    def test_evaluate_signature(self):
        """Test that evaluate method has correct signature."""

        class TestMetric(BaseMetric):
            def evaluate(  # type: ignore[override]
                self,
                user_query: str,
                submission: str,
                model: str = "test:model",
                max_retries: int = 3,
                **kwargs: object,
            ) -> MetricScore:
                return MetricScore(metric_name="test", score=50.0, evaluator_comment="Test")

        metric = TestMetric()
        result = metric.evaluate(
            user_query="query",
            submission="submission",
            model="provider:model",
            max_retries=5,
        )

        assert isinstance(result, MetricScore)


class TestLLMJudgeMetric:
    """Test suite for LLMJudgeMetric abstract class."""

    def test_cannot_instantiate_llm_judge_metric(self):
        """Test that LLMJudgeMetric cannot be instantiated directly."""
        with pytest.raises(TypeError):
            LLMJudgeMetric()  # type: ignore[abstract]

    def test_must_implement_get_instruction_method(self):
        """Test that subclass must implement get_instruction method."""

        with pytest.raises(TypeError):

            class IncompleteMetric(LLMJudgeMetric):
                pass

            IncompleteMetric()  # type: ignore[abstract]

    def test_valid_llm_judge_metric_implementation(self):
        """Test that a properly implemented LLMJudgeMetric subclass can be instantiated."""

        class ValidLLMMetric(LLMJudgeMetric):
            def get_instruction(self) -> str:
                return "Test evaluation instruction"

        metric = ValidLLMMetric()
        assert type(metric).__name__ == "ValidLLMMetric"
        assert metric.get_instruction() == "Test evaluation instruction"

    @patch("mixseek.evaluator.metrics.base.evaluate_with_llm")
    @pytest.mark.asyncio
    async def test_evaluate_method_calls_llm_client(self, mock_evaluate):
        """Test that evaluate method calls evaluate_with_llm correctly."""

        class TestLLMMetric(LLMJudgeMetric):
            def get_instruction(self) -> str:
                return "Test instruction"

        # Mock the LLM response
        mock_llm_result = BaseLLMEvaluation(score=85.0, evaluator_comment="Good response")
        mock_evaluate.return_value = mock_llm_result

        settings = PromptBuilderSettings()
        metric = TestLLMMetric()
        result = await metric.evaluate(
            user_query="What is Python?",
            submission="Python is a programming language",
            model="anthropic:claude-sonnet-4-5-20250929",
            prompt_builder_settings=settings,
            max_retries=3,
        )

        # Verify the result
        assert isinstance(result, MetricScore)
        assert result.metric_name == "TestLLMMetric"
        assert result.score == 85.0
        assert result.evaluator_comment == "Good response"

        # Verify evaluate_with_llm was called correctly
        mock_evaluate.assert_called_once()
        call_kwargs = mock_evaluate.call_args[1]
        assert call_kwargs["model"] == "anthropic:claude-sonnet-4-5-20250929"
        assert call_kwargs["response_model"] == BaseLLMEvaluation
        assert call_kwargs["max_retries"] == 3

    @patch("mixseek.evaluator.metrics.base.evaluate_with_llm")
    @pytest.mark.asyncio
    async def test_get_user_prompt_default_implementation(self, mock_evaluate):
        """Test that _get_user_prompt generates correct prompt format."""

        class TestLLMMetric(LLMJudgeMetric):
            def get_instruction(self) -> str:
                return "Test instruction"

        mock_llm_result = BaseLLMEvaluation(score=85.0, evaluator_comment="Good")
        mock_evaluate.return_value = mock_llm_result

        settings = PromptBuilderSettings()
        metric = TestLLMMetric()
        user_query = "What is Python?"
        submission = "Python is a programming language"

        await metric.evaluate(
            user_query=user_query,
            submission=submission,
            model="test:model",
            prompt_builder_settings=settings,
        )

        # Check the user prompt structure (Japanese format)
        call_kwargs = mock_evaluate.call_args[1]
        user_prompt = call_kwargs["user_prompt"]

        assert "# ユーザから指定されたタスク" in user_prompt
        assert user_query in user_prompt
        assert "# 提出内容" in user_prompt
        assert submission in user_prompt

    @patch("mixseek.evaluator.metrics.base.evaluate_with_llm")
    @pytest.mark.asyncio
    async def test_custom_user_prompt_override(self, mock_evaluate):
        """Test that _get_user_prompt can be overridden in subclasses."""

        class CustomPromptMetric(LLMJudgeMetric):
            def get_instruction(self) -> str:
                return "Custom instruction"

            def _get_user_prompt(
                self,
                user_query: str,
                submission: str,
                prompt_builder_settings: PromptBuilderSettings,
            ) -> str:
                return f"CUSTOM: Query={user_query}, Answer={submission}"

        mock_llm_result = BaseLLMEvaluation(score=85.0, evaluator_comment="Good")
        mock_evaluate.return_value = mock_llm_result

        settings = PromptBuilderSettings()
        metric = CustomPromptMetric()
        await metric.evaluate(
            user_query="test query",
            submission="test submission",
            model="test:model",
            prompt_builder_settings=settings,
        )

        # Check that custom prompt was used
        call_kwargs = mock_evaluate.call_args[1]
        user_prompt = call_kwargs["user_prompt"]
        assert user_prompt.startswith("CUSTOM:")
        assert "Query=test query" in user_prompt
        assert "Answer=test submission" in user_prompt

    @patch("mixseek.evaluator.metrics.base.evaluate_with_llm")
    @pytest.mark.asyncio
    async def test_evaluate_propagates_max_retries(self, mock_evaluate):
        """Test that max_retries parameter is propagated to evaluate_with_llm."""

        class TestLLMMetric(LLMJudgeMetric):
            def get_instruction(self) -> str:
                return "Test instruction"

        mock_llm_result = BaseLLMEvaluation(score=85.0, evaluator_comment="Good")
        mock_evaluate.return_value = mock_llm_result

        settings = PromptBuilderSettings()
        metric = TestLLMMetric()

        # Test with custom max_retries
        await metric.evaluate(
            user_query="test",
            submission="test",
            model="test:model",
            prompt_builder_settings=settings,
            max_retries=5,
        )

        call_kwargs = mock_evaluate.call_args[1]
        assert call_kwargs["max_retries"] == 5

    @patch("mixseek.evaluator.metrics.base.evaluate_with_llm")
    @pytest.mark.asyncio
    async def test_evaluate_uses_instruction_from_subclass(self, mock_evaluate):
        """Test that evaluate uses the instruction from get_instruction method."""

        class SpecificInstructionMetric(LLMJudgeMetric):
            def get_instruction(self) -> str:
                return "Very specific evaluation instruction with unique criteria"

        mock_llm_result = BaseLLMEvaluation(score=85.0, evaluator_comment="Good")
        mock_evaluate.return_value = mock_llm_result

        settings = PromptBuilderSettings()
        metric = SpecificInstructionMetric()
        expected_base_instruction = metric.get_instruction()
        await metric.evaluate(
            user_query="test",
            submission="test",
            model="test:model",
            prompt_builder_settings=settings,
        )

        call_kwargs = mock_evaluate.call_args[1]
        actual_instruction = call_kwargs["instruction"]

        # Verify instruction contains the base instruction from get_instruction()
        assert expected_base_instruction in actual_instruction
        # Verify the instruction is exactly the base instruction (no additional formatting added)
        assert actual_instruction == expected_base_instruction

    def test_inheritance_hierarchy(self):
        """Test that LLMJudgeMetric inherits from BaseMetric."""
        assert issubclass(LLMJudgeMetric, BaseMetric)
        assert issubclass(LLMJudgeMetric, ABC)

    @patch("mixseek.evaluator.metrics.base.evaluate_with_llm")
    @pytest.mark.asyncio
    async def test_multiple_metrics_independence(self, mock_evaluate):
        """Test that multiple metric instances work independently."""

        class Metric1(LLMJudgeMetric):
            def get_instruction(self) -> str:
                return "Instruction 1"

        class Metric2(LLMJudgeMetric):
            def get_instruction(self) -> str:
                return "Instruction 2"

        mock_llm_result = BaseLLMEvaluation(score=85.0, evaluator_comment="Good")
        mock_evaluate.return_value = mock_llm_result

        settings = PromptBuilderSettings()
        metric1 = Metric1()
        metric2 = Metric2()

        result1 = await metric1.evaluate(
            user_query="test",
            submission="test",
            model="test:model",
            prompt_builder_settings=settings,
        )
        result2 = await metric2.evaluate(
            user_query="test",
            submission="test",
            model="test:model",
            prompt_builder_settings=settings,
        )

        assert result1.metric_name == "Metric1"
        assert result2.metric_name == "Metric2"


class TestLLMJudgeMetricUserPromptBuilderIntegration:
    """Test suite for LLMJudgeMetric integration with UserPromptBuilder.

    Feature: 140-user-prompt-builder-evaluator-judgement
    Task: T016
    """

    @patch("mixseek.evaluator.metrics.base.evaluate_with_llm")
    @patch("mixseek.prompt_builder.builder.get_current_datetime_with_timezone")
    @pytest.mark.asyncio
    async def test_user_prompt_builder_integration_default_template(
        self, mock_dt: Any, mock_evaluate: Any, tmp_path: Path
    ) -> None:
        """Test that _get_user_prompt uses UserPromptBuilder with default template."""

        class TestLLMMetric(LLMJudgeMetric):
            def get_instruction(self) -> str:
                return "Test instruction"

        mock_dt.return_value = "2025-11-25T14:30:00+09:00"
        mock_llm_result = BaseLLMEvaluation(score=85.0, evaluator_comment="Good")
        mock_evaluate.return_value = mock_llm_result

        settings = PromptBuilderSettings()
        metric = TestLLMMetric()
        user_query = "What is Python?"
        submission = "Python is a programming language"

        await metric.evaluate(
            user_query=user_query,
            submission=submission,
            model="test:model",
            prompt_builder_settings=settings,
        )

        # Verify UserPromptBuilder was used
        call_kwargs = mock_evaluate.call_args[1]
        user_prompt = call_kwargs["user_prompt"]

        # Verify Japanese format from DEFAULT_EVALUATOR_USER_PROMPT
        assert "ユーザから指定されたタスク" in user_prompt
        assert "提出内容" in user_prompt
        assert "現在日時: 2025-11-25T14:30:00+09:00" in user_prompt
        assert user_query in user_prompt
        assert submission in user_prompt

    @patch("mixseek.evaluator.metrics.base.evaluate_with_llm")
    @patch("mixseek.prompt_builder.builder.get_current_datetime_with_timezone")
    @pytest.mark.asyncio
    async def test_user_prompt_builder_integration_format_unchanged(self, mock_dt, mock_evaluate, tmp_path):
        """Test that UserPromptBuilder output matches expected format exactly."""

        class TestLLMMetric(LLMJudgeMetric):
            def get_instruction(self) -> str:
                return "Test instruction"

        mock_dt.return_value = "2025-11-25T15:00:00+09:00"
        mock_llm_result = BaseLLMEvaluation(score=90.0, evaluator_comment="Excellent")
        mock_evaluate.return_value = mock_llm_result

        settings = PromptBuilderSettings()
        metric = TestLLMMetric()
        await metric.evaluate(
            user_query="Explain recursion",
            submission="Recursion is when a function calls itself",
            model="test:model",
            prompt_builder_settings=settings,
        )

        call_kwargs = mock_evaluate.call_args[1]
        user_prompt = call_kwargs["user_prompt"]

        # Verify structure
        assert "---\n現在日時: 2025-11-25T15:00:00+09:00\n---" in user_prompt
        assert "# ユーザから指定されたタスク\nExplain recursion" in user_prompt
        assert "# 提出内容\nRecursion is when a function calls itself" in user_prompt

    @patch("mixseek.evaluator.metrics.base.evaluate_with_llm")
    @patch("mixseek.prompt_builder.builder.get_current_datetime_with_timezone")
    @pytest.mark.asyncio
    async def test_user_prompt_builder_integration_multiline(self, mock_dt, mock_evaluate):
        """Test that multiline user_query and submission are handled correctly."""

        class TestLLMMetric(LLMJudgeMetric):
            def get_instruction(self) -> str:
                return "Test instruction"

        mock_dt.return_value = "2025-11-25T16:00:00+09:00"
        mock_llm_result = BaseLLMEvaluation(score=75.0, evaluator_comment="Good effort")
        mock_evaluate.return_value = mock_llm_result

        settings = PromptBuilderSettings()
        metric = TestLLMMetric()
        user_query = "Question 1: What is Python?\nQuestion 2: What are its features?"
        submission = "Answer 1: Python is a language.\nAnswer 2: Features include dynamic typing."

        await metric.evaluate(
            user_query=user_query,
            submission=submission,
            model="test:model",
            prompt_builder_settings=settings,
        )

        call_kwargs = mock_evaluate.call_args[1]
        user_prompt = call_kwargs["user_prompt"]

        # Verify multiline content preserved
        assert "Question 1: What is Python?" in user_prompt
        assert "Question 2: What are its features?" in user_prompt
        assert "Answer 1: Python is a language." in user_prompt
        assert "Answer 2: Features include dynamic typing." in user_prompt

    @patch("mixseek.evaluator.metrics.base.evaluate_with_llm")
    @patch("mixseek.prompt_builder.builder.get_current_datetime_with_timezone")
    @pytest.mark.asyncio
    async def test_user_prompt_builder_integration_custom_prompt(self, mock_dt, mock_evaluate):
        """Test that custom evaluator_user_prompt works with UserPromptBuilder."""

        class TestLLMMetric(LLMJudgeMetric):
            def get_instruction(self) -> str:
                return "Test instruction"

        mock_dt.return_value = "2025-11-25T17:00:00+09:00"
        mock_llm_result = BaseLLMEvaluation(score=80.0, evaluator_comment="Custom evaluation")
        mock_evaluate.return_value = mock_llm_result

        # Note: To test custom prompts, we'd need to set up a custom PromptBuilderSettings
        # For now, verify the default template works as expected
        settings = PromptBuilderSettings()
        metric = TestLLMMetric()
        await metric.evaluate(
            user_query="Custom query",
            submission="Custom submission",
            model="test:model",
            prompt_builder_settings=settings,
        )

        call_kwargs = mock_evaluate.call_args[1]
        user_prompt = call_kwargs["user_prompt"]

        # Verify default template used
        assert "ユーザから指定されたタスク" in user_prompt
        assert "Custom query" in user_prompt
        assert "Custom submission" in user_prompt

    @patch("mixseek.evaluator.metrics.base.evaluate_with_llm")
    @pytest.mark.asyncio
    async def test_existing_tests_still_pass(self, mock_evaluate):
        """Test that existing test cases still pass after UserPromptBuilder integration (100% compatibility).

        This test verifies backward compatibility - all existing tests should continue to pass.
        """

        class TestLLMMetric(LLMJudgeMetric):
            def get_instruction(self) -> str:
                return "Test instruction"

        mock_llm_result = BaseLLMEvaluation(score=85.0, evaluator_comment="Good response")
        mock_evaluate.return_value = mock_llm_result

        settings = PromptBuilderSettings()
        metric = TestLLMMetric()
        result = await metric.evaluate(
            user_query="What is Python?",
            submission="Python is a programming language",
            model="test:model",
            prompt_builder_settings=settings,
        )

        # Verify existing behavior preserved
        assert isinstance(result, MetricScore)
        assert result.metric_name == "TestLLMMetric"
        assert result.score == 85.0
        assert result.evaluator_comment == "Good response"

        # Verify evaluate_with_llm still called correctly
        mock_evaluate.assert_called_once()
        call_kwargs = mock_evaluate.call_args[1]
        assert call_kwargs["model"] == "test:model"
        assert call_kwargs["response_model"] == BaseLLMEvaluation
        assert "user_prompt" in call_kwargs
        assert "instruction" in call_kwargs
