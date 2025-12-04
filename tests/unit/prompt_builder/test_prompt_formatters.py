"""Unit tests for prompt_builder formatters.

Feature: 092-user-prompt-builder-team
Date: 2025-11-19
"""

from datetime import UTC, datetime

import pytest

from mixseek.prompt_builder.formatters import (
    format_ranking_table,
    format_submission_history,
    generate_position_message,
    get_current_datetime_with_timezone,
)
from mixseek.round_controller.models import RoundState


class TestGetCurrentDatetimeWithTimezone:
    """Tests for get_current_datetime_with_timezone function."""

    def test_default_utc_when_tz_not_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that UTC is used when TZ is not set."""
        monkeypatch.delenv("TZ", raising=False)
        result = get_current_datetime_with_timezone()
        assert "+00:00" in result or result.endswith("Z")

    def test_valid_timezone_asia_tokyo(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test with valid timezone Asia/Tokyo."""
        monkeypatch.setenv("TZ", "Asia/Tokyo")
        result = get_current_datetime_with_timezone()
        assert "+09:00" in result

    def test_valid_timezone_america_new_york(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test with valid timezone America/New_York."""
        monkeypatch.setenv("TZ", "America/New_York")
        result = get_current_datetime_with_timezone()
        # EST/EDT is either -05:00 or -04:00
        assert "-05:00" in result or "-04:00" in result

    def test_invalid_timezone_raises_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that invalid TZ raises ValueError."""
        monkeypatch.setenv("TZ", "Invalid/Timezone")
        with pytest.raises(ValueError, match="Invalid timezone in TZ environment variable"):
            get_current_datetime_with_timezone()


class TestFormatSubmissionHistory:
    """Tests for format_submission_history function."""

    def test_empty_history(self) -> None:
        """Test with empty history."""
        result = format_submission_history([])
        assert result == "まだ過去のSubmissionはありません。"

    def test_single_round_history(self) -> None:
        """Test with single round history."""
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
        result = format_submission_history(history)
        assert "## ラウンド 1" in result
        assert "### スコア: 75.50/100" in result
        assert "### あなたの提出内容:" in result
        assert "First submission" in result

    def test_multiple_rounds_history(self) -> None:
        """Test with multiple rounds history."""
        now = datetime.now(UTC)
        history = [
            RoundState(
                round_number=1,
                submission_content="First submission",
                evaluation_score=75.5,
                score_details={},
                round_started_at=now,
                round_ended_at=now,
            ),
            RoundState(
                round_number=2,
                submission_content="Second submission",
                evaluation_score=85.0,
                score_details={},
                round_started_at=now,
                round_ended_at=now,
            ),
        ]
        result = format_submission_history(history)
        assert "## ラウンド 1" in result
        assert "## ラウンド 2" in result
        assert "スコア: 75.50/100" in result
        assert "スコア: 85.00/100" in result


class TestFormatRankingTable:
    """Tests for format_ranking_table function."""

    def test_none_ranking(self) -> None:
        """Test with None ranking (ranking feature unavailable)."""
        result = format_ranking_table(None, "team1")
        assert result == "まだランキング情報がありません。"

    def test_empty_ranking(self) -> None:
        """Test with empty ranking."""
        result = format_ranking_table([], "team1")
        assert result == "まだランキング情報がありません。"

    def test_single_team_ranking(self) -> None:
        """Test with single team ranking."""
        ranking = [
            {"team_id": "team1", "team_name": "Alpha", "max_score": 85.5, "total_rounds": 3},
        ]
        result = format_ranking_table(ranking, "team1")
        assert "**#1 Alpha (あなたのチーム) - スコア: 85.50/100 (ラウンド数: 3)**" in result

    def test_multiple_teams_ranking_first_place(self) -> None:
        """Test with multiple teams, current team in first place."""
        ranking = [
            {"team_id": "team1", "team_name": "Alpha", "max_score": 85.5, "total_rounds": 3},
            {"team_id": "team2", "team_name": "Beta", "max_score": 80.0, "total_rounds": 2},
        ]
        result = format_ranking_table(ranking, "team1")
        assert "**#1 Alpha (あなたのチーム) - スコア: 85.50/100 (ラウンド数: 3)**" in result
        assert "#2 Beta - スコア: 80.00/100 (ラウンド数: 2)" in result

    def test_multiple_teams_ranking_second_place(self) -> None:
        """Test with multiple teams, current team in second place."""
        ranking = [
            {"team_id": "team2", "team_name": "Beta", "max_score": 90.0, "total_rounds": 3},
            {"team_id": "team1", "team_name": "Alpha", "max_score": 80.0, "total_rounds": 2},
        ]
        result = format_ranking_table(ranking, "team1")
        assert "#1 Beta - スコア: 90.00/100 (ラウンド数: 3)" in result
        assert "**#2 Alpha (あなたのチーム) - スコア: 80.00/100 (ラウンド数: 2)**" in result


class TestGeneratePositionMessage:
    """Tests for generate_position_message function."""

    def test_none_position(self) -> None:
        """Test with None position (position unavailable)."""
        result = generate_position_message(None, None)
        assert result == "まだあなたのチームの順位はありません。"

    def test_none_position_with_total_teams(self) -> None:
        """Test with None position but valid total_teams."""
        result = generate_position_message(None, 5)
        assert result == "まだあなたのチームの順位はありません。"

    def test_position_with_none_total_teams(self) -> None:
        """Test with valid position but None total_teams."""
        result = generate_position_message(2, None)
        assert result == "まだあなたのチームの順位はありません。"

    def test_first_place(self) -> None:
        """Test message for first place."""
        result = generate_position_message(1, 5)
        assert result == "🏆 現在、あなたのチームは1位です！この調子で頑張ってください。"

    def test_second_place(self) -> None:
        """Test message for second place."""
        result = generate_position_message(2, 5)
        assert result == "現在、5チーム中2位です。素晴らしい成績です！"

    def test_third_place(self) -> None:
        """Test message for third place."""
        result = generate_position_message(3, 5)
        assert result == "現在、5チーム中3位です。素晴らしい成績です！"

    def test_fourth_place(self) -> None:
        """Test message for fourth place."""
        result = generate_position_message(4, 5)
        assert result == "現在、5チーム中4位です。"

    def test_last_place(self) -> None:
        """Test message for last place."""
        result = generate_position_message(5, 5)
        assert result == "現在、5チーム中5位です。"

    def test_invalid_position_too_low(self) -> None:
        """Test error for position < 1."""
        with pytest.raises(ValueError, match="Invalid position"):
            generate_position_message(0, 5)

    def test_invalid_position_too_high(self) -> None:
        """Test error for position > total_teams."""
        with pytest.raises(ValueError, match="Invalid position"):
            generate_position_message(6, 5)

    def test_invalid_total_teams(self) -> None:
        """Test error for total_teams < 1."""
        with pytest.raises(ValueError, match="Invalid total_teams"):
            generate_position_message(1, 0)
