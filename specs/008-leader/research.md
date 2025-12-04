# Research: Leader Agent - Agent Delegation と Member Agent応答記録

**Date**: 2025-10-23
**Feature**: 026-mixseek-core-leader
**Purpose**: Phase 0技術調査 - Agent Delegation実装パターン、DuckDB並列書き込み、既存コード調査

## Research Topics

### 1. Pydantic AI Agent Delegationの実装パターン

#### Decision
Pydantic AIの標準Agent Delegationパターンを採用し、Leader AgentのToolを通じてMember Agentを動的に呼び出す方式を実装します。

#### Rationale

**Pydantic AI Agent Delegationの利点**:
- **型安全性**: `RunContext[Deps]`を通じた型安全な依存関係共有
- **RunUsage自動統合**: `ctx.usage`を委譲先に渡すことで、全Agentのトークン使用量を自動集計
- **ステートレス設計**: Agentはグローバルに定義可能、依存関係は実行時に注入
- **非同期実行**: asyncio完全サポート、`await member_agent.run()`で呼び出し
- **リソース効率**: 必要なMember Agentのみ実行、不要なAgent実行を回避

**全Agent並列実行方式との比較**:

| 観点 | Agent Delegation | 全Agent並列実行 |
|------|------------------|----------------|
| Member Agent選択 | LLMが動的に選択 | 全て実行（静的） |
| リソース効率 | 高（必要なもののみ） | 低（不要なAgentも実行） |
| 柔軟性 | 高（タスクに応じて選択） | 低（常に全て実行） |
| 制御 | LLMに委ねる | 確定的 |
| TUMIX準拠 | 不要（参考のみ） | 必要 |

#### 実装パターン
```python
from pydantic_ai import Agent, RunContext, RunUsage

# Leader Agent定義
leader_agent = Agent(
    'openai:gpt-4o',
    deps_type=TeamDependencies,
    system_prompt='''
タスクを分析し、適切なMember Agentを選択してください：
- delegate_to_analyst: 論理的分析が必要な場合
- delegate_to_web_searcher: 最新情報が必要な場合
'''
)

# Member Agentの動的Tool登録（TOML設定から生成）
@leader_agent.tool
async def delegate_to_analyst(
    ctx: RunContext[TeamDependencies],
    task: str
) -> str:
    """論理的な分析・データ解釈を実行します"""
    result = await analyst_agent.run(
        task,
        deps=ctx.deps,      # 依存関係を共有
        usage=ctx.usage     # RunUsageを統合（重要！）
    )

    # MemberSubmission記録
    submission = create_member_submission(
        agent_name="analyst",
        content=result.output,
        usage=result.usage()
    )
    ctx.deps.record_submission(submission)

    return result.output

# Leader Agent実行
result = await leader_agent.run(
    "最新のAI技術トレンドを分析してください",
    deps=team_deps
)
# result.usage() には全Member AgentのRunUsageが含まれる
```

#### Alternatives Considered
- **プログラマティックHand-off**: アプリケーションコードが複数Agentを順次呼び出し
  - 却下理由: LLMの自律的判断が活用できず、柔軟性が低い、タスク分析ロジックを別途実装必要
- **Graph-based control flow**: LangGraphのような状態機械
  - 却下理由: 過剰な複雑性、Pydantic AIネイティブでない、学習コスト高
- **全Agent並列実行**: TUMIX論文方式
  - 却下理由: リソース効率悪い、TUMIX遵守不要（ユーザー承認済み）

#### References
- `draft/references/pydantic-ai-docs/multi-agent-applications.md` (Agent Delegation section)
- `draft/references/pydantic-ai-doc-ja/multi-agent-applications.md` (日本語版)
- Pydantic AI公式ドキュメント: https://ai.pydantic.dev

---

### 2. DuckDB MVCC並列書き込みのベストプラクティス

#### Decision
DuckDB 1.3.1+ のMVCC（Multi-Version Concurrency Control）を活用し、複数チームの同時書き込みをロックフリーで実現します。

#### Rationale
- **ロックフリー**: MVCC方式により、READはWRITEをブロックせず、WRITEも他WRITEをブロックしない
- **トランザクション原子性**: `BEGIN` - `COMMIT`でMessage History + MemberSubmissionsRecordを単一トランザクションで保存（FR-007-1）
- **JSON型ネイティブサポート**: Message HistoryをJSON型で保存・クエリ可能
- **高速分析**: 列指向ストレージでLeader Board集計が高速（<1秒、100万行）

