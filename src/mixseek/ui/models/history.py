"""Pydantic models for history page."""

from datetime import datetime

from pydantic import BaseModel, Field

from mixseek.ui.models.execution import Execution, ExecutionStatus


class HistoryEntry(BaseModel):
    """履歴ページ用の実行履歴エントリ."""

    execution_id: str = Field(..., description="実行ID")
    prompt_preview: str = Field(..., description="プロンプト概要（最初の100文字）")
    created_at: datetime = Field(..., description="実行開始日時")
    status: ExecutionStatus = Field(..., description="実行ステータス")
    best_team_display: str = Field(..., description="最高スコアチーム表示（チームID + スコア%）")

    @classmethod
    def from_execution(cls, execution: Execution) -> "HistoryEntry":
        """Executionモデルから生成."""
        # best_teamの表示文字列を生成
        if execution.best_team_id and execution.best_score is not None:
            score_display = round(execution.best_score)  # 整数に四捨五入（既に0-100の範囲）
            best_team_display = f"{execution.best_team_id} ({score_display})"
        else:
            best_team_display = "N/A"

        return cls(
            execution_id=execution.execution_id,
            prompt_preview=execution.prompt_preview,
            created_at=execution.created_at,
            status=execution.status,
            best_team_display=best_team_display,
        )

    class Config:
        use_enum_values = True
