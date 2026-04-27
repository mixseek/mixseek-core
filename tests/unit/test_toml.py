"""`mixseek.utils.toml.load_toml_with_workspace` の単体テスト。

`TeamTomlSource` / `WorkflowTomlSource` / `ConfigurationManager.load_unit_settings`
で重複していた「workspace 基準の相対パス解決 + tomllib 読み込み + 例外変換」の
共通ユーティリティに対するテスト。
"""

from pathlib import Path
from textwrap import dedent

import pytest
from pytest import MonkeyPatch

from mixseek.config.constants import WORKSPACE_ENV_VAR
from mixseek.utils.toml import load_toml_with_workspace


def _write_toml(dir_path: Path, name: str, content: str) -> Path:
    path = dir_path / name
    path.write_text(dedent(content).lstrip())
    return path


class TestRelativePathResolution:
    """相対パス → workspace 起点で解決するケース。"""

    def test_relative_path_resolves_against_workspace(self, tmp_path: Path) -> None:
        _write_toml(
            tmp_path,
            "cfg.toml",
            """
            [section]
            key = "value"
            """,
        )
        data = load_toml_with_workspace(Path("cfg.toml"), workspace=tmp_path)
        assert data == {"section": {"key": "value"}}

    def test_absolute_path_does_not_prepend_workspace(self, tmp_path: Path) -> None:
        path = _write_toml(
            tmp_path,
            "cfg.toml",
            """
            [section]
            key = "absolute"
            """,
        )
        other_workspace = tmp_path / "other"
        other_workspace.mkdir()
        data = load_toml_with_workspace(path, workspace=other_workspace)
        assert data == {"section": {"key": "absolute"}}

    def test_workspace_none_falls_back_to_env(self, tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
        """workspace=None のとき MIXSEEK_WORKSPACE 経由で解決される。"""
        _write_toml(
            tmp_path,
            "cfg.toml",
            """
            [section]
            key = "env-based"
            """,
        )
        monkeypatch.setenv(WORKSPACE_ENV_VAR, str(tmp_path))
        data = load_toml_with_workspace(Path("cfg.toml"))
        assert data == {"section": {"key": "env-based"}}


class TestErrorMessages:
    """context を差し替えることで呼び出し側ごとのエラーメッセージを生成できる。"""

    def test_file_not_found_uses_default_context(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="TOML file not found"):
            load_toml_with_workspace(Path("missing.toml"), workspace=tmp_path)

    def test_file_not_found_uses_custom_context(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="Team config file not found"):
            load_toml_with_workspace(
                Path("missing.toml"),
                workspace=tmp_path,
                context="Team config file",
            )

    def test_invalid_toml_syntax_includes_context(self, tmp_path: Path) -> None:
        path = tmp_path / "broken.toml"
        path.write_text("this is = not = valid [[")
        with pytest.raises(ValueError, match=r"Invalid TOML syntax in Workflow config file"):
            load_toml_with_workspace(
                Path("broken.toml"),
                workspace=tmp_path,
                context="Workflow config file",
            )


class TestReturnsDict:
    """読み込み結果は dict で返る（tomllib.load と同じ契約）。"""

    def test_returns_nested_dict(self, tmp_path: Path) -> None:
        _write_toml(
            tmp_path,
            "cfg.toml",
            """
            [outer]
            a = 1

            [outer.inner]
            b = "two"
            """,
        )
        data = load_toml_with_workspace(Path("cfg.toml"), workspace=tmp_path)
        assert data == {"outer": {"a": 1, "inner": {"b": "two"}}}
