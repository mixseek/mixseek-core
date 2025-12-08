"""Integration tests for workspace creation and handling."""

import tomllib
from pathlib import Path

import pytest
from pytest import MonkeyPatch
from typer.testing import CliRunner

from mixseek.cli.main import app

runner = CliRunner()


class TestWorkspaceCreation:
    """Test workspace creation functionality."""

    def test_init_creates_workspace_structure(self, tmp_path: Path) -> None:
        """Test init creates all required workspace directories."""
        workspace_path = tmp_path / "test-workspace"

        result = runner.invoke(app, ["init", "--workspace", str(workspace_path)])

        assert result.exit_code == 0
        assert workspace_path.exists()
        assert (workspace_path / "logs").exists()
        assert (workspace_path / "logs").is_dir()
        assert (workspace_path / "configs").exists()
        assert (workspace_path / "configs").is_dir()
        assert (workspace_path / "templates").exists()
        assert (workspace_path / "templates").is_dir()

    def test_init_generates_template_configs(self, tmp_path: Path) -> None:
        """Test init generates all template configuration files."""
        workspace_path = tmp_path / "test-workspace"

        result = runner.invoke(app, ["init", "--workspace", str(workspace_path)])

        assert result.exit_code == 0

        # Verify orchestrator configs
        assert (workspace_path / "configs" / "search_news.toml").exists()
        assert (workspace_path / "configs" / "search_news_multi_perspective.toml").exists()

        # Verify team configs
        assert (workspace_path / "configs" / "agents" / "team_general_researcher.toml").exists()
        assert (workspace_path / "configs" / "agents" / "team_sns_researcher.toml").exists()
        assert (workspace_path / "configs" / "agents" / "team_academic_researcher.toml").exists()

        # Verify evaluator config
        assert (workspace_path / "configs" / "evaluators" / "evaluator_search_news.toml").exists()

        # Verify judgment config
        assert (workspace_path / "configs" / "judgment" / "judgment_search_news.toml").exists()

    def test_init_creates_subdirectories(self, tmp_path: Path) -> None:
        """Test init creates configs subdirectories for agents, evaluators, and judgment."""
        workspace_path = tmp_path / "test-workspace"

        result = runner.invoke(app, ["init", "--workspace", str(workspace_path)])

        assert result.exit_code == 0
        assert (workspace_path / "configs" / "agents").exists()
        assert (workspace_path / "configs" / "agents").is_dir()
        assert (workspace_path / "configs" / "evaluators").exists()
        assert (workspace_path / "configs" / "evaluators").is_dir()
        assert (workspace_path / "configs" / "judgment").exists()
        assert (workspace_path / "configs" / "judgment").is_dir()

    def test_evaluator_config_validity(self, tmp_path: Path) -> None:
        """Test evaluator config has valid structure and weights sum to 1.0."""
        workspace_path = tmp_path / "test-workspace"

        result = runner.invoke(app, ["init", "--workspace", str(workspace_path)])

        assert result.exit_code == 0

        evaluator_config = workspace_path / "configs" / "evaluators" / "evaluator_search_news.toml"
        assert evaluator_config.exists()

        # Validate TOML structure
        with open(evaluator_config, "rb") as f:
            config_data = tomllib.load(f)

        assert "default_model" in config_data
        assert "metrics" in config_data
        assert isinstance(config_data["metrics"], list)
        assert len(config_data["metrics"]) == 4

        # Validate metric names are default metrics
        metric_names = {m["name"] for m in config_data["metrics"]}
        assert metric_names == {"Coverage", "Relevance", "ClarityCoherence", "LLMPlain"}

        # Validate weights sum to 1.0
        total_weight = sum(m["weight"] for m in config_data["metrics"])
        assert abs(total_weight - 1.0) < 0.001  # Allow small floating point error


