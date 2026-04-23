"""Workflow executor の実行アダプター。

本モジュールは workflow mode の実行単位である `Executable` を定義し、
`MemberAgent` を包む `AgentExecutable` と Python callable を包む
`FunctionExecutable` を提供する。

重要な invariant:
    `Executable.run` は**例外を絶対に漏らさない**（`BaseException` は除く）。
    発生した例外は `ExecutableResult.status="ERROR"` に包んで返す。これにより
    `WorkflowEngine._execute_step` が `asyncio.gather(return_exceptions=False)`
    で並列実行しても、他 executor の結果を取りこぼさない。

logfire はオプション依存のため、未導入環境では `_logfire_span` が
`contextlib.nullcontext()` を返すよう fallback する。
"""

import asyncio
import importlib
import logging
import time
from collections.abc import Awaitable, Callable
from contextlib import AbstractContextManager, nullcontext
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from pydantic_ai import RunUsage

from mixseek.agents.leader.dependencies import TeamDependencies
from mixseek.agents.member.base import BaseMemberAgent
from mixseek.agents.member.factory import MemberAgentFactory
from mixseek.config.schema import (
    AgentExecutorSettings,
    FunctionExecutorSettings,
)
from mixseek.workflow.models import ExecutableResult

# logfire はオプショナル依存。未導入環境では nullcontext にフォールバック。
# round_controller/controller.py:34-39 と同じパターンで team mode と対称。
_logfire: Any | None
try:
    import logfire as _logfire

    _LOGFIRE_AVAILABLE = True
except ImportError:
    _logfire = None
    _LOGFIRE_AVAILABLE = False

logger = logging.getLogger("mixseek.workflow.function")


def _logfire_span(name: str, **attrs: Any) -> AbstractContextManager[Any]:
    """logfire が利用可能なら `logfire.span`、未導入時は `nullcontext()` を返す。

    `WorkflowEngine.run` と `FunctionExecutable.run` の両方から使用される。
    `instrument_pydantic_ai()` の自動トレース対象外（Function executor 等）の
    span を手動で張る用途。
    """
    if _LOGFIRE_AVAILABLE and _logfire is not None:
        return _logfire.span(name, **attrs)  # type: ignore[no-any-return]
    return nullcontext()


@runtime_checkable
class Executable(Protocol):
    """Workflow ステップ内の実行単位。agent / function 共通のインタフェース。

    `@runtime_checkable` により `isinstance(x, Executable)` が使える。
    """

    @property
    def name(self) -> str:
        """ステップ内で一意の executor 名。"""
        ...

    @property
    def executor_type(self) -> str:
        """executor 種別（"plain" / "web_search" / "custom" / "function" 等）。"""
        ...

    async def run(self, input: str) -> ExecutableResult:
        """executor を実行し、`ExecutableResult` を返す。

        例外を漏らさない契約（`BaseException` は除く）。
        """
        ...


def _to_run_usage(usage_info: dict[str, Any] | None) -> RunUsage:
    """`MemberAgentResult.usage_info` (dict) を `RunUsage` に変換する。"""
    if not usage_info:
        return RunUsage()
    return RunUsage(
        input_tokens=usage_info.get("input_tokens", 0),
        output_tokens=usage_info.get("output_tokens", 0),
        requests=usage_info.get("requests", 1),
    )


