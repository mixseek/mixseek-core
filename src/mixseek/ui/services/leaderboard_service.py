"""Leaderboard service for fetching leaderboard data from DuckDB."""

import json

from mixseek.ui.models.leaderboard import LeaderboardEntry, Submission
from mixseek.ui.utils.duckdb_conn import get_read_connection


def fetch_leaderboard(execution_id: str) -> list[LeaderboardEntry]:
    """指定実行IDのリーダーボードを取得（leader_boardテーブル）.

    全チームの全ラウンドのレコードを取得します。

    Args:
        execution_id: 実行ID

    Returns:
        list[LeaderboardEntry]: リーダーボードエントリ（rank昇順）
    """
    try:
        conn = get_read_connection()
        if conn is None:
            # 接続失敗時（Orchestrator実行中など）は空リスト
            return []

        result = conn.execute(
            """
            SELECT
                team_id,
                team_name,
                score,
                ROW_NUMBER() OVER (ORDER BY score DESC, created_at ASC) as rank,
                round_number,
                created_at,
                execution_id
            FROM leader_board
            WHERE execution_id = ?
            ORDER BY score DESC, created_at ASC
        """,
            [execution_id],
        ).fetchall()

        conn.close()

        entries = [
            LeaderboardEntry(
                team_id=row[0],
                team_name=row[1],
                score=row[2],
                rank=row[3],
                round_number=row[4],
                created_at=row[5],
                execution_id=row[6],
            )
            for row in result
        ]

        return entries

    except FileNotFoundError:
        # DBファイルが存在しない場合は空リスト
        return []


def fetch_team_submission(execution_id: str, team_id: str, round_number: int) -> Submission | None:
    """指定チームの特定ラウンドのサブミッションを取得（leader_boardテーブルから）.

    Args:
        execution_id: 実行ID
        team_id: チームID
        round_number: ラウンド番号

    Returns:
        Submission | None: チームのサブミッション（存在しない場合はNone）
    """
    try:
        conn = get_read_connection()
        if conn is None:
            # 接続失敗時（Orchestrator実行中など）はNone
            return None

        result = conn.execute(
            """
            SELECT
                team_id,
                team_name,
                execution_id,
                score,
                submission_content,
                score_details,
                round_number,
                created_at
            FROM leader_board
            WHERE execution_id = ? AND team_id = ? AND round_number = ?
            LIMIT 1
        """,
            [execution_id, team_id, round_number],
        ).fetchone()

        conn.close()

        if not result:
            return None

        # Parse JSON score_details
        score_details = json.loads(result[5]) if isinstance(result[5], str) else result[5]

        return Submission(
            team_id=result[0],
            team_name=result[1],
            execution_id=result[2],
            score=result[3],
            submission_content=result[4],
            score_details=score_details,
            round_number=result[6],
            created_at=result[7],
        )

    except FileNotFoundError:
        return None


def fetch_top_submission(execution_id: str) -> Submission | None:
    """最高スコアのサブミッションを取得（leader_boardテーブルから）.

    Args:
        execution_id: 実行ID

    Returns:
        Submission | None: 最高スコアのサブミッション（存在しない場合はNone）
    """
    try:
        conn = get_read_connection()
        if conn is None:
            # 接続失敗時（Orchestrator実行中など）はNone
            return None

        result = conn.execute(
            """
            SELECT
                team_id,
                team_name,
                execution_id,
                score,
                submission_content,
                score_details,
                round_number,
                created_at
            FROM leader_board
            WHERE execution_id = ?
            ORDER BY score DESC, created_at ASC
            LIMIT 1
        """,
            [execution_id],
        ).fetchone()

        conn.close()

        if not result:
            return None

        # Parse JSON score_details
        score_details = json.loads(result[5]) if isinstance(result[5], str) else result[5]

        return Submission(
            team_id=result[0],
            team_name=result[1],
            execution_id=result[2],
            score=result[3],
            submission_content=result[4],
            score_details=score_details,
            round_number=result[6],
            created_at=result[7],
        )

    except FileNotFoundError:
        return None
