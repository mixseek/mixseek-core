"""`WorkflowEngine.run` 実行制御の単体テスト。

invariant:
    - function ERROR → WorkflowStepFailedError 即昇格、後続 step 未呼び出し
    - build_executable 失敗 → WorkflowStepFailedError 昇格
    - agent ERROR → deps.submissions に積まれ step 継続
    - deps.submissions 積み順 == step 順 × executor 定義順
"""

import pytest
from pydantic_ai import RunUsage

from mixseek.workflow.engine import WorkflowEngine
from mixseek.workflow.exceptions import WorkflowStepFailedError
from mixseek.workflow.models import ExecutableResult

from ._engine_helpers import (
    FakeExecutable,
    error_result,
    install_fake_builder,
    make_settings,
    success_result,
    workflow_team_deps,
)


@pytest.mark.asyncio
async def test_single_step_single_executor_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fakes = {
        "e1": FakeExecutable("e1", "plain", lambda: success_result("out-1")),
    }
    install_fake_builder(monkeypatch, fakes)

    settings = make_settings([{"id": "s1", "executors": [{"name": "e1", "type": "plain"}]}])
    deps = workflow_team_deps()

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
        "e-a": FakeExecutable("e-a", "plain", lambda: success_result("A")),
        "e-b": FakeExecutable("e-b", "plain", lambda: success_result("B")),
    }
    install_fake_builder(monkeypatch, fakes)

    settings = make_settings(
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
    deps = workflow_team_deps()
    await WorkflowEngine(settings).run("p", deps)

    assert [s.agent_name for s in deps.submissions] == ["e-a", "e-b"]


@pytest.mark.asyncio
async def test_parallel_submissions_preserve_definition_order_under_latency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """並列実行時、先定義 executor が遅くても submission は定義順を保持する回帰テスト。

    実装の初期バージョンでは `_run_one` 内で `deps.submissions.append` していたため、
    並列実行時に完了順で記録されてしまう問題があった。このテストは完了順の揺らぎを
    作り、定義順が保持されることを保証する。
    """
    fakes = {
        "slow": FakeExecutable(
            "slow",
            "plain",
            lambda: success_result("S"),
            delay_seconds=0.05,
        ),
        "fast": FakeExecutable("fast", "plain", lambda: success_result("F")),
    }
    install_fake_builder(monkeypatch, fakes)

    settings = make_settings(
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
    deps = workflow_team_deps()
    await WorkflowEngine(settings).run("p", deps)

    assert [s.agent_name for s in deps.submissions] == ["slow", "fast"]


@pytest.mark.asyncio
async def test_multiple_steps_submission_order(monkeypatch: pytest.MonkeyPatch) -> None:
    """deps.submissions 順 == step 順 × executor 定義順。"""
    fakes = {
        "s1-a": FakeExecutable("s1-a", "plain", lambda: success_result()),
        "s1-b": FakeExecutable("s1-b", "plain", lambda: success_result()),
        "s2-a": FakeExecutable("s2-a", "plain", lambda: success_result()),
        "s2-b": FakeExecutable("s2-b", "plain", lambda: success_result()),
    }
    install_fake_builder(monkeypatch, fakes)

    settings = make_settings(
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
    deps = workflow_team_deps()
    await WorkflowEngine(settings).run("p", deps)

    assert [s.agent_name for s in deps.submissions] == ["s1-a", "s1-b", "s2-a", "s2-b"]


@pytest.mark.asyncio
async def test_agent_soft_failure_continues(monkeypatch: pytest.MonkeyPatch) -> None:
    """agent ERROR は step 継続、後続 step も実行される。"""
    fakes = {
        "e1": FakeExecutable("e1", "plain", lambda: error_result("agent down")),
        "e2": FakeExecutable("e2", "plain", lambda: success_result("ok")),
        "next": FakeExecutable("next", "plain", lambda: success_result("next-ok")),
    }
    install_fake_builder(monkeypatch, fakes)

    settings = make_settings(
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
    deps = workflow_team_deps()
    await WorkflowEngine(settings).run("p", deps)

    assert [s.status for s in deps.submissions] == ["ERROR", "SUCCESS", "SUCCESS"]
    assert fakes["next"].call_count == 1


@pytest.mark.asyncio
async def test_function_hard_failure_halts_workflow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """function ERROR → WorkflowStepFailedError 即昇格、後続 step 未実行。"""
    fakes = {
        "agent-1": FakeExecutable("agent-1", "plain", lambda: success_result()),
        "fn-1": FakeExecutable("fn-1", "function", lambda: error_result("fn failed")),
        "s2-agent": FakeExecutable("s2-agent", "plain", lambda: success_result()),
    }
    install_fake_builder(
        monkeypatch,
        fakes,
        fail_if=lambda n: n == "s2-agent",
    )

    settings = make_settings(
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
    deps = workflow_team_deps()
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
    """build_executable 例外 → WorkflowStepFailedError 昇格。"""
    fakes: dict[str, FakeExecutable] = {}
    install_fake_builder(
        monkeypatch,
        fakes,
        raise_on={"bad": ValueError("module not found")},
    )

    settings = make_settings(
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
    deps = workflow_team_deps()
    with pytest.raises(WorkflowStepFailedError) as exc_info:
        await WorkflowEngine(settings).run("p", deps)

    assert exc_info.value.step_id == "s1"
    assert exc_info.value.executor_name == "bad"
    assert "failed to build executable" in (exc_info.value.error_message or "")


@pytest.mark.asyncio
async def test_all_messages_concatenation_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """all_messages は step 順 × executor 定義順で連結される。

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
    install_fake_builder(monkeypatch, fakes)

    settings = make_settings(
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
    deps = workflow_team_deps()
    result = await WorkflowEngine(settings).run("p", deps)

    assert [id(m) for m in result.all_messages] == [id(msg_s1a), id(msg_s1b), id(msg_s2a)]


@pytest.mark.asyncio
async def test_total_usage_summed(monkeypatch: pytest.MonkeyPatch) -> None:
    fakes = {
        "e1": FakeExecutable(
            "e1",
            "plain",
            lambda: success_result(usage=RunUsage(input_tokens=10, output_tokens=20, requests=1)),
        ),
        "e2": FakeExecutable(
            "e2",
            "plain",
            lambda: success_result(usage=RunUsage(input_tokens=5, output_tokens=7, requests=1)),
        ),
    }
    install_fake_builder(monkeypatch, fakes)

    settings = make_settings(
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
    deps = workflow_team_deps()
    result = await WorkflowEngine(settings).run("p", deps)

    assert result.total_usage.input_tokens == 15
    assert result.total_usage.output_tokens == 27
    assert result.total_usage.requests == 2
