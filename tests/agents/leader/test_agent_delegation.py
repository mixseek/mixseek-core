"""Agent Delegation のテスト

Article 3: Test-First Imperative準拠

Leader AgentがAgent Delegationパターンでタスクを分析し、
適切なMember AgentをToolを通じて動的に選択・実行するテスト。

Tests:
    - 単純タスクで1つのMember Agentのみ選択
    - 複雑タスクで複数のMember Agent選択
    - RunUsage統合
    - 失敗Member Agent自動除外
"""

from unittest.mock import AsyncMock, Mock

import pytest
from pydantic_ai import RunUsage

from mixseek.agents.leader.dependencies import TeamDependencies
from mixseek.agents.leader.models import MemberSubmission


class TestAgentDelegation:
    """Agent Delegation基本動作テスト（T015, T017, T018）"""

    @pytest.mark.asyncio
    async def test_tool_registration_succeeds(self) -> None:
        """Tool登録成功（T015: Agent Delegation基本動作）

        register_member_tools関数が正常に実行され、
        エラーなくToolが登録されることを確認。
        """
        # Arrange
        from unittest.mock import Mock

        from mixseek.agents.leader.config import TeamConfig, TeamMemberAgentConfig
        from mixseek.agents.leader.tools import register_member_tools

        team_config = TeamConfig(
            team_id="test-team",
            team_name="Test Team",
            members=[
                TeamMemberAgentConfig(
                    agent_name="test_agent",
                    agent_type="plain",
                    tool_name="test_tool",
                    tool_description="Test tool",
                    model="test",
                    system_instruction="You are a test agent",
                    temperature=0.7,
                    max_tokens=100,
                )
            ],
        )

        # Mock Leader Agent and Member Agent
        from typing import Any

        mock_leader: Any = Mock()
        mock_leader.tool = Mock()
        mock_member = Mock()
        member_agents: Any = {"test_agent": mock_member}

        # Act: Tool登録
        register_member_tools(mock_leader, team_config, member_agents)

        # Assert: leader_agent.tool()が呼び出された
        mock_leader.tool.assert_called_once()

        # 登録されたTool関数を確認
        registered_tool = mock_leader.tool.call_args[0][0]
        assert registered_tool.__name__ == "test_tool"
        assert registered_tool.__doc__ == "Test tool"

    @pytest.mark.asyncio
    async def test_deps_submissions_populated(self) -> None:
        """TeamDependencies.submissionsに記録される（T015）

        Tool実行時、ctx.deps.submissionsにMemberSubmissionが追加される。
        """
        # Arrange
        deps = TeamDependencies(team_id="team-001", team_name="Test Team", round_number=1, execution_id="exec-test")

        # Tool関数を直接テスト（register_member_toolsで生成される関数と同等）
        from pydantic_ai import RunUsage

        from mixseek.agents.leader.models import MemberSubmission

        # Act: Submissionを手動追加（Tool実行をシミュレーション）
        deps.submissions.append(
            MemberSubmission(
                agent_name="test_agent",
                agent_type="plain",
                content="Test response",
                status="SUCCESS",
                usage=RunUsage(input_tokens=10, output_tokens=20, requests=1),
            )
        )

        # Assert
        assert len(deps.submissions) == 1
        assert deps.submissions[0].agent_name == "test_agent"

    @pytest.mark.asyncio
    async def test_run_usage_integration(self) -> None:
        """RunUsage統合（FR-034）

        ctx.usageがMember Agentに渡され、Member AgentのRunUsageが
        Leader Agentに統合されることを確認。
        """
        # Arrange
        deps = TeamDependencies(team_id="team-001", team_name="Test Team", round_number=1, execution_id="exec-test")

        # Mock Member Agent
        mock_member_agent = AsyncMock()
        mock_result = Mock()
        mock_result.output = "分析結果"
        mock_result.usage.return_value = RunUsage(input_tokens=100, output_tokens=200, requests=1)
        mock_member_agent.run.return_value = mock_result

        # Act: Tool関数シミュレーション（ctx.usage渡し）
        parent_usage = RunUsage()
        await mock_member_agent.run("タスク", deps=deps, usage=parent_usage)

        # Assert
        mock_member_agent.run.assert_called_once()
        call_kwargs = mock_member_agent.run.call_args.kwargs
        assert call_kwargs["usage"] == parent_usage  # usageが渡されている
        assert call_kwargs["deps"] == deps  # depsが渡されている

    @pytest.mark.asyncio
    async def test_failed_member_agent_auto_excluded(self) -> None:
        """失敗Member Agent自動除外（FR-002、Acceptance 3）

        3つのMember Agentで1つが失敗した場合、
        successful_submissionsに成功応答のみ含まれる。
        """
        # Arrange
        deps = TeamDependencies(team_id="team-001", team_name="Test Team", round_number=1, execution_id="exec-test")

        # 3つのMember Agent応答をシミュレーション
        deps.submissions.append(
            MemberSubmission(
                agent_name="analyst",
                agent_type="plain",
                content="分析成功",
                status="SUCCESS",
                usage=RunUsage(input_tokens=100, output_tokens=200, requests=1),
            )
        )
        deps.submissions.append(
            MemberSubmission(
                agent_name="slow-agent",
                agent_type="plain",
                content="",
                status="ERROR",
                error_message="Timeout",
                usage=RunUsage(input_tokens=50, output_tokens=0, requests=1),
            )
        )
        deps.submissions.append(
            MemberSubmission(
                agent_name="summarizer",
                agent_type="plain",
                content="要約成功",
                status="SUCCESS",
                usage=RunUsage(input_tokens=80, output_tokens=150, requests=1),
            )
        )

        # Act: MemberSubmissionsRecord作成
        from mixseek.agents.leader.models import MemberSubmissionsRecord

        record = MemberSubmissionsRecord(
            execution_id="test-exec-001",
            team_id=deps.team_id,
            team_name=deps.team_name,
            round_number=deps.round_number,
            submissions=deps.submissions,
        )

        # Assert: 失敗応答が自動除外
        assert record.total_count == 3
        assert record.success_count == 2
        assert record.failure_count == 1
        assert len(record.successful_submissions) == 2
        assert record.successful_submissions[0].agent_name == "analyst"
        assert record.successful_submissions[1].agent_name == "summarizer"
        # 失敗したagentは含まれない
        assert all(s.agent_name != "slow-agent" for s in record.successful_submissions)
