# API Contract: Leader Agent

**Feature**: 026-mixseek-core-leader
**Date**: 2025-10-23
**Purpose**: Leader Agent API契約定義（Agent Delegation + データ永続化）

## Overview

Leader Agent APIは、Agent Delegationによる動的なMember Agent選択・実行と、応答の構造化データ記録を提供します。すべてのAPIは型安全（Pydantic BaseModel）で、非同期実行をサポートします。

---

## 1. LeaderAgent クラス

### 1.1 初期化

**Signature**:
```python
class LeaderAgent:
    def __init__(
        self,
        team_config: TeamConfig,
        member_agents: dict[str, Agent],
        db_store: AggregationStore | None = None
    ) -> None:
        """Leader Agent初期化

        Args:
            team_config: チーム設定（TOML読み込み済み）
            member_agents: Member Agentのマップ（agent_name -> Agent）
            db_store: データベースストア（Noneの場合は自動作成）

        Raises:
            ValueError: team_configバリデーションエラー
            EnvironmentError: MIXSEEK_WORKSPACE未設定
        """
```

**Contract**:
- **Preconditions**:
  - `team_config.members`が最低1つ
  - `member_agents`に`team_config.members`の全Agent名が存在
  - 環境変数`MIXSEEK_WORKSPACE`が設定済み（db_store=Noneの場合）

- **Postconditions**:
  - Leader AgentインスタンスがAgent Delegation可能な状態
  - 各Member AgentがLeader AgentのToolとして登録済み

- **Side Effects**:
  - DuckDBテーブル初期化（初回のみ）

---

### 1.2 run（メイン実行）

**Signature**:
```python
async def run(
    self,
    user_prompt: str,
    round_number: int = 1,
    message_history: list[ModelMessage] | None = None,
    usage_limits: UsageLimits | None = None
) -> AgentRunResult:
    """Leader Agent実行（Agent Delegation）

    Args:
        user_prompt: ユーザープロンプト
        round_number: ラウンド番号（デフォルト1）
        message_history: 前ラウンドのMessage History（Round 2以降）
        usage_limits: リソース使用量制限

    Returns:
        AgentRunResult（output + usage + all_messages）

    Raises:
        ValueError: user_prompt空文字列
        UsageLimitExceeded: リソース制限超過
        DatabaseWriteError: データベース保存失敗（3回リトライ後）
    """
```

**Contract**:
- **Preconditions**:
  - `user_prompt`が非空文字列
  - `round_number >= 1`

- **Postconditions**:
  - Leader AgentがLLMでタスク分析
  - 適切なMember AgentがToolを通じて動的に選択・実行
  - `TeamDependencies.submissions`に選択されたMember Agent応答が記録
  - `AgentRunResult.usage()`に全Member AgentのRunUsageが統合

- **Side Effects**:
  - Member Agent実行（Agent Delegation）
  - `TeamDependencies.submissions`更新

- **Performance**:
  - Agent Delegation 1回あたり <5秒（Member Agent実行時間含む）
  - LLMのTool選択時間 <1秒

---

### 1.3 save_to_database（データ永続化）

**Signature**:
```python
async def save_to_database(
    self,
    record: MemberSubmissionsRecord,
    message_history: list[ModelMessage]
) -> None:
    """DuckDBにデータ永続化（単一トランザクション）

    Args:
        record: Member Agent応答記録
        message_history: Pydantic AI Message History

    Raises:
        DatabaseWriteError: 書き込み失敗（3回リトライ後）
        ValueError: team_id + round_numberが既存レコードと重複（UNIQUE制約違反）
    """
```

**Contract** (FR-007-1):
- **Preconditions**:
  - `record.team_id`が非空文字列
  - `record.round_number >= 1`

- **Postconditions**:
  - `message_history`と`record`が**単一トランザクション**でDuckDBに保存
  - UNIQUE制約（team_id + round_number）により、既存レコードは上書き（UPSERT）

- **Side Effects**:
  - DuckDB `round_history`テーブルにINSERT
  - エクスポネンシャルバックオフリトライ（1, 2, 4秒、最大3回）

- **Performance**:
  - 書き込み時間 <100ms（MVCC並列書き込み）
  - 複数チーム同時書き込み時もロック競合なし

---

## 2. MemberAgentTool（動的生成）

### 2.1 Tool関数シグネチャ

