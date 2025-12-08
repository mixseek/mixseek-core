"""Integration tests for mixseek evaluate CLI command.

Tests the complete CLI integration with logging and Logfire options.
"""

from pathlib import Path
from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from mixseek.cli.main import app
from mixseek.models.evaluation_result import EvaluationResult, MetricScore

runner = CliRunner()


class TestEvaluateCommand:
    """Integration tests for mixseek evaluate command."""

    @patch("mixseek.cli.commands.evaluate.evaluate_content")
    def test_basic_evaluation_success(self, mock_evaluate: AsyncMock, tmp_path: Path) -> None:
        """Test basic evaluation with required arguments."""
        mock_result = EvaluationResult(
            metrics=[
                MetricScore(metric_name="clarity_coherence", score=80.0, evaluator_comment="Clear"),
                MetricScore(metric_name="coverage", score=70.0, evaluator_comment="Good coverage"),
                MetricScore(metric_name="relevance", score=90.0, evaluator_comment="Relevant"),
            ],
            overall_score=80.0,
        )
        mock_evaluate.return_value = mock_result

        result = runner.invoke(
            app,
            [
                "evaluate",
                "Pythonとは？",
                "Pythonは言語です",
                "--workspace",
                str(tmp_path),
            ],
        )

        assert result.exit_code == 0
        assert mock_evaluate.called

    def test_logfire_flags_mutually_exclusive(self) -> None:
        """Test that multiple Logfire flags cannot be specified together."""
        result = runner.invoke(
            app,
            [
                "evaluate",
                "test query",
                "test submission",
                "--logfire",
                "--logfire-metadata",
            ],
        )

        assert result.exit_code == 1
        assert "Only one of --logfire" in result.stdout

    def test_logfire_http_and_metadata_mutually_exclusive(self) -> None:
        """Test that --logfire-http and --logfire-metadata are mutually exclusive."""
        result = runner.invoke(
            app,
            [
                "evaluate",
                "test query",
                "test submission",
                "--logfire-http",
                "--logfire-metadata",
            ],
        )

        assert result.exit_code == 1
        assert "Only one of --logfire" in result.stdout

    def test_all_three_logfire_flags_error(self) -> None:
        """Test that all three Logfire flags cannot be specified together."""
        result = runner.invoke(
            app,
            [
                "evaluate",
                "test query",
                "test submission",
                "--logfire",
                "--logfire-metadata",
                "--logfire-http",
            ],
        )

        assert result.exit_code == 1
        assert "Only one of --logfire" in result.stdout

    @patch("mixseek.cli.commands.evaluate.setup_logging_from_cli")
    @patch("mixseek.cli.commands.evaluate.setup_logfire_from_cli")
    @patch("mixseek.cli.commands.evaluate.evaluate_content")
    def test_logging_setup_called_with_correct_params(
        self, mock_evaluate: AsyncMock, mock_setup_logfire: AsyncMock, mock_setup_logging: AsyncMock, tmp_path: Path
    ) -> None:
        """Test that logging setup functions are called with correct parameters."""
        mock_result = EvaluationResult(
            metrics=[
                MetricScore(metric_name="clarity_coherence", score=80.0, evaluator_comment="Clear"),
                MetricScore(metric_name="coverage", score=70.0, evaluator_comment="Good coverage"),
                MetricScore(metric_name="relevance", score=90.0, evaluator_comment="Relevant"),
            ],
            overall_score=80.0,
        )
        mock_evaluate.return_value = mock_result

        result = runner.invoke(
            app,
            [
                "evaluate",
                "test query",
                "test submission",
                "--log-level",
                "debug",
                "--no-log-console",
                "--logfire",
                "--workspace",
                str(tmp_path),
            ],
        )

        assert result.exit_code == 0
        # Verify setup_logging_from_cli was called
        assert mock_setup_logging.called
        # Verify setup_logfire_from_cli was called
        assert mock_setup_logfire.called

    @patch("mixseek.cli.commands.evaluate.evaluate_content")
    def test_workspace_option(self, mock_evaluate: AsyncMock, tmp_path: Path) -> None:
        """Test that --workspace option is accepted."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        mock_result = EvaluationResult(
            metrics=[
                MetricScore(metric_name="clarity_coherence", score=80.0, evaluator_comment="Clear"),
                MetricScore(metric_name="coverage", score=70.0, evaluator_comment="Good coverage"),
                MetricScore(metric_name="relevance", score=90.0, evaluator_comment="Relevant"),
            ],
            overall_score=80.0,
        )
        mock_evaluate.return_value = mock_result

        result = runner.invoke(
            app,
            [
                "evaluate",
                "test query",
                "test submission",
                "--workspace",
                str(workspace),
            ],
        )

        assert result.exit_code == 0

    @patch("mixseek.cli.commands.evaluate.evaluate_content")
    def test_verbose_option(self, mock_evaluate: AsyncMock, tmp_path: Path) -> None:
        """Test that -v short flag works (from VERBOSE_OPTION)."""
        mock_result = EvaluationResult(
            metrics=[
                MetricScore(metric_name="clarity_coherence", score=80.0, evaluator_comment="Clear"),
                MetricScore(metric_name="coverage", score=70.0, evaluator_comment="Good coverage"),
                MetricScore(metric_name="relevance", score=90.0, evaluator_comment="Relevant"),
            ],
            overall_score=80.0,
        )
        mock_evaluate.return_value = mock_result

        result = runner.invoke(
            app,
            [
                "evaluate",
                "test query",
                "test submission",
                "-v",
                "--workspace",
                str(tmp_path),
            ],
        )

        assert result.exit_code == 0

    @patch("mixseek.cli.commands.evaluate.evaluate_content")
    def test_json_output_format(self, mock_evaluate: AsyncMock, tmp_path: Path) -> None:
        """Test JSON output format."""
        mock_result = EvaluationResult(
            metrics=[
                MetricScore(metric_name="clarity_coherence", score=80.0, evaluator_comment="Clear"),
                MetricScore(metric_name="coverage", score=70.0, evaluator_comment="Good coverage"),
                MetricScore(metric_name="relevance", score=90.0, evaluator_comment="Relevant"),
            ],
            overall_score=80.0,
        )
        mock_evaluate.return_value = mock_result

        result = runner.invoke(
            app,
            [
                "evaluate",
                "test query",
                "test submission",
                "--output-format",
                "json",
                "--workspace",
                str(tmp_path),
            ],
        )

        assert result.exit_code == 0
        # JSON output should contain expected fields
        assert "metrics" in result.stdout
        assert "overall_score" in result.stdout

    @patch("mixseek.cli.commands.evaluate.evaluate_content")
    def test_evaluation_failure_returns_error_code(self, mock_evaluate: AsyncMock) -> None:
        """Test that evaluation failure results in error exit code."""
        # Mock evaluate_content to return None (error case)
        mock_evaluate.return_value = None

        result = runner.invoke(
            app,
            [
                "evaluate",
                "test query",
                "test submission",
            ],
        )

        assert result.exit_code == 1

    @patch("mixseek.cli.commands.evaluate.evaluate_content")
    def test_custom_config_option(self, mock_evaluate: AsyncMock, tmp_path: Path) -> None:
        """Test --config option with custom evaluator config."""
        config_file = tmp_path / "evaluator.toml"
        config_file.write_text("""
[evaluator]
model = "google-gla:gemini-2.5-flash-lite"
temperature = 0.5
max_tokens = 2048
""")

        mock_result = EvaluationResult(
            metrics=[
                MetricScore(metric_name="clarity_coherence", score=80.0, evaluator_comment="Clear"),
                MetricScore(metric_name="coverage", score=70.0, evaluator_comment="Good coverage"),
                MetricScore(metric_name="relevance", score=90.0, evaluator_comment="Relevant"),
            ],
            overall_score=80.0,
        )
        mock_evaluate.return_value = mock_result

        result = runner.invoke(
            app,
            [
                "evaluate",
                "test query",
                "test submission",
                "--config",
                str(config_file),
                "--workspace",
                str(tmp_path),
            ],
        )

        assert result.exit_code == 0
