"""Member Agent Tool動的生成

TOML設定からMember Agent ToolをLeader Agentに動的登録します。
Pydantic AIのAgent Delegationパターンに準拠。

References:
    - Spec: specs/008-leader/spec.md (FR-031-034)
    - Research: specs/008-leader/research.md (Section 1, 3)
    - Data Model: specs/008-leader/data-model.md (Section 3-4)
"""

from collections.abc import Callable, Coroutine, Mapping
from datetime import UTC, datetime
from typing import Any

from pydantic_ai import Agent, RunContext, RunUsage

from mixseek.agents.leader.config import TeamConfig, TeamMemberAgentConfig
from mixseek.agents.leader.dependencies import TeamDependencies
from mixseek.agents.leader.models import MemberSubmission
from mixseek.agents.member.base import BaseMemberAgent


def register_member_tools(
    leader_agent: Agent[TeamDependencies, str],
    team_config: TeamConfig,
    member_agents: Mapping[str, Any],
) -> None:
    """TOML設定からMember Agent ToolをLeader Agentに登録（FR-032）

    各Member AgentをLeader AgentのToolとして動的に登録します。
    Pydantic AIのAgent Delegationパターンに準拠し、ctx.usageを統合します。

    Args:
        leader_agent: Leader Agentインスタンス
        team_config: チーム設定
        member_agents: Member Agentマップ（agent_name -> Agent）

    Raises:
        KeyError: member_agentsにagent_nameが存在しない
    """
    for member_config in team_config.members:
        tool_name = member_config.get_tool_name()
        member_agent = member_agents[member_config.agent_name]

        # Toolクロージャー生成（Agent Delegation標準パターン）
        def make_tool_func(
            mc: TeamMemberAgentConfig,
            ma: Any,  # Agent | BaseMemberAgent
        ) -> Callable[[RunContext[TeamDependencies], str], Coroutine[Any, Any, str]]:
            """Tool関数を生成（クロージャー）

            Args:
                mc: Member Agent設定
                ma: Member Agentインスタンス

            Returns:
                Tool関数（async）
            """

            async def tool_func(ctx: RunContext[TeamDependencies], task: str) -> str:
                """Member Agentを実行するTool関数

                Args:
                    ctx: RunContext（deps, usage含む）
                    task: Member Agentに渡すタスク

                Returns:
                    Member Agentの応答テキスト

                Raises:
                    ValueError: タスクが空の場合
                """
                if not task.strip():
                    raise ValueError("Task cannot be empty")

                start_time = datetime.now(UTC)

                # Member Agent実行（BaseMemberAgentまたはPydantic AI Agent）
                if isinstance(ma, BaseMemberAgent):
                    # BaseMemberAgent（WebSearchTool等が初期化済み）
                    result_obj = await ma.execute(task)
                    content = result_obj.content
                    all_messages = result_obj.all_messages  # FR-034: Member Agent message history
                    # Issue #59: MemberAgentResult.status を MemberSubmission に伝播
                    status = result_obj.status.value.upper()  # "SUCCESS" or "ERROR"
                    error_message = result_obj.error_message
                    usage = RunUsage(
                        input_tokens=result_obj.usage_info.get("input_tokens", 0) if result_obj.usage_info else 0,
                        output_tokens=result_obj.usage_info.get("output_tokens", 0) if result_obj.usage_info else 0,
                        requests=1,
                    )
                else:
                    # Pydantic AI Agent（FR-034: ctx.usage統合）
                    result_obj = await ma.run(task, deps=ctx.deps, usage=ctx.usage)
                    content = str(result_obj.output)
                    all_messages = result_obj.all_messages()  # FR-034: Member Agent message history
                    # Pydantic AI Agent にはエラー概念がないため常に SUCCESS
                    status = "SUCCESS"
                    error_message = None
                    usage = result_obj.usage()

                end_time = datetime.now(UTC)
                execution_time_ms = (end_time - start_time).total_seconds() * 1000

                # MemberSubmission記録
                submission = MemberSubmission(
                    agent_name=mc.agent_name,
                    agent_type=mc.agent_type,
                    content=content,
                    status=status,  # Issue #59: result_obj.status から取得
                    error_message=error_message,  # Issue #59: エラーメッセージを伝播
                    usage=usage,
                    execution_time_ms=execution_time_ms,
                    timestamp=end_time,
                    all_messages=all_messages,  # FR-034: Include Member Agent message history
                )
                ctx.deps.submissions.append(submission)

                return content

            # Tool関数のメタデータ設定
            tool_func.__name__ = tool_name
            tool_func.__doc__ = mc.tool_description

            return tool_func

        # Tool登録
        tool = make_tool_func(member_config, member_agent)
        leader_agent.tool(tool)
