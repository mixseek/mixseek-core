"""プリフライトチェック: TOML トップレベルキー判別ヘルパー。

`_detect_unit_kind` を独立モジュールに置くことで、`team.py` / `workflow.py` から
`from mixseek.config.preflight.validators.unit_kind import _detect_unit_kind` で
直接 import でき、`validators/__init__.py` 経由の循環 import を回避する。
"""

import tomllib
from pathlib import Path
from typing import Literal

from mixseek.config import OrchestratorSettings

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
    resolved = config_path if config_path.is_absolute() else (workspace / config_path)
    try:
        with open(resolved, "rb") as f:
            data = tomllib.load(f)
    except (FileNotFoundError, tomllib.TOMLDecodeError, OSError):
        return "unknown"
    has_team = "team" in data
    has_workflow = "workflow" in data
    if has_team and not has_workflow:
        return "team"
    if has_workflow and not has_team:
        return "workflow"
    return "unknown"


def _detect_unit_kinds(settings: OrchestratorSettings, workspace: Path) -> list[UnitKind]:
    """orchestrator の `teams` 全 entry の kind を一度だけ判定する。

    runner から両 validator に同じ結果を共有することで、TOML を 2 回ではなく 1 回しか
    読まずに済み、validator 間で kind 判定がずれる余地を排除する。
    """
    return [_detect_unit_kind(Path(entry.get("config", "")), workspace) for entry in settings.teams]
