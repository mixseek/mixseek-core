"""Unit tests for common validation functions.

Article 3 (Test-First Imperative) compliance:
This test file is created BEFORE implementing validators_common.py.
"""

import pytest

from mixseek.config.validators_common import validate_model_format


class TestValidateModelFormat:
    """validate_model_format()のテスト（Article 3準拠：実装前にテスト作成）"""

    def test_valid_model_format_with_colon(self) -> None:
        """Test valid model format with colon separator"""
        # Valid formats
        assert validate_model_format("google-gla:gemini-2.5-flash-lite") == "google-gla:gemini-2.5-flash-lite"
        assert validate_model_format("openai:gpt-4o") == "openai:gpt-4o"
        assert validate_model_format("anthropic:claude-sonnet-4-5") == "anthropic:claude-sonnet-4-5"

    def test_invalid_model_format_without_colon(self) -> None:
        """Test invalid model format without colon separator"""
        with pytest.raises(ValueError) as exc_info:
            validate_model_format("gemini-2.5-flash-lite")

        error_msg = str(exc_info.value)
        assert "Invalid model format" in error_msg
        assert "provider:model-name" in error_msg

    def test_empty_string_rejected_by_default(self) -> None:
        """Test empty string is rejected when allow_empty=False (default)"""
        with pytest.raises(ValueError) as exc_info:
            validate_model_format("")

        error_msg = str(exc_info.value)
        assert "Invalid model format" in error_msg

    def test_empty_string_allowed_with_flag(self) -> None:
        """Test empty string is allowed when allow_empty=True"""
        result = validate_model_format("", allow_empty=True)
        assert result == ""

    def test_whitespace_only_rejected_by_default(self) -> None:
        """Test whitespace-only string is rejected"""
        with pytest.raises(ValueError):
            validate_model_format("   ")

    def test_whitespace_only_allowed_with_flag(self) -> None:
        """Test whitespace-only string is allowed when allow_empty=True"""
        result = validate_model_format("  ", allow_empty=True)
        assert result == "  "

    def test_model_format_with_multiple_colons(self) -> None:
        """Test model format with multiple colons (should be valid)"""
        # Some providers might use multiple colons in their model names
        assert validate_model_format("custom:provider:model:v1") == "custom:provider:model:v1"

    def test_model_format_preserves_original_value(self) -> None:
        """Test that validation preserves the original value"""
        original = "google-gla:gemini-2.5-flash-lite"
        result = validate_model_format(original)
        assert result is original or result == original

    @pytest.mark.parametrize(
        "invalid_format",
        [
            "gpt-4o",  # No colon
            "gemini",  # No colon
            "claude-sonnet-4-5",  # No colon
            "model_name",  # No colon, underscore
        ],
    )
    def test_invalid_formats_parametrized(self, invalid_format: str) -> None:
        """Test various invalid formats raise ValueError"""
        with pytest.raises(ValueError, match="Invalid model format"):
            validate_model_format(invalid_format)

    @pytest.mark.parametrize(
        "valid_format",
        [
            "google-gla:gemini-2.5-flash-lite",
            "openai:gpt-4o",
            "anthropic:claude-sonnet-4-5",
            "custom:my-model",
            "provider:model:version",  # Multiple colons
        ],
    )
    def test_valid_formats_parametrized(self, valid_format: str) -> None:
        """Test various valid formats pass validation"""
        result = validate_model_format(valid_format)
        assert result == valid_format
