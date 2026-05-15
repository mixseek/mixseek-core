"""`AgentExecutable` の単体テスト。

`BaseMemberAgent` を `Executable` プロトコルに適合させるアダプタの検証。
invariant:
    - AgentExecutable.run が BaseMemberAgent 例外を status="ERROR" に変換
"""

import asyncio
from unittest.mock import MagicMock

import pytest

from mixseek.agents.leader.dependencies import TeamDependencies
from mixseek.models.member_agent import MemberAgentResult, ResultStatus
from mixseek.workflow.executable import AgentExecutable

from ._executable_helpers import make_agent_mock


class TestAgentExecutableProperties:
    def test_name_and_type_from_agent(self, team_deps: TeamDependencies) -> None:
        agent = make_agent_mock(name="researcher", agent_type="web_search")
        ex = AgentExecutable(agent=agent, deps=team_deps)
        assert ex.name == "researcher"
        assert ex.executor_type == "web_search"


class TestAgentExecutableRunSuccess:
    @pytest.mark.asyncio
    async def test_success_status_uppercased(self, team_deps: TeamDependencies) -> None:
        agent = make_agent_mock()
        agent.execute.return_value = MemberAgentResult(
            status=ResultStatus.SUCCESS,
            content="body",
            agent_name="agent-a",
            agent_type="plain",
            execution_time_ms=42,
            usage_info={"input_tokens": 3, "output_tokens": 5, "requests": 1},
            all_messages=None,
        )
        ex = AgentExecutable(agent=agent, deps=team_deps)
        result = await ex.run("task")
        assert result.status == "SUCCESS"
        assert result.content == "body"
        assert result.execution_time_ms == 42.0
        assert result.usage.input_tokens == 3
        assert result.all_messages == []

    @pytest.mark.asyncio
    async def test_context_has_three_keys(self, team_deps: TeamDependencies) -> None:
        agent = make_agent_mock()
        agent.execute.return_value = MemberAgentResult(
            status=ResultStatus.SUCCESS,
            content="",
            agent_name="agent-a",
            agent_type="plain",
        )
        ex = AgentExecutable(agent=agent, deps=team_deps)
        await ex.run("task")
        args, kwargs = agent.execute.call_args
        assert args == ("task",)
        assert kwargs["context"] == {
            "execution_id": "exec-123",
            "team_id": "team-a",
            "round_number": 1,
        }

    @pytest.mark.asyncio
    async def test_error_status_uppercased_preserves_error_message(self, team_deps: TeamDependencies) -> None:
        agent = make_agent_mock()
        agent.execute.return_value = MemberAgentResult(
            status=ResultStatus.ERROR,
            content="",
            agent_name="agent-a",
            agent_type="plain",
            error_message="something broke",
        )
        ex = AgentExecutable(agent=agent, deps=team_deps)
        result = await ex.run("task")
        assert result.status == "ERROR"
        assert result.error_message == "something broke"

    @pytest.mark.asyncio
    async def test_all_messages_list_preserved(self, team_deps: TeamDependencies) -> None:
        """`all_messages` は型バリデーション対象外の MagicMock で検証（list 伝搬のみ確認）。"""
        agent = make_agent_mock()
        fake_messages = [MagicMock()]
        mock_result = MagicMock()
        mock_result.status = ResultStatus.SUCCESS
        mock_result.content = ""
        mock_result.execution_time_ms = None
        mock_result.usage_info = None
        mock_result.error_message = None
        mock_result.all_messages = fake_messages
        agent.execute.return_value = mock_result
        ex = AgentExecutable(agent=agent, deps=team_deps)
        result = await ex.run("task")
        assert result.all_messages == fake_messages

    @pytest.mark.asyncio
    async def test_all_messages_none_becomes_empty_list(self, team_deps: TeamDependencies) -> None:
        """`result.all_messages` が None でも `ExecutableResult.all_messages` は空リスト。"""
        agent = make_agent_mock()
        agent.execute.return_value = MemberAgentResult(
            status=ResultStatus.SUCCESS,
            content="",
            agent_name="a",
            agent_type="plain",
            all_messages=None,
        )
        ex = AgentExecutable(agent=agent, deps=team_deps)
        result = await ex.run("task")
        assert result.all_messages == []


class TestAgentExecutableRunException:
    """execute() 例外を status="ERROR" に包む。"""

    @pytest.mark.asyncio
    async def test_catches_exception_and_returns_error(self, team_deps: TeamDependencies) -> None:
        agent = make_agent_mock()
        agent.execute.side_effect = RuntimeError("boom")
        ex = AgentExecutable(agent=agent, deps=team_deps)
        result = await ex.run("task")
        assert result.status == "ERROR"
        assert result.error_message == "boom"
        assert result.content == ""

    @pytest.mark.asyncio
    async def test_cancelled_error_propagates(self, team_deps: TeamDependencies) -> None:
        """CancelledError は BaseException なので伝播する（Exception 捕捉にかからない）。"""
        agent = make_agent_mock()
        agent.execute.side_effect = asyncio.CancelledError()
        ex = AgentExecutable(agent=agent, deps=team_deps)
        with pytest.raises(asyncio.CancelledError):
            await ex.run("task")
