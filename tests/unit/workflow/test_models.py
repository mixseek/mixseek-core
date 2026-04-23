"""`mixseek.workflow.models` の単体テスト。

以下の invariant を検証する（PR2 計画 §Invariants 対応表）:
    #1 `WorkflowContext.build_task_context` のキー集合 == {"user_prompt", "previous_steps"}
    #2 `WorkflowContext._serialize` の 4 フィールド固定
    #3 `_last_previous_step` は Step 1 実行時 `{}` を返す
"""

import json

import pytest
from pydantic_ai import RunUsage

from mixseek.workflow.models import (
    ExecutableOutput,
    ExecutableResult,
    StepResult,
    StrategyResult,
    WorkflowContext,
    WorkflowResult,
)


def _make_output(
    name: str = "exec-1",
    executor_type: str = "plain",
    content: str = "ok",
    status: str = "SUCCESS",
    error_message: str | None = None,
) -> ExecutableOutput:
    return ExecutableOutput(
        name=name,
        executor_type=executor_type,
        result=ExecutableResult(
            content=content,
            execution_time_ms=1.0,
            status=status,  # type: ignore[arg-type]
            error_message=error_message,
        ),
    )


class TestWorkflowContextBuildTaskContext:
    """invariant #1: build_task_context の JSON キー構造固定。"""

    def test_top_level_keys(self) -> None:
        ctx = WorkflowContext(user_prompt="q")
        payload = json.loads(ctx.build_task_context(include_all=True))
        assert set(payload.keys()) == {"user_prompt", "previous_steps"}

    def test_user_prompt_is_preserved(self) -> None:
        ctx = WorkflowContext(user_prompt="my-prompt")
        payload = json.loads(ctx.build_task_context(include_all=False))
        assert payload["user_prompt"] == "my-prompt"

    def test_previous_steps_empty_on_first_step(self) -> None:
        ctx = WorkflowContext(user_prompt="q")
        payload = json.loads(ctx.build_task_context(include_all=True))
        assert payload["previous_steps"] == {}

    def test_ensure_ascii_false_preserves_non_ascii(self) -> None:
        ctx = WorkflowContext(user_prompt="日本語プロンプト")
        raw = ctx.build_task_context(include_all=True)
        assert "日本語プロンプト" in raw


class TestWorkflowContextSerialize:
    """invariant #2: _serialize の 4 フィールド固定。"""

    def test_four_fields_shape(self) -> None:
        out = _make_output(
            name="agent-a",
            content="body",
            status="ERROR",
            error_message="boom",
        )
        serialized = WorkflowContext._serialize(out)
        assert set(serialized.keys()) == {
            "executor_name",
            "status",
            "content",
            "error_message",
        }
        assert serialized["executor_name"] == "agent-a"
        assert serialized["status"] == "ERROR"
        assert serialized["content"] == "body"
        assert serialized["error_message"] == "boom"

    def test_executor_type_not_in_serialized(self) -> None:
        """executor_type は _serialize に含まれない（agent/function の区別は不要）。"""
        out = _make_output(executor_type="function")
        assert "executor_type" not in WorkflowContext._serialize(out)


class TestLastPreviousStep:
    """invariant #3: Step 1 実行時 `{}`、2 ステップ目以降で直前 1 ステップのみ。"""

    def test_empty_when_no_steps(self) -> None:
        ctx = WorkflowContext(user_prompt="q")
        assert ctx._last_previous_step() == {}

    def test_returns_only_last_step(self) -> None:
        ctx = WorkflowContext(user_prompt="q")
        ctx.add_step_result("s1", StepResult("s1", [_make_output(name="e1")]))
        ctx.add_step_result("s2", StepResult("s2", [_make_output(name="e2")]))
        result = ctx._last_previous_step()
        assert set(result.keys()) == {"s2"}
        assert result["s2"][0]["executor_name"] == "e2"


class TestAllPreviousSteps:
    """`_all_previous_steps` が全ステップを含むこと。"""

    def test_all_steps_included(self) -> None:
        ctx = WorkflowContext(user_prompt="q")
        ctx.add_step_result("s1", StepResult("s1", [_make_output(name="e1")]))
        ctx.add_step_result("s2", StepResult("s2", [_make_output(name="e2")]))
        result = ctx._all_previous_steps()
        assert set(result.keys()) == {"s1", "s2"}


class TestIncludeAllContextBehavior:
    """include_all=True と False で build_task_context の previous_steps が変わる。"""

    def test_include_all_true_returns_all_steps(self) -> None:
        ctx = WorkflowContext(user_prompt="q")
        ctx.add_step_result("s1", StepResult("s1", [_make_output(name="e1")]))
        ctx.add_step_result("s2", StepResult("s2", [_make_output(name="e2")]))
        payload = json.loads(ctx.build_task_context(include_all=True))
        assert set(payload["previous_steps"].keys()) == {"s1", "s2"}

    def test_include_all_false_returns_only_last(self) -> None:
        ctx = WorkflowContext(user_prompt="q")
        ctx.add_step_result("s1", StepResult("s1", [_make_output(name="e1")]))
        ctx.add_step_result("s2", StepResult("s2", [_make_output(name="e2")]))
        payload = json.loads(ctx.build_task_context(include_all=False))
        assert set(payload["previous_steps"].keys()) == {"s2"}


class TestInsertionOrder:
    """`step_results` が挿入順を保持（Python 3.7+ dict 保証）。"""

    def test_three_step_order(self) -> None:
        ctx = WorkflowContext(user_prompt="q")
        ctx.add_step_result("b", StepResult("b", [_make_output()]))
        ctx.add_step_result("a", StepResult("a", [_make_output()]))
        ctx.add_step_result("c", StepResult("c", [_make_output()]))
        assert list(ctx.step_results.keys()) == ["b", "a", "c"]

    def test_build_task_context_respects_insertion_order(self) -> None:
        ctx = WorkflowContext(user_prompt="q")
        ctx.add_step_result("b", StepResult("b", [_make_output()]))
        ctx.add_step_result("a", StepResult("a", [_make_output()]))
        payload = json.loads(ctx.build_task_context(include_all=True))
        assert list(payload["previous_steps"].keys()) == ["b", "a"]


class TestExecutableResultDefaults:
    """`ExecutableResult` のデフォルト値と型検証。"""

    def test_default_status_is_success(self) -> None:
        r = ExecutableResult(content="x", execution_time_ms=0.0)
        assert r.status == "SUCCESS"
        assert r.error_message is None
        assert r.all_messages == []
        assert isinstance(r.usage, RunUsage)

    def test_error_status_with_message(self) -> None:
        r = ExecutableResult(
            content="",
            execution_time_ms=0.0,
            status="ERROR",
            error_message="fail",
        )
        assert r.status == "ERROR"
        assert r.error_message == "fail"


class TestWorkflowResultAndStrategyResult:
    """`WorkflowResult` / `StrategyResult` が想定通り構築できる。"""

    def test_workflow_result_fields(self) -> None:
        wr = WorkflowResult(
            submission_content="final",
            all_messages=[],
            total_usage=RunUsage(),
        )
        assert wr.submission_content == "final"
        assert wr.all_messages == []
        assert isinstance(wr.total_usage, RunUsage)

    def test_strategy_result_fields(self) -> None:
        sr = StrategyResult(submission_content="final", all_messages=[])
        assert sr.submission_content == "final"
        assert sr.all_messages == []


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
