# Research: MixSeek-Core Orchestrator（1ラウンド仮実装）

**Date**: 2025-11-05
**Spec**: [spec.md](./spec.md)
**Plan**: [plan.md](./plan.md)

このドキュメントは、Phase 0で実施した技術調査の結果をまとめたものです。

## 1. Leader Agent統合方法

### 調査結果

既存のLeader Agent実装（`src/mixseek/agents/leader/agent.py`）は以下の構造になっています:

**Leader Agentの作成**:
```python
from mixseek.agents.leader.agent import create_leader_agent
from mixseek.agents.leader.config import TeamConfig, load_team_config

# TOML読み込み
team_config = load_team_config(Path("team.toml"), workspace=Path("/workspace"))

# Member Agentマップ準備（agent_name -> Agent）
member_agents = {...}

# Leader Agent作成
leader_agent = create_leader_agent(team_config, member_agents)
```

**Leader Agentの実行**:
```python
from pydantic_ai import ModelMessage

# 実行
result = await leader_agent.run(
    user_prompt="タスク説明",
    deps=TeamDependencies(...),
    message_history=[]  # 前ラウンドからの引き継ぎ（初回は空リスト）
)

# 結果取得
submission_text: str = result.data
message_history: list[ModelMessage] = result.all_messages()
usage: RunUsage = result.usage()
```

### Decision

- **Orchestrator → RoundController → Leader Agent**の階層構造を採用
- RoundControllerがLeader Agentを起動し、結果を取得
- RoundController内でEvaluatorを呼び出し、評価結果を取得
- 既存の`create_leader_agent()`と`leader_agent.run()`をそのまま利用

### Rationale

- 既存のLeader Agent実装を変更せずに統合できる（DRY原則遵守）
- Leader Agentの役割（単一ラウンド内処理）と明確に分離
- 将来的に複数ラウンド対応時も、RoundControllerの責務が明確

## 2. 並列実行戦略

### 調査結果

Pythonの`asyncio.gather()`を使用することで、複数チームの並列実行が可能です:

```python
import asyncio

results = await asyncio.gather(
    round_controller1.run_round(prompt),
    round_controller2.run_round(prompt),
    round_controller3.run_round(prompt),
    return_exceptions=True  # エラーが発生しても他のチームは継続
)
```

`return_exceptions=True`により、1チームが失敗しても他のチームは継続実行されます。

### Decision

- **asyncio.gather()でチーム単位の並列実行**を実現
- `return_exceptions=True`でエラーハンドリング
- 各RoundControllerは独立してLeader Agentを実行

### Rationale

- 親仕様（specs/001-specs/spec.md FR-002）の「複数チーム並列実行」要件を満たす
- 1チームのエラーが他チームに影響しない（FR-006の失格処理ポリシーに準拠）
- 既存のAggregationStoreはスレッドローカルコネクションで並列書き込み対応済み

## 3. DuckDB記録タイミング

### 調査結果

既存のDuckDBスキーマ（specs/008-leader/contracts/database-schema.sql）:

```sql
-- round_history テーブル
CREATE TABLE IF NOT EXISTS round_history (
    id INTEGER PRIMARY KEY,
    team_id TEXT NOT NULL,
    team_name TEXT NOT NULL,
    round_number INTEGER NOT NULL,
    message_history JSON,  -- Pydantic AI Message History
    member_submissions_record JSON,  -- Member Agent応答記録
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(team_id, round_number)
);

-- leader_board テーブル
CREATE TABLE IF NOT EXISTS leader_board (
    id INTEGER PRIMARY KEY,
    team_id TEXT NOT NULL,
    team_name TEXT NOT NULL,
    round_number INTEGER NOT NULL,
    evaluation_score DOUBLE NOT NULL CHECK (evaluation_score >= 0.0 AND evaluation_score <= 1.0),
    evaluation_feedback TEXT,
    submission_content TEXT NOT NULL,
    usage_info JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

既存の`AggregationStore`（`src/mixseek/storage/aggregation_store.py`）が提供するメソッド:

- `save_aggregation()`: round_historyへの保存
- `save_to_leader_board()`: leader_boardへの保存
- `load_round_history()`: round_historyからの読み込み
- `get_leader_board()`: leader_boardランキング取得

### Decision

**記録タイミング**:

1. **ラウンド開始時**: 記録なし（初期実装では不要）
2. **ラウンド完了時**:
   - `round_history`への記録（Message History + Member Agent応答）
   - `leader_board`への記録（Submission + 評価スコア + フィードバック）

**記録処理**:
- RoundController内で`AggregationStore`を使用
- Leader Agent実行直後に`save_aggregation()`
- Evaluator実行直後に`save_to_leader_board()`

### Rationale

- 既存スキーマとAggregationStoreをそのまま活用（DRY原則）
- FR-002（即時記録）、FR-003（ラウンド記録管理）、FR-010（Leader Board記録）を満たす
- 初期実装（1ラウンドのみ）では開始時の記録は不要

## 4. TOMLファイル設計（複数チーム設定）

### 調査結果

既存のチーム設定TOML（`examples/team-inline-agents.toml`）は単一チームの定義です:

```toml
[team]
team_id = "team-001"
team_name = "Research Team"
max_concurrent_members = 5

