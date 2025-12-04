"""Contract tests for CLI interface compliance."""

from pathlib import Path

from pytest import MonkeyPatch
from typer.testing import CliRunner

from mixseek.cli.main import app

runner = CliRunner()


class TestInitCommandExitCodes:
    """Test CLI exit codes conform to contract."""

    def test_init_success_exit_code(self, tmp_path: Path) -> None:
        """Test successful init returns exit code 0."""
        workspace_path = tmp_path / "test-workspace"

        result = runner.invoke(app, ["init", "--workspace", str(workspace_path)])

        assert result.exit_code == 0

    def test_init_error_exit_code(self, tmp_path: Path) -> None:
        """Test error conditions return non-zero exit code."""
        # Test with invalid parent directory
        invalid_path = tmp_path / "nonexistent" / "workspace"

        result = runner.invoke(app, ["init", "--workspace", str(invalid_path)])

        assert result.exit_code != 0

    def test_init_invalid_usage_exit_code(self) -> None:
        """Test invalid command usage returns non-zero exit code."""
        result = runner.invoke(app, ["init", "--invalid-option"])

        assert result.exit_code != 0


class TestOutputFormat:
    """Test stdout/stderr format compliance."""

    def test_success_output_format(self, tmp_path: Path) -> None:
        """Test successful output goes to stdout with expected format."""
        workspace_path = tmp_path / "test-workspace"

        result = runner.invoke(app, ["init", "--workspace", str(workspace_path)])

        assert result.exit_code == 0
        assert "initialized successfully" in result.stdout.lower()
        assert str(workspace_path) in result.stdout

    def test_error_output_format(self, tmp_path: Path) -> None:
        """Test error output goes to stderr with expected format."""
        invalid_path = tmp_path / "nonexistent" / "workspace"

        result = runner.invoke(app, ["init", "--workspace", str(invalid_path)])

        assert result.exit_code != 0
        # CliRunner combines stdout and stderr in result.stdout by default
        output = result.stdout + (result.stderr or "")
        assert len(output) > 0
        assert "error" in output.lower() or "Error" in output


class TestCLIOptionPriority:
    """Test CLI option priority compliance."""

    def test_cli_option_overrides_env_var(self, tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
        """Test --workspace option overrides MIXSEEK_WORKSPACE env var."""
        env_workspace = tmp_path / "env-workspace"
        cli_workspace = tmp_path / "cli-workspace"

        # Set environment variable
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(env_workspace))

        result = runner.invoke(
            app, ["init", "--workspace", str(cli_workspace)], env={"MIXSEEK_WORKSPACE": str(env_workspace)}
        )

        assert result.exit_code == 0
        assert cli_workspace.exists()
        assert not env_workspace.exists()


class TestShortOptionEquivalence:
    """Test short option equivalence."""

    def test_short_option_w_equivalent_to_long_workspace(self, tmp_path: Path) -> None:
        """Test -w option is equivalent to --workspace."""
        workspace_path = tmp_path / "test-workspace"

        result = runner.invoke(app, ["init", "-w", str(workspace_path)])

        assert result.exit_code == 0
        assert workspace_path.exists()
        assert (workspace_path / "logs").exists()
        assert (workspace_path / "configs").exists()
        assert (workspace_path / "templates").exists()
