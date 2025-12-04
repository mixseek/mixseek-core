"""AggregationStore ユニットテスト

Test Coverage:
    - __init__: 環境変数チェック、テーブル作成
    - save_aggregation: 集約結果保存、リトライ
    - load_round_history: 履歴読み込み、Pydantic AI復元
    - save_to_leader_board: Leader Board保存
    - get_leader_board: ランキング取得

References:
    - Spec: specs/008-leader/spec.md (US2)
    - Contract: specs/008-leader/contracts/aggregation_store.md
"""

from pathlib import Path
from typing import cast

import pytest
from pydantic_ai import ModelMessage
from pydantic_ai.messages import ModelRequest, UserPromptPart

from mixseek.agents.leader.models import MemberSubmission, MemberSubmissionsRecord
from mixseek.exceptions import WorkspacePathNotSpecifiedError
from mixseek.storage.aggregation_store import AggregationStore


class TestAggregationStoreInit:
    """AggregationStore初期化テスト（T015）"""

    def test_init_with_env_variable(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """正常系: 環境変数から正常初期化"""
        # Given: MIXSEEK_WORKSPACE設定
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))

        # When: AggregationStore初期化
        store = AggregationStore()

        # Then: 正常に初期化される
        assert store.db_path == tmp_path / "mixseek.db"
        assert store.db_path.parent.exists()

    def test_init_env_variable_missing(
        self, monkeypatch: pytest.MonkeyPatch, isolate_from_project_dotenv: None
    ) -> None:
        """異常系: MIXSEEK_WORKSPACE未設定（FR-016, FR-20, Article 9準拠）"""
        # Given: 環境変数未設定
        monkeypatch.delenv("MIXSEEK_WORKSPACE", raising=False)
        monkeypatch.delenv("MIXSEEK_WORKSPACE_PATH", raising=False)

        # When/Then: WorkspacePathNotSpecifiedError送出（Article 9準拠）
        with pytest.raises(WorkspacePathNotSpecifiedError, match="MIXSEEK_WORKSPACE"):
            AggregationStore()

    def test_init_creates_tables(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """正常系: テーブル自動作成"""
        # Given: 環境変数設定
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))

        # When: 初期化
        store = AggregationStore()

        # Then: テーブルが作成される
        conn = store._get_connection()
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        table_names = [t[0] for t in tables]

        assert "round_history" in table_names
        assert "leader_board" in table_names


