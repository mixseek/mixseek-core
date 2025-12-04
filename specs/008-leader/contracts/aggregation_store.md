# Contract: AggregationStore API

**Date**: 2025-10-22
**Feature**: 026-mixseek-core-leader
**Type**: Python API Contract

## Overview

`AggregationStore`はLeader AgentのMember Agent応答集約結果とMessage HistoryをDuckDBに永続化するストアクラスです。MVCC方式により複数チーム並列書き込みをサポートします。

---

## Class Interface

### AggregationStore

```python
from pathlib import Path
from typing import Optional
from pydantic_ai import ModelMessage

class AggregationStore:
    """DuckDB並列書き込み対応ストア

    DuckDB Python APIは同期のみのため、asyncio.to_threadで
    スレッドプールに退避して非同期実行を実現。
    スレッドローカルコネクションにより、各チームが独立した
    コネクションを使用してMVCC並列書き込みを実現。
    """

    def __init__(self, db_path: Optional[Path] = None) -> None:
        """初期化

        Args:
            db_path: データベースファイルパス
                    Noneの場合は$MIXSEEK_WORKSPACE/mixseek.dbを使用

        Raises:
            OSError: MIXSEEK_WORKSPACE未設定時（憲章Article 9）
            PermissionError: DBファイル作成権限なし

        Note:
            スレッドローカルコネクション管理により、asyncio.gatherでの
            並列呼び出し時も各スレッドが独立したコネクションを使用。
        """
        ...

    async def save_aggregation(
        self,
        aggregated: AggregatedMemberSubmissions,
        message_history: list[ModelMessage]
    ) -> None:
        """集約結果とMessage Historyを保存 (FR-006, FR-007)

        複数Leader Agentから同時呼び出しされても安全（ロックフリー）。
        DuckDB同期APIをasyncio.to_threadでスレッドプールに退避し、
        真の非同期並列実行を実現。

        Args:
            aggregated: 集約されたMember Agent応答
            message_history: Pydantic AI Message History

        Raises:
            DatabaseWriteError: 書き込み失敗（3回リトライ後）
            ValidationError: データ検証失敗

        Implementation:
            内部で_save_sync()をasyncio.to_threadで実行。
            スレッドローカルコネクションにより、各チームが
            独立したDuckDBコネクションを使用。
        """
        ...

    async def save_to_leader_board(
        self,
        team_id: str,
        team_name: str,
        round_number: int,
        evaluation_score: float,
        evaluation_feedback: str,
        submission: str,
        usage_info: Optional[dict[str, int]] = None
    ) -> None:
        """Leader Boardに保存 (FR-010)

        複数チームから並列書き込み可能（ロックフリー）。

        Args:
            team_id: チームID
            team_name: チーム名
            round_number: ラウンド番号
            evaluation_score: 評価スコア (0.0-1.0)
            evaluation_feedback: 評価フィードバック
            submission: Submission内容（aggregated_content）
            usage_info: リソース使用量（optional）

        Raises:
            DatabaseWriteError: 書き込み失敗
            ValueError: パラメータ検証失敗
        """
        ...

    async def load_round_history(
        self,
        team_id: str,
        round_number: int
    ) -> tuple[Optional[AggregatedMemberSubmissions], list[ModelMessage]]:
        """ラウンド履歴を読み込み (FR-012)

        Args:
            team_id: チームID
            round_number: ラウンド番号

        Returns:
            (集約結果, Message History)のタプル
            レコード未存在時は(None, [])

        Raises:
            DatabaseReadError: 読み込み失敗
            ValidationError: JSON復元失敗
        """
        ...

    async def get_leader_board(
        self,
        limit: int = 10
    ) -> pd.DataFrame:
        """Leader Board取得 (FR-011)

        スコア降順、同スコアは作成日時早い順でソート。

        Args:
            limit: 取得件数

        Returns:
            Pandas DataFrame (columns: team_name, round_number,
                                      evaluation_score, created_at)

        Raises:
            DatabaseReadError: 読み込み失敗
        """
        ...

```

---

## Method Contracts

### save_aggregation()

