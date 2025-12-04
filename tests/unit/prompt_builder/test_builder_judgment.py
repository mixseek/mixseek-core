"""Unit tests for UserPromptBuilder.build_judgment_prompt method.

Feature: 140-user-prompt-builder-evaluator-judgement
Task: T024
Date: 2025-11-25
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mixseek.config.schema import PromptBuilderSettings
from mixseek.prompt_builder import UserPromptBuilder
from mixseek.prompt_builder.models import RoundPromptContext
from mixseek.round_controller.models import RoundState


class TestBuildJudgmentPrompt:
    """Tests for UserPromptBuilder.build_judgment_prompt method."""

    async def test_build_judgment_prompt_default_template(self, tmp_path: Path) -> None:
        """Test prompt formatting with default template."""
        settings = PromptBuilderSettings()
        builder = UserPromptBuilder(settings=settings, store=None)

        round_history = [
            RoundState(
                round_number=1,
                submission_content="Initial submission",
                evaluation_score=75.5,
                score_details={"accuracy": 80.0, "completeness": 71.0},
                round_started_at=datetime(2025, 11, 25, 10, 0, 0),
                round_ended_at=datetime(2025, 11, 25, 10, 5, 0),
            )
        ]

        context = RoundPromptContext(
            user_prompt="Test task",
            round_number=2,
            round_history=round_history,
            team_id="team-001",
            team_name="Team Alpha",
            execution_id="exec-123",
            store=None,
        )

        with patch("mixseek.prompt_builder.builder.get_current_datetime_with_timezone") as mock_dt:
            mock_dt.return_value = "2025-11-25T14:30:00+09:00"
            prompt = await builder.build_judgment_prompt(context)

        assert "Test task" in prompt
        assert "Initial submission" in prompt
        assert "タスク" in prompt
        assert "提出履歴" in prompt

    async def test_build_judgment_prompt_custom_template(self, tmp_path: Path) -> None:
        """Test prompt formatting with custom template."""
        custom_template = """Custom Judgment Prompt:
