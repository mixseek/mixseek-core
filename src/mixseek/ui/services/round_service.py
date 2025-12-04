"""ラウンドデータ取得サービス.

DuckDB (mixseek.db) からラウンド進捗、スコア推移、サブミッション情報を取得します。

Functions:
    fetch_current_round_progress: 現在のラウンド進捗取得
    fetch_team_progress_list: 全チーム進捗一覧取得
    fetch_round_timeline: ラウンドタイムライン取得
    fetch_all_teams_score_history: 全チームスコア推移取得
    fetch_team_final_submission: チーム最終サブミッション取得

References:
    - Query specs: specs/014-ui/research.md (Section 2: データベースクエリ仕様)
    - Database schema: specs/008-leader/contracts/database-schema.sql
    - Existing pattern: build/lib/mixseek_ui/services/leaderboard_service.py
"""

import pandas as pd

from mixseek.ui.models.round_models import RoundProgress, TeamSubmission
from mixseek.ui.utils.db_utils import get_db_connection


def fetch_current_round_progress(execution_id: str) -> RoundProgress | None:
    """現在のラウンド進捗を取得（research.md クエリ1）.

    round_statusテーブルから最新のラウンド番号を取得。
    実行ページ上部の"ラウンド X/Y"表示に使用。

    Args:
        execution_id: 実行識別子(UUID)

    Returns:
        RoundProgress | None: 現在のラウンド進捗、またはNone（データ不在時）

    Example:
        >>> progress = fetch_current_round_progress("b2d88c86-6b29-4b08-bba1-c9ce5cc9a504")
        >>> if progress:
        ...     print(f"ラウンド {progress.round_number}")
    """
    conn = get_db_connection()
    if conn is None:
        return None

    try:
        result = conn.execute(
            """
            SELECT team_id, team_name, round_number
            FROM round_status
            WHERE execution_id = ?
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            [execution_id],
        ).fetchone()

        if result is None:
            return None

        return RoundProgress.from_db_row(result)
    except Exception:
        # クエリ実行エラー（テーブル不在、スキーマ不一致等）は無視してNone返却
        # UIはデータ不在として扱い、エラー終了しない
        return None
    finally:
        conn.close()


def fetch_team_progress_list(execution_id: str) -> list[RoundProgress]:
    """全チーム進捗一覧を取得（research.md クエリ2）.

    round_statusテーブルから各チームの現在ラウンド、開始/終了時刻を取得。
    実行ページの進捗確認領域に表示。

    Args:
        execution_id: 実行識別子(UUID)

    Returns:
        list[RoundProgress]: チーム進捗一覧（空リスト可）

    Example:
        >>> progress_list = fetch_team_progress_list("b2d88c86-6b29-4b08-bba1-c9ce5cc9a504")
        >>> for progress in progress_list:
        ...     print(f"{progress.team_name}: ラウンド {progress.round_number}")
    """
    conn = get_db_connection()
    if conn is None:
        return []

    try:
        result = conn.execute(
            """
            SELECT team_id, team_name, round_number, round_started_at, round_ended_at
            FROM round_status
            WHERE execution_id = ?
            ORDER BY team_name, round_number
            """,
            [execution_id],
        ).fetchall()

        return [RoundProgress.from_db_row(row) for row in result]
    except Exception:
        # クエリ実行エラー時は空リスト返却（エラー終了しない）
        return []
    finally:
        conn.close()


def fetch_round_timeline(execution_id: str, team_id: str) -> list[RoundProgress]:
    """ラウンドタイムラインを取得（research.md クエリ3）.

    round_statusテーブルから特定チームの各ラウンドの開始/終了時刻を取得。
    結果ページのタイムライン表示に使用。

    Args:
        execution_id: 実行識別子(UUID)
        team_id: チーム識別子

    Returns:
        list[RoundProgress]: ラウンドタイムライン（空リスト可）

    Example:
        >>> timeline = fetch_round_timeline("b2d88c86-...", "team-a")
        >>> for round in timeline:
        ...     print(f"Round {round.round_number}: {round.round_started_at} → {round.round_ended_at}")
    """
    conn = get_db_connection()
    if conn is None:
        return []

    try:
        result = conn.execute(
            """
            SELECT round_number, round_started_at, round_ended_at
            FROM round_status
            WHERE execution_id = ? AND team_id = ?
            ORDER BY round_number
            """,
            [execution_id, team_id],
        ).fetchall()

        # タイムライン用の短い形式（3フィールド）でRoundProgressを生成
        # from_db_rowが自動的にteam_id/team_nameをNoneに設定
        return [RoundProgress.from_db_row(row) for row in result]
    except Exception:
        # クエリ実行エラー時は空リスト返却（エラー終了しない）
        return []
    finally:
        conn.close()


def fetch_all_teams_score_history(execution_id: str) -> pd.DataFrame:
    """全チームスコア推移を取得（research.md クエリ4）.

    leader_boardテーブルから全チームの各ラウンドスコアを取得。
    結果ページの折れ線グラフ描画に使用。

    Args:
        execution_id: 実行識別子(UUID)

    Returns:
        pd.DataFrame: スコア推移データ
            カラム: team_id, team_name, round_number, score
            空DataFrame（データ不在時）

    Example:
        >>> df = fetch_all_teams_score_history("b2d88c86-...")
        >>> import plotly.express as px
        >>> fig = px.line(df, x="round_number", y="score", color="team_name")
    """
    conn = get_db_connection()
    if conn is None:
        return pd.DataFrame(columns=["team_id", "team_name", "round_number", "score"])

    try:
        # NOTE: 実際のスキーマではevaluation_scoreではなくscoreカラムを使用
        # （research.md Section 2参照）
        result = conn.execute(
            """
            SELECT team_id, team_name, round_number, score
            FROM leader_board
            WHERE execution_id = ?
            ORDER BY team_id, round_number
            """,
            [execution_id],
        ).fetchdf()

        return result
    except Exception:
        # クエリ実行エラー時は空DataFrame返却（エラー終了しない）
        return pd.DataFrame(columns=["team_id", "team_name", "round_number", "score"])
    finally:
        conn.close()


def fetch_team_final_submission(execution_id: str, team_id: str) -> TeamSubmission | None:
    """チーム最終サブミッションを取得（research.md クエリ5）.

    leader_boardテーブルから特定チームの最終ラウンドサブミッションを取得。
    実行ページのチームタブ内に表示。

    final_submission = TRUEのレコードを優先的に取得し、存在しない場合は
    最高スコア（同点の場合は最新ラウンド）のレコードをフォールバックとして返す。

    Args:
        execution_id: 実行識別子(UUID)
        team_id: チーム識別子

    Returns:
        TeamSubmission | None: 最終サブミッション、またはNone（データ不在時）

    Example:
        >>> submission = fetch_team_final_submission("b2d88c86-...", "team-a")
        >>> if submission:
        ...     print(f"スコア: {submission.score}")
        ...     print(submission.submission_content)
    """
    conn = get_db_connection()
    if conn is None:
        return None

    try:
        # 1. まずfinal_submission = TRUEのレコードを検索
        result = conn.execute(
            """
            SELECT team_id, team_name, round_number, submission_content,
                   score, score_details, created_at, final_submission
            FROM leader_board
            WHERE execution_id = ? AND team_id = ? AND final_submission = TRUE
            ORDER BY round_number DESC
            LIMIT 1
            """,
            [execution_id, team_id],
        ).fetchone()

        # 2. 見つからない場合は最高スコアのレコードを取得
        if result is None:
            result = conn.execute(
                """
                SELECT team_id, team_name, round_number, submission_content,
                       score, score_details, created_at, final_submission
                FROM leader_board
                WHERE execution_id = ? AND team_id = ?
                ORDER BY score DESC, round_number DESC
                LIMIT 1
                """,
                [execution_id, team_id],
            ).fetchone()

        if result is None:
            return None

        return TeamSubmission.from_db_row(result)
    except Exception:
        # クエリ実行エラー時はNone返却（エラー終了しない）
        return None
    finally:
        conn.close()
