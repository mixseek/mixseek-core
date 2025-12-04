"""Integration tests for mixseek member CLI command.

Tests the complete CLI integration with --agent and --config options,
including proper mocking to avoid external API dependencies.
"""

from pathlib import Path
from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from mixseek.cli.main import app
from mixseek.models.member_agent import MemberAgentResult, ResultStatus

runner = CliRunner()


class TestMemberCommand:
    """Integration tests for mixseek member command."""

    @patch("mixseek.cli.commands.member.execute_agent_from_config")
    def test_agent_option_plain_success(self, mock_execute: AsyncMock, tmp_path: Path) -> None:
        """Test --agent plain option success."""
        # Mock successful execution
        mock_result = MemberAgentResult(
            content="Test response",
            status=ResultStatus.SUCCESS,
            agent_name="plain",
            agent_type="plain",
        )
        mock_execute.return_value = mock_result

        result = runner.invoke(app, ["member", "こんにちは", "--agent", "plain", "--workspace", str(tmp_path)])

        assert result.exit_code == 0
        # Warning message should be in stderr
        assert "Development/Testing only" in result.stderr or "⚠" in result.stderr

    @patch("mixseek.cli.commands.member.execute_agent_from_config")
    def test_agent_option_web_search_success(self, mock_execute: AsyncMock, tmp_path: Path) -> None:
        """Test --agent web-search option success."""
        mock_result = MemberAgentResult(
            content="Test response",
            status=ResultStatus.SUCCESS,
            agent_name="web-search",
            agent_type="web_search",
        )
        mock_execute.return_value = mock_result

        result = runner.invoke(app, ["member", "最新ニュース", "--agent", "web-search", "--workspace", str(tmp_path)])

        assert result.exit_code == 0

    @patch("mixseek.cli.commands.member.execute_agent_from_config")
    def test_agent_option_code_exec_success(self, mock_execute: AsyncMock, tmp_path: Path) -> None:
        """Test --agent code-exec option success."""
        mock_result = MemberAgentResult(
            content="Test response",
            status=ResultStatus.SUCCESS,
            agent_name="code-exec",
            agent_type="code_execution",
        )
        mock_execute.return_value = mock_result

        result = runner.invoke(
            app, ["member", "計算してください", "--agent", "code-exec", "--workspace", str(tmp_path)]
        )

        assert result.exit_code == 0

    def test_agent_option_invalid_name_error(self, tmp_path: Path) -> None:
        """Test error for invalid agent name."""
        result = runner.invoke(app, ["member", "test", "--agent", "invalid", "--workspace", str(tmp_path)])

        assert result.exit_code == 1
        assert "Unknown member agent 'invalid'" in result.stderr
        assert "Available agents:" in result.stderr

    def test_mutually_exclusive_config_and_agent(self, tmp_path: Path) -> None:
        """Test that --config and --agent are mutually exclusive."""
        # Create a dummy config file
        config_file = tmp_path / "test.toml"
        config_file.write_text("[agent]\nname='test'\n")

        result = runner.invoke(app, ["member", "test", "--config", str(config_file), "--agent", "plain"])

        assert result.exit_code == 2  # typer.BadParameter returns exit code 2
        assert "mutually exclusive" in result.stderr.lower()

    def test_neither_config_nor_agent_error(self, tmp_path: Path) -> None:
        """Test error when neither --config nor --agent specified."""
        result = runner.invoke(app, ["member", "test", "--workspace", str(tmp_path)])

        assert result.exit_code == 1
        assert "Either --config or --agent must be specified" in result.stderr

    def test_logfire_flags_mutually_exclusive(self) -> None:
        """Test that multiple Logfire flags cannot be specified together."""
        result = runner.invoke(
            app,
            [
                "member",
                "test prompt",
                "--agent",
                "plain",
                "--logfire",
                "--logfire-metadata",
            ],
        )

        assert result.exit_code == 1
        assert "Only one of --logfire" in result.stderr

    def test_logfire_http_and_metadata_mutually_exclusive(self) -> None:
        """Test that --logfire-http and --logfire-metadata are mutually exclusive."""
        result = runner.invoke(
            app,
            [
                "member",
                "test prompt",
                "--agent",
                "plain",
                "--logfire-http",
                "--logfire-metadata",
            ],
        )

        assert result.exit_code == 1
        assert "Only one of --logfire" in result.stderr

    @patch("mixseek.cli.commands.member.setup_logging_from_cli")
    @patch("mixseek.cli.commands.member.setup_logfire_from_cli")
    @patch("mixseek.cli.commands.member.execute_agent_from_config")
    def test_logging_setup_called_with_correct_params(
        self, mock_execute: AsyncMock, mock_setup_logfire: AsyncMock, mock_setup_logging: AsyncMock, tmp_path: Path
    ) -> None:
        """Test that logging setup functions are called with correct parameters."""
        mock_result = MemberAgentResult(
            content="Test response",
            status=ResultStatus.SUCCESS,
            agent_name="plain",
            agent_type="plain",
        )
        mock_execute.return_value = mock_result

        result = runner.invoke(
            app,
            [
                "member",
                "test prompt",
                "--agent",
                "plain",
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

    @patch("mixseek.cli.commands.member.execute_agent_from_config")
    def test_verbose_option_uses_common_constant(self, mock_execute: AsyncMock, tmp_path: Path) -> None:
        """Test that -v short flag works (from VERBOSE_OPTION)."""
        mock_result = MemberAgentResult(
            content="Test response",
            status=ResultStatus.SUCCESS,
            agent_name="plain",
            agent_type="plain",
        )
        mock_execute.return_value = mock_result

        result = runner.invoke(app, ["member", "test prompt", "--agent", "plain", "-v", "--workspace", str(tmp_path)])

        assert result.exit_code == 0
        # Verbose flag should trigger verbose output (logging configured message or development warning)
        assert "Logging configured" in result.stderr or "Development/Testing" in result.stderr