User Prompt: {{ user_prompt }}
Round: {{ round_number }}
History: {{ submission_history }}
Ranking: {{ ranking_table }}
Position: {{ team_position_message }}
DateTime: {{ current_datetime }}"""

        settings = PromptBuilderSettings()
        builder = UserPromptBuilder(settings=settings, store=None)
        builder.settings.judgment_user_prompt = custom_template

        round_history = [
            RoundState(
                round_number=1,
                submission_content="Test submission",
                evaluation_score=80.0,
                score_details={"metric1": 85.0},
                round_started_at=datetime(2025, 11, 25, 10, 0, 0),
                round_ended_at=datetime(2025, 11, 25, 10, 5, 0),
            )
        ]

        context = RoundPromptContext(
            user_prompt="Custom task",
            round_number=2,
            round_history=round_history,
            team_id="team-002",
            team_name="Team Beta",
            execution_id="exec-456",
            store=None,
        )

        with patch("mixseek.prompt_builder.builder.get_current_datetime_with_timezone") as mock_dt:
            mock_dt.return_value = "2025-11-25T15:00:00+09:00"
            prompt = await builder.build_judgment_prompt(context)

        assert "Custom Judgment Prompt:" in prompt
        assert "User Prompt: Custom task" in prompt
        assert "Round: 2" in prompt
        assert "Test submission" in prompt
        assert "DateTime: 2025-11-25T15:00:00+09:00" in prompt

    async def test_build_judgment_prompt_multiple_rounds(self, tmp_path: Path) -> None:
        """Test prompt formatting with multiple round history (format_submission_history integration)."""
        settings = PromptBuilderSettings()
        builder = UserPromptBuilder(settings=settings, store=None)

        round_history = [
            RoundState(
                round_number=1,
                submission_content="Round 1 submission",
                evaluation_score=70.0,
                score_details={"accuracy": 75.0, "completeness": 65.0},
                round_started_at=datetime(2025, 11, 25, 10, 0, 0),
                round_ended_at=datetime(2025, 11, 25, 10, 5, 0),
            ),
            RoundState(
                round_number=2,
                submission_content="Round 2 improved submission",
                evaluation_score=82.5,
                score_details={"accuracy": 85.0, "completeness": 80.0},
                round_started_at=datetime(2025, 11, 25, 11, 0, 0),
                round_ended_at=datetime(2025, 11, 25, 11, 5, 0),
            ),
            RoundState(
                round_number=3,
                submission_content="Round 3 further improved",
                evaluation_score=90.0,
                score_details={"accuracy": 92.0, "completeness": 88.0},
                round_started_at=datetime(2025, 11, 25, 12, 0, 0),
                round_ended_at=datetime(2025, 11, 25, 12, 5, 0),
            ),
        ]

        context = RoundPromptContext(
            user_prompt="Multi-round task",
            round_number=4,
            round_history=round_history,
            team_id="team-003",
            team_name="Team Gamma",
            execution_id="exec-789",
            store=None,
        )

        with patch("mixseek.prompt_builder.builder.get_current_datetime_with_timezone") as mock_dt:
            mock_dt.return_value = "2025-11-25T16:00:00+09:00"
            prompt = await builder.build_judgment_prompt(context)

        # Verify all rounds are included
        assert "Round 1 submission" in prompt
        assert "Round 2 improved submission" in prompt
        assert "Round 3 further improved" in prompt
        assert "70.00/100" in prompt
        assert "82.50/100" in prompt
        assert "90.00/100" in prompt

    async def test_build_judgment_prompt_with_ranking_table(self, tmp_path: Path) -> None:
        """Test formatter integration: format_ranking_table called with correct signature (FR-010)."""
        # Create mock store
        mock_store = MagicMock()
        mock_store.get_leader_board_ranking = AsyncMock(return_value=[])

        settings = PromptBuilderSettings()
        builder = UserPromptBuilder(settings=settings, store=mock_store)

        # Use custom template that includes team_position_message placeholder
        builder.settings.judgment_user_prompt = """Test Judgment:
{{ user_prompt }}
{{ submission_history }}
Ranking: {{ ranking_table }}
Position: {{ team_position_message }}"""

        round_history = [
            RoundState(
                round_number=1,
                submission_content="Test",
                evaluation_score=85.0,
                score_details={"metric1": 85.0},
                round_started_at=datetime(2025, 11, 25, 10, 0, 0),
                round_ended_at=datetime(2025, 11, 25, 10, 5, 0),
            )
        ]

        context = RoundPromptContext(
            user_prompt="Test task",
            round_number=2,
            round_history=round_history,
            team_id="team-001",
            team_name="Team Alpha",
            execution_id="exec-123",
            store=mock_store,
        )

        with (
            patch("mixseek.prompt_builder.builder.get_current_datetime_with_timezone") as mock_dt,
            patch("mixseek.prompt_builder.builder.format_ranking_table") as mock_ranking,
            patch("mixseek.prompt_builder.builder.generate_position_message") as mock_position,
        ):
            mock_dt.return_value = "2025-11-25T14:30:00+09:00"
            mock_ranking.return_value = "Ranking table output"
            mock_position.return_value = "Position message output"

            prompt = await builder.build_judgment_prompt(context)

            # Verify format_ranking_table was called with correct signature (positional args)
            mock_ranking.assert_called_once()
            call_args = mock_ranking.call_args.args
            assert len(call_args) == 2
            assert call_args[0] == []  # ranking (empty list from mocked store)
            assert call_args[1] == "team-001"  # team_id

            # Verify generate_position_message was called
            mock_position.assert_called_once()
            position_args = mock_position.call_args.args
            assert len(position_args) == 2
            assert position_args[0] is None  # current_team_position
            assert position_args[1] is None  # total_teams

            # Verify outputs are embedded in prompt
            assert "Ranking table output" in prompt
            assert "Position message output" in prompt

    async def test_build_judgment_prompt_store_none_empty_ranking(self, tmp_path: Path) -> None:
        """Test that ranking info is empty string when store is None."""
        settings = PromptBuilderSettings()
        builder = UserPromptBuilder(settings=settings, store=None)

        round_history = [
            RoundState(
                round_number=1,
                submission_content="Test",
                evaluation_score=75.0,
                score_details={"metric1": 75.0},
                round_started_at=datetime(2025, 11, 25, 10, 0, 0),
                round_ended_at=datetime(2025, 11, 25, 10, 5, 0),
            )
        ]

        context = RoundPromptContext(
            user_prompt="Test task",
            round_number=2,
            round_history=round_history,
            team_id="team-001",
            team_name="Team Alpha",
            execution_id="exec-123",
            store=None,  # No store
        )

        with patch("mixseek.prompt_builder.builder.get_current_datetime_with_timezone") as mock_dt:
            mock_dt.return_value = "2025-11-25T14:30:00+09:00"
            prompt = await builder.build_judgment_prompt(context)

        # When store is None, ranking_table and team_position_message should be empty
        # The default template has "# リーダーボード" section
        assert "リーダーボード" in prompt
        # But the actual ranking table content should be minimal/empty

    async def test_build_judgment_prompt_placeholder_validation(self, tmp_path: Path) -> None:
        """Test that all required placeholder variables are embedded."""
        settings = PromptBuilderSettings()
        builder = UserPromptBuilder(settings=settings, store=None)

        round_history = [
            RoundState(
                round_number=1,
                submission_content="Special chars: @#$%",
                evaluation_score=88.5,
                score_details={"metric": 88.5},
                round_started_at=datetime(2025, 11, 25, 10, 0, 0),
                round_ended_at=datetime(2025, 11, 25, 10, 5, 0),
            )
        ]

        context = RoundPromptContext(
            user_prompt="Task with special chars: < > &",
            round_number=2,
            round_history=round_history,
            team_id="team-999",
            team_name="Special Team",
            execution_id="exec-999",
            store=None,
        )

        with patch("mixseek.prompt_builder.builder.get_current_datetime_with_timezone") as mock_dt:
            mock_dt.return_value = "2025-11-25T17:00:00+09:00"
            prompt = await builder.build_judgment_prompt(context)

        # Verify placeholders are replaced
        assert "{{ user_prompt }}" not in prompt
        assert "{{ round_number }}" not in prompt
        assert "{{ submission_history }}" not in prompt
        assert "{{ ranking_table }}" not in prompt
        assert "{{ team_position_message }}" not in prompt
        assert "{{ current_datetime }}" not in prompt

        # Verify actual values are present
        assert "Task with special chars: < > &" in prompt
        assert "Special chars: @#$%" in prompt

    async def test_build_judgment_prompt_template_syntax_error(self, tmp_path: Path) -> None:
        """Test that Jinja2 syntax errors raise RuntimeError."""
        settings = PromptBuilderSettings()
        builder = UserPromptBuilder(settings=settings, store=None)
        builder.settings.judgment_user_prompt = "{{ invalid syntax"  # Missing closing braces

        round_history = [
            RoundState(
                round_number=1,
                submission_content="Test",
                evaluation_score=75.0,
                score_details={},
                round_started_at=datetime(2025, 11, 25, 10, 0, 0),
                round_ended_at=datetime(2025, 11, 25, 10, 5, 0),
            )
        ]

        context = RoundPromptContext(
            user_prompt="Test",
            round_number=2,
            round_history=round_history,
            team_id="team-001",
            team_name="Team",
            execution_id="exec-001",
            store=None,
        )

        with pytest.raises(RuntimeError, match="Jinja2 template error"):
            await builder.build_judgment_prompt(context)

    async def test_build_judgment_prompt_undefined_variable_error(self, tmp_path: Path) -> None:
        """Test that undefined variables raise RuntimeError."""
        settings = PromptBuilderSettings()
        builder = UserPromptBuilder(settings=settings, store=None)
        builder.settings.judgment_user_prompt = "Before {{ undefined_variable }} After"

        round_history = [
            RoundState(
                round_number=1,
                submission_content="Test",
                evaluation_score=75.0,
                score_details={},
                round_started_at=datetime(2025, 11, 25, 10, 0, 0),
                round_ended_at=datetime(2025, 11, 25, 10, 5, 0),
            )
        ]

        context = RoundPromptContext(
            user_prompt="Test",
            round_number=2,
            round_history=round_history,
            team_id="team-001",
            team_name="Team",
            execution_id="exec-001",
            store=None,
        )

        # StrictUndefined behavior: undefined variables raise RuntimeError
        with pytest.raises(RuntimeError, match="Jinja2 template error"):
            await builder.build_judgment_prompt(context)

    async def test_build_judgment_prompt_formatter_integration_completeness(self, tmp_path: Path) -> None:
        """Test complete formatter integration: all formatters called with correct signatures (FR-010)."""
        mock_store = MagicMock()
        mock_store.get_leader_board_ranking = AsyncMock(return_value=[])
        settings = PromptBuilderSettings()
        builder = UserPromptBuilder(settings=settings, store=mock_store)

        # Use custom template that includes all placeholders
        builder.settings.judgment_user_prompt = """Complete Test:
