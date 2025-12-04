"""Member Agent configuration loader.

This module provides utilities for loading and validating Member Agent
configurations from TOML files with environment variable overrides.

.. note:: T088移行完了
    内部実装はConfigurationManager.load_member_settings()を使用しています。
    詳細設定（retry_config, usage_limits等）はTOML [agent]セクションから直接読み込みます。
    Note: これらはMemberAgentSettingsスキーマに含まれないため、別途処理が必要です。
    外部APIはT088移行後も変更なしで使用可能です。
"""

import tomllib
from pathlib import Path
from typing import TYPE_CHECKING, Any

from mixseek.models.member_agent import (
    EnvironmentConfig,
    MemberAgentConfig,
    ToolSettings,
)

if TYPE_CHECKING:
    from mixseek.config.schema import MemberAgentSettings

__all__ = ["MemberAgentLoader", "EnvironmentConfig", "member_settings_to_config"]


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
        デフォルト値を読み込む際に使用されます（Article 10 DRY準拠）。
    """
    # agent_dataがNoneの場合は空dictを使用
    if agent_data is None:
        agent_data = {}

    # system_instructionフィールドの変換
    # settings.system_instructionが未定義（None）の場合、デフォルトTOMLから読み込む（FR-005）
    if settings.system_instruction is None:
        # agent_type を bundled agent name にマッピング
        from typing import Literal

        agent_type_map: dict[str, Literal["plain", "web-search", "code-exec"]] = {
            "plain": "plain",
            "web_search": "web-search",
            "code_execution": "code-exec",
        }
        bundled_name = agent_type_map.get(settings.agent_type)

        if bundled_name is None:
            # カスタムエージェント等、デフォルトTOMLが存在しない場合は空文字列
            system_instruction_text = ""
        else:
            # 標準エージェントの場合、BundledMemberAgentLoaderで読み込み（Article 10 DRY準拠）
            from mixseek.config.bundled_member_agents import BundledMemberAgentLoader

            loader = BundledMemberAgentLoader(workspace=workspace)
            bundled_settings = loader.load(bundled_name)  # 例外発生時はそのまま伝播（Article 9準拠）
            system_instruction_text = bundled_settings.system_instruction or ""  # str | None → str
    else:
        system_instruction_text = settings.system_instruction

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

    .. note:: T088移行完了
        内部実装はConfigurationManagerを使用するように更新されました。
        外部APIは変更なしで使用可能です（既存コードへの影響なし）。
    """

    @staticmethod
    def load_config(toml_path: Path) -> MemberAgentConfig:
        """Load and validate Member Agent configuration from TOML file.

        .. note:: T088移行完了
            内部実装は新しいConfigurationManager.load_member_settings()を使用しています。
            詳細設定（retry_config, usage_limits等）はTOML [agent]セクションから別途読み込みます。
            Note: これらはMemberAgentSettingsスキーマに含まれないため、直接読み込みが必要です。
            外部APIはT088移行後も変更なしで使用可能です。

        Args:
            toml_path: Path to TOML configuration file

        Returns:
            Validated MemberAgentConfig instance

        Raises:
            FileNotFoundError: If configuration file does not exist
            ValueError: If configuration is invalid
        """
        # T088移行: 新しいConfigurationManagerを使用
        from mixseek.config.manager import ConfigurationManager
        from mixseek.utils.env import get_workspace_path

        # T088 fix: 相対パスを絶対パスに変換
        # 例: configs/agents/plain_agent.toml → /path/to/repo/configs/agents/plain_agent.toml
        resolved_path = toml_path.resolve()

        if not resolved_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {toml_path} (resolved: {resolved_path})")

        # Article 9 compliance: Explicit workspace specification required
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
