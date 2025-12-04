"""Tests for DuckDB connection helper."""

from pathlib import Path

import duckdb
import pytest

from mixseek.ui.utils.duckdb_conn import get_read_connection


def test_get_read_connection_raises_when_db_not_found(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """DBファイルが存在しない場合にFileNotFoundErrorを発生させること."""
    monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
    with pytest.raises(FileNotFoundError, match="Database file not found"):
        get_read_connection()


def test_get_read_connection_returns_connection(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """DBファイルが存在する場合に読み取り専用接続を返すこと."""
    monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
    db_path = tmp_path / "mixseek.db"

    # テスト用DBを作成
    conn = duckdb.connect(str(db_path))
    conn.execute("CREATE TABLE test (id INTEGER)")
    conn.close()

    # 読み取り専用接続を取得
    read_conn = get_read_connection()
    assert read_conn is not None

    # 書き込みが禁止されていることを確認
    with pytest.raises(Exception):  # DuckDBのread-only例外
        read_conn.execute("INSERT INTO test VALUES (1)")

    read_conn.close()
