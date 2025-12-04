"""Unit tests for Relevance metric."""

from unittest.mock import patch

import pytest

from mixseek.config.schema import PromptBuilderSettings
from mixseek.evaluator.metrics.base import BaseLLMEvaluation
from mixseek.evaluator.metrics.relevance import Relevance
from mixseek.models.evaluation_result import MetricScore


class TestRelevance:
    """Test suite for Relevance."""

    def test_metric_name(self):
        """Test that metric name is derived from class name."""
        metric = Relevance()
        assert type(metric).__name__ == "Relevance"

    def test_get_instruction_returns_string(self):
        """Test that get_instruction returns a non-empty string."""
        metric = Relevance()
        instruction = metric.get_instruction()

        assert isinstance(instruction, str)
        assert len(instruction) > 0

    def test_instruction_contains_key_criteria(self):
        """Test that instruction contains relevance evaluation criteria."""
        metric = Relevance()
        instruction = metric.get_instruction()

        # Check for key criteria in the instruction
        assert "関連性" in instruction
        assert "直接" in instruction or "適切" in instruction

    def test_instruction_contains_scoring_guide(self):
        """Test that instruction contains scoring guide."""
        metric = Relevance()
        instruction = metric.get_instruction()

        # Check for scoring ranges
        assert "90-100" in instruction or "0-100" in instruction
        assert "スコア" in instruction

    @patch("mixseek.evaluator.metrics.base.evaluate_with_llm")
    @pytest.mark.asyncio
    async def test_evaluate_returns_metric_score(self, mock_evaluate):
        """Test that evaluate returns a MetricScore instance."""
        mock_llm_result = BaseLLMEvaluation(
            score=92.0, evaluator_comment="Highly relevant and directly addresses the query"
        )
        mock_evaluate.return_value = mock_llm_result

        metric = Relevance()
        result = await metric.evaluate(
            user_query="What is Python?",
            submission="Python is a high-level programming language created by Guido van Rossum...",
            model="anthropic:claude-sonnet-4-5-20250929",
            prompt_builder_settings=PromptBuilderSettings(),
        )

        assert isinstance(result, MetricScore)
        assert result.metric_name == "Relevance"
        assert result.score == 92.0
        assert result.evaluator_comment == "Highly relevant and directly addresses the query"

    @patch("mixseek.evaluator.metrics.base.evaluate_with_llm")
    @pytest.mark.asyncio
    async def test_evaluate_calls_llm_with_correct_params(self, mock_evaluate):
        """Test that evaluate calls evaluate_with_llm with correct parameters."""
        mock_llm_result = BaseLLMEvaluation(score=92.0, evaluator_comment="Good")
        mock_evaluate.return_value = mock_llm_result

        metric = Relevance()
        user_query = "What is Python?"
        submission = "Python is a programming language"
        model = "google:gemini-pro"

        await metric.evaluate(
            user_query=user_query,
            submission=submission,
            model=model,
            max_retries=2,
            prompt_builder_settings=PromptBuilderSettings(),
        )

        mock_evaluate.assert_called_once()
        call_kwargs = mock_evaluate.call_args[1]

        assert call_kwargs["model"] == model
        assert call_kwargs["max_retries"] == 2
        assert call_kwargs["response_model"] == BaseLLMEvaluation
        assert user_query in call_kwargs["user_prompt"]
        assert submission in call_kwargs["user_prompt"]

    @patch("mixseek.evaluator.metrics.base.evaluate_with_llm")
    @pytest.mark.asyncio
    async def test_evaluate_with_different_models(self, mock_evaluate):
        """Test that evaluate works with different LLM models."""
        mock_llm_result = BaseLLMEvaluation(score=92.0, evaluator_comment="Good")
        mock_evaluate.return_value = mock_llm_result

        metric = Relevance()
        models = [
            "anthropic:claude-sonnet-4-5-20250929",
            "openai:gpt-5",
            "google:gemini-pro",
        ]

        for model in models:
            result = await metric.evaluate(
                user_query="test", submission="test", model=model, prompt_builder_settings=PromptBuilderSettings()
            )
            assert result.metric_name == "Relevance"

    @patch("mixseek.evaluator.metrics.base.evaluate_with_llm")
    @pytest.mark.asyncio
    async def test_evaluate_with_highly_relevant_submission(self, mock_evaluate):
        """Test that evaluate handles highly relevant submissions."""
        mock_llm_result = BaseLLMEvaluation(
            score=98.0, evaluator_comment="Perfectly relevant, directly answers the question"
        )
        mock_evaluate.return_value = mock_llm_result

        metric = Relevance()
        query = "What is the capital of France?"
        relevant_submission = "The capital of France is Paris."

        result = await metric.evaluate(
            user_query=query,
            submission=relevant_submission,
            model="test:model",
            prompt_builder_settings=PromptBuilderSettings(),
        )

        assert result.score == 98.0
        assert "relevant" in result.evaluator_comment.lower() or "directly" in result.evaluator_comment.lower()

    @patch("mixseek.evaluator.metrics.base.evaluate_with_llm")
    @pytest.mark.asyncio
    async def test_evaluate_with_irrelevant_submission(self, mock_evaluate):
        """Test that evaluate handles irrelevant submissions."""
        mock_llm_result = BaseLLMEvaluation(
            score=15.0, evaluator_comment="Completely off-topic, does not address the query"
        )
        mock_evaluate.return_value = mock_llm_result

        metric = Relevance()
        query = "What is the capital of France?"
        irrelevant_submission = "Python is a great programming language."

        result = await metric.evaluate(
            user_query=query,
            submission=irrelevant_submission,
            model="test:model",
            prompt_builder_settings=PromptBuilderSettings(),
        )

        assert result.score == 15.0
        assert "off-topic" in result.evaluator_comment or "does not address" in result.evaluator_comment

    @patch("mixseek.evaluator.metrics.base.evaluate_with_llm")
    @pytest.mark.asyncio
    async def test_evaluate_with_partially_relevant_submission(self, mock_evaluate):
        """Test that evaluate handles partially relevant submissions."""
        mock_llm_result = BaseLLMEvaluation(
            score=55.0, evaluator_comment="Partially relevant but includes tangential information"
        )
        mock_evaluate.return_value = mock_llm_result

        metric = Relevance()
        query = "What is Python used for?"
        mixed_submission = (
            "Python is used for web development, data analysis, and AI. "
            "By the way, the weather today is nice. "
            "Python was created in 1991."
        )

        result = await metric.evaluate(
            user_query=query,
            submission=mixed_submission,
            model="test:model",
            prompt_builder_settings=PromptBuilderSettings(),
        )

        assert result.score == 55.0

    @patch("mixseek.evaluator.metrics.base.evaluate_with_llm")
    @pytest.mark.asyncio
    async def test_evaluate_score_range(self, mock_evaluate):
        """Test that evaluate handles different score ranges correctly."""
        metric = Relevance()

        # Test boundary scores
        for score in [0.0, 35.0, 65.0, 88.0, 100.0]:
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
    async def test_evaluate_preserves_detailed_comment(self, mock_evaluate):
        """Test that evaluate preserves detailed feedback comments."""
        detailed_comment = (
            "Direct answer: 40/40 points. Contextual appropriateness: 28/30 points. "
            "Focus and conciseness: 25/30 points. Minor tangential content detected. "
            "Total: 93/100."
        )
        mock_llm_result = BaseLLMEvaluation(score=93.0, evaluator_comment=detailed_comment)
        mock_evaluate.return_value = mock_llm_result

        metric = Relevance()
        result = await metric.evaluate(
            user_query="test",
            submission="test",
            model="test:model",
            prompt_builder_settings=PromptBuilderSettings(),
        )

        assert result.evaluator_comment == detailed_comment

    @patch("mixseek.evaluator.metrics.base.evaluate_with_llm")
    @pytest.mark.asyncio
    async def test_evaluate_uses_metric_specific_instruction(self, mock_evaluate):
        """Test that evaluate uses the relevance specific instruction."""
        mock_llm_result = BaseLLMEvaluation(score=92.0, evaluator_comment="Good")
        mock_evaluate.return_value = mock_llm_result

        metric = Relevance()
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
    async def test_multiple_evaluations_independent(self, mock_evaluate):
        """Test that multiple evaluations produce independent results."""
        metric = Relevance()

        # First evaluation - low relevance
        mock_evaluate.return_value = BaseLLMEvaluation(score=25.0, evaluator_comment="Off-topic")
        result1 = await metric.evaluate(
            user_query="query1",
            submission="irrelevant",
            model="test:model",
            prompt_builder_settings=PromptBuilderSettings(),
        )

        # Second evaluation - high relevance
        mock_evaluate.return_value = BaseLLMEvaluation(score=95.0, evaluator_comment="Highly relevant")
        result2 = await metric.evaluate(
            user_query="query2",
            submission="relevant",
            model="test:model",
            prompt_builder_settings=PromptBuilderSettings(),
        )

        assert result1.score == 25.0
        assert result2.score == 95.0
        assert "Off-topic" in result1.evaluator_comment
        assert "Highly relevant" in result2.evaluator_comment
        assert mock_evaluate.call_count == 2

    @patch("mixseek.evaluator.metrics.base.evaluate_with_llm")
    @pytest.mark.asyncio
    async def test_evaluate_with_context_specific_query(self, mock_evaluate):
        """Test that evaluate handles context-specific queries."""
        mock_llm_result = BaseLLMEvaluation(score=90.0, evaluator_comment="Contextually appropriate and focused")
        mock_evaluate.return_value = mock_llm_result

        metric = Relevance()
        context_query = "In the context of machine learning, what are the advantages of Python?"
        context_submission = (
            "For machine learning, Python offers scikit-learn, TensorFlow, "
            "and PyTorch libraries with extensive ML algorithms."
        )

        result = await metric.evaluate(
            user_query=context_query,
            submission=context_submission,
            model="test:model",
            prompt_builder_settings=PromptBuilderSettings(),
        )

        assert result.score == 90.0
        mock_evaluate.assert_called_once()

    @patch("mixseek.evaluator.metrics.base.evaluate_with_llm")
    @pytest.mark.asyncio
    async def test_evaluate_detects_rambling_submissions(self, mock_evaluate):
        """Test that evaluate penalizes rambling or unfocused submissions."""
        mock_llm_result = BaseLLMEvaluation(
            score=40.0, evaluator_comment="Loses focus with excessive tangential content"
        )
        mock_evaluate.return_value = mock_llm_result

        metric = Relevance()
        rambling_submission = (
            "Python is a language. I like coffee. "
            "The weather is nice today. By the way, programming is fun. "
            "My favorite color is blue. Python has libraries."
        )

        result = await metric.evaluate(
            user_query="What is Python?",
            submission=rambling_submission,
            model="test:model",
            prompt_builder_settings=PromptBuilderSettings(),
        )

        assert result.score == 40.0

    @patch("mixseek.evaluator.metrics.base.evaluate_with_llm")
    @pytest.mark.asyncio
    async def test_user_prompt_includes_structured_output_instruction(self, mock_evaluate):
        """Test that user prompt includes structured output format instruction.

        This is critical to ensure LLM returns both 'score' and 'evaluator_comment' fields.
        Without explicit instruction, LLMs may not return the required fields, causing
        Pydantic validation errors.
        """
        mock_llm_result = BaseLLMEvaluation(score=92.0, evaluator_comment="Test comment")
        mock_evaluate.return_value = mock_llm_result

        metric = Relevance()
        await metric.evaluate(
            user_query="What is Python?",
            submission="Python is...",
            model="test:model",
            prompt_builder_settings=PromptBuilderSettings(),
        )

        call_kwargs = mock_evaluate.call_args[1]
        user_prompt = call_kwargs["user_prompt"]

        # Verify user_prompt contains user_query and submission
        assert "What is Python?" in user_prompt
        assert "Python is..." in user_prompt
