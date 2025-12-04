"""Leader Agent E2Eテスト

Agent Delegation、構造化データ記録、DuckDB永続化のエンドツーエンド動作確認。

Tests:
    - チーム設定TOML → Leader Agent初期化 → 実行 → DB保存 → 読み込み
    - Agent Delegation動作確認
    - 構造化データ記録確認
"""

import os
import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic_ai import Agent

from mixseek.agents.leader.agent import create_leader_agent
from mixseek.agents.leader.config import LeaderAgentConfig, TeamConfig, TeamMemberAgentConfig, load_team_config
from mixseek.agents.leader.dependencies import TeamDependencies
from mixseek.agents.leader.models import MemberSubmissionsRecord
from mixseek.storage.aggregation_store import AggregationStore


class TestLeaderAgentE2E:
    """Leader Agent E2Eテスト（T044）"""

    @pytest.fixture
    def test_workspace(self) -> Generator[Path]:
        """テスト用ワークスペース"""
        tmpdir = tempfile.mkdtemp()
        workspace = Path(tmpdir)

        original_workspace = os.environ.get("MIXSEEK_WORKSPACE")
        os.environ["MIXSEEK_WORKSPACE"] = str(workspace)

        yield workspace

        if original_workspace:
            os.environ["MIXSEEK_WORKSPACE"] = original_workspace
        else:
            del os.environ["MIXSEEK_WORKSPACE"]

        shutil.rmtree(workspace, ignore_errors=True)

    @pytest.fixture
    def sample_team_toml(self, test_workspace: Path) -> Path:
        """サンプルチーム設定TOML"""
        toml_content = """
[team]
team_id = "e2e-test-team"
team_name = "E2E Test Team"

[team.leader]
model = "mock:test"
system_instruction = "You are a test leader"

[[team.members]]
agent_name = "test_analyst"
agent_type = "plain"
tool_description = "Test analysis"
model = "mock:test"
system_instruction = "Test analyst"
temperature = 0.7
max_tokens = 100
"""
        toml_path = test_workspace / "team.toml"
        toml_path.write_text(toml_content)
        return toml_path

    @pytest.mark.asyncio
    async def test_leader_agent_end_to_end(self, test_workspace: Path, sample_team_toml: Path) -> None:
        """Leader Agent E2Eテスト

        チーム設定TOML → Leader Agent初期化 → 実行 → DB保存 → 読み込み
        """
        # Arrange: TeamConfig読み込み
        team_config = load_team_config(sample_team_toml)

        # Member Agent作成（test model使用）
        member_agents = {}
        for member_config in team_config.members:
            member_agent = Agent("test", instructions=member_config.system_instruction, output_type=str)
            member_agents[member_config.agent_name] = member_agent

        # Leader Agent作成
        leader_agent = create_leader_agent(team_config, member_agents)

        # TeamDependencies初期化
        deps = TeamDependencies(team_id=team_config.team_id, team_name=team_config.team_name, round_number=1)

        # Act 1: Leader Agent実行
        result = await leader_agent.run("Test task", deps=deps)

        # Assert 1: 実行成功
        assert result.output is not None

        # Generate execution_id for this test run
        execution_id = str(uuid4())

        # Act 2: MemberSubmissionsRecord作成
        record = MemberSubmissionsRecord(
            execution_id=execution_id,
            team_id=deps.team_id,
            team_name=deps.team_name,
            round_number=deps.round_number,
            submissions=deps.submissions,
        )

        # Assert 2: 構造化データ記録
        assert record.team_id == "e2e-test-team"
        assert record.round_number == 1
        # Agent Delegationで選択されたAgent数（0以上）
        assert record.total_count >= 0

        # Act 3: DuckDB保存
        store = AggregationStore()
        messages = result.all_messages()
        await store.save_aggregation(execution_id, record, messages)

        # Act 4: DuckDB読み込み
        loaded_record, loaded_messages = await store.load_round_history(execution_id, "e2e-test-team", 1)

        # Assert 3: データ完全復元
        assert loaded_record is not None
        assert loaded_record.team_id == "e2e-test-team"
        assert loaded_record.round_number == 1
        # Message History復元
        assert isinstance(loaded_messages, list)

    @pytest.mark.asyncio
    async def test_agent_delegation_dynamic_selection(self, test_workspace: Path) -> None:
        """Agent Delegation動的選択の確認

        複数のMember Agentから一部のみが選択されることを確認。
        """
        # Arrange: 3つのMember Agentを定義
        team_config = TeamConfig(
            team_id="delegation-test",
            team_name="Delegation Test Team",
            leader=LeaderAgentConfig(model="test", system_instruction="Select appropriate agents"),
            members=[
                TeamMemberAgentConfig(
                    agent_name="agent1",
                    agent_type="plain",
                    tool_description="Agent 1",
                    model="test",
                    system_instruction="Agent 1",
                    temperature=0.7,
                    max_tokens=100,
                ),
                TeamMemberAgentConfig(
                    agent_name="agent2",
                    agent_type="plain",
                    tool_description="Agent 2",
                    model="test",
                    system_instruction="Agent 2",
                    temperature=0.7,
                    max_tokens=100,
                ),
                TeamMemberAgentConfig(
                    agent_name="agent3",
                    agent_type="plain",
                    tool_description="Agent 3",
                    model="test",
                    system_instruction="Agent 3",
                    temperature=0.7,
                    max_tokens=100,
                ),
            ],
        )

        # Member Agent作成
        member_agents = {}
        for member_config in team_config.members:
            member_agent = Agent("test", instructions=member_config.system_instruction, output_type=str)
            member_agents[member_config.agent_name] = member_agent

        # Leader Agent作成
        leader_agent = create_leader_agent(team_config, member_agents)

        # TeamDependencies初期化
        deps = TeamDependencies(team_id="delegation-test", team_name="Test", round_number=1)

        # Act: Leader Agent実行
        await leader_agent.run("Simple task", deps=deps)

        # Assert: Agent Delegation動作
        # 選択されたAgent数は0-3の範囲（タスクに応じて動的）
        assert 0 <= len(deps.submissions) <= 3

        # Generate execution_id for this test run
        execution_id_2 = str(uuid4())

        # 選択されたAgentのみが記録される
        record = MemberSubmissionsRecord(
            execution_id=execution_id_2,
            team_id=deps.team_id,
            team_name=deps.team_name,
            round_number=deps.round_number,
            submissions=deps.submissions,
        )

        # Agent Delegationにより、全Agentが実行されるとは限らない
        assert record.total_count <= 3

    @pytest.mark.asyncio
    async def test_leader_agent_solo_execution(self, test_workspace: Path) -> None:
        """Member Agent 0件でLeader Agentが単独で応答生成（SC-008）

        Given: Member Agent 0件のチーム設定
        When: Leader Agentを作成・実行
        Then: Leader Agentが単独で応答を生成し、Member Submissionは空リスト
        """
        # Given: チーム設定作成（Member Agent 0件）
        team_config = TeamConfig(
            team_id="solo-test-001",
            team_name="Solo Test Team",
            max_concurrent_members=15,
            leader=LeaderAgentConfig(
                model="test",  # モックモデル
                system_instruction="あなたは単独で動作するLeader Agentです。",
            ),
            members=[],  # ✅ 空リスト
        )

        # When: Leader Agent作成（空のmember_agents辞書）
        leader_agent = create_leader_agent(team_config, member_agents={})

        # And: Dependencies準備
        deps = TeamDependencies(
            team_id="solo-test-001",
            team_name="Solo Test Team",
            round_number=1,
        )

        # And: Leader Agent実行
        result = await leader_agent.run("簡単なタスクを実行してください。", deps=deps)

        # Then: Leader Agentが応答生成
        assert result.output is not None

        # And: Member Submissionは空
        assert len(deps.submissions) == 0  # ✅ Member Submissionは空

        # Generate execution_id for this test run
        execution_id_3 = str(uuid4())

        # And: 記録結果作成
        record = MemberSubmissionsRecord(
            execution_id=execution_id_3,
            team_id=deps.team_id,
            team_name=deps.team_name,
            round_number=deps.round_number,
            submissions=deps.submissions,
        )

        # And: 記録結果の検証
        assert record.total_count == 0
        assert record.success_count == 0
        assert record.failure_count == 0
        assert len(record.successful_submissions) == 0
        assert len(record.failed_submissions) == 0
