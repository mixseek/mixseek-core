"""DuckDB並列書き込み対応ストア

このモジュールはLeader AgentのMember Agent応答集約結果と
Message HistoryをDuckDBに永続化します。

MVCC並列制御により、複数チーム同時実行時もロック競合なしで動作します。

Technical Strategy:
    DuckDB Python APIは同期のみのため、asyncio.to_threadで
    スレッドプールに退避して非同期実行を実現。
    スレッドローカルコネクションにより、各チームが独立した
    コネクションを使用してMVCC並列書き込みを実現。

References:
    - Spec: specs/008-leader/spec.md (FR-006 ~ FR-016)
    - Contract: specs/008-leader/contracts/aggregation_store.md
    - Research: specs/008-leader/research.md (R5)
"""

import asyncio
import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, cast

import duckdb
import pandas as pd
from pydantic_ai import ModelMessage
from pydantic_core import to_jsonable_python

from mixseek.agents.leader.models import MemberSubmissionsRecord
from mixseek.storage import schema

# Pydantic AI Message型アダプター（遅延インポート回避）
try:
    from pydantic_ai.messages import ModelMessagesTypeAdapter
except ImportError:
    from pydantic import TypeAdapter

    ModelMessagesTypeAdapter = TypeAdapter(list[ModelMessage])


class DatabaseWriteError(Exception):
    """データベース書き込み失敗（3回リトライ後）"""


class DatabaseReadError(Exception):
    """データベース読み込み失敗"""


