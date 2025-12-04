"""Member Agent-specific TOML configuration source.

このモジュールは個別のMember Agent TOML（例: examples/agents/plain_agent.toml）を
読み込むための設定ソースを提供します。
"""

import tomllib
from pathlib import Path
from typing import Any

from pydantic.fields import FieldInfo
from pydantic_settings import PydanticBaseSettingsSource

from .field_mapper import normalize_member_agent_fields


class MemberAgentTomlSource(PydanticBaseSettingsSource):
    """Member Agent設定専用のTOMLソース（T079実装）。

    個別のMember Agent TOMLファイル（Feature 027形式）を読み込み、
    MemberAgentSettingsスキーマに変換します。

    TOMLファイル形式:
        [agent]
        name = "plain-agent"
        type = "plain"
        model = "google-gla:gemini-2.5-flash-lite"
        temperature = 0.2
        max_tokens = 4096

        [agent.system_instruction]
        text = "..."

        [agent.usage_limits]
        max_requests_per_hour = 500
        ...
    """

    def __init__(
        self,
        settings_cls: type,
        toml_file: Path,
        workspace: Path | None = None,
    ) -> None:
        """初期化。

        Args:
            settings_cls: 設定クラス（MemberAgentSettings）
            toml_file: Member Agent設定TOMLファイルパス
            workspace: 相対パス解決の起点パス（未指定時は自動取得）
        """
        super().__init__(settings_cls)
        self.toml_file = toml_file
        self.workspace = workspace
        self.toml_data: dict[str, Any] = {}
        self._load_and_convert()

    def _load_and_convert(self) -> None:
        """TOMLファイルを読み込み、MemberAgentSettings形式に変換。

        Raises:
            FileNotFoundError: TOMLファイルが見つからない場合
            ValueError: TOML構文エラーまたはバリデーションエラー
        """
        # workspace未指定時は明示的エラー（Article 9準拠 - T079 fix）
        if self.workspace is None:
            from mixseek.utils.env import get_workspace_path

            self.workspace = get_workspace_path(cli_arg=None)

        # toml_fileが相対パスの場合、workspaceからの相対パスとして解釈
        toml_path = self.toml_file
        if not toml_path.is_absolute():
            toml_path = self.workspace / toml_path

        if not toml_path.exists():
            raise FileNotFoundError(
                f"Member Agent config file not found: {toml_path}\n"
                f"Workspace: {self.workspace}\n"
                f"Original path: {self.toml_file}"
            )

        # TOMLファイルを読み込み（解決済みパスを使用）
        with open(toml_path, "rb") as f:
            data = tomllib.load(f)

        if "agent" not in data:
            raise ValueError(f"Invalid member agent config: missing 'agent' section in {toml_path}")

        # [agent] セクションのデータを取得
        agent_data = data["agent"]

        # 共通マッピング関数を使用して MemberAgentSettings 形式に変換
        self.toml_data = normalize_member_agent_fields(agent_data)

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
            Member Agent設定辞書
        """
        return self.toml_data
