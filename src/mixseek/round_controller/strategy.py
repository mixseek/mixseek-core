"""ExecutionStrategy - team / workflow 両モードを統一する実行戦略。

`RoundController` は 1 ラウンドの「Member 生成 + Leader 実行」または「WorkflowEngine 実行」を
本モジュールの strategy 経由で行う。これにより以下を満たす:

- ラウンド管理 (Evaluator / DuckDB / 進捗ファイル / 終了判定) を team/workflow で共通化
- team mode 既存挙動の完全保持（`LeaderStrategy` は L286-310 をそのまま carve-out）
- workflow mode は `WorkflowStrategy` 経由で `WorkflowEngine` に委譲

Note:
    `create_leader_agent`, `MemberAgentFactory`, `member_settings_to_config`,
    `WorkflowEngine` は **module-level import** で取り込む。テストは
    ``mixseek.round_controller.strategy.<symbol>`` を patch するため、
    関数内ローカル import に変更すると patch が効かなくなる。
"""

from pathlib import Path
from typing import Protocol, runtime_checkable

from mixseek.agents.leader.agent import create_leader_agent
from mixseek.agents.leader.config import team_settings_to_team_config
from mixseek.agents.leader.dependencies import TeamDependencies
from mixseek.agents.member.factory import MemberAgentFactory
from mixseek.config.member_agent_loader import member_settings_to_config
from mixseek.config.schema import TeamSettings, WorkflowSettings
from mixseek.workflow.engine import WorkflowEngine
from mixseek.workflow.models import StrategyResult

__all__ = [
    "ExecutionStrategy",
    "LeaderStrategy",
    "WorkflowStrategy",
]


@runtime_checkable
class ExecutionStrategy(Protocol):
    """team / workflow を統一する実行戦略 Protocol。

    `RoundController._execute_single_round` から呼ばれ、`StrategyResult` を返す。
    返値の 2 フィールド (`submission_content`, `all_messages`) は team mode の
    `result.output` / `result.all_messages()` と完全互換。
    """

    async def execute(self, user_prompt: str, deps: TeamDependencies) -> StrategyResult:
        """1 ラウンドを実行し `StrategyResult` を返す。"""
        ...


class LeaderStrategy:
    """team mode の Leader/Member 実行を担う ExecutionStrategy 実装。

    既存 `RoundController._execute_single_round` の L286-310 を carve-out したもの。
    `MemberAgentFactory.create_agent` で member 辞書を構築し、`create_leader_agent`
    で Leader Agent を生成、`leader_agent.run(user_prompt, deps=deps)` を実行する。
    """

    def __init__(self, team_settings: TeamSettings, workspace: Path) -> None:
        self._team_settings = team_settings
        self._team_config = team_settings_to_team_config(team_settings)
        self._workspace = workspace

    async def execute(self, user_prompt: str, deps: TeamDependencies) -> StrategyResult:
        member_agents: dict[str, object] = {}
        for member_settings in self._team_settings.members:
            member_config = member_settings_to_config(
                member_settings,
                agent_data=None,
                workspace=self._workspace,
            )
            member_agent = MemberAgentFactory.create_agent(member_config)
            member_agents[member_settings.agent_name] = member_agent

        leader_agent = create_leader_agent(self._team_config, member_agents)
        result = await leader_agent.run(user_prompt, deps=deps)
        return StrategyResult(
            submission_content=result.output,
            all_messages=result.all_messages(),
        )


class WorkflowStrategy:
    """workflow mode の `WorkflowEngine` を `StrategyResult` で包む ExecutionStrategy 実装。

    `WorkflowEngine.run` の `WorkflowResult` から `submission_content` / `all_messages`
    のみを取り出して `StrategyResult` に詰め替える。`total_usage` は team mode との
    互換性維持のため `StrategyResult` には伝搬しない（観測は workflow パッケージ側）。
    """

    def __init__(self, workflow_settings: WorkflowSettings, workspace: Path) -> None:
        self._engine = WorkflowEngine(workflow_settings, workspace=workspace)

    async def execute(self, user_prompt: str, deps: TeamDependencies) -> StrategyResult:
        wf_result = await self._engine.run(user_prompt, deps)
        return StrategyResult(
            submission_content=wf_result.submission_content,
            all_messages=wf_result.all_messages,
        )