**Signature** (例: delegate_to_analyst):
```python
@leader_agent.tool
async def delegate_to_analyst(
    ctx: RunContext[TeamDependencies],
    task: str
) -> str:
    """論理的な分析・データ解釈を実行します

    Args:
        ctx: RunContext（依存関係・usage含む）
        task: 分析タスクの説明

    Returns:
        分析結果のテキスト

    Raises:
        ValueError: タスクが空文字列
        AgentExecutionError: Member Agent実行失敗
    """
```

**Contract** (FR-031-034):
- **Preconditions**:
  - `task`が非空文字列

- **Postconditions**:
  - Member Agentが実行され、応答を返す
  - `ctx.deps.submissions`に`MemberSubmission`が追加
  - `ctx.usage`にMember AgentのRunUsageが統合

- **Side Effects**:
  - Member Agent実行（LLM API呼び出し）
  - `TeamDependencies.submissions`更新

---

### 2.2 Tool自動登録

**Signature**:
```python
def register_member_tools(
    leader_agent: Agent,
    team_config: TeamConfig,
    member_agents: dict[str, Agent]
) -> None:
    """TOML設定からMember Agent ToolをLeader Agentに登録

    Args:
        leader_agent: Leader Agentインスタンス
        team_config: チーム設定
        member_agents: Member Agentマップ

    Raises:
        ValueError: tool_name重複
        KeyError: member_agentsにagent_nameが存在しない
    """
```

**Contract** (FR-032):
- **Preconditions**:
  - `team_config.members`の全Member Agentが`member_agents`に存在
  - `tool_name`が一意（自動生成含む）

- **Postconditions**:
  - 各Member AgentがLeader AgentのToolとして登録
  - Tool名 = `tool_name` or `f"delegate_to_{agent_name}"`
  - Tool説明 = `tool_description`

---

## 3. AggregationStore（データベース永続化）

### 3.1 save_aggregation

**Signature**:
```python
async def save_aggregation(
    self,
    record: MemberSubmissionsRecord,
    message_history: list[ModelMessage]
) -> None:
    """集約結果とMessage Historyを保存

    Args:
        record: Member Agent応答記録
        message_history: Pydantic AI Message History

    Raises:
        DatabaseWriteError: 書き込み失敗（3回リトライ後）
    """
```

**Contract** (FR-006, FR-007, FR-007-1):
- **Preconditions**:
  - `record`が有効なMemberSubmissionsRecord
  - `message_history`がPydantic AI ModelMessageリスト

- **Postconditions**:
  - `message_history`と`record`が**単一トランザクション**で保存
  - `team_id + round_number`でUNIQUE制約、既存は上書き

- **Side Effects**:
  - DuckDB INSERT（UPSERT）
  - エクスポネンシャルバックオフリトライ（最大3回）

- **Performance** (SC-001):
  - 複数チーム並列書き込み時もロック競合なし（MVCC）
  - 書き込み時間 <100ms

---

### 3.2 load_round_history

**Signature**:
```python
async def load_round_history(
    self,
    team_id: str,
    round_number: int
) -> tuple[MemberSubmissionsRecord | None, list[ModelMessage]]:
    """ラウンド履歴を読み込み

    Args:
        team_id: チームID
        round_number: ラウンド番号

    Returns:
        (記録結果, Message History)のタプル
        レコード未存在時は (None, [])

    Raises:
        DatabaseReadError: 読み込み失敗
    """
```

**Contract** (FR-012):
- **Preconditions**:
  - なし（レコード未存在は正常）

- **Postconditions**:
  - JSON → Pydantic型に完全復元
  - `ModelMessagesTypeAdapter.validate_json()`使用

- **Performance**:
  - 読み込み時間 <50ms

---

### 3.3 get_leader_board

**Signature**:
```python
async def get_leader_board(
    self,
    limit: int = 10
) -> pd.DataFrame:
    """Leader Boardランキング取得

    Args:
        limit: 取得件数（デフォルト10）

    Returns:
        Pandas DataFrame（team_name, round_number, evaluation_score等）

    Raises:
        DatabaseReadError: 読み込み失敗
    """
```

**Contract** (FR-011, SC-003):
- **Preconditions**:
  - `limit > 0`

- **Postconditions**:
  - スコア降順ソート
  - 同スコアは作成日時早い順（2次ソート）

