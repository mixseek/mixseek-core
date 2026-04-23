"""`mixseek.workflow.engine.WorkflowEngine` の単体テスト。

Invariant 対応（PR2 計画 §Invariants 対応表）:
    #7  function ERROR → WorkflowStepFailedError 即昇格、後続 step 未呼び出し
    #8  build_executable 失敗 → WorkflowStepFailedError 昇格
    #9  agent ERROR → deps.submissions に積まれ step 継続
    #10 deps.submissions 積み順 == step 順 × executor 定義順
    #11 _build_submission_content に user_prompt が含まれない（4 ケース）
    #12 ERROR 時の整形: json は error_message 含む / text は見出しに (ERROR: msg)

テスト戦略:
    `monkeypatch.setattr("mixseek.workflow.engine.build_executable", fake_builder)` で
    最小侵襲モック。`FakeExecutable` を登録 dict に仕込んで `fake_builder` が lookup する。
"""

import asyncio
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import pytest
from pydantic_ai import RunUsage

from mixseek.agents.leader.dependencies import TeamDependencies
from mixseek.config.schema import WorkflowSettings
from mixseek.workflow import engine as engine_module
from mixseek.workflow.engine import (
    WorkflowEngine,
    _add_usage,
    _format_executor_text,
)
from mixseek.workflow.exceptions import WorkflowStepFailedError
from mixseek.workflow.models import (
    ExecutableOutput,
    ExecutableResult,
    StepResult,
    WorkflowContext,
)

# ---- Helpers ----


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


def _success_result(content: str = "ok", usage: RunUsage | None = None) -> ExecutableResult:
    return ExecutableResult(
        content=content,
        execution_time_ms=1.0,
        status="SUCCESS",
        usage=usage or RunUsage(),
    )


def _error_result(msg: str = "boom") -> ExecutableResult:
    return ExecutableResult(
        content="",
        execution_time_ms=1.0,
        status="ERROR",
        error_message=msg,
    )


