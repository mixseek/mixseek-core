"""DuckDB connection helper for Mixseek UI."""

import logging

import duckdb

from mixseek.ui.utils.workspace import get_db_path

logger = logging.getLogger(__name__)


def get_read_connection() -> duckdb.DuckDBPyConnection | None:
    """mixseek.dbへの読み取り専用接続を取得.

    Returns:
        duckdb.DuckDBPyConnection | None: 読み取り専用接続、または接続失敗時はNone

    Raises:
        FileNotFoundError: DBファイルが存在しない場合

    Note:
        - 接続は使用後に必ずclose()すること
        - DuckDB接続エラー（Orchestrator実行中など）はNoneを返す
    """
    db_path = get_db_path()
    if not db_path.exists():
        raise FileNotFoundError(
            f"Database file not found: {db_path}. Please run a task execution first to create the database."
        )

    try:
        return duckdb.connect(str(db_path), read_only=True)
    except Exception as e:
        # 接続エラー時（Orchestrator実行中など）はNoneを返す
        logger.debug(f"Failed to connect to DuckDB (likely in use by Orchestrator): {e}")
        return None
