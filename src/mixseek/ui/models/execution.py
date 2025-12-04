"""Pydantic models for execution records."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ExecutionStatus(str, Enum):
    """実行ステータス（execution_summaryテーブルの値に対応）."""

    PENDING = "pending"  # 実行前
    RUNNING = "running"  # 実行中
    COMPLETED = "completed"  # 全チーム成功
    PARTIAL_FAILURE = "partial_failure"  # 一部チーム失敗
    FAILED = "failed"  # 全チーム失敗


class FailedTeamInfo(BaseModel):
    """失敗チーム情報."""

    team_id: str = Field(..., description="チームID")
    team_name: str = Field(..., description="チーム名")
    error_message: str = Field(..., description="エラーメッセージ")


class Execution(BaseModel):
    """タスク実行レコード（execution_summaryテーブルに対応）."""

    execution_id: str = Field(..., description="実行ID（UUID）")
    prompt: str = Field(..., description="ユーザプロンプト")
    status: ExecutionStatus = Field(..., description="実行ステータス")
    best_team_id: str | None = Field(None, description="最高スコアチームID")
    best_score: float | None = Field(None, description="最高評価スコア（0-100）")
    duration_seconds: float | None = Field(None, description="実行時間（秒）")
    created_at: datetime = Field(..., description="実行開始日時")
    completed_at: datetime | None = Field(None, description="実行完了日時")
    failed_teams_info: list[FailedTeamInfo] = Field(default_factory=list, description="失敗したチームの情報")

    @property
    def prompt_preview(self) -> str:
        """プロンプトのプレビュー（最初の100文字）."""
        max_length = 100
        if len(self.prompt) <= max_length:
            return self.prompt
        return self.prompt[:max_length] + "..."

    @property
    def result_summary(self) -> str | None:
        """結果サマリー（best_team_idとbest_scoreから生成）."""
        if self.best_team_id and self.best_score is not None:
            score_display = round(self.best_score)  # 整数に四捨五入（既に0-100の範囲）
            return f"Best Team: {self.best_team_id} (Score: {score_display})"
        return None

    class Config:
        use_enum_values = True  # Enumを文字列値としてシリアライズ


class ExecutionState(BaseModel):
    """リアルタイム実行状態（ポーリング用）."""

    execution_id: str = Field(..., description="実行ID（UUID）")
    status: ExecutionStatus = Field(..., description="実行ステータス")
    current_round: int | None = Field(None, ge=1, description="現在ラウンド番号")
    total_rounds: int | None = Field(None, ge=1, description="総ラウンド数")
    error_message: str | None = Field(None, description="エラーメッセージ（FAILED時）")

    @property
    def is_running(self) -> bool:
        """実行中かどうか."""
        return self.status == ExecutionStatus.RUNNING

    @property
    def is_completed(self) -> bool:
        """完了しているかどうか."""
        return self.status in (
            ExecutionStatus.COMPLETED,
            ExecutionStatus.PARTIAL_FAILURE,
            ExecutionStatus.FAILED,
        )

    @property
    def progress_percentage(self) -> float | None:
        """進捗率（0.0-1.0）."""
        if self.current_round is None or self.total_rounds is None:
            return None
        if self.total_rounds == 0:
            return 0.0
        return min(1.0, self.current_round / self.total_rounds)

    class Config:
        use_enum_values = True


class TeamProgressState(BaseModel):
    """チーム別進捗状態（リアルタイム表示用）."""

    team_id: str = Field(..., description="チームID")
    team_name: str = Field(..., description="チーム名")
    current_round: int = Field(..., ge=1, description="現在ラウンド番号")
    total_rounds: int = Field(..., ge=1, description="総ラウンド数")
    status: str = Field(..., description="ステータス（running/completed/failed）")
    current_agent: str | None = Field(None, description="現在実行中のエージェント（leader/evaluator/None）")
    updated_at: datetime = Field(..., description="最終更新日時")
    error_message: str | None = Field(None, description="エラーメッセージ（status=failed時）")

    @property
    def progress_percentage(self) -> float:
        """進捗率（0.0-1.0）."""
        if self.total_rounds == 0:
            return 0.0
        return min(1.0, self.current_round / self.total_rounds)

    @property
    def is_completed(self) -> bool:
        """完了しているかどうか."""
        return self.status == "completed"

    @property
    def status_icon(self) -> str:
        """ステータスアイコン."""
        return "✅" if self.is_completed else "🟢"

    @property
    def agent_display_text(self) -> str:
        """エージェントステータステキスト.

        Returns:
            str: エージェントステータス
                - "完了": ステータスがcompletedの場合
                - "実行中": current_agent="leader"の場合
                - "評価中": current_agent="evaluator"の場合
                - "待機中": current_agent=Noneの場合
        """
        if self.is_completed:
            return "完了"
        if self.current_agent == "leader":
            return "実行中"
        if self.current_agent == "evaluator":
            return "評価中"
        return "待機中"
