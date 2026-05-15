"""`WorkflowEngine._build_submission_content` / `_format_executor_text` / `_add_usage` の単体テスト。

invariant:
    - `_build_submission_content` に user_prompt が含まれない（4 ケース）
    - ERROR 時の整形: json は error_message 含む / text は見出しに (ERROR: msg)
"""

import json
from typing import Any

import pytest
from pydantic_ai import RunUsage

from mixseek.workflow.engine import (
    WorkflowEngine,
    _add_usage,
    _format_executor_text,
)
from mixseek.workflow.models import (
    ExecutableOutput,
    ExecutableResult,
    StepResult,
    WorkflowContext,
)

from ._engine_helpers import make_settings


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
    settings = make_settings(
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
    """4 ケース全てで返値文字列に user_prompt を含まない。"""
    ctx = _populated_context(user_prompt="my-secret-prompt")
    content = _engine()._build_submission_content(
        ctx,
        include_all=include_all,
        fmt=fmt,  # type: ignore[arg-type]
    )
    assert "my-secret-prompt" not in content
    assert "user_prompt" not in content


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
