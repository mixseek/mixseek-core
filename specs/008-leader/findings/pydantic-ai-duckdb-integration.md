# Findings: Pydantic AI + DuckDB統合の実装知見

**Date**: 2025-10-22
**Feature**: 026-mixseek-core-leader
**Context**: Leader Agent実装（Phase 1-9）で得られた技術的知見

## Overview

Leader Agent実装を通じて、Pydantic AIのMessage HistoryをDuckDBに永続化し、asyncio環境で並列書き込みを実現する過程で得られた重要な知見をまとめます。

---

## Finding 1: Pydantic AI Message Historyの完全永続化

### 発見

Pydantic AIの複雑なネストしたMessage構造を、DuckDBのJSON型で**完全に保存・復元**できる。

### 実装パターン

```python
from pydantic_core import to_jsonable_python
from pydantic_ai import ModelMessage
from pydantic_ai.messages import ModelMessagesTypeAdapter
import json

# 保存（Pydantic AI → JSON → DuckDB）
messages: list[ModelMessage] = agent.run(...).all_messages()
messages_dict = to_jsonable_python(messages)
json_str = json.dumps(messages_dict)

conn.execute("""
    INSERT INTO round_history (message_history)
    VALUES (?)
""", [json_str])

# 復元（DuckDB → JSON → Pydantic AI）
result = conn.execute("SELECT message_history FROM round_history").fetchone()
restored_messages = ModelMessagesTypeAdapter.validate_json(result[0])

# 完全復元確認
assert isinstance(restored_messages[0], ModelRequest)
assert restored_messages[0].parts[0].content == original_content
```

### 重要なポイント

1. **DuckDB JSON型の活用**:
   - `message_history JSON` カラムでネスト構造をそのまま保存
   - TEXT型よりもJSON型推奨（クエリ可能性）

2. **型安全な復元**:
   - `ModelMessagesTypeAdapter.validate_json()` で型チェック付き復元
   - ValidationError発生時は即座にエラー検出

3. **完全性保証**:
   - ModelRequest/ModelResponseの構造を完全保持
   - timestamp, usage情報も含めて全て復元可能

### 参考リソース

- `draft/references/pydantic-ai-docs/message-history.md`: 公式ガイド
- `src/mixseek/storage/aggregation_store.py:355-390`: 実装例

---

## Finding 2: DuckDB同期APIの非同期ラッパー戦略

### 課題

DuckDB Python APIは**同期のみ**。async defで定義しても、実際にはイベントループをブロックする。

```python
# ❌ これは実際にブロッキングする
async def save_data(self, data):
    conn = duckdb.connect("db.duckdb")
    conn.execute("INSERT ...")  # ← ここでブロック
```

### 解決策: asyncio.to_thread + スレッドローカルコネクション

```python
import asyncio
import threading
import duckdb

class AggregationStore:
    def __init__(self):
        self._local = threading.local()  # スレッドローカル変数

    def _get_connection(self) -> duckdb.DuckDBPyConnection:
        """スレッドローカルコネクション取得"""
        if not hasattr(self._local, 'conn'):
            self._local.conn = duckdb.connect(str(self.db_path))
        return self._local.conn

    def _save_sync(self, data):
        """同期保存処理（スレッドプールで実行）"""
        conn = self._get_connection()
        conn.execute("INSERT ...")

    async def save_aggregation(self, data):
        """非同期保存（asyncio.to_threadでラップ）"""
        await asyncio.to_thread(self._save_sync, data)
```

### これにより実現できること

1. **真の並列実行**:
```python
# 10チーム並列書き込み（ロック待機なし）
tasks = [store.save_aggregation(team_i_data) for i in range(10)]
await asyncio.gather(*tasks)  # 全て並列実行
```

2. **MVCC並列制御**:
   - 各スレッドが独立したDuckDBコネクション使用
   - スナップショット分離によりロック競合なし

3. **パフォーマンス**:
   - ベンチマーク: 10チーム並列で約1.5秒（50件保存）
   - スレッドプール活用でCPU効率的

