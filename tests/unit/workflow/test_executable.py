"""`mixseek.workflow.executable` の単体テスト。

Invariant 対応（PR2 計画 §Invariants 対応表）:
    #4 AgentExecutable.run が BaseMemberAgent 例外を status="ERROR" に変換
    #5 FunctionExecutable sync/async/timeout/exception 4 パス
    #6 build_executable 未知型 TypeError / _load_function 不正 import
    #15 logfire 非導入時 (_LOGFIRE_AVAILABLE=False) でも workflow が動く
"""

import asyncio
from contextlib import nullcontext
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture

from mixseek.agents.leader.dependencies import TeamDependencies
from mixseek.models.member_agent import MemberAgentResult, ResultStatus
from mixseek.workflow import executable as executable_module
from mixseek.workflow.executable import (
    AgentExecutable,
    Executable,
    FunctionExecutable,
    _load_function,
    _logfire_span,
    _to_run_usage,
    build_executable,
)

# ---- Fixtures ----


@pytest.fixture
def team_deps() -> TeamDependencies:
    return TeamDependencies(
        execution_id="exec-123",
        team_id="team-a",
        team_name="Team A",
        round_number=1,
    )


# ---- _logfire_span ----


class TestLogfireSpan:
    """invariant #15: logfire 非導入時の nullcontext fallback。"""

    def test_fallback_to_nullcontext_when_unavailable(self, mocker: MockerFixture) -> None:
        mocker.patch.object(executable_module, "_LOGFIRE_AVAILABLE", False)
        mocker.patch.object(executable_module, "_logfire", None)
        span = _logfire_span("workflow.function", function_name="x")
        assert isinstance(span, type(nullcontext()))

    def test_fallback_works_as_context_manager(self, mocker: MockerFixture) -> None:
        mocker.patch.object(executable_module, "_LOGFIRE_AVAILABLE", False)
        mocker.patch.object(executable_module, "_logfire", None)
        with _logfire_span("workflow.function", function_name="x"):
            pass  # 例外が出ないことを確認

    def test_uses_logfire_span_when_available(self, mocker: MockerFixture) -> None:
        fake_logfire = MagicMock()
        fake_span = MagicMock()
        fake_logfire.span.return_value = fake_span
        mocker.patch.object(executable_module, "_LOGFIRE_AVAILABLE", True)
        mocker.patch.object(executable_module, "_logfire", fake_logfire)
        result = _logfire_span("workflow.function", function_name="x")
        fake_logfire.span.assert_called_once_with("workflow.function", function_name="x")
        assert result is fake_span


# ---- _to_run_usage ----


class TestToRunUsage:
    def test_none_returns_empty_runusage(self) -> None:
        usage = _to_run_usage(None)
        assert usage.input_tokens == 0
        assert usage.output_tokens == 0

    def test_empty_dict_returns_empty_runusage(self) -> None:
        usage = _to_run_usage({})
        assert usage.input_tokens == 0

    def test_populates_from_dict(self) -> None:
        usage = _to_run_usage({"input_tokens": 10, "output_tokens": 20, "requests": 2})
        assert usage.input_tokens == 10
        assert usage.output_tokens == 20
        assert usage.requests == 2


# ---- AgentExecutable ----


def _make_agent_mock(
    name: str = "agent-a",
    agent_type: str = "plain",
) -> MagicMock:
    """`BaseMemberAgent` の MagicMock を作成。`execute` は AsyncMock。"""
    agent = MagicMock()
    # PropertyMock にしなくてもこの代入で name/agent_type/agent_name を読める
    agent.agent_name = name
    agent.agent_type = agent_type
    agent.execute = AsyncMock()
    return agent


class TestAgentExecutableProperties:
    def test_name_and_type_from_agent(self, team_deps: TeamDependencies) -> None:
        agent = _make_agent_mock(name="researcher", agent_type="web_search")
        ex = AgentExecutable(agent=agent, deps=team_deps)
        assert ex.name == "researcher"
        assert ex.executor_type == "web_search"


