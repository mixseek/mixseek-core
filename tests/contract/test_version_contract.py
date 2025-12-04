"""Contract tests for version display compliance."""

import re

from typer.testing import CliRunner

from mixseek.cli.main import app

runner = CliRunner()


class TestVersionDisplay:
    """Test version display compliance."""

    def test_mixseek_version_displays_number(self) -> None:
        """Test mixseek --version displays version number (PEP 440 compliant).

        Supports stable versions (0.1.0, 1.0.0) and pre-releases (0.1.0a1, 0.1.0b1, 0.1.0rc1).
        """
        result = runner.invoke(app, ["--version"])

        assert result.exit_code == 0
        # Check for PEP 440 version pattern (e.g., 0.1.0, 1.0.0, 0.1.0a1, 0.1.0b1, 0.1.0rc1)
        version_pattern = r"\d+\.\d+\.\d+((a|b|rc)\d+)?"
        assert re.search(version_pattern, result.stdout)

    def test_mixseek_version_exit_code_zero(self) -> None:
        """Test mixseek --version exits with code 0."""
        result = runner.invoke(app, ["--version"])

        assert result.exit_code == 0
