"""AggregationStore のテスト

Article 3: Test-First Imperative準拠

DuckDB並列書き込み、Message History永続化、リトライロジックのテスト。

Tests:
    - save_aggregation: Message History + MemberSubmissionsRecord保存
    - load_round_history: データ読み込みと復元
    - エクスポネンシャルバックオフリトライ
    - 環境変数MIXSEEK_WORKSPACE
"""

import os
import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic_ai import RunUsage
from pydantic_ai.messages import ModelRequest, ModelResponse

from mixseek.agents.leader.models import MemberSubmission, MemberSubmissionsRecord
from mixseek.storage.aggregation_store import AggregationStore, DatabaseWriteError


class TestAggregationStore:
    """AggregationStore基本機能テスト（T023-T024, T026-T027）"""

    @pytest.fixture
    def test_workspace(self) -> Generator[Path]:
        """テスト用ワークスペース"""
        tmpdir = tempfile.mkdtemp()
        workspace = Path(tmpdir)

        # 環境変数設定
        original_workspace = os.environ.get("MIXSEEK_WORKSPACE")
        os.environ["MIXSEEK_WORKSPACE"] = str(workspace)

        yield workspace

        # クリーンアップ
        if original_workspace:
            os.environ["MIXSEEK_WORKSPACE"] = original_workspace
        else:
            del os.environ["MIXSEEK_WORKSPACE"]

        # ディレクトリ全体削除
        shutil.rmtree(workspace, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_save_and_load_round_history(self, test_workspace: Path) -> None:
        """save_aggregation + load_round_history（FR-006, FR-007, FR-007-1）

        単一トランザクションでMessage History + MemberSubmissionsRecordを保存。
        """
        # Arrange
        store = AggregationStore()
        execution_id = str(uuid4())

        record = MemberSubmissionsRecord(
            execution_id=execution_id,
            team_id="team-001",
            team_name="Test Team",
            round_number=1,
            submissions=[
                MemberSubmission(
                    agent_name="analyst",
                    agent_type="plain",
                    content="分析結果",
                    status="SUCCESS",
                    usage=RunUsage(input_tokens=100, output_tokens=200, requests=1),
                )
            ],
        )

        # Message History（空リストでテスト、実際のAgent実行結果は別途E2Eで確認）
        messages: list[ModelRequest | ModelResponse] = []

        # Act: 保存
        await store.save_aggregation(execution_id, record, messages)

        # Act: 読み込み
        loaded_record, loaded_messages = await store.load_round_history(execution_id, "team-001", 1)

        # Assert
        assert loaded_record is not None
        assert loaded_record.team_id == "team-001"
        assert loaded_record.round_number == 1
        assert len(loaded_record.submissions) == 1
        assert loaded_record.submissions[0].agent_name == "analyst"

        # Message History完全復元（FR-012）
        assert loaded_messages == []  # 空リストで保存したので空リスト

    @pytest.mark.asyncio
    async def test_unique_constraint_upsert(self, test_workspace: Path) -> None:
        """UNIQUE制約（execution_id + team_id + round_number）とUPSERT（Edge Case）"""
        # Arrange
        store = AggregationStore()
        execution_id = str(uuid4())

        record1 = MemberSubmissionsRecord(
            execution_id=execution_id,
            team_id="team-001",
            team_name="Team A",
            round_number=1,
            submissions=[
                MemberSubmission(
                    agent_name="analyst",
                    agent_type="plain",
                    content="初回",
                    status="SUCCESS",
                    usage=RunUsage(input_tokens=100, output_tokens=200, requests=1),
                )
            ],
        )

        messages1: list[ModelRequest | ModelResponse] = []

        # Act: 1回目保存
        await store.save_aggregation(execution_id, record1, messages1)

        # 同じexecution_id + team_id + round_numberで2回目保存（UPSERT）
        record2 = MemberSubmissionsRecord(
            execution_id=execution_id,
            team_id="team-001",
            team_name="Team A",
            round_number=1,
            submissions=[
                MemberSubmission(
                    agent_name="summarizer",
                    agent_type="plain",
                    content="更新",
                    status="SUCCESS",
                    usage=RunUsage(input_tokens=50, output_tokens=100, requests=1),
                )
            ],
        )

        messages2: list[ModelRequest | ModelResponse] = []

        # 2回目保存（UPSERT、エラーなし）
        await store.save_aggregation(execution_id, record2, messages2)

        # Assert: 最新データが保存されている
        loaded_record, _ = await store.load_round_history(execution_id, "team-001", 1)
        assert loaded_record is not None
        assert loaded_record.submissions[0].content == "更新"  # 上書きされている

    @pytest.mark.asyncio
    async def test_load_nonexistent_record(self, test_workspace: Path) -> None:
        """存在しないレコード読み込み（None返却）"""
        # Arrange
        store = AggregationStore()
        execution_id = str(uuid4())

        # Act
        loaded_record, loaded_messages = await store.load_round_history(execution_id, "nonexistent", 999)

        # Assert
        assert loaded_record is None
        assert loaded_messages == []

    @pytest.mark.asyncio
    async def test_environment_variable_not_set(
        self, monkeypatch: pytest.MonkeyPatch, isolate_from_project_dotenv: None
    ) -> None:
        """環境変数MIXSEEK_WORKSPACE未設定エラー（FR-016、Edge Case、Article 9準拠）"""
        # Arrange: 環境変数削除
        monkeypatch.delenv("MIXSEEK_WORKSPACE", raising=False)
        monkeypatch.delenv("MIXSEEK_WORKSPACE_PATH", raising=False)

        # Act & Assert: Article 9準拠でWorkspacePathNotSpecifiedErrorまたはExceptionを期待
        with pytest.raises(Exception) as exc_info:
            AggregationStore()

        # エラーメッセージに設定例含む
        assert "MIXSEEK_WORKSPACE" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_exponential_backoff_retry(self, test_workspace: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """エクスポネンシャルバックオフリトライ（FR-019）

        1秒、2秒、4秒のリトライ、最大3回。
        """
        # Arrange
        store = AggregationStore()
        execution_id = str(uuid4())

        record = MemberSubmissionsRecord(
            execution_id=execution_id,
            team_id="team-001",
            team_name="Team A",
            round_number=1,
            submissions=[],
        )
        messages: list[ModelRequest | ModelResponse] = []

        # _save_syncを一時的に失敗させる（モック）
        call_count = 0
        original_save = store._save_sync

        def failing_save(
            execution_id: str, record: MemberSubmissionsRecord, messages: list[ModelRequest | ModelResponse]
        ) -> None:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            # 3回目は成功
            return original_save(execution_id, record, messages)

        monkeypatch.setattr(store, "_save_sync", failing_save)

        # Act: リトライで最終的に成功
        await store.save_aggregation(execution_id, record, messages)

        # Assert: 3回呼び出された
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, test_workspace: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """最大リトライ回数超過後エラー（FR-019）"""
        # Arrange
        store = AggregationStore()
        execution_id = str(uuid4())

        record = MemberSubmissionsRecord(
            execution_id=execution_id,
            team_id="team-001",
            team_name="Team A",
            round_number=1,
            submissions=[],
        )
        messages: list[ModelRequest | ModelResponse] = []

        # _save_syncを常に失敗させる
        def always_fail(*args: object, **kwargs: object) -> None:
            raise Exception("Permanent failure")

        monkeypatch.setattr(store, "_save_sync", always_fail)

        # Act & Assert: 3回リトライ後にDatabaseWriteError
        with pytest.raises(DatabaseWriteError) as exc_info:
            await store.save_aggregation(execution_id, record, messages)

        assert "Failed to save after 3 retries" in str(exc_info.value)