### 注意点

- **スレッドローカル変数必須**: `threading.local()` でコネクション管理
- **同期版メソッド分離**: `_save_sync()` と `async save_aggregation()` を分ける
- **型チェック**: `cast(duckdb.DuckDBPyConnection, ...)` で型安全性確保

### 参考リソース

- `specs/008-leader/research.md` (R5): 非同期戦略詳細
- `specs/008-leader/feedbacks/2025-10-22-plan-review.md`: Codex指摘
- `src/mixseek/storage/aggregation_store.py:106-118`: 実装例

---

## Finding 3: Pydantic computed_fieldによるTUMIX準拠実装

### 発見

Pydantic v2の`@computed_field`を使うことで、TUMIX論文のメッセージ共有方式を**宣言的に**実装できる。

### 実装パターン

```python
from pydantic import BaseModel, Field, computed_field

class AggregatedMemberSubmissions(BaseModel):
    successful_submissions: list[MemberSubmission] = Field(...)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def aggregated_content(self) -> str:
        """TUMIX形式で整形・連結されたコンテンツ

        全Member応答をAgent名ラベル付きで連結。
        このコンテンツがSubmission.contentに格納され、
        次ラウンドで全Member Agentに共有される。
        """
        if not self.successful_submissions:
            return "(成功したMember Agent応答がありません)"

        sections = []
        for submission in self.successful_submissions:
            section = (
                f"## {submission.agent_name} の応答:\n\n"
                f"{submission.content.strip()}\n"
            )
            sections.append(section)

        return "\n---\n\n".join(sections)
```

### TUMIX論文との対応

**TUMIX論文（Section 3.2）**:
> "In each round, every agent independently generates a new solution by considering both the original question and the solutions provided by all agents in the previous round"

**実装での実現**:
```
Round 1:
  各Member Agent → オリジナルプロンプト
  Leader Agent → aggregated_content生成
    ↓
  Submission.content = aggregated_content
    ↓
  ## data-analyst の応答:
  データ分析結果...

  ---

  ## web-searcher の応答:
  検索結果...

Round 2以降:
  各Member Agent → オリジナルプロンプト
                    + 前Submission（全Member応答含む）
                    + 評価フィードバック
```

**結果**: TUMIX論文と同等のメッセージ共有

### computed_fieldの利点

1. **動的計算**: アクセス時に常に最新の連結コンテンツを生成
2. **型安全**: Pydantic検証対象
3. **シリアライズ可能**: `model_dump()`でJSON出力可能
4. **宣言的**: ビジネスロジックが明確

### 注意点

```python
# mypy strict modeでwarning回避
@computed_field  # type: ignore[prop-decorator]
@property
def aggregated_content(self) -> str:
    ...
```

### 参考リソース

- `draft/references/thesis/2510.01279v1.md` (Section 3.2): TUMIX論文
- `src/mixseek/models/leader_agent.py:142-169`: 実装例
- `specs/008-leader/spec.md` (Clarifications): TUMIX準拠の確認

---

## Finding 4: DuckDB IDENTITY列の必須性

### 課題

SQLiteからの移行時に見落としやすい罠：DuckDBでは`INTEGER PRIMARY KEY`だけでは自動採番されない。

### SQLiteとの違い

```sql
-- SQLite: これで自動採番される
CREATE TABLE test (
    id INTEGER PRIMARY KEY,  -- 自動的にAUTOINCREMENT
    data TEXT
)

-- DuckDB: これはエラーになる
CREATE TABLE test (
    id INTEGER PRIMARY KEY,  -- 自動採番されない！
    data TEXT
)

INSERT INTO test (data) VALUES ('test');
-- エラー: BinderException: Column with no default not referenced in INSERT
```

### 正しいDuckDB実装

```sql
-- DuckDB: IDENTITY句が必須
CREATE TABLE test (
    id INTEGER PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
    data TEXT
)

INSERT INTO test (data) VALUES ('test');  -- ✅ 成功
```

### 実装への影響

