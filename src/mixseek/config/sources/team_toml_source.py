"""Team-specific TOML configuration source with reference resolution support."""

import tomllib
from pathlib import Path
from typing import Any

from pydantic.fields import FieldInfo
from pydantic_settings import PydanticBaseSettingsSource

from .field_mapper import merge_member_agent_fields, normalize_member_agent_fields


class TeamTomlSource(PydanticBaseSettingsSource):
    """Team設定専用のTOMLソース（T090：参照形式サポート）。

    既存のteam.toml形式（参照形式 config="agents/xxx.toml" を含む）と
    完全互換性を維持します。

    参照形式の例:
        [[team.members]]
        config = "agents/web-search.toml"
        tool_name = "web_search_tool"  # オプション：上書き可能
        tool_description = "Web検索を実行"  # オプション：上書き可能
    """

    def __init__(
        self,
        settings_cls: type,
        toml_file: Path,
        workspace: Path | None = None,
    ) -> None:
        """初期化。

        Args:
            settings_cls: 設定クラス（TeamSettings）
            toml_file: Team設定TOMLファイルパス
            workspace: Member Agent config解決の起点パス（未指定時は自動取得）
        """
        super().__init__(settings_cls)
        self.toml_file = toml_file
        self.workspace = workspace
        self.toml_data: dict[str, Any] = {}
        self._load_and_resolve()

    def _load_toml_file(self, toml_path: Path, context: str = "TOML file") -> dict[str, Any]:
        """TOMLファイルを読み込む共通処理（Article 10: DRY原則準拠）。

        Args:
            toml_path: TOMLファイルのパス（相対パスの場合はworkspace起点で解決）
            context: エラーメッセージ用のコンテキスト（例："team.toml", "member reference"）

        Returns:
            読み込んだTOMLデータ

        Raises:
            FileNotFoundError: ファイルが見つからない場合
            ValueError: TOML構文エラーの場合
        """
        # workspaceは_load_and_resolve()で必ず設定される
        assert self.workspace is not None, "workspace must be set before loading TOML files"

        # 絶対パスの場合はそのまま、相対パスの場合はworkspace起点で解決
        resolved_path = toml_path
        if not resolved_path.is_absolute():
            resolved_path = self.workspace / resolved_path

        if not resolved_path.exists():
            raise FileNotFoundError(f"{context} not found: {resolved_path}")

        try:
            with resolved_path.open("rb") as f:
                return tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            raise ValueError(f"Invalid TOML syntax in {context} ({resolved_path}): {e}") from e

    def _load_and_resolve(self) -> None:
        """TOMLファイルを読み込み、参照形式を解決。

        Raises:
            FileNotFoundError: TOMLファイルまたは参照先ファイルが見つからない場合
            ValueError: TOML構文エラーまたはバリデーションエラー
        """
        # workspace未指定時は自動取得
        if self.workspace is None:
            from mixseek.utils.env import get_workspace_for_config

            self.workspace = get_workspace_for_config()

        # 共通処理を使用してTOMLファイルを読み込み（Article 10: DRY原則準拠）
        data = self._load_toml_file(self.toml_file, context="Team config file")

        if "team" not in data:
            raise ValueError(f"Invalid team config: missing 'team' section in {self.toml_file}")

        # team セクションのデータをフラット化（TeamSettings用）
        team_data = data["team"]

        # member参照を解決
        resolved_members = []
        for member_data in team_data.get("members", []):
            if "config" in member_data:
                # 参照形式：外部ファイルを読み込み
                resolved_member = self._resolve_member_reference(member_data)
            else:
                # インライン形式：そのまま使用
                resolved_member = self._process_inline_member(member_data)

            resolved_members.append(resolved_member)

        # TeamSettings形式に変換
        self.toml_data = {
            "team_id": team_data.get("team_id"),
            "team_name": team_data.get("team_name"),
            "max_concurrent_members": team_data.get("max_concurrent_members", 15),
            "leader": team_data.get("leader", {}),
            "members": resolved_members,
        }

    def _resolve_member_reference(self, member_data: dict[str, Any]) -> dict[str, Any]:
        """Member Agent参照を解決（Feature 027互換）。

        Args:
            member_data: member設定（config="agents/xxx.toml"を含む）

        Returns:
            解決済みのmember設定

        Raises:
            FileNotFoundError: 参照先ファイルが見つからない場合
        """
        ref_path = Path(member_data["config"])

        # 共通処理を使用して外部TOMLを読み込み（Article 10: DRY原則準拠）
        context = f"member reference '{member_data['config']}'"
        member_toml = self._load_toml_file(ref_path, context=context)

        if "agent" not in member_toml:
            raise ValueError(f"Invalid agent config: missing 'agent' section in {member_data['config']}")

        # 共通マッピング関数を使用して MemberAgentSettings 形式に変換
        agent_data = member_toml["agent"]
        mapped_config = normalize_member_agent_fields(agent_data)

        # team.toml で tool_name/tool_description を上書き可能
        mapped_config = merge_member_agent_fields(mapped_config, member_data)

        return mapped_config

    def _process_inline_member(self, member_data: dict[str, Any]) -> dict[str, Any]:
        """インライン形式のmember設定を処理。

        Args:
            member_data: インライン形式のmember設定

        Returns:
            処理済みのmember設定
        """
        # 共通マッピング関数を使用して MemberAgentSettings 形式に変換
        # インライン形式でも name/type/description を使えるようにする
        return normalize_member_agent_fields(member_data)

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
            解決済みのTeam設定辞書
        """
        return self.toml_data