#### 実装パターン
```python
import duckdb
from pathlib import Path
from contextlib import contextmanager

class DuckDBStore:
    """DuckDB接続管理（MVCCトランザクションサポート）"""

    def __init__(self, db_path: Path):
        self.conn = duckdb.connect(str(db_path))

    @contextmanager
    def transaction(self):
        """トランザクション管理コンテキストマネージャ"""
        try:
            self.conn.execute("BEGIN")
            yield self.conn
            self.conn.execute("COMMIT")
        except Exception:
            self.conn.execute("ROLLBACK")
            raise

    def save_round(
        self,
        team_id: str,
        round_num: int,
        message_history_json: str,
        submissions_json: str
    ) -> None:
        """単一トランザクションでMessage History + Submissionsを保存"""
        with self.transaction() as conn:
            # UPSERT（既存レコード更新または新規挿入）
            conn.execute("""
                INSERT INTO round_history (team_id, round, message_history, submissions, created_at)
                VALUES (?, ?, ?::JSON, ?::JSON, CURRENT_TIMESTAMP)
                ON CONFLICT (team_id, round) DO UPDATE SET
                    message_history = EXCLUDED.message_history,
                    submissions = EXCLUDED.submissions,
                    created_at = CURRENT_TIMESTAMP
            """, [team_id, round_num, message_history_json, submissions_json])
```

#### Alternatives Considered
- **SQLite**: 親仕様の選択肢の1つ
  - 却下理由: JSON型サポート弱い（JSON1拡張必要）、並列書き込みで即座にロック（WALモードでも遅い）
- **PostgreSQL**: 親仕様の選択肢の1つ
  - 却下理由: 初期段階には過剰、単一ファイル不可、デプロイ複雑、サーバープロセス必要
- **自動コミットモード**: トランザクション管理なし
  - 却下理由: データ整合性保証不可（FR-007-1違反）

#### References
- DuckDB公式ドキュメント: Concurrency (MVCC)
- DuckDB JSON型: https://duckdb.org/docs/data/json/overview
- Clarifications Session 2025-10-22で決定済み

---

### 3. Member Agent TOML設定の読み込みとTool自動生成

#### Decision
TOML設定から各Member AgentのTool定義（tool_name, tool_description）を読み込み、Leader AgentのToolとして動的に登録します。

#### Rationale
- **設定駆動**: コード変更なしでMember Agent追加可能
- **DRY原則**: 既存Member Agent TOML参照形式サポート（FR-025）
- **型安全性**: Pydantic BaseModelでTOML validation
- **柔軟性**: インライン定義と参照形式の混在可能（FR-025）

#### 実装パターン
```python
import tomllib  # Python 3.11+標準ライブラリ
from pydantic import BaseModel, Field
from pathlib import Path

class MemberAgentConfig(BaseModel):
    agent_name: str
    agent_type: str
    tool_name: str | None = None  # 未設定時はagent_nameから自動生成
    tool_description: str
    model: str
    system_prompt: str
    temperature: float = Field(ge=0.0, le=1.0)
    max_tokens: int = Field(gt=0)
    config: str | None = None  # 参照形式パス

class LeaderConfig(BaseModel):
    system_prompt: str | None = None  # オプション

class TeamConfig(BaseModel):
    team_id: str
    team_name: str
    leader: LeaderConfig | None = None
    members: list[MemberAgentConfig]

# TOML読み込み（参照形式サポート）
def load_team_config(toml_path: Path) -> TeamConfig:
    with open(toml_path, "rb") as f:
        data = tomllib.load(f)

    members = []
    for member_data in data["team"].get("members", []):
        if "config" in member_data:
            # 参照形式: 外部Member Agent TOMLを読み込み
            ref_path = Path(member_data["config"])
            if not ref_path.exists():
                raise FileNotFoundError(
                    f"Referenced agent config not found: {ref_path}\n"
                    f"Current directory: {Path.cwd()}"
                )

            with open(ref_path, "rb") as mf:
                member_toml = tomllib.load(mf)

            # tool_name/descriptionは上書き可能
            member_toml["agent"].update({
                k: v for k, v in member_data.items()
                if k in ["tool_name", "tool_description"] and v is not None
            })
            members.append(MemberAgentConfig(**member_toml["agent"]))
        else:
            # インライン定義
            members.append(MemberAgentConfig(**member_data))

    # tool_name重複チェック
    tool_names = [
        m.tool_name or f"delegate_to_{m.agent_name}"
        for m in members
    ]
    if len(tool_names) != len(set(tool_names)):
        duplicates = [name for name in tool_names if tool_names.count(name) > 1]
        raise ValueError(f"Duplicate tool_name detected: {duplicates}")

    return TeamConfig(
        team_id=data["team"]["team_id"],
        team_name=data["team"]["team_name"],
        leader=LeaderConfig(**data["team"].get("leader", {})) if "leader" in data["team"] else None,
        members=members
    )
```

