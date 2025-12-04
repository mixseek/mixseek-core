"""Evaluation-specific TOML configuration source.

このモジュールはevaluator.toml（複雑な構造：llm_default + metrics配列）を
読み込むための設定ソースを提供します。
"""

import tomllib
from pathlib import Path
from typing import Any

from pydantic.fields import FieldInfo
from pydantic_settings import PydanticBaseSettingsSource


class EvaluationTomlSource(PydanticBaseSettingsSource):
    """Evaluation設定専用のTOMLソース（T080実装）。

    evaluator.toml形式（EvaluationConfig互換）を読み込み、
    EvaluatorSettingsスキーマに変換します。

    TOMLファイル形式:
        [llm_default]
        model = "anthropic:claude-sonnet-4-5-20250929"
        temperature = 0.0
        max_tokens = 2000
        max_retries = 3

        [[metrics]]
        name = "ClarityCoherence"
        weight = 0.4
        model = "anthropic:claude-sonnet-4-5-20250929"

        [[metrics]]
        name = "Coverage"
        weight = 0.3
    """

    def __init__(
        self,
        settings_cls: type,
        toml_file: Path,
        workspace: Path | None = None,
    ) -> None:
        """初期化。

        Args:
            settings_cls: 設定クラス（EvaluatorSettings）
            toml_file: Evaluator設定TOMLファイルパス
            workspace: 相対パス解決の起点パス（未指定時は自動取得）
        """
        super().__init__(settings_cls)
        self.toml_file = toml_file
        self.workspace = workspace
        self.toml_data: dict[str, Any] = {}
        self._load_and_convert()

    def _load_and_convert(self) -> None:
        """TOMLファイルを読み込み、EvaluatorSettings形式に変換。

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
                f"Evaluator config file not found: {toml_path}\n"
                f"Workspace: {self.workspace}\n"
                f"Original path: {self.toml_file}"
            )

        # TOMLファイルを読み込み（解決済みパスを使用）
        with open(toml_path, "rb") as f:
            data = tomllib.load(f)

        # [llm_default] セクション（オプション）
        llm_default = data.get("llm_default", {})

        # トップレベルのdefault_modelとmax_retriesもサポート（後方互換性）
        # 優先順位: llm_default.model > default_model
        default_model = llm_default.get("model") or data.get("default_model")
        max_retries = llm_default.get("max_retries")
        if max_retries is None:
            max_retries = data.get("max_retries")

        # timeout_seconds: 優先順位 llm_default.timeout_seconds > トップレベルのtimeout_seconds
        timeout_seconds = llm_default.get("timeout_seconds")
        if timeout_seconds is None:
            timeout_seconds = data.get("timeout_seconds")

        # EvaluatorSettings形式に変換
        self.toml_data = {
            "default_model": default_model,
            "temperature": llm_default.get("temperature"),
            "max_tokens": llm_default.get("max_tokens"),
            "max_retries": max_retries,
            "timeout_seconds": timeout_seconds,
            # 動的配列をそのまま格納（TeamSettingsパターン）
            "metrics": data.get("metrics", []),
            "custom_metrics": data.get("custom_metrics", {}),
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
            Evaluation設定辞書
        """
        return self.toml_data
