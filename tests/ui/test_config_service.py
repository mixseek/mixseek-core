"""Tests for config service."""

from pathlib import Path

import pytest

from mixseek.ui.services.config_service import (
    get_all_orchestration_options,
    list_config_files,
    validate_orchestrator_config,
)


def test_list_config_files_empty(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """configs/が空の場合は空リストを返す."""
    monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
    configs = list_config_files()
    assert configs == []


def test_list_config_files_returns_sorted(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """複数ファイルがlast_modified降順でソートされる."""
    monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()

    # Create test files with different timestamps
    file1 = configs_dir / "old.toml"
    file2 = configs_dir / "new.toml"

    file1.write_text("# old")
    file2.write_text("# new")

    # Modify timestamps
    import time

    time.sleep(0.01)
    file2.touch()  # Update new.toml timestamp

    configs = list_config_files()
    assert len(configs) == 2
    assert configs[0].file_name == "new.toml"  # Most recent first
    assert configs[1].file_name == "old.toml"


def test_validate_orchestrator_config_success() -> None:
    """有効なorchestrator設定を検証."""
    toml_content = """
[orchestrator]
timeout_per_team_seconds = 600

[[orchestrator.teams]]
config = "configs/agents/team-a.toml"
"""
    assert validate_orchestrator_config(toml_content) is True


def test_validate_orchestrator_config_invalid() -> None:
    """無効な設定を検出."""
    # orchestratorセクションがない
    invalid_toml = """
[some_other_section]
value = 123
"""
    assert validate_orchestrator_config(invalid_toml) is False


def test_validate_orchestrator_config_syntax_error() -> None:
    """構文エラーでFalseを返す."""
    invalid_toml = """
[invalid syntax
"""
    assert validate_orchestrator_config(invalid_toml) is False


def test_validate_orchestrator_config_missing_teams() -> None:
    """teamsキーがない設定を無効と判定."""
    toml_content = """
[orchestrator]
timeout_per_team_seconds = 600
"""
    assert validate_orchestrator_config(toml_content) is False


def test_validate_orchestrator_config_empty_teams() -> None:
    """teams配列が空の設定を無効と判定."""
    toml_content = """
[orchestrator]
timeout_per_team_seconds = 600
teams = []
"""
    assert validate_orchestrator_config(toml_content) is False


def test_validate_orchestrator_config_invalid_team_structure() -> None:
    """teamに必須フィールド(config)がない設定を無効と判定."""
    toml_content = """
[orchestrator]
timeout_per_team_seconds = 600

[[orchestrator.teams]]
name = "team-a"
"""
    assert validate_orchestrator_config(toml_content) is False


def test_get_all_orchestration_options_returns_options(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """複数ファイルから選択肢を生成."""
    monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()

    # Create test config files (orchestrator format)
    config1 = configs_dir / "config1.toml"
    config1.write_text("""
[orchestrator]
timeout_per_team_seconds = 600

[[orchestrator.teams]]
config = "configs/agents/team-a.toml"
""")

    config2 = configs_dir / "config2.toml"
    config2.write_text("""
[orchestrator]
timeout_per_team_seconds = 600

[[orchestrator.teams]]
config = "configs/agents/team-b.toml"
""")

    options = get_all_orchestration_options()
    assert len(options) == 2

    # Check display labels (ファイル名ベース)
    labels = [opt.display_label for opt in options]
    assert "config1" in labels
    assert "config2" in labels


def test_get_all_orchestration_options_skips_invalid_toml(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """構文エラーファイルと無効な設定はスキップ."""
    monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()

    # Valid file (orchestrator format)
    valid_config = configs_dir / "valid.toml"
    valid_config.write_text("""
[orchestrator]
timeout_per_team_seconds = 600

[[orchestrator.teams]]
config = "configs/agents/team-a.toml"
""")

    # Invalid file (syntax error)
    invalid_config = configs_dir / "invalid.toml"
    invalid_config.write_text("[invalid syntax")

    # Valid TOML but wrong format (no orchestrator section)
    wrong_format = configs_dir / "wrong.toml"
    wrong_format.write_text("""
[some_other_section]
value = 123
""")

    options = get_all_orchestration_options()
    assert len(options) == 1  # Only valid orchestrator file
    assert options[0].orchestration_id == "valid"