User: {{ user_prompt }}
Round: {{ round_number }}
History: {{ submission_history }}
Ranking: {{ ranking_table }}
Position: {{ team_position_message }}
DateTime: {{ current_datetime }}"""

        round_history = [
            RoundState(
                round_number=1,
                submission_content="Round 1",
                evaluation_score=80.0,
                score_details={"metric1": 80.0},
                round_started_at=datetime(2025, 11, 25, 10, 0, 0),
                round_ended_at=datetime(2025, 11, 25, 10, 5, 0),
            ),
            RoundState(
                round_number=2,
                submission_content="Round 2",
                evaluation_score=85.0,
                score_details={"metric1": 85.0},
                round_started_at=datetime(2025, 11, 25, 11, 0, 0),
                round_ended_at=datetime(2025, 11, 25, 11, 5, 0),
            ),
        ]

        context = RoundPromptContext(
            user_prompt="Complete integration test",
            round_number=3,
            round_history=round_history,
            team_id="team-complete",
            team_name="Complete Team",
            execution_id="exec-complete",
            store=mock_store,
        )

        with (
            patch("mixseek.prompt_builder.builder.get_current_datetime_with_timezone") as mock_dt,
            patch("mixseek.prompt_builder.builder.format_submission_history") as mock_history,
            patch("mixseek.prompt_builder.builder.format_ranking_table") as mock_ranking,
            patch("mixseek.prompt_builder.builder.generate_position_message") as mock_position,
        ):
            mock_dt.return_value = "2025-11-25T18:00:00+09:00"
            mock_history.return_value = "Formatted submission history"
            mock_ranking.return_value = "Formatted ranking table"
            mock_position.return_value = "Team position: 2nd place"

            prompt = await builder.build_judgment_prompt(context)

            # Verify format_submission_history called
            mock_history.assert_called_once_with(round_history)

            # Verify format_ranking_table called with correct signature (positional args)
            mock_ranking.assert_called_once()
            ranking_args = mock_ranking.call_args.args
            assert len(ranking_args) == 2
            assert ranking_args[0] == []  # ranking (empty list from mocked store)
            assert ranking_args[1] == "team-complete"  # team_id

            # Verify generate_position_message called (positional args)
            mock_position.assert_called_once()
            position_args = mock_position.call_args.args
            assert len(position_args) == 2
            assert position_args[0] is None  # current_team_position
            assert position_args[1] is None  # total_teams

            # Verify all outputs embedded in prompt
            assert "Formatted submission history" in prompt
            assert "Formatted ranking table" in prompt
            assert "Team position: 2nd place" in prompt
            assert "2025-11-25T18:00:00+09:00" in prompt

    async def test_build_judgment_prompt_empty_round_history(self, tmp_path: Path) -> None:
        """Test handling of empty round history."""
        settings = PromptBuilderSettings()
        builder = UserPromptBuilder(settings=settings, store=None)

        context = RoundPromptContext(
            user_prompt="New task",
            round_number=1,
            round_history=[],  # Empty history
            team_id="team-new",
            team_name="New Team",
            execution_id="exec-new",
            store=None,
        )

        with patch("mixseek.prompt_builder.builder.get_current_datetime_with_timezone") as mock_dt:
            mock_dt.return_value = "2025-11-25T19:00:00+09:00"
            prompt = await builder.build_judgment_prompt(context)

        # Should not crash, should generate valid prompt
        assert "New task" in prompt
        assert "タスク" in prompt

    async def test_build_judgment_prompt_unicode_and_multiline(self, tmp_path: Path) -> None:
        """Test that Unicode characters and multiline content are handled correctly."""
        settings = PromptBuilderSettings()
        builder = UserPromptBuilder(settings=settings, store=None)

        round_history = [
            RoundState(
                round_number=1,
                submission_content="日本語の提出内容\n複数行のテキスト\n特殊文字: 😀🐍",
                evaluation_score=92.5,
                score_details={"正確性": 95.0, "完全性": 90.0},
                round_started_at=datetime(2025, 11, 25, 10, 0, 0),
                round_ended_at=datetime(2025, 11, 25, 10, 5, 0),
            )
        ]

        context = RoundPromptContext(
            user_prompt="日本語のタスク\n改行を含む\n絵文字も: ✅❌",
            round_number=2,
            round_history=round_history,
            team_id="team-unicode",
            team_name="ユニコードチーム",
            execution_id="exec-unicode",
            store=None,
        )

        with patch("mixseek.prompt_builder.builder.get_current_datetime_with_timezone") as mock_dt:
            mock_dt.return_value = "2025-11-25T20:00:00+09:00"
            prompt = await builder.build_judgment_prompt(context)

        assert "日本語のタスク" in prompt
        assert "改行を含む" in prompt
        assert "✅❌" in prompt
        assert "日本語の提出内容" in prompt
        assert "😀🐍" in prompt