class AggregationStore:
    """DuckDB並列書き込み対応ストア

    DuckDB Python APIは同期のみのため、asyncio.to_threadで
    スレッドプールに退避して非同期実行を実現。
    スレッドローカルコネクションにより、各チームが独立した
    コネクションを使用してMVCC並列書き込みを実現。
    """

    def __init__(self, workspace: Path | None = None, db_path: Path | None = None) -> None:
        """初期化

        Args:
            workspace: ワークスペースディレクトリパス
                      Noneの場合はConfigurationManager経由で取得
            db_path: データベースファイルパス
                    Noneの場合は{workspace}/mixseek.dbを使用

        Raises:
            WorkspacePathNotSpecifiedError: workspace未指定かつConfigurationManagerで取得できない場合
            PermissionError: DBファイル作成権限なし
        """
        self.db_path = self._get_db_path(workspace, db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # スレッドローカル変数（各スレッドが独立したコネクション保持）
        self._local = threading.local()

        # 初期化（テーブル作成）
        self._init_tables_sync()

    def _get_db_path(self, workspace: Path | None, db_path: Path | None) -> Path:
        """データベースファイルパス取得

        Args:
            workspace: ワークスペースディレクトリパス
            db_path: 指定されたパス（Noneの場合は{workspace}/mixseek.db）

        Returns:
            データベースファイルパス

        Raises:
            WorkspacePathNotSpecifiedError: workspace未指定かつConfigurationManagerで取得できない場合
        """
        if db_path is not None:
            return db_path

        # Article 9準拠: ConfigurationManager経由でworkspaceを取得
        if workspace is None:
            from mixseek.utils.env import get_workspace_path

            workspace = get_workspace_path(cli_arg=None)

        return workspace / "mixseek.db"

    def _get_connection(self) -> duckdb.DuckDBPyConnection:
        """スレッドローカルコネクション取得

        各スレッドが独立したDuckDBコネクションを使用することで、
        MVCC並列書き込みを実現。

        Returns:
            DuckDBコネクション
        """
        if not hasattr(self._local, "conn"):
            self._local.conn = duckdb.connect(str(self.db_path))
        return cast(duckdb.DuckDBPyConnection, self._local.conn)

    @contextmanager
    def _transaction(self, conn: duckdb.DuckDBPyConnection) -> Iterator[duckdb.DuckDBPyConnection]:
        """同期トランザクション管理 (FR-015)

        Args:
            conn: DuckDBコネクション

        Yields:
            トランザクション内のコネクション

        Raises:
            Exception: トランザクション失敗時（ROLLBACK実行）
        """
        try:
            conn.execute("BEGIN TRANSACTION")
            yield conn
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise

    def _init_tables_sync(self) -> None:
        """テーブル初期化（同期版）

        round_history、leader_board、execution_summaryテーブルを作成。
        Orchestrator統合対応: execution_idカラム追加（025-mixseek-core-orchestration）
        """
        conn = self._get_connection()

        # シーケンス作成
        conn.execute("CREATE SEQUENCE IF NOT EXISTS round_history_id_seq")
        conn.execute("CREATE SEQUENCE IF NOT EXISTS leader_board_id_seq")
        conn.execute("CREATE SEQUENCE IF NOT EXISTS execution_summary_id_seq")

        # round_historyテーブル (FR-006, FR-007, Orchestrator統合)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS round_history (
                id INTEGER PRIMARY KEY DEFAULT nextval('round_history_id_seq'),
                execution_id TEXT NOT NULL,
                team_id TEXT NOT NULL,
                team_name TEXT NOT NULL,
                round_number INTEGER NOT NULL,

                -- Pydantic AI Message History（JSON型）
                message_history JSON,

                -- Member Agent応答記録（JSON型）
                member_submissions_record JSON,

                -- メタデータ
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                -- 一意性制約（Orchestrator統合対応）
                UNIQUE(execution_id, team_id, round_number)
            )
        """)

        # leader_boardテーブル (Feature 037: New schema with 'score' column 0-100)
        # Note: Old schema removed. Use initialize_schema() for Feature 037 tables.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS leader_board (
                id INTEGER PRIMARY KEY DEFAULT nextval('leader_board_id_seq'),
                execution_id VARCHAR NOT NULL,
                team_id VARCHAR NOT NULL,
                team_name VARCHAR NOT NULL,
                round_number INTEGER NOT NULL,

                submission_content TEXT NOT NULL,
                submission_format VARCHAR NOT NULL DEFAULT 'md',

                score FLOAT NOT NULL CHECK (score >= 0.0 AND score <= 100.0),
                score_details JSON NOT NULL,

                final_submission BOOLEAN NOT NULL DEFAULT FALSE,
                exit_reason VARCHAR NULL,

                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

                UNIQUE (execution_id, team_id, round_number)
            )
        """)

        # execution_summaryテーブル (Orchestrator、025-mixseek-core-orchestration)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS execution_summary (
                execution_id TEXT PRIMARY KEY,
                user_prompt TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('completed', 'partial_failure', 'failed')),
                team_results JSON NOT NULL,
                total_teams INTEGER NOT NULL,
                best_team_id TEXT,
                best_score DOUBLE,
                total_execution_time_seconds DOUBLE NOT NULL,
                completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # インデックス作成（Feature 037: score column only）
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_leader_board_score
            ON leader_board(score DESC, created_at ASC)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_round_history_execution
            ON round_history(execution_id, team_id, round_number)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_leader_board_execution
            ON leader_board(execution_id)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_execution_summary_status
            ON execution_summary(status, completed_at DESC)
        """)

        # Feature 037: Round Controller schema (round_status table)
        # Execute all schema DDL statements to ensure round_status and related tables exist
        for ddl in schema.ALL_SCHEMA_DDL:
            conn.execute(ddl)

    def _save_sync(
        self, execution_id: str, aggregated: MemberSubmissionsRecord, message_history: list[ModelMessage]
    ) -> None:
        """同期保存処理（スレッドプールで実行）

        Args:
            execution_id: 実行識別子(UUID)
            aggregated: 集約されたMember Agent応答
            message_history: Pydantic AI Message History

        Raises:
            Exception: データベース書き込み失敗
        """
        conn = self._get_connection()

        # Pydantic AI → JSON変換
        messages_dict = to_jsonable_python(message_history)
        aggregated_dict = aggregated.model_dump(mode="json")

        with self._transaction(conn):
            conn.execute(
                """
                INSERT INTO round_history
                (execution_id, team_id, team_name, round_number, message_history, member_submissions_record)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT (execution_id, team_id, round_number) DO UPDATE SET
                    message_history = EXCLUDED.message_history,
                    member_submissions_record = EXCLUDED.member_submissions_record
            """,
                [
                    execution_id,
                    aggregated.team_id,
                    aggregated.team_name,
                    aggregated.round_number,
                    json.dumps(messages_dict, ensure_ascii=False),
                    json.dumps(aggregated_dict, ensure_ascii=False),
                ],
            )

    async def save_aggregation(
        self, execution_id: str, aggregated: MemberSubmissionsRecord, message_history: list[ModelMessage]
    ) -> None:
        """集約結果とMessage Historyを保存 (FR-006, FR-007)

        複数Leader Agentから同時呼び出しされても安全（ロックフリー）。
        DuckDB同期APIをasyncio.to_threadでスレッドプールに退避し、
        真の非同期並列実行を実現。

        Args:
            execution_id: 実行識別子(UUID)
            aggregated: 集約されたMember Agent応答
            message_history: Pydantic AI Message History

        Raises:
            DatabaseWriteError: 書き込み失敗（3回リトライ後）
        """
        # エクスポネンシャルバックオフリトライ (FR-019)
        delays = [1, 2, 4]

        for attempt, delay in enumerate(delays, 1):
            try:
                await asyncio.to_thread(self._save_sync, execution_id, aggregated, message_history)
                return
            except Exception as e:
                if attempt == len(delays):
                    raise DatabaseWriteError(f"Failed to save after {attempt} retries: {e}") from e
                await asyncio.sleep(delay)

    def _load_round_history_sync(
        self, execution_id: str, team_id: str, round_number: int
    ) -> tuple[MemberSubmissionsRecord | None, list[ModelMessage]]:
        """ラウンド履歴を読み込み（同期版）

        Args:
            execution_id: 実行識別子(UUID)
            team_id: チームID
            round_number: ラウンド番号

        Returns:
            (集約結果, Message History)のタプル
        """
        conn = self._get_connection()

        result = conn.execute(
            """
            SELECT member_submissions_record, message_history
            FROM round_history
            WHERE execution_id = ? AND team_id = ? AND round_number = ?
        """,
            [execution_id, team_id, round_number],
        ).fetchone()

        if not result:
            return None, []

        # JSON → Pydantic型に復元 (FR-012)
        aggregated = None
        if result[0]:
            aggregated = MemberSubmissionsRecord.model_validate_json(result[0])

        messages: list[ModelMessage] = []
        if result[1]:
            messages = ModelMessagesTypeAdapter.validate_json(result[1])

        return aggregated, messages

    async def load_round_history(
        self, execution_id: str, team_id: str, round_number: int
    ) -> tuple[MemberSubmissionsRecord | None, list[ModelMessage]]:
        """ラウンド履歴を読み込み (FR-012)

        Args:
            execution_id: 実行識別子(UUID)
            team_id: チームID
            round_number: ラウンド番号

        Returns:
            (集約結果, Message History)のタプル
            レコード未存在時は(None, [])

        Raises:
            DatabaseReadError: 読み込み失敗
        """
        try:
            return await asyncio.to_thread(self._load_round_history_sync, execution_id, team_id, round_number)
        except Exception as e:
            raise DatabaseReadError(f"Failed to load round history: {e}") from e

    def _get_leader_board_sync(self, limit: int) -> pd.DataFrame:
        """Leader Board取得（同期版）

        Args:
            limit: 取得件数

        Returns:
            Pandas DataFrame
        """
        conn = self._get_connection()

        # FR-011: スコア降順、同スコアは作成日時早い順
        # Feature 037: Use 'score' column instead of 'evaluation_score'
        return conn.execute(
            """
            SELECT
                team_name,
                round_number,
                score,
                score_details,
                created_at
            FROM leader_board
            ORDER BY score DESC, created_at ASC
            LIMIT ?
        """,
            [limit],
        ).df()

    async def get_leader_board(self, limit: int = 10) -> pd.DataFrame:
        """Leader Board取得 (FR-011)

        スコア降順、同スコアは作成日時早い順でソート。

        Args:
            limit: 取得件数

        Returns:
            Pandas DataFrame

        Raises:
            DatabaseReadError: 読み込み失敗
        """
        try:
            return await asyncio.to_thread(self._get_leader_board_sync, limit)
        except Exception as e:
            raise DatabaseReadError(f"Failed to get leader board: {e}") from e

    def _get_team_statistics_sync(self, team_id: str) -> dict[str, float | int]:
        """チーム統計取得（同期版）

        Args:
            team_id: チームID

        Returns:
            統計情報辞書
        """
        conn = self._get_connection()

        # JSON内部クエリで統計集計（FR-013）
        # Feature 037: Use 'score' column (0-100 scale) instead of 'evaluation_score'
        result = conn.execute(
            """
            SELECT
                COUNT(*) as total_rounds,
                AVG(score) as avg_score,
                MAX(score) as best_score,
                SUM(CAST(json_extract(score_details, '$.input_tokens') AS INTEGER)) as total_input_tokens,
                SUM(CAST(json_extract(score_details, '$.output_tokens') AS INTEGER)) as total_output_tokens
            FROM leader_board
            WHERE team_id = ?
        """,
            [team_id],
        ).fetchone()

        if not result:
            return {
                "total_rounds": 0,
                "avg_score": 0.0,
                "best_score": 0.0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
            }

        return {
            "total_rounds": int(result[0]) if result[0] else 0,
            "avg_score": float(result[1]) if result[1] else 0.0,
            "best_score": float(result[2]) if result[2] else 0.0,
            "total_input_tokens": int(result[3]) if result[3] else 0,
            "total_output_tokens": int(result[4]) if result[4] else 0,
        }

    async def get_team_statistics(self, team_id: str) -> dict[str, float | int]:
        """チーム統計取得 (FR-013)

        JSON内部クエリで総ラウンド数、平均スコア、総トークン使用量を集計。

        Args:
            team_id: チームID

        Returns:
            統計情報辞書
            - total_rounds: 総ラウンド数
            - avg_score: 平均スコア
            - best_score: 最高スコア
            - total_input_tokens: 総入力トークン数
            - total_output_tokens: 総出力トークン数

        Raises:
            DatabaseReadError: 読み込み失敗
        """
        try:
            return await asyncio.to_thread(self._get_team_statistics_sync, team_id)
        except Exception as e:
            raise DatabaseReadError(f"Failed to get team statistics: {e}") from e

    def _save_execution_summary_sync(
        self,
        execution_id: str,
        user_prompt: str,
        status: str,
        team_results: list[dict[str, Any]],
        total_teams: int,
        best_team_id: str | None,
        best_score: float | None,
        total_execution_time_seconds: float,
    ) -> None:
        """ExecutionSummary保存（同期版）

        Args:
            execution_id: 実行識別子(UUID)
            user_prompt: ユーザプロンプト
            status: 実行ステータス（completed/partial_failure/failed）
            team_results: チーム結果リスト（JSON配列）
            total_teams: チーム総数
            best_team_id: 最高スコアチームID
            best_score: 最高評価スコア
            total_execution_time_seconds: 総実行時間（秒）

        Raises:
            ValueError: statusが不正な値
        """
        # statusバリデーション
        valid_statuses = {"completed", "partial_failure", "failed"}
        if status not in valid_statuses:
            raise ValueError(f"status must be one of {valid_statuses}, got {status}")

        conn = self._get_connection()

        with self._transaction(conn):
            conn.execute(
                """
                INSERT INTO execution_summary
                (execution_id, user_prompt, status, team_results, total_teams,
                 best_team_id, best_score, total_execution_time_seconds)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                [
                    execution_id,
                    user_prompt,
                    status,
                    json.dumps(team_results, ensure_ascii=False),
                    total_teams,
                    best_team_id,
                    best_score,
                    total_execution_time_seconds,
                ],
            )

    async def save_execution_summary(
        self,
        execution_id: str,
        user_prompt: str,
        status: str,
        team_results: list[dict[str, Any]],
        total_teams: int,
        best_team_id: str | None,
        best_score: float | None,
        total_execution_time_seconds: float,
    ) -> None:
        """ExecutionSummary保存（非同期版、Orchestrator統合）

        複数チームの実行結果を集約した最終サマリーをDuckDBに保存。

        Args:
            execution_id: 実行識別子(UUID)
            user_prompt: ユーザプロンプト
            status: 実行ステータス（completed/partial_failure/failed）
            team_results: チーム結果リスト（JSON配列）
            total_teams: チーム総数
            best_team_id: 最高スコアチームID
            best_score: 最高評価スコア
            total_execution_time_seconds: 総実行時間（秒）

        Raises:
            DatabaseWriteError: 書き込み失敗（3回リトライ後）
        """
        # エクスポネンシャルバックオフリトライ
        delays = [1, 2, 4]

        for attempt, delay in enumerate(delays, 1):
            try:
                await asyncio.to_thread(
                    self._save_execution_summary_sync,
                    execution_id,
                    user_prompt,
                    status,
                    team_results,
                    total_teams,
                    best_team_id,
                    best_score,
                    total_execution_time_seconds,
                )
                return
            except ValueError:
                # ValidationErrorは即座に再発生（リトライしない）
                raise
            except Exception as e:
                if attempt == len(delays):
                    raise DatabaseWriteError(f"Failed to save execution summary after {attempt} retries: {e}") from e
                await asyncio.sleep(delay)

    def initialize_schema(self) -> None:
        """Initialize Round Controller DuckDB schema (Feature 037)

        Creates round_status and leader_board tables for Round Controller feature.
        This method is idempotent and can be called multiple times.

        Raises:
            Exception: Database initialization failed
        """
        conn = self._get_connection()

        # Execute all schema DDL statements
        for ddl in schema.ALL_SCHEMA_DDL:
            conn.execute(ddl)

    def _save_round_status_sync(
        self,
        execution_id: str,
        team_id: str,
        team_name: str,
        round_number: int,
        should_continue: bool | None,
        reasoning: str | None,
        confidence_score: float | None,
        round_started_at: str,
        round_ended_at: str,
    ) -> None:
        """Save round status to DuckDB (synchronous version)

        Args:
            execution_id: Execution identifier (UUID)
            team_id: Team identifier
            team_name: Team name
            round_number: Round number
            should_continue: Whether to continue to next round
            reasoning: Judgment reasoning
            confidence_score: Confidence score (0.0-1.0)
            round_started_at: Round start timestamp (ISO format)
            round_ended_at: Round end timestamp (ISO format)

        Raises:
            ValueError: Invalid parameters
        """
        # Validate confidence_score if provided
        if confidence_score is not None and not (0.0 <= confidence_score <= 1.0):
            raise ValueError(f"confidence_score must be between 0.0 and 1.0, got {confidence_score}")

        conn = self._get_connection()

        # Get current timestamp for updated_at
        from datetime import UTC, datetime

        updated_at = datetime.now(UTC).isoformat()

        with self._transaction(conn):
            conn.execute(
                """
                INSERT INTO round_status
                (execution_id, team_id, team_name, round_number, should_continue,
                 reasoning, confidence_score, round_started_at, round_ended_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (execution_id, team_id, round_number) DO UPDATE SET
                    should_continue = EXCLUDED.should_continue,
                    reasoning = EXCLUDED.reasoning,
                    confidence_score = EXCLUDED.confidence_score,
                    round_ended_at = EXCLUDED.round_ended_at,
                    updated_at = EXCLUDED.updated_at
            """,
                [
                    execution_id,
                    team_id,
                    team_name,
                    round_number,
                    should_continue,
                    reasoning,
                    confidence_score,
                    round_started_at,
                    round_ended_at,
                    updated_at,
                ],
            )

    async def save_round_status(
        self,
        execution_id: str,
        team_id: str,
        team_name: str,
        round_number: int,
        should_continue: bool | None,
        reasoning: str | None,
        confidence_score: float | None,
        round_started_at: str,
        round_ended_at: str,
    ) -> None:
        """Save round status to DuckDB (asynchronous version)

        Args:
            execution_id: Execution identifier (UUID)
            team_id: Team identifier
            team_name: Team name
            round_number: Round number
            should_continue: Whether to continue to next round
            reasoning: Judgment reasoning
            confidence_score: Confidence score (0.0-1.0)
            round_started_at: Round start timestamp (ISO format)
            round_ended_at: Round end timestamp (ISO format)

        Raises:
            DatabaseWriteError: Write failed after 3 retries
        """
        delays = [1, 2, 4]

        for attempt, delay in enumerate(delays, 1):
            try:
                await asyncio.to_thread(
                    self._save_round_status_sync,
                    execution_id,
                    team_id,
                    team_name,
                    round_number,
                    should_continue,
                    reasoning,
                    confidence_score,
                    round_started_at,
                    round_ended_at,
                )
                return
            except ValueError:
                # ValidationError は即座に再発生
                raise
            except Exception as e:
                if attempt == len(delays):
                    raise DatabaseWriteError(f"Failed to save round status after {attempt} retries: {e}") from e
                await asyncio.sleep(delay)

    def _save_to_leader_board_sync(
        self,
        execution_id: str,
        team_id: str,
        team_name: str,
        round_number: int,
        submission_content: str,
        submission_format: str,
        score: float,
        score_details: dict[str, Any],
        final_submission: bool,
        exit_reason: str | None,
    ) -> None:
        """Save to leader_board table (synchronous version)

        This is the new leader_board table with 0-100 score scale.

        Args:
            execution_id: Execution identifier (UUID)
            team_id: Team identifier
            team_name: Team name
            round_number: Round number
            submission_content: Submission content
            submission_format: Submission format (default: 'md')
            score: Evaluation score (0-100 scale)
            score_details: Detailed score breakdown (JSON)
            final_submission: Whether this is the final submission
            exit_reason: Exit reason (e.g., 'max rounds reached')

        Raises:
            ValueError: Invalid score range
        """
        # Validate score (0-100 scale)
        if not (0.0 <= score <= 100.0):
            raise ValueError(f"score must be between 0.0 and 100.0, got {score}")

        conn = self._get_connection()

        # Get current timestamp for updated_at
        from datetime import UTC, datetime

        updated_at = datetime.now(UTC).isoformat()

        with self._transaction(conn):
            conn.execute(
                """
                INSERT INTO leader_board
                (execution_id, team_id, team_name, round_number, submission_content,
                 submission_format, score, score_details, final_submission, exit_reason, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (execution_id, team_id, round_number) DO UPDATE SET
                    submission_content = EXCLUDED.submission_content,
                    score = EXCLUDED.score,
                    score_details = EXCLUDED.score_details,
                    final_submission = EXCLUDED.final_submission,
                    exit_reason = EXCLUDED.exit_reason,
                    updated_at = EXCLUDED.updated_at
            """,
                [
                    execution_id,
                    team_id,
                    team_name,
                    round_number,
                    submission_content,
                    submission_format,
                    score,
                    json.dumps(score_details, ensure_ascii=False),
                    final_submission,
                    exit_reason,
                    updated_at,
                ],
            )

    async def save_to_leader_board(
        self,
        execution_id: str,
        team_id: str,
        team_name: str,
        round_number: int,
        submission_content: str,
        submission_format: str,
        score: float,
        score_details: dict[str, Any],
        final_submission: bool = False,
        exit_reason: str | None = None,
    ) -> None:
        """Save to leader_board table (asynchronous version)

        This is the leader_board table with 0-100 score scale.

        Args:
            execution_id: Execution identifier (UUID)
            team_id: Team identifier
            team_name: Team name
            round_number: Round number
            submission_content: Submission content
            submission_format: Submission format (default: 'md')
            score: Evaluation score (0-100 scale)
            score_details: Detailed score breakdown (JSON)
            final_submission: Whether this is the final submission
            exit_reason: Exit reason (e.g., 'max rounds reached')

        Raises:
            DatabaseWriteError: Write failed after 3 retries
        """
        delays = [1, 2, 4]

        for attempt, delay in enumerate(delays, 1):
            try:
                await asyncio.to_thread(
                    self._save_to_leader_board_sync,
                    execution_id,
                    team_id,
                    team_name,
                    round_number,
                    submission_content,
                    submission_format,
                    score,
                    score_details,
                    final_submission,
                    exit_reason,
                )
                return
            except ValueError:
                # ValidationError は即座に再発生
                raise
            except Exception as e:
                if attempt == len(delays):
                    raise DatabaseWriteError(f"Failed to save to leader board after {attempt} retries: {e}") from e
                await asyncio.sleep(delay)

    def _get_leader_board_ranking_sync(self, execution_id: str) -> list[dict[str, Any]]:
        """Get leader board ranking for all teams (synchronous version)

        Args:
            execution_id: Execution identifier (UUID)

        Returns:
            List of team rankings with max scores
        """
        conn = self._get_connection()

        # Get max score for each team, ordered by score descending
        result = conn.execute(
            """
            SELECT
                team_id,
                team_name,
                MAX(score) AS max_score,
                COUNT(*) AS total_rounds
            FROM leader_board
            WHERE execution_id = ?
            GROUP BY team_id, team_name
            ORDER BY max_score DESC, team_id ASC
        """,
            [execution_id],
        ).fetchall()

        return [
            {
                "team_id": row[0],
                "team_name": row[1],
                "max_score": float(row[2]),
                "total_rounds": int(row[3]),
            }
            for row in result
        ]

    async def get_leader_board_ranking(self, execution_id: str) -> list[dict[str, Any]]:
        """Get leader board ranking for all teams (asynchronous version)

        Feature 037: Get max score for each team to display in next round prompt.

        Args:
            execution_id: Execution identifier (UUID)

        Returns:
            List of team rankings with max scores

        Raises:
            DatabaseReadError: Read failed
        """
        try:
            return await asyncio.to_thread(self._get_leader_board_ranking_sync, execution_id)
        except Exception as e:
            raise DatabaseReadError(f"Failed to get leader board ranking: {e}") from e