[team.leader]
model = "google-gla:gemini-2.5-flash-lite"
system_instruction = "..."

[[team.members]]
agent_name = "analyst"
agent_type = "plain"
...
```

### Decision

**オーケストレータ設定TOML**（新規フォーマット）:

```toml
# orchestrator.toml
[orchestrator]
timeout_per_team_seconds = 600  # チーム単位タイムアウト（FR-006）

[[orchestrator.teams]]
config = "workspace/configs/team1.toml"  # 参照形式

[[orchestrator.teams]]
config = "workspace/configs/team2.toml"  # 参照形式
```

各チーム設定は既存のTOMLフォーマットをそのまま使用します。

### Rationale

- 既存のTeamConfig構造を変更せずに利用可能
- 複数チーム設定を管理しやすい（各チームを独立ファイルで管理）
- 将来的にチーム固有のパラメータ（優先度、リソース制限等）を追加可能

### Alternatives Considered

- **単一TOML内に複数チーム定義**: 却下（ファイルが肥大化、既存フォーマットの変更が必要）
- **CLIオプションで複数チーム指定**: 却下（コマンドライン引数が複雑化）

## 5. エラーハンドリング・タイムアウト管理

### 調査結果

親仕様（specs/007-orchestration/spec.md）より:

- **FR-006**: チームのタイムアウト時は即座に失格、再試行なし
- **FR-008**: DuckDB通信障害時は書き込みキューで再送

既存のAggregationStoreはリトライ機能を実装済み（3回リトライ、エクスポネンシャルバックオフ）。

### Decision

**タイムアウト処理**:
- RoundController内で`asyncio.wait_for()`を使用してタイムアウト実装
- タイムアウト時は例外を発生させ、Orchestratorで失格処理

**エラーハンドリング**:
- Leader Agentエラー: チーム失格（FR-006）
- Evaluatorエラー: チーム失格（FR-006）
- DuckDBエラー: AggregationStoreの自動リトライに委譲（FR-008）

### Rationale

- 親仕様のエラー処理ポリシーに完全準拠
- 既存のAggregationStoreリトライ機能を活用
- シンプルで明確なエラー処理フロー

## 6. Evaluator統合

### 調査結果

既存のEvaluator実装（src/mixseek/evaluator/）を確認しました。親仕様（specs/001-specs/spec.md FR-008, FR-009）準拠:

- **完全なLLM-as-a-Judge実装**: ClarityCoherence, Coverage, Relevanceなどの組み込みメトリクス
- **柔軟な設定**: `{workspace}/configs/evaluator.toml`で評価基準とLLMパラメータを管理
- **構造化された出力**: `EvaluationResult` Pydantic Model（0-100スケールのスコア + 詳細なコメント）
- **カスタムメトリクス対応**: `register_custom_metric()`で独自評価指標を追加可能

### Decision

**既存Evaluator実装を直接使用**:
- `src/mixseek/evaluator/Evaluator`クラスを使用
- `EvaluationRequest`で評価リクエストを作成
- `EvaluationResult`から`overall_score`（0-100）と各メトリクスのコメントを取得
- 非同期コンテキストでは`asyncio.to_thread()`で同期メソッドをラップ

### Rationale

- **DRY原則遵守（Constitution Article 10）**: 評価ロジックの重複を回避
- **一貫性保証**: すべてのチームで同じ評価基準を適用
- **既存機能の活用**: 成熟したEvaluator実装を再利用
- **メンテナンス性**: 評価ロジックの一元管理

## Summary

すべての技術調査が完了し、実装に必要な情報が揃いました。Phase 1（Data Model & Contracts設計）に進むことができます。

**主な決定事項**:

1. **Leader Agent統合**: 既存実装をそのまま利用、RoundController経由で実行
2. **並列実行**: asyncio.gather()で複数チーム並列実行
3. **DuckDB記録**: 既存AggregationStoreを活用、ラウンド完了時に2回記録
4. **TOML設計**: オーケストレータ設定TOMLで複数チームを参照形式で管理
5. **エラーハンドリング**: asyncio.wait_for()でタイムアウト、失格処理は即座に実行
6. **Evaluator**: 既存実装（src/mixseek/evaluator/）を直接使用
