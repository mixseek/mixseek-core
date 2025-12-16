"""Member Agent Tool動的生成のテスト

Article 3: Test-First Imperative準拠

TOML設定からMember Agent ToolをLeader Agentに動的登録するテスト。

Tests:
    - Tool動的生成
    - tool_name自動生成
    - tool_description設定
    - Tool実行でMember Agent呼び出し
"""

from unittest.mock import Mock

import pytest

from mixseek.agents.leader.config import TeamConfig, TeamMemberAgentConfig
from mixseek.agents.leader.tools import register_member_tools


class TestRegisterMemberTools:
    """register_member_tools関数のテスト（FR-032）"""

    def test_register_tools_from_config(self) -> None:
        """TOML設定からTool動的生成"""
        # Arrange
        team_config = TeamConfig(
            team_id="team-001",
            team_name="Test Team",
            members=[
                TeamMemberAgentConfig(
                    agent_name="analyst",
                    agent_type="plain",
                    tool_name="delegate_to_analyst",
                    tool_description="論理的な分析を実行します",
                    model="gemini-2.5-flash-lite",
                    system_instruction="アナリスト",
                    temperature=0.7,
                    max_tokens=2048,
                )
            ],
        )

        # Mock Agentを使用（APIキー不要）
        from typing import Any

        leader_agent: Any = Mock()
        leader_agent.tool = Mock()
        member_agents: Any = {"analyst": Mock()}

        # Act
        register_member_tools(leader_agent, team_config, member_agents)

        # Assert
        # leader_agent.tool()が呼び出されたことを確認
        leader_agent.tool.assert_called_once()

        # 登録されたTool関数を取得
        registered_tool = leader_agent.tool.call_args[0][0]
        assert registered_tool.__name__ == "delegate_to_analyst"
        assert registered_tool.__doc__ == "論理的な分析を実行します"

    def test_tool_name_auto_generation(self) -> None:
        """tool_name自動生成（Edge Case: 未設定時）"""
        # Arrange
        team_config = TeamConfig(
            team_id="team-001",
            team_name="Test Team",
            members=[
                TeamMemberAgentConfig(
                    agent_name="analyst",
                    agent_type="plain",
                    # tool_name未設定
                    tool_description="分析",
                    model="gemini-2.5-flash-lite",
                    system_instruction="test",
                    temperature=0.7,
                    max_tokens=2048,
                )
            ],
        )

        # Act
        tool_name = team_config.members[0].get_tool_name()

        # Assert
        assert tool_name == "delegate_to_analyst"  # agent_nameから自動生成

    @pytest.mark.asyncio
    async def test_tool_execution_calls_member_agent(self) -> None:
        """Tool実行でMember Agent呼び出し"""
        # このテストは実際のTool実装後に有効化
        pytest.skip("Tool実装後に有効化（T020完了後）")


