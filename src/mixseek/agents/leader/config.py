"""Leader Agent TOML設定管理

IMPORTANT (T078移行完了): このモジュールのLeaderAgentConfig/TeamConfig/load_team_config()は
レガシーAPIとして維持されていますが、内部的にはConfigurationManager（新）を使用します。
新規コードではConfigurationManager.load_team_settings()を直接使用してください。
"""

import warnings
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

from mixseek.config.schema import TeamSettings


class LeaderAgentConfig(BaseModel):
    """Leader Agent設定"""

    system_instruction: str | None = Field(default=None, description="システム指示（Pydantic AIのinstructions）")
    system_prompt: str | None = Field(
        default=None, description="システムプロンプト（Pydantic AIのsystem_prompt、高度な利用者向け）"
    )
    model: str = Field(default="google-gla:gemini-2.5-flash-lite", description="LLMモデル")
    temperature: float | None = Field(
        default=None, ge=0.0, le=2.0, description="Temperature（Noneの場合はモデルのデフォルト値を使用）"
    )
    max_tokens: int | None = Field(
        default=None, gt=0, description="最大トークン数（Noneの場合はモデルのデフォルト値を使用）"
    )
    timeout_seconds: int | None = Field(
        default=300, ge=10, le=600, description="HTTPタイムアウト（秒、デフォルト: 300秒 / 5分）"
    )
    max_retries: int = Field(default=3, ge=0, description="LLM API呼び出しの最大リトライ回数")
    stop_sequences: list[str] | None = Field(default=None, description="生成を停止するシーケンスのリスト")
    top_p: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Top-pサンプリングパラメータ（Noneの場合はモデルのデフォルト値）"
    )
    seed: int | None = Field(
        default=None, description="ランダムシード（OpenAI/Geminiでサポート、Anthropicでは非サポート）"
    )

    @field_validator("system_instruction")
    @classmethod
    def validate_system_instruction(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if v == "":
            return ""
        if not v.strip():
            warnings.warn(
                "system_instruction is whitespace-only. Treating it as empty string.",
                UserWarning,
                stacklevel=2,
            )
            return ""
        return v


class TeamMemberAgentConfig(BaseModel):
    """Member Agent設定（Team/Leader Agent視点）"""

    agent_name: str = Field(description="Agent名")
    agent_type: str = Field(description="Agent種別")
    tool_name: str | None = Field(default=None, description="Tool名")
    tool_description: str = Field(description="Tool説明")
    model: str = Field(description="LLMモデル")
    system_instruction: str | None = Field(
        default=None, description="システム指示（Noneの場合はデフォルト指示を自動適用）"
    )
    system_prompt: str | None = Field(
        default=None, description="システムプロンプト（Pydantic AIのsystem_prompt、system_instructionと併用可能）"
    )
    temperature: float | None = Field(
        default=None, ge=0.0, le=2.0, description="Temperature（Noneの場合はモデルのデフォルト値を使用）"
    )
    max_tokens: int | None = Field(
        default=None, gt=0, description="最大トークン数（Noneの場合はモデルのデフォルト値を使用）"
    )
    timeout_seconds: int | None = Field(default=None, ge=0, description="タイムアウト（秒）")
    max_retries: int = Field(default=3, ge=0, description="LLM API呼び出しの最大リトライ回数")
    stop_sequences: list[str] | None = Field(default=None, description="生成を停止するシーケンスのリスト")
    top_p: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Top-pサンプリングパラメータ（Noneの場合はモデルのデフォルト値）"
    )
    seed: int | None = Field(
        default=None, description="ランダムシード（OpenAI/Geminiでサポート、Anthropicでは非サポート）"
    )
    config: str | None = Field(default=None, description="参照形式パス")

    @field_validator("tool_description")
    @classmethod
    def validate_tool_description(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("tool_description cannot be empty")
        return v

    def get_tool_name(self) -> str:
        return self.tool_name or f"delegate_to_{self.agent_name}"


class TeamConfig(BaseModel):
    """チーム設定"""

    team_id: str = Field(description="チームID")
    team_name: str = Field(description="チーム名")
    max_concurrent_members: int = Field(default=15, ge=1, le=50, description="最大Member Agent数")
    leader: LeaderAgentConfig = Field(default_factory=LeaderAgentConfig, description="Leader Agent設定")
    members: list[TeamMemberAgentConfig] = Field(
        default_factory=list, description="Member Agent設定リスト（0件の場合はLeader Agent単独実行）"
    )

    @field_validator("members")
    @classmethod
    def validate_member_count(cls, v: list[TeamMemberAgentConfig], info: Any) -> list[TeamMemberAgentConfig]:
        max_count = info.data.get("max_concurrent_members", 15)
        if len(v) > max_count:
            raise ValueError(
                f"Too many members: {len(v)} > {max_count}. Adjust max_concurrent_members or reduce member count."
            )
        return v

    @field_validator("members")
    @classmethod
    def validate_unique_agent_names(cls, v: list[TeamMemberAgentConfig]) -> list[TeamMemberAgentConfig]:
        names = [m.agent_name for m in v]
        if len(names) != len(set(names)):
            duplicates = [name for name in names if names.count(name) > 1]
            raise ValueError(f"Duplicate agent_name detected: {duplicates}")
        return v

    @field_validator("members")
    @classmethod
    def validate_unique_tool_names(cls, v: list[TeamMemberAgentConfig]) -> list[TeamMemberAgentConfig]:
        tool_names = [m.get_tool_name() for m in v]
        if len(tool_names) != len(set(tool_names)):
            duplicates = [name for name in tool_names if tool_names.count(name) > 1]
            raise ValueError(f"Duplicate tool_name detected: {duplicates}")
        return v


def load_team_config(toml_path: Path, workspace: Path | None = None) -> TeamConfig:
    """チーム設定TOML読み込み（参照形式サポート）

    .. deprecated:: T078
        新規コードではConfigurationManager.load_team_settings()を使用してください。
        このAPIは段階的移行期間中は維持されます（既存コードへの影響を最小化）。

    .. note:: T078移行完了
        内部実装は新しいConfigurationManager.load_team_settings()を使用しています。
        外部APIは変更なしのため、既存コードは動作し続けます。

    Args:
        toml_path: Team設定TOMLファイルパス（相対パスはworkspaceから解釈）
        workspace: Member Agent config解決の起点パス（未指定時は明示的エラー）

    Returns:
        TeamConfig instance

    Raises:
        WorkspacePathNotSpecifiedError: workspace未指定かつ環境変数未設定の場合（Article 9準拠）
        FileNotFoundError: 参照先ファイルが見つからない場合
    """
    # workspace未指定時は環境変数を確認（Article 9準拠 - T078 fix）
    if workspace is None:
        from mixseek.exceptions import WorkspacePathNotSpecifiedError
        from mixseek.utils.env import get_workspace_path

        try:
            # 環境変数またはCLI引数からworkspaceを取得
            workspace = get_workspace_path(cli_arg=None)
        except WorkspacePathNotSpecifiedError:
            # 環境変数未設定の場合は明示的エラー
            raise

    # T078移行: 新しいConfigurationManagerを使用
    from mixseek.config.manager import ConfigurationManager

    manager = ConfigurationManager(workspace=workspace)
    team_settings = manager.load_team_settings(toml_path)

    # 新しいTeamSettingsを既存のTeamConfigに変換（段階的移行: 公開API維持のため）
    return team_settings_to_team_config(team_settings)


def team_settings_to_team_config(team_settings: TeamSettings) -> TeamConfig:
    """TeamSettings（新）をTeamConfig（既存API）に変換（T078移行ヘルパー）。

    ConfigurationManager.load_team_settings()で読み込んだTeamSettingsを
    既存のLeader Agent公開APIで使用できるTeamConfigに変換します。

    Note:
        内部実装はモダン化済み（ConfigurationManager使用）。
        外部APIは既存形式を維持（段階的移行期間中）。

    Args:
        team_settings: TeamSettings instance（from ConfigurationManager）

    Returns:
        TeamConfig instance（既存公開API形式）

    Examples:
        >>> from mixseek.config.manager import ConfigurationManager
        >>> from mixseek.config.schema import TeamSettings
        >>> manager = ConfigurationManager(workspace=Path("/workspace"))
        >>> team_settings = manager.load_team_settings(Path("team.toml"))
        >>> team_config = team_settings_to_team_config(team_settings)
        >>> agent = create_leader_agent(team_config, member_agents)
    """
    # Leader設定を変換（team_settings.leaderは必ず存在する）
    leader_config = LeaderAgentConfig(**team_settings.leader)

    # Member設定リストを変換
    # MemberAgentSettingsをTeamMemberAgentConfigに変換
    # Note: plugin/tool_settingsはTeamMemberAgentConfigに存在しないため除外
    member_configs: list[TeamMemberAgentConfig] = [
        TeamMemberAgentConfig(
            **member_settings.model_dump(exclude={"plugin", "tool_settings"}),
            config=None,  # 参照形式は使用しない
        )
        for member_settings in team_settings.members
    ]

    # TeamConfigを構築
    return TeamConfig(
        team_id=team_settings.team_id,
        team_name=team_settings.team_name,
        max_concurrent_members=team_settings.max_concurrent_members,
        leader=leader_config,
        members=member_configs,
    )
