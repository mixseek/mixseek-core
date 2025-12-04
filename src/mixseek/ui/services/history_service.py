"""History service for fetching execution history from DuckDB."""

from mixseek.ui.models.execution import Execution, ExecutionStatus
from mixseek.ui.models.history import HistoryEntry
from mixseek.ui.utils.duckdb_conn import get_read_connection


def fetch_history(
    page_number: int = 1,
    page_size: int = 50,
    sort_order: str = "desc",
    status_filter: ExecutionStatus | None = None,
) -> tuple[list[HistoryEntry], int]:
    """実行履歴を取得（ページネーション対応）.

    Args:
        page_number: ページ番号（1始まり）
        page_size: 1ページあたりの件数
        sort_order: ソート順（"asc" or "desc"）
        status_filter: ステータスによる絞り込み

    Returns:
        tuple[list[HistoryEntry], int]: (履歴エントリリスト, 総件数)
    """
    try:
        conn = get_read_connection()
        if conn is None:
            # 接続失敗時（Orchestrator実行中など）は空リスト
            return [], 0

        # WHERE句構築
        where_clause = ""
        params = []
        if status_filter:
            where_clause = "WHERE status = ?"
            params.append(status_filter.value)

        # 総件数取得
        total_count_query = f"SELECT COUNT(*) FROM execution_summary {where_clause}"
        count_result = conn.execute(total_count_query, params).fetchone()
        total_count = count_result[0] if count_result else 0

        # データ取得
        offset = (page_number - 1) * page_size
        order = "ASC" if sort_order == "asc" else "DESC"

        query = f"""
            SELECT
                execution_id,
                user_prompt,
                status,
                best_team_id,
                best_score,
                total_execution_time_seconds,
                created_at,
                completed_at
            FROM execution_summary
            {where_clause}
            ORDER BY created_at {order}
            LIMIT ? OFFSET ?
        """

        result = conn.execute(query, params + [page_size, offset]).fetchall()
        conn.close()

        executions = [
            Execution(
                execution_id=row[0],
                prompt=row[1],
                status=ExecutionStatus(row[2]),
                best_team_id=row[3],
                best_score=row[4],
                duration_seconds=row[5],
                created_at=row[6],
                completed_at=row[7],
            )
            for row in result
        ]

        entries = [HistoryEntry.from_execution(exec) for exec in executions]

        return entries, total_count

    except FileNotFoundError:
        return [], 0


def fetch_execution_detail(execution_id: str) -> Execution | None:
    """実行詳細を取得.

    Args:
        execution_id: 実行ID

    Returns:
        Execution | None: 実行レコード（存在しない場合はNone）
    """
    try:
        conn = get_read_connection()
        if conn is None:
            # 接続失敗時（Orchestrator実行中など）はNone
            return None

        result = conn.execute(
            """
            SELECT
                execution_id,
                user_prompt,
                status,
                best_team_id,
                best_score,
                total_execution_time_seconds,
                created_at,
                completed_at
            FROM execution_summary
            WHERE execution_id = ?
        """,
            [execution_id],
        ).fetchone()

        conn.close()

        if not result:
            return None

        return Execution(
            execution_id=result[0],
            prompt=result[1],
            status=ExecutionStatus(result[2]),
            best_team_id=result[3],
            best_score=result[4],
            duration_seconds=result[5],
            created_at=result[6],
            completed_at=result[7],
        )

    except FileNotFoundError:
        return None
