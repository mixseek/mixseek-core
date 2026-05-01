"""`RoundController.run_round` を workflow TOML で起動し、DuckDB の team/workflow
共通形式で round_history / leader_board / round_status が保存されることを検証する。

`mixseek.workflow.engine.build_executable` を `_workflow_helpers.install_fake_builder`
で差し替えるため、Engine 本体 (`asyncio.gather` / 昇格判定 / submission 配線 /
message 連結) は実物のまま動く。Evaluator / JudgmentClient は controller 側で
patch して LLM 呼び出しを除去する。
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mixseek.config import ConfigurationManager
from mixseek.evaluator import EvaluationResult
from mixseek.models.evaluation_result import MetricScore
from mixseek.orchestrator.models import OrchestratorTask
from mixseek.round_controller import RoundController
from mixseek.round_controller.models import ImprovementJudgment
from mixseek.storage.aggregation_store import AggregationStore

from ._workflow_helpers import (
    FakeExecutable,
    install_fake_builder,
    success,
    write_workflow_toml,
)


@pytest.mark.asyncio
@pytest.mark.integration
@patch("mixseek.round_controller.controller.JudgmentClient")
@patch("mixseek.round_controller.controller.Evaluator")
async def test_round_controller_runs_workflow_and_persists_team_format(
    mock_evaluator_class: MagicMock,
    mock_judgment_client_class: MagicMock,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """workflow を 1 ラウンドで完了させ、team mode と同形式の DuckDB レコードを検証する。

    検証ポイント (計画書 §3 主要検証):
        1. LeaderBoardEntry.team_id == workflow_id ("test-workflow-001")
        2. final_submission=True / exit_reason="no_improvement_expected"
        3. submission_content は `{"steps": {"s1": [...], "s2": [...], "s3": [...]}}` JSON
        4. round_history.member_submissions_record に 4 件の submission
           (agent-a / agent-b / fn-formatter / agent-c の TOML 定義順)
        5. agent_type 集合が {"plain", "function"} を含む
        6. round_history.message_history が JSON 配列として保存される
        7. leader_board に final_submission=TRUE が 1 件、score == 85.0
        8. round_status の should_continue == False
        9. 各 FakeExecutable.call_count == 1 (1 ラウンドで 1 回呼ばれる)
    """
    # FakeExecutable を 4 件 (agent-a / agent-b / fn-formatter / agent-c) 用意
    fakes: dict[str, FakeExecutable] = {
        "agent-a": FakeExecutable(
            name="agent-a",
            executor_type="plain",
            result_factory=lambda _n: success(content="A-out"),
        ),
        "agent-b": FakeExecutable(
            name="agent-b",
            executor_type="plain",
            result_factory=lambda _n: success(content="B-out"),
        ),
        "fn-formatter": FakeExecutable(
            name="fn-formatter",
            executor_type="function",
            result_factory=lambda _n: success(content="formatted"),
        ),
        "agent-c": FakeExecutable(
            name="agent-c",
            executor_type="plain",
            result_factory=lambda _n: success(content="C-final"),
        ),
    }
    install_fake_builder(monkeypatch, fakes)

    # Evaluator mock: 固定スコア 85.0 を返す
    mock_evaluator = MagicMock()
    mock_evaluator.evaluate = AsyncMock(
        return_value=EvaluationResult(
            metrics=[
                MetricScore(
                    metric_name="ClarityCoherence",
                    score=85.0,
                    evaluator_comment="workflow integration test",
                )
            ],
            overall_score=85.0,
        )
    )
    mock_evaluator_class.return_value = mock_evaluator

    # Judgment mock: 1 ラウンドで終了 (should_continue=False)
    mock_client = MagicMock()
    mock_client.judge_improvement_prospects = AsyncMock(
        return_value=ImprovementJudgment(
            should_continue=False,
            reasoning="single round ok",
            confidence_score=0.95,
        )
    )
    mock_judgment_client_class.return_value = mock_client

    # workflow TOML 書き出し (デフォルト 3 ステップ構成)
    toml_path = tmp_path / "workflow.toml"
    write_workflow_toml(toml_path, workflow_id="test-workflow-001", workflow_name="Test Workflow")

    # Settings をデフォルト値で取得
    config_manager = ConfigurationManager(workspace=tmp_path)
    evaluator_settings = config_manager.get_evaluator_settings(None)
    judgment_settings = config_manager.get_judgment_settings(None)
    prompt_builder_settings = config_manager.get_prompt_builder_settings(None)

    task = OrchestratorTask(
        user_prompt="workflow integration test",
        team_configs=[toml_path],
        timeout_seconds=60,
        max_rounds=3,
        min_rounds=1,
    )

    controller = RoundController(
        team_config_path=toml_path,
        workspace=tmp_path,
        task=task,
        evaluator_settings=evaluator_settings,
        judgment_settings=judgment_settings,
        prompt_builder_settings=prompt_builder_settings,
    )

    entry = await controller.run_round(user_prompt="workflow integration test", timeout_seconds=60)

    # (1) team_id にも workflow_id の値が入る (TeamSettings/WorkflowSettings 共通インターフェース)
    assert entry.team_id == "test-workflow-001"
    assert entry.team_name == "Test Workflow"

    # (2) final_submission / exit_reason
    assert entry.final_submission is True
    assert entry.exit_reason == "no_improvement_expected"
    assert entry.score == 85.0

    # (3) submission_content の JSON 構造
    payload = json.loads(entry.submission_content)
    assert set(payload["steps"].keys()) == {"s1", "s2", "s3"}
    assert [out["executor_name"] for out in payload["steps"]["s1"]] == ["agent-a", "agent-b"]
    assert [out["executor_name"] for out in payload["steps"]["s2"]] == ["fn-formatter"]
    assert [out["executor_name"] for out in payload["steps"]["s3"]] == ["agent-c"]
    assert payload["steps"]["s3"][0]["content"] == "C-final"

    # (9) call_count: 各 executor は 1 ラウンドで 1 回呼ばれる
    for name in ("agent-a", "agent-b", "fn-formatter", "agent-c"):
        assert fakes[name].call_count == 1, f"{name} should be called exactly once"

    # DuckDB 検証
    store = AggregationStore(db_path=tmp_path / "mixseek.db")
    conn = store._get_connection()

    # (4) round_history.member_submissions_record の中身
    rows = conn.execute(
        "SELECT round_number, member_submissions_record, message_history "
        "FROM round_history WHERE team_id = ? ORDER BY round_number",
        ["test-workflow-001"],
    ).fetchall()
    assert len(rows) == 1
    round_number, member_record_json, message_history_json = rows[0]
    assert round_number == 1

    member_record = json.loads(member_record_json)
    submissions = member_record["submissions"]
    assert [s["agent_name"] for s in submissions] == ["agent-a", "agent-b", "fn-formatter", "agent-c"]

    # (5) agent_type の集合に plain / function が混在
    agent_types = {s["agent_type"] for s in submissions}
    assert {"plain", "function"} <= agent_types

    # (6) message_history は JSON 配列 (FakeExecutable は all_messages=[] のため空配列)
    parsed_messages = json.loads(message_history_json)
    assert isinstance(parsed_messages, list)
    assert parsed_messages == []

    # (7) leader_board に final_submission=TRUE の行
    lb_rows = conn.execute(
        "SELECT round_number, score, final_submission, exit_reason "
        "FROM leader_board WHERE team_id = ? AND final_submission = TRUE",
        ["test-workflow-001"],
    ).fetchall()
    assert len(lb_rows) == 1
    lb_round, lb_score, lb_final, lb_exit = lb_rows[0]
    assert lb_round == 1
    assert lb_score == 85.0
    assert lb_final is True
    assert lb_exit == "no_improvement_expected"

    # (8) round_status: 1 行、should_continue=False
    rs_rows = conn.execute(
        "SELECT round_number, should_continue FROM round_status WHERE team_id = ? ORDER BY round_number",
        ["test-workflow-001"],
    ).fetchall()
    assert len(rs_rows) == 1
    assert rs_rows[0] == (1, False)
