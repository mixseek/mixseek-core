"""Unit tests for Orchestrator data models"""

from pathlib import Path

import pytest
from pydantic_ai import RunUsage

from mixseek.models.leaderboard import LeaderBoardEntry
from mixseek.orchestrator.models import (
    ExecutionSummary,
    FailedTeamInfo,
    OrchestratorTask,
    PartialTeamFailureError,
    RoundResult,
    TeamStatus,
)


# OrchestratorTask Tests
def test_orchestrator_task_creation() -> None:
    """OrchestratorTask作成テスト"""
    task = OrchestratorTask(
        user_prompt="テストプロンプト",
        team_configs=[Path("team1.toml"), Path("team2.toml")],
        timeout_seconds=600,
    )
    assert task.user_prompt == "テストプロンプト"
    assert len(task.team_configs) == 2
    assert task.timeout_seconds == 600
    assert task.execution_id is not None  # UUIDが自動生成される
    assert task.created_at is not None


def test_orchestrator_task_validation() -> None:
    """OrchestratorTask バリデーションテスト"""
    with pytest.raises(ValueError):
        OrchestratorTask(
            user_prompt="",  # 空文字列
            team_configs=[],
            timeout_seconds=600,
        )

    with pytest.raises(ValueError):
        OrchestratorTask(
            user_prompt="テスト",
            team_configs=[],  # 空リスト
            timeout_seconds=600,
        )


# TeamStatus Tests
def test_team_status_creation() -> None:
    """TeamStatus作成テスト"""
    status = TeamStatus(
        team_id="team-001",
        team_name="Test Team",
    )
    assert status.team_id == "team-001"
    assert status.status == "pending"
    assert status.current_round == 0


def test_team_status_transitions() -> None:
    """TeamStatus ステータス遷移テスト"""
    status = TeamStatus(team_id="team-001", team_name="Test Team")
    status.status = "running"
    assert status.status == "running"

    status.status = "completed"
    assert status.status == "completed"


# RoundResult Tests
def test_round_result_creation() -> None:
    """RoundResult作成テスト"""
    result = RoundResult(
        execution_id="550e8400-e29b-41d4-a716-446655440000",
        team_id="team-001",
        team_name="Test Team",
        round_number=1,
        submission_content="テストSubmission",
        evaluation_score=0.85,
        evaluation_feedback="良好",
        usage=RunUsage(input_tokens=100, output_tokens=200, requests=1),
        execution_time_seconds=30.5,
    )
    assert result.team_id == "team-001"
    assert result.evaluation_score == 0.85
    assert result.execution_time_seconds == 30.5


def test_round_result_validation() -> None:
    """RoundResult unlimited score support test"""
    # Test that unlimited score range is supported (negative, >100, etc.)
    result = RoundResult(
        execution_id="550e8400-e29b-41d4-a716-446655440000",
        team_id="team-001",
        team_name="Test Team",
        round_number=1,
        submission_content="テスト",
        evaluation_score=150.5,  # Score > 100 allowed
        evaluation_feedback="",
        usage=RunUsage(),
        execution_time_seconds=30.0,
    )
    assert result.evaluation_score == 150.5

    # Test negative scores are also allowed
    result_negative = RoundResult(
        execution_id="550e8400-e29b-41d4-a716-446655440000",
        team_id="team-002",
        team_name="Test Team 2",
        round_number=1,
        submission_content="テスト",
        evaluation_score=-42.3,  # Negative score allowed
        evaluation_feedback="",
        usage=RunUsage(),
        execution_time_seconds=30.0,
    )
    assert result_negative.evaluation_score == -42.3


# ExecutionSummary Tests
def test_execution_summary_creation() -> None:
    """ExecutionSummary作成テスト"""
    from mixseek.models.leaderboard import LeaderBoardEntry

    execution_id = "550e8400-e29b-41d4-a716-446655440000"
    result1 = LeaderBoardEntry(
        execution_id=execution_id,
        team_id="team-001",
        team_name="Test Team 1",
        round_number=1,
        submission_content="テストSubmission1",
        score=85.0,
        score_details={"overall_score": 85.0, "feedback": "良好"},
        final_submission=True,
    )
    result2 = LeaderBoardEntry(
        execution_id=execution_id,
        team_id="team-002",
        team_name="Test Team 2",
        round_number=1,
        submission_content="テストSubmission2",
        score=92.0,
        score_details={"overall_score": 92.0, "feedback": "優秀"},
        final_submission=True,
    )

    summary = ExecutionSummary(
        execution_id=execution_id,
        user_prompt="テストプロンプト",
        team_results=[result1, result2],
        best_team_id="team-002",
        best_score=92.0,
        total_execution_time_seconds=45.3,
    )

    assert summary.total_teams == 2
    assert summary.completed_teams == 2
    assert summary.failed_teams == 0


