"""Member Agent configuration loader.

This module provides utilities for loading and validating Member Agent
configurations from TOML files with environment variable overrides.

内部実装はConfigurationManager.load_member_settings()を使用しています。
詳細設定（retry_config, usage_limits等）はTOML [agent]セクションから直接読み込みます。
Note: これらはMemberAgentSettingsスキーマに含まれないため、別途処理が必要です。
"""

import tomllib
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from mixseek.models.member_agent import (
    EnvironmentConfig,
    MemberAgentConfig,
    ToolSettings,
)

if TYPE_CHECKING:
    from mixseek.config.schema import MemberAgentSettings

__all__ = ["MemberAgentLoader", "EnvironmentConfig", "member_settings_to_config"]


def _resolve_bundled_system_instruction(
    agent_type: str,
    system_instruction: str | None,
    workspace: Path | None,
) -> str:
    """bundled agent の system_instruction を解決（team / workflow 共通ヘルパー）。

    Args:
        agent_type: agent_type 文字列（"plain" / "web_search" / "code_execution" / "custom" 等）
        system_instruction: 明示指定された system_instruction（未指定なら None）
        workspace: workspace パス（bundled TOML 解決に使用、省略可）

    Returns:
        解決された system_instruction 文字列（常に str、None が返ることはない）

    Note:
        - system_instruction が非 None ならそのまま返す
        - None かつ agent_type が {plain, web_search, code_execution} なら bundled TOML から読み込む
        - それ以外（custom 等 bundled 未提供）は空文字列
    """
    if system_instruction is not None:
        return system_instruction

    agent_type_map: dict[str, Literal["plain", "web-search", "code-exec"]] = {
        "plain": "plain",
        "web_search": "web-search",
        "code_execution": "code-exec",
    }
    bundled_name = agent_type_map.get(agent_type)
    if bundled_name is None:
        return ""

    # 遅延 import（循環回避）
    from mixseek.config.bundled_member_agents import BundledMemberAgentLoader

    loader = BundledMemberAgentLoader(workspace=workspace)
    bundled_settings = loader.load(bundled_name)
    return bundled_settings.system_instruction or ""


def member_settings_to_config(
    settings: "MemberAgentSettings",
    agent_data: dict[str, Any] | None = None,
    workspace: Path | None = None,
) -> MemberAgentConfig:
    """MemberAgentSettings → MemberAgentConfig変換（公開API）.

    Args:
        settings: MemberAgentSettings instance
        agent_data: TOMLの[agent]セクションの生データ（オプション設定用、Noneの場合は空dict）
                   Note: Issue #146完全対応により、plugin/tool_settingsはsettingsから直接取得
        workspace: Workspace path (used for loading bundled agent system_instruction, optional)

    Returns:
        MemberAgentConfig instance

    Note:
        この関数は他のモジュールから再利用可能です。
        Issue #146完全対応: plugin, tool_settingsはMemberAgentSettingsから直接読み込み
        agent_dataがNoneの場合、すべてのオプション設定はデフォルト値が使用されます。
        workspace引数は、system_instructionがNoneの場合にbundled agent TOMLから
        デフォルト値を読み込む際に使用されます。
    """
    # agent_dataがNoneの場合は空dictを使用
    if agent_data is None:
        agent_data = {}

    # bundled system_instruction 解決は team/workflow 共通ヘルパーに委譲
    system_instruction_text = _resolve_bundled_system_instruction(
        settings.agent_type, settings.system_instruction, workspace
    )

    # Issue #146完全対応: plugin, tool_settingsはMemberAgentSettingsから直接取得
    # TOMLのteam.membersセクションで[[team.members.plugin]]として定義可能
    plugin = settings.plugin

    # tool_settings: agent_dataが優先、なければsettingsから（Noneも許容）
    tool_settings_data = agent_data.get("tool_settings", {})
    tool_settings: ToolSettings | None
    if tool_settings_data:
        tool_settings = ToolSettings(**tool_settings_data)
    else:
        tool_settings = settings.tool_settings  # None も許容

    # metadata: MemberAgentSettingsから取得し、agent_dataでマージ
    metadata = dict(settings.metadata)  # コピーを作成
    if agent_data:
        agent_metadata = agent_data.get("metadata", {})
        metadata.update(agent_metadata)

    # カスタムエージェント向け: tool_settingsの内容をmetadataにもコピー
    # 一部のカスタムエージェントはmetadata["tool_settings"]から追加設定を読み込む
    if settings.tool_settings is not None:
        # ToolSettingsをdictに変換してmetadataに追加
        if "tool_settings" not in metadata:
            metadata["tool_settings"] = settings.tool_settings.model_dump(exclude_none=True)

    # description（TOMLから読み込み、存在しなければ空文字列）
    description = agent_data.get("description", "")

    return MemberAgentConfig(
        name=settings.agent_name,
        type=settings.agent_type,
        model=settings.model,
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
        timeout_seconds=settings.timeout_seconds,
        max_retries=settings.max_retries,
        stop_sequences=settings.stop_sequences,
        top_p=settings.top_p,
        seed=settings.seed,
        system_instruction=system_instruction_text,
        system_prompt=settings.system_prompt,
        description=description,
        tool_settings=tool_settings,
        plugin=plugin,
        metadata=metadata,
    )


