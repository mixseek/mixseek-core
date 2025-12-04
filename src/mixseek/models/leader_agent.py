"""Leader Agent - Member Agent応答記録モデル

このモジュールはLeader AgentによるMember Agent応答の構造化データ記録を実装します。

責務範囲:
    - 単一ラウンド内のMember Agent応答を構造化データとして記録
    - 失敗応答の自動除外とリソース使用量の集計
    - Markdown連結などの整形処理はRound Controllerが実施（本モジュールの責務外）

References:
    - Spec: specs/008-leader/spec.md (FR-003)
    - Data Model: specs/008-leader/data-model.md
"""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, computed_field

from mixseek.models.member_agent import AgentType, MemberAgentResult, ResultStatus


class MemberSubmission(BaseModel):
    """Member Agentの単一ラウンドにおける応答（集約用）

    既存のMemberAgentResultから変換され、Leader Agentによる
    集約処理に最適化された軽量データモデル。

    Attributes:
        agent_name: Member Agent名
        agent_type: Member Agentタイプ
        content: 応答コンテンツ
        status: 実行ステータス
        error_message: エラーメッセージ（失敗時）
        usage_info: RunUsageから取得したリソース使用情報
        execution_time_ms: 実行時間（ミリ秒）
        timestamp: 応答生成時刻
    """

    # Member Agent識別情報
    agent_name: str = Field(..., description="Member Agent名")
    agent_type: AgentType = Field(..., description="Member Agentタイプ")

    # 応答内容
    content: str = Field(..., description="応答コンテンツ")

    # ステータス情報
    status: ResultStatus = Field(..., description="実行ステータス")
    error_message: str | None = Field(default=None, description="エラーメッセージ（失敗時）")

    # リソース情報（Pydantic AI互換）
    usage_info: dict[str, Any] | None = Field(default=None, description="RunUsageから取得したリソース使用情報")
    execution_time_ms: int | None = Field(default=None, description="実行時間（ミリ秒）")

    # タイムスタンプ
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="応答生成時刻")

    @classmethod
    def from_member_result(cls, result: MemberAgentResult) -> "MemberSubmission":
        """既存のMemberAgentResultから変換

        Args:
            result: Member Agent実行結果

        Returns:
            集約用のMemberSubmission
        """
        return cls(
            agent_name=result.agent_name,
            agent_type=AgentType(result.agent_type),  # str -> AgentType変換
            content=result.content,
            status=result.status,
            error_message=result.error_message,
            usage_info=result.usage_info,
            execution_time_ms=result.execution_time_ms,
            timestamp=result.timestamp,
        )

    def is_successful(self) -> bool:
        """成功した応答かどうか

        Returns:
            成功応答の場合True
        """
        return self.status == ResultStatus.SUCCESS

    def is_failed(self) -> bool:
        """失敗した応答かどうか

        Returns:
            失敗応答の場合True
        """
        return self.status == ResultStatus.ERROR


class MemberSubmissionsRecord(BaseModel):
    """Leader AgentによるMember Agent応答の記録（構造化データ）

    責務:
    - 単一ラウンド内のMember Agent応答を構造化データ（List[MemberSubmission]）として記録
    - 失敗応答の自動除外（FR-002）
    - リソース使用量の集計（FR-005）

    責務外（Round Controllerが実施）:
    - Markdown連結などの整形処理
    - 複数ラウンド間の統合処理
    - 評価フィードバックの適用

    Attributes:
        round_number: 現在のラウンド番号
        team_id: チームの一意識別子
        team_name: チーム名
        all_submissions: 全Member Agentの応答（成功・失敗含む）
        successful_submissions: 成功したSubmissionのみ（エラー除外済み、FR-002）
        failed_submissions: 失敗したSubmission（ログ・分析用）
        total_count: 総応答数
        success_count: 成功応答数
        failure_count: 失敗応答数
        total_usage: 全Member Agentの合計リソース使用量（FR-005）
    """

    # ラウンド情報
    round_number: int = Field(..., ge=1, description="現在のラウンド番号")
    team_id: str = Field(..., description="チームの一意識別子")
    team_name: str = Field(..., description="チーム名")

    # 全応答（成功・失敗含む）
    all_submissions: list[MemberSubmission] = Field(
        default_factory=list, description="全Member Agentの応答（成功・失敗含む）"
    )

    # 成功した応答のみ（エラー除外済み）
    successful_submissions: list[MemberSubmission] = Field(
        default_factory=list, description="成功したSubmissionのみ（FR-002: エラー除外）"
    )

    # 失敗した応答（記録用）
    failed_submissions: list[MemberSubmission] = Field(
        default_factory=list, description="失敗したSubmission（ログ・分析用）"
    )

    # 統計情報
    total_count: int = Field(..., ge=0, description="総応答数")
    success_count: int = Field(..., ge=0, description="成功応答数")
    failure_count: int = Field(..., ge=0, description="失敗応答数")

    # リソース使用量の集約（Pydantic AI RunUsage互換）
    total_usage: dict[str, int] | None = Field(
        default=None, description="全Member Agentの合計リソース使用量 (input_tokens, output_tokens, requests)"
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def summary(self) -> str:
        """集約結果のサマリー（ログ用）

        Returns:
            サマリー文字列
        """
        return f"[Round {self.round_number}] {self.success_count}/{self.total_count} Member Agents succeeded"

    @classmethod
    def from_member_results(
        cls, results: list[MemberAgentResult], round_number: int, team_id: str, team_name: str
    ) -> "MemberSubmissionsRecord":
        """MemberAgentResultのリストから記録結果を作成 (FR-001, FR-003)

        Args:
            results: Member Agent実行結果のリスト
            round_number: 現在のラウンド番号
            team_id: チームの一意識別子
            team_name: チーム名

        Returns:
            構造化データとして記録されたMemberSubmissionsRecord
        """
        # MemberAgentResult -> MemberSubmissionに変換
        all_submissions = [MemberSubmission.from_member_result(result) for result in results]

        # 成功/失敗で分類（FR-002: エラー除外）
        successful = [s for s in all_submissions if s.is_successful()]
        failed = [s for s in all_submissions if s.is_failed()]

        # リソース使用量の集約（FR-005）
        total_usage = cls._aggregate_usage(all_submissions)

        return cls(
            round_number=round_number,
            team_id=team_id,
            team_name=team_name,
            all_submissions=all_submissions,
            successful_submissions=successful,
            failed_submissions=failed,
            total_count=len(all_submissions),
            success_count=len(successful),
            failure_count=len(failed),
            total_usage=total_usage,
        )

    @staticmethod
    def _aggregate_usage(submissions: list[MemberSubmission]) -> dict[str, int] | None:
        """リソース使用量を集約 (FR-005)

        Pydantic AI RunUsageと互換性のある形式で集約。

        Args:
            submissions: Member Submissionリスト

        Returns:
            集約されたリソース使用量。全てのsubmissionにusage_infoがない場合はNone
        """
        if not submissions:
            return None

        total_input_tokens = 0
        total_output_tokens = 0
        total_requests = 0

        for submission in submissions:
            if submission.usage_info:
                total_input_tokens += submission.usage_info.get("input_tokens", 0) or 0
                total_output_tokens += submission.usage_info.get("output_tokens", 0) or 0
                total_requests += submission.usage_info.get("requests", 0) or 0

        return {"input_tokens": total_input_tokens, "output_tokens": total_output_tokens, "requests": total_requests}