def test_execution_summary_with_failed_teams() -> None:
    """ExecutionSummary失敗チーム含むテスト"""
    from mixseek.models.leaderboard import LeaderBoardEntry

    execution_id = "550e8400-e29b-41d4-a716-446655440000"
    result1 = LeaderBoardEntry(
        execution_id=execution_id,
        team_id="team-001",
        team_name="Test Team 1",
        round_number=1,
        submission_content="テストSubmission1",
        score=85.0,
        score_details={"overall_score": 85.0, "feedback": "良好"},
        final_submission=True,
    )

    failed1 = FailedTeamInfo(
        team_id="team-002",
        team_name="Failed Team 1",
        error_message="Timeout after 600 seconds",
    )
    failed2 = FailedTeamInfo(
        team_id="team-003",
        team_name="Failed Team 2",
        error_message="Connection error",
    )

    summary = ExecutionSummary(
        execution_id=execution_id,
        user_prompt="テストプロンプト",
        team_results=[result1],
        failed_teams_info=[failed1, failed2],
        best_team_id="team-001",
        best_score=85.0,
        total_execution_time_seconds=45.3,
    )

    # computed_fieldの検証
    assert summary.total_teams == 3  # 成功1 + 失敗2
    assert summary.completed_teams == 1  # 成功1
    assert summary.failed_teams == 2  # 失敗2
    assert summary.partial_teams == 0  # 重複なし


# =============================================================================
# PartialTeamFailureError and partial success computed fields tests
# =============================================================================


def _make_leaderboard_entry(team_id: str = "team-001", team_name: str = "Test Team") -> LeaderBoardEntry:
    """テスト用LeaderBoardEntry生成ヘルパー"""
    return LeaderBoardEntry(
        execution_id="test-exec-id",
        team_id=team_id,
        team_name=team_name,
        round_number=1,
        submission_content="test submission",
        score=75.0,
        score_details={"overall_score": 75.0},
    )


def test_total_teams_deduplicates_with_partial_success() -> None:
    """同一チームが team_results と failed_teams_info の両方に入っても total_teams が重複排除される"""
    summary = ExecutionSummary(
        execution_id="test-exec-id",
        user_prompt="test prompt",
        team_results=[_make_leaderboard_entry("team-1", "Team 1")],
        failed_teams_info=[FailedTeamInfo(team_id="team-1", team_name="Team 1", error_message="round 2 failed")],
        total_execution_time_seconds=1.0,
    )
    assert summary.total_teams == 1  # 重複排除
    assert summary.completed_teams == 1
    assert summary.failed_teams == 1
    assert summary.partial_teams == 1


def test_partial_teams_count_mixed() -> None:
    """部分成功・完全成功・完全失敗が混在する場合の partial_teams"""
    summary = ExecutionSummary(
        execution_id="test-exec-id",
        user_prompt="test prompt",
        team_results=[
            _make_leaderboard_entry("team-a", "Team A"),  # 完全成功
            _make_leaderboard_entry("team-b", "Team B"),  # 部分成功
        ],
        failed_teams_info=[
            FailedTeamInfo(team_id="team-b", team_name="Team B", error_message="round 3 failed"),  # 部分成功
            FailedTeamInfo(team_id="team-c", team_name="Team C", error_message="round 1 failed"),  # 完全失敗
        ],
        total_execution_time_seconds=1.0,
    )
    assert summary.total_teams == 3  # A, B, C
    assert summary.completed_teams == 2  # A, B
    assert summary.failed_teams == 2  # B, C
    assert summary.partial_teams == 1  # B のみ


def test_total_teams_no_overlap() -> None:
    """重複がない場合の従来動作確認"""
    summary = ExecutionSummary(
        execution_id="test-exec-id",
        user_prompt="test prompt",
        team_results=[_make_leaderboard_entry("team-1", "Team 1")],
        failed_teams_info=[FailedTeamInfo(team_id="team-2", team_name="Team 2", error_message="failed")],
        total_execution_time_seconds=1.0,
    )
    assert summary.total_teams == 2
    assert summary.partial_teams == 0


def test_partial_team_failure_exception() -> None:
    """PartialTeamFailureError 例外が正しいプロパティを保持する"""
    entry = _make_leaderboard_entry("team-1", "Team 1")
    original = RuntimeError("round 2 evaluation failed")
    exc = PartialTeamFailureError(entry=entry, original_error=original)

    assert exc.entry is entry
    assert exc.original_error is original
    assert "team-1" in str(exc)
    assert "round 2 evaluation failed" in str(exc)