#### Tool動的登録
```python
def register_member_tools(
    leader_agent: Agent,
    team_config: TeamConfig,
    member_agents: dict[str, Agent]
) -> None:
    """TOML設定からMember Agent ToolをLeader Agentに登録"""

    for member_config in team_config.members:
        tool_name = member_config.tool_name or f"delegate_to_{member_config.agent_name}"
        member_agent = member_agents[member_config.agent_name]

        # Toolクロージャー生成
        async def make_tool(mc=member_config, ma=member_agent):
            async def tool_func(ctx: RunContext[TeamDependencies], task: str) -> str:
                result = await ma.run(task, deps=ctx.deps, usage=ctx.usage)

                # 記録
                submission = MemberSubmission(
                    agent_name=mc.agent_name,
                    agent_type=mc.agent_type,
                    content=result.output,
                    status="SUCCESS",
                    usage=result.usage(),
                    timestamp=datetime.now(UTC)
                )
                ctx.deps.submissions.append(submission)

                return result.output

            tool_func.__name__ = tool_name
            tool_func.__doc__ = mc.tool_description
            return tool_func

        # Tool登録
        tool = await make_tool()
        leader_agent.tool(tool)
```

#### Alternatives Considered
- **静的Tool定義**: コードにハードコード
  - 却下理由: 柔軟性なし、DRY違反、Member Agent追加ごとにコード変更必要
- **JSON設定**: TOMLの代わりにJSON
  - 却下理由: Member Agent（specs/027）との一貫性なし、コメント不可、人間可読性低下

#### References
- Python 3.11+ `tomllib`標準ライブラリ
- Pydantic BaseModel validation
- Member Agent仕様（specs/027）のTOML構造

---

### 4. 既存DuckDB接続管理コードの調査（DRY Article 10）

#### Investigation Task
既存の`mixseek_core/database/`配下のDuckDB接続管理コードを調査し、共通化可能なパターンを特定します。

#### 調査方法
```bash
# 既存DuckDB使用箇所を検索
rg "import duckdb" mixseek_core/
rg "duckdb\.connect" mixseek_core/
rg "BEGIN.*COMMIT" mixseek_core/
rg "ROLLBACK" mixseek_core/
```

#### 調査観点
1. 既存の接続管理クラスの有無
2. トランザクション管理パターン
3. エラーハンドリング（リトライロジック）
4. スレッドローカル接続管理

#### 期待される成果
- 既存コードの再利用可能性評価
- 共通基底クラスの設計指針
- DRY違反の回避

#### 調査結果 ✅ 完了

**既存実装発見**: `src/mixseek/storage/aggregation_store.py`

**主要な既存実装**:
1. **AggregationStoreクラス**: DuckDB接続管理・永続化ロジック
2. **スレッドローカル接続**: `threading.local()`による各スレッド独立接続
3. **トランザクション管理**: `@contextmanager`による`BEGIN`-`COMMIT`-`ROLLBACK`
4. **非同期ラッパー**: `asyncio.to_thread`でDuckDB同期APIをスレッドプールに退避
5. **エクスポネンシャルバックオフ**: `[1, 2, 4]`秒のリトライロジック既実装
6. **Message History永続化**: `ModelMessagesTypeAdapter.validate_json()`使用
7. **Leader Board**: スコア降順ソート、統計集計機能

#### Decision
**既存の`AggregationStore`クラスを最大限再利用します**

