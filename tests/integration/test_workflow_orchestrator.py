"""`Orchestrator.execute` で team mode と workflow mode を混在させた並列実行の検証。

`orchestrator.toml` に `team` 設定 (`tests/fixtures/team1.toml`) と
`workflow` 設定 (`tmp_path/workflow.toml`) を絶対 path で 2 件登録し、
`load_orchestrator_settings` 経由で読み込んで `Orchestrator.execute` を回す。

team 側は `mixseek.round_controller.strategy.create_leader_agent` を mock し、
workflow 側は `mixseek.workflow.engine.build_executable` を fake builder に
差し替えることで、両モードの実コードパスを通しつつ LLM/外部依存を除去する。
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic_ai import RunUsage

from mixseek.evaluator import EvaluationResult
from mixseek.models.evaluation_result import MetricScore
from mixseek.orchestrator import Orchestrator
from mixseek.orchestrator.orchestrator import load_orchestrator_settings
from mixseek.round_controller.models import ImprovementJudgment
from mixseek.storage.aggregation_store import AggregationStore
from mixseek.workflow.models import ExecutableResult

from ._workflow_helpers import (
    FakeExecutable,
    clear_orchestrator_env,
    install_fake_builder,
    success,
    write_workflow_toml,
)


def _make_success_factory(name: str) -> Callable[[int], ExecutableResult]:
    """`name` をクロージャに束ねて 1-arg `result_factory` を生成する。

    dict comprehension 内で lambda + デフォルト引数を使うとループ変数の遅延束縛問題を
    回避できるが mypy が lambda の型を推論できない。明示型注釈付きの helper にして
    `Callable[[int], ExecutableResult]` を確定させる。
    """

    def _factory(_call_count: int) -> ExecutableResult:
        return success(content=f"{name}-out")

    return _factory


TEAM1_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "team1.toml"


def _build_evaluator_mock(score: float = 80.0) -> MagicMock:
    """workflow / team 共用の Evaluator mock。固定スコアを返す。"""
    evaluator = MagicMock()
    evaluator.evaluate = AsyncMock(
        return_value=EvaluationResult(
            metrics=[MetricScore(metric_name="ClarityCoherence", score=score, evaluator_comment="ok")],
            overall_score=score,
        )
    )
    return evaluator


def _build_judgment_mock(*, should_continue: bool = False) -> MagicMock:
    """team / workflow 共用の Judgment mock。"""
    client = MagicMock()
    client.judge_improvement_prospects = AsyncMock(
        return_value=ImprovementJudgment(
            should_continue=should_continue,
            reasoning="orchestrator integration test",
            confidence_score=0.9,
        )
    )
    return client


def _build_leader_agent_mock() -> MagicMock:
    """team 側の Leader Agent mock。`create_leader_agent` の戻り値として使う。"""
    leader_agent = AsyncMock()
    leader_result = MagicMock()
    leader_result.output = "team final submission"
    leader_result.all_messages.return_value = []
    leader_result.usage.return_value = RunUsage(input_tokens=10, output_tokens=5, requests=1)
    leader_agent.run.return_value = leader_result
    return leader_agent


def _write_orchestrator_toml(
    path: Path,
    *,
    team_config: Path,
    workflow_config: Path,
    max_rounds: int = 3,
    min_rounds: int = 1,
) -> None:
    """orchestrator.toml を team + workflow の 2 entry 構成で書き出す。"""
    path.write_text(
        "[orchestrator]\n"
        "timeout_per_team_seconds = 60\n"
        "max_retries_per_team = 0\n"
        f"max_rounds = {max_rounds}\n"
        f"min_rounds = {min_rounds}\n\n"
        "[[orchestrator.teams]]\n"
        f'config = "{team_config}"\n\n'
        "[[orchestrator.teams]]\n"
        f'config = "{workflow_config}"\n',
        encoding="utf-8",
    )


@pytest.mark.asyncio
@pytest.mark.integration
@patch("mixseek.round_controller.strategy.create_leader_agent")
@patch("mixseek.round_controller.controller.JudgmentClient")
@patch("mixseek.round_controller.controller.Evaluator")
async def test_orchestrator_runs_team_and_workflow_in_parallel(
    mock_evaluator_class: MagicMock,
    mock_judgment_client_class: MagicMock,
    mock_create_leader: MagicMock,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """team + workflow 混在の並列実行が成功し、両 entry が ExecutionSummary に含まれる。

    検証ポイント (計画書 §4 主要検証):
        1. team_results が 2 件
        2. team_id 集合 = {test-team-001, test-workflow-001}
        3. 全 entry が final_submission=True
        4. failed_teams_info == []
        5. DuckDB execution_summary.status == "completed", total_teams == 2
        6. round_history が各 team_id ごとに 1 件以上
    """
    # 別テスト由来の MIXSEEK_* 環境変数残留を排除して TOML 値の優先を担保
    clear_orchestrator_env(monkeypatch)

    # workflow 側の FakeExecutable: workflow.toml の executor 4 件分
    fakes: dict[str, FakeExecutable] = {
        name: FakeExecutable(
            name=name,
            executor_type=("function" if name == "fn-formatter" else "plain"),
            result_factory=_make_success_factory(name),
        )
        for name in ("agent-a", "agent-b", "fn-formatter", "agent-c")
    }
    install_fake_builder(monkeypatch, fakes)

    # team 側の Leader Agent mock
    mock_create_leader.return_value = _build_leader_agent_mock()

    # Evaluator / Judgment mock (team / workflow 共用)
    mock_evaluator_class.return_value = _build_evaluator_mock(score=80.0)
    mock_judgment_client_class.return_value = _build_judgment_mock(should_continue=False)

    workflow_toml = tmp_path / "workflow.toml"
    write_workflow_toml(workflow_toml, workflow_id="test-workflow-001", workflow_name="Test Workflow")

    orchestrator_toml = tmp_path / "orchestrator.toml"
    _write_orchestrator_toml(orchestrator_toml, team_config=TEAM1_FIXTURE, workflow_config=workflow_toml)

    settings = load_orchestrator_settings(orchestrator_toml, workspace=tmp_path)
    orchestrator = Orchestrator(settings=settings)

    summary = await orchestrator.execute(user_prompt="multi-team test", timeout_seconds=60)

    # (1)(2) 両 team の結果が含まれる
    assert len(summary.team_results) == 2
    result_team_ids = {r.team_id for r in summary.team_results}
    assert result_team_ids == {"test-team-001", "test-workflow-001"}

    # (3) 全 entry が final_submission=True
    assert all(r.final_submission for r in summary.team_results)

    # (4) 失敗チームなし
    assert summary.failed_teams_info == []

    # (5)(6) DuckDB に保存された execution_summary / round_history
    store = AggregationStore(db_path=tmp_path / "mixseek.db")
    conn = store._get_connection()

    summary_row = conn.execute(
        "SELECT status, total_teams FROM execution_summary ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    assert summary_row is not None
    assert summary_row[0] == "completed"
    assert summary_row[1] == 2

    for team_id in ("test-team-001", "test-workflow-001"):
        count_row = conn.execute("SELECT COUNT(*) FROM round_history WHERE team_id = ?", [team_id]).fetchone()
        assert count_row is not None
        assert count_row[0] >= 1, f"team {team_id} should have at least one round_history row"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_orchestrator_rejects_workflow_id_colliding_with_team_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """workflow_id と team_id の重複が `Orchestrator._execute_impl` で検出される。

    `_execute_impl` の重複ガードは Strategy / RoundController 構築前に走るため、
    Evaluator / Judgment / Leader / build_executable をどれも呼ばずに
    `ValueError("Duplicate team_id ...")` が raise される。

    本テストは `build_executable` が呼ばれたら即 `pytest.fail` する fake を仕込み、
    重複ガードが Strategy 構築前に作動していることも併せて検証する。
    """

    clear_orchestrator_env(monkeypatch)

    def _fake_builder_must_not_be_called(*_args: Any, **_kwargs: Any) -> Any:
        pytest.fail("build_executable must not be called when duplicate team_id detected")

    from mixseek.workflow import engine as engine_module

    monkeypatch.setattr(engine_module, "build_executable", _fake_builder_must_not_be_called)

    # workflow_id を team1.toml の team_id ("test-team-001") に揃える
    workflow_toml = tmp_path / "workflow_dup.toml"
    write_workflow_toml(workflow_toml, workflow_id="test-team-001", workflow_name="Dup")

    orchestrator_toml = tmp_path / "orchestrator.toml"
    _write_orchestrator_toml(
        orchestrator_toml,
        team_config=TEAM1_FIXTURE,
        workflow_config=workflow_toml,
        max_rounds=1,
    )

    settings = load_orchestrator_settings(orchestrator_toml, workspace=tmp_path)
    orchestrator = Orchestrator(settings=settings)

    with pytest.raises(ValueError, match="Duplicate team_id"):
        await orchestrator.execute(user_prompt="dup test", timeout_seconds=60)