```python
# 両テーブルでIDENTITY必須
conn.execute("""
    CREATE TABLE IF NOT EXISTS round_history (
        id INTEGER PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
        ...
    )
""")

conn.execute("""
    CREATE TABLE IF NOT EXISTS leader_board (
        id INTEGER PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
        ...
    )
""")
```

### 教訓

- DuckDBはSQLiteと**完全互換ではない**
- 主キー自動採番は明示的に`GENERATED ... AS IDENTITY`
- 既存SQLiteコードの移行時は要注意

### 参考リソース

- `specs/008-leader/feedbacks/2025-10-22-phase1-4-implementation-review.md`: Codex指摘
- `src/mixseek/storage/aggregation_store.py:148-192`: 修正後の実装

---

## Finding 5: 型安全性とcast()の実践的使用

### 課題

Pydantic AIの`list[ModelMessage]`型は、`list[ModelRequest]`と互換性がない（invariant）。

```python
# ❌ mypy error: list is invariant
messages: list[ModelMessage] = [
    ModelRequest(parts=[UserPromptPart(content="test")])
]

# エラー: Argument has incompatible type "list[ModelRequest]";
#        expected "list[ModelRequest | ModelResponse]"
```

### 解決策: cast()による明示的型宣言

```python
from typing import cast
from pydantic_ai import ModelMessage
from pydantic_ai.messages import ModelRequest, UserPromptPart

# ✅ cast()で明示的に型を宣言
messages = cast(
    list[ModelMessage],
    [ModelRequest(parts=[UserPromptPart(content="test")])]
)

# これで型チェック通過
await store.save_aggregation(aggregated, messages)
```

### Sequenceを使う代替案（推奨）

```python
from collections.abc import Sequence

async def save_aggregation(
    self,
    aggregated: AggregatedMemberSubmissions,
    message_history: Sequence[ModelMessage]  # Sequenceはcovariant
) -> None:
    ...
```

**ただし**: Pydantic AIのシグネチャに合わせるため、本実装ではcast()を使用。

### 適用箇所

全テストファイルで使用：
- `tests/unit/storage/test_aggregation_store.py`: 5箇所
- `tests/integration/test_concurrent_writes.py`: 3箇所
- `tests/integration/test_end_to_end.py`: 2箇所
- `src/mixseek/cli/commands/team.py`: 1箇所

### 教訓

- **list型はinvariant**: サブタイプのリストは親タイプのリストに代入不可
- **cast()で回避**: テストコードでは実用的
- **Sequence検討**: ライブラリAPIではcovariantなSequence推奨

### 参考リソース

- mypy documentation: https://mypy.readthedocs.io/en/stable/common_issues.html#variance
- `src/mixseek/cli/commands/team.py:206`: 実装例

---

## Finding 6: DuckDBのCHECK制約による二重防御

### 発見

データ整合性は**アプリケーション層とデータベース層の二重で**保護すべき。

### 実装パターン

#### Layer 1: アプリケーション層バリデーション

```python
def _save_to_leader_board_sync(
    self,
    evaluation_score: float,
    ...
) -> None:
    """Leader Board保存（同期版）"""
    # Pythonレベル検証（憲章Article 9準拠）
    if not 0.0 <= evaluation_score <= 1.0:
        raise ValueError(
            f"evaluation_score must be between 0.0 and 1.0, got {evaluation_score}. "
            "This violates the contract specification."
        )

    conn.execute("INSERT INTO leader_board ...")
```

#### Layer 2: データベース層制約

```sql
CREATE TABLE leader_board (
    id INTEGER PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,

    -- DB level validation
    evaluation_score DOUBLE NOT NULL
        CHECK (evaluation_score >= 0.0 AND evaluation_score <= 1.0),

    ...
)
```

### 二重防御の利点

1. **早期検出**: Pythonバリデーションで即座にエラー
2. **最終防衛**: 万が一の場合もDB制約で防御
3. **自己文書化**: スキーマ自体が制約を明示
4. **外部アクセス保護**: 直接SQL実行でも制約有効

