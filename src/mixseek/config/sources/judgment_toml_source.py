"""Judgment-specific TOML configuration source.

このモジュールはjudgment.toml（LLM-as-a-Judge判定設定）を
読み込むための設定ソースを提供します。
"""

import tomllib
from pathlib import Path
from typing import Any

from pydantic.fields import FieldInfo
from pydantic_settings import PydanticBaseSettingsSource


class JudgmentTomlSource(PydanticBaseSettingsSource):
    """Judgment設定専用のTOMLソース。

    judgment.toml形式を読み込み、JudgmentSettingsスキーマに変換します。

    TOMLファイル形式:
        model = "google-gla:gemini-2.5-flash"
        temperature = 0.0
        max_tokens = 2000
        max_retries = 3
        timeout_seconds = 60
        stop_sequences = ["END", "STOP"]  # optional
        top_p = 0.9  # optional
        seed = 42  # optional (OpenAI/Gemini only)
        system_instruction = "..."  # optional
    """

    def __init__(
        self,
        settings_cls: type,
        toml_file: Path,
        workspace: Path | None = None,
    ) -> None:
        """初期化。

        Args:
            settings_cls: 設定クラス（JudgmentSettings）
            toml_file: Judgment設定TOMLファイルパス
            workspace: 相対パス解決の起点パス（未指定時は自動取得）
        """
        super().__init__(settings_cls)
        self.toml_file = toml_file
        self.workspace = workspace
        self.toml_data: dict[str, Any] = {}
        self._load_and_convert()

    def _load_and_convert(self) -> None:
        """TOMLファイルを読み込み、JudgmentSettings形式に変換。

        Raises:
            FileNotFoundError: TOMLファイルが見つからない場合
            ValueError: TOML構文エラーまたはバリデーションエラー
        """
        # workspace未指定時は自動取得
        if self.workspace is None:
            from mixseek.utils.env import get_workspace_for_config

            self.workspace = get_workspace_for_config()

        # toml_fileが相対パスの場合、workspaceからの相対パスとして解釈
        toml_path = self.toml_file
        if not toml_path.is_absolute():
            toml_path = self.workspace / toml_path

        if not toml_path.exists():
            raise FileNotFoundError(
                f"Judgment config file not found: {toml_path}\n"
                f"Workspace: {self.workspace}\n"
                f"Original path: {self.toml_file}"
            )

        # TOMLファイルを読み込み（解決済みパスを使用）
        with open(toml_path, "rb") as f:
            data = tomllib.load(f)

        # JudgmentSettings形式に変換（フラットな構造）
        self.toml_data = {
            "model": data.get("model"),
            "temperature": data.get("temperature"),
            "max_tokens": data.get("max_tokens"),
            "max_retries": data.get("max_retries"),
            "timeout_seconds": data.get("timeout_seconds"),
            "stop_sequences": data.get("stop_sequences"),
            "top_p": data.get("top_p"),
            "seed": data.get("seed"),
            "system_instruction": data.get("system_instruction"),
        }

        # Noneの値を除去（デフォルト値を使用）
        self.toml_data = {k: v for k, v in self.toml_data.items() if v is not None}

    def get_field_value(self, field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        """フィールド値を取得。

        Args:
            field: フィールド情報
            field_name: フィールド名

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
        """値の前処理。

        Args:
            field_name: フィールド名
            field: フィールド情報
            value: 値
            value_is_complex: 複雑な値かどうか

        Returns:
            処理済みの値
        """
        return value

    def __call__(self) -> dict[str, Any]:
        """すべてのフィールド値を取得。

        Returns:
            Judgment設定辞書
        """
        return self.toml_data
