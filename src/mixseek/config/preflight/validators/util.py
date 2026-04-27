"""プリフライトチェック: validator 共通ユーティリティ。

`validators/` 配下のファイル名慣例は config 種類（team / workflow / auth / ...）
を表すため、それに該当しない共通ヘルパーは本モジュールに集約する。
"""

from pathlib import Path
from typing import Literal

from mixseek.config import OrchestratorSettings
from mixseek.utils.toml import load_toml_with_workspace

UnitKind = Literal["team", "workflow", "unknown"]


def _detect_unit_kind(config_path: Path, workspace: Path) -> UnitKind:
    """`[team]` / `[workflow]` のトップレベルキーを判別する。

    `"unknown"` (TOML 解析失敗 / 両セクション同居 / どちらもなし / file not found) は
    呼び出し側 (team validator) が `load_unit_settings` で ValueError / FileNotFoundError
    を raise させ ERROR 化する。本ヘルパー単体ではエラー報告しない。

    Args:
        config_path: 判別対象 TOML パス（絶対 / 相対どちらも可）。
        workspace: 相対パス解決の起点となるワークスペースパス。

    Returns:
        `"team"`: `[team]` のみ存在
        `"workflow"`: `[workflow]` のみ存在
        `"unknown"`: TOML 解析失敗 / 両セクション同居 / どちらもなし / file not found
    """
    try:
        data = load_toml_with_workspace(config_path, workspace=workspace, context="Unit config file")
    except (FileNotFoundError, ValueError, OSError):
        return "unknown"
    has_team = "team" in data
    has_workflow = "workflow" in data
    if has_team and not has_workflow:
        return "team"
    if has_workflow and not has_team:
        return "workflow"
    return "unknown"


def _detect_unit_kinds(settings: OrchestratorSettings, workspace: Path) -> list[UnitKind]:
    """orchestrator の `teams` 全 entry の kind を一括判定する。

    `_validate_teams` / `_validate_workflows` の各 validator 先頭で 1 回呼び、
    `zip(settings.teams, unit_kinds, strict=True)` で entry とペアにして処理する。
    """
    return [_detect_unit_kind(Path(entry.get("config", "")), workspace) for entry in settings.teams]