- **Performance**:
  - 100万行でも <1秒（DuckDB列指向ストレージ）

---

## 4. TeamConfig（TOML読み込み）

### 4.1 load_team_config

**Signature**:
```python
def load_team_config(
    toml_path: Path
) -> TeamConfig:
    """チーム設定TOMLを読み込み

    Args:
        toml_path: TOMLファイルパス

    Returns:
        TeamConfig（バリデーション済み）

    Raises:
        FileNotFoundError: TOMLファイル不存在
        ValueError: TOML構文エラー、バリデーションエラー
        ValueError: tool_name重複、agent_name重複
    """
```

**Contract** (FR-025, FR-030, FR-032):
- **Preconditions**:
  - TOMLファイルが存在

- **Postconditions**:
  - TeamConfig構造化データ生成
  - インライン定義と参照形式の混在サポート
  - tool_name自動生成（未設定時）
  - tool_name・agent_name重複チェック

- **Side Effects**:
  - 参照形式の場合、外部TOMLファイル読み込み

---

## 5. CLI Command: mixseek team

### 5.1 コマンドシグネチャ

**Signature**:
```bash
mixseek team <prompt> --config <team.toml> [OPTIONS]
```

**Options**:
- `--config PATH, -c`: チーム設定TOMLファイルパス（必須）
- `--output-format {json,text}, -f`: 出力形式（デフォルト: text）
- `--save-db`: DuckDBに保存（デバッグ用）
- `--previous-round PATH`: 前ラウンド結果JSONファイル（Round 2シミュレーション）
- `--load-from-db TEAM_ID:ROUND`: 前ラウンド結果DB読み込み（Round 2シミュレーション）
- `--evaluation-feedback TEXT`: 評価フィードバック（前ラウンドオプションと併用）

**Contract** (FR-021-028):
- **Preconditions**:
  - `<prompt>`が非空文字列
  - `--config`ファイルが存在
  - 前ラウンドオプション使用時、指定ファイル/DB存在

- **Postconditions**:
  - 開発・テスト専用警告を標準エラー出力
  - Agent Delegationで選択されたMember Agent実行
  - 記録結果を指定形式で出力
  - `--save-db`指定時、DuckDBに保存

- **Exit Codes**:
  - `0`: 成功
  - `1`: 一般エラー（TOML読み込み失敗、バリデーションエラー等）
  - `2`: 選択された全Member Agent失敗
  - `3`: 環境変数未設定
  - `4`: 前ラウンドファイル/DB不存在

---

### 5.2 出力形式

#### JSON出力 (`--output-format json`)

```json
{
  "team_id": "research-team-001",
  "team_name": "Advanced Research Team",
  "round_number": 1,
  "status": "success",
  "total_count": 2,
  "success_count": 2,
  "failure_count": 0,
  "submissions": [
    {
      "agent_name": "analyst",
      "agent_type": "plain",
      "content": "...",
      "status": "SUCCESS",
      "usage": {...},
      "timestamp": "2025-10-23T10:30:45Z"
    }
  ],
  "total_usage": {
    "input_tokens": 250,
    "output_tokens": 500,
    "requests": 2
  }
}
```

#### テキスト出力 (`--output-format text`)

```
⚠️  Development/Testing only - Not for production use

=== Leader Agent Execution ===
Team: Advanced Research Team (research-team-001)
Round: 1

Selected Member Agents: 2/3
✓ analyst (SUCCESS) - 150 input, 300 output tokens
✓ web-searcher (SUCCESS) - 100 input, 200 output tokens

Total Usage: 250 input, 500 output tokens, 2 requests

=== Results ===
[構造化データまたは整形済みコンテンツ]
```

---

## 6. Error Handling Contracts

### 6.1 環境変数未設定 (FR-016, FR-020)

**Error**:
```python
raise EnvironmentError(
    "MIXSEEK_WORKSPACE environment variable is not set.\n"
    "Please set it: export MIXSEEK_WORKSPACE=/path/to/workspace"
)
```

**Contract**:
- Article 9準拠（フォールバック禁止）
- 即座にエラー終了
- 設定方法を明示

---

### 6.2 tool_name重複 (Edge Case)

**Error**:
```python
raise ValueError(
    "Duplicate tool_name detected: ['delegate_to_analyst']\n"
    "Each Member Agent must have a unique tool_name.\n"
    "Check your team.toml configuration."
)
```

