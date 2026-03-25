"""Unit tests for Orchestrator"""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mixseek.agents.leader.models import MemberSubmission
from mixseek.config.schema import OrchestratorSettings
from mixseek.models.leaderboard import LeaderBoardEntry
from mixseek.orchestrator import Orchestrator
from mixseek.orchestrator.models import PartialTeamFailureError
from mixseek.round_controller import RoundState


@pytest.fixture
def orchestrator_settings(tmp_path: Path) -> OrchestratorSettings:
    """テスト用OrchestratorSettings（FR-011）"""
    return OrchestratorSettings(
        workspace_path=tmp_path,
        timeout_per_team_seconds=600,
        teams=[
            {"config": "tests/fixtures/team1.toml"},
        ],
    )


def test_orchestrator_initialization(orchestrator_settings: OrchestratorSettings) -> None:
    """Orchestrator初期化テスト（FR-011: OrchestratorSettings直接受け取り）"""
    orchestrator = Orchestrator(settings=orchestrator_settings)
    assert orchestrator.settings == orchestrator_settings
    assert orchestrator.workspace == orchestrator_settings.workspace_path


@pytest.mark.asyncio
async def test_orchestrator_get_team_status_not_found(orchestrator_settings: OrchestratorSettings) -> None:
    """Orchestrator チームステータス取得テスト（Not Found）（FR-011）"""
    orchestrator = Orchestrator(settings=orchestrator_settings)

    with pytest.raises(KeyError):
        await orchestrator.get_team_status("nonexistent-team")