**再利用可能な機能**:
- ✅ `_get_connection()`: スレッドローカル接続管理
- ✅ `_transaction()`: トランザクション管理コンテキストマネージャ
- ✅ `_get_db_path()`: 環境変数`MIXSEEK_WORKSPACE`からパス取得（Article 9準拠）
- ✅ `save_aggregation()`: エクスポネンシャルバックオフリトライ実装済み
- ✅ `load_round_history()`: Message History復元ロジック
- ✅ `get_leader_board()`, `get_team_statistics()`: 分析クエリ

**必要な変更**:
- ⚠️ モデル名変更: `AggregatedMemberSubmissions` → `MemberSubmissionsRecord`
- ⚠️ スキーマ更新: `aggregated_submissions`カラム → `member_submissions_record`
- ⚠️ Agent Delegation対応: Tool実行記録の追加

**DRY Article 10準拠判定**: ✅ PASS
- 既存コードを最大限活用
- 車輪の再発明を回避
- 共通パターンの抽出済み

---

### 5. Pydantic AI Message Historyのシリアライズ・デシリアライズ

#### Decision
Pydantic AIの`ModelMessagesTypeAdapter`を使用してMessage HistoryをJSON化し、DuckDB JSON型に保存します。

#### Rationale
- **型安全性**: Pydantic AI標準の変換API
- **完全な往復変換**: `dump_json()` → JSON型 → `validate_json()` で完全復元
- **後方互換性**: Pydantic AIのMessage構造変更に追従
- **シンプル**: カスタムシリアライザ不要（Anti-Abstraction Article 6準拠）

#### 実装パターン
```python
from pydantic_ai.messages import ModelMessagesTypeAdapter, ModelMessage

class MessageHistoryStore:
    """Message History永続化"""

    def save_messages(
        self,
        team_id: str,
        round_num: int,
        messages: list[ModelMessage]
    ) -> None:
        """Message HistoryをDuckDBに保存"""
        # JSON化
        json_bytes = ModelMessagesTypeAdapter.dump_json(messages)
        json_str = json_bytes.decode('utf-8')

        # DuckDBに保存
        self.conn.execute(
            "INSERT INTO round_history (team_id, round, message_history) "
            "VALUES (?, ?, ?::JSON)",
            [team_id, round_num, json_str]
        )

    def load_messages(
        self,
        team_id: str,
        round_num: int
    ) -> list[ModelMessage]:
        """Message HistoryをDuckDBから読み込み"""
        row = self.conn.execute(
            "SELECT message_history FROM round_history "
            "WHERE team_id=? AND round=?",
            [team_id, round_num]
        ).fetchone()

        if row is None:
            raise ValueError(f"No history found for {team_id}:{round_num}")

        # JSON文字列からMessage復元
        return ModelMessagesTypeAdapter.validate_json(row[0])
```

#### Alternatives Considered
- **カスタムシリアライザ**: 独自JSON変換実装
  - 却下理由: Pydantic AI型との互換性失われる、保守コスト高、Article 6違反
- **Pickle**: Pythonオブジェクト直接保存
  - 却下理由: データベース分析クエリ不可、セキュリティリスク、バージョン間互換性問題

#### References
- Pydantic AI `ModelMessagesTypeAdapter` API
- Clarifications Session 2025-10-22で決定済み（FR-012）

---

### 6. エクスポネンシャルバックオフ リトライロジック

#### Decision
データベース書き込み失敗時、エクスポネンシャルバックオフ（1秒、2秒、4秒）で最大3回リトライします。

#### Rationale
- **一時的競合の回復**: 短時間で回復する一時的な競合（MVCC競合等）に対応
- **深刻な障害の早期検出**: 3回失敗で即座に終了、無限ループ回避
- **リソース効率**: 固定間隔より効率的、指数的に待機時間増加