class MemberAgentLoader:
    """Loader for Member Agent configurations and environment settings.

    内部実装はConfigurationManagerを使用するように更新されました。
    外部APIは変更なしで使用可能です（既存コードへの影響なし）。
    """

    @staticmethod
    def load_config(toml_path: Path) -> MemberAgentConfig:
        """Load and validate Member Agent configuration from TOML file.

        内部実装はConfigurationManager.load_member_settings()を使用しています。
        詳細設定（retry_config, usage_limits等）はTOML [agent]セクションから別途読み込みます。
        Note: これらはMemberAgentSettingsスキーマに含まれないため、直接読み込みが必要です。

        Args:
            toml_path: Path to TOML configuration file

        Returns:
            Validated MemberAgentConfig instance

        Raises:
            FileNotFoundError: If configuration file does not exist
            ValueError: If configuration is invalid
        """
        # 新しいConfigurationManagerを使用
        from mixseek.config.manager import ConfigurationManager
        from mixseek.utils.env import get_workspace_path

        # 相対パスを絶対パスに変換
        # 例: configs/agents/plain_agent.toml → /path/to/repo/configs/agents/plain_agent.toml
        resolved_path = toml_path.resolve()

        if not resolved_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {toml_path} (resolved: {resolved_path})")

        # Explicit workspace specification required
        # Workspace must be provided via MIXSEEK_WORKSPACE environment variable
        # No implicit fallbacks allowed - fail fast if not specified
        workspace = get_workspace_path(cli_arg=None)

        # ConfigurationManagerを使用してMemberAgentSettingsを読み込む
        config_manager = ConfigurationManager(workspace=workspace)
        member_settings = config_manager.load_member_settings(resolved_path)

        # 詳細設定（retry_config, usage_limits等）を別途読み込み
        # Note: これらはMemberAgentSettingsスキーマに含まれないため、TOMLから直接取得
        with open(resolved_path, "rb") as f:
            toml_data = tomllib.load(f)

        if "agent" not in toml_data:
            raise ValueError(f"Invalid member agent config: missing 'agent' section in {resolved_path}")

        agent_data = toml_data["agent"]

        # MemberAgentSettings + agent_data → MemberAgentConfig変換（後方互換性）
        return member_settings_to_config(member_settings, agent_data, workspace=workspace)

    @staticmethod
    def load_environment() -> EnvironmentConfig:
        """Load environment configuration with default settings.

        Returns:
            EnvironmentConfig instance with environment variables applied
        """
        return EnvironmentConfig()
