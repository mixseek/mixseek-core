"""mixseek exec コマンド終了コードテスト

Article 3: Test-First Imperative準拠

終了コード仕様:
    - 0: 全チーム成功（failed_teams_info が空）
    - 1: 部分成功（team_results が非空 かつ failed_teams_info が非空）
    - 2: 全チーム失敗（team_results が空）/ 未処理例外
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from mixseek.cli.main import app
from mixseek.models.leaderboard import LeaderBoardEntry
from mixseek.orchestrator.models import ExecutionSummary, FailedTeamInfo


@pytest.fixture
def runner() -> CliRunner:
    """CLIテストランナー"""
    return CliRunner()


@pytest.fixture
def orchestrator_toml(tmp_path: Path) -> Path:
    """最小限のオーケストレータ設定TOML"""
    team_toml = tmp_path / "team.toml"
    team_toml.write_text("""
[team]
team_id = "test-team"
team_name = "Test Team"

[[team.members]]
agent_name = "dummy"
agent_type = "plain"
tool_description = "dummy agent"
model = "google-gla:gemini-2.5-flash-lite"
system_instruction = "dummy"
temperature = 0.7
max_tokens = 2048
""")

    config = tmp_path / "orchestrator.toml"
    config.write_text(f"""
[orchestrator]