**Preconditions**:
- `aggregated.team_id`: 非空文字列
- `aggregated.round_number`: >=1
- `message_history`: 空リスト可（Round 1）

**Postconditions**:
- `round_history`テーブルに1レコード挿入
- 既存レコード（同team_id + round_number）はUPSERT
- トランザクションコミット成功

**Invariants**:
- UNIQUE(team_id, round_number)制約維持
- JSON型検証合格（DuckDB側）

**Error Handling** (FR-020, FR-021):
- 1回目失敗: 1秒待機してリトライ
- 2回目失敗: 2秒待機してリトライ
- 3回目失敗: 4秒待機してリトライ
- 全失敗: `DatabaseWriteError`送出（即終了、詳細ログ）

---

### load_round_history()

**Preconditions**:
- `team_id`: 非空文字列
- `round_number`: >=1

**Postconditions**:
- レコード存在時: (AggregatedMemberSubmissions, list[ModelMessage])
- レコード未存在時: (None, [])

**Invariants**:
- 返却されたMessage HistoryはPydantic AI型として検証済み
- ValidationError発生時は即エラー（フォールバック禁止）

---

### get_leader_board()

**Preconditions**:
- `limit`: >0

**Postconditions**:
- Pandas DataFrame返却
- ソート順: `ORDER BY evaluation_score DESC, created_at ASC` (FR-011)

**Performance** (SC-003):
- 100万行: <1秒

---

## Concurrency Contract

### MVCC並列書き込み (FR-009)

**Guarantees**:
- 複数`save_aggregation()`の同時呼び出し: ロック待機なし
- トランザクション分離レベル: Snapshot Isolation
- データ一貫性: ACID保証

**Test Scenario** (FR-014):
```python
# 10チーム並列書き込み
tasks = [
    store.save_aggregation(team_i_data)
    for i in range(10)
]
await asyncio.gather(*tasks)  # 全て並列実行、ロック競合なし
```

**Expected Behavior**:
- 全トランザクション成功
- 合計10レコード挿入
- 実行時間: <2秒

---

## Exception Hierarchy

```python
class MixSeekStorageError(Exception):
    """ストレージ基底例外"""

class DatabaseWriteError(MixSeekStorageError):
    """書き込み失敗（3回リトライ後）"""

class DatabaseReadError(MixSeekStorageError):
    """読み込み失敗"""

class ExportError(MixSeekStorageError):
    """Parquetエクスポート失敗"""
```

**Error Propagation** (憲章Article 9):
- ❌ 例外キャッチ後のサイレント継続禁止
- ✅ 詳細コンテキスト付きで再送出
- ✅ ログ出力（パス、権限、エラー詳細）

---

## Testing Contract

### Unit Tests

```python
class TestAggregationStore:
    """AggregationStoreユニットテスト"""

    async def test_save_aggregation_success(self) -> None:
        """正常系: 集約結果保存"""
        # Given: 集約結果とMessage History
        # When: save_aggregation()呼び出し
        # Then: DBに保存、エラーなし

    async def test_load_round_history_existing(self) -> None:
        """正常系: 既存履歴読み込み"""
        # Given: DB内にレコード存在
        # When: load_round_history()呼び出し
        # Then: 正しく復元、Pydantic AI型チェック合格

    async def test_environment_variable_missing(self) -> None:
        """異常系: MIXSEEK_WORKSPACE未設定"""
        # Given: 環境変数未設定
        # When: __init__()呼び出し
        # Then: EnvironmentError送出
```

### Integration Tests

```python
class TestConcurrentWrites:
    """並列書き込みインテグレーションテスト (FR-014)"""

    async def test_10_teams_parallel_writes(self) -> None:
        """10チーム並列書き込み"""
        # Given: 10チーム
        # When: 各チームが同時にsave_aggregation()
        # Then: 全50件（10×5ラウンド）成功、ロック競合なし
```

---

## References

- **仕様書**: `specs/008-leader/spec.md` (FR-006〜FR-021)
- **データモデル**: `specs/008-leader/data-model.md`
- **憲章**: `.specify/memory/constitution.md` (Article 9, Article 16)
