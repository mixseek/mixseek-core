"""Leader Agent モデルのユニットテスト

Test Coverage:
    - MemberSubmission: Member Agent応答の軽量モデル
    - MemberSubmissionsRecord: 記録結果モデル（構造化データ）

References:
    - Spec: specs/008-leader/spec.md (FR-003)
    - Data Model: specs/008-leader/data-model.md
"""

from mixseek.models.leader_agent import MemberSubmission, MemberSubmissionsRecord
from mixseek.models.member_agent import AgentType, MemberAgentResult, ResultStatus


class TestMemberSubmission:
    """MemberSubmission変換テスト（T008）"""

    def test_from_member_result_success(self) -> None:
        """正常系: 成功応答の変換"""
        # Given: 成功したMemberAgentResult
        result = MemberAgentResult.success(
            content="データ分析結果",
            agent_name="data-analyst",
            agent_type=AgentType.CODE_EXECUTION,
            execution_time_ms=1200,
            usage_info={"input_tokens": 100, "output_tokens": 200},
        )

        # When: MemberSubmissionに変換
        submission = MemberSubmission.from_member_result(result)

        # Then: 正しく変換される
        assert submission.agent_name == "data-analyst"
        assert submission.agent_type == AgentType.CODE_EXECUTION
        assert submission.content == "データ分析結果"
        assert submission.status == ResultStatus.SUCCESS
        assert submission.error_message is None
        assert submission.execution_time_ms == 1200
        assert submission.usage_info == {"input_tokens": 100, "output_tokens": 200}

    def test_from_member_result_error(self) -> None:
        """正常系: エラー応答の変換"""
        # Given: 失敗したMemberAgentResult
        result = MemberAgentResult.error(
            error_message="Timeout exceeded",
            agent_name="slow-agent",
            agent_type=AgentType.PLAIN,
            error_code="TIMEOUT",
        )

        # When: MemberSubmissionに変換
        submission = MemberSubmission.from_member_result(result)

        # Then: エラー情報が保持される
        assert submission.agent_name == "slow-agent"
        assert submission.status == ResultStatus.ERROR
        assert submission.error_message == "Timeout exceeded"
        assert submission.content == ""  # エラー時は空文字列

    def test_is_successful(self) -> None:
        """is_successful()メソッドテスト"""
        # Given: 成功応答
        success_result = MemberAgentResult.success(content="Success", agent_name="agent1", agent_type=AgentType.PLAIN)
        success_submission = MemberSubmission.from_member_result(success_result)

        # Given: 失敗応答
        error_result = MemberAgentResult.error(error_message="Error", agent_name="agent2", agent_type=AgentType.PLAIN)
        error_submission = MemberSubmission.from_member_result(error_result)

        # Then: ステータス判定が正しい
        assert success_submission.is_successful() is True
        assert error_submission.is_successful() is False

    def test_is_failed(self) -> None:
        """is_failed()メソッドテスト"""
        # Given: 成功応答と失敗応答
        success_result = MemberAgentResult.success(content="Success", agent_name="agent1", agent_type=AgentType.PLAIN)
        error_result = MemberAgentResult.error(error_message="Error", agent_name="agent2", agent_type=AgentType.PLAIN)

        # Then: 失敗判定が正しい
        assert MemberSubmission.from_member_result(success_result).is_failed() is False
        assert MemberSubmission.from_member_result(error_result).is_failed() is True


class TestMemberSubmissionsRecord:
    """MemberSubmissionsRecord記録テスト（T009）"""

    def test_from_member_results_all_success(self) -> None:
        """正常系: 全て成功時の記録"""
        # Given: 3つの成功応答
        results = [
            MemberAgentResult.success(
                content=f"Agent {i} response", agent_name=f"agent-{i}", agent_type=AgentType.PLAIN
            )
            for i in range(3)
        ]

        # When: 記録
        record = MemberSubmissionsRecord.from_member_results(
            results=results, round_number=1, team_id="team-001", team_name="Test Team"
        )

        # Then: 全て成功として分類
        assert record.total_count == 3
        assert record.success_count == 3
        assert record.failure_count == 0
        assert len(record.successful_submissions) == 3
        assert len(record.failed_submissions) == 0

    def test_from_member_results_with_failures(self) -> None:
        """正常系: 失敗混在時のエラー除外（FR-002）"""
        # Given: 2成功、1失敗
        results = [
            MemberAgentResult.success(content="Success 1", agent_name="agent-1", agent_type=AgentType.PLAIN),
            MemberAgentResult.error(error_message="Timeout", agent_name="agent-2", agent_type=AgentType.PLAIN),
            MemberAgentResult.success(content="Success 2", agent_name="agent-3", agent_type=AgentType.WEB_SEARCH),
        ]

        # When: 記録
        record = MemberSubmissionsRecord.from_member_results(
            results=results, round_number=1, team_id="team-001", team_name="Test Team"
        )

        # Then: 失敗が自動除外される（FR-002）
        assert record.total_count == 3
        assert record.success_count == 2
        assert record.failure_count == 1
        assert len(record.successful_submissions) == 2
        assert len(record.failed_submissions) == 1
        assert record.failed_submissions[0].agent_name == "agent-2"

    def test_aggregate_usage(self) -> None:
        """リソース使用量集計（FR-005）"""
        # Given: 3つの応答（リソース情報付き）
        results = [
            MemberAgentResult.success(
                content="R1",
                agent_name="a1",
                agent_type=AgentType.PLAIN,
                usage_info={"input_tokens": 100, "output_tokens": 200, "requests": 1},
            ),
            MemberAgentResult.success(
                content="R2",
                agent_name="a2",
                agent_type=AgentType.PLAIN,
                usage_info={"input_tokens": 150, "output_tokens": 250, "requests": 1},
            ),
            MemberAgentResult.success(
                content="R3",
                agent_name="a3",
                agent_type=AgentType.PLAIN,
                # usage_info なし
            ),
        ]

        # When: 記録
        record = MemberSubmissionsRecord.from_member_results(
            results=results, round_number=1, team_id="team-001", team_name="Test Team"
        )

        # Then: リソースが正しく合計される
        assert record.total_usage is not None
        assert record.total_usage["input_tokens"] == 250  # 100 + 150 + 0
        assert record.total_usage["output_tokens"] == 450  # 200 + 250 + 0
        assert record.total_usage["requests"] == 2  # 1 + 1 + 0

    def test_aggregate_usage_all_missing(self) -> None:
        """全てusage_infoなしの場合"""
        # Given: usage_infoなし
        results = [
            MemberAgentResult.success(content="R1", agent_name="a1", agent_type=AgentType.PLAIN),
            MemberAgentResult.success(content="R2", agent_name="a2", agent_type=AgentType.PLAIN),
        ]

        # When: 記録
        record = MemberSubmissionsRecord.from_member_results(
            results=results, round_number=1, team_id="team-001", team_name="Test Team"
        )

        # Then: 全て0として集計
        assert record.total_usage is not None
        assert record.total_usage["input_tokens"] == 0
        assert record.total_usage["output_tokens"] == 0
        assert record.total_usage["requests"] == 0
