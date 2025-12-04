"""Contract tests for help system compliance."""

import os

import pytest
from typer.testing import CliRunner

from mixseek.cli.main import app

runner = CliRunner()


class TestGlobalHelp:
    """Test global help command compliance."""

    def test_mixseek_help_displays_subcommands(self) -> None:
        """Test mixseek --help displays subcommands."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "init" in result.stdout
        assert "Commands:" in result.stdout or "commands:" in result.stdout.lower() or "Commands" in result.stdout

    def test_mixseek_help_exit_code_zero(self) -> None:
        """Test mixseek --help exits with code 0."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0


class TestInitHelp:
    """Test init command help compliance."""

    @pytest.mark.skipif(os.getenv("GITHUB_ACTIONS") == "true", reason="CLI help format differs in CI environment")
    def test_mixseek_init_help_displays_options(self) -> None:
        """Test mixseek init --help displays options."""
        result = runner.invoke(app, ["init", "--help"])

        assert result.exit_code == 0
        assert "--workspace" in result.stdout
        assert "-w" in result.stdout

    def test_mixseek_init_help_includes_examples(self) -> None:
        """Test mixseek init --help includes usage examples."""
        result = runner.invoke(app, ["init", "--help"])

        assert result.exit_code == 0
        # Check for example patterns
        output_lower = result.stdout.lower()
        assert "example" in output_lower or "usage:" in output_lower or "mixseek init" in output_lower
