"""Tests for history service."""

from pathlib import Path

import duckdb
import pytest

from mixseek.ui.models.execution import ExecutionStatus
from mixseek.ui.services.history_service import fetch_execution_detail, fetch_history


def test_fetch_history_returns_empty_when_db_not_found(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """DBファイル不在時は空リストを返す."""
    monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
    entries, total_count = fetch_history()
    assert entries == []
    assert total_count == 0


def test_fetch_history_paginates_correctly(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """ページネーションが正しく動作."""
    monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
    db_path = tmp_path / "mixseek.db"

    # Create test database with execution_summary
    conn = duckdb.connect(str(db_path))
    conn.execute("""
        CREATE TABLE execution_summary (
            execution_id VARCHAR PRIMARY KEY,
            user_prompt VARCHAR NOT NULL,
            status VARCHAR NOT NULL,
            best_team_id VARCHAR,
            best_score DOUBLE,
            total_execution_time_seconds DOUBLE,
            created_at TIMESTAMP NOT NULL,
            completed_at TIMESTAMP
        )
    """)

    # Insert 100 test records
    for i in range(100):
        conn.execute(
            """
            INSERT INTO execution_summary VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            [
                f"exec{i}",
                f"Test prompt {i}",
                "completed",
                f"team{i % 5}",
                0.85 + (i % 15) * 0.01,
                300.0 + i,
                f"2025-01-01 {i % 24:02d}:00:00",
                f"2025-01-01 {i % 24:02d}:05:00",
            ],
        )
    conn.close()

    # Test first page
    entries, total_count = fetch_history(page_number=1, page_size=50)
    assert len(entries) == 50
    assert total_count == 100

    # Test second page
    entries, total_count = fetch_history(page_number=2, page_size=50)
    assert len(entries) == 50
    assert total_count == 100


def test_fetch_history_filters_by_status(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """ステータスフィルタが動作."""
    monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
    db_path = tmp_path / "mixseek.db"

    # Create test database
    conn = duckdb.connect(str(db_path))
    conn.execute("""
        CREATE TABLE execution_summary (
            execution_id VARCHAR PRIMARY KEY,
            user_prompt VARCHAR NOT NULL,
            status VARCHAR NOT NULL,
            best_team_id VARCHAR,
            best_score DOUBLE,
            total_execution_time_seconds DOUBLE,
            created_at TIMESTAMP NOT NULL,
            completed_at TIMESTAMP
        )
    """)
    conn.execute("""
        INSERT INTO execution_summary VALUES
        ('exec1', 'Prompt 1', 'completed', 'team1', 0.95, 300.0,
         '2025-01-01 10:00:00', '2025-01-01 10:05:00'),
        ('exec2', 'Prompt 2', 'failed', NULL, NULL, 150.0,
         '2025-01-01 11:00:00', '2025-01-01 11:05:00'),
        ('exec3', 'Prompt 3', 'completed', 'team3', 0.88, 320.0,
         '2025-01-01 12:00:00', '2025-01-01 12:05:00')
    """)
    conn.close()

    # Filter by COMPLETED
    entries, total_count = fetch_history(status_filter=ExecutionStatus.COMPLETED)
    assert len(entries) == 2
    assert total_count == 2

    # Filter by FAILED
    entries, total_count = fetch_history(status_filter=ExecutionStatus.FAILED)
    assert len(entries) == 1
    assert total_count == 1
    assert entries[0].status == ExecutionStatus.FAILED


def test_fetch_execution_detail_returns_execution(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """実行詳細取得が成功."""
    monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
    db_path = tmp_path / "mixseek.db"

    # Create test database
    conn = duckdb.connect(str(db_path))
    conn.execute("""
        CREATE TABLE execution_summary (
            execution_id VARCHAR PRIMARY KEY,
            user_prompt VARCHAR NOT NULL,
            status VARCHAR NOT NULL,
            best_team_id VARCHAR,
            best_score DOUBLE,
            total_execution_time_seconds DOUBLE,
            created_at TIMESTAMP NOT NULL,
            completed_at TIMESTAMP
        )
    """)
    conn.execute("""
        INSERT INTO execution_summary VALUES
        ('exec123', 'Test prompt', 'completed', 'team1', 0.92, 280.0,
         '2025-01-01 10:00:00', '2025-01-01 10:05:00')
    """)
    conn.close()

    execution = fetch_execution_detail("exec123")
    assert execution is not None
    assert execution.execution_id == "exec123"
    assert execution.prompt == "Test prompt"
    assert execution.status == ExecutionStatus.COMPLETED


def test_fetch_execution_detail_returns_none_when_not_found(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """実行が見つからない場合はNoneを返す."""
    monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
    execution = fetch_execution_detail("nonexistent")
    assert execution is None
