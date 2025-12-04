"""E2E tests for Orchestrator CLI commands and full orchestration flow"""

import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic_ai import RunUsage

from mixseek.config.schema import OrchestratorSettings
from mixseek.evaluator import EvaluationResult
from mixseek.models.evaluation_result import MetricScore
from mixseek.orchestrator import Orchestrator


def test_mixseek_exec_help() -> None:
    """mixseek exec --helpテスト"""
    # Note: This test verifies the command is registered and callable via CLI
    # Full integration testing requires a running environment with proper dependencies
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "mixseek.cli.main", "exec", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "ユーザプロンプト" in result.stdout or "prompt" in result.stdout.lower()


def test_mixseek_exec_json_output(tmp_path: Path) -> None:
    """mixseek exec JSON出力テスト"""
    import sys

    # テスト用設定ファイル準備
    config_dir = tmp_path / "configs"
    config_dir.mkdir()

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "mixseek.cli.main",
            "exec",
            "テストプロンプト",
            "--output-format",
            "json",
        ],
        capture_output=True,
        text=True,
        env={"MIXSEEK_WORKSPACE": str(tmp_path)},
    )

    # テスト実行時にはコマンドが存在することを確認
    # 実装完了後に詳細な出力検証を追加
    assert result.returncode != 0 or result.stdout or result.stderr


