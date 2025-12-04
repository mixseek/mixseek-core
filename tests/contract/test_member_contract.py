"""Contract tests for mixseek member CLI command.

Tests that the member command interface adheres to its documented contract
including all required options and arguments.
"""

import os

import pytest
from typer.testing import CliRunner

from mixseek.cli.main import app

runner = CliRunner()


class TestMemberCommandContract:
    """Contract tests for member command interface."""

    def test_command_exists(self) -> None:
        """Test that member command is registered."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "member" in result.stdout

    def test_requires_prompt_argument(self) -> None:
        """Test that prompt argument is required."""
        result = runner.invoke(app, ["member"])
        assert result.exit_code != 0

    @pytest.mark.skipif(os.getenv("GITHUB_ACTIONS") == "true", reason="CLI help format differs in CI environment")
    def test_supports_config_option(self) -> None:
        """Test that --config option is supported."""
        result = runner.invoke(app, ["member", "--help"])
        assert result.exit_code == 0
        assert "--config" in result.stdout

    @pytest.mark.skipif(os.getenv("GITHUB_ACTIONS") == "true", reason="CLI help format differs in CI environment")
    def test_supports_agent_option(self) -> None:
        """Test that --agent option is supported."""
        result = runner.invoke(app, ["member", "--help"])
        assert result.exit_code == 0
        assert "--agent" in result.stdout

    @pytest.mark.skipif(os.getenv("GITHUB_ACTIONS") == "true", reason="CLI help format differs in CI environment")
    def test_supports_verbose_option(self) -> None:
        """Test that --verbose option is supported."""
        result = runner.invoke(app, ["member", "--help"])
        assert result.exit_code == 0
        assert "--verbose" in result.stdout

    @pytest.mark.skipif(os.getenv("GITHUB_ACTIONS") == "true", reason="CLI help format differs in CI environment")
    def test_supports_format_option(self) -> None:
        """Test that --output-format option is supported."""
        result = runner.invoke(app, ["member", "--help"])
        assert result.exit_code == 0
        assert "--output-format" in result.stdout

    def test_command_description_mentions_development(self) -> None:
        """Test that command description mentions development/testing purpose."""
        result = runner.invoke(app, ["member", "--help"])
        assert result.exit_code == 0
        assert "development" in result.stdout.lower() or "testing" in result.stdout.lower()
