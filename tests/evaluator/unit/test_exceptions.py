"""Unit tests for evaluator custom exceptions."""

import pytest

from mixseek.evaluator.exceptions import (
    EvaluatorAPIError,
    EvaluatorConfigError,
    ModelFormatError,
    WeightValidationError,
)


class TestEvaluatorConfigError:
    """Test EvaluatorConfigError exception."""

    def test_raise_evaluator_config_error(self) -> None:
        """Test raising EvaluatorConfigError."""
        with pytest.raises(EvaluatorConfigError) as exc_info:
            raise EvaluatorConfigError("Invalid configuration")

        assert "Invalid configuration" in str(exc_info.value)

    def test_evaluator_config_error_is_value_error(self) -> None:
        """Test that EvaluatorConfigError inherits from ValueError."""
        assert issubclass(EvaluatorConfigError, ValueError)

    def test_evaluator_config_error_with_detailed_message(self) -> None:
        """Test EvaluatorConfigError with detailed message."""
        message = "Invalid configuration: weights must sum to 1.0, got 0.8"
        with pytest.raises(EvaluatorConfigError) as exc_info:
            raise EvaluatorConfigError(message)

        assert message in str(exc_info.value)


class TestWeightValidationError:
    """Test WeightValidationError exception."""

    def test_raise_weight_validation_error(self) -> None:
        """Test raising WeightValidationError."""
        with pytest.raises(WeightValidationError) as exc_info:
            raise WeightValidationError("Weights must sum to 1.0")

        assert "Weights must sum to 1.0" in str(exc_info.value)

    def test_weight_validation_error_inherits_from_config_error(self) -> None:
        """Test that WeightValidationError inherits from EvaluatorConfigError."""
        assert issubclass(WeightValidationError, EvaluatorConfigError)

    def test_weight_validation_error_with_details(self) -> None:
        """Test WeightValidationError with weight details."""
        message = "Metric weights must sum to 1.0, got 0.8. Current weights: clarity_coherence=0.4, relevance=0.4"
        with pytest.raises(WeightValidationError) as exc_info:
            raise WeightValidationError(message)

        error = str(exc_info.value)
        assert "0.8" in error
        assert "clarity_coherence=0.4" in error


class TestModelFormatError:
    """Test ModelFormatError exception."""

    def test_raise_model_format_error(self) -> None:
        """Test raising ModelFormatError."""
        with pytest.raises(ModelFormatError) as exc_info:
            raise ModelFormatError("Invalid model format")

        assert "Invalid model format" in str(exc_info.value)

    def test_model_format_error_inherits_from_config_error(self) -> None:
        """Test that ModelFormatError inherits from EvaluatorConfigError."""
        assert issubclass(ModelFormatError, EvaluatorConfigError)

    def test_model_format_error_with_details(self) -> None:
        """Test ModelFormatError with format details."""
        message = "Invalid model format: 'gpt-4'. Expected format: 'provider:model-name' (e.g., 'openai:gpt-5')"
        with pytest.raises(ModelFormatError) as exc_info:
            raise ModelFormatError(message)

        error = str(exc_info.value)
        assert "gpt-4" in error
        assert "provider:model-name" in error