class TestAgentExecutableRunSuccess:
    @pytest.mark.asyncio
    async def test_success_status_uppercased(self, team_deps: TeamDependencies) -> None:
        agent = _make_agent_mock()
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
        agent = _make_agent_mock()
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
        agent = _make_agent_mock()
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
        agent = _make_agent_mock()
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
        agent = _make_agent_mock()
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
    """invariant #4: execute() 例外を status="ERROR" に包む。"""

    @pytest.mark.asyncio
    async def test_catches_exception_and_returns_error(self, team_deps: TeamDependencies) -> None:
        agent = _make_agent_mock()
        agent.execute.side_effect = RuntimeError("boom")
        ex = AgentExecutable(agent=agent, deps=team_deps)
        result = await ex.run("task")
        assert result.status == "ERROR"
        assert result.error_message == "boom"
        assert result.content == ""

    @pytest.mark.asyncio
    async def test_cancelled_error_propagates(self, team_deps: TeamDependencies) -> None:
        """CancelledError は BaseException なので伝播する（Exception 捕捉にかからない）。"""
        agent = _make_agent_mock()
        agent.execute.side_effect = asyncio.CancelledError()
        ex = AgentExecutable(agent=agent, deps=team_deps)
        with pytest.raises(asyncio.CancelledError):
            await ex.run("task")


# ---- FunctionExecutable ----


class TestFunctionExecutableSync:
    @pytest.mark.asyncio
    async def test_sync_function_success(self) -> None:
        def greet(input: str) -> str:
            return f"hello {input}"

        ex = FunctionExecutable(name="greet", func=greet)
        result = await ex.run("world")
        assert result.status == "SUCCESS"
        assert result.content == "hello world"

    @pytest.mark.asyncio
    async def test_sync_function_non_string_return_coerced(self) -> None:
        def to_number(input: str) -> int:
            return 42

        ex = FunctionExecutable(name="num", func=to_number)  # type: ignore[arg-type]
        result = await ex.run("ignored")
        assert result.status == "SUCCESS"
        assert result.content == "42"

    @pytest.mark.asyncio
    async def test_sync_function_exception(self) -> None:
        def broken(input: str) -> str:
            raise ValueError("bad input")

        ex = FunctionExecutable(name="broken", func=broken)
        result = await ex.run("x")
        assert result.status == "ERROR"
        assert result.error_message == "bad input"


class TestFunctionExecutableAsync:
    @pytest.mark.asyncio
    async def test_async_function_success(self) -> None:
        async def greet(input: str) -> str:
            return f"hi {input}"

        ex = FunctionExecutable(name="async-greet", func=greet)
        result = await ex.run("tonic")
        assert result.status == "SUCCESS"
        assert result.content == "hi tonic"

    @pytest.mark.asyncio
    async def test_async_function_exception(self) -> None:
        async def broken(input: str) -> str:
            raise RuntimeError("async boom")

        ex = FunctionExecutable(name="async-broken", func=broken)
        result = await ex.run("x")
        assert result.status == "ERROR"
        assert result.error_message == "async boom"


class TestFunctionExecutableTimeout:
    @pytest.mark.asyncio
    async def test_timeout_triggers_error_status(self) -> None:
        async def slow(input: str) -> str:
            await asyncio.sleep(10)
            return "never"

        ex = FunctionExecutable(name="slow", func=slow, timeout_seconds=1)
        result = await ex.run("x")
        assert result.status == "ERROR"
        assert result.error_message is not None
        assert "timed out" in result.error_message

    @pytest.mark.asyncio
    async def test_no_timeout_when_none(self) -> None:
        async def fast(input: str) -> str:
            return "done"

        ex = FunctionExecutable(name="fast", func=fast, timeout_seconds=None)
        result = await ex.run("x")
        assert result.status == "SUCCESS"


