"""Orchestrator data models"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, computed_field, field_validator
from pydantic_ai import RunUsage

from mixseek.models.leaderboard import LeaderBoardEntry


class OrchestratorTask(BaseModel):
    """ユーザプロンプトから生成されるタスク定義"""

    execution_id: str = Field(default_factory=lambda: str(uuid4()), description="実行一意識別子(UUID)")
    user_prompt: str = Field(description="ユーザプロンプト")
    team_configs: list[Path] = Field(description="チーム設定TOMLパスリスト")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="作成日時")
    timeout_seconds: int = Field(gt=0, description="チーム単位タイムアウト（秒）")

    # Round configuration (Feature 037-mixseek-core-round-controller)
    max_rounds: int = Field(default=5, ge=1, le=10, description="Maximum number of rounds")
    min_rounds: int = Field(default=2, ge=1, description="Minimum number of rounds (before LLM judgment)")
    submission_timeout_seconds: int = Field(default=300, gt=0, description="Submission timeout (seconds)")
    judgment_timeout_seconds: int = Field(default=60, gt=0, description="Judgment timeout (seconds)")

    @field_validator("user_prompt")
    @classmethod
    def validate_user_prompt(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("user_prompt cannot be empty")
        return v

    @field_validator("team_configs")
    @classmethod
    def validate_team_configs(cls, v: list[Path]) -> list[Path]:
        if not v:
            raise ValueError("team_configs must have at least one config")
        return v

    @field_validator("min_rounds")
    @classmethod
    def validate_min_rounds(cls, v: int, info: Any) -> int:
        """Validate min_rounds <= max_rounds"""
        max_rounds = info.data.get("max_rounds")
        if max_rounds is not None and v > max_rounds:
            raise ValueError(f"min_rounds ({v}) must be <= max_rounds ({max_rounds})")
        return v


class TeamStatus(BaseModel):
    """特定チームの実行状態"""

    team_id: str = Field(description="チーム識別子")
    team_name: str = Field(description="チーム名")
    status: Literal["pending", "running", "completed", "failed", "timeout"] = Field(
        default="pending",
        description="実行ステータス",
    )
    current_round: int = Field(default=0, ge=0, description="現在のラウンド番号")
    started_at: datetime | None = Field(default=None, description="実行開始日時")
    completed_at: datetime | None = Field(default=None, description="実行完了日時")
    error_message: str | None = Field(default=None, description="エラーメッセージ")


class RoundResult(BaseModel):
    """1ラウンドの実行結果"""

    execution_id: str = Field(description="実行識別子(UUID)")
    team_id: str = Field(description="チーム識別子")
    team_name: str = Field(description="チーム名")
    round_number: int = Field(ge=1, description="ラウンド番号")
    submission_content: str = Field(description="Submissionテキスト")
    evaluation_score: float = Field(ge=0.0, le=1.0, description="評価スコア（0.0-1.0スケール）")
    evaluation_feedback: str = Field(description="評価フィードバック")
    usage: RunUsage = Field(description="リソース使用量")
    execution_time_seconds: float = Field(gt=0, description="実行時間（秒）")
    completed_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="完了日時",
    )


class FailedTeamInfo(BaseModel):
    """失敗チームの情報"""

    team_id: str = Field(description="チーム識別子")
    team_name: str = Field(description="チーム名")
    error_message: str = Field(description="エラーメッセージ")


class ExecutionSummary(BaseModel):
    """全チームの完了後に生成される最終集約情報

    Feature 037-mixseek-core-round-controller:
    - team_results changed from list[RoundResult] to list[LeaderBoardEntry]
    - best_score changed from 0.0-1.0 to 0.0-100.0 scale
    """

    execution_id: str = Field(description="実行識別子(UUID)")
    user_prompt: str = Field(description="ユーザプロンプト")
    team_results: list[LeaderBoardEntry] = Field(
        default_factory=list, description="各チームの最高スコアSubmission (LeaderBoardEntry)"
    )
    best_team_id: str | None = Field(default=None, description="最高スコアチームID")
    best_score: float | None = Field(default=None, ge=0.0, le=100.0, description="最高評価スコア（0-100スケール）")
    total_execution_time_seconds: float = Field(gt=0, description="総実行時間（秒）")
    failed_teams_info: list[FailedTeamInfo] = Field(default_factory=list, description="失敗チームの詳細情報")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="サマリー作成日時",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_teams(self) -> int:
        """総チーム数"""
        return len(self.team_results) + len(self.failed_teams_info)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def completed_teams(self) -> int:
        """完了チーム数"""
        return len(self.team_results)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def failed_teams(self) -> int:
        """失敗チーム数"""
        return len(self.failed_teams_info)