@pytest.mark.asyncio
async def test_orchestrator_workspace_from_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Orchestrator ワークスペース環境変数取得テスト（FR-011）"""
    monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))

    settings = OrchestratorSettings(
        workspace_path=tmp_path,
        timeout_per_team_seconds=600,
        teams=[{"config": "tests/fixtures/team1.toml"}],
    )

    orchestrator = Orchestrator(settings=settings)
    assert orchestrator.workspace == tmp_path


@pytest.mark.asyncio
async def test_orchestrator_workspace_missing_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, isolate_from_project_dotenv: None
) -> None:
    """Orchestrator ワークスペース検証テスト（Article 9準拠 + FR-011）"""
    monkeypatch.delenv("MIXSEEK_WORKSPACE", raising=False)
    monkeypatch.delenv("MIXSEEK_WORKSPACE_PATH", raising=False)

    # Article 9準拠: workspace_pathが必須
    with pytest.raises(Exception):
        OrchestratorSettings(
            timeout_per_team_seconds=600,
            teams=[{"config": "tests/fixtures/team1.toml"}],
        )


@pytest.mark.asyncio
async def test_orchestrator_duplicate_team_id_raises_error(tmp_path: Path) -> None:
    """Orchestrator team_id重複時にValueErrorが発生することを確認（FR-011）"""
    # 絶対パスに変換（相対パスはworkspaceからの相対として解釈されるため）
    team1_path = str(Path("tests/fixtures/team1.toml").resolve())
    team_duplicate_path = str(Path("tests/fixtures/team_duplicate_id.toml").resolve())

    settings = OrchestratorSettings(
        workspace_path=tmp_path,
        timeout_per_team_seconds=600,
        teams=[
            {"config": team1_path},
            {"config": team_duplicate_path},
        ],
    )

    orchestrator = Orchestrator(settings=settings)

    with pytest.raises(ValueError, match="Duplicate team_id detected: 'test-team-001'"):
        await orchestrator.execute(user_prompt="Test prompt", timeout_seconds=300)


@pytest.mark.skip(reason="Skipped until RoundController + ConfigurationManager integration is implemented")
@pytest.mark.asyncio
async def test_orchestrator_receives_leaderboard_entries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """T044: Orchestrator が各チームから LeaderBoardEntry を受け取ることを検証

    Note: This test is skipped because RoundController uses lazy import and
    ConfigurationManager integration is deferred. Will be re-enabled when
    RoundController + ConfigurationManager integration is implemented.
    """
    from unittest.mock import AsyncMock, patch

    from mixseek.models.leaderboard import LeaderBoardEntry

    monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))

    # 絶対パスに変換
    team1_path = str(Path("tests/fixtures/team1.toml").resolve())

    settings = OrchestratorSettings(
        workspace_path=tmp_path,
        timeout_per_team_seconds=600,
        teams=[{"config": team1_path}],
    )

    orchestrator = Orchestrator(settings=settings)

    # Mock RoundController to return LeaderBoardEntry
    with patch("mixseek.orchestrator.orchestrator.RoundController") as mock_rc_class:
        mock_rc = AsyncMock()
        mock_rc.get_team_id.return_value = "test-team-001"
        mock_rc.get_team_name.return_value = "Test Team 1"

        # Create a mock LeaderBoardEntry
        from datetime import UTC, datetime

        mock_entry = LeaderBoardEntry(
            execution_id="test-execution-id",
            team_id="test-team-001",
            team_name="Test Team 1",
            round_number=2,
            submission_content="Best submission",
            score=85.0,
            score_details={"metric1": 85.0},
            final_submission=True,
            exit_reason="max rounds reached",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        mock_rc.run_round.return_value = mock_entry
        mock_rc_class.return_value = mock_rc

        # Execute
        summary = await orchestrator.execute(user_prompt="Test prompt", timeout_seconds=300)

        # Verify: ExecutionSummary contains LeaderBoardEntry list
        assert len(summary.team_results) == 1
        result = summary.team_results[0]
        assert isinstance(result, LeaderBoardEntry)
        assert result.team_id == "test-team-001"
        assert result.score == 85.0
        assert result.final_submission is True
        assert result.exit_reason == "max rounds reached"

        # Verify: best_score is on 0-100 scale
        assert summary.best_score == 85.0
        assert summary.best_team_id == "test-team-001"


# =============================================================================
# Issue #68: on_round_complete callback tests
# =============================================================================


def test_orchestrator_with_on_round_complete(orchestrator_settings: OrchestratorSettings) -> None:
    """Orchestrator on_round_complete パラメータテスト

    Issue #68: OrchestratorがRoundControllerにon_round_completeをパススルーする
    """

    async def dummy_callback(
        round_state: RoundState,
        member_submissions: list[MemberSubmission],
    ) -> None:
        pass

    orchestrator = Orchestrator(
        settings=orchestrator_settings,
        on_round_complete=dummy_callback,
    )
    assert orchestrator._on_round_complete is dummy_callback


def test_orchestrator_on_round_complete_none_default(orchestrator_settings: OrchestratorSettings) -> None:
    """Orchestrator on_round_complete デフォルト値テスト

    Issue #68: on_round_completeのデフォルト値はNone
    """
    orchestrator = Orchestrator(settings=orchestrator_settings)
    assert orchestrator._on_round_complete is None


@pytest.mark.asyncio
async def test_orchestrator_passes_on_round_complete_to_round_controller(tmp_path: Path) -> None:
    """Orchestrator が on_round_complete を RoundController に渡すことを検証

    Issue #68: OrchestratorはRoundController作成時にon_round_completeをパススルーする
    """
    from datetime import UTC, datetime

    from mixseek.models.leaderboard import LeaderBoardEntry

    async def dummy_callback(
        round_state: RoundState,
        member_submissions: list[MemberSubmission],
    ) -> None:
        pass

    # 絶対パスに変換
    team1_path = str(Path("tests/fixtures/team1.toml").resolve())

    settings = OrchestratorSettings(
        workspace_path=tmp_path,
        timeout_per_team_seconds=600,
        teams=[{"config": team1_path}],
    )

    orchestrator = Orchestrator(
        settings=settings,
        save_db=False,
        on_round_complete=dummy_callback,
    )

    # Mock RoundController to capture constructor arguments
    # Note: RoundController is lazy imported inside _execute_impl, so patch the source module
    with patch("mixseek.round_controller.RoundController") as mock_rc_class:
        mock_rc = AsyncMock()
        mock_rc.get_team_id.return_value = "test-team-001"
        mock_rc.get_team_name.return_value = "Test Team 1"

        # Create a mock LeaderBoardEntry
        mock_entry = LeaderBoardEntry(
            execution_id="test-execution-id",
            team_id="test-team-001",
            team_name="Test Team 1",
            round_number=1,
            submission_content="Test submission",
            score=80.0,
            score_details={"metric1": 80.0},
            final_submission=True,
            exit_reason="max rounds reached",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_rc.run_round.return_value = mock_entry
        mock_rc_class.return_value = mock_rc

        # Execute
        await orchestrator.execute(user_prompt="Test prompt", timeout_seconds=300)

        # Verify RoundController was instantiated with on_round_complete
        mock_rc_class.assert_called_once()
        call_kwargs = mock_rc_class.call_args.kwargs
        assert "on_round_complete" in call_kwargs
        assert call_kwargs["on_round_complete"] is dummy_callback


# =============================================================================
# Partial team failure recovery tests
# =============================================================================


def _make_mock_round_state(round_number: int = 1, score: float = 75.0) -> RoundState:
    """テスト用RoundState生成ヘルパー"""
    now = datetime.now(UTC)
    return RoundState(
        round_number=round_number,
        submission_content="test submission",
        evaluation_score=score,
        score_details={"overall_score": score},
        improvement_judgment=None,
        round_started_at=now,
        round_ended_at=now,
        message_history=[],
    )


def _make_mock_entry(team_id: str = "test-team-001", team_name: str = "Test Team 1") -> LeaderBoardEntry:
    """テスト用LeaderBoardEntry生成ヘルパー"""
    now = datetime.now(UTC)
    return LeaderBoardEntry(
        execution_id="test-execution-id",
        team_id=team_id,
        team_name=team_name,
        round_number=1,
        submission_content="best submission",
        score=80.0,
        score_details={"metric1": 80.0},
        final_submission=True,
        exit_reason="partial_failure",
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_run_team_partial_failure_with_round_history(tmp_path: Path) -> None:
    """_run_team: round_history が非空の時に PartialTeamFailureError が送出される"""
    team1_path = str(Path("tests/fixtures/team1.toml").resolve())

    settings = OrchestratorSettings(
        workspace_path=tmp_path,
        timeout_per_team_seconds=600,
        teams=[{"config": team1_path}],
    )
    orchestrator = Orchestrator(settings=settings, save_db=False)

    # TeamStatus を手動登録（_execute_impl が行う初期化を模擬）
    from mixseek.orchestrator.models import TeamStatus

    orchestrator.team_statuses["test-team-001"] = TeamStatus(
        team_id="test-team-001",
        team_name="Test Team 1",
    )

    # Mock controller
    mock_controller = MagicMock()
    mock_controller.get_team_id.return_value = "test-team-001"
    mock_controller.get_team_name.return_value = "Test Team 1"
    mock_controller.round_history = [_make_mock_round_state()]

    # run_round が例外を送出
    mock_controller.run_round = AsyncMock(side_effect=RuntimeError("evaluator API error"))

    # _finalize_and_return_best が最善結果を返す
    mock_entry = _make_mock_entry()
    mock_controller._finalize_and_return_best = AsyncMock(return_value=mock_entry)

    # _write_progress_file のモック
    mock_controller._write_progress_file = MagicMock()

    # When
    with pytest.raises(PartialTeamFailureError) as exc_info:
        await orchestrator._run_team(mock_controller, "test prompt", 600)

    # Then
    assert exc_info.value.entry is mock_entry
    assert isinstance(exc_info.value.original_error, RuntimeError)
    assert orchestrator.team_statuses["test-team-001"].status == "failed"
    mock_controller._finalize_and_return_best.assert_awaited_once_with("partial_failure", None)


@pytest.mark.asyncio
async def test_run_team_no_round_history_raises_original(tmp_path: Path) -> None:
    """_run_team: round_history が空の場合は元の例外がそのまま送出される"""
    team1_path = str(Path("tests/fixtures/team1.toml").resolve())

    settings = OrchestratorSettings(
        workspace_path=tmp_path,
        timeout_per_team_seconds=600,
        teams=[{"config": team1_path}],
    )
    orchestrator = Orchestrator(settings=settings, save_db=False)

    from mixseek.orchestrator.models import TeamStatus

    orchestrator.team_statuses["test-team-001"] = TeamStatus(
        team_id="test-team-001",
        team_name="Test Team 1",
    )

    mock_controller = MagicMock()
    mock_controller.get_team_id.return_value = "test-team-001"
    mock_controller.get_team_name.return_value = "Test Team 1"
    mock_controller.round_history = []  # 空: ラウンド0で失敗
    mock_controller.run_round = AsyncMock(side_effect=RuntimeError("immediate failure"))
    mock_controller._write_progress_file = MagicMock()

    with pytest.raises(RuntimeError, match="immediate failure"):
        await orchestrator._run_team(mock_controller, "test prompt", 600)

    assert orchestrator.team_statuses["test-team-001"].status == "failed"


@pytest.mark.asyncio
async def test_execute_impl_handles_partial_team_failure(tmp_path: Path) -> None:
    """_execute_impl: PartialTeamFailureError が team_results と failed_teams_info の両方に入る"""
    team1_path = str(Path("tests/fixtures/team1.toml").resolve())

    settings = OrchestratorSettings(
        workspace_path=tmp_path,
        timeout_per_team_seconds=600,
        teams=[{"config": team1_path}],
    )
    orchestrator = Orchestrator(settings=settings, save_db=False)

    mock_entry = _make_mock_entry()

    with patch("mixseek.round_controller.RoundController") as mock_rc_class:
        mock_rc = MagicMock()
        mock_rc.get_team_id.return_value = "test-team-001"
        mock_rc.get_team_name.return_value = "Test Team 1"
        mock_rc.round_history = [_make_mock_round_state()]
        mock_rc.run_round = AsyncMock(side_effect=RuntimeError("round 2 failed"))
        mock_rc._finalize_and_return_best = AsyncMock(return_value=mock_entry)
        mock_rc._write_progress_file = MagicMock()
        mock_rc_class.return_value = mock_rc

        summary = await orchestrator.execute(user_prompt="Test prompt", timeout_seconds=300)

    # team_results と failed_teams_info の両方に同一チームが入る
    assert len(summary.team_results) == 1
    assert summary.team_results[0].team_id == "test-team-001"
    assert len(summary.failed_teams_info) == 1
    assert summary.failed_teams_info[0].team_id == "test-team-001"
    assert summary.total_teams == 1  # 重複排除
    assert summary.partial_teams == 1