### 教訓

- **憲章Article 9準拠**: アプリレベルバリデーション必須
- **Defense in Depth**: DB制約で二重防御
- **契約準拠**: 契約で定義された範囲を両層で保証

### 参考リソース

- `specs/008-leader/feedbacks/20251022-gemini-review-phase5-impl.md`: Gemini提案
- `src/mixseek/storage/aggregation_store.py:179`: CHECK制約
- `src/mixseek/storage/aggregation_store.py:293`: アプリ検証

---

## Finding 7: ParquetエクスポートとJSON型の扱い

### 発見

DuckDBからParquetエクスポート時、JSON型カラムは**STRING型として保存**される（表形式に自動展開されない）。

### 動作の詳細

```sql
-- テーブル（JSON型）
CREATE TABLE round_history (
    id INTEGER,
    message_history JSON  -- ネストしたJSON構造
)

-- Parquetエクスポート
COPY (SELECT * FROM round_history)
TO 'output.parquet'
(FORMAT PARQUET, COMPRESSION ZSTD)

-- Parquetファイル内の構造:
-- id | message_history
-- 1  | "[{\"kind\":\"request\",...}]"  ← STRING型（JSON文字列）
```

### Parquetからのクエリ方法

```sql
-- ✅ Option 1: CASTでJSON型に変換
SELECT
    CAST(message_history AS JSON)->0->>'kind' as message_kind
FROM 'archive/2025-10-22/history.parquet'

-- ✅ Option 2: json_extract()関数使用
SELECT
    json_extract(message_history, '$[0].kind')
FROM 'archive/2025-10-22/history.parquet'

-- ❌ これは動作しない（STRING型のまま）
SELECT
    message_history->0->>'kind'  -- エラー: JSON演算子使えない
FROM 'archive/2025-10-22/history.parquet'
```

### Orchestration Layer実装への示唆

```python
# Parquetエクスポート（Orchestration Layer責務）
conn.execute("""
    COPY (SELECT * FROM round_history)
    TO 'archive/2025-10-22/history.parquet'
    (FORMAT PARQUET, COMPRESSION ZSTD, APPEND true)
""")

# アーカイブデータ分析
result = conn.execute("""
    SELECT
        team_name,
        CAST(message_history AS JSON)[0].parts[0].content as first_prompt
    FROM 'archive/*/history.parquet'
    WHERE CAST(message_history AS JSON)[0]->>'kind' = 'request'
""").df()
```

### 教訓

- JSON型 → Parquet: **STRING型として保存**
- クエリ時: **CAST必須**またはjson_extract()
- 自動展開なし: 明示的なフラット化が必要な場合は別途クエリ

### 参考リソース

- `specs/008-leader/spec.md` (Clarifications): Parquet JSON型の扱い
- DuckDB Parquet: https://duckdb.org/docs/data/parquet/overview
- DuckDB JSON Functions: https://duckdb.org/docs/extensions/json

---

## Finding 8: 環境変数必須化と憲章Article 9の実践

### 憲章Article 9の要求

**禁止事項**:
- ❌ デフォルト値（`~/.mixseek`）提供
- ❌ 暗黙的フォールバック
- ❌ ハードコードパス

### 実装パターン

```python
import os
from pathlib import Path

def _get_db_path(self, db_path: Path | None) -> Path:
    """データベースファイルパス取得"""
    if db_path is not None:
        return db_path

    # 環境変数必須（憲章Article 9: デフォルト値禁止）
    if "MIXSEEK_WORKSPACE" not in os.environ:
        raise EnvironmentError(
            "MIXSEEK_WORKSPACE environment variable is not set.\n"
            "Please set it: export MIXSEEK_WORKSPACE=/path/to/workspace"
        )

    workspace = Path(os.environ["MIXSEEK_WORKSPACE"])
    return workspace / "mixseek.db"
```

### ❌ 憲章違反の例

