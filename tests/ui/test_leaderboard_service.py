"""Tests for leaderboard service."""

from pathlib import Path

import duckdb
import pytest

from mixseek.ui.services.leaderboard_service import (
    fetch_leaderboard,
    fetch_team_submission,
    fetch_top_submission,
)


def test_fetch_leaderboard_returns_empty_when_db_not_found(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """DBファイル不在時は空リストを返す."""
    monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
    leaderboard = fetch_leaderboard("test-execution-id")
    assert leaderboard == []


def test_fetch_leaderboard_returns_sorted_entries(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """エントリがrank昇順でソートされる."""
    monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
    db_path = tmp_path / "mixseek.db"

    # Create test database with leader_board (new schema)
    conn = duckdb.connect(str(db_path))
    conn.execute("""
        CREATE TABLE leader_board (
            team_id VARCHAR NOT NULL,
            team_name VARCHAR NOT NULL,
            score FLOAT NOT NULL,
            round_number INTEGER NOT NULL,
            submission_content VARCHAR NOT NULL,
            score_details JSON NOT NULL,
            created_at TIMESTAMP NOT NULL,
            execution_id VARCHAR NOT NULL
        )
    """)
    conn.execute("""
        INSERT INTO leader_board VALUES
        ('team1', 'Team Alpha', 95.5, 1, 'Content 1',
         '{"overall_score": 95.5, "metrics": []}', '2025-01-01 10:00:00', 'exec1'),
        ('team2', 'Team Beta', 98.0, 1, 'Content 2',
         '{"overall_score": 98.0, "metrics": []}', '2025-01-01 10:05:00', 'exec1'),
        ('team3', 'Team Gamma', 90.0, 1, 'Content 3',
         '{"overall_score": 90.0, "metrics": []}', '2025-01-01 10:10:00', 'exec1')
    """)
    conn.close()

    leaderboard = fetch_leaderboard("exec1")
    assert len(leaderboard) == 3
    assert leaderboard[0].rank == 1
    assert leaderboard[0].team_name == "Team Beta"
    assert leaderboard[1].rank == 2
    assert leaderboard[2].rank == 3


def test_fetch_top_submission_returns_highest_score(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """最高スコアのサブミッションを返す."""
    monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
    db_path = tmp_path / "mixseek.db"

    # Create test database with leader_board (new schema)
    conn = duckdb.connect(str(db_path))
    conn.execute("""
        CREATE TABLE leader_board (
            team_id VARCHAR NOT NULL,
            team_name VARCHAR NOT NULL,
            execution_id VARCHAR NOT NULL,
            score FLOAT NOT NULL,
            submission_content VARCHAR NOT NULL,
            score_details JSON NOT NULL,
            round_number INTEGER NOT NULL,
            created_at TIMESTAMP NOT NULL
        )
    """)
    # Long JSON strings for score_details (noqa to suppress line length warnings)
    details_1 = '{"overall_score": 85.0, "metrics": [{"metric_name": "Test", "score": 85.0, "evaluator_comment": "Feedback 1"}]}'  # noqa: E501
    details_2 = '{"overall_score": 95.0, "metrics": [{"metric_name": "Test", "score": 95.0, "evaluator_comment": "Feedback 2"}]}'  # noqa: E501
    details_3 = '{"overall_score": 90.0, "metrics": [{"metric_name": "Test", "score": 90.0, "evaluator_comment": "Feedback 3"}]}'  # noqa: E501
    conn.execute(f"""
        INSERT INTO leader_board VALUES
        ('team1', 'Team 1', 'exec1', 85.0, 'Content 1', '{details_1}', 1, '2025-01-01 10:00:00'),
        ('team2', 'Team 2', 'exec1', 95.0, 'Content 2', '{details_2}', 1, '2025-01-01 10:05:00'),
        ('team3', 'Team 3', 'exec1', 90.0, 'Content 3', '{details_3}', 1, '2025-01-01 10:10:00')
    """)
    conn.close()

    top_submission = fetch_top_submission("exec1")
    assert top_submission is not None
    assert top_submission.score == 95.0
    assert top_submission.team_id == "team2"
    assert top_submission.submission_content == "Content 2"


def test_fetch_top_submission_returns_none_when_no_data(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """データがない場合はNoneを返す."""
    monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
    top_submission = fetch_top_submission("nonexistent-exec-id")
    assert top_submission is None


def test_fetch_team_submission_returns_team_data(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """指定チームのサブミッションを返す."""
    monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
    db_path = tmp_path / "mixseek.db"

    # Create test database with leader_board (new schema)
    conn = duckdb.connect(str(db_path))
    conn.execute("""
        CREATE TABLE leader_board (
            team_id VARCHAR NOT NULL,
            team_name VARCHAR NOT NULL,
            execution_id VARCHAR NOT NULL,
            score FLOAT NOT NULL,
            submission_content VARCHAR NOT NULL,
            score_details JSON NOT NULL,
            round_number INTEGER NOT NULL,
            created_at TIMESTAMP NOT NULL
        )
    """)
    # Long JSON strings for score_details (noqa to suppress line length warnings)
    details_1 = '{"overall_score": 85.0, "metrics": [{"metric_name": "Test", "score": 85.0, "evaluator_comment": "Feedback 1"}]}'  # noqa: E501
    details_2 = '{"overall_score": 95.0, "metrics": [{"metric_name": "Test", "score": 95.0, "evaluator_comment": "Feedback 2"}]}'  # noqa: E501
    conn.execute(f"""
        INSERT INTO leader_board VALUES
        ('team1', 'Team Alpha', 'exec1', 85.0, 'Content 1', '{details_1}', 1, '2025-01-01 10:00:00'),
        ('team2', 'Team Beta', 'exec1', 95.0, 'Content 2', '{details_2}', 1, '2025-01-01 10:05:00')
    """)
    conn.close()

    submission = fetch_team_submission("exec1", "team1", 1)
    assert submission is not None
    assert submission.team_id == "team1"
    assert submission.team_name == "Team Alpha"
    assert submission.score == 85.0
    assert submission.submission_content == "Content 1"


def test_fetch_team_submission_returns_none_when_not_found(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """チームが見つからない場合はNoneを返す."""
    monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
    submission = fetch_team_submission("nonexistent-exec-id", "nonexistent-team", 1)
    assert submission is None
