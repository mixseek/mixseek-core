"""Unit tests for result formatters.

This test suite validates the formatting utilities for displaying
Member Agent results in various formats.
"""

import json
from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from mixseek.cli.formatters import ResultFormatter
from mixseek.models.member_agent import MemberAgentResult, ResultStatus


@pytest.fixture
def sample_success_result() -> MemberAgentResult:
    """Create a sample successful result."""
    return MemberAgentResult(
        status=ResultStatus.SUCCESS,
        content="This is a test response from the agent.",
        agent_name="test-agent",
        agent_type="plain",
        timestamp=datetime.now(UTC),
        execution_time_ms=1500,
        usage_info={"total_tokens": 150, "prompt_tokens": 50, "completion_tokens": 100},
        metadata={
            "model_id": "google-gla:gemini-2.5-flash-lite",
            "temperature": 0.2,
            "max_tokens": 2048,
            "additional_info": "test metadata",
        },
    )


@pytest.fixture
def sample_error_result() -> MemberAgentResult:
    """Create a sample error result."""
    return MemberAgentResult(
        status=ResultStatus.ERROR,
        content="",
        agent_name="test-agent",
        agent_type="code_execution",
        timestamp=datetime.now(UTC),
        execution_time_ms=500,
        error_message="Connection timeout occurred",
        error_code="TIMEOUT_ERROR",
        retry_count=3,
        max_retries_exceeded=True,
    )


@pytest.fixture
def sample_warning_result() -> MemberAgentResult:
    """Create a sample result with warning."""
    return MemberAgentResult(
        status=ResultStatus.SUCCESS,
        content="Task completed with minor issues.",
        agent_name="web-search-agent",
        agent_type="web_search",
        timestamp=datetime.now(UTC),
        execution_time_ms=2000,
        warning_message="Some search results may be incomplete",
    )


class TestResultFormatter:
    """Test ResultFormatter functionality."""

    def test_get_formatter_valid_formats(self) -> None:
        """Test getting formatter functions for valid format names."""
        # Test all valid formats
        valid_formats = ["structured", "json", "text", "csv"]

        for format_name in valid_formats:
            formatter = ResultFormatter.get_formatter(format_name)
            assert callable(formatter)

    def test_get_formatter_invalid_format(self) -> None:
        """Test getting formatter for invalid format name."""
        with pytest.raises(ValueError) as exc_info:
            ResultFormatter.get_formatter("invalid_format")

        assert "Unknown format 'invalid_format'" in str(exc_info.value)
        assert "Available formats:" in str(exc_info.value)

    def test_format_json_success(self, sample_success_result: MemberAgentResult) -> None:
        """Test JSON formatting for successful result."""
        with patch("typer.echo") as mock_echo:
            ResultFormatter.format_json(sample_success_result, 1500, verbose=True)

            # Verify typer.echo was called
            assert mock_echo.call_count == 1

            # Parse the JSON output
            json_output = mock_echo.call_args[0][0]
            data = json.loads(json_output)

            # Verify required fields
            assert data["status"] == "success"
            assert data["agent_name"] == "test-agent"
            assert data["agent_type"] == "plain"
            assert data["content"] == "This is a test response from the agent."
            assert data["execution_time_ms"] == 1500
            assert "timestamp" in data
            assert "usage_info" in data
            assert "metadata" in data

    def test_format_json_error(self, sample_error_result: MemberAgentResult) -> None:
        """Test JSON formatting for error result."""
        with patch("typer.echo") as mock_echo:
            ResultFormatter.format_json(sample_error_result, 500, verbose=False)

            json_output = mock_echo.call_args[0][0]
            data = json.loads(json_output)

            # Verify error-specific fields
            assert data["status"] == "error"
            assert data["error_message"] == "Connection timeout occurred"
            assert data["error_code"] == "TIMEOUT_ERROR"
            assert data["retry_count"] == 3
            assert data["max_retries_exceeded"] is True

    def test_format_json_warning(self, sample_warning_result: MemberAgentResult) -> None:
        """Test JSON formatting for result with warning."""
        with patch("typer.echo") as mock_echo:
            ResultFormatter.format_json(sample_warning_result, 2000)

            json_output = mock_echo.call_args[0][0]
            data = json.loads(json_output)

            # Verify warning field
            assert data["warning_message"] == "Some search results may be incomplete"

    def test_format_text_success(self, sample_success_result: MemberAgentResult) -> None:
        """Test text formatting for successful result."""
        with patch("typer.echo") as mock_echo:
            ResultFormatter.format_text(sample_success_result, 1500, verbose=True)

            # Should output just the content
            mock_echo.assert_called_once_with("This is a test response from the agent.")

    def test_format_text_error(self, sample_error_result: MemberAgentResult) -> None:
        """Test text formatting for error result."""
        with patch("typer.echo") as mock_echo:
            ResultFormatter.format_text(sample_error_result, 500, verbose=False)

            # Should output error message
            mock_echo.assert_called_once_with("Error: Connection timeout occurred")

    def test_format_text_no_content(self) -> None:
        """Test text formatting for result with no content."""
        result = MemberAgentResult(
            status=ResultStatus.SUCCESS, content="", agent_name="test-agent", agent_type="plain"
        )

        with patch("typer.echo") as mock_echo:
            ResultFormatter.format_text(result, 100)

            mock_echo.assert_called_once_with("(No content)")

    def test_format_structured_success(self, sample_success_result: MemberAgentResult) -> None:
        """Test structured formatting for successful result."""
        with patch("typer.echo") as mock_echo, patch("typer.secho") as mock_secho:
            ResultFormatter.format_structured(sample_success_result, 1500, verbose=True)

            # Should have multiple calls for structured output
            assert mock_echo.call_count > 5  # Multiple lines of output
            assert mock_secho.call_count > 3  # Colored output lines

    def test_format_structured_error(self, sample_error_result: MemberAgentResult) -> None:
        """Test structured formatting for error result."""
        with patch("typer.echo") as mock_echo, patch("typer.secho") as mock_secho:
            ResultFormatter.format_structured(sample_error_result, 500, verbose=False)

            # Should have structured output including error details
            assert mock_echo.call_count > 3
            assert mock_secho.call_count > 2

    def test_format_structured_verbose(self, sample_success_result: MemberAgentResult) -> None:
        """Test structured formatting with verbose output."""
        with patch("typer.echo") as mock_echo, patch("typer.secho") as mock_secho:
            ResultFormatter.format_structured(sample_success_result, 1500, verbose=True)

            # Verbose mode should have more output
            verbose_calls = mock_echo.call_count + mock_secho.call_count

            # Reset and test non-verbose
            mock_echo.reset_mock()
            mock_secho.reset_mock()

            ResultFormatter.format_structured(sample_success_result, 1500, verbose=False)
            non_verbose_calls = mock_echo.call_count + mock_secho.call_count

            # Verbose should have more calls
            assert verbose_calls > non_verbose_calls

    def test_format_csv_multiple_results(
        self, sample_success_result: MemberAgentResult, sample_error_result: MemberAgentResult
    ) -> None:
        """Test CSV formatting for multiple results."""
        results = [sample_success_result, sample_error_result]
        execution_times = [1500, 500]

        with patch("typer.echo") as mock_echo:
            ResultFormatter.format_csv(results, execution_times)

            # Should have header + 2 data rows = 3 calls
            assert mock_echo.call_count == 3

            # Check header
            header_call = mock_echo.call_args_list[0][0][0]
            assert "timestamp,agent_name,agent_type,status,execution_time_ms" in header_call

            # Check data rows contain expected values
            data_calls = [call[0][0] for call in mock_echo.call_args_list[1:]]
            assert any("test-agent" in call and "plain" in call and "success" in call for call in data_calls)
            assert any("test-agent" in call and "code_execution" in call and "error" in call for call in data_calls)

    def test_format_csv_empty_results(self) -> None:
        """Test CSV formatting with empty results list."""
        with patch("typer.echo") as mock_echo:
            ResultFormatter.format_csv([], [])

            # Should only output header
            mock_echo.assert_called_once()
            header_call = mock_echo.call_args[0][0]
            assert header_call.startswith("timestamp,agent_name")

    def test_formatter_error_handling(self, sample_success_result: MemberAgentResult) -> None:
        """Test that formatters handle edge cases gracefully."""
        # Test with result that has minimal data
        minimal_result = MemberAgentResult(
            status=ResultStatus.SUCCESS, content="Test", agent_name="minimal", agent_type="plain"
        )

        # All formatters should handle minimal result without error
        with patch("typer.echo"), patch("typer.secho"):
            ResultFormatter.format_structured(minimal_result, 100, False)
            ResultFormatter.format_json(minimal_result, 100, False)
            ResultFormatter.format_text(minimal_result, 100, False)

        # CSV formatter with single result
        with patch("typer.echo"):
            ResultFormatter.format_csv([minimal_result], [100])


