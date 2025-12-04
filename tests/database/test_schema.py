"""DuckDBスキーマのテスト

Article 3: Test-First Imperative準拠

Tests:
    - RoundHistoryテーブル作成
    - LeaderBoardテーブル作成
    - UNIQUE制約、インデックス確認
    - スキーマ更新（aggregated_submissions → member_submissions_record）
"""

import tempfile
from collections.abc import Generator
from pathlib import Path

import duckdb
import pytest


class TestDuckDBSchema:
    """DuckDBスキーマテスト（contracts/database-schema.sql準拠）"""

    @pytest.fixture
    def test_db_path(self) -> Generator[Path]:
        """テスト用DuckDBファイルパス"""
        # TemporaryDirectoryを使用してパスのみ生成（ファイルは作成しない）
        tmpdir = tempfile.mkdtemp()
        db_path = Path(tmpdir) / "test.db"
        yield db_path
        # クリーンアップ
        if db_path.exists():
            db_path.unlink()
        Path(tmpdir).rmdir()

    @pytest.fixture
    def conn(self, test_db_path: Path) -> Generator[duckdb.DuckDBPyConnection]:
        """DuckDB接続"""
        connection = duckdb.connect(str(test_db_path))
        yield connection
        connection.close()

    def test_round_history_table_creation(self, conn: duckdb.DuckDBPyConnection) -> None:
        """RoundHistoryテーブル作成"""
        # Arrange & Act: スキーマ作成（AggregationStore._init_tables_sync()相当）
        conn.execute("CREATE SEQUENCE IF NOT EXISTS round_history_id_seq")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS round_history (
                id INTEGER PRIMARY KEY DEFAULT nextval('round_history_id_seq'),
                team_id TEXT NOT NULL,
                team_name TEXT NOT NULL,
                round_number INTEGER NOT NULL CHECK (round_number >= 1),
                message_history JSON,
                member_submissions_record JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(team_id, round_number)
            )
        """)

        # Assert: テーブル存在確認
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='round_history'").fetchall()
        assert len(tables) == 1

        # カラム確認
        columns = conn.execute("PRAGMA table_info(round_history)").fetchall()
        column_names = [col[1] for col in columns]

        assert "id" in column_names
        assert "team_id" in column_names
        assert "member_submissions_record" in column_names  # 新カラム名
        assert "aggregated_submissions" not in column_names  # 旧カラム名は存在しない

    def test_round_history_unique_constraint(self, conn: duckdb.DuckDBPyConnection) -> None:
        """RoundHistory UNIQUE制約（team_id + round_number、FR-008）"""
        # Arrange: テーブル作成
        conn.execute("CREATE SEQUENCE IF NOT EXISTS round_history_id_seq")
        conn.execute("""
            CREATE TABLE round_history (
                id INTEGER PRIMARY KEY DEFAULT nextval('round_history_id_seq'),
                team_id TEXT NOT NULL,
                team_name TEXT NOT NULL,
                round_number INTEGER NOT NULL,
                message_history JSON,
                member_submissions_record JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(team_id, round_number)
            )
        """)

        # Act: 1回目の挿入成功
        conn.execute(
            "INSERT INTO round_history (team_id, team_name, round_number) VALUES (?, ?, ?)",
            ["team-001", "Team A", 1],
        )

        # Assert: 同じteam_id + round_numberで挿入失敗
        with pytest.raises(duckdb.ConstraintException) as exc_info:
            conn.execute(
                "INSERT INTO round_history (team_id, team_name, round_number) VALUES (?, ?, ?)",
                ["team-001", "Team A", 1],
            )

        assert "Constraint" in str(exc_info.value) or "UNIQUE" in str(exc_info.value)

    def test_round_history_index_creation(self, conn: duckdb.DuckDBPyConnection) -> None:
        """RoundHistoryインデックス作成"""
        # Arrange & Act
        conn.execute("CREATE SEQUENCE IF NOT EXISTS round_history_id_seq")
        conn.execute("""
            CREATE TABLE round_history (
                id INTEGER PRIMARY KEY DEFAULT nextval('round_history_id_seq'),
                team_id TEXT NOT NULL,
                round_number INTEGER NOT NULL,
                message_history JSON,
                member_submissions_record JSON,
                UNIQUE(team_id, round_number)
            )
        """)

        conn.execute("CREATE INDEX idx_round_history_team ON round_history(team_id, round_number)")

        # Assert: インデックス存在確認
        indexes = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_round_history_team'"
        ).fetchall()
        assert len(indexes) == 1

    def test_leader_board_table_creation(self, conn: duckdb.DuckDBPyConnection) -> None:
        """LeaderBoardテーブル作成"""
        # Arrange & Act
        conn.execute("CREATE SEQUENCE IF NOT EXISTS leader_board_id_seq")

        conn.execute("""
            CREATE TABLE leader_board (
                id INTEGER PRIMARY KEY DEFAULT nextval('leader_board_id_seq'),
                team_id TEXT NOT NULL,
                team_name TEXT NOT NULL,
                round_number INTEGER NOT NULL,
                evaluation_score DOUBLE NOT NULL CHECK (evaluation_score >= 0.0 AND evaluation_score <= 1.0),
                evaluation_feedback TEXT,
                submission_content TEXT NOT NULL,
                submission_format TEXT DEFAULT 'structured_json',
                usage_info JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Assert
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='leader_board'").fetchall()
        assert len(tables) == 1

        # submission_format デフォルト値確認
        conn.execute(
            "INSERT INTO leader_board (team_id, team_name, round_number, "
            "evaluation_score, submission_content) VALUES (?, ?, ?, ?, ?)",
            ["team-001", "Team A", 1, 0.85, "test"],
        )
        row = conn.execute("SELECT submission_format FROM leader_board").fetchone()
        assert row is not None
        assert row[0] == "structured_json"  # デフォルト値

    def test_leader_board_score_check_constraint(self, conn: duckdb.DuckDBPyConnection) -> None:
        """LeaderBoard evaluation_score CHECK制約（0.0-1.0）"""
        # Arrange
        conn.execute("CREATE SEQUENCE IF NOT EXISTS leader_board_id_seq")
        conn.execute("""
            CREATE TABLE leader_board (
                id INTEGER PRIMARY KEY DEFAULT nextval('leader_board_id_seq'),
                team_id TEXT NOT NULL,
                evaluation_score DOUBLE NOT NULL CHECK (evaluation_score >= 0.0 AND evaluation_score <= 1.0),
                submission_content TEXT NOT NULL
            )
        """)

        # Act: 有効な範囲（0.0-1.0）
        conn.execute(
            "INSERT INTO leader_board (team_id, evaluation_score, submission_content) VALUES (?, ?, ?)",
            ["team-001", 0.85, "test"],
        )

        # Assert: 範囲外はエラー
        with pytest.raises(duckdb.ConstraintException):
            conn.execute(
                "INSERT INTO leader_board (team_id, evaluation_score, submission_content) VALUES (?, ?, ?)",
                ["team-002", 1.5, "test"],  # 1.0超過
            )

        with pytest.raises(duckdb.ConstraintException):
            conn.execute(
                "INSERT INTO leader_board (team_id, evaluation_score, submission_content) VALUES (?, ?, ?)",
                ["team-003", -0.1, "test"],  # 負の値
            )

    def test_leader_board_ranking_index(self, conn: duckdb.DuckDBPyConnection) -> None:
        """LeaderBoardランキングインデックス（FR-011）"""
        # Arrange & Act
        conn.execute("CREATE SEQUENCE IF NOT EXISTS leader_board_id_seq")
        conn.execute("""
            CREATE TABLE leader_board (
                id INTEGER PRIMARY KEY DEFAULT nextval('leader_board_id_seq'),
                team_id TEXT NOT NULL,
                evaluation_score DOUBLE NOT NULL,
                submission_content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # スコア降順、作成日時早い順のインデックス
        conn.execute("CREATE INDEX idx_leader_board_score ON leader_board(evaluation_score DESC, created_at ASC)")

        # Assert
        indexes = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_leader_board_score'"
        ).fetchall()
        assert len(indexes) == 1
