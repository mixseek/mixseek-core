"""並列書き込み統合テスト

Test Coverage:
    - 複数チーム並列書き込み（MVCC動作確認）
    - asyncio.to_thread並列実行
    - ロック競合なし確認

References:
    - Spec: specs/008-leader/spec.md (US2, FR-014, SC-001, SC-005)
    - Research: specs/008-leader/research.md (R5)
"""

import asyncio
from pathlib import Path
from typing import cast
from uuid import uuid4

import pytest
from pydantic_ai import ModelMessage, RunUsage
from pydantic_ai.messages import ModelRequest, UserPromptPart

from mixseek.agents.leader.models import MemberSubmission, MemberSubmissionsRecord
from mixseek.storage.aggregation_store import AggregationStore


class TestConcurrentWrites:
    """並列書き込みテスト（T018）"""

    @pytest.fixture
    def store(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> AggregationStore:
        """テスト用ストア"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
        return AggregationStore()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_10_teams_parallel_writes(self, store: AggregationStore) -> None:
        """10チーム×5ラウンド並列書き込み（FR-014, SC-001）"""

        async def team_worker(team_id: str, num_rounds: int, execution_id: str) -> None:
            """チームシミュレーション"""
            for round_num in range(1, num_rounds + 1):
                # サンプル集約結果
                submissions = [
                    MemberSubmission(
                        agent_name="a1",
                        agent_type="plain",
                        content=f"R{round_num}",
                        status="SUCCESS",
                        usage=RunUsage(input_tokens=100, output_tokens=200, requests=1),
                    )
                ]
                record = MemberSubmissionsRecord(
                    execution_id=execution_id,
                    team_id=team_id,
                    team_name=f"Team {team_id}",
                    round_number=round_num,
                    submissions=submissions,
                )

                # Message History
                messages = cast(
                    list[ModelMessage], [ModelRequest(parts=[UserPromptPart(content=f"Prompt {round_num}")])]
                )

                # 保存（並列実行）
                await store.save_aggregation(execution_id, record, messages)

        # When: 10チーム並列実行 (simulating one orchestration execution)
        execution_id = str(uuid4())
        teams = [f"team-{i:03d}" for i in range(10)]
        tasks = [team_worker(tid, 5, execution_id) for tid in teams]
        await asyncio.gather(*tasks)

        # Then: 全50件（10×5）保存成功
        conn = store._get_connection()
        result = conn.execute("SELECT COUNT(*) FROM round_history").fetchone()
        assert result is not None
        count = result[0]
        assert count == 50

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_all_data_saved_successfully(self, store: AggregationStore) -> None:
        """全データ正常保存確認（SC-005）"""

        # Generate execution_id for this test run (simulating one orchestration execution)
        execution_id = str(uuid4())

        async def save_task(team_num: int, execution_id: str) -> bool:
            """保存タスク"""
            try:
                submissions = [
                    MemberSubmission(
                        agent_name="a",
                        agent_type="plain",
                        content="R",
                        status="SUCCESS",
                        usage=RunUsage(input_tokens=100, output_tokens=200, requests=1),
                    )
                ]
                record = MemberSubmissionsRecord(
                    execution_id=execution_id,
                    team_id=f"team-{team_num}",
                    team_name=f"Team {team_num}",
                    round_number=1,
                    submissions=submissions,
                )
                messages = cast(list[ModelMessage], [ModelRequest(parts=[UserPromptPart(content="P")])])
                await store.save_aggregation(execution_id, record, messages)
                return True
            except Exception:
                return False

        # When: 複数チーム並列保存
        results = await asyncio.gather(*[save_task(i, execution_id) for i in range(5)])

        # Then: 全て成功
        assert all(results), "Some parallel writes failed"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_mvcc_no_lock_contention(self, store: AggregationStore) -> None:
        """MVCC動作確認: ロック競合なし（FR-009）"""

        # Generate execution_id for this test run (simulating one orchestration execution)
        execution_id = str(uuid4())

        async def concurrent_save(team_id: str, execution_id: str) -> None:
            """同時保存"""
            submissions = [
                MemberSubmission(
                    agent_name="a",
                    agent_type="plain",
                    content="R",
                    status="SUCCESS",
                    usage=RunUsage(input_tokens=100, output_tokens=200, requests=1),
                )
            ]
            record = MemberSubmissionsRecord(
                execution_id=execution_id,
                team_id=team_id,
                team_name=f"Team {team_id}",
                round_number=1,
                submissions=submissions,
            )
            messages = cast(list[ModelMessage], [ModelRequest(parts=[UserPromptPart(content="P")])])
            await store.save_aggregation(execution_id, record, messages)

        # When: 同時保存（ロック競合が発生しないことを確認）
        teams = [f"team-{i}" for i in range(10)]
        await asyncio.gather(*[concurrent_save(tid, execution_id) for tid in teams])

        # Then: 全て保存成功（例外なし）
        conn = store._get_connection()
        result = conn.execute("SELECT COUNT(*) FROM round_history").fetchone()
        assert result is not None
        count = result[0]
        assert count == 10
