"""Leader Agent実装

Agent Delegationパターンによる動的なMember Agent選択・実行。
Leader Agentは単一ラウンド内の記録のみを担当します。

重要な設計:
- Agent Delegation: LLMがタスクを分析し、適切なMember AgentをToolで選択
- 前ラウンド非依存: Leader Agentは単一ラウンド内のみ動作
- 構造化データ記録: Round Controllerが整形処理を担当

References:
    - Spec: specs/008-leader/spec.md (FR-031-034)
    - Research: specs/008-leader/research.md (Section 1)
"""

from collections.abc import Mapping
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings

from mixseek.agents.leader.config import TeamConfig
from mixseek.agents.leader.dependencies import TeamDependencies
from mixseek.agents.leader.tools import register_member_tools
from mixseek.core.auth import create_authenticated_model

DEFAULT_LEADER_SYSTEM_INSTRUCTION = """
あなたは研究チームのリーダーエージェントです。
タスクを分析し、利用可能なMember Agentから適切なものを選択して実行してください。

戦略:
- タスクの複雑度を評価（単純/中程度/複雑）
- 必要な専門性を特定
- 最小限のMember Agentを選択（リソース効率優先）
- 必要に応じて複数のAgentを順次実行

各Member Agentの詳細はToolの説明を参照してください。
"""


def create_leader_agent(team_config: TeamConfig, member_agents: Mapping[str, Any]) -> Agent[TeamDependencies, str]:
    """Leader Agent作成

    Args:
        team_config: チーム設定
        member_agents: Member Agentマップ（agent_name -> Agent）

    Returns:
        Leader Agentインスタンス（Agent Delegation対応）
    """
    leader_config = team_config.leader

    # system_instruction取得（FR-027, FR-030）
    system_instruction: str | None = DEFAULT_LEADER_SYSTEM_INSTRUCTION
    if leader_config.system_instruction is not None:
        system_instruction = leader_config.system_instruction
        # 空文字列の場合はNoneに変換（デフォルト無効化）
        if system_instruction == "":
            system_instruction = None

    # system_prompt取得（FR-032、アドバンスド設定）
    system_prompt = leader_config.system_prompt

    # Leader Agent model取得（issue #51準拠）
    model_id = leader_config.model

    # 認証済みモデル作成（Vertex AI対応、DRY準拠）
    authenticated_model = create_authenticated_model(model_id)

    # ModelSettings作成（全パラメータ統合）
    model_settings: ModelSettings = {}
    if leader_config.temperature is not None:
        model_settings["temperature"] = leader_config.temperature
    if leader_config.max_tokens is not None:
        model_settings["max_tokens"] = leader_config.max_tokens
    if leader_config.stop_sequences is not None:
        model_settings["stop_sequences"] = leader_config.stop_sequences
    if leader_config.top_p is not None:
        model_settings["top_p"] = leader_config.top_p
    if leader_config.seed is not None:
        model_settings["seed"] = leader_config.seed
    if leader_config.timeout_seconds is not None:
        model_settings["timeout"] = float(leader_config.timeout_seconds)

    # retries設定を取得
    retries = leader_config.max_retries

    # Leader Agent作成（instructionsとsystem_promptを併用可能）
    # 注意: Pydantic AI AgentはNone値のsystem_promptを受け付けない（TypeError発生）
    # そのため、system_promptがNoneの場合は引数として渡さず、省略する必要がある
    if system_prompt is not None:
        leader_agent = Agent(
            authenticated_model,
            deps_type=TeamDependencies,
            instructions=system_instruction,
            system_prompt=system_prompt,
            model_settings=model_settings,
            retries=retries,
        )
    else:
        leader_agent = Agent(
            authenticated_model,
            deps_type=TeamDependencies,
            instructions=system_instruction,
            model_settings=model_settings,
            retries=retries,
        )

    # Member Agent Toolを動的登録（FR-032）
    register_member_tools(leader_agent, team_config, member_agents)

    return leader_agent