#### 実装パターン
```python
import asyncio
from typing import TypeVar, Callable, Awaitable

T = TypeVar('T')

async def retry_with_exponential_backoff(
    func: Callable[[], Awaitable[T]],
    max_retries: int = 3,
    base_delay: float = 1.0
) -> T:
    """エクスポネンシャルバックオフでリトライ

    Args:
        func: リトライする非同期関数
        max_retries: 最大リトライ回数（デフォルト3）
        base_delay: 基底遅延時間（秒、デフォルト1.0）

    Returns:
        関数の実行結果

    Raises:
        最終リトライ失敗時の例外
    """
    last_exception = None

    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            last_exception = e
            if attempt == max_retries - 1:
                raise  # 最終リトライ失敗

            delay = base_delay * (2 ** attempt)  # 1, 2, 4秒
            logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay}s: {e}")
            await asyncio.sleep(delay)

    # 到達しないが型チェッカー対策
    assert last_exception is not None
    raise last_exception

# 使用例
await retry_with_exponential_backoff(
    lambda: store.save_round(team_id, round_num, history_json, submissions_json),
    max_retries=3,
    base_delay=1.0
)
```

#### Alternatives Considered
- **固定間隔リトライ**: 毎回1秒待機
  - 却下理由: 深刻な障害時に無駄な待機、一時的競合時に短すぎる可能性
- **無限リトライ**: 成功するまで継続
  - 却下理由: デッドロックリスク、リソース浪費、Article 9違反
- **リトライなし**: 1回失敗で即座に終了
  - 却下理由: 一時的な競合で失敗、堅牢性低下

#### References
- Clarifications Session 2025-10-22で決定済み（FR-019）
- 一般的なリトライパターン（指数バックオフ）

---

### 7. Member Agent Tool引数設計

#### Decision
Member Agent Tool引数は最小限（`task: str`）とし、Leader Agentの自律的判断を最大化します。

#### Rationale
- **シンプル**: タスク記述のみを渡す、Leader AgentがLLMでタスク内容を決定
- **柔軟性**: 構造化引数による制約なし
- **型安全性**: Pydantic validationで引数検証

#### 実装パターン
```python
@leader_agent.tool
async def delegate_to_analyst(
    ctx: RunContext[TeamDependencies],
    task: str
) -> str:
    """論理的な分析・データ解釈を実行します

    Args:
        task: 分析タスクの説明（必須、空文字列不可）

    Returns:
        分析結果のテキスト

    Raises:
        ValueError: タスクが空の場合
    """
    if not task.strip():
        raise ValueError("Task cannot be empty")

    result = await analyst_agent.run(task, deps=ctx.deps, usage=ctx.usage)
    return result.output
```

#### Alternatives Considered
- **構造化引数**: `AnalysisRequest(query: str, depth: int, format: str)`
  - 却下理由: 柔軟性低下、Leader AgentのLLM判断を制限、Agent Delegationの利点失われる
- **可変長引数**: `*args, **kwargs`
  - 却下理由: 型安全性失われる、Article 16違反

---

## Summary of Key Decisions

| 項目 | 決定 | 根拠 |
|------|------|------|
| **Agent実行方式** | Agent Delegation（動的選択） | Pydantic AI標準、リソース効率、柔軟性優先 |
| **TUMIX準拠** | 参考のみ（遵守不要） | ユーザー承認済み、並列実行破棄 |
| **データベース** | DuckDB >=1.3.1 | MVCC並列、JSON型、分析高速 |
| **Message History** | JSON型で保存、TypeAdapter復元 | Pydantic AI設計準拠 |
| **TOML設定** | tomllib（Python 3.11+標準） | 参照形式サポート、DRY準拠 |
| **Tool自動生成** | tool_name/description動的登録 | 設定駆動、柔軟性 |
| **トランザクション** | 単一トランザクション（History + Submissions） | データ整合性保証 |
| **リトライ** | エクスポネンシャルバックオフ（1, 2, 4秒、最大3回） | 一時的競合対応、早期障害検出 |
| **環境変数** | MIXSEEK_WORKSPACE必須 | 憲章Article 9準拠 |
| **Tool引数** | 最小限（task: str） | 柔軟性最大化 |

### 要調査事項（実施予定）
- ✅ 既存DuckDB接続管理コードの調査（`mixseek_core/database/`）
  - DRY Article 10準拠のため、既存実装を先に調査

**全ての技術選択は仕様書、憲章、親仕様に準拠しています。Agent Delegation方式への変更はユーザー承認済みです。**

---

## Next Steps

Phase 0調査完了後：
1. 既存DuckDB接続管理コードを調査（DRY調査）
2. Phase 1: data-model.md生成（エンティティ詳細設計）
3. Phase 1: contracts/生成（API契約定義）
4. Phase 1: quickstart.md生成（クイックスタート）
5. Agent context更新
