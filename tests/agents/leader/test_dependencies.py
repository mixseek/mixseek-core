"""TeamDependencies のテスト

Article 3: Test-First Imperative準拠

TeamDependenciesはAgent Delegationで各Member Agentに共有される依存関係オブジェクト。
RunContext[TeamDependencies]として使用されます。

Tests:
    - TeamDependencies初期化
    - submissionsリスト（mutable）
    - MemberSubmission追加
"""

from pydantic_ai import RunUsage

from mixseek.agents.leader.dependencies import TeamDependencies
from mixseek.agents.leader.models import MemberSubmission


class TestTeamDependencies:
    """TeamDependencies モデルのテスト（data-model.md Section 4）"""

    def test_create_team_dependencies(self) -> None:
        """TeamDependencies初期化"""
        # Act
        deps = TeamDependencies(team_id="team-001", team_name="Test Team", round_number=1)

        # Assert
        assert deps.team_id == "team-001"
        assert deps.team_name == "Test Team"
        assert deps.round_number == 1
        assert deps.submissions == []  # 初期空リスト

    def test_submissions_list_is_mutable(self) -> None:
        """submissionsリストがmutable（Agent Delegation時に追加可能）"""
        # Arrange
        deps = TeamDependencies(team_id="team-001", team_name="Test Team", round_number=1)

        # Act: MemberSubmission追加
        submission = MemberSubmission(
            agent_name="analyst",
            agent_type="plain",
            content="分析結果",
            status="SUCCESS",
            usage=RunUsage(input_tokens=100, output_tokens=200, requests=1),
        )
        deps.submissions.append(submission)

        # Assert
        assert len(deps.submissions) == 1
        assert deps.submissions[0].agent_name == "analyst"

    def test_multiple_submissions(self) -> None:
        """複数のMemberSubmission追加（Agent Delegationで複数Member Agent実行）"""
        # Arrange
        deps = TeamDependencies(team_id="team-001", team_name="Test Team", round_number=1)

        # Act: 複数追加
        deps.submissions.append(
            MemberSubmission(
                agent_name="analyst",
                agent_type="plain",
                content="分析",
                status="SUCCESS",
                usage=RunUsage(input_tokens=100, output_tokens=200, requests=1),
            )
        )
        deps.submissions.append(
            MemberSubmission(
                agent_name="summarizer",
                agent_type="plain",
                content="要約",
                status="SUCCESS",
                usage=RunUsage(input_tokens=80, output_tokens=150, requests=1),
            )
        )

        # Assert
        assert len(deps.submissions) == 2
        assert deps.submissions[0].agent_name == "analyst"
        assert deps.submissions[1].agent_name == "summarizer"

    def test_submissions_initially_empty(self) -> None:
        """submissionsは初期状態で空リスト"""
        # Act
        deps = TeamDependencies(team_id="team-001", team_name="Test Team", round_number=1)

        # Assert
        assert isinstance(deps.submissions, list)
        assert len(deps.submissions) == 0
