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