[[orchestrator.teams]]
config = "{team_toml}"
""")
    return config


def _make_entry(team_id: str = "team-1", team_name: str = "Team 1") -> LeaderBoardEntry:
    """テスト用LeaderBoardEntry生成"""
    return LeaderBoardEntry(
        execution_id="test-exec-id",
        team_id=team_id,
        team_name=team_name,
        round_number=1,
        submission_content="test submission",
        score=85.0,
        score_details={"comment": "good"},
    )


def _make_failed(team_id: str = "team-2", team_name: str = "Team 2") -> FailedTeamInfo:
    """テスト用FailedTeamInfo生成"""
    return FailedTeamInfo(
        team_id=team_id,
        team_name=team_name,
        error_message="execution failed",
    )


def _make_summary(
    team_results: list[LeaderBoardEntry] | None = None,
    failed_teams_info: list[FailedTeamInfo] | None = None,
) -> ExecutionSummary:
    """テスト用ExecutionSummary生成"""
    return ExecutionSummary(
        execution_id="test-exec-id",
        user_prompt="test prompt",
        team_results=team_results or [],
        failed_teams_info=failed_teams_info or [],
        total_execution_time_seconds=1.0,
    )


# モック対象パス
_EXEC_MODULE = "mixseek.cli.commands.exec"


class TestExecExitCode:
    """exec コマンド終了コードテスト"""

    @patch(f"{_EXEC_MODULE}.close_all_auth_clients", new_callable=AsyncMock)
    @patch(f"{_EXEC_MODULE}.setup_logfire_from_cli")
    @patch(f"{_EXEC_MODULE}.setup_logging_from_cli")
    @patch(f"{_EXEC_MODULE}.ConfigurationManager")
    @patch(f"{_EXEC_MODULE}.Orchestrator")
    @patch(f"{_EXEC_MODULE}._load_and_validate_config")
    @patch(f"{_EXEC_MODULE}._execute_orchestration")
    def test_all_teams_success_exit_code_0(
        self,
        mock_execute_orch: MagicMock,
        mock_load_config: MagicMock,
        mock_orchestrator_cls: MagicMock,
        mock_config_mgr: MagicMock,
        mock_setup_logging: MagicMock,
        mock_setup_logfire: MagicMock,
        mock_close_auth: AsyncMock,
        runner: CliRunner,
        orchestrator_toml: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """全チーム成功 → exit code 0"""
        # Given
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(orchestrator_toml.parent))
        summary = _make_summary(team_results=[_make_entry()])
        mock_execute_orch.return_value = summary
        mock_settings = MagicMock()
        mock_settings.teams = [MagicMock()]
        mock_load_config.return_value = mock_settings

        # When
        result = runner.invoke(app, ["exec", "test prompt", "--config", str(orchestrator_toml)])

        # Then
        assert result.exit_code == 0

    @patch(f"{_EXEC_MODULE}.close_all_auth_clients", new_callable=AsyncMock)
    @patch(f"{_EXEC_MODULE}.setup_logfire_from_cli")
    @patch(f"{_EXEC_MODULE}.setup_logging_from_cli")
    @patch(f"{_EXEC_MODULE}.ConfigurationManager")
    @patch(f"{_EXEC_MODULE}.Orchestrator")
    @patch(f"{_EXEC_MODULE}._load_and_validate_config")
    @patch(f"{_EXEC_MODULE}._execute_orchestration")
    def test_partial_success_exit_code_1(
        self,
        mock_execute_orch: MagicMock,
        mock_load_config: MagicMock,
        mock_orchestrator_cls: MagicMock,
        mock_config_mgr: MagicMock,
        mock_setup_logging: MagicMock,
        mock_setup_logfire: MagicMock,
        mock_close_auth: AsyncMock,
        runner: CliRunner,
        orchestrator_toml: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """部分成功（成功+失敗チームあり）→ exit code 1"""
        # Given
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(orchestrator_toml.parent))
        summary = _make_summary(
            team_results=[_make_entry()],
            failed_teams_info=[_make_failed()],
        )
        mock_execute_orch.return_value = summary
        mock_settings = MagicMock()
        mock_settings.teams = [MagicMock(), MagicMock()]
        mock_load_config.return_value = mock_settings

        # When
        result = runner.invoke(app, ["exec", "test prompt", "--config", str(orchestrator_toml)])

        # Then
        assert result.exit_code == 1

    @patch(f"{_EXEC_MODULE}.close_all_auth_clients", new_callable=AsyncMock)
    @patch(f"{_EXEC_MODULE}.setup_logfire_from_cli")
    @patch(f"{_EXEC_MODULE}.setup_logging_from_cli")
    @patch(f"{_EXEC_MODULE}.ConfigurationManager")
    @patch(f"{_EXEC_MODULE}.Orchestrator")
    @patch(f"{_EXEC_MODULE}._load_and_validate_config")
    @patch(f"{_EXEC_MODULE}._execute_orchestration")
    def test_all_teams_failed_exit_code_2(
        self,
        mock_execute_orch: MagicMock,
        mock_load_config: MagicMock,
        mock_orchestrator_cls: MagicMock,
        mock_config_mgr: MagicMock,
        mock_setup_logging: MagicMock,
        mock_setup_logfire: MagicMock,
        mock_close_auth: AsyncMock,
        runner: CliRunner,
        orchestrator_toml: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """全チーム失敗 → exit code 2"""
        # Given
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(orchestrator_toml.parent))
        summary = _make_summary(
            team_results=[],
            failed_teams_info=[_make_failed("team-1", "Team 1"), _make_failed("team-2", "Team 2")],
        )
        mock_execute_orch.return_value = summary
        mock_settings = MagicMock()
        mock_settings.teams = [MagicMock(), MagicMock()]
        mock_load_config.return_value = mock_settings

        # When
        result = runner.invoke(app, ["exec", "test prompt", "--config", str(orchestrator_toml)])

        # Then
        assert result.exit_code == 2

    @patch(f"{_EXEC_MODULE}.close_all_auth_clients", new_callable=AsyncMock)
    @patch(f"{_EXEC_MODULE}.setup_logfire_from_cli")
    @patch(f"{_EXEC_MODULE}.setup_logging_from_cli")
    @patch(f"{_EXEC_MODULE}.ConfigurationManager")
    @patch(f"{_EXEC_MODULE}.Orchestrator")
    @patch(f"{_EXEC_MODULE}._load_and_validate_config")
    @patch(f"{_EXEC_MODULE}._execute_orchestration")
    def test_unhandled_exception_exit_code_2(
        self,
        mock_execute_orch: MagicMock,
        mock_load_config: MagicMock,
        mock_orchestrator_cls: MagicMock,
        mock_config_mgr: MagicMock,
        mock_setup_logging: MagicMock,
        mock_setup_logfire: MagicMock,
        mock_close_auth: AsyncMock,
        runner: CliRunner,
        orchestrator_toml: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """未処理例外 → exit code 2"""
        # Given
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(orchestrator_toml.parent))
        mock_execute_orch.side_effect = RuntimeError("unexpected error")
        mock_settings = MagicMock()
        mock_settings.teams = [MagicMock()]
        mock_load_config.return_value = mock_settings

        # When
        result = runner.invoke(app, ["exec", "test prompt", "--config", str(orchestrator_toml)])

        # Then
        assert result.exit_code == 2

    @patch(f"{_EXEC_MODULE}.close_all_auth_clients", new_callable=AsyncMock)
    @patch(f"{_EXEC_MODULE}.setup_logfire_from_cli")
    @patch(f"{_EXEC_MODULE}.setup_logging_from_cli")
    @patch(f"{_EXEC_MODULE}.ConfigurationManager")
    @patch(f"{_EXEC_MODULE}.Orchestrator")
    @patch(f"{_EXEC_MODULE}._load_and_validate_config")
    @patch(f"{_EXEC_MODULE}._execute_orchestration")
    def test_single_team_partial_success_exit_code_1(
        self,
        mock_execute_orch: MagicMock,
        mock_load_config: MagicMock,
        mock_orchestrator_cls: MagicMock,
        mock_config_mgr: MagicMock,
        mock_setup_logging: MagicMock,
        mock_setup_logfire: MagicMock,
        mock_close_auth: AsyncMock,
        runner: CliRunner,
        orchestrator_toml: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """単一チーム部分成功（R1成功, R2失敗）→ exit code 1"""
        # Given: 同一チームが team_results と failed_teams_info の両方に存在
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(orchestrator_toml.parent))
        summary = _make_summary(
            team_results=[_make_entry("team-1", "Team 1")],
            failed_teams_info=[_make_failed("team-1", "Team 1")],
        )
        mock_execute_orch.return_value = summary
        mock_settings = MagicMock()
        mock_settings.teams = [MagicMock()]
        mock_load_config.return_value = mock_settings

        # When
        result = runner.invoke(app, ["exec", "test prompt", "--config", str(orchestrator_toml)])

        # Then
        assert result.exit_code == 1

    @patch(f"{_EXEC_MODULE}.close_all_auth_clients", new_callable=AsyncMock)
    @patch(f"{_EXEC_MODULE}.setup_logfire_from_cli")
    @patch(f"{_EXEC_MODULE}.setup_logging_from_cli")
    @patch(f"{_EXEC_MODULE}.ConfigurationManager")
    @patch(f"{_EXEC_MODULE}.Orchestrator")
    @patch(f"{_EXEC_MODULE}._load_and_validate_config")
    @patch(f"{_EXEC_MODULE}._execute_orchestration")
    def test_mixed_full_partial_failure_exit_code_1(
        self,
        mock_execute_orch: MagicMock,
        mock_load_config: MagicMock,
        mock_orchestrator_cls: MagicMock,
        mock_config_mgr: MagicMock,
        mock_setup_logging: MagicMock,
        mock_setup_logfire: MagicMock,
        mock_close_auth: AsyncMock,
        runner: CliRunner,
        orchestrator_toml: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Team A全成功 + Team B部分失敗 + Team C完全失敗 → exit code 1"""
        # Given
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(orchestrator_toml.parent))
        summary = _make_summary(
            team_results=[
                _make_entry("team-a", "Team A"),
                _make_entry("team-b", "Team B"),
            ],
            failed_teams_info=[
                _make_failed("team-b", "Team B"),
                _make_failed("team-c", "Team C"),
            ],
        )
        mock_execute_orch.return_value = summary
        mock_settings = MagicMock()
        mock_settings.teams = [MagicMock(), MagicMock(), MagicMock()]
        mock_load_config.return_value = mock_settings

        # When
        result = runner.invoke(app, ["exec", "test prompt", "--config", str(orchestrator_toml)])

        # Then
        assert result.exit_code == 1
