"""TOML ファイル読み込みユーティリティ。

workspace 基準の相対パス解決と tomllib による読み込み・例外変換を一元化する。

以前は `TeamTomlSource._load_toml_file` / `WorkflowTomlSource._load_toml_file` /
`ConfigurationManager.load_unit_settings` の 3 箇所で同一ロジックが重複していたため
統合した。
"""

import tomllib
from pathlib import Path
from typing import Any


def load_toml_with_workspace(
    toml_path: Path,
    *,
    workspace: Path | None = None,
    context: str = "TOML file",
) -> dict[str, Any]:
    """workspace 基準で相対パスを解決し TOML ファイルを辞書として読み込む。

    Args:
        toml_path: TOML ファイルのパス。相対なら `workspace` 起点で解決する。
        workspace: 相対パス解決の起点。未指定時は `get_workspace_for_config()` で取得する。
        context: エラーメッセージに使うコンテキスト名（例: "Team config file"）。

    Returns:
        TOML の内容を表す辞書。

    Raises:
        FileNotFoundError: ファイルが存在しない。
        ValueError: TOML 構文エラー。
    """
    if workspace is None:
        # 循環 import 回避のため関数内 import（utils.env → config → utils で循環するのを防ぐ）
        from mixseek.utils.env import get_workspace_for_config

        workspace = get_workspace_for_config()

    resolved_path = toml_path
    if not resolved_path.is_absolute():
        resolved_path = workspace / resolved_path

    if not resolved_path.exists():
        raise FileNotFoundError(f"{context} not found: {resolved_path}")

    try:
        with resolved_path.open("rb") as f:
            return tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise ValueError(f"Invalid TOML syntax in {context} ({resolved_path}): {e}") from e