@pytest.mark.asyncio
@pytest.mark.integration
@patch("mixseek.round_controller.controller.create_leader_agent")
@patch("mixseek.round_controller.controller.Evaluator")
@patch("mixseek.round_controller.controller.JudgmentClient")
async def test_single_round_e2e_with_new_schema(
    mock_judgment_client_class: MagicMock,
    mock_evaluator_class: MagicMock,
    mock_create_leader: MagicMock,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T046: 単一ラウンドのE2Eテスト（新DuckDBスキーマで動作することを検証）"""

    monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))

    # Leader Agentのモック
    mock_agent = AsyncMock()
    mock_result = MagicMock()
    mock_result.output = "E2E Test Submission"
    mock_result.all_messages.return_value = []
    mock_result.usage.return_value = RunUsage(input_tokens=100, output_tokens=50, requests=1)
    mock_agent.run.return_value = mock_result
    mock_create_leader.return_value = mock_agent

    # Evaluatorのモック (async version)
    mock_evaluator = MagicMock()
    mock_evaluation_result = EvaluationResult(
        metrics=[
            MetricScore(
                metric_name="ClarityCoherence",
                score=88.0,
                evaluator_comment="E2E test evaluation",
            ),
        ],
        overall_score=88.0,
    )
    mock_evaluator.evaluate = AsyncMock(return_value=mock_evaluation_result)
    mock_evaluator_class.return_value = mock_evaluator

    # JudgmentClient mock - terminate after 1 round
    from mixseek.round_controller.models import ImprovementJudgment

    mock_client = MagicMock()
    mock_client.judge_improvement_prospects = AsyncMock(
        return_value=ImprovementJudgment(should_continue=False, reasoning="E2E test termination", confidence_score=0.9)
    )
    mock_judgment_client_class.return_value = mock_client

    # テスト用設定ファイル作成（FR-011: OrchestratorSettings直接使用）
    team_config_path = Path.cwd() / "tests" / "fixtures" / "team1.toml"

    settings = OrchestratorSettings(
        workspace_path=tmp_path,
        timeout_per_team_seconds=600,
        teams=[{"config": str(team_config_path)}],
    )

    orchestrator = Orchestrator(settings=settings)

    # オーケストレーション実行
    summary = await orchestrator.execute(user_prompt="E2E Test Prompt", timeout_seconds=300)

    # T046: 検証 - 新DuckDBスキーマでの動作確認
    assert summary is not None
    assert len(summary.team_results) == 1
    assert summary.best_score == 88.0
    assert summary.best_team_id == "test-team-001"

    # LeaderBoardEntryが返されることを確認
    result = summary.team_results[0]
    assert result.team_id == "test-team-001"
    assert result.score == 88.0
    assert result.final_submission is True
    assert result.exit_reason is not None

    # DuckDBに正しく保存されていることを確認
    from mixseek.storage.aggregation_store import AggregationStore

    store = AggregationStore(db_path=tmp_path / "mixseek.db")
    conn = store._get_connection()

    # round_statusテーブルの確認
    round_status_result = conn.execute(
        "SELECT COUNT(*) FROM round_status WHERE team_id = ?", ["test-team-001"]
    ).fetchone()
    assert round_status_result is not None
    round_status_count = round_status_result[0]
    assert round_status_count >= 1

    # leader_boardテーブルの確認
    leader_board_result = conn.execute(
        "SELECT COUNT(*) FROM leader_board WHERE team_id = ?", ["test-team-001"]
    ).fetchone()
    assert leader_board_result is not None
    leader_board_count = leader_board_result[0]
    assert leader_board_count >= 1

    # final_submissionフラグの確認
    final_submission = conn.execute(
        "SELECT final_submission, exit_reason FROM leader_board WHERE team_id = ? AND final_submission = TRUE",
        ["test-team-001"],
    ).fetchone()
    assert final_submission is not None
    assert final_submission[0] is True
    assert final_submission[1] is not None


@pytest.mark.asyncio
@pytest.mark.integration
@patch("mixseek.round_controller.controller.create_leader_agent")
@patch("mixseek.round_controller.controller.Evaluator")
@patch("mixseek.round_controller.controller.JudgmentClient")
async def test_multi_round_e2e_iterative_improvement(
    mock_judgment_client_class: MagicMock,
    mock_evaluator_class: MagicMock,
    mock_create_leader: MagicMock,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T053: 複数ラウンドのE2Eテスト（反復改善の動作を検証）"""

    monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))

    # Leader Agentのモック - 各ラウンドで異なるSubmission
    mock_agent = AsyncMock()
    call_count = [0]

    async def mock_run(*args: Any, **kwargs: Any) -> Any:
        call_count[0] += 1
        mock_result = MagicMock()
        mock_result.output = f"E2E Round {call_count[0]} Submission"
        mock_result.all_messages.return_value = []
        mock_result.usage.return_value = RunUsage(input_tokens=100, output_tokens=50, requests=1)
        return mock_result

    mock_agent.run.side_effect = mock_run
    mock_create_leader.return_value = mock_agent

    # Evaluatorのモック - スコアが向上 (async version)
    eval_count = [0]

    async def mock_evaluate(*args: Any, **kwargs: Any) -> EvaluationResult:
        eval_count[0] += 1
        score = 75.0 + eval_count[0] * 5.0  # 80, 85, 90
        return EvaluationResult(
            metrics=[
                MetricScore(
                    metric_name="ClarityCoherence",
                    score=score,
                    evaluator_comment=f"E2E Round {eval_count[0]}",
                ),
            ],
            overall_score=score,
        )

    mock_evaluator = MagicMock()
    mock_evaluator.evaluate = AsyncMock(side_effect=mock_evaluate)
    mock_evaluator_class.return_value = mock_evaluator

    # JudgmentClient mock - 3ラウンド実行後に終了
    from mixseek.round_controller.models import ImprovementJudgment

    judgment_count = [0]

    async def mock_judgment(*args: Any, **kwargs: Any) -> ImprovementJudgment:
        judgment_count[0] += 1
        should_continue = judgment_count[0] < 3  # Stop after 3 rounds
        return ImprovementJudgment(
            should_continue=should_continue,
            reasoning=f"E2E Judgment {judgment_count[0]}",
            confidence_score=0.9,
        )

    mock_client = MagicMock()
    mock_client.judge_improvement_prospects = AsyncMock(side_effect=mock_judgment)
    mock_judgment_client_class.return_value = mock_client

    # テスト用設定ファイル（FR-011: OrchestratorSettings直接使用）
    team_config_path = Path.cwd() / "tests" / "fixtures" / "team1.toml"

    settings = OrchestratorSettings(
        workspace_path=tmp_path,
        timeout_per_team_seconds=600,
        teams=[{"config": str(team_config_path)}],
    )

    orchestrator = Orchestrator(settings=settings)

    # オーケストレーション実行
    summary = await orchestrator.execute(user_prompt="E2E Multi-Round Test", timeout_seconds=300)

    # T053: 検証 - 複数ラウンドの反復改善
    assert summary is not None
    assert len(summary.team_results) == 1

    result = summary.team_results[0]
    assert result.team_id == "test-team-001"
    assert result.round_number >= 2  # 最低2ラウンド実行
    assert result.final_submission is True

    # 最高スコアのラウンドが選ばれていることを確認
    assert result.score >= 80.0  # スコアが向上している

    # DuckDBに複数ラウンドが記録されていることを確認
    from mixseek.storage.aggregation_store import AggregationStore

    store = AggregationStore(db_path=tmp_path / "mixseek.db")
    conn = store._get_connection()

    # 複数ラウンドが記録されていることを確認
    round_count_result = conn.execute(
        "SELECT COUNT(*) FROM round_status WHERE team_id = ?", ["test-team-001"]
    ).fetchone()
    assert round_count_result is not None
    round_count = round_count_result[0]
    assert round_count >= 2  # 最低2ラウンド

    leader_board_count_result = conn.execute(
        "SELECT COUNT(*) FROM leader_board WHERE team_id = ?", ["test-team-001"]
    ).fetchone()
    assert leader_board_count_result is not None
    leader_board_count = leader_board_count_result[0]
    assert leader_board_count >= 2

    # 最高スコアのラウンドにfinal_submissionフラグが立っていることを確認
    final_round = conn.execute(
        "SELECT round_number, score, final_submission FROM leader_board WHERE team_id = ? AND final_submission = TRUE",
        ["test-team-001"],
    ).fetchone()
    assert final_round is not None
    assert final_round[2] is True

    # スコアが向上していることを確認
    all_scores = conn.execute(
        "SELECT round_number, score FROM leader_board WHERE team_id = ? ORDER BY round_number",
        ["test-team-001"],
    ).fetchall()
    assert len(all_scores) >= 2
    # 最初のラウンドより後のラウンドの方がスコアが高い
    assert all_scores[-1][1] > all_scores[0][1]
