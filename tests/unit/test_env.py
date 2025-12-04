"""Unit tests for environment variable utilities."""

from pathlib import Path

import pytest
from pytest import MonkeyPatch

from mixseek.config.constants import WORKSPACE_ENV_VAR
from mixseek.exceptions import WorkspacePathNotSpecifiedError
from mixseek.utils.env import get_workspace_path


class TestGetWorkspacePath:
    """Test get_workspace_path function."""

    def test_get_workspace_path_priority_cli_over_env(self, monkeypatch: MonkeyPatch) -> None:
        """Test CLI argument takes priority over environment variable."""
        cli_path = Path("/cli/workspace")
        env_path = "/env/workspace"

        monkeypatch.setenv(WORKSPACE_ENV_VAR, env_path)

        result = get_workspace_path(cli_path)
        assert result == cli_path

    def test_get_workspace_path_uses_env_when_no_cli(self, monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
        """Test environment variable is used when CLI argument is None (Article 9準拠)."""
        env_path = tmp_path / "workspace"
        env_path.mkdir(parents=True, exist_ok=True)

        monkeypatch.setenv(WORKSPACE_ENV_VAR, str(env_path))

        result = get_workspace_path(None)
        assert result == env_path

    def test_get_workspace_path_error_when_neither_provided(
        self, monkeypatch: MonkeyPatch, isolate_from_project_dotenv: None
    ) -> None:
        """Test WorkspacePathNotSpecifiedError is raised when neither CLI nor env var is set (Article 9準拠)."""
        # Remove environment variable if it exists
        monkeypatch.delenv(WORKSPACE_ENV_VAR, raising=False)
        monkeypatch.delenv("MIXSEEK_WORKSPACE_PATH", raising=False)

        with pytest.raises(WorkspacePathNotSpecifiedError) as exc_info:
            get_workspace_path(None)

        assert "Workspace path not specified" in str(exc_info.value)
        assert "MIXSEEK_WORKSPACE" in str(exc_info.value)

    def test_get_workspace_path_handles_empty_env_var(
        self, monkeypatch: MonkeyPatch, isolate_from_project_dotenv: None
    ) -> None:
        """Test empty environment variable is treated as not set (Article 9準拠)."""
        monkeypatch.setenv(WORKSPACE_ENV_VAR, "")
        monkeypatch.delenv("MIXSEEK_WORKSPACE_PATH", raising=False)

        with pytest.raises(WorkspacePathNotSpecifiedError):
            get_workspace_path(None)

    def test_get_workspace_path_cli_arg_path_object(self) -> None:
        """Test function works with Path object as CLI argument."""
        cli_path = Path("/path/to/workspace")

        result = get_workspace_path(cli_path)
        assert result == cli_path
        assert isinstance(result, Path)

    def test_get_workspace_path_env_var_converted_to_path(self, monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
        """Test environment variable string is converted to Path object."""
        env_path = tmp_path / "workspace"
        env_path.mkdir(parents=True, exist_ok=True)

        monkeypatch.setenv(WORKSPACE_ENV_VAR, str(env_path))

        result = get_workspace_path(None)
        assert result == env_path
        assert isinstance(result, Path)

    def test_get_workspace_path_with_clean_environment(
        self, monkeypatch: MonkeyPatch, isolate_from_project_dotenv: None
    ) -> None:
        """Test with completely clean environment (Article 9準拠)."""
        # Clear all workspace-related environment variables
        monkeypatch.delenv(WORKSPACE_ENV_VAR, raising=False)
        monkeypatch.delenv("MIXSEEK_WORKSPACE_PATH", raising=False)

        with pytest.raises(WorkspacePathNotSpecifiedError) as exc_info:
            get_workspace_path(None)

        assert WORKSPACE_ENV_VAR in str(exc_info.value)

    def test_get_workspace_path_special_characters(self, monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
        """Test environment variable with special characters."""
        env_path = tmp_path / "path with spaces" / "workspace"
        env_path.mkdir(parents=True, exist_ok=True)

        monkeypatch.setenv(WORKSPACE_ENV_VAR, str(env_path))

        result = get_workspace_path(None)
        assert result == env_path