class AgentExecutable:
    """`BaseMemberAgent` を `Executable` プロトコルに適合させるアダプター。

    team mode の `tools.py` と同じ 3 キー context
    (`execution_id` / `team_id` / `round_number`) を `TeamDependencies` から合成し、
    `BaseMemberAgent.execute(task, context=...)` を呼び出す。

    logfire トレースは `instrument_pydantic_ai()` による自動 span で取得されるため、
    本クラスでは手動 span は張らない（team mode と対称）。
    """

    def __init__(self, agent: BaseMemberAgent, deps: TeamDependencies) -> None:
        self._agent = agent
        self._deps = deps

    @property
    def name(self) -> str:
        return self._agent.agent_name

    @property
    def executor_type(self) -> str:
        return self._agent.agent_type

    async def run(self, input: str) -> ExecutableResult:
        start = time.perf_counter()
        context = {
            "execution_id": self._deps.execution_id,
            "team_id": self._deps.team_id,
            "round_number": self._deps.round_number,
        }
        try:
            result = await self._agent.execute(input, context=context)
            elapsed = float(
                result.execution_time_ms
                if result.execution_time_ms is not None
                else (time.perf_counter() - start) * 1000
            )
            # ResultStatus は小文字 ("success"/"error"/"warning") なので .upper() で
            # ExecutableResult.status の大文字 Literal に変換する。DuckDB 側の
            # MemberSubmissionsRecord が "SUCCESS" 文字列比較を使うため（leader/models.py L43）。
            return ExecutableResult(
                content=result.content,
                execution_time_ms=elapsed,
                status=result.status.value.upper(),  # type: ignore[arg-type]
                error_message=result.error_message,
                usage=_to_run_usage(result.usage_info),
                all_messages=result.all_messages or [],
            )
        except Exception as e:
            # BaseException (CancelledError, KeyboardInterrupt) は伝播させる。
            # custom agent は execute() の例外保証がないためここで捕捉する。
            elapsed = (time.perf_counter() - start) * 1000
            return ExecutableResult(
                content="",
                execution_time_ms=elapsed,
                status="ERROR",
                error_message=str(e),
            )


class FunctionExecutable:
    """Python callable を `Executable` プロトコルに適合させるアダプター。

    同期関数は `asyncio.to_thread` で coroutine 化し、非同期関数と統一的に
    `asyncio.wait_for` でタイムアウト制御する。

    Note:
        `asyncio.wait_for` で timeout しても同期関数を走らせている thread は
        中断できない（Python の制約）。`timeout_seconds` は「ハング時の上限」で
        あり、確実なキャンセル保証ではない（既知リスク）。
    """

    def __init__(
        self,
        name: str,
        func: Callable[[str], str | Awaitable[str]],
        timeout_seconds: int | None = None,
    ) -> None:
        self._name = name
        self._func = func
        self._timeout_seconds = timeout_seconds

    @property
    def name(self) -> str:
        return self._name

    @property
    def executor_type(self) -> str:
        return "function"

    async def run(self, input: str) -> ExecutableResult:
        start = time.perf_counter()
        with _logfire_span(
            "workflow.function",
            function_name=self._name,
            timeout_seconds=self._timeout_seconds,
        ):
            logger.info("function_execution_start", extra={"function_name": self._name})
            try:
                if asyncio.iscoroutinefunction(self._func):
                    coro: Awaitable[Any] = self._func(input)
                else:
                    coro = asyncio.to_thread(self._func, input)
                if self._timeout_seconds is not None:
                    # coroutine を Task にラップし、wait_for タイムアウト由来の
                    # TimeoutError と、ユーザー関数自身が raise した TimeoutError を
                    # task.exception() の型で判別する（経過時間ベースの判定は境界で誤る）。
                    task = asyncio.ensure_future(coro)
                    try:
                        content = await asyncio.wait_for(task, timeout=self._timeout_seconds)
                    except TimeoutError:
                        user_exc = _user_exception_if_done(task)
                        if user_exc is not None:
                            # ユーザー関数由来の TimeoutError → 通常エラー経路へ
                            raise user_exc from None
                        elapsed = (time.perf_counter() - start) * 1000
                        msg = f"function timed out after {self._timeout_seconds}s"
                        logger.error(
                            "function_execution_timeout",
                            extra={"function_name": self._name, "timeout_seconds": self._timeout_seconds},
                            exc_info=True,
                        )
                        return ExecutableResult(
                            content="", execution_time_ms=elapsed, status="ERROR", error_message=msg
                        )
                else:
                    content = await coro
                elapsed = (time.perf_counter() - start) * 1000
                logger.info(
                    "function_execution_complete",
                    extra={"function_name": self._name, "execution_time_ms": elapsed},
                )
                return ExecutableResult(content=str(content), execution_time_ms=elapsed, status="SUCCESS")
            except Exception as e:
                elapsed = (time.perf_counter() - start) * 1000
                logger.error(
                    "function_execution_error",
                    extra={"function_name": self._name, "error": str(e)},
                    exc_info=True,
                )
                return ExecutableResult(content="", execution_time_ms=elapsed, status="ERROR", error_message=str(e))