**Contract**:
- TOML読み込み時に検出
- 重複しているtool_nameをリストで表示
- 即座にエラー終了

---

### 6.3 データベース書き込み失敗 (FR-019)

**Error** (3回リトライ後):
```python
raise DatabaseWriteError(
    "Failed to save after 3 retries: [original error]\n"
    "Last attempt: [timestamp]\n"
    "Check database permissions and disk space."
)
```

**Contract**:
- エクスポネンシャルバックオフ（1, 2, 4秒）で最大3回リトライ
- 最終失敗時に詳細エラーメッセージ
- 原因特定可能な情報（パス、権限等）を含む

---

### 6.4 前ラウンドファイル/DB不存在 (FR-028)

**Error**:
```python
# ファイル不存在
raise FileNotFoundError(
    f"Previous round file not found: {path}\n"
    "Verify the file path is correct."
)

# DB不存在
raise ValueError(
    f"No record found in database for team_id:round = {team_id}:{round_num}\n"
    "Verify the team_id and round number are correct."
)
```

**Contract**:
- フォールバック禁止（Article 9）
- 指定されたパスまたはteam_id:roundを明示
- 即座にエラー終了

---

## 7. Type Safety Contracts (Article 16)

### 7.1 Pydantic Validation

すべてのデータモデルは自動的にPydanticバリデーションを実施：

```python
# 自動バリデーション
record = MemberSubmissionsRecord(
    team_id="",  # ❌ ValidationError: team_id cannot be empty
    round_number=0  # ❌ ValidationError: round_number must be >= 1
)

# 正常
record = MemberSubmissionsRecord(
    team_id="team-001",
    round_number=1,
    submissions=[]  # ✅ 空リスト可能（Edge Case）
)
```

### 7.2 RunUsage型統合 (FR-034)

```python
# Tool内でRunUsage統合
@leader_agent.tool
async def delegate_to_analyst(ctx: RunContext[TeamDependencies], task: str) -> str:
    result = await analyst_agent.run(
        task,
        usage=ctx.usage  # ✅ RunUsage統合（重要！）
    )
    # result.usage()が親のusageに自動的に追加される
    return result.output

# Leader Agent実行後
result = await leader_agent.run("タスク", deps=deps)
print(result.usage())  # ✅ Leader + 全Member AgentのRunUsageが含まれる
```

---

## 8. Performance Contracts

| API | Performance Goal | Success Criterion |
|-----|-----------------|-------------------|
| `LeaderAgent.run()` | <5秒/実行 | Agent Delegation 1-3回 |
| `save_aggregation()` | <100ms/保存 | MVCC並列書き込み |
| `load_round_history()` | <50ms/読み込み | JSON復元含む |
| `get_leader_board()` | <1秒/100万行 | DuckDB列指向ストレージ |

---

## 9. Security Contracts

### 9.1 環境変数セキュリティ (Article 9)

**Contract**:
- ❌ ハードコードパス禁止
- ❌ デフォルト値禁止
- ✅ 環境変数`MIXSEEK_WORKSPACE`必須

### 9.2 TOML Injection防止

**Contract**:
- Pydanticバリデーションで型安全性保証
- TOMLパーサー（tomllib）は標準ライブラリ使用
- システムプロンプトは文字列として扱い、eval()等の動的実行なし

---

## 10. Compatibility Contracts

### 10.1 Pydantic AI互換性

**Contract**:
- Pydantic AI Agent Delegationパターン準拠
- RunContext[Deps]型安全性保証
- ModelMessagesTypeAdapter使用

### 10.2 DuckDB互換性

**Contract**:
- DuckDB >=1.3.1
- MVCC並列書き込み対応
- JSON型ネイティブサポート

---

## Summary

- **7つのAPI契約**: LeaderAgent.run(), save_to_database(), MemberAgentTool, register_member_tools(), AggregationStore各メソッド, CLI command
- **型安全性**: すべてPydantic BaseModel、Article 16準拠
- **エラー処理**: Article 9準拠（フォールバック禁止、明示的エラー）
- **パフォーマンス**: 具体的な数値目標（<1秒、<100ms等）
- **セキュリティ**: 環境変数必須、Injection防止

**Next**: データベーススキーマDDL生成
