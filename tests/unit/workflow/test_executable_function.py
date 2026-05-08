"""`FunctionExecutable` および `Executable` プロトコルの単体テスト。

invariant:
    - FunctionExecutable sync/async/timeout/exception 4 パス
    - `Executable` は `@runtime_checkable` で isinstance 判定可能
"""

import asyncio

import pytest

from mixseek.agents.leader.dependencies import TeamDependencies
from mixseek.workflow.executable import (
    AgentExecutable,
    Executable,
    FunctionExecutable,
)

from ._executable_helpers import make_agent_mock


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


class TestExecutableProtocol:
    def test_agent_executable_is_executable(self, team_deps: TeamDependencies) -> None:
        agent = make_agent_mock()
        ex = AgentExecutable(agent=agent, deps=team_deps)
        assert isinstance(ex, Executable)

    def test_function_executable_is_executable(self) -> None:
        ex = FunctionExecutable(name="x", func=lambda s: s)
        assert isinstance(ex, Executable)
