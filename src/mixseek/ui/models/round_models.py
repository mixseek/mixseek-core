"""ラウンド進捗関連のデータモデル.

このモジュールはDuckDB (mixseek.db) から取得したラウンドデータの
Pydanticモデルを定義します。

Models:
    RoundProgress: ラウンド進捗情報
    TeamScoreHistory: チームスコア推移
    TeamSubmission: チームサブミッション

References:
    - Database schema: specs/008-leader/contracts/database-schema.sql
    - Research: specs/014-ui/research.md (Section 2: DuckDB スキーマ)
"""

from datetime import datetime
from typing import cast

from pydantic import BaseModel, Field


class RoundProgress(BaseModel):
    """ラウンド進捗情報.

    DuckDB round_statusテーブルから取得したラウンド進捗データ。
    チームごとの現在ラウンド番号、開始/終了時刻を保持。

    Attributes:
        team_id: チーム識別子（タイムライン表示時はオプショナル）
        team_name: チーム名（タイムライン表示時はオプショナル）
        round_number: 現在のラウンド番号
        round_started_at: ラウンド開始時刻（None可: ラウンド未開始時）
        round_ended_at: ラウンド終了時刻（None可: ラウンド進行中）

    Example:
        >>> progress = RoundProgress.from_db_row(
        ...     ("team-a", "チームA", 3, "2025-11-12 08:32:03", "2025-11-12 08:33:22")
        ... )
        >>> progress.round_number
        3
    """

    team_id: str | None = Field(None, description="チーム識別子")
    team_name: str | None = Field(None, description="チーム名")
    round_number: int = Field(..., ge=1, description="現在のラウンド番号")
    round_started_at: datetime | None = Field(None, description="ラウンド開始時刻")
    round_ended_at: datetime | None = Field(None, description="ラウンド終了時刻")

    @classmethod
    def from_db_row(cls, row: tuple[str | int | datetime | None, ...]) -> "RoundProgress":
        """DuckDBクエリ結果からモデルインスタンスを生成.

        Args:
            row: DuckDBクエリ結果のタプル
                形式1: (team_id, team_name, round_number, round_started_at, round_ended_at)
                形式2: (round_number, round_started_at, round_ended_at) - タイムライン用

        Returns:
            RoundProgressインスタンス

        Raises:
            ValueError: 行データの形式が不正な場合
        """
        # タイムライン用の短い形式（3フィールド）の場合
        if len(row) == 3:
            return cls(
                team_id=None,
                team_name=None,
                round_number=int(cast(int, row[0])),
                round_started_at=cast(datetime, row[1]) if row[1] is not None else None,
                round_ended_at=cast(datetime, row[2]) if row[2] is not None else None,
            )

        # 通常形式（5フィールド以上）の場合
        if len(row) < 3:
            raise ValueError(f"Invalid row format: expected at least 3 fields, got {len(row)}")

        return cls(
            team_id=str(row[0]) if row[0] is not None else None,
            team_name=str(row[1]) if row[1] is not None else None,
            round_number=int(cast(int, row[2])),
            round_started_at=cast(datetime, row[3]) if len(row) > 3 and row[3] is not None else None,
            round_ended_at=cast(datetime, row[4]) if len(row) > 4 and row[4] is not None else None,
        )


class TeamScoreHistory(BaseModel):
    """チームスコア推移.

    DuckDB leader_boardテーブルから取得したチームのスコア履歴。
    ラウンドごとのスコアを保持し、折れ線グラフ描画に使用。

    Attributes:
        team_id: チーム識別子
        team_name: チーム名
        round_number: ラウンド番号
        score: 評価スコア

    Example:
        >>> history = TeamScoreHistory.from_db_row(
        ...     ("team-a", "チームA", 1, 37.37)
        ... )
        >>> history.score
        37.37
    """

    team_id: str = Field(..., description="チーム識別子")
    team_name: str = Field(..., description="チーム名")
    round_number: int = Field(..., ge=1, description="ラウンド番号")
    score: float = Field(..., description="評価スコア")

    @classmethod
    def from_db_row(cls, row: tuple[str | int | float, ...]) -> "TeamScoreHistory":
        """DuckDBクエリ結果からモデルインスタンスを生成.

        Args:
            row: DuckDBクエリ結果のタプル
                (team_id, team_name, round_number, score)

        Returns:
            TeamScoreHistoryインスタンス

        Raises:
            ValueError: 行データの形式が不正な場合
        """
        if len(row) != 4:
            raise ValueError(f"Invalid row format: expected 4 fields, got {len(row)}")

        return cls(
            team_id=str(row[0]),
            team_name=str(row[1]),
            round_number=int(row[2]),
            score=float(row[3]),
        )


class TeamSubmission(BaseModel):
    """チームサブミッション.

    DuckDB leader_boardテーブルから取得したチームのサブミッション情報。
    最終ラウンドのサブミッション内容、スコア、詳細を保持。

    Attributes:
        team_id: チーム識別子
        team_name: チーム名
        round_number: ラウンド番号
        submission_content: サブミッション内容（マークダウン形式）
        score: 評価スコア
        score_details: スコア詳細（JSON）
        created_at: 作成日時
        final_submission: 最終サブミッションフラグ

    Example:
        >>> submission = TeamSubmission.from_db_row(
        ...     ("team-a", "チームA", 2, "# 分析結果", 41.68, '{"detail": "good"}',
        ...      "2025-11-12 08:35:02", True)
        ... )
        >>> submission.final_submission
        True
    """

    team_id: str = Field(..., description="チーム識別子")
    team_name: str = Field(..., description="チーム名")
    round_number: int = Field(..., ge=1, description="ラウンド番号")
    submission_content: str = Field(..., description="サブミッション内容")
    score: float = Field(..., description="評価スコア")
    score_details: str | None = Field(None, description="スコア詳細JSON")
    created_at: datetime = Field(..., description="作成日時")
    final_submission: bool = Field(False, description="最終サブミッションフラグ")

    @classmethod
    def from_db_row(cls, row: tuple[str | int | float | datetime | bool | None, ...]) -> "TeamSubmission":
        """DuckDBクエリ結果からモデルインスタンスを生成.

        Args:
            row: DuckDBクエリ結果のタプル
                (team_id, team_name, round_number, submission_content, score,
                 score_details, created_at, final_submission)

        Returns:
            TeamSubmissionインスタンス

        Raises:
            ValueError: 行データの形式が不正な場合
        """
        if len(row) < 5:
            raise ValueError(f"Invalid row format: expected at least 5 fields, got {len(row)}")

        return cls(
            team_id=str(row[0]),
            team_name=str(row[1]),
            round_number=int(cast(int, row[2])),
            submission_content=str(row[3]),
            score=float(cast(float, row[4])),
            score_details=str(row[5]) if len(row) > 5 and row[5] is not None else None,
            created_at=cast(datetime, row[6]) if len(row) > 6 else datetime.now(),
            final_submission=bool(row[7]) if len(row) > 7 else False,
        )
