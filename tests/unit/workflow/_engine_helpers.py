"""`test_engine_*` 共通ヘルパー。

pytest は `test_*.py` のみ collection するため、本ファイル（`_engine_helpers.py`）は
テスト収集対象外。
"""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import pytest
from pydantic_ai import RunUsage

from mixseek.agents.leader.dependencies import TeamDependencies
from mixseek.config.schema import WorkflowSettings
from mixseek.workflow import engine as engine_module
from mixseek.workflow.models import ExecutableResult


@dataclass
class FakeExecutable:
    """テスト用の `Executable` 実装。`build_executable` モック経由で WorkflowEngine に
    注入される。`run` 呼び出し時に `result_factory` を呼び結果を返す。

    `delay_seconds` を指定すると run 内で `asyncio.sleep` を挟み、並列実行の
    完了順を揺らせる（順序保証テストで使用）。
    """

    name: str
    executor_type: str
    result_factory: Callable[[], ExecutableResult]
    delay_seconds: float = 0.0
    call_count: int = 0
    last_input: str | None = field(default=None)

    async def run(self, input: str) -> ExecutableResult:
        self.call_count += 1
        self.last_input = input
        if self.delay_seconds > 0:
            await asyncio.sleep(self.delay_seconds)
        return self.result_factory()


def success_result(content: str = "ok", usage: RunUsage | None = None) -> ExecutableResult:
    return ExecutableResult(
        content=content,
        execution_time_ms=1.0,
        status="SUCCESS",
        usage=usage or RunUsage(),
    )


def error_result(msg: str = "boom") -> ExecutableResult:
    return ExecutableResult(
        content="",
        execution_time_ms=1.0,
        status="ERROR",
        error_message=msg,
    )


def make_settings(
    steps: list[dict[str, Any]],
    *,
    include_all_context: bool = True,
    final_output_format: str = "json",
    default_model: str = "google-gla:gemini-2.5-flash",
) -> WorkflowSettings:
    return WorkflowSettings.model_validate(
        {
            "workflow_id": "test-wf",
            "workflow_name": "Test WF",
            "default_model": default_model,
            "include_all_context": include_all_context,
            "final_output_format": final_output_format,
            "steps": steps,
        }
    )


def workflow_team_deps() -> TeamDependencies:
    """`test_engine_*` で使う workflow ID 向け TeamDependencies。

    `conftest.py::team_deps` fixture とは team_id / team_name が異なる（workflow 用）。
    """
    return TeamDependencies(
        execution_id="exec-1",
        team_id="test-wf",
        team_name="Test WF",
        round_number=1,
    )


def install_fake_builder(
    monkeypatch: pytest.MonkeyPatch,
    fakes: dict[str, FakeExecutable],
    *,
    raise_on: dict[str, Exception] | None = None,
    fail_if: Callable[[str], bool] | None = None,
) -> None:
    """`build_executable` を差し替え、`cfg.name` で `fakes` を返す。

    Args:
        raise_on: {executor_name: Exception} を指定すると当該 cfg で例外を投げる
        fail_if: 引数 `cfg.name` で True 判定なら `pytest.fail` を発動
    """
    raise_on = raise_on or {}

    def fake_builder(cfg: Any, deps: Any, *, workspace: Any, default_model: Any) -> FakeExecutable:
        name = cfg.name
        if fail_if is not None and fail_if(name):
            pytest.fail(f"build_executable must not be called for '{name}'")
        if name in raise_on:
            raise raise_on[name]
        return fakes[name]

    monkeypatch.setattr(engine_module, "build_executable", fake_builder)