class TestFunctionExecutableUserRaisedTimeoutError:
    """ユーザー関数自身が `TimeoutError` を投げた場合、wait_for 由来のタイムアウトと
    混同されずに通常エラー（ERROR, error_message=ユーザー由来メッセージ）として
    扱われることを保証する（回帰テスト）。

    初期実装は経過時間ベースのヒューリスティック判定で境界付近を誤分類していた。
    現行実装は `task.exception()` ベースで判定するため、以下 2 ケースとも確実に
    ユーザー由来の `error_message` が返る。
    """

    @pytest.mark.asyncio
    async def test_timeout_set_user_raises_timeouterror_treated_as_error(self) -> None:
        async def user_raises(input: str) -> str:
            raise TimeoutError("user-raised")

        ex = FunctionExecutable(name="u", func=user_raises, timeout_seconds=10)
        result = await ex.run("x")
        assert result.status == "ERROR"
        assert result.error_message == "user-raised"
        # wait_for 由来の "function timed out after ..." ではないこと
        assert result.error_message is not None
        assert "timed out after" not in result.error_message

    @pytest.mark.asyncio
    async def test_timeout_none_user_raises_timeouterror_treated_as_error(self) -> None:
        async def user_raises(input: str) -> str:
            raise TimeoutError("no-timeout-user")

        ex = FunctionExecutable(name="u", func=user_raises, timeout_seconds=None)
        result = await ex.run("x")
        assert result.status == "ERROR"
        assert result.error_message == "no-timeout-user"
        assert "timed out after" not in (result.error_message or "")

    @pytest.mark.asyncio
    async def test_sync_user_raises_timeouterror(self) -> None:
        """sync 関数で TimeoutError を投げた場合も同じ経路で扱う。"""

        def user_raises_sync(input: str) -> str:
            raise TimeoutError("sync-user-raised")

        ex = FunctionExecutable(name="u", func=user_raises_sync, timeout_seconds=10)
        result = await ex.run("x")
        assert result.status == "ERROR"
        assert result.error_message == "sync-user-raised"


# ---- Executable Protocol runtime_checkable ----


class TestExecutableProtocol:
    def test_agent_executable_is_executable(self, team_deps: TeamDependencies) -> None:
        agent = _make_agent_mock()
        ex = AgentExecutable(agent=agent, deps=team_deps)
        assert isinstance(ex, Executable)

    def test_function_executable_is_executable(self) -> None:
        ex = FunctionExecutable(name="x", func=lambda s: s)
        assert isinstance(ex, Executable)


# ---- build_executable ----


class TestBuildExecutable:
    def test_function_settings_returns_function_executable(self, team_deps: TeamDependencies) -> None:
        from mixseek.config.schema import (
            FunctionExecutorSettings,
            FunctionPluginMetadata,
        )

        cfg = FunctionExecutorSettings(
            name="fn",
            plugin=FunctionPluginMetadata(
                module="tests.unit.workflow.test_executable",
                function="_sample_function",
            ),
            timeout_seconds=5,
        )
        ex = build_executable(cfg, team_deps, default_model="google-gla:gemini-2.5-flash")
        assert isinstance(ex, FunctionExecutable)
        assert ex.name == "fn"
        assert ex.executor_type == "function"

    def test_agent_settings_returns_agent_executable(self, team_deps: TeamDependencies, mocker: MockerFixture) -> None:
        from mixseek.config.schema import AgentExecutorSettings

        mock_agent = _make_agent_mock(name="ag", agent_type="plain")
        mocker.patch(
            "mixseek.workflow.executable.MemberAgentFactory.create_agent",
            return_value=mock_agent,
        )
        cfg = AgentExecutorSettings(name="ag", type="plain")
        ex = build_executable(cfg, team_deps, default_model="google-gla:gemini-2.5-flash")
        assert isinstance(ex, AgentExecutable)
        assert ex.name == "ag"

    def test_unknown_type_raises_typeerror(self, team_deps: TeamDependencies) -> None:
        with pytest.raises(TypeError, match="Unsupported executor config"):
            build_executable(
                "not-a-cfg",  # type: ignore[arg-type]
                team_deps,
                default_model="google-gla:gemini-2.5-flash",
            )


# ---- _load_function ----


def _sample_function(input: str) -> str:
    """`test_function_settings_returns_function_executable` から import される。"""
    return f"sample: {input}"


_sample_non_callable = 42


class TestLoadFunction:
    def test_module_not_found(self) -> None:
        with pytest.raises(ValueError, match="Failed to import module"):
            _load_function("no_such_module_xyz_abc", "foo")

    def test_attribute_not_found(self) -> None:
        with pytest.raises(ValueError, match="has no attribute"):
            _load_function("tests.unit.workflow.test_executable", "nonexistent_attr")

    def test_not_callable(self) -> None:
        with pytest.raises(ValueError, match="is not callable"):
            _load_function(
                "tests.unit.workflow.test_executable",
                "_sample_non_callable",
            )

    def test_callable_returned(self) -> None:
        fn = _load_function("tests.unit.workflow.test_executable", "_sample_function")
        assert callable(fn)
        assert fn("x") == "sample: x"
