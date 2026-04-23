"""Workflow 設定専用の TOML ソース。

`[workflow]` セクションを読み込み `WorkflowSettings` 構築用の辞書に平坦化する。
`team_toml_source.py` が行っている member の `config = "..."` 参照解決は、workflow
MVP では Non-goal のため実装しない（設計書 §1.3）。

Pydantic default を活かすため、`default_model` / `include_all_context` /
`final_output_format` の 3 フィールドは **TOML に指定がある場合のみ**辞書に含める
（`None` を渡すと Pydantic の default を上書きしてしまうため）。
"""

import tomllib
from pathlib import Path
from typing import Any

from pydantic.fields import FieldInfo
from pydantic_settings import PydanticBaseSettingsSource


class WorkflowTomlSource(PydanticBaseSettingsSource):
    """`WorkflowSettings` 構築用の TOML ソース。

    `TeamTomlSource` と同じ `PydanticBaseSettingsSource` サブクラスだが、以下が異なる:
      - `[workflow]` セクションを前提とする（team 側は `[team]`）
      - executor の `config = "..."` 参照解決は行わない（MVP Non-goal）
      - Pydantic default を保つため、省略可能フィールドは key ごと辞書から省く
    """

    def __init__(
        self,
        settings_cls: type,
        toml_file: Path,
        workspace: Path | None = None,
    ) -> None:
        """初期化時に TOML を読み込み `[workflow]` を平坦化する。

        Args:
            settings_cls: 設定クラス（`WorkflowSettings`）
            toml_file: workflow 設定 TOML のパス
            workspace: 相対パス解決の起点（未指定時は `get_workspace_for_config()` で取得）
        """
        super().__init__(settings_cls)
        self.toml_file = toml_file
        self.workspace = workspace
        self.toml_data: dict[str, Any] = {}
        self._load_and_resolve()

    def _load_toml_file(self, toml_path: Path) -> dict[str, Any]:
        """TOML ファイルを読み込む（workspace 基準で相対パス解決）。"""
        # workspace 未指定時は _load_and_resolve() で自動取得済み
        assert self.workspace is not None, "workspace must be set before loading TOML files"

        resolved_path = toml_path
        if not resolved_path.is_absolute():
            resolved_path = self.workspace / resolved_path

        if not resolved_path.exists():
            raise FileNotFoundError(f"Workflow config file not found: {resolved_path}")

        try:
            with resolved_path.open("rb") as f:
                return tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            raise ValueError(f"Invalid TOML syntax in workflow config ({resolved_path}): {e}") from e

    def _load_and_resolve(self) -> None:
        """TOML を読み込み `[workflow]` 配下を平坦化する。

        Raises:
            FileNotFoundError: TOML ファイル不在
            ValueError: TOML 構文エラー / `[workflow]` セクション欠如
        """
        if self.workspace is None:
            from mixseek.utils.env import get_workspace_for_config

            self.workspace = get_workspace_for_config()

        data = self._load_toml_file(self.toml_file)

        if "workflow" not in data:
            raise ValueError(f"Invalid workflow config: missing 'workflow' section in {self.toml_file}")

        wf = data["workflow"]

        # 必須フィールド + steps（空 list でも Pydantic の min_length=1 で弾かれる）
        self.toml_data = {
            "workflow_id": wf.get("workflow_id"),
            "workflow_name": wf.get("workflow_name"),
            "steps": wf.get("steps", []),
        }

        # 省略可能フィールドは TOML 指定時のみ辞書に入れる（Pydantic default を活かす）。
        # key ごと落とすのは、None を渡すと WorkflowSettings の default を上書きしてしまうため。
        for key in ("default_model", "include_all_context", "final_output_format"):
            if key in wf:
                self.toml_data[key] = wf[key]

    def get_field_value(self, field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        """フィールド値を取得。

        Returns:
            (値, キー, 値が見つかったかどうか) のタプル
        """
        value = self.toml_data.get(field_name)
        return value, field_name, value is not None

    def prepare_field_value(
        self,
        field_name: str,
        field: FieldInfo,
        value: Any,
        value_is_complex: bool,
    ) -> Any:
        """値の前処理（WorkflowTomlSource は pass-through）。"""
        return value

    def __call__(self) -> dict[str, Any]:
        """解決済みの workflow 設定辞書を返す。"""
        return self.toml_data
