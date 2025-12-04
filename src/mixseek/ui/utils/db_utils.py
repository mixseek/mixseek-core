"""DuckDB接続ヘルパー for Mixseek UI.

このモジュールはmixseek.dbへの接続とワークスペースパス取得を提供します。
Article 9 (Data Accuracy Mandate) 準拠: 環境変数の明示的読み取り、
デフォルト値の暗黙的使用禁止。

Functions:
    get_workspace_path: 環境変数MIXSEEK_WORKSPACEからパス取得
    get_db_connection: mixseek.dbへの読み取り専用接続取得

References:
    - Existing pattern: build/lib/mixseek_ui/utils/workspace.py
    - Existing pattern: build/lib/mixseek_ui/utils/duckdb_conn.py
    - Constitution: .specify/memory/constitution.md (Article 9)
"""

import os
from pathlib import Path

import duckdb


def get_workspace_path() -> Path:
    """環境変数MIXSEEK_WORKSPACEからワークスペースパスを取得.

    Article 9準拠: 環境変数が未設定の場合は例外を投げ、
    デフォルト値を使用しない。

    Returns:
        Path: ワークスペースディレクトリの絶対パス

    Raises:
        ValueError: 環境変数MIXSEEK_WORKSPACEが未設定の場合

    Example:
        >>> os.environ["MIXSEEK_WORKSPACE"] = "/home/user/workspace"
        >>> path = get_workspace_path()
        >>> path
        Path('/home/user/workspace')
    """
    workspace = os.getenv("MIXSEEK_WORKSPACE")
    if not workspace:
        raise ValueError(
            "MIXSEEK_WORKSPACE environment variable is not set.\n"
            "Please set it: export MIXSEEK_WORKSPACE=/path/to/workspace"
        )
    return Path(workspace).resolve()


def get_db_connection() -> duckdb.DuckDBPyConnection | None:
    """mixseek.dbへの読み取り専用接続を取得.

    DBファイルが存在しない場合はNoneを返し、エラーを投げない。
    これによりUI起動時にDBファイル不在でもエラー終了しない（空状態として扱う）。

    Returns:
        duckdb.DuckDBPyConnection | None: 読み取り専用接続、またはNone（DB不在時）

    Example:
        >>> conn = get_db_connection()
        >>> if conn:
        ...     result = conn.execute("SELECT * FROM round_status").fetchall()
        ...     conn.close()

    Note:
        接続はNoneでない場合、使用後に必ずclose()すること。
    """
    try:
        db_path = get_workspace_path() / "mixseek.db"
        if not db_path.exists():
            # DBファイル不在時はNone返却（エラーとしない）
            return None

        return duckdb.connect(str(db_path), read_only=True)
    except ValueError as e:
        # 環境変数未設定時は例外を再発生（Article 9準拠）
        raise e
    except Exception:
        # DuckDB接続エラー（ロック等）はNone返却
        # Orchestrator実行中にUIがアクセスするとロックエラーが発生するため
        return None
