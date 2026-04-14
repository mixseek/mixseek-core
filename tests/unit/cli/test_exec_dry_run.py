"""mixseek exec --dry-run CLI統合テスト

TDD: Red-Green-Refactor サイクルの Red フェーズ。
CLIフラグ、出力フォーマット、プリフライト統合をテストする。
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from mixseek.cli.main import app
from mixseek.config.preflight import (
    CategoryResult,
    CheckResult,
    CheckStatus,
    PreflightResult,
)

_EXEC_MODULE = "mixseek.cli.commands.exec"


@pytest.fixture
def runner() -> CliRunner:
    """CLIテストランナー"""
    return CliRunner()


@pytest.fixture
def orchestrator_toml(tmp_path: Path) -> Path:
    """最小限のオーケストレータ設定TOML"""
    team_toml = tmp_path / "team.toml"
    team_toml.write_text(
        '[team]\nteam_id = "test-team"\nteam_name = "Test Team"\n'
        "[[team.members]]\n"
        'agent_name = "dummy"\nagent_type = "plain"\n'
        'tool_description = "dummy agent"\n'
        'model = "google-gla:gemini-2.5-flash-lite"\n'
        'system_instruction = "dummy"\ntemperature = 0.7\nmax_tokens = 2048\n'
    )
    config = tmp_path / "orchestrator.toml"
    config.write_text(f'[orchestrator]\n[[orchestrator.teams]]\nconfig = "{team_toml}"\n')
    return config


def _make_valid_preflight() -> PreflightResult:
    """正常なプリフライト結果を生成"""
    return PreflightResult(
        categories=[
            CategoryResult(
                category="オーケストレータ",
                checks=[CheckResult(name="orchestrator_config", status=CheckStatus.OK)],
            ),
        ]
    )


def _make_invalid_preflight() -> PreflightResult:
    """エラーを含むプリフライト結果を生成"""
    return PreflightResult(
        categories=[
            CategoryResult(
                category="オーケストレータ",
                checks=[
                    CheckResult(
                        name="orchestrator_config",
                        status=CheckStatus.ERROR,
                        message="設定エラー",
                    )
                ],
            ),
        ]
    )


# ---------------------------------------------------------------------------
# TestExecDryRunFlag
# ---------------------------------------------------------------------------


class TestExecDryRunFlag:
    """--dry-run フラグの CLI テスト"""

    def test_help_shows_dry_run(self, runner: CliRunner) -> None:
        """--helpに--dry-runが表示される"""
        result = runner.invoke(app, ["exec", "--help"])
        # Rich/typerの出力幅によってテキストが折り返される場合があるため、
        # 空白やハイフンの前後を正規化して検証する
        normalized = result.output.replace("\n", " ").replace("  ", " ")
        assert "dry-run" in normalized or "dry_run" in normalized

    @patch(f"{_EXEC_MODULE}._execute_orchestration")
    @patch(f"{_EXEC_MODULE}.run_preflight_check")
    @patch(f"{_EXEC_MODULE}.initialize_observability")
    @patch(f"{_EXEC_MODULE}.ConfigurationManager")
    def test_dry_run_valid_config_exit_0(
        self,
        mock_config_mgr: MagicMock,
        mock_init_obs: MagicMock,
        mock_preflight: MagicMock,
        mock_execute_orch: MagicMock,
        runner: CliRunner,
        orchestrator_toml: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """--dry-run 正常設定 → exit code 0、実行系に進まない"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(orchestrator_toml.parent))
        mock_preflight.return_value = _make_valid_preflight()

        result = runner.invoke(
            app,
            ["exec", "test prompt", "--config", str(orchestrator_toml), "--dry-run"],
        )
        assert result.exit_code == 0
        mock_preflight.assert_called_once()
        # dry-runでは実行系に進まないことを保証
        mock_execute_orch.assert_not_called()

    @patch(f"{_EXEC_MODULE}.run_preflight_check")
    @patch(f"{_EXEC_MODULE}.initialize_observability")
    @patch(f"{_EXEC_MODULE}.ConfigurationManager")
    def test_dry_run_valid_config_json_output(
        self,
        mock_config_mgr: MagicMock,
        mock_init_obs: MagicMock,
        mock_preflight: MagicMock,
        runner: CliRunner,
        orchestrator_toml: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """--dry-run 正常設定 --output-format json → exit code 0、JSON出力"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(orchestrator_toml.parent))
        mock_preflight.return_value = _make_valid_preflight()

        result = runner.invoke(
            app,
            [
                "exec",
                "test prompt",
                "--config",
                str(orchestrator_toml),
                "--dry-run",
                "--output-format",
                "json",
            ],
        )
        assert result.exit_code == 0
        # JSON出力を含む
        assert '"categories"' in result.output

    @patch(f"{_EXEC_MODULE}.run_preflight_check")
    @patch(f"{_EXEC_MODULE}.initialize_observability")
    @patch(f"{_EXEC_MODULE}.ConfigurationManager")
    def test_dry_run_invalid_config_exit_2(
        self,
        mock_config_mgr: MagicMock,
        mock_init_obs: MagicMock,
        mock_preflight: MagicMock,
        runner: CliRunner,
        orchestrator_toml: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """--dry-run 不正設定 → exit code 2"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(orchestrator_toml.parent))
        mock_preflight.return_value = _make_invalid_preflight()

        result = runner.invoke(
            app,
            ["exec", "test prompt", "--config", str(orchestrator_toml), "--dry-run"],
        )
        assert result.exit_code == 2

    def test_dry_run_no_config_exit_2(
        self,
        runner: CliRunner,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """--dry-run --config未指定 → exit code 2"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))

        result = runner.invoke(
            app,
            ["exec", "test prompt", "--dry-run"],
        )
        assert result.exit_code == 2


# ---------------------------------------------------------------------------
# TestExecPreflightIntegration
# ---------------------------------------------------------------------------


class TestExecPreflightIntegration:
    """通常exec実行時のプリフライト統合テスト"""

    @patch(f"{_EXEC_MODULE}.close_all_auth_clients", new_callable=AsyncMock)
    @patch(f"{_EXEC_MODULE}._execute_orchestration")
    @patch(f"{_EXEC_MODULE}.run_preflight_check")
    @patch(f"{_EXEC_MODULE}.initialize_observability")
    @patch(f"{_EXEC_MODULE}.ConfigurationManager")
    def test_normal_exec_preflight_fail_stops(
        self,
        mock_config_mgr: MagicMock,
        mock_init_obs: MagicMock,
        mock_preflight: MagicMock,
        mock_execute_orch: MagicMock,
        mock_close_auth: AsyncMock,
        runner: CliRunner,
        orchestrator_toml: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """通常exec: プリフライト失敗 → 実行せずexit"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(orchestrator_toml.parent))
        mock_preflight.return_value = _make_invalid_preflight()

        result = runner.invoke(
            app,
            ["exec", "test prompt", "--config", str(orchestrator_toml)],
        )
        # プリフライト失敗で exit code 2
        assert result.exit_code == 2
        # 実行系に進まないことを保証
        mock_execute_orch.assert_not_called()

    @patch(f"{_EXEC_MODULE}.close_all_auth_clients", new_callable=AsyncMock)
    @patch(f"{_EXEC_MODULE}._execute_orchestration")
    @patch(f"{_EXEC_MODULE}.Orchestrator")
    @patch(f"{_EXEC_MODULE}.run_preflight_check")
    @patch(f"{_EXEC_MODULE}.initialize_observability")
    @patch(f"{_EXEC_MODULE}.ConfigurationManager")
    def test_normal_exec_preflight_pass_continues(
        self,
        mock_config_mgr: MagicMock,
        mock_init_obs: MagicMock,
        mock_preflight: MagicMock,
        mock_orchestrator_cls: MagicMock,
        mock_execute_orch: MagicMock,
        mock_close_auth: AsyncMock,
        runner: CliRunner,
        orchestrator_toml: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """通常exec: プリフライト成功 → orchestrator.execute()が呼ばれる"""
        from mixseek.models.leaderboard import LeaderBoardEntry
        from mixseek.orchestrator.models import ExecutionSummary

        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(orchestrator_toml.parent))
        mock_settings = MagicMock()
        mock_settings.teams = [MagicMock()]
        preflight_result = _make_valid_preflight()
        preflight_result.orchestrator_settings = mock_settings
        mock_preflight.return_value = preflight_result
        mock_execute_orch.return_value = ExecutionSummary(
            execution_id="test",
            user_prompt="test",
            team_results=[
                LeaderBoardEntry(
                    execution_id="test",
                    team_id="t1",
                    team_name="T1",
                    round_number=1,
                    submission_content="ok",
                    score=90.0,
                    score_details={},
                ),
            ],
            failed_teams_info=[],
            total_execution_time_seconds=1.0,
        )

        result = runner.invoke(
            app,
            ["exec", "test prompt", "--config", str(orchestrator_toml)],
        )
        assert result.exit_code == 0
        # orchestrator.execute が呼ばれた
        mock_execute_orch.assert_called_once()