class TestToolFuncStatusPropagation:
    """tool_func の status/error_message 伝播テスト（Issue #59）

    BaseMemberAgent.execute() が返す MemberAgentResult.status が
    MemberSubmission.status に正しく伝播されることを確認する。
    """

    @pytest.mark.asyncio
    async def test_propagates_error_status_from_base_member_agent(self) -> None:
        """BaseMemberAgent が ERROR を返した場合、MemberSubmission.status も ERROR になる"""
        from typing import Any
        from unittest.mock import AsyncMock

        from mixseek.agents.leader.dependencies import TeamDependencies
        from mixseek.agents.member.base import BaseMemberAgent
        from mixseek.models.member_agent import MemberAgentResult, ResultStatus

        # Arrange: ERROR を返す BaseMemberAgent をモック
        mock_member_agent = AsyncMock(spec=BaseMemberAgent)
        mock_member_agent.execute.return_value = MemberAgentResult(
            status=ResultStatus.ERROR,
            content="",
            agent_name="test_agent",
            agent_type="plain",
            error_message="Test error message",
            usage_info={"input_tokens": 10, "output_tokens": 0},
            all_messages=None,
        )

        team_config = TeamConfig(
            team_id="team-001",
            team_name="Test Team",
            members=[
                TeamMemberAgentConfig(
                    agent_name="test_agent",
                    agent_type="plain",
                    tool_name="delegate_to_test_agent",
                    tool_description="Test agent",
                    model="gemini-2.5-flash-lite",
                    system_instruction="test",
                    temperature=0.7,
                    max_tokens=2048,
                )
            ],
        )

        # Mock leader agent to capture the registered tool
        leader_agent: Any = Mock()
        registered_tools: list[Any] = []
        leader_agent.tool = lambda func: registered_tools.append(func)

        member_agents: Any = {"test_agent": mock_member_agent}

        # Act: Tool を登録
        register_member_tools(leader_agent, team_config, member_agents)

        # 登録された tool_func を取得
        assert len(registered_tools) == 1
        tool_func = registered_tools[0]

        # Mock RunContext with TeamDependencies
        deps = TeamDependencies(team_id="team-001", team_name="Test Team", round_number=1)
        mock_ctx: Any = Mock()
        mock_ctx.deps = deps

        # Act: tool_func を実行
        await tool_func(mock_ctx, "test task")

        # Assert: submission.status == "ERROR", submission.error_message が設定されている
        assert len(deps.submissions) == 1
        submission = deps.submissions[0]
        assert submission.status == "ERROR"
        assert submission.error_message == "Test error message"

    @pytest.mark.asyncio
    async def test_propagates_success_status_from_base_member_agent(self) -> None:
        """BaseMemberAgent が SUCCESS を返した場合、MemberSubmission.status も SUCCESS になる"""
        from typing import Any
        from unittest.mock import AsyncMock

        from mixseek.agents.leader.dependencies import TeamDependencies
        from mixseek.agents.member.base import BaseMemberAgent
        from mixseek.models.member_agent import MemberAgentResult, ResultStatus

        # Arrange: SUCCESS を返す BaseMemberAgent をモック
        mock_member_agent = AsyncMock(spec=BaseMemberAgent)
        mock_member_agent.execute.return_value = MemberAgentResult(
            status=ResultStatus.SUCCESS,
            content="Success response",
            agent_name="test_agent",
            agent_type="plain",
            error_message=None,
            usage_info={"input_tokens": 100, "output_tokens": 200},
            all_messages=None,
        )

        team_config = TeamConfig(
            team_id="team-001",
            team_name="Test Team",
            members=[
                TeamMemberAgentConfig(
                    agent_name="test_agent",
                    agent_type="plain",
                    tool_name="delegate_to_test_agent",
                    tool_description="Test agent",
                    model="gemini-2.5-flash-lite",
                    system_instruction="test",
                    temperature=0.7,
                    max_tokens=2048,
                )
            ],
        )

        leader_agent: Any = Mock()
        registered_tools: list[Any] = []
        leader_agent.tool = lambda func: registered_tools.append(func)

        member_agents: Any = {"test_agent": mock_member_agent}

        # Act: Tool を登録
        register_member_tools(leader_agent, team_config, member_agents)

        tool_func = registered_tools[0]

        deps = TeamDependencies(team_id="team-001", team_name="Test Team", round_number=1)
        mock_ctx: Any = Mock()
        mock_ctx.deps = deps

        # Act: tool_func を実行
        result = await tool_func(mock_ctx, "test task")

        # Assert: submission.status == "SUCCESS"
        assert len(deps.submissions) == 1
        submission = deps.submissions[0]
        assert submission.status == "SUCCESS"
        assert submission.error_message is None
        assert result == "Success response"

    @pytest.mark.asyncio
    async def test_propagates_error_message(self) -> None:
        """error_message が正しく伝播される"""
        from typing import Any
        from unittest.mock import AsyncMock

        from mixseek.agents.leader.dependencies import TeamDependencies
        from mixseek.agents.member.base import BaseMemberAgent
        from mixseek.models.member_agent import MemberAgentResult, ResultStatus

        # Arrange: 特定のエラーメッセージを返す BaseMemberAgent をモック
        error_msg = "WebSearchTool failed: allowed_domains restriction violated"
        mock_member_agent = AsyncMock(spec=BaseMemberAgent)
        mock_member_agent.execute.return_value = MemberAgentResult(
            status=ResultStatus.ERROR,
            content="",
            agent_name="web_search_agent",
            agent_type="web_search",
            error_message=error_msg,
            usage_info=None,
            all_messages=None,
        )

        team_config = TeamConfig(
            team_id="team-001",
            team_name="Test Team",
            members=[
                TeamMemberAgentConfig(
                    agent_name="web_search_agent",
                    agent_type="web_search",
                    tool_name="delegate_to_web_search",
                    tool_description="Web search agent",
                    model="gemini-2.5-flash-lite",
                    system_instruction="search",
                    temperature=0.7,
                    max_tokens=2048,
                )
            ],
        )

        leader_agent: Any = Mock()
        registered_tools: list[Any] = []
        leader_agent.tool = lambda func: registered_tools.append(func)

        member_agents: Any = {"web_search_agent": mock_member_agent}

        register_member_tools(leader_agent, team_config, member_agents)
        tool_func = registered_tools[0]

        deps = TeamDependencies(team_id="team-001", team_name="Test Team", round_number=1)
        mock_ctx: Any = Mock()
        mock_ctx.deps = deps

        # Act
        await tool_func(mock_ctx, "search query")

        # Assert: error_message が正しく伝播される
        assert len(deps.submissions) == 1
        submission = deps.submissions[0]
        assert submission.status == "ERROR"
        assert submission.error_message == error_msg
