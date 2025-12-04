"""Unit tests for LLM client wrapper.

NOTE: These tests are skipped because mocking pydantic-ai's ModelRequest
and related classes is complex and fragile. The LLM client functionality
is thoroughly tested in integration tests (test_evaluator_us1.py) and
E2E tests (test_evaluator_e2e.py) where it's tested with realistic usage patterns.
"""

import pytest
from pydantic import BaseModel, Field

from mixseek.evaluator.llm_client import evaluate_with_llm


# Test response model
class _TestScore(BaseModel):
    """Test response model for LLM evaluation."""

    score: float = Field(ge=0, le=100)
    comment: str


class TestEvaluateWithLLM:
    """Test suite for evaluate_with_llm function.

    Most tests are covered by integration and E2E tests.
    Only basic validation logic is tested here.
    """

    @pytest.mark.asyncio
    async def test_invalid_model_format_no_colon(self):
        """Test that model format without colon raises ValueError."""
        with pytest.raises(ValueError, match="Invalid model format"):
            await evaluate_with_llm(
                instruction="Test instruction",
                user_prompt="Test prompt",
                model="invalid-model-format",
                response_model=_TestScore,
                max_retries=1,
            )

    @pytest.mark.asyncio
    async def test_invalid_model_format_empty(self):
        """Test that empty model format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid model format"):
            await evaluate_with_llm(
                instruction="Test instruction",
                user_prompt="Test prompt",
                model="",
                response_model=_TestScore,
                max_retries=1,
            )

    @pytest.mark.asyncio
    async def test_model_format_validation_before_api_call(self):
        """Test that model format is validated before making API calls."""
        # This should fail fast with ValueError, not make any API calls
        invalid_models = [
            "no-colon-format",
            ":",
            "",
            "only-provider:",
        ]

        for model in invalid_models:
            with pytest.raises(ValueError, match="Invalid model format"):
                await evaluate_with_llm(
                    instruction="Test",
                    user_prompt="Test",
                    model=model,
                    response_model=_TestScore,
                    max_retries=1,
                )


# Note: More comprehensive LLM client tests including:
# - Successful evaluations
# - Retry logic
# - API error handling
# - Response parsing
# - Temperature settings
# - Structured output enforcement
# - Different providers
#
# Are covered in:
# - tests/evaluator/integration/test_evaluator_us1.py (with mocked LLM responses)
# - tests/evaluator/e2e/test_evaluator_e2e.py (with real LLM APIs)