```python
# ❌ 悪い例: デフォルト値提供（憲章違反）
workspace = os.environ.get("MIXSEEK_WORKSPACE", "~/.mixseek")

# ❌ 悪い例: サイレントフォールバック
try:
    workspace = os.environ["MIXSEEK_WORKSPACE"]
except KeyError:
    workspace = Path.home() / ".mixseek"  # 暗黙の代替
```

### 利点

1. **明示性**: 設定が明確（推測なし）
2. **エラー追跡**: 未設定時に即座に検出
3. **本番安全**: 意図しないパス使用を防止

### 教訓

- **`os.environ["KEY"]`**: 未設定時KeyError（推奨）
- **`os.environ.get()`**: デフォルト値提供可能（憲章違反リスク）
- **エラーメッセージ**: 設定例を含める

### 参考リソース

- `.specify/memory/constitution.md` (Article 9): 憲章詳細
- `src/mixseek/storage/aggregation_store.py:81-105`: 実装例
- `specs/005-command/spec.md`: MIXSEEK_WORKSPACE定義

---

## Finding 9: DuckDB JSON内部クエリの実践

### 発見

DuckDBのJSON関数を使うことで、ネストしたJSON構造を**SQL内で直接集計**できる。

### 実装例: チーム統計集計

```python
def _get_team_statistics_sync(self, team_id: str) -> dict[str, float | int]:
    """チーム統計取得（同期版）"""
    conn = self._get_connection()

    # JSON内部クエリで統計集計（FR-013）
    result = conn.execute("""
        SELECT
            COUNT(*) as total_rounds,
            AVG(evaluation_score) as avg_score,
            MAX(evaluation_score) as best_score,
            SUM(CAST(json_extract(usage_info, '$.input_tokens') AS INTEGER)) as total_input_tokens,
            SUM(CAST(json_extract(usage_info, '$.output_tokens') AS INTEGER)) as total_output_tokens
        FROM leader_board
        WHERE team_id = ?
    """, [team_id]).fetchone()

    return {
        "total_rounds": int(result[0]) if result[0] else 0,
        "avg_score": float(result[1]) if result[1] else 0.0,
        "best_score": float(result[2]) if result[2] else 0.0,
        "total_input_tokens": int(result[3]) if result[3] else 0,
        "total_output_tokens": int(result[4]) if result[4] else 0,
    }
```

### JSON構造

```json
// usage_info JSON型カラムの構造
{
  "input_tokens": 100,
  "output_tokens": 200,
  "requests": 1
}
```

### DuckDB JSON演算子 vs 関数

| 方式 | 使用例 | 適用場面 |
|------|--------|---------|
| **JSON演算子** | `column->>'$.key'` | DB内JSON型カラム |
| **json_extract()** | `json_extract(column, '$.key')` | ParquetのSTRING型 |
| **CAST** | `CAST(column AS JSON)->>'key'` | ParquetをJSON型に変換 |

### パフォーマンス

```python
# ✅ DB内で集計（高速）
stats = await store.get_team_statistics("team-001")

# ❌ Pythonで集計（遅い）
# records = await store.get_all_records()
# total_tokens = sum(r.usage_info["input_tokens"] for r in records)
```

### 教訓

- **DB内集計優先**: SQL内でJSON集計が最速
- **json_extract()**: ネストしたフィールド取得
- **CAST**: 型変換で計算可能に

### 参考リソース

- `src/mixseek/storage/aggregation_store.py:470-511`: 実装例
- DuckDB JSON: https://duckdb.org/docs/extensions/json

---

## Finding 10: Pydantic BaseModelとDuckDB JSONの相互変換

### 発見

Pydantic BaseModelは`model_dump(mode='json')`でJSON互換dictに変換でき、DuckDBのJSON型カラムに直接保存可能。

### 保存パターン

```python
# Pydantic Model → DuckDB JSON型
aggregated = AggregatedMemberSubmissions(...)

# JSON互換dictに変換
aggregated_dict = aggregated.model_dump(mode='json')

# JSON文字列化
json_str = json.dumps(aggregated_dict)

# DuckDB JSON型カラムに保存
conn.execute("""
    INSERT INTO round_history (aggregated_submissions)
    VALUES (?)
""", [json_str])
```

