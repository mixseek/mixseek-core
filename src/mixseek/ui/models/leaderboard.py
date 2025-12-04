"""Pydantic models for leaderboard (leader_boardテーブルに対応)."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class LeaderboardEntry(BaseModel):
    """リーダーボードエントリ（leader_boardテーブル1レコード）."""

    team_id: str = Field(..., description="チームID")
    team_name: str = Field(..., description="チーム名")
    score: float = Field(..., description="評価スコア（0-100）")
    rank: int = Field(..., ge=1, description="順位（1位からの整数、クエリ時に計算）")
    round_number: int = Field(..., description="ラウンド番号")
    created_at: datetime = Field(..., description="作成日時")
    execution_id: str = Field(..., description="紐づく実行ID")

    @property
    def is_top(self) -> bool:
        """1位かどうか."""
        return self.rank == 1

    @property
    def score_percentage(self) -> float:
        """スコアを0-100%で表示."""
        return self.score


class Submission(BaseModel):
    """サブミッション（leader_boardテーブルの最高スコアレコード）."""

    team_id: str = Field(..., description="チームID")
    team_name: str = Field(..., description="チーム名")
    execution_id: str = Field(..., description="実行ID")
    score: float = Field(..., description="評価スコア（0-100）")
    submission_content: str = Field(..., description="サブミッション内容")
    score_details: dict[str, Any] = Field(..., description="評価詳細（JSON）")
    round_number: int = Field(..., description="ラウンド番号")
    created_at: datetime = Field(..., description="作成日時")

    @property
    def content_preview(self) -> str:
        """内容のプレビュー（最初の200文字）."""
        max_length = 200
        if len(self.submission_content) <= max_length:
            return self.submission_content
        return self.submission_content[:max_length] + "..."

    @property
    def score_percentage(self) -> float:
        """スコアを0-100%で表示."""
        return self.score

    @property
    def evaluation_feedback(self) -> str:
        """評価フィードバック（後方互換性のため、score_detailsから生成）."""
        if not self.score_details or "metrics" not in self.score_details:
            return ""

        metrics = self.score_details.get("metrics", [])
        if not metrics:
            return ""

        feedback_lines = [
            f"{metric.get('metric_name', 'Unknown')}: {metric.get('evaluator_comment', 'No comment')}"
            for metric in metrics
        ]
        return "\n".join(feedback_lines)
