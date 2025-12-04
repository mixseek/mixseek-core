"""Tests for execution service."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from mixseek.ui.models.config import OrchestrationOption
from mixseek.ui.models.execution import ExecutionStatus
from mixseek.ui.services.execution_service import run_orchestration


def test_run_orchestration_raises_on_empty_prompt() -> None:
    """空プロンプトでValueErrorを発生させる."""
    option = OrchestrationOption(
        config_file_name="test.toml",
        orchestration_id="test_orch",
        display_label="test.toml - test_orch",
    )

    with pytest.raises(ValueError, match="Task prompt cannot be empty"):
        run_orchestration("", option)

    with pytest.raises(ValueError, match="Task prompt cannot be empty"):
        run_orchestration("   ", option)


def test_run_orchestration_creates_execution(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """実行レコードが作成される."""
    # ワークスペースをモック
    monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    config_file = config_dir / "test.toml"
    config_file.write_text("[orchestrator]\ntimeout_per_team_seconds = 300\n")

    # ExecutionSummaryモックを作成
    mock_summary = MagicMock()
    mock_summary.execution_id = "test-execution-id"
    mock_summary.best_team_id = "team1"
    mock_summary.best_score = 0.95
    mock_summary.failed_teams = 0
    mock_summary.completed_teams = 1

    # Orchestratorをモック
    mock_orchestrator = MagicMock()
    mock_orchestrator.execute = AsyncMock(return_value=mock_summary)

    # load_orchestrator_settingsをモック（FR-011: OrchestratorSettings直接返す）
    mock_settings = MagicMock()
    mock_settings.timeout_per_team_seconds = 300
    mock_settings.workspace_path = tmp_path

    import mixseek.ui.services.execution_service

    monkeypatch.setattr(
        mixseek.ui.services.execution_service, "load_orchestrator_settings", lambda x, workspace=None: mock_settings
    )
    monkeypatch.setattr(mixseek.ui.services.execution_service, "Orchestrator", lambda **kwargs: mock_orchestrator)

    option = OrchestrationOption(
        config_file_name="test.toml",
        orchestration_id="test_orch",
        display_label="test.toml - test_orch",
    )

    execution = run_orchestration("Test task prompt", option)

    assert execution.execution_id == "test-execution-id"
    assert execution.prompt == "Test task prompt"
    assert execution.status == ExecutionStatus.COMPLETED
    assert execution.created_at is not None
    assert execution.best_team_id == "team1"
    assert execution.best_score == 0.95


def test_run_orchestration_returns_completed_status(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """成功時にCOMPLETED状態を返す."""
    # ワークスペースをモック
    monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    config_file = config_dir / "test.toml"
    config_file.write_text("[orchestrator]\ntimeout_per_team_seconds = 300\n")

    # ExecutionSummaryモックを作成
    mock_summary = MagicMock()
    mock_summary.execution_id = "test-execution-id"
    mock_summary.best_team_id = "team1"
    mock_summary.best_score = 0.85
    mock_summary.failed_teams = 0
    mock_summary.completed_teams = 1

    # Orchestratorをモック
    mock_orchestrator = MagicMock()
    mock_orchestrator.execute = AsyncMock(return_value=mock_summary)

    # load_orchestrator_settingsをモック（FR-011: OrchestratorSettings直接返す）
    mock_settings = MagicMock()
    mock_settings.timeout_per_team_seconds = 300
    mock_settings.workspace_path = tmp_path

    import mixseek.ui.services.execution_service

    monkeypatch.setattr(
        mixseek.ui.services.execution_service, "load_orchestrator_settings", lambda x, workspace=None: mock_settings
    )
    monkeypatch.setattr(mixseek.ui.services.execution_service, "Orchestrator", lambda **kwargs: mock_orchestrator)

    option = OrchestrationOption(
        config_file_name="test.toml",
        orchestration_id="test_orch",
        display_label="test.toml - test_orch",
    )

    execution = run_orchestration("Test task", option)

    assert execution.status == ExecutionStatus.COMPLETED
    assert execution.completed_at is not None
    assert execution.result_summary is not None


def test_get_recent_logs_file_not_exists(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """ログファイルが存在しない場合は空リストを返す."""
    monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))

    from mixseek.ui.services.execution_service import get_recent_logs

    result = get_recent_logs()
    assert result == []


def test_get_recent_logs_empty_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """ログファイルが空の場合は空リストを返す."""
    monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    (log_dir / "mixseek.log").write_text("")

    from mixseek.ui.services.execution_service import get_recent_logs

    result = get_recent_logs()
    assert result == []


def test_get_recent_logs_filters_by_level(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """INFOレベル以上のログのみフィルタリング."""
    monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
    log_dir = tmp_path / "logs"
    log_dir.mkdir()

    log_content = """2025-01-01 10:00:00 - mixseek - DEBUG - debug message
