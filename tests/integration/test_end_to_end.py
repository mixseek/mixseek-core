"""エンドツーエンド統合テスト

Test Coverage:
    - CLI → 集約 → DB保存 → 読み込みの完全フロー
    - 複数チーム実行 → Leader Boardランキング

References:
    - Spec: specs/008-leader/spec.md
    - 全User Stories統合テスト
"""

from pathlib import Path
from uuid import uuid4

import pytest

from mixseek.agents.leader.models import MemberSubmission, MemberSubmissionsRecord
from mixseek.storage.aggregation_store import AggregationStore


class TestEndToEnd:
    """エンドツーエンドテスト（T045）"""

    @pytest.fixture
    def store(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> AggregationStore:
        """テスト用ストア"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
        return AggregationStore()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_full_workflow(self, store: AggregationStore) -> None:
        """完全ワークフロー: 集約 → DB保存 → 読み込み"""
        from pydantic_ai import RunUsage

        # Given: execution_id for this test run
        execution_id = str(uuid4())

        # Given: Member Agent応答（モック）
        submissions = [
            MemberSubmission(
                agent_name="analyst",
                agent_type="code_execution",
                content="Analysis result",
                status="SUCCESS",
                usage=RunUsage(input_tokens=100, output_tokens=200, requests=1),
            ),
            MemberSubmission(
                agent_name="searcher",
                agent_type="web_search",
                content="Search result",
                status="SUCCESS",
                usage=RunUsage(input_tokens=150, output_tokens=250, requests=1),
            ),
        ]

        # When: 集約
        aggregated = MemberSubmissionsRecord(
            execution_id=execution_id,
            team_id="team-001",
            team_name="Integration Test Team",
            round_number=1,
            submissions=submissions,
        )

        # Then: 集約結果検証
        assert aggregated.success_count == 2
        assert any(s.agent_name == "analyst" for s in aggregated.submissions)
        assert any(s.agent_name == "searcher" for s in aggregated.submissions)

        # When: DB保存
        from typing import cast

        from pydantic_ai import ModelMessage
        from pydantic_ai.messages import ModelRequest, UserPromptPart

        messages = cast(list[ModelMessage], [ModelRequest(parts=[UserPromptPart(content="Test prompt")])])
        await store.save_aggregation(execution_id, aggregated, messages)

        # When: DB読み込み
        loaded_aggregated, loaded_messages = await store.load_round_history(execution_id, "team-001", 1)

        # Then: 完全復元
        assert loaded_aggregated is not None
        assert loaded_aggregated.team_id == "team-001"
        assert loaded_aggregated.success_count == 2
        assert len(loaded_messages) == 1

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_leader_board_ranking(self, store: AggregationStore) -> None:
        """複数チーム実行 → ランキング正常"""
        from pydantic_ai import RunUsage

        # Given: execution_id for this test run (simulating one orchestration execution)
        execution_id = str(uuid4())

        # Given: 3チームの集約結果を保存
        teams_data = [
            ("team-A", "Team Alpha", 0.95),
            ("team-B", "Team Beta", 0.75),
            ("team-C", "Team Gamma", 0.90),
        ]

        for team_id, team_name, score in teams_data:
            # 集約結果作成
            submissions = [
                MemberSubmission(
                    agent_name="a",
                    agent_type="plain",
                    content="Result",
                    status="SUCCESS",
                    usage=RunUsage(input_tokens=100, output_tokens=200, requests=1),
                )
            ]
            aggregated = MemberSubmissionsRecord(
                execution_id=execution_id,
                team_id=team_id,
                team_name=team_name,
                round_number=1,
                submissions=submissions,
            )

            # DB保存
            from typing import cast

            from pydantic_ai import ModelMessage
            from pydantic_ai.messages import ModelRequest, UserPromptPart

            messages = cast(list[ModelMessage], [ModelRequest(parts=[UserPromptPart(content="Prompt")])])
            await store.save_aggregation(execution_id, aggregated, messages)

            # Leader Board登録
            submission_content = "\n".join([s.content for s in aggregated.submissions])
            await store.save_to_leader_board(
                execution_id=execution_id,
                team_id=team_id,
                team_name=team_name,
                round_number=1,
                submission_content=submission_content,
                submission_format="md",
                score=score * 100.0,  # Convert 0.0-1.0 to 0-100 scale
                score_details={"overall_score": score * 100.0, "feedback": "OK"},
            )

        # When: Leader Board取得
        df = await store.get_leader_board(limit=10)

        # Then: スコア順にランキング
        assert len(df) == 3
        assert df.iloc[0]["team_name"] == "Team Alpha"  # 0.95
        assert df.iloc[1]["team_name"] == "Team Gamma"  # 0.90
        assert df.iloc[2]["team_name"] == "Team Beta"  # 0.75