class TestProgressFormatter:
    """Test ProgressFormatter functionality."""

    def test_show_spinner(self) -> None:
        """Test spinner display."""
        from mixseek.cli.formatters import ProgressFormatter

        with patch("typer.echo") as mock_echo:
            ProgressFormatter.show_spinner("Processing test")

            mock_echo.assert_called_once_with("Processing test...", nl=False)

    def test_show_progress_bar_partial(self) -> None:
        """Test progress bar with partial completion."""
        from mixseek.cli.formatters import ProgressFormatter

        with patch("typer.echo") as mock_echo:
            ProgressFormatter.show_progress_bar(3, 10, "Test Progress")

            # Should show progress without newline
            mock_echo.assert_called_once()
            call_args = mock_echo.call_args[0][0]
            assert "Test Progress:" in call_args
            assert "30%" in call_args
            assert "(3/10)" in call_args

    def test_show_progress_bar_complete(self) -> None:
        """Test progress bar at completion."""
        from mixseek.cli.formatters import ProgressFormatter

        with patch("typer.echo") as mock_echo:
            ProgressFormatter.show_progress_bar(10, 10, "Complete")

            # Should have 2 calls - progress line and newline
            assert mock_echo.call_count == 2

            # First call should show 100%
            progress_call = mock_echo.call_args_list[0][0][0]
            assert "100%" in progress_call
            assert "(10/10)" in progress_call

            # Second call should be newline only
            newline_call = mock_echo.call_args_list[1]
            assert newline_call[0] == ()  # No positional args for newline

    def test_show_progress_bar_zero_total(self) -> None:
        """Test progress bar with zero total (edge case)."""
        from mixseek.cli.formatters import ProgressFormatter

        with patch("typer.echo") as mock_echo:
            ProgressFormatter.show_progress_bar(0, 0, "Edge Case")

            # Should have calls (at least one for progress, maybe one for newline)
            assert mock_echo.call_count >= 1

            # Find the progress call (first call with content)
            progress_calls = [call for call in mock_echo.call_args_list if call[0]]
            if progress_calls:
                call_args = progress_calls[0][0][0]
                assert "100%" in call_args  # Should show 100% when total is 0