2025-01-01 10:00:01 - mixseek - INFO - info message
2025-01-01 10:00:02 - mixseek - WARNING - warning message
2025-01-01 10:00:03 - mixseek - ERROR - error message
"""
    (log_dir / "mixseek.log").write_text(log_content)

    from mixseek.ui.services.execution_service import get_recent_logs

    result = get_recent_logs(level="INFO")
    assert len(result) == 3
    assert "DEBUG" not in " ".join(result)
    assert "INFO" in result[0]
    assert "WARNING" in result[1]
    assert "ERROR" in result[2]


def test_get_recent_logs_limits_lines(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """指定行数より多いログは末尾のみ取得."""
    monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
    log_dir = tmp_path / "logs"
    log_dir.mkdir()

    log_content = """2025-01-01 10:00:01 - mixseek - INFO - line 1
2025-01-01 10:00:02 - mixseek - INFO - line 2
2025-01-01 10:00:03 - mixseek - INFO - line 3
"""
    (log_dir / "mixseek.log").write_text(log_content)

    from mixseek.ui.services.execution_service import get_recent_logs

    result = get_recent_logs(lines=2)
    assert len(result) == 2
    assert "line 2" in result[0]
    assert "line 3" in result[1]


def test_get_failed_teams_from_progress_files(tmp_path: Path) -> None:
    """進捗ファイルから失敗チーム情報を取得."""
    import json

    from mixseek.ui.services.execution_service import _get_failed_teams_from_progress_files

    # logs ディレクトリ作成
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()

    execution_id = "test-execution-123"

    # 成功チームの進捗ファイル
    success_progress = {
        "execution_id": execution_id,
        "team_id": "team-success",
        "team_name": "Success Team",
        "status": "completed",
        "current_round": 3,
        "total_rounds": 3,
        "updated_at": "2025-01-01T10:00:00",
    }
    (logs_dir / f"{execution_id}.team-success.progress.json").write_text(json.dumps(success_progress))

    # 失敗チームの進捗ファイル
    failed_progress = {
        "execution_id": execution_id,
        "team_id": "team-failed",
        "team_name": "Failed Team",
        "status": "failed",
        "error_message": "Model not found: invalid-model",
        "current_round": 1,
        "total_rounds": 3,
        "updated_at": "2025-01-01T10:00:01",
    }
    (logs_dir / f"{execution_id}.team-failed.progress.json").write_text(json.dumps(failed_progress))

    result = _get_failed_teams_from_progress_files(execution_id, tmp_path)

    assert len(result) == 1
    assert result[0].team_id == "team-failed"
    assert result[0].team_name == "Failed Team"
    assert "Model not found" in result[0].error_message


def test_get_failed_teams_from_progress_files_empty_when_no_failures(tmp_path: Path) -> None:
    """失敗チームがない場合は空リストを返す."""
    import json

    from mixseek.ui.services.execution_service import _get_failed_teams_from_progress_files

    # logs ディレクトリ作成
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()

    execution_id = "test-execution-456"

    # 成功チームのみ
    success_progress = {
        "execution_id": execution_id,
        "team_id": "team-success",
        "team_name": "Success Team",
        "status": "completed",
        "current_round": 3,
        "total_rounds": 3,
        "updated_at": "2025-01-01T10:00:00",
    }
    (logs_dir / f"{execution_id}.team-success.progress.json").write_text(json.dumps(success_progress))

    result = _get_failed_teams_from_progress_files(execution_id, tmp_path)

    assert result == []


def test_get_failed_teams_from_progress_files_no_logs_dir(tmp_path: Path) -> None:
    """logsディレクトリがない場合は空リストを返す."""
    from mixseek.ui.services.execution_service import _get_failed_teams_from_progress_files

    result = _get_failed_teams_from_progress_files("test-execution", tmp_path)

    assert result == []
