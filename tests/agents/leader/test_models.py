"""Leader Agent モデルのテスト

Article 3: Test-First Imperative準拠
このテストは実装前に作成され、Red（失敗）を確認します。

Tests:
    - MemberSubmission: 個別Member Agent応答モデル
    - MemberSubmissionsRecord: 単一ラウンド内の記録モデル（Agent Delegation対応）
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError
from pydantic_ai import RunUsage

from mixseek.agents.leader.models import MemberSubmission, MemberSubmissionsRecord


class TestMemberSubmission:
    """MemberSubmissionモデルのテスト（data-model.md Section 1）"""

    def test_create_success_submission(self) -> None:
        """成功応答のMemberSubmission作成"""
        # Arrange
        usage = RunUsage(input_tokens=150, output_tokens=300, requests=1)

        # Act
        submission = MemberSubmission(
            agent_name="analyst",
            agent_type="plain",
            content="データ分析の結果...",
            status="SUCCESS",
            usage=usage,
        )

        # Assert
        assert submission.agent_name == "analyst"
        assert submission.agent_type == "plain"
        assert submission.content == "データ分析の結果..."
        assert submission.status == "SUCCESS"
        assert submission.error_message is None
        assert submission.usage == usage
        assert submission.usage.input_tokens == 150
        assert isinstance(submission.timestamp, datetime)

    def test_create_error_submission(self) -> None:
        """エラー応答のMemberSubmission作成"""
        # Arrange
        usage = RunUsage(input_tokens=50, output_tokens=0, requests=1)

        # Act
        submission = MemberSubmission(
            agent_name="slow-agent",
            agent_type="plain",
            content="",
            status="ERROR",
            error_message="Timeout exceeded",
            usage=usage,
        )

        # Assert
        assert submission.status == "ERROR"
        assert submission.error_message == "Timeout exceeded"
        assert submission.content == ""  # エラー時は空文字列可

    def test_timestamp_auto_generation(self) -> None:
        """timestamp自動生成（UTC）"""
        # Act
        submission = MemberSubmission(
            agent_name="test",
            agent_type="plain",
            content="test",
            status="SUCCESS",
            usage=RunUsage(input_tokens=10, output_tokens=20, requests=1),
        )

        # Assert
        assert submission.timestamp.tzinfo is not None
        # UTCタイムスタンプ確認
        now_utc = datetime.now(UTC)
        assert (now_utc - submission.timestamp).total_seconds() < 1.0

    def test_execution_time_optional(self) -> None:
        """execution_time_msはオプション"""
        # Act
        submission = MemberSubmission(
            agent_name="test",
            agent_type="plain",
            content="test",
            status="SUCCESS",
            usage=RunUsage(input_tokens=10, output_tokens=20, requests=1),
        )

        # Assert
        assert submission.execution_time_ms is None

        # execution_time_ms設定
        submission_with_time = MemberSubmission(
            agent_name="test",
            agent_type="plain",
            content="test",
            status="SUCCESS",
            usage=RunUsage(input_tokens=10, output_tokens=20, requests=1),
            execution_time_ms=1234.5,
        )
        assert submission_with_time.execution_time_ms == 1234.5

    def test_validation_status_enum(self) -> None:
        """statusバリデーション: SUCCESS/ERRORのみ許可"""
        # Arrange
        usage = RunUsage(input_tokens=10, output_tokens=20, requests=1)

        # 有効な値
        MemberSubmission(agent_name="test", agent_type="plain", content="test", status="SUCCESS", usage=usage)
        MemberSubmission(agent_name="test", agent_type="plain", content="test", status="ERROR", usage=usage)

        # 無効な値は将来的にenumで制約（現在はstr型）
        # TODO: statusをenumに変更する場合、このテストを有効化
        # with pytest.raises(ValidationError):
        #     MemberSubmission(
        #         agent_name="test", agent_type="plain", content="test",
        #         status="INVALID", usage=usage
        #     )

    def test_json_serialization_with_datetime(self) -> None:
        """JSON serialization with datetime field (mode='json')"""
        # Arrange
        usage = RunUsage(input_tokens=150, output_tokens=300, requests=1)
        submission = MemberSubmission(
            agent_name="analyst",
            agent_type="plain",
            content="データ分析の結果...",
            status="SUCCESS",
            usage=usage,
        )

        # Act - mode='json'でdatetimeをISO8601文字列に変換
        dumped = submission.model_dump(mode="json")

        # Assert
        assert isinstance(dumped["timestamp"], str)  # datetime → str
        assert "T" in dumped["timestamp"]  # ISO8601フォーマット
        # JSON serialization可能であることを確認
        import json

        json_str = json.dumps(dumped)
        assert isinstance(json_str, str)


class TestMemberSubmissionsRecord:
    """MemberSubmissionsRecordモデルのテスト（data-model.md Section 2）

    重要な設計変更:
    - aggregated_content computed fieldを削除（Round Controllerが整形）
    - Agent Delegation対応（submissionsは動的に選択されたMember Agentのみ）
    """

    def test_create_with_submissions(self) -> None:
        """submissionsリスト付きで作成"""
        # Arrange
        submissions = [
            MemberSubmission(
                agent_name="analyst",
                agent_type="plain",
                content="分析結果",
                status="SUCCESS",
                usage=RunUsage(input_tokens=150, output_tokens=300, requests=1),
            ),
            MemberSubmission(
                agent_name="summarizer",
                agent_type="plain",
                content="要約結果",
                status="SUCCESS",
                usage=RunUsage(input_tokens=100, output_tokens=200, requests=1),
            ),
        ]

        # Act
        record = MemberSubmissionsRecord(
            execution_id="test-exec-001",
            team_id="team-001",
            team_name="Test Team",
            round_number=1,
            submissions=submissions,
        )

        # Assert
        assert record.team_id == "team-001"
        assert record.round_number == 1
        assert len(record.submissions) == 2

    def test_create_with_empty_submissions(self) -> None:
        """空のsubmissionsリストで作成（Edge Case: Leader Agentが1つもMember Agentを選択しない）"""
        # Act
        record = MemberSubmissionsRecord(
            execution_id="test-exec-001",
            team_id="team-001",
            team_name="Test Team",
            round_number=1,
            submissions=[],  # 空リスト可能
        )

        # Assert
        assert len(record.submissions) == 0
        assert record.total_count == 0
        assert record.success_count == 0
        assert record.failure_count == 0

    def test_successful_submissions_computed_field(self) -> None:
        """successful_submissions computed field（FR-002: エラー除外）"""
        # Arrange
        submissions = [
            MemberSubmission(
                agent_name="analyst",
                agent_type="plain",
                content="成功",
                status="SUCCESS",
                usage=RunUsage(input_tokens=100, output_tokens=200, requests=1),
            ),
            MemberSubmission(
                agent_name="slow-agent",
                agent_type="plain",
                content="",
                status="ERROR",
                error_message="Timeout",
                usage=RunUsage(input_tokens=50, output_tokens=0, requests=1),
            ),
            MemberSubmission(
                agent_name="summarizer",
                agent_type="plain",
                content="要約",
                status="SUCCESS",
                usage=RunUsage(input_tokens=80, output_tokens=150, requests=1),
            ),
        ]

        # Act
        record = MemberSubmissionsRecord(
            execution_id="test-exec-001",
            team_id="team-001",
            team_name="Test Team",
            round_number=1,
            submissions=submissions,
        )

        # Assert
        assert len(record.successful_submissions) == 2
        assert record.successful_submissions[0].agent_name == "analyst"
        assert record.successful_submissions[1].agent_name == "summarizer"

    def test_failed_submissions_computed_field(self) -> None:
        """failed_submissions computed field"""
        # Arrange
        submissions = [
            MemberSubmission(
                agent_name="analyst",
                agent_type="plain",
                content="成功",
                status="SUCCESS",
                usage=RunUsage(input_tokens=100, output_tokens=200, requests=1),
            ),
            MemberSubmission(
                agent_name="slow-agent",
                agent_type="plain",
                content="",
                status="ERROR",
                error_message="Timeout",
                usage=RunUsage(input_tokens=50, output_tokens=0, requests=1),
            ),
        ]

        # Act
        record = MemberSubmissionsRecord(
            execution_id="test-exec-001",
            team_id="team-001",
            team_name="Test Team",
            round_number=1,
            submissions=submissions,
        )

        # Assert
        assert len(record.failed_submissions) == 1
        assert record.failed_submissions[0].agent_name == "slow-agent"
        assert record.failed_submissions[0].error_message == "Timeout"

    def test_count_computed_fields(self) -> None:
        """total_count, success_count, failure_count computed fields"""
        # Arrange
        submissions = [
            MemberSubmission(
                agent_name="agent1",
                agent_type="plain",
                content="ok",
                status="SUCCESS",
                usage=RunUsage(input_tokens=10, output_tokens=20, requests=1),
            ),
            MemberSubmission(
                agent_name="agent2",
                agent_type="plain",
                content="ok",
                status="SUCCESS",
                usage=RunUsage(input_tokens=10, output_tokens=20, requests=1),
            ),
            MemberSubmission(
                agent_name="agent3",
                agent_type="plain",
                content="",
                status="ERROR",
                error_message="Err",
                usage=RunUsage(input_tokens=10, output_tokens=0, requests=1),
            ),
        ]

        # Act
        record = MemberSubmissionsRecord(
            execution_id="test-exec-001",
            team_id="team-001",
            team_name="Test Team",
            round_number=1,
            submissions=submissions,
        )

        # Assert
        assert record.total_count == 3
        assert record.success_count == 2
        assert record.failure_count == 1

    def test_total_usage_aggregation(self) -> None:
        """total_usage computed field（FR-005: 全Member Agentのリソース使用量合計）"""
        # Arrange
        submissions = [
            MemberSubmission(
                agent_name="analyst",
                agent_type="plain",
                content="分析",
                status="SUCCESS",
                usage=RunUsage(input_tokens=150, output_tokens=300, requests=1),
            ),
            MemberSubmission(
                agent_name="summarizer",
                agent_type="plain",
                content="要約",
                status="SUCCESS",
                usage=RunUsage(input_tokens=100, output_tokens=200, requests=1),
            ),
            MemberSubmission(
                agent_name="failed-agent",
                agent_type="plain",
                content="",
                status="ERROR",
                error_message="Error",
                usage=RunUsage(input_tokens=50, output_tokens=0, requests=1),
            ),
        ]

        # Act
        record = MemberSubmissionsRecord(
            execution_id="test-exec-001",
            team_id="team-001",
            team_name="Test Team",
            round_number=1,
            submissions=submissions,
        )

        # Assert
        # 全Agent（成功・失敗含む）のusageを合計
        assert record.total_usage.input_tokens == 300  # 150 + 100 + 50
        assert record.total_usage.output_tokens == 500  # 300 + 200 + 0
        assert record.total_usage.requests == 3  # 1 + 1 + 1

    def test_total_usage_with_empty_submissions(self) -> None:
        """total_usage with empty submissions（Edge Case）"""
        # Act
        record = MemberSubmissionsRecord(
            execution_id="test-exec-001", team_id="team-001", team_name="Test Team", round_number=1, submissions=[]
        )

        # Assert
        assert record.total_usage.input_tokens == 0
        assert record.total_usage.output_tokens == 0
        assert record.total_usage.requests == 0

    def test_round_number_validation(self) -> None:
        """round_number >= 1バリデーション"""
        # Arrange
        submissions: list[MemberSubmission] = []

        # round_number = 1は有効
        MemberSubmissionsRecord(
            execution_id="test-exec-001",
            team_id="team-001",
            team_name="Test Team",
            round_number=1,
            submissions=submissions,
        )

        # round_number = 0は無効
        with pytest.raises(ValidationError) as exc_info:
            MemberSubmissionsRecord(
                execution_id="test-exec-001",
                team_id="team-001",
                team_name="Test Team",
                round_number=0,
                submissions=submissions,
            )
        assert "round_number" in str(exc_info.value)

        # round_number < 0は無効
        with pytest.raises(ValidationError):
            MemberSubmissionsRecord(
                execution_id="test-exec-001",
                team_id="team-001",
                team_name="Test Team",
                round_number=-1,
                submissions=submissions,
            )

    def test_no_aggregated_content_field(self) -> None:
        """aggregated_content fieldが存在しないことを確認（Round Controllerが整形）"""
        # Arrange
        submissions = [
            MemberSubmission(
                agent_name="analyst",
                agent_type="plain",
                content="分析結果",
                status="SUCCESS",
                usage=RunUsage(input_tokens=100, output_tokens=200, requests=1),
            )
        ]

        # Act
        record = MemberSubmissionsRecord(
            execution_id="test-exec-001",
            team_id="team-001",
            team_name="Test Team",
            round_number=1,
            submissions=submissions,
        )

        # Assert
        # aggregated_content属性が存在しないことを確認（設計変更）
        assert not hasattr(record, "aggregated_content")

        # model_dump()にもaggregated_contentが含まれないことを確認
        dumped = record.model_dump()
        assert "aggregated_content" not in dumped
