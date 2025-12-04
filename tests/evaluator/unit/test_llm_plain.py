"""Unit tests for LLMPlain metric."""

from unittest.mock import patch

import pytest

from mixseek.config.schema import PromptBuilderSettings
from mixseek.evaluator.metrics.base import BaseLLMEvaluation
from mixseek.evaluator.metrics.llm_plain import LLMPlain
from mixseek.models.evaluation_result import MetricScore


class TestLLMPlainMetric:
    """Test suite for LLMPlain."""

    def test_metric_name(self):
        """Test that metric name is derived from class name."""
        metric = LLMPlain()
        assert type(metric).__name__ == "LLMPlain"

    def test_get_instruction_returns_string(self):
        """Test that get_instruction returns a non-empty string."""
        metric = LLMPlain()
        instruction = metric.get_instruction()

        assert isinstance(instruction, str)
        assert len(instruction) > 0

    @patch("mixseek.evaluator.metrics.base.evaluate_with_llm")
    @pytest.mark.asyncio
    async def test_evaluate_returns_metric_score(self, mock_evaluate):
        """Test that evaluate returns a MetricScore instance."""
        mock_llm_result = BaseLLMEvaluation(score=85.0, evaluator_comment="Good quality response")
        mock_evaluate.return_value = mock_llm_result

        metric = LLMPlain()
        result = await metric.evaluate(
            user_query="What is Python?",
            submission="Python is a high-level programming language...",
            model="anthropic:claude-sonnet-4-5-20250929",
            prompt_builder_settings=PromptBuilderSettings(),
        )

        assert isinstance(result, MetricScore)
        assert result.metric_name == "LLMPlain"
        assert result.score == 85.0
        assert result.evaluator_comment == "Good quality response"

    @patch("mixseek.evaluator.metrics.base.evaluate_with_llm")
    @pytest.mark.asyncio
    async def test_evaluate_calls_llm_with_correct_params(self, mock_evaluate):
        """Test that evaluate calls evaluate_with_llm with correct parameters."""
        mock_llm_result = BaseLLMEvaluation(score=85.0, evaluator_comment="Good")
        mock_evaluate.return_value = mock_llm_result

        metric = LLMPlain()
        user_query = "What is Python?"
        submission = "Python is a programming language"
        model = "anthropic:claude-sonnet-4-5-20250929"

        await metric.evaluate(
            user_query=user_query,
            submission=submission,
            model=model,
            max_retries=5,
            prompt_builder_settings=PromptBuilderSettings(),
        )

        mock_evaluate.assert_called_once()
        call_kwargs = mock_evaluate.call_args[1]

        assert call_kwargs["model"] == model
        assert call_kwargs["max_retries"] == 5
        assert call_kwargs["response_model"] == BaseLLMEvaluation
        assert user_query in call_kwargs["user_prompt"]
        assert submission in call_kwargs["user_prompt"]

    @patch("mixseek.evaluator.metrics.base.evaluate_with_llm")
    @pytest.mark.asyncio
    async def test_evaluate_with_custom_system_instruction(self, mock_evaluate):
        """Test that evaluate uses custom system_instruction when provided."""
        mock_llm_result = BaseLLMEvaluation(score=85.0, evaluator_comment="Good")
        mock_evaluate.return_value = mock_llm_result

        metric = LLMPlain()
        custom_instruction = "Evaluate the technical accuracy of the response."

        await metric.evaluate(
            user_query="What is Python?",
            submission="Python is a programming language",
            model="anthropic:claude-sonnet-4-5-20250929",
            prompt_builder_settings=PromptBuilderSettings(),
            system_instruction=custom_instruction,
        )

        call_kwargs = mock_evaluate.call_args[1]
        actual_instruction = call_kwargs["instruction"]

        # Verify instruction is exactly the custom system_instruction (no additional formatting added)
        assert actual_instruction == custom_instruction

    @patch("mixseek.evaluator.metrics.base.evaluate_with_llm")
    @pytest.mark.asyncio
    async def test_evaluate_uses_default_instruction_when_not_overridden(self, mock_evaluate):
        """Test that evaluate uses default instruction when system_instruction is not provided."""
        mock_llm_result = BaseLLMEvaluation(score=85.0, evaluator_comment="Good")
        mock_evaluate.return_value = mock_llm_result

        metric = LLMPlain()
        expected_base_instruction = metric.get_instruction()

        await metric.evaluate(
            user_query="test",
            submission="test",
            model="test:model",
            prompt_builder_settings=PromptBuilderSettings(),
        )

        call_kwargs = mock_evaluate.call_args[1]
        actual_instruction = call_kwargs["instruction"]

        # Verify instruction contains the base instruction from get_instruction()
        assert expected_base_instruction in actual_instruction
        # Verify instruction contains the output format section
        assert "出力形式:" in actual_instruction
        assert "evaluator_comment" in actual_instruction

    @patch("mixseek.evaluator.metrics.base.evaluate_with_llm")
    @pytest.mark.asyncio
    async def test_evaluate_with_different_models(self, mock_evaluate):
        """Test that evaluate works with different LLM models."""
        mock_llm_result = BaseLLMEvaluation(score=85.0, evaluator_comment="Good")
        mock_evaluate.return_value = mock_llm_result

        metric = LLMPlain()
        models = [
            "anthropic:claude-sonnet-4-5-20250929",
            "openai:gpt-5",
            "google:gemini-pro",
        ]

        for model in models:
            result = await metric.evaluate(
                user_query="test", submission="test", model=model, prompt_builder_settings=PromptBuilderSettings()
            )
            assert result.metric_name == "LLMPlain"

    @patch("mixseek.evaluator.metrics.base.evaluate_with_llm")
    @pytest.mark.asyncio
    async def test_evaluate_with_long_text(self, mock_evaluate):
        """Test that evaluate handles long query and submission."""
        mock_llm_result = BaseLLMEvaluation(score=90.0, evaluator_comment="Excellent")
        mock_evaluate.return_value = mock_llm_result

        metric = LLMPlain()
        long_query = "What are the benefits of Python?" * 100
        long_submission = "Python offers many benefits..." * 100

        result = await metric.evaluate(
            user_query=long_query,
            submission=long_submission,
            model="test:model",
            prompt_builder_settings=PromptBuilderSettings(),
        )

        assert isinstance(result, MetricScore)
        mock_evaluate.assert_called_once()

    @patch("mixseek.evaluator.metrics.base.evaluate_with_llm")
    @pytest.mark.asyncio
    async def test_evaluate_score_range(self, mock_evaluate):
        """Test that evaluate handles different score ranges correctly."""
        metric = LLMPlain()

        # Test boundary scores
        for score in [0.0, 25.0, 50.0, 75.0, 100.0]:
            mock_llm_result = BaseLLMEvaluation(score=score, evaluator_comment="Test")
            mock_evaluate.return_value = mock_llm_result

            result = await metric.evaluate(
                user_query="test",
                submission="test",
                model="test:model",
                prompt_builder_settings=PromptBuilderSettings(),
            )

            assert result.score == score
            assert 0.0 <= result.score <= 100.0

    @patch("mixseek.evaluator.metrics.base.evaluate_with_llm")
    @pytest.mark.asyncio
    async def test_evaluate_with_empty_comment(self, mock_evaluate):
        """Test that evaluate handles empty evaluator comments."""
        mock_llm_result = BaseLLMEvaluation(score=85.0, evaluator_comment="")
        mock_evaluate.return_value = mock_llm_result

        metric = LLMPlain()
        result = await metric.evaluate(
            user_query="test",
            submission="test",
            model="test:model",
            prompt_builder_settings=PromptBuilderSettings(),
        )

        assert result.evaluator_comment == ""

    @patch("mixseek.evaluator.metrics.base.evaluate_with_llm")
    @pytest.mark.asyncio
    async def test_evaluate_preserves_comment(self, mock_evaluate):
        """Test that evaluate preserves the full comment from LLM."""
        long_comment = "This is a very detailed comment about quality. " * 10
        mock_llm_result = BaseLLMEvaluation(score=85.0, evaluator_comment=long_comment)
        mock_evaluate.return_value = mock_llm_result

        metric = LLMPlain()
        result = await metric.evaluate(
            user_query="test",
            submission="test",
            model="test:model",
            prompt_builder_settings=PromptBuilderSettings(),
        )

        # Strip trailing whitespace for comparison since some formatting may vary
        assert result.evaluator_comment.strip() == long_comment.strip()

    @patch("mixseek.evaluator.metrics.base.evaluate_with_llm")
    @pytest.mark.asyncio
    async def test_multiple_evaluations_independent(self, mock_evaluate):
        """Test that multiple evaluations produce independent results."""
        metric = LLMPlain()

        # First evaluation
        mock_evaluate.return_value = BaseLLMEvaluation(score=80.0, evaluator_comment="First")
        result1 = await metric.evaluate(
            user_query="query1",
            submission="submission1",
            model="test:model",
            prompt_builder_settings=PromptBuilderSettings(),
        )

        # Second evaluation
        mock_evaluate.return_value = BaseLLMEvaluation(score=90.0, evaluator_comment="Second")
        result2 = await metric.evaluate(
            user_query="query2",
            submission="submission2",
            model="test:model",
            prompt_builder_settings=PromptBuilderSettings(),
        )

        assert result1.score == 80.0
        assert result2.score == 90.0
        assert result1.evaluator_comment == "First"
        assert result2.evaluator_comment == "Second"
        assert mock_evaluate.call_count == 2

    @patch("mixseek.evaluator.metrics.base.evaluate_with_llm")
    @pytest.mark.asyncio
    async def test_evaluate_with_llm_parameters(self, mock_evaluate):
        """Test that evaluate passes all LLM parameters correctly."""
        mock_llm_result = BaseLLMEvaluation(score=85.0, evaluator_comment="Good")
        mock_evaluate.return_value = mock_llm_result

        metric = LLMPlain()

        await metric.evaluate(
            user_query="test",
            submission="test",
            model="test:model",
            prompt_builder_settings=PromptBuilderSettings(),
            temperature=0.5,
            max_tokens=1000,
            max_retries=5,
        )

        call_kwargs = mock_evaluate.call_args[1]
        assert call_kwargs["temperature"] == 0.5
        assert call_kwargs["max_tokens"] == 1000
        assert call_kwargs["max_retries"] == 5