class TestEvaluatorAPIError:
    """Test EvaluatorAPIError exception."""

    def test_raise_evaluator_api_error_basic(self) -> None:
        """Test raising EvaluatorAPIError with basic message."""
        with pytest.raises(EvaluatorAPIError) as exc_info:
            raise EvaluatorAPIError("API call failed")

        assert "API call failed" in str(exc_info.value)

    def test_evaluator_api_error_with_provider(self) -> None:
        """Test EvaluatorAPIError with provider information."""
        error = EvaluatorAPIError("API key invalid", provider="anthropic")

        assert error.provider == "anthropic"
        assert "anthropic" in str(error)

    def test_evaluator_api_error_with_metric_name(self) -> None:
        """Test EvaluatorAPIError with metric_name information."""
        error = EvaluatorAPIError("Evaluation failed", metric_name="clarity_coherence")

        assert error.metric_name == "clarity_coherence"
        assert "clarity_coherence" in str(error)

    def test_evaluator_api_error_with_retry_count(self) -> None:
        """Test EvaluatorAPIError with retry_count information."""
        error = EvaluatorAPIError("Failed after retries", retry_count=3)

        assert error.retry_count == 3
        assert "3" in str(error)

    def test_evaluator_api_error_with_all_attributes(self) -> None:
        """Test EvaluatorAPIError with all attributes."""
        error = EvaluatorAPIError(
            "Failed to evaluate clarity_coherence metric after 3 retries: API key invalid",
            provider="anthropic",
            metric_name="clarity_coherence",
            retry_count=3,
        )

        assert error.provider == "anthropic"
        assert error.metric_name == "clarity_coherence"
        assert error.retry_count == 3

        error_str = str(error)
        assert "API key invalid" in error_str
        assert "anthropic" in error_str
        assert "clarity_coherence" in error_str
        assert "3" in error_str

    def test_evaluator_api_error_str_format(self) -> None:
        """Test EvaluatorAPIError string formatting."""
        error = EvaluatorAPIError(
            "Test error",
            provider="openai",
            metric_name="coverage",
            retry_count=5,
        )

        error_str = str(error)
        # Should contain pipe-separated format
        assert "Provider:" in error_str or "openai" in error_str
        assert "Metric:" in error_str or "coverage" in error_str
        assert "Retries:" in error_str or "5" in error_str

    def test_evaluator_api_error_without_optional_fields(self) -> None:
        """Test EvaluatorAPIError without optional fields."""
        error = EvaluatorAPIError("Simple error message")

        assert error.provider is None
        assert error.metric_name is None
        assert error.retry_count is None
        assert "Simple error message" in str(error)

    def test_evaluator_api_error_is_exception(self) -> None:
        """Test that EvaluatorAPIError inherits from Exception."""
        assert issubclass(EvaluatorAPIError, Exception)

    def test_catch_evaluator_api_error(self) -> None:
        """Test catching EvaluatorAPIError."""
        try:
            raise EvaluatorAPIError("Test error", provider="anthropic")
        except EvaluatorAPIError as e:
            assert e.provider == "anthropic"
            assert "Test error" in str(e)
        else:
            pytest.fail("EvaluatorAPIError was not raised")


class TestExceptionInheritance:
    """Test exception inheritance hierarchy."""

    def test_config_error_hierarchy(self) -> None:
        """Test that config errors inherit correctly."""
        # WeightValidationError -> EvaluatorConfigError -> ValueError
        assert issubclass(WeightValidationError, EvaluatorConfigError)
        assert issubclass(WeightValidationError, ValueError)

        # ModelFormatError -> EvaluatorConfigError -> ValueError
        assert issubclass(ModelFormatError, EvaluatorConfigError)
        assert issubclass(ModelFormatError, ValueError)

    def test_api_error_separate_from_config_error(self) -> None:
        """Test that API error is separate from config errors."""
        # EvaluatorAPIError -> Exception (not ValueError)
        assert issubclass(EvaluatorAPIError, Exception)
        assert not issubclass(EvaluatorAPIError, ValueError)
        assert not issubclass(EvaluatorAPIError, EvaluatorConfigError)

    def test_catch_base_config_error(self) -> None:
        """Test catching derived errors with base EvaluatorConfigError."""
        # Should be able to catch WeightValidationError as EvaluatorConfigError
        try:
            raise WeightValidationError("Weight error")
        except EvaluatorConfigError as e:
            assert "Weight error" in str(e)
        else:
            pytest.fail("Expected EvaluatorConfigError")

        # Should be able to catch ModelFormatError as EvaluatorConfigError
        try:
            raise ModelFormatError("Model error")
        except EvaluatorConfigError as e:
            assert "Model error" in str(e)
        else:
            pytest.fail("Expected EvaluatorConfigError")
