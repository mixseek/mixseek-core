"""Tests for workspace utilities."""

from pathlib import Path

import pytest

from mixseek.ui.utils.workspace import get_configs_dir, get_db_path, get_workspace_path


def test_get_workspace_path_raises_when_not_set(
    monkeypatch: pytest.MonkeyPatch, isolate_from_project_dotenv: None
) -> None:
    """環境変数未設定時にValueErrorを発生させること."""
    monkeypatch.delenv("MIXSEEK_WORKSPACE", raising=False)
    monkeypatch.delenv("MIXSEEK_WORKSPACE_PATH", raising=False)
    with pytest.raises(ValueError, match="Workspace path not specified"):
        get_workspace_path()


def test_get_workspace_path_returns_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """環境変数設定時に正しいパスを返すこと."""
    monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
    assert get_workspace_path() == tmp_path


def test_get_configs_dir_creates_directory(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """configs/ディレクトリが存在しない場合は作成すること."""
    monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
    configs_dir = get_configs_dir()
    assert configs_dir.exists()
    assert configs_dir.name == "configs"


def test_get_db_path_returns_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """mixseek.dbのパスを返すこと（ファイル不在でも）."""
    monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
    db_path = get_db_path()
    assert db_path == tmp_path / "mixseek.db"
