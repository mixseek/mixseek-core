"""Unit tests for UserPromptBuilder class."""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from mixseek.config.schema import PromptBuilderSettings
from mixseek.prompt_builder.builder import UserPromptBuilder
from mixseek.prompt_builder.models import RoundPromptContext
from mixseek.round_controller.models import RoundState


class TestUserPromptBuilderRound1:
    """Tests for Round 1 prompt generation."""

    async def test_round_1_no_history_no_ranking(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test Round 1 prompt with no history and no ranking."""
        monkeypatch.delenv("TZ", raising=False)

        settings = PromptBuilderSettings()
        builder = UserPromptBuilder(settings=settings, store=None)
        context = RoundPromptContext(
            user_prompt="データ分析タスク",
            round_number=1,
            round_history=[],
            team_id="team1",
            team_name="Alpha",
            execution_id="exec1",
            store=None,
        )

        result = await builder.build_team_prompt(context)

        assert "# ユーザから指定されたタスク" in result
        assert "データ分析タスク" in result
        assert "まだ過去のSubmissionはありません。" in result
        assert "現在日時:" in result
        # History section is always present
        assert "# 過去の提出履歴" in result
        # Should contain empty ranking message in round 1
        assert "まだランキング情報がありません。" in result


class TestUserPromptBuilderRound2Plus:
    """Tests for Round 2+ prompt generation."""

    async def test_round_2_with_history_no_store(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test Round 2 prompt with history but no store."""
        monkeypatch.delenv("TZ", raising=False)
        now = datetime.now(UTC)

        history = [
            RoundState(
                round_number=1,
                submission_content="First submission",
                evaluation_score=75.5,
                score_details={},
                round_started_at=now,
                round_ended_at=now,
            )
        ]

        settings = PromptBuilderSettings()
        builder = UserPromptBuilder(settings=settings, store=None)
        context = RoundPromptContext(
            user_prompt="データ分析タスク",
            round_number=2,
            round_history=history,
            team_id="team1",
            team_name="Alpha",
            execution_id="exec1",
            store=None,
        )

        result = await builder.build_team_prompt(context)

        assert "# ユーザから指定されたタスク" in result
        assert "データ分析タスク" in result
        assert "# 過去の提出履歴" in result
        assert "## ラウンド 1" in result
        assert "スコア: 75.50/100" in result
        # Should contain empty ranking message since store is None
        assert "まだランキング情報がありません。" in result
        assert "まだあなたのチームの順位はありません。" in result

    @pytest.mark.asyncio
    async def test_round_2_with_history_and_ranking(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test Round 2 prompt with history and ranking from store."""
        monkeypatch.delenv("TZ", raising=False)
        now = datetime.now(UTC)

        history = [
            RoundState(
                round_number=1,
                submission_content="First submission",
                evaluation_score=85.5,
                score_details={},
                round_started_at=now,
                round_ended_at=now,
            )
        ]

        # Mock store with spec
        from mixseek.storage.aggregation_store import AggregationStore

        mock_store = MagicMock(spec=AggregationStore)
        mock_store.get_leader_board_ranking = AsyncMock(
            return_value=[
                {"team_id": "team1", "team_name": "Alpha", "max_score": 85.5, "total_rounds": 1},
                {"team_id": "team2", "team_name": "Beta", "max_score": 80.0, "total_rounds": 1},
            ]
        )

        settings = PromptBuilderSettings()
        builder = UserPromptBuilder(settings=settings, store=mock_store)
        context = RoundPromptContext(
            user_prompt="データ分析タスク",
            round_number=2,
            round_history=history,
            team_id="team1",
            team_name="Alpha",
            execution_id="exec1",
            store=mock_store,
        )

        result = await builder.build_team_prompt(context)

        assert "# ユーザから指定されたタスク" in result
        assert "# 過去の提出履歴" in result
        assert "## ラウンド 1" in result
        assert "# 現在のリーダーボード" in result
        assert "**#1 Alpha (あなたのチーム)" in result
        assert "#2 Beta" in result
        assert "🏆 現在、あなたのチームは1位です！" in result

    async def test_round_3_with_all_history(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test Round 3 with ALL rounds in history (not just last 2)."""
        monkeypatch.delenv("TZ", raising=False)
        now = datetime.now(UTC)

        history = [
            RoundState(
                round_number=1,
                submission_content="First submission",
                evaluation_score=70.0,
                score_details={},
                round_started_at=now,
                round_ended_at=now,
            ),
            RoundState(
                round_number=2,
                submission_content="Second submission",
                evaluation_score=80.0,
                score_details={},
                round_started_at=now,
                round_ended_at=now,
            ),
        ]

        settings = PromptBuilderSettings()
        builder = UserPromptBuilder(settings=settings, store=None)
        context = RoundPromptContext(
            user_prompt="データ分析タスク",
            round_number=3,
            round_history=history,
            team_id="team1",
            team_name="Alpha",
            execution_id="exec1",
            store=None,
        )

        result = await builder.build_team_prompt(context)

        # Verify ALL rounds are included (not just last 2)
        assert "## ラウンド 1" in result
        assert "## ラウンド 2" in result
        assert "スコア: 70.00/100" in result
        assert "スコア: 80.00/100" in result


class TestUserPromptBuilderCustomTemplate:
    """Tests for custom TOML template usage (User Story 2)."""

    async def test_custom_template_from_toml(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test custom template usage from TOML config."""
        # Given: Create custom TOML config with custom template
        configs_dir = tmp_path / "configs"
        configs_dir.mkdir(parents=True, exist_ok=True)
        toml_path = configs_dir / "prompt_builder.toml"

        custom_template = """カスタムプロンプト
タスク: {{ user_prompt }}
ラウンド: {{ round_number }}"""

        toml_path.write_text(f'[prompt_builder]\nteam_user_prompt = """{custom_template}"""', encoding="utf-8")

        # Given: Load custom settings from TOML using ConfigurationManager
        from mixseek.config import ConfigurationManager

        config_manager = ConfigurationManager(workspace=tmp_path)
        settings = config_manager.load_prompt_builder_settings(toml_path)
        builder = UserPromptBuilder(settings=settings, store=None)

        # When: Build prompt for round 1
        context = RoundPromptContext(
            user_prompt="テストタスク",
            round_number=1,
            round_history=[],
            team_id="team1",
            team_name="Alpha",
            execution_id="exec1",
            store=None,
        )
        result = await builder.build_team_prompt(context)

        # Then: Verify custom template is used
        assert "カスタムプロンプト" in result
        assert "タスク: テストタスク" in result
        assert "ラウンド: 1" in result
        # Default template content should NOT be present
        assert "ユーザから指定されたタスク" not in result

    async def test_placeholder_variables_user_prompt(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test {{ user_prompt }} placeholder variable."""
        configs_dir = tmp_path / "configs"
        configs_dir.mkdir(parents=True, exist_ok=True)
        toml_path = configs_dir / "prompt_builder.toml"
        toml_path.write_text('[prompt_builder]\nteam_user_prompt = """PROMPT: {{ user_prompt }}"""', encoding="utf-8")

        from mixseek.config import ConfigurationManager

        config_manager = ConfigurationManager(workspace=tmp_path)
        settings = config_manager.load_prompt_builder_settings(toml_path)
        builder = UserPromptBuilder(settings=settings, store=None)
        context = RoundPromptContext(
            user_prompt="カスタムユーザプロンプト",
            round_number=1,
            round_history=[],
            team_id="team1",
            team_name="Alpha",
            execution_id="exec1",
            store=None,
        )
        result = await builder.build_team_prompt(context)

        assert "PROMPT: カスタムユーザプロンプト" in result

    async def test_placeholder_variables_round_number(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test {{ round_number }} placeholder variable."""
        configs_dir = tmp_path / "configs"
        configs_dir.mkdir(parents=True, exist_ok=True)
        toml_path = configs_dir / "prompt_builder.toml"
        toml_path.write_text('[prompt_builder]\nteam_user_prompt = """Round: {{ round_number }}"""', encoding="utf-8")

        from mixseek.config import ConfigurationManager

        config_manager = ConfigurationManager(workspace=tmp_path)
        settings = config_manager.load_prompt_builder_settings(toml_path)
        builder = UserPromptBuilder(settings=settings, store=None)
        context = RoundPromptContext(
            user_prompt="Test",
            round_number=3,
            round_history=[],
            team_id="team1",
            team_name="Alpha",
            execution_id="exec1",
            store=None,
        )
        result = await builder.build_team_prompt(context)

        assert "Round: 3" in result

    async def test_placeholder_variables_submission_history(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test {{ submission_history }} placeholder variable."""
        monkeypatch.delenv("TZ", raising=False)
        now = datetime.now(UTC)

        configs_dir = tmp_path / "configs"
        configs_dir.mkdir(parents=True, exist_ok=True)
        toml_path = configs_dir / "prompt_builder.toml"
        toml_path.write_text(
            '[prompt_builder]\nteam_user_prompt = """History:\n{{ submission_history }}"""', encoding="utf-8"
        )

        history = [
            RoundState(
                round_number=1,
                submission_content="Test submission",
                evaluation_score=85.5,
                score_details={},
                round_started_at=now,
                round_ended_at=now,
            )
        ]

        from mixseek.config import ConfigurationManager

        config_manager = ConfigurationManager(workspace=tmp_path)
        settings = config_manager.load_prompt_builder_settings(toml_path)
        builder = UserPromptBuilder(settings=settings, store=None)
        context = RoundPromptContext(
            user_prompt="Test",
            round_number=2,
            round_history=history,
            team_id="team1",
            team_name="Alpha",
            execution_id="exec1",
            store=None,
        )
        result = await builder.build_team_prompt(context)

        assert "History:" in result
        assert "## ラウンド 1" in result
        assert "Test submission" in result

    async def test_placeholder_variables_ranking_table(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test {{ ranking_table }} placeholder variable."""
        monkeypatch.delenv("TZ", raising=False)
        now = datetime.now(UTC)

        configs_dir = tmp_path / "configs"
        configs_dir.mkdir(parents=True, exist_ok=True)
        toml_path = configs_dir / "prompt_builder.toml"
        toml_path.write_text(
            '[prompt_builder]\nteam_user_prompt = """Ranking:\n{{ ranking_table }}"""', encoding="utf-8"
        )

        history = [
            RoundState(
                round_number=1,
                submission_content="Test",
                evaluation_score=85.5,
                score_details={},
                round_started_at=now,
                round_ended_at=now,
            )
        ]

        # Mock store
        from mixseek.storage.aggregation_store import AggregationStore

        mock_store = MagicMock(spec=AggregationStore)
        mock_store.get_leader_board_ranking = AsyncMock(
            return_value=[
                {"team_id": "team1", "team_name": "Alpha", "max_score": 85.5, "total_rounds": 1},
            ]
        )

        from mixseek.config import ConfigurationManager

        config_manager = ConfigurationManager(workspace=tmp_path)
        settings = config_manager.load_prompt_builder_settings(toml_path)
        builder = UserPromptBuilder(settings=settings, store=mock_store)
        context = RoundPromptContext(
            user_prompt="Test",
            round_number=2,
            round_history=history,
            team_id="team1",
            team_name="Alpha",
            execution_id="exec1",
            store=mock_store,
        )
        result = await builder.build_team_prompt(context)

        assert "Ranking:" in result
        assert "**#1 Alpha (あなたのチーム)" in result

    async def test_placeholder_variables_current_datetime(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test {{ current_datetime }} placeholder variable."""
        monkeypatch.delenv("TZ", raising=False)

        configs_dir = tmp_path / "configs"
        configs_dir.mkdir(parents=True, exist_ok=True)
        toml_path = configs_dir / "prompt_builder.toml"
        toml_path.write_text(
            '[prompt_builder]\nteam_user_prompt = """Time: {{ current_datetime }}"""', encoding="utf-8"
        )

        from mixseek.config import ConfigurationManager

        config_manager = ConfigurationManager(workspace=tmp_path)
        settings = config_manager.load_prompt_builder_settings(toml_path)
        builder = UserPromptBuilder(settings=settings, store=None)
        context = RoundPromptContext(
            user_prompt="Test",
            round_number=1,
            round_history=[],
            team_id="team1",
            team_name="Alpha",
            execution_id="exec1",
            store=None,
        )
        result = await builder.build_team_prompt(context)

        assert "Time: " in result
        # Verify ISO 8601 format with timezone (should end with +00:00 for UTC)
        assert "+00:00" in result or "Z" in result