class TestSaveAggregation:
    """save_aggregation テスト（T016）"""

    @pytest.fixture
    def store(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> AggregationStore:
        """テスト用ストア"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
        return AggregationStore()

    @pytest.fixture
    def sample_aggregated(self) -> MemberSubmissionsRecord:
        """サンプル集約結果"""
        from pydantic_ai import RunUsage

        submissions = [
            MemberSubmission(
                agent_name="agent-1",
                agent_type="plain",
                content="Result 1",
                status="SUCCESS",
                usage=RunUsage(input_tokens=100, output_tokens=200, requests=1),
            ),
            MemberSubmission(
                agent_name="agent-2",
                agent_type="plain",
                content="Result 2",
                status="SUCCESS",
                usage=RunUsage(input_tokens=150, output_tokens=250, requests=1),
            ),
        ]
        return MemberSubmissionsRecord(
            execution_id="550e8400-e29b-41d4-a716-446655440000",
            team_id="team-001",
            team_name="Test Team",
            round_number=1,
            submissions=submissions,
        )

    @pytest.mark.asyncio
    async def test_save_aggregation_success(
        self, store: AggregationStore, sample_aggregated: MemberSubmissionsRecord
    ) -> None:
        """正常系: 集約結果保存（FR-006, FR-007）"""
        # Given: 集約結果とMessage History
        messages = cast(list[ModelMessage], [ModelRequest(parts=[UserPromptPart(content="Test prompt")])])

        # When: 保存
        await store.save_aggregation("550e8400-e29b-41d4-a716-446655440000", sample_aggregated, messages)

        # Then: DBに保存される
        conn = store._get_connection()
        result = conn.execute(
            "SELECT team_id, round_number FROM round_history WHERE team_id = ?", ["team-001"]
        ).fetchone()

        assert result is not None
        assert result[0] == "team-001"
        assert result[1] == 1

    @pytest.mark.asyncio
    async def test_save_unique_constraint(
        self, store: AggregationStore, sample_aggregated: MemberSubmissionsRecord
    ) -> None:
        """UNIQUE(team_id, round_number)検証（FR-008）"""
        # Given: 同じteam_id + round_numberで2回保存
        messages = cast(list[ModelMessage], [ModelRequest(parts=[UserPromptPart(content="Test")])])

        # When: 1回目保存
        await store.save_aggregation("550e8400-e29b-41d4-a716-446655440000", sample_aggregated, messages)

        # When: 2回目保存（同じキー）
        sample_aggregated.team_name = "Updated Team Name"
        await store.save_aggregation("550e8400-e29b-41d4-a716-446655440000", sample_aggregated, messages)

        # Then: UPSERT動作（上書き）
        conn = store._get_connection()
        result = conn.execute("SELECT COUNT(*) FROM round_history WHERE team_id = 'team-001'").fetchone()
        assert result is not None
        count = result[0]
        assert count == 1  # 1レコードのみ（上書き）


class TestLoadRoundHistory:
    """load_round_history テスト（T017）"""

    @pytest.fixture
    def store(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> AggregationStore:
        """テスト用ストア"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
        return AggregationStore()

    @pytest.mark.asyncio
    async def test_load_existing_record(self, store: AggregationStore) -> None:
        """正常系: 既存レコード読み込み"""
        from pydantic_ai import RunUsage

        # Given: 保存済みデータ
        submissions = [
            MemberSubmission(
                agent_name="a1",
                agent_type="plain",
                content="Data",
                status="SUCCESS",
                usage=RunUsage(input_tokens=100, output_tokens=200, requests=1),
            )
        ]
        aggregated = MemberSubmissionsRecord(
            execution_id="550e8400-e29b-41d4-a716-446655440000",
            team_id="team-001",
            team_name="Team",
            round_number=1,
            submissions=submissions,
        )
        messages = cast(list[ModelMessage], [ModelRequest(parts=[UserPromptPart(content="Prompt")])])
        await store.save_aggregation("550e8400-e29b-41d4-a716-446655440000", aggregated, messages)

        # When: 読み込み
        loaded_aggregated, loaded_messages = await store.load_round_history(
            "550e8400-e29b-41d4-a716-446655440000", "team-001", 1
        )

        # Then: 正しく復元される
        assert loaded_aggregated is not None
        assert loaded_aggregated.team_id == "team-001"
        assert loaded_aggregated.round_number == 1
        assert len(loaded_messages) == 1

    @pytest.mark.asyncio
    async def test_load_nonexistent_record(self, store: AggregationStore) -> None:
        """正常系: 未存在レコード読み込み"""
        # When: 存在しないレコード読み込み
        aggregated, messages = await store.load_round_history(
            "550e8400-e29b-41d4-a716-446655440000", "nonexistent", 999
        )

        # Then: (None, [])返却
        assert aggregated is None
        assert messages == []

    @pytest.mark.asyncio
    async def test_pydantic_ai_message_restoration(self, store: AggregationStore) -> None:
        """Pydantic AI Message完全復元（FR-012）"""
        from pydantic_ai import RunUsage

        # Given: Pydantic AIメッセージ保存
        original_messages = cast(list[ModelMessage], [ModelRequest(parts=[UserPromptPart(content="Original prompt")])])
        submissions = [
            MemberSubmission(
                agent_name="a1",
                agent_type="plain",
                content="R",
                status="SUCCESS",
                usage=RunUsage(input_tokens=100, output_tokens=200, requests=1),
            )
        ]
        aggregated = MemberSubmissionsRecord(
            execution_id="550e8400-e29b-41d4-a716-446655440000",
            team_id="team-001",
            team_name="Team",
            round_number=1,
            submissions=submissions,
        )
        await store.save_aggregation("550e8400-e29b-41d4-a716-446655440000", aggregated, original_messages)

        # When: 読み込み
        _, restored_messages = await store.load_round_history("550e8400-e29b-41d4-a716-446655440000", "team-001", 1)

        # Then: 完全復元（型チェック合格）
        assert len(restored_messages) == 1
        assert isinstance(restored_messages[0], ModelRequest)
        assert restored_messages[0].parts[0].content == "Original prompt"


class TestLeaderBoard:
    """Leader Boardテスト（US3の一部だがUS2で基本機能テスト）"""

    @pytest.fixture
    def store(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> AggregationStore:
        """テスト用ストア"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
        return AggregationStore()

    @pytest.mark.asyncio
    async def test_save_to_leader_board(self, store: AggregationStore) -> None:
        """正常系: Leader Board保存（FR-010）"""
        # When: Leader Board保存
        await store.save_to_leader_board(
            execution_id="550e8400-e29b-41d4-a716-446655440000",
            team_id="team-001",
            team_name="Team A",
            round_number=1,
            submission_content="Content here",
            submission_format="md",
            score=85.0,
            score_details={"overall_score": 85.0, "feedback": "Good work"},
        )

        # Then: DBに保存される（0-100 scale）
        conn = store._get_connection()
        result = conn.execute("SELECT team_name, score FROM leader_board").fetchone()

        assert result is not None
        assert result[0] == "Team A"
        assert result[1] == 85.0

    @pytest.mark.asyncio
    async def test_get_leader_board_ranking(self, store: AggregationStore) -> None:
        """ランキング取得: スコア降順ソート（FR-011）"""
        # Given: 3チーム保存（異なるスコア）
        await store.save_to_leader_board(
            execution_id="550e8400-e29b-41d4-a716-446655440000",
            team_id="t1",
            team_name="Team A",
            round_number=1,
            submission_content="Content A",
            submission_format="md",
            score=95.0,
            score_details={"overall_score": 95.0, "feedback": "Best"},
        )
        await store.save_to_leader_board(
            execution_id="550e8400-e29b-41d4-a716-446655440000",
            team_id="t2",
            team_name="Team B",
            round_number=1,
            submission_content="Content B",
            submission_format="md",
            score=75.0,
            score_details={"overall_score": 75.0, "feedback": "OK"},
        )
        await store.save_to_leader_board(
            execution_id="550e8400-e29b-41d4-a716-446655440000",
            team_id="t3",
            team_name="Team C",
            round_number=1,
            submission_content="Content C",
            submission_format="md",
            score=90.0,
            score_details={"overall_score": 90.0, "feedback": "Good"},
        )

        # When: Leader Board取得
        df = await store.get_leader_board(limit=10)

        # Then: スコア降順
        assert len(df) == 3
        assert df.iloc[0]["team_name"] == "Team A"  # 95.0
        assert df.iloc[1]["team_name"] == "Team C"  # 90.0
        assert df.iloc[2]["team_name"] == "Team B"  # 75.0

    @pytest.mark.asyncio
    async def test_get_leader_board_limit(self, store: AggregationStore) -> None:
        """limit動作（SC-007）"""
        # Given: 5チーム保存
        for i in range(5):
            await store.save_to_leader_board(
                execution_id="550e8400-e29b-41d4-a716-446655440000",
                team_id=f"t{i}",
                team_name=f"Team {i}",
                round_number=1,
                submission_content="Content",
                submission_format="md",
                score=80.0 + i * 1.0,
                score_details={"overall_score": 80.0 + i * 1.0, "feedback": "OK"},
            )

        # When: limit=3で取得
        df = await store.get_leader_board(limit=3)

        # Then: 3件のみ返却
        assert len(df) == 3

    @pytest.mark.asyncio
    async def test_save_to_leader_board_score_validation(self, store: AggregationStore) -> None:
        """異常系: score範囲外（契約違反、憲章Article 9）"""
        # When/Then: スコア < 0.0
        with pytest.raises(ValueError, match="must be between 0.0 and 100.0"):
            await store.save_to_leader_board(
                execution_id="550e8400-e29b-41d4-a716-446655440000",
                team_id="t1",
                team_name="Team",
                round_number=1,
                submission_content="content",
                submission_format="md",
                score=-0.1,
                score_details={"feedback": "feedback"},
            )

        # When/Then: スコア > 100.0
        with pytest.raises(ValueError, match="must be between 0.0 and 100.0"):
            await store.save_to_leader_board(
                execution_id="550e8400-e29b-41d4-a716-446655440000",
                team_id="t2",
                team_name="Team",
                round_number=1,
                submission_content="content",
                submission_format="md",
                score=150.0,
                score_details={"feedback": "feedback"},
            )

    @pytest.mark.asyncio
    async def test_get_leader_board_tie_breaker(self, store: AggregationStore) -> None:
        """同スコア時の2次ソート: 作成日時早い順（FR-011）"""
        # Given: 同スコア(85.0)の3チームを時間差で保存
        import asyncio

        await store.save_to_leader_board(
            execution_id="550e8400-e29b-41d4-a716-446655440000",
            team_id="t1",
            team_name="Team A",
            round_number=1,
            submission_content="Content A",
            submission_format="md",
            score=85.0,
            score_details={"overall_score": 85.0, "feedback": "OK"},
        )
        await asyncio.sleep(0.1)  # 時間差確保
        await store.save_to_leader_board(
            execution_id="550e8400-e29b-41d4-a716-446655440000",
            team_id="t2",
            team_name="Team B",
            round_number=1,
            submission_content="Content B",
            submission_format="md",
            score=85.0,
            score_details={"overall_score": 85.0, "feedback": "OK"},
        )
        await asyncio.sleep(0.1)
        await store.save_to_leader_board(
            execution_id="550e8400-e29b-41d4-a716-446655440000",
            team_id="t3",
            team_name="Team C",
            round_number=1,
            submission_content="Content C",
            submission_format="md",
            score=85.0,
            score_details={"overall_score": 85.0, "feedback": "OK"},
        )

        # When: Leader Board取得
        df = await store.get_leader_board(limit=10)

        # Then: 同スコアは作成日時早い順（0-100 scale）
        same_score_teams = df[df["score"] == 85.0]
        assert len(same_score_teams) == 3
        assert same_score_teams.iloc[0]["team_name"] == "Team A"  # 最初に保存
        assert same_score_teams.iloc[1]["team_name"] == "Team B"  # 2番目
        assert same_score_teams.iloc[2]["team_name"] == "Team C"  # 3番目


class TestRoundStatusTable:
    """T045: round_statusテーブルへの書き込みテスト（Feature 037）"""

    @pytest.fixture
    def store(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> AggregationStore:
        """テスト用ストア"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
        return AggregationStore()

    @pytest.mark.asyncio
    async def test_save_round_status(self, store: AggregationStore) -> None:
        """round_statusテーブルへの書き込みテスト"""
        from datetime import UTC, datetime

        # Given: Round status data
        execution_id = "test-exec-001"
        team_id = "team-001"
        team_name = "Test Team"
        round_number = 1
        should_continue = True
        reasoning = "Score is improving"
        confidence_score = 0.85
        round_started_at = datetime.now(UTC)
        round_ended_at = datetime.now(UTC)

        # When: Save to round_status table
        await store.save_round_status(
            execution_id=execution_id,
            team_id=team_id,
            team_name=team_name,
            round_number=round_number,
            should_continue=should_continue,
            reasoning=reasoning,
            confidence_score=confidence_score,
            round_started_at=round_started_at.isoformat(),
            round_ended_at=round_ended_at.isoformat(),
        )

        # Then: Verify record was saved
        conn = store._get_connection()
        result = conn.execute(
            """SELECT execution_id, team_id, round_number, should_continue,
                      reasoning, confidence_score
               FROM round_status
               WHERE execution_id = ? AND team_id = ?""",
            [execution_id, team_id],
        ).fetchone()

        assert result is not None
        assert result[0] == execution_id
        assert result[1] == team_id
        assert result[2] == round_number
        assert result[3] is True
        assert result[4] == reasoning
        assert pytest.approx(result[5]) == confidence_score  # Float comparison


class TestLeaderBoardTableNew:
    """T045: leader_boardテーブルへの書き込みテスト

    Feature 037 - new schema with execution_id, final_submission, exit_reason
    """

    @pytest.fixture
    def store(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> AggregationStore:
        """テスト用ストア"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
        return AggregationStore()

    @pytest.mark.asyncio
    async def test_save_to_new_leader_board(self, store: AggregationStore) -> None:
        """新leader_boardテーブルへの書き込みテスト（execution_id, final_submission, exit_reason含む）"""
        # Given: Leader board entry data
        execution_id = "exec-001"
        team_id = "team-001"
        team_name = "Test Team"
        round_number = 2
        submission_content = "Test submission"
        score = 85.0
        score_details = {"metric1": 85.0, "comment": "Good work"}
        final_submission = True
        exit_reason = "max rounds reached"

        # When: Save to leader_board table
        await store.save_to_leader_board(
            execution_id=execution_id,
            team_id=team_id,
            team_name=team_name,
            round_number=round_number,
            submission_content=submission_content,
            submission_format="md",
            score=score,
            score_details=score_details,
            final_submission=final_submission,
            exit_reason=exit_reason,
        )

        # Then: Verify record was saved
        conn = store._get_connection()
        result = conn.execute(
            """SELECT execution_id, team_id, round_number, score,
                      final_submission, exit_reason
               FROM leader_board
               WHERE execution_id = ? AND team_id = ?""",
            [execution_id, team_id],
        ).fetchone()

        assert result is not None
        assert result[0] == execution_id
        assert result[1] == team_id
        assert result[2] == round_number
        assert result[3] == 85.0
        assert result[4] is True
        assert result[5] == exit_reason

    @pytest.mark.asyncio
    async def test_get_ranking_by_execution(self, store: AggregationStore) -> None:
        """T052: execution_id でランキングを取得するテスト"""
        # Given: Multiple teams with different scores
        execution_id = "exec-001"
        await store.save_to_leader_board(
            execution_id=execution_id,
            team_id="team-a",
            team_name="Team A",
            round_number=1,
            submission_content="Submission A",
            submission_format="md",
            score=95.0,
            score_details={},
        )
        await store.save_to_leader_board(
            execution_id=execution_id,
            team_id="team-b",
            team_name="Team B",
            round_number=1,
            submission_content="Submission B",
            submission_format="md",
            score=80.0,
            score_details={},
        )
        await store.save_to_leader_board(
            execution_id=execution_id,
            team_id="team-c",
            team_name="Team C",
            round_number=1,
            submission_content="Submission C",
            submission_format="md",
            score=90.0,
            score_details={},
        )

        # When: Get ranking by execution_id (using get_leader_board_ranking)
        ranking = await store.get_leader_board_ranking(execution_id=execution_id)

        # Then: Results are sorted by score DESC
        assert len(ranking) == 3
        assert ranking[0]["team_id"] == "team-a"
        assert ranking[0]["max_score"] == 95.0
        assert ranking[1]["team_id"] == "team-c"
        assert ranking[1]["max_score"] == 90.0
        assert ranking[2]["team_id"] == "team-b"
        assert ranking[2]["max_score"] == 80.0


class TestTeamStatistics:
    """チーム統計テスト（T027 - US3）"""

    @pytest.fixture
    def store(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> AggregationStore:
        """テスト用ストア"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
        return AggregationStore()

    @pytest.mark.asyncio
    async def test_get_team_statistics(self, store: AggregationStore) -> None:
        """JSON内部クエリで統計集計（FR-013）"""
        # Given: 複数ラウンドのLeader Boardデータ
        for round_num in range(1, 4):
            score = (0.8 + round_num * 0.05) * 100.0  # Convert to 0-100 scale
            await store.save_to_leader_board(
                execution_id="550e8400-e29b-41d4-a716-446655440000",
                team_id="team-001",
                team_name="Team A",
                round_number=round_num,
                submission_content="Content",
                submission_format="md",
                score=score,
                score_details={"overall_score": score, "feedback": "OK"},
            )

        # When: チーム統計取得
        stats = await store.get_team_statistics("team-001")

        # Then: 統計が正しく集計される（Feature 037: 0-100 scale）
        assert stats["total_rounds"] == 3
        assert stats["avg_score"] == pytest.approx(90.0)  # (85 + 90 + 95) / 3
        assert stats["best_score"] == pytest.approx(95.0)  # 0.95 * 100 = 95.0
        # Note: usage_info is no longer stored in score_details, so tokens will be 0
        assert stats["total_input_tokens"] == 0
        assert stats["total_output_tokens"] == 0

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_statistics_large_dataset(self, store: AggregationStore) -> None:
        """大量データの統計集計性能（SC-003）"""
        # NOTE: 100万行のテストは時間がかかるため、
        # 実際の実装では@pytest.mark.performanceマーカーを付けて
        # 通常のCIからは除外することを推奨
        #
        # このテストは実装完了後、性能検証として実行
        pytest.skip("Performance test - run manually with @pytest.mark.performance")