def _make_settings(
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


def _team_deps() -> TeamDependencies:
    return TeamDependencies(
        execution_id="exec-1",
        team_id="test-wf",
        team_name="Test WF",
        round_number=1,
    )


def _install_fake_builder(
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


# ---- Execution control ----


@pytest.mark.asyncio
async def test_single_step_single_executor_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fakes = {
        "e1": FakeExecutable("e1", "plain", lambda: _success_result("out-1")),
    }
    _install_fake_builder(monkeypatch, fakes)

    settings = _make_settings([{"id": "s1", "executors": [{"name": "e1", "type": "plain"}]}])
    deps = _team_deps()

    result = await WorkflowEngine(settings).run("prompt", deps)

    assert fakes["e1"].call_count == 1
    assert len(deps.submissions) == 1
    assert deps.submissions[0].agent_name == "e1"
    assert deps.submissions[0].status == "SUCCESS"
    assert "e1" in result.submission_content


@pytest.mark.asyncio
async def test_parallel_step_submissions_in_definition_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fakes = {
        "e-a": FakeExecutable("e-a", "plain", lambda: _success_result("A")),
        "e-b": FakeExecutable("e-b", "plain", lambda: _success_result("B")),
    }
    _install_fake_builder(monkeypatch, fakes)

    settings = _make_settings(
        [
            {
                "id": "s1",
                "executors": [
                    {"name": "e-a", "type": "plain"},
                    {"name": "e-b", "type": "plain"},
                ],
            }
        ]
    )
    deps = _team_deps()
    await WorkflowEngine(settings).run("p", deps)

    assert [s.agent_name for s in deps.submissions] == ["e-a", "e-b"]


@pytest.mark.asyncio
async def test_parallel_submissions_preserve_definition_order_under_latency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """invariant #10 回帰: 先定義 executor が遅くても submission は定義順を保持。

    実装の初期バージョンでは `_run_one` 内で `deps.submissions.append` していたため、
    並列実行時に完了順で記録されてしまう問題があった。このテストは完了順の揺らぎを
    作り、定義順が保持されることを保証する。
    """
    fakes = {
        "slow": FakeExecutable(
            "slow",
            "plain",
            lambda: _success_result("S"),
            delay_seconds=0.05,
        ),
        "fast": FakeExecutable("fast", "plain", lambda: _success_result("F")),
    }
    _install_fake_builder(monkeypatch, fakes)

    settings = _make_settings(
        [
            {
                "id": "s1",
                "executors": [
                    {"name": "slow", "type": "plain"},
                    {"name": "fast", "type": "plain"},
                ],
            }
        ]
    )
    deps = _team_deps()
    await WorkflowEngine(settings).run("p", deps)

    assert [s.agent_name for s in deps.submissions] == ["slow", "fast"]


@pytest.mark.asyncio
async def test_multiple_steps_submission_order(monkeypatch: pytest.MonkeyPatch) -> None:
    """invariant #10: deps.submissions 順 == step 順 × executor 定義順。"""
    fakes = {
        "s1-a": FakeExecutable("s1-a", "plain", lambda: _success_result()),
        "s1-b": FakeExecutable("s1-b", "plain", lambda: _success_result()),
        "s2-a": FakeExecutable("s2-a", "plain", lambda: _success_result()),
        "s2-b": FakeExecutable("s2-b", "plain", lambda: _success_result()),
    }
    _install_fake_builder(monkeypatch, fakes)

    settings = _make_settings(
        [
            {
                "id": "s1",
                "executors": [
                    {"name": "s1-a", "type": "plain"},
                    {"name": "s1-b", "type": "plain"},
                ],
            },
            {
                "id": "s2",
                "executors": [
                    {"name": "s2-a", "type": "plain"},
                    {"name": "s2-b", "type": "plain"},
                ],
            },
        ]
    )
    deps = _team_deps()
    await WorkflowEngine(settings).run("p", deps)

    assert [s.agent_name for s in deps.submissions] == ["s1-a", "s1-b", "s2-a", "s2-b"]


@pytest.mark.asyncio
async def test_agent_soft_failure_continues(monkeypatch: pytest.MonkeyPatch) -> None:
    """invariant #9: agent ERROR は step 継続、後続 step も実行される。"""
    fakes = {
        "e1": FakeExecutable("e1", "plain", lambda: _error_result("agent down")),
        "e2": FakeExecutable("e2", "plain", lambda: _success_result("ok")),
        "next": FakeExecutable("next", "plain", lambda: _success_result("next-ok")),
    }
    _install_fake_builder(monkeypatch, fakes)

    settings = _make_settings(
        [
            {
                "id": "s1",
                "executors": [
                    {"name": "e1", "type": "plain"},
                    {"name": "e2", "type": "plain"},
                ],
            },
            {
                "id": "s2",
                "executors": [{"name": "next", "type": "plain"}],
            },
        ]
    )
    deps = _team_deps()
    await WorkflowEngine(settings).run("p", deps)

    assert [s.status for s in deps.submissions] == ["ERROR", "SUCCESS", "SUCCESS"]
    assert fakes["next"].call_count == 1


@pytest.mark.asyncio
async def test_function_hard_failure_halts_workflow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """invariant #7: function ERROR → WorkflowStepFailedError 即昇格、後続 step 未実行。"""
    fakes = {
        "agent-1": FakeExecutable("agent-1", "plain", lambda: _success_result()),
        "fn-1": FakeExecutable("fn-1", "function", lambda: _error_result("fn failed")),
        "s2-agent": FakeExecutable("s2-agent", "plain", lambda: _success_result()),
    }
    _install_fake_builder(
        monkeypatch,
        fakes,
        fail_if=lambda n: n == "s2-agent",
    )

    settings = _make_settings(
        [
            {
                "id": "s1",
                "executors": [
                    {"name": "agent-1", "type": "plain"},
                    {
                        "name": "fn-1",
                        "type": "function",
                        "plugin": {"module": "fake.mod", "function": "fn"},
                    },
                ],
            },
            {
                "id": "s2",
                "executors": [{"name": "s2-agent", "type": "plain"}],
            },
        ]
    )
    deps = _team_deps()
    with pytest.raises(WorkflowStepFailedError) as exc_info:
        await WorkflowEngine(settings).run("p", deps)

    assert exc_info.value.step_id == "s1"
    assert exc_info.value.executor_name == "fn-1"
    assert exc_info.value.error_message == "fn failed"
    # 並列実行済みの s1 の全 executor submission は残る（agent SUCCESS + fn ERROR）
    assert [s.agent_name for s in deps.submissions] == ["agent-1", "fn-1"]
    assert fakes["s2-agent"].call_count == 0


@pytest.mark.asyncio
async def test_build_executable_failure_halts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """invariant #8: build_executable 例外 → WorkflowStepFailedError 昇格。"""
    fakes: dict[str, FakeExecutable] = {}
    _install_fake_builder(
        monkeypatch,
        fakes,
        raise_on={"bad": ValueError("module not found")},
    )

    settings = _make_settings(
        [
            {
                "id": "s1",
                "executors": [
                    {
                        "name": "bad",
                        "type": "function",
                        "plugin": {"module": "no.such", "function": "fn"},
                    },
                ],
            }
        ]
    )
    deps = _team_deps()
    with pytest.raises(WorkflowStepFailedError) as exc_info:
        await WorkflowEngine(settings).run("p", deps)

    assert exc_info.value.step_id == "s1"
    assert exc_info.value.executor_name == "bad"
    assert "failed to build executable" in (exc_info.value.error_message or "")


@pytest.mark.asyncio
async def test_all_messages_concatenation_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D3: all_messages は step 順 × executor 定義順で連結される。

    `MemberSubmission.all_messages: list[ModelMessage]` のバリデーションを通すため、
    マーカーには空の `ModelRequest` インスタンスを使う（各 executor ごとに異なる
    インスタンスで id() による順序確認）。
    """
    from pydantic_ai.messages import ModelRequest

    msg_s1a = ModelRequest(parts=[])
    msg_s1b = ModelRequest(parts=[])
    msg_s2a = ModelRequest(parts=[])

    fakes = {
        "s1-a": FakeExecutable(
            "s1-a",
            "plain",
            lambda: ExecutableResult(
                content="A",
                execution_time_ms=0.0,
                status="SUCCESS",
                all_messages=[msg_s1a],
            ),
        ),
        "s1-b": FakeExecutable(
            "s1-b",
            "plain",
            lambda: ExecutableResult(
                content="B",
                execution_time_ms=0.0,
                status="SUCCESS",
                all_messages=[msg_s1b],
            ),
        ),
        "s2-a": FakeExecutable(
            "s2-a",
            "plain",
            lambda: ExecutableResult(
                content="C",
                execution_time_ms=0.0,
                status="SUCCESS",
                all_messages=[msg_s2a],
            ),
        ),
    }
    _install_fake_builder(monkeypatch, fakes)

    settings = _make_settings(
        [
            {
                "id": "s1",
                "executors": [
                    {"name": "s1-a", "type": "plain"},
                    {"name": "s1-b", "type": "plain"},
                ],
            },
            {
                "id": "s2",
                "executors": [{"name": "s2-a", "type": "plain"}],
            },
        ]
    )
    deps = _team_deps()
    result = await WorkflowEngine(settings).run("p", deps)

    assert [id(m) for m in result.all_messages] == [id(msg_s1a), id(msg_s1b), id(msg_s2a)]


@pytest.mark.asyncio
async def test_total_usage_summed(monkeypatch: pytest.MonkeyPatch) -> None:
    fakes = {
        "e1": FakeExecutable(
            "e1",
            "plain",
            lambda: _success_result(usage=RunUsage(input_tokens=10, output_tokens=20, requests=1)),
        ),
        "e2": FakeExecutable(
            "e2",
            "plain",
            lambda: _success_result(usage=RunUsage(input_tokens=5, output_tokens=7, requests=1)),
        ),
    }
    _install_fake_builder(monkeypatch, fakes)

    settings = _make_settings(
        [
            {
                "id": "s1",
                "executors": [
                    {"name": "e1", "type": "plain"},
                    {"name": "e2", "type": "plain"},
                ],
            }
        ]
    )
    deps = _team_deps()
    result = await WorkflowEngine(settings).run("p", deps)

    assert result.total_usage.input_tokens == 15
    assert result.total_usage.output_tokens == 27
    assert result.total_usage.requests == 2


# ---- _build_submission_content (invariant #11, #12) ----


def _populated_context(user_prompt: str = "my-secret-prompt") -> WorkflowContext:
    """2 ステップ × 各 2 executor の完了状態にした WorkflowContext を返す。"""
    ctx = WorkflowContext(user_prompt=user_prompt)
    ctx.add_step_result(
        "s1",
        StepResult(
            "s1",
            [
                ExecutableOutput(
                    "s1-a",
                    "plain",
                    ExecutableResult(content="A", execution_time_ms=1.0, status="SUCCESS"),
                ),
                ExecutableOutput(
                    "s1-b",
                    "plain",
                    ExecutableResult(
                        content="",
                        execution_time_ms=1.0,
                        status="ERROR",
                        error_message="boom",
                    ),
                ),
            ],
        ),
    )
    ctx.add_step_result(
        "s2",
        StepResult(
            "s2",
            [
                ExecutableOutput(
                    "s2-a",
                    "plain",
                    ExecutableResult(content="FINAL", execution_time_ms=1.0, status="SUCCESS"),
                ),
            ],
        ),
    )
    return ctx


def _engine(**kwargs: Any) -> WorkflowEngine:
    steps = kwargs.get("steps") or [
        {"id": "s1", "executors": [{"name": "s1-a", "type": "plain"}]},
        {"id": "s2", "executors": [{"name": "s2-a", "type": "plain"}]},
    ]
    settings = _make_settings(
        steps,
        include_all_context=kwargs.get("include_all_context", True),
        final_output_format=kwargs.get("final_output_format", "json"),
    )
    return WorkflowEngine(settings)


class TestBuildSubmissionContentJson:
    def test_json_all_structure(self) -> None:
        ctx = _populated_context()
        content = _engine()._build_submission_content(ctx, include_all=True, fmt="json")
        payload = json.loads(content)
        assert set(payload["steps"].keys()) == {"s1", "s2"}
        s1 = payload["steps"]["s1"]
        assert {e["executor_name"] for e in s1} == {"s1-a", "s1-b"}
        error_entry = next(e for e in s1 if e["executor_name"] == "s1-b")
        assert error_entry["status"] == "ERROR"
        assert error_entry["error_message"] == "boom"

    def test_json_last_only_final_step(self) -> None:
        ctx = _populated_context()
        content = _engine()._build_submission_content(ctx, include_all=False, fmt="json")
        payload = json.loads(content)
        assert set(payload["steps"].keys()) == {"s2"}
        assert payload["steps"]["s2"][0]["executor_name"] == "s2-a"


class TestBuildSubmissionContentText:
    def test_text_all_includes_step_and_executor_headings(self) -> None:
        ctx = _populated_context()
        content = _engine()._build_submission_content(ctx, include_all=True, fmt="text")
        assert "## s1" in content
        assert "## s2" in content
        assert "### s1-a" in content
        assert "### s2-a" in content

    def test_text_all_error_annotation(self) -> None:
        ctx = _populated_context()
        content = _engine()._build_submission_content(ctx, include_all=True, fmt="text")
        # s1-b は ERROR なので見出しに (ERROR: boom) が付く
        assert "### s1-b (ERROR: boom)" in content

    def test_text_last_uses_two_level_heading(self) -> None:
        ctx = _populated_context()
        content = _engine()._build_submission_content(ctx, include_all=False, fmt="text")
        assert "## s2-a" in content
        # s1 系の見出しは含まれない
        assert "## s1" not in content
        assert "### s1-a" not in content


@pytest.mark.parametrize(
    ("include_all", "fmt"),
    [(True, "json"), (False, "json"), (True, "text"), (False, "text")],
)
def test_submission_content_excludes_user_prompt(include_all: bool, fmt: str) -> None:
    """invariant #11: 4 ケース全てで返値文字列に user_prompt を含まない。"""
    ctx = _populated_context(user_prompt="my-secret-prompt")
    content = _engine()._build_submission_content(
        ctx,
        include_all=include_all,
        fmt=fmt,  # type: ignore[arg-type]
    )
    assert "my-secret-prompt" not in content
    assert "user_prompt" not in content


# ---- _format_executor_text ----


class TestFormatExecutorText:
    def test_success_heading(self) -> None:
        out = ExecutableOutput("e1", "plain", ExecutableResult(content="x", execution_time_ms=0.0, status="SUCCESS"))
        assert _format_executor_text(out, heading="##") == "## e1\n\nx"

    def test_error_heading_appends_error_message(self) -> None:
        out = ExecutableOutput(
            "e1",
            "plain",
            ExecutableResult(
                content="",
                execution_time_ms=0.0,
                status="ERROR",
                error_message="oops",
            ),
        )
        assert _format_executor_text(out, heading="###").startswith("### e1 (ERROR: oops)")


# ---- _add_usage ----


class TestAddUsage:
    def test_sums_fields(self) -> None:
        a = RunUsage(input_tokens=1, output_tokens=2, requests=1)
        b = RunUsage(input_tokens=10, output_tokens=20, requests=2)
        total = _add_usage(a, b)
        assert total.input_tokens == 11
        assert total.output_tokens == 22
        assert total.requests == 3

    def test_handles_none_fields(self) -> None:
        a = RunUsage()
        b = RunUsage(input_tokens=5, output_tokens=6, requests=1)
        total = _add_usage(a, b)
        assert total.input_tokens == 5
        assert total.output_tokens == 6
        assert total.requests == 1

    def test_both_empty(self) -> None:
        total = _add_usage(RunUsage(), RunUsage())
        assert total.input_tokens == 0
        assert total.output_tokens == 0
        assert total.requests == 0