def _user_exception_if_done(task: "asyncio.Task[Any]") -> BaseException | None:
    """task が done で CancelledError 以外の例外を持っていれば返す。

    `asyncio.wait_for` はタイムアウト時に task.cancel() → CancelledError → TimeoutError の
    順で変換する。ユーザー関数が自身で `TimeoutError` を raise した場合は task の例外が
    `TimeoutError`（非 CancelledError）になるため、この関数が返す。返ってきた場合、
    呼び出し側はそれを再送して通常のエラーハンドリングに流す。

    既知の制約:
        ユーザー関数が `except CancelledError` で wait_for のキャンセルシグナルを捕捉し、
        別例外（特に `TimeoutError`）を raise する pattern の場合、task の例外が
        非 `CancelledError` になるため「ユーザー例外」と誤分類する。Python の asyncio
        仕様上、外から wait_for のキャンセルシグナル由来の例外かを 100% 確実に判定する
        手段がないため、この極めて稀なケースは許容する（既知リスク）。
    """
    if not task.done():
        return None
    try:
        exc = task.exception()
    except asyncio.CancelledError:
        return None
    if exc is None or isinstance(exc, asyncio.CancelledError):
        return None
    return exc


def build_executable(
    cfg: AgentExecutorSettings | FunctionExecutorSettings,
    deps: TeamDependencies,
    *,
    workspace: Path | None = None,
    default_model: str,
) -> Executable:
    """`StepExecutorConfig` から `Executable` を生成する。

    Args:
        cfg: `AgentExecutorSettings` または `FunctionExecutorSettings`
        deps: `AgentExecutable` の 3 キー context 合成に使用
        workspace: `AgentExecutor` の bundled system_instruction 解決に使用
        default_model: `WorkflowSettings.default_model`。agent の `model` 省略時
            のフォールバック

    Raises:
        TypeError: 未知の cfg 型
        ValueError: function の module/attribute import 失敗
            （`WorkflowEngine._execute_step` で `WorkflowStepFailedError` に昇格）
    """
    if isinstance(cfg, FunctionExecutorSettings):
        func = _load_function(cfg.plugin.module, cfg.plugin.function)
        return FunctionExecutable(
            name=cfg.name,
            func=func,
            timeout_seconds=cfg.timeout_seconds,
        )
    if isinstance(cfg, AgentExecutorSettings):
        agent = MemberAgentFactory.create_agent(
            cfg.to_member_agent_config(workspace=workspace, default_model=default_model)
        )
        return AgentExecutable(agent=agent, deps=deps)
    raise TypeError(f"Unsupported executor config: {type(cfg).__name__}")


def _load_function(module: str, function: str) -> Callable[[str], Any]:
    """`module.function` を動的解決して callable を返す。

    Raises:
        ValueError: module import 失敗 / attribute 不在 / callable でない
    """
    try:
        mod = importlib.import_module(module)
    except ImportError as e:
        raise ValueError(f"Failed to import module '{module}': {e}") from e
    if not hasattr(mod, function):
        raise ValueError(f"Module '{module}' has no attribute '{function}'")
    fn: Callable[[str], Any] = getattr(mod, function)
    if not callable(fn):
        raise ValueError(f"'{module}.{function}' is not callable")
    return fn