class TestEnvironmentVariableHandling:
    """Test environment variable handling."""

    @pytest.mark.skip(reason="CLI environment variable resolution needs implementation (Article 9 compliance)")
    def test_init_with_env_var(self, tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
        """Test init works with MIXSEEK_WORKSPACE environment variable."""
        import os
        import subprocess
        import sys

        workspace_path = tmp_path / "env-workspace"

        # CliRunner does not properly isolate environment variables
        # Use subprocess to test actual CLI behavior with environment variables
        env = os.environ.copy()
        # Set both MIXSEEK_WORKSPACE and MIXSEEK_WORKSPACE_PATH for compatibility
        env["MIXSEEK_WORKSPACE"] = str(workspace_path)
        env["MIXSEEK_WORKSPACE_PATH"] = str(workspace_path)

        result = subprocess.run(
            [sys.executable, "-m", "mixseek.cli.main", "init"],
            env=env,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"Command failed: {result.stderr}"
        assert workspace_path.exists()
        assert (workspace_path / "logs").exists()
        assert (workspace_path / "configs").exists()
        assert (workspace_path / "templates").exists()

    def test_init_with_cli_option(self, tmp_path: Path) -> None:
        """Test init works with CLI option."""
        workspace_path = tmp_path / "cli-workspace"

        result = runner.invoke(app, ["init", "--workspace", str(workspace_path)])

        assert result.exit_code == 0
        assert workspace_path.exists()


class TestExistingWorkspaceHandling:
    """Test handling of existing workspaces."""

    def test_init_existing_workspace_prompt(self, tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
        """Test init prompts when workspace already exists."""
        workspace_path = tmp_path / "existing-workspace"
        workspace_path.mkdir()

        # Simulate 'no' response to overwrite prompt
        monkeypatch.setattr("builtins.input", lambda _: "n")

        result = runner.invoke(app, ["init", "--workspace", str(workspace_path)], input="n\n")

        assert result.exit_code != 0
        output = result.stdout  # CliRunner mixes stdout and stderr by default
        assert "aborted" in output.lower()

    def test_init_partial_workspace(self, tmp_path: Path) -> None:
        """Test init handles partially existing workspace."""
        workspace_path = tmp_path / "partial-workspace"
        workspace_path.mkdir()
        (workspace_path / "logs").mkdir()  # Only logs exists

        result = runner.invoke(app, ["init", "--workspace", str(workspace_path)], input="y\n")

        # Should either succeed with overwrite or prompt for confirmation
        if result.exit_code == 0:
            assert (workspace_path / "configs").exists()
            assert (workspace_path / "templates").exists()


class TestErrorScenarios:
    """Test error handling scenarios."""

    def test_init_parent_not_exists(self, tmp_path: Path) -> None:
        """Test init fails when parent directory doesn't exist."""
        invalid_path = tmp_path / "nonexistent" / "workspace"

        result = runner.invoke(app, ["init", "--workspace", str(invalid_path)])

        assert result.exit_code != 0
        output = result.stdout  # CliRunner mixes stdout and stderr by default
        assert "parent directory" in output.lower() or "does not exist" in output.lower()

    def test_init_no_write_permission(self, tmp_path: Path) -> None:
        """Test init fails when no write permission."""
        # Create read-only parent directory
        readonly_parent = tmp_path / "readonly"
        readonly_parent.mkdir()
        readonly_parent.chmod(0o444)  # Read-only

        workspace_path = readonly_parent / "workspace"

        try:
            result = runner.invoke(app, ["init", "--workspace", str(workspace_path)])

            # Might succeed on some systems, but if it fails, should be permission error
            if result.exit_code != 0:
                output = result.stdout  # CliRunner mixes stdout and stderr by default
                assert "permission" in output.lower() or "Permission" in output
        finally:
            # Restore permissions for cleanup
            readonly_parent.chmod(0o755)

    def test_init_no_path_specified(self, monkeypatch: MonkeyPatch) -> None:
        """Test init fails when no workspace path specified."""
        # Clear environment variable
        monkeypatch.delenv("MIXSEEK_WORKSPACE", raising=False)

        result = runner.invoke(app, ["init"], env={})

        assert result.exit_code != 0


class TestSpecialPathCases:
    """Test special path handling."""

    def test_init_with_spaces_in_path(self, tmp_path: Path) -> None:
        """Test init works with spaces in workspace path."""
        workspace_path = tmp_path / "workspace with spaces"

        result = runner.invoke(app, ["init", "--workspace", str(workspace_path)])

        assert result.exit_code == 0
        assert workspace_path.exists()

    def test_init_with_symlink(self, tmp_path: Path) -> None:
        """Test init resolves symlinks correctly."""
        real_path = tmp_path / "real-workspace"
        symlink_path = tmp_path / "symlink-workspace"

        real_path.mkdir()
        symlink_path.symlink_to(real_path)

        result = runner.invoke(app, ["init", "--workspace", str(symlink_path)], input="y\n")

        assert result.exit_code == 0
        # Check that subdirectories were created
        assert (real_path / "logs").exists()
        assert (real_path / "configs").exists()
        assert (real_path / "templates").exists()

    def test_init_with_relative_path(self, tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
        """Test init works with relative paths."""
        # Change to tmp_path directory
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["init", "--workspace", "./relative-workspace"])

        assert result.exit_code == 0
        assert (tmp_path / "relative-workspace").exists()


class TestShortOptionVariations:
    """Test short option variations."""

    def test_short_option_with_absolute_path(self, tmp_path: Path) -> None:
        """Test -w option with absolute path."""
        workspace_path = tmp_path / "abs-workspace"

        result = runner.invoke(app, ["init", "-w", str(workspace_path)])

        assert result.exit_code == 0
        assert workspace_path.exists()

    def test_short_option_with_relative_path(self, tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
        """Test -w option with relative path."""
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["init", "-w", "./rel-workspace"])

        assert result.exit_code == 0
        assert (tmp_path / "rel-workspace").exists()

    def test_short_option_with_spaces(self, tmp_path: Path) -> None:
        """Test -w option with spaces in path."""
        workspace_path = tmp_path / "workspace with spaces"

        result = runner.invoke(app, ["init", "-w", str(workspace_path)])

        assert result.exit_code == 0
        assert workspace_path.exists()
