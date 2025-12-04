"""Orchestrator-specific TOML configuration source (T086)."""

import tomllib
from pathlib import Path
from typing import Any

from pydantic.fields import FieldInfo
from pydantic_settings import PydanticBaseSettingsSource


class OrchestratorTomlSource(PydanticBaseSettingsSource):
    """Orchestrator設定専用のTOMLソース（T086：orchestrator.toml形式サポート）。

    orchestrator.toml形式の例:
        [orchestrator]
        timeout_per_team_seconds = 600

        [[orchestrator.teams]]
        config = "configs/agents/team-a.toml"

        [[orchestrator.teams]]
        config = "configs/agents/team-b.toml"
    """

    def __init__(
        self,
        settings_cls: type,
        toml_file: Path,
        workspace: Path | None = None,
    ) -> None:
        """初期化。

        Args:
            settings_cls: 設定クラス（OrchestratorSettings）
            toml_file: Orchestrator設定TOMLファイルパス
            workspace: Team config解決の起点パス（未指定時は自動取得）
        """
        super().__init__(settings_cls)
        self.toml_file = toml_file
        self.workspace = workspace
        self.toml_data: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """TOMLファイルを読み込み。

        Raises:
            FileNotFoundError: TOMLファイルが見つからない場合
            ValueError: TOML構文エラーまたはバリデーションエラー
        """
        # workspace未指定時は自動取得
        if self.workspace is None:
            from mixseek.utils.env import get_workspace_for_config

            self.workspace = get_workspace_for_config()

        # toml_pathが相対パスの場合、workspaceからの相対パスとして解釈
        toml_path = self.toml_file
        if not toml_path.is_absolute():
            toml_path = self.workspace / toml_path

        if not toml_path.exists():
            raise FileNotFoundError(f"Orchestrator config file not found: {toml_path}")

        # TOMLファイルを読み込み
        try:
            with open(toml_path, "rb") as f:
                data = tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            raise ValueError(f"Invalid TOML syntax in {toml_path}: {e}") from e

        if "orchestrator" not in data:
            raise ValueError(f"Invalid orchestrator config: missing 'orchestrator' section in {toml_path}")

        # orchestrator セクションのデータをフラット化（OrchestratorSettings用）
        orchestrator_data = data["orchestrator"]

        # TOMLデータを保存
        self.toml_data = orchestrator_data

    def get_field_value(self, field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        """指定されたフィールドの値を取得。

        Args:
            field: フィールド情報
            field_name: フィールド名

        Returns:
            (value, field_key, value_is_complex) のタプル
        """
        value = self.toml_data.get(field_name)
        return value, field_name, False

    def __call__(self) -> dict[str, Any]:
        """設定値の辞書を返す。

        Returns:
            設定値の辞書
        """
        return self.toml_data
