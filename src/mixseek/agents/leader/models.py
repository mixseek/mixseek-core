"""Leader Agent データモデル

Agent Delegation方式に対応したデータモデル。
"""

from datetime import UTC, datetime

from pydantic import BaseModel, Field, computed_field
from pydantic_ai import RunUsage
from pydantic_ai.messages import ModelMessage


class MemberSubmission(BaseModel):
    """個別Member Agent応答モデル"""

    agent_name: str = Field(description="Member Agent名")
    agent_type: str = Field(description="Member Agent種別")
    content: str = Field(description="Member Agentの応答テキスト")
    status: str = Field(description="実行ステータス")
    error_message: str | None = Field(default=None, description="エラーメッセージ")
    usage: RunUsage = Field(description="Pydantic AI RunUsage")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="応答生成時刻")
    execution_time_ms: float | None = Field(default=None, description="実行時間（ミリ秒）")
    all_messages: list[ModelMessage] | None = Field(
        default=None,
        description="Member Agent message history (FR-034)",
    )


class MemberSubmissionsRecord(BaseModel):
    """単一ラウンド内のMember Agent応答記録"""

    execution_id: str = Field(description="実行識別子(UUID)")
    team_id: str = Field(description="チームID")
    team_name: str = Field(description="チーム名")
    round_number: int = Field(ge=1, description="ラウンド番号")
    submissions: list[MemberSubmission] = Field(default_factory=list, description="Member Agent応答")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def successful_submissions(self) -> list[MemberSubmission]:
        """成功したMember Agent応答のみ"""
        return [s for s in self.submissions if s.status == "SUCCESS"]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def failed_submissions(self) -> list[MemberSubmission]:
        """失敗したMember Agent応答のみ"""
        return [s for s in self.submissions if s.status == "ERROR"]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_count(self) -> int:
        """総数"""
        return len(self.submissions)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def success_count(self) -> int:
        """成功数"""
        return len(self.successful_submissions)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def failure_count(self) -> int:
        """失敗数"""
        return len(self.failed_submissions)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_usage(self) -> RunUsage:
        """全Member Agentのリソース使用量合計"""
        total_input = sum(s.usage.input_tokens or 0 for s in self.submissions)
        total_output = sum(s.usage.output_tokens or 0 for s in self.submissions)
        total_requests = sum(s.usage.requests or 0 for s in self.submissions)
        return RunUsage(input_tokens=total_input, output_tokens=total_output, requests=total_requests)