### 復元パターン

```python
# DuckDB → Pydantic Model
result = conn.execute(
    "SELECT aggregated_submissions FROM round_history"
).fetchone()

# JSON → Pydantic Model復元
aggregated = AggregatedMemberSubmissions.model_validate_json(result[0])

# 型安全に復元済み
assert isinstance(aggregated, AggregatedMemberSubmissions)
assert aggregated.success_count == 2
```

### mode='json'の重要性

```python
# mode='json': datetimeを文字列化、JSON互換に
aggregated.model_dump(mode='json')
# → {"timestamp": "2025-10-22T12:34:56Z", ...}

# mode='python': datetimeオブジェクトのまま（JSON化不可）
aggregated.model_dump(mode='python')
# → {"timestamp": datetime(...), ...}  # json.dumpsでエラー
```

### 利点

1. **型安全性**: Pydantic検証付き保存・復元
2. **完全性**: 全フィールド保持
3. **シンプル**: カスタムシリアライザ不要

### 注意点

- **computed_field**: `model_dump()`に自動含まれる
- **exclude設定**: 必要に応じて除外可能

### 参考リソース

- `src/mixseek/storage/aggregation_store.py:230`: `model_dump(mode='json')`使用例
- `src/mixseek/storage/aggregation_store.py:383`: `model_validate_json()`使用例
- Pydantic Serialization: https://docs.pydantic.dev/latest/concepts/serialization/

---

## 実装上の重要な学び（まとめ）

### 1. 非同期戦略

**DuckDB（同期API）+ asyncio**:
- `asyncio.to_thread` でスレッドプール退避
- スレッドローカルコネクション管理
- 真の並列実行実現

### 2. 型安全性

**Pydantic AI + mypy strict**:
- `cast(list[ModelMessage], ...)` で型整合
- `computed_field` で宣言的実装
- 全関数に型注釈必須

### 3. データ整合性

**憲章Article 9準拠**:
- 環境変数必須（デフォルト値禁止）
- アプリ + DB二重バリデーション
- 明示的エラー伝播

### 4. TUMIX論文実装

**メッセージ共有方式**:
- `aggregated_content` computed field
- 全Member応答をラベル付き連結
- 次ラウンドで共有

### 5. DuckDB実践

**SQLiteとの違い**:
- IDENTITY列明示必須
- JSON型の活用（内部クエリ）
- ParquetエクスポートのSTRING型変換

---

## 今後の実装への推奨事項

### 1. 非同期ライブラリ選択時

同期APIのライブラリ（DuckDB等）を使う場合:
- `asyncio.to_thread` パターン適用
- スレッドローカル変数でリソース管理
- 同期版メソッドと非同期ラッパーを分離

### 2. Pydantic AI統合時

Message History永続化:
- `to_jsonable_python()` → JSON → DB
- `ModelMessagesTypeAdapter.validate_json()` で復元
- JSON型カラム推奨（クエリ可能性）

### 3. データベース設計時

DuckDB使用時:
- `GENERATED BY DEFAULT AS IDENTITY` 明示
- CHECK制約でデータ整合性保証
- JSON型活用（分析クエリ高速化）

### 4. 型安全性確保時

mypy strict mode:
- `cast()` で型整合性確保
- `type: ignore` は最小限に
- computed_fieldに`# type: ignore[prop-decorator]`

---

## References

- **実装コード**: `src/mixseek/models/leader_agent.py`, `src/mixseek/storage/aggregation_store.py`
- **テストコード**: `tests/unit/`, `tests/integration/`
- **仕様書**: `specs/008-leader/spec.md`
- **Research**: `specs/008-leader/research.md`
- **Pydantic AI Docs**: `draft/references/pydantic-ai-docs/`
- **TUMIX Paper**: `draft/references/thesis/2510.01279v1.md`
- **Feedbacks**: `specs/008-leader/feedbacks/`
