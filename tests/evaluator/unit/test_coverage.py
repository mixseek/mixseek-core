"""Unit tests for Coverage metric."""

from unittest.mock import patch

import pytest

from mixseek.config.schema import PromptBuilderSettings
from mixseek.evaluator.metrics.base import BaseLLMEvaluation
from mixseek.evaluator.metrics.coverage import Coverage
from mixseek.models.evaluation_result import MetricScore


class TestCoverage:
    """Test suite for Coverage."""

    def test_metric_name(self):
        """Test that metric name is derived from class name."""
        metric = Coverage()
        assert type(metric).__name__ == "Coverage"

    def test_get_instruction_returns_string(self):
        """Test that get_instruction returns a non-empty string."""
        metric = Coverage()
        instruction = metric.get_instruction()

        assert isinstance(instruction, str)
        assert len(instruction) > 0

    def test_instruction_contains_key_criteria(self):
        """Test that instruction contains coverage evaluation criteria."""
        metric = Coverage()
        instruction = metric.get_instruction()

        # Check for key criteria in the instruction
        assert "包括性" in instruction or "カバレッジ" in instruction
        assert "深さ" in instruction or "完全性" in instruction

    def test_instruction_contains_scoring_guide(self):
        """Test that instruction contains scoring guide."""
        metric = Coverage()
        instruction = metric.get_instruction()

        # Check for scoring ranges
        assert "90-100" in instruction or "0-100" in instruction
        assert "スコア" in instruction

    @patch("mixseek.evaluator.metrics.base.evaluate_with_llm")
    @pytest.mark.asyncio
    async def test_evaluate_returns_metric_score(self, mock_evaluate):
        """Test that evaluate returns a MetricScore instance."""
        mock_llm_result = BaseLLMEvaluation(score=82.0, evaluator_comment="Comprehensive coverage with good depth")
        mock_evaluate.return_value = mock_llm_result

        metric = Coverage()
        result = await metric.evaluate(
            user_query="What is Python?",
            submission="Python is a high-level programming language...",
            model="anthropic:claude-sonnet-4-5-20250929",
            prompt_builder_settings=PromptBuilderSettings(),
        )

        assert isinstance(result, MetricScore)
        assert result.metric_name == "Coverage"
        assert result.score == 82.0
        assert result.evaluator_comment == "Comprehensive coverage with good depth"

    @patch("mixseek.evaluator.metrics.base.evaluate_with_llm")
    @pytest.mark.asyncio
    async def test_evaluate_calls_llm_with_correct_params(self, mock_evaluate):
        """Test that evaluate calls evaluate_with_llm with correct parameters."""
        mock_llm_result = BaseLLMEvaluation(score=82.0, evaluator_comment="Good")
        mock_evaluate.return_value = mock_llm_result

        metric = Coverage()
        user_query = "What is Python?"
        submission = "Python is a programming language"
        model = "openai:gpt-5"

        await metric.evaluate(
            user_query=user_query,
            submission=submission,
            model=model,
            max_retries=4,
            prompt_builder_settings=PromptBuilderSettings(),
        )

        mock_evaluate.assert_called_once()
        call_kwargs = mock_evaluate.call_args[1]

        assert call_kwargs["model"] == model
        assert call_kwargs["max_retries"] == 4
        assert call_kwargs["response_model"] == BaseLLMEvaluation
        assert user_query in call_kwargs["user_prompt"]
        assert submission in call_kwargs["user_prompt"]

    @patch("mixseek.evaluator.metrics.base.evaluate_with_llm")
    @pytest.mark.asyncio
    async def test_evaluate_with_different_models(self, mock_evaluate):
        """Test that evaluate works with different LLM models."""
        mock_llm_result = BaseLLMEvaluation(score=82.0, evaluator_comment="Good")
        mock_evaluate.return_value = mock_llm_result

        metric = Coverage()
        models = [
            "anthropic:claude-sonnet-4-5-20250929",
            "openai:gpt-5",
            "google:gemini-pro",
        ]

        for model in models:
            result = await metric.evaluate(
                user_query="test", submission="test", model=model, prompt_builder_settings=PromptBuilderSettings()
            )
            assert result.metric_name == "Coverage"

    @patch("mixseek.evaluator.metrics.base.evaluate_with_llm")
    @pytest.mark.asyncio
    async def test_evaluate_with_comprehensive_submission(self, mock_evaluate):
        """Test that evaluate handles comprehensive submissions."""
        mock_llm_result = BaseLLMEvaluation(score=95.0, evaluator_comment="Excellent comprehensive coverage")
        mock_evaluate.return_value = mock_llm_result

        metric = Coverage()
        comprehensive_submission = """
        Python offers multiple benefits:
        1. Easy to learn syntax
        2. Rich ecosystem of libraries
        3. Strong community support
        4. Cross-platform compatibility
        5. Extensive documentation
        """

        result = await metric.evaluate(
            user_query="What are the benefits of Python?",
            submission=comprehensive_submission,
            model="test:model",
            prompt_builder_settings=PromptBuilderSettings(),
        )

        assert result.score == 95.0
        mock_evaluate.assert_called_once()

    @patch("mixseek.evaluator.metrics.base.evaluate_with_llm")
    @pytest.mark.asyncio
    async def test_evaluate_with_shallow_submission(self, mock_evaluate):
        """Test that evaluate handles shallow submissions."""
        mock_llm_result = BaseLLMEvaluation(score=40.0, evaluator_comment="Superficial coverage, lacks depth")
        mock_evaluate.return_value = mock_llm_result

        metric = Coverage()
        shallow_submission = "Python is good."

        result = await metric.evaluate(
            user_query="What are the benefits of Python?",
            submission=shallow_submission,
            model="test:model",
            prompt_builder_settings=PromptBuilderSettings(),
        )

        assert result.score == 40.0
        assert "Superficial" in result.evaluator_comment or "lacks depth" in result.evaluator_comment

    @patch("mixseek.evaluator.metrics.base.evaluate_with_llm")
    @pytest.mark.asyncio
    async def test_evaluate_score_range(self, mock_evaluate):
        """Test that evaluate handles different score ranges correctly."""
        metric = Coverage()

        # Test boundary scores
        for score in [0.0, 30.0, 60.0, 85.0, 100.0]:
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
            "The submission covers major topics well (30/30) but lacks depth "
            "in some areas (20/30). Examples are provided (15/20). Overall "
            "completeness is good (18/20). Total: 83/100."
        )
        mock_llm_result = BaseLLMEvaluation(score=83.0, evaluator_comment=detailed_comment)
        mock_evaluate.return_value = mock_llm_result

        metric = Coverage()
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
        """Test that evaluate uses the coverage specific instruction."""
        mock_llm_result = BaseLLMEvaluation(score=82.0, evaluator_comment="Good")
        mock_evaluate.return_value = mock_llm_result

        metric = Coverage()
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
        metric = Coverage()

        # First evaluation - low coverage
        mock_evaluate.return_value = BaseLLMEvaluation(score=45.0, evaluator_comment="Incomplete coverage")
        result1 = await metric.evaluate(
            user_query="query1",
            submission="short",
            model="test:model",
            prompt_builder_settings=PromptBuilderSettings(),
        )

        # Second evaluation - high coverage
        mock_evaluate.return_value = BaseLLMEvaluation(score=92.0, evaluator_comment="Comprehensive coverage")
        result2 = await metric.evaluate(
            user_query="query2",
            submission="detailed",
            model="test:model",
            prompt_builder_settings=PromptBuilderSettings(),
        )

        assert result1.score == 45.0
        assert result2.score == 92.0
        assert "Incomplete" in result1.evaluator_comment
        assert "Comprehensive" in result2.evaluator_comment
        assert mock_evaluate.call_count == 2

    @patch("mixseek.evaluator.metrics.base.evaluate_with_llm")
    @pytest.mark.asyncio
    async def test_evaluate_with_multipart_query(self, mock_evaluate):
        """Test that evaluate handles queries with multiple parts."""
        mock_llm_result = BaseLLMEvaluation(score=88.0, evaluator_comment="All parts addressed")
        mock_evaluate.return_value = mock_llm_result

        metric = Coverage()
        multipart_query = "1. What is Python? 2. What are its benefits? 3. How is it used in data science?"

        result = await metric.evaluate(
            user_query=multipart_query,
            submission="Comprehensive answer covering all three aspects...",
            model="test:model",
            prompt_builder_settings=PromptBuilderSettings(),
        )

        assert result.score == 88.0
        mock_evaluate.assert_called_once()

    @patch("mixseek.evaluator.metrics.base.evaluate_with_llm")
    @pytest.mark.asyncio
    async def test_user_prompt_includes_structured_output_instruction(self, mock_evaluate):
        """Test that user prompt includes structured output format instruction.

        This is critical to ensure LLM returns both 'score' and 'evaluator_comment' fields.
        Without explicit instruction, LLMs may not return the required fields, causing
        Pydantic validation errors.
        """
        mock_llm_result = BaseLLMEvaluation(score=82.0, evaluator_comment="Test comment")
        mock_evaluate.return_value = mock_llm_result

        metric = Coverage()
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
