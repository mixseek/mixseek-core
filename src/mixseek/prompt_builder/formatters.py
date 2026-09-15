"""Formatter functions for UserPromptBuilder.

Feature: 092-user-prompt-builder-team
Date: 2025-11-19
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, tzinfo
from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from mixseek.prompt_builder.injection import sanitize_context_text

if TYPE_CHECKING:
    from mixseek.round_controller.models import RoundState


def get_current_datetime_with_timezone() -> str:
    """Get current datetime based on TZ environment variable (ISO 8601 format).

    If TZ environment variable is not set, defaults to UTC.

    Returns:
        ISO 8601 format datetime string with timezone

    Raises:
        ValueError: If TZ environment variable has an invalid value

    Example:
        >>> # TZ not set
        >>> get_current_datetime_with_timezone()
        "2025-11-19T12:34:56.789012+00:00"

        >>> # TZ="Asia/Tokyo"
        >>> get_current_datetime_with_timezone()
        "2025-11-19T21:34:56.789012+09:00"
    """
    tz_name = os.environ.get("TZ")

    tz: tzinfo
    if tz_name is None:
        # Use UTC as default when TZ is not set
        tz = UTC
    else:
        try:
            tz = ZoneInfo(tz_name)
        except ZoneInfoNotFoundError as e:
            msg = (
                f"Invalid timezone in TZ environment variable: {tz_name}. "
                "Valid examples: 'UTC', 'Asia/Tokyo', 'America/New_York'"
            )
            raise ValueError(msg) from e

    now = datetime.now(tz)
    return now.isoformat()


def format_submission_history(round_history: list[RoundState]) -> str:
    """Format past submission history.

    Args:
        round_history: History of all past rounds

    Returns:
        Formatted history string. Returns "まだ過去のSubmissionはありません。"
        if history is empty

    Example:
        >>> history = [
        ...     RoundState(round_number=1, submission_content="...",
        ...                evaluation_score=75.5, score_details={},
        ...                round_started_at=datetime.now(), round_ended_at=datetime.now())
        ... ]
        >>> print(format_submission_history(history))
        ## ラウンド 1
        ### スコア: 75.50/100
        ### スコア詳細:
        {}
        <submission>
        ...
        </submission>

    Note:
        提出内容は LLM の生成物であり Markdown 見出しを含みうるため、`<submission>` タグで
        囲んでラウンド区切りの見出しと衝突しないようにする（issue #153）。
        提出内容に閉じタグが含まれるとブロック境界が壊れるため、埋め込む前に
        `sanitize_context_text` で構造タグを中和する。
    """
    if not round_history:
        return "まだ過去のSubmissionはありません。"

    parts = []
    for state in round_history:
        parts.append(f"## ラウンド {state.round_number}")
        parts.append(f"### スコア: {state.evaluation_score:.2f}/100")
        parts.append("### スコア詳細:")
        parts.append(json.dumps(state.score_details, ensure_ascii=False, indent=2))
        parts.append("<submission>")
        parts.append(sanitize_context_text(state.submission_content))
        parts.append("</submission>")
        parts.append("")  # Empty line between rounds

    # Remove trailing empty line
    return "\n".join(parts[:-1]) if parts else ""


def format_ranking_table(
    ranking: list[dict[str, Any]] | None,
    team_id: str,
) -> str:
    """Format Leader Board ranking.

    Args:
        ranking: Ranking info from Leader Board.
                 Each element: {"team_id": str, "team_name": str,
                               "max_score": float, "total_rounds": int}
                 None if ranking feature is unavailable
        team_id: Current team ID

    Returns:
        Formatted ranking table.
        - Returns empty string if ranking is None (feature unavailable)
        - Returns "まだランキング情報がありません。" if ranking is empty list

    Example:
        >>> ranking = [
        ...     {"team_id": "team1", "team_name": "Alpha",
        ...      "max_score": 85.5, "total_rounds": 3},
        ...     {"team_id": "team2", "team_name": "Beta",
        ...      "max_score": 80.0, "total_rounds": 2},
        ... ]
        >>> print(format_ranking_table(ranking, "team1"))
        **#1 Alpha (あなたのチーム) - スコア: 85.50/100 (ラウンド数: 3)**
        #2 Beta - スコア: 80.00/100 (ラウンド数: 2)
        >>> print(format_ranking_table(None, "team1"))
        <BLANKLINE>
        >>> print(format_ranking_table([], "team1"))
        まだランキング情報がありません。
    """
    # Return empty string if ranking feature is unavailable
    if ranking is None or not ranking:
        return "まだランキング情報がありません。"

    parts = []
    for idx, team_entry in enumerate(ranking, start=1):
        entry_team_id = team_entry["team_id"]
        entry_team_name = sanitize_context_text(team_entry["team_name"])
        max_score = team_entry["max_score"]
        total_rounds = team_entry["total_rounds"]

        if entry_team_id == team_id:
            parts.append(
                f"**#{idx} {entry_team_name} (あなたのチーム) - "
                f"スコア: {max_score:.2f}/100 (ラウンド数: {total_rounds})**"
            )
        else:
            parts.append(f"#{idx} {entry_team_name} - スコア: {max_score:.2f}/100 (ラウンド数: {total_rounds})")

    return "\n".join(parts)


def generate_position_message(position: int | None, total_teams: int | None) -> str:
    """Generate team position message.

    Args:
        position: Team position (>=1), or None if position is unavailable
        total_teams: Total number of teams, or None if unavailable

    Returns:
        Position-specific message, or empty string if position/total_teams is None

    Raises:
        ValueError: If position or total_teams is invalid (when not None)

    Example:
        >>> generate_position_message(1, 5)
        "🏆 現在、あなたのチームは1位です！この調子で頑張ってください。"
        >>> generate_position_message(2, 5)
        "現在、5チーム中2位です。素晴らしい成績です！"
        >>> generate_position_message(4, 5)
        "現在、5チーム中4位です。"
        >>> generate_position_message(None, None)
        "まだあなたのチームの順位はありません。"
    """
    # Return empty string if position or total_teams is None
    if position is None or total_teams is None:
        return "まだあなたのチームの順位はありません。"

    if total_teams < 1:
        msg = f"Invalid total_teams: {total_teams}"
        raise ValueError(msg)
    if position < 1 or position > total_teams:
        msg = f"Invalid position: {position} (total_teams: {total_teams})"
        raise ValueError(msg)

    if position == 1:
        return "🏆 現在、あなたのチームは1位です！この調子で頑張ってください。"
    if position <= 3:
        return f"現在、{total_teams}チーム中{position}位です。素晴らしい成績です！"
    return f"現在、{total_teams}チーム中{position}位です。"
