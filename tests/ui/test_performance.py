"""Performance tests for UI components (SC-004, SC-005, SC-007)."""

import time
from pathlib import Path

import duckdb
import pytest

from mixseek.ui.models.execution import ExecutionStatus
from mixseek.ui.services.config_service import get_all_orchestration_options
from mixseek.ui.services.history_service import fetch_history
from mixseek.ui.services.leaderboard_service import fetch_leaderboard, fetch_top_submission


@pytest.mark.performance
def test_sc_007_config_loading_under_1_second(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """SC-007: Config loading completes within 1 second with 10 TOML files."""
    # Setup workspace with 10 TOML files
    monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()

    # Create 10 valid TOML files with orchestrations
    for i in range(10):
        toml_content = f"""
[orchestrator]
timeout_per_team_seconds = 600

[[orchestrator.teams]]
config = "configs/agents/team-{i}.toml"
"""
        (configs_dir / f"config_{i:02d}.toml").write_text(toml_content)

    # Measure loading time
    start = time.perf_counter()
    options = get_all_orchestration_options()
    elapsed = time.perf_counter() - start

    assert len(options) == 10
    assert elapsed < 1.0, f"Config loading took {elapsed:.3f}s, expected < 1.0s"


@pytest.mark.performance
def test_sc_004_leaderboard_display_under_2_seconds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """SC-004: Leaderboard displays within 2 seconds with 100 teams."""
    # Setup workspace and database
    monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
    (tmp_path / "configs").mkdir()
    db_path = tmp_path / "mixseek.db"  # Match get_db_path() expected location

    # Create database with 100 teams (new schema)
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

    execution_id = "perf-test-exec-001"
    teams_data = [
        (
            f"team-{i:03d}",
            f"Team {i}",
            100.0 - i * 0.5,  # 0-100 scale
            1,
            f"Submission content for team {i}",
            f'{{"overall_score": {100.0 - i * 0.5}, "metrics": []}}',
            "2024-01-01 12:00:00",
            execution_id,
        )
        for i in range(100)
    ]
    conn.executemany("INSERT INTO leader_board VALUES (?, ?, ?, ?, ?, ?, ?, ?)", teams_data)
    conn.close()

    # Measure leaderboard loading time (after DB is closed for write, can open for read)
    start = time.perf_counter()
    leaderboard = fetch_leaderboard(execution_id)
    top_submission = fetch_top_submission(execution_id)
    elapsed = time.perf_counter() - start

    assert len(leaderboard) == 100
    assert top_submission is not None
    assert elapsed < 2.0, f"Leaderboard display took {elapsed:.3f}s, expected < 2.0s"


@pytest.mark.performance
def test_sc_005_history_display_under_2_seconds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """SC-005: History page displays within 2 seconds with 500 records."""
    # Setup workspace and database
    monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
    (tmp_path / "configs").mkdir()
    db_path = tmp_path / "mixseek.db"  # Match get_db_path() expected location

    # Create database with 500 execution records
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

    executions_data = [
        (
            f"exec-{i:04d}",
            f"Test prompt {i}",
            ExecutionStatus.COMPLETED.value,
            f"team-{i % 10}",
            0.85 + (i % 15) * 0.01,
            300.0 + i,
            f"2024-01-{(i % 28) + 1:02d} 12:00:00",
            f"2024-01-{(i % 28) + 1:02d} 12:05:00",
        )
        for i in range(500)
    ]
    conn.executemany("INSERT INTO execution_summary VALUES (?, ?, ?, ?, ?, ?, ?, ?)", executions_data)
    conn.close()

    # Measure initial page load (50 items) after DB is closed
    start = time.perf_counter()
    entries, total_count = fetch_history(page_number=1, page_size=50)
    elapsed = time.perf_counter() - start

    assert total_count == 500
    assert len(entries) == 50
    assert elapsed < 2.0, f"History initial load took {elapsed:.3f}s, expected < 2.0s"

    # Measure page navigation (SC-005: < 1 second)
    start = time.perf_counter()
    entries_page2, _ = fetch_history(page_number=2, page_size=50)
    elapsed_navigation = time.perf_counter() - start

    assert len(entries_page2) == 50
    assert elapsed_navigation < 1.0, f"History page navigation took {elapsed_navigation:.3f}s, expected < 1.0s"
