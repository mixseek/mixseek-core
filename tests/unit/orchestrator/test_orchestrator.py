"""Unit tests for Orchestrator"""

from pathlib import Path

import pytest

from mixseek.config.schema import OrchestratorSettings
from mixseek.orchestrator import Orchestrator


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
