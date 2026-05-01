"""Workflow mode の `WorkflowStepFailedError` 経由ハード失敗経路の E2E 検証。

PR5 で最も重要なテストファイル。`function executor` の ERROR が
`WorkflowEngine._execute_step` で `WorkflowStepFailedError` に昇格し、
`Orchestrator._run_team` の except 経路で `_try_recover_partial_failure` が
動く一連の流れを実コードパスで通す。

Test 1: Round 1 ハード失敗 → 全ラウンド失敗 (`team_statuses[...] = "failed"`)
Test 2: Round 1 成功 → Round 2 ハード失敗 → partial_failure リカバリ
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mixseek.evaluator import EvaluationResult
from mixseek.models.evaluation_result import MetricScore
from mixseek.orchestrator import Orchestrator
from mixseek.orchestrator.orchestrator import load_orchestrator_settings
from mixseek.round_controller.models import ImprovementJudgment
from mixseek.storage.aggregation_store import AggregationStore

from ._workflow_helpers import (
    FakeExecutable,
    clear_orchestrator_env,
    error,
    install_fake_builder,
    success,
    write_workflow_toml,
)


def _single_step_with_function_steps_text(function_executor_name: str) -> str:
    """`agent-a` (plain) + 指定 function executor の 1 ステップ workflow を生成する。

    `s1` のみで構成し、function 失敗で Round 全体が即落ちる挙動を検証するため。
    """
    return (
        "[[workflow.steps]]\n"
        'id = "s1"\n\n'
        "[[workflow.steps.executors]]\n"
        'name = "agent-a"\n'
        'type = "plain"\n\n'
        "[[workflow.steps.executors]]\n"
        f'name = "{function_executor_name}"\n'
        'type = "function"\n\n'
        "[workflow.steps.executors.plugin]\n"
        'module = "tests.integration._workflow_helpers"\n'
        'function = "noop_function"\n'
    )


def _write_orchestrator_toml_for_workflow(
    path: Path,
    *,
    workflow_config: Path,
    max_rounds: int,
    min_rounds: int = 1,
) -> None:
    """workflow を 1 件だけ持つ orchestrator.toml を書き出す。"""
    path.write_text(
        "[orchestrator]\n"
        "timeout_per_team_seconds = 60\n"
        "max_retries_per_team = 0\n"
        f"max_rounds = {max_rounds}\n"
        f"min_rounds = {min_rounds}\n\n"
        "[[orchestrator.teams]]\n"
        f'config = "{workflow_config}"\n',
        encoding="utf-8",
    )


@pytest.mark.asyncio
@pytest.mark.integration
@patch("mixseek.round_controller.controller.JudgmentClient")
@patch("mixseek.round_controller.controller.Evaluator")
async def test_workflow_round1_function_failure_marks_team_failed(
    mock_evaluator_class: MagicMock,
    mock_judgment_client_class: MagicMock,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Round 1 で function ERROR → `WorkflowStepFailedError` で全ラウンド失敗扱い。

    検証ポイント (計画書 §5 Test 1):
        - summary.team_results == []
        - failed_teams_info に 1 件、error_message に "WorkflowStepFailedError" を含む
        - team_statuses["test-workflow-001"].status == "failed"
        - DuckDB round_history / leader_board / round_status の該当 team_id 行 0 件
        - DuckDB execution_summary.status == "failed", total_teams == 1
        - Evaluator / Judgment mock は **呼ばれない** (round_started_at 前に raise)
    """
    clear_orchestrator_env(monkeypatch)

    fakes: dict[str, FakeExecutable] = {
        "agent-a": FakeExecutable(
            name="agent-a",
            executor_type="plain",
            result_factory=lambda _n: success(content="a-ok"),
        ),
        "fn-bad": FakeExecutable(
            name="fn-bad",
            executor_type="function",
            result_factory=lambda _n: error("fn boom in r1"),
        ),
    }
    install_fake_builder(monkeypatch, fakes)

    # Evaluator / Judgment mock (呼ばれないはずだが構築時の AttributeError 回避のため作る)
    mock_evaluator = MagicMock()
    mock_evaluator.evaluate = AsyncMock(
        return_value=EvaluationResult(
            metrics=[MetricScore(metric_name="C", score=0.0, evaluator_comment="never")],
            overall_score=0.0,
        )
    )
    mock_evaluator_class.return_value = mock_evaluator

    mock_client = MagicMock()
    mock_client.judge_improvement_prospects = AsyncMock(
        return_value=ImprovementJudgment(should_continue=False, reasoning="never", confidence_score=0.0)
    )
    mock_judgment_client_class.return_value = mock_client

    workflow_toml = tmp_path / "workflow.toml"
    write_workflow_toml(
        workflow_toml,
        workflow_id="test-workflow-001",
        workflow_name="Hard Fail R1",
        steps_text=_single_step_with_function_steps_text("fn-bad"),
    )

    orchestrator_toml = tmp_path / "orchestrator.toml"
    _write_orchestrator_toml_for_workflow(orchestrator_toml, workflow_config=workflow_toml, max_rounds=3)

    settings = load_orchestrator_settings(orchestrator_toml, workspace=tmp_path)
    orchestrator = Orchestrator(settings=settings)

    summary = await orchestrator.execute(user_prompt="hard fail r1", timeout_seconds=60)

    # 全ラウンド失敗 → team_results は空
    assert summary.team_results == []
    assert len(summary.failed_teams_info) == 1
    failed = summary.failed_teams_info[0]
    assert failed.team_id == "test-workflow-001"
    assert "WorkflowStepFailedError" in failed.error_message

    # team status
    status = await orchestrator.get_team_status("test-workflow-001")
    assert status.status == "failed"
    assert status.error_message is not None
    assert "WorkflowStepFailedError" in status.error_message

    # DuckDB: round_history / leader_board / round_status は team_id について 0 件
    store = AggregationStore(db_path=tmp_path / "mixseek.db")
    conn = store._get_connection()
    for table in ("round_history", "leader_board", "round_status"):
        row = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE team_id = ?", ["test-workflow-001"]).fetchone()
        assert row is not None
        assert row[0] == 0, f"table {table} should have 0 rows for failed workflow team"

    # execution_summary
    summary_row = conn.execute(
        "SELECT status, total_teams FROM execution_summary ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    assert summary_row is not None
    assert summary_row[0] == "failed"
    assert summary_row[1] == 1

    # Evaluator / Judgment は呼ばれない (Round 1 が strategy.execute 内で raise されるため)
    mock_evaluator.evaluate.assert_not_awaited()
    mock_client.judge_improvement_prospects.assert_not_awaited()

    # FakeExecutable は build_executable 経由で作られて 1 回ずつ run された
    # (Engine は asyncio.gather で全 executor を完了させてから昇格判定する)
    assert fakes["agent-a"].call_count == 1
    assert fakes["fn-bad"].call_count == 1


@pytest.mark.asyncio
@pytest.mark.integration
@patch("mixseek.round_controller.controller.JudgmentClient")
@patch("mixseek.round_controller.controller.Evaluator")
async def test_workflow_round2_function_failure_keeps_round1_via_partial_failure(
    mock_evaluator_class: MagicMock,
    mock_judgment_client_class: MagicMock,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Round 1 成功 → Round 2 ハード失敗 → partial_failure リカバリで Round 1 を最終 entry 化。

    検証ポイント (計画書 §5 Test 2):
        - summary.team_results に 1 件 (Round 1 の entry)
        - entry: team_id, round_number=1, score=80.0, exit_reason="partial_failure",
          final_submission=True
        - failed_teams_info にも 1 件 (status=failed)
        - team_statuses[...].status == "failed" (partial_failure 時に上書きしない実装)
        - DuckDB:
            * round_history: round_number=1 のみ
            * round_status: round_number=1 のみ
            * leader_board: round_number=1 が final_submission=TRUE/exit_reason="partial_failure"
              (UPSERT で更新)
            * execution_summary.status == "partial_failure"
        - fakes["agent-a"].call_count == 2, fakes["fn-flaky"].call_count == 2
    """
    clear_orchestrator_env(monkeypatch)

    fakes: dict[str, FakeExecutable] = {
        "agent-a": FakeExecutable(
            name="agent-a",
            executor_type="plain",
            result_factory=lambda n: success(content=f"a-r{n}"),
        ),
        "fn-flaky": FakeExecutable(
            name="fn-flaky",
            executor_type="function",
            # Round 1 (call_count==1) で SUCCESS、Round 2 (call_count==2) で ERROR
            result_factory=lambda n: success(content="ok") if n == 1 else error("flaky boom in r2"),
        ),
    }
    install_fake_builder(monkeypatch, fakes)

    # Evaluator: Round 1 で 1 回だけ呼ばれて 80.0 を返す (Round 2 は raise されるため呼ばれない)
    mock_evaluator = MagicMock()
    mock_evaluator.evaluate = AsyncMock(
        return_value=EvaluationResult(
            metrics=[MetricScore(metric_name="ClarityCoherence", score=80.0, evaluator_comment="r1 ok")],
            overall_score=80.0,
        )
    )
    mock_evaluator_class.return_value = mock_evaluator

    # Judgment: Round 1 後に should_continue=True を返して Round 2 へ進ませる
    mock_client = MagicMock()
    mock_client.judge_improvement_prospects = AsyncMock(
        return_value=ImprovementJudgment(
            should_continue=True,
            reasoning="continue to r2",
            confidence_score=0.8,
        )
    )
    mock_judgment_client_class.return_value = mock_client

    workflow_toml = tmp_path / "workflow.toml"
    write_workflow_toml(
        workflow_toml,
        workflow_id="test-workflow-001",
        workflow_name="Partial Fail R2",
        steps_text=_single_step_with_function_steps_text("fn-flaky"),
    )

    orchestrator_toml = tmp_path / "orchestrator.toml"
    _write_orchestrator_toml_for_workflow(orchestrator_toml, workflow_config=workflow_toml, max_rounds=3)

    settings = load_orchestrator_settings(orchestrator_toml, workspace=tmp_path)
    orchestrator = Orchestrator(settings=settings)

    summary = await orchestrator.execute(user_prompt="partial fail r2", timeout_seconds=60)

    # team_results に Round 1 の partial_failure entry が 1 件
    assert len(summary.team_results) == 1
    entry = summary.team_results[0]
    assert entry.team_id == "test-workflow-001"
    assert entry.round_number == 1
    assert entry.score == 80.0
    assert entry.exit_reason == "partial_failure"
    assert entry.final_submission is True

    # failed_teams_info にも team_id が含まれる (status は failed のまま)
    assert len(summary.failed_teams_info) == 1
    assert summary.failed_teams_info[0].team_id == "test-workflow-001"

    status = await orchestrator.get_team_status("test-workflow-001")
    assert status.status == "failed"

    # FakeExecutable は Round 1 / Round 2 で 1 回ずつ = 2 回ずつ呼ばれた
    assert fakes["agent-a"].call_count == 2
    assert fakes["fn-flaky"].call_count == 2

    # Evaluator は Round 1 のみ 1 回呼ばれる (Round 2 は raise されるため呼ばれない)
    assert mock_evaluator.evaluate.await_count == 1
    # Judgment も Round 1 後に 1 回だけ呼ばれる
    assert mock_client.judge_improvement_prospects.await_count == 1

    # DuckDB 検証
    store = AggregationStore(db_path=tmp_path / "mixseek.db")
    conn = store._get_connection()

    # round_history: round_number=1 のみ
    rh_rows = conn.execute(
        "SELECT round_number FROM round_history WHERE team_id = ? ORDER BY round_number",
        ["test-workflow-001"],
    ).fetchall()
    assert [r[0] for r in rh_rows] == [1]

    # round_status: round_number=1 のみ
    rs_rows = conn.execute(
        "SELECT round_number FROM round_status WHERE team_id = ? ORDER BY round_number",
        ["test-workflow-001"],
    ).fetchall()
    assert [r[0] for r in rs_rows] == [1]

    # leader_board: round_number=1 が final_submission=TRUE / exit_reason="partial_failure"
    lb_rows = conn.execute(
        "SELECT round_number, final_submission, exit_reason FROM leader_board WHERE team_id = ?",
        ["test-workflow-001"],
    ).fetchall()
    assert len(lb_rows) == 1
    lb_round, lb_final, lb_exit = lb_rows[0]
    assert lb_round == 1
    assert lb_final is True
    assert lb_exit == "partial_failure"

    # execution_summary
    summary_row = conn.execute(
        "SELECT status, total_teams FROM execution_summary ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    assert summary_row is not None
    assert summary_row[0] == "partial_failure"
    assert summary_row[1] == 1
