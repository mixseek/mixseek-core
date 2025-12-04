# Quick Start: Leader Agent - Agent Delegation

**Feature**: 026-mixseek-core-leader
**Date**: 2025-10-23
**Target**: 開発者・テスト担当者

## Overview

このガイドでは、Leader AgentのAgent Delegation機能を使用して、動的にMember Agentを選択・実行し、応答を構造化データとして記録する方法を説明します。

**重要**: `mixseek team`コマンドは**開発・テスト専用**です。本番環境ではOrchestration Layerを使用してください。

---

## Prerequisites

1. **環境変数設定** (必須、Article 9準拠):
```bash
export MIXSEEK_WORKSPACE=/path/to/workspace
```

2. **依存関係インストール**:
```bash
uv sync
```

3. **API キー設定** (Member Agentで使用):
```bash
export OPENAI_API_KEY=your-key
export GOOGLE_API_KEY=your-key
```

---

## Step 1: チーム設定TOMLを作成

`team-example.toml`:
```toml
[team]
team_id = "quickstart-team-001"
team_name = "Quick Start Team"
max_concurrent_members = 5

[team.leader]
# Leader Agentシステムプロンプト（オプション）
system_prompt = """
あなたは研究チームのリーダーエージェントです。
タスクを分析し、以下のMember Agentから適切なものを選択して実行してください：

- delegate_to_analyst: 論理的分析・データ解釈が必要な場合に使用
- delegate_to_summarizer: 情報を簡潔にまとめる必要がある場合に使用

必要に応じて複数のAgentを順次呼び出すことができます。
"""

# Member Agent 1: アナリスト
[[team.members]]
agent_name = "analyst"
agent_type = "plain"
tool_name = "delegate_to_analyst"
tool_description = "論理的な分析・データ解釈を実行します。統計分析や論理推論が必要な場合に使用してください。"
model = "gemini-2.5-flash-lite"
temperature = 0.7
max_tokens = 2048
system_prompt = "あなたは論理的な分析を得意とするアナリストです。"

# Member Agent 2: サマライザー
[[team.members]]
agent_name = "summarizer"
agent_type = "plain"
tool_name = "delegate_to_summarizer"
tool_description = "情報を簡潔にまとめます。長文の要約や重要ポイントの抽出に使用してください。"
model = "gemini-2.5-flash-lite"
temperature = 0.3
max_tokens = 1024
system_prompt = "あなたは情報を簡潔にまとめる専門家です。"
```

---

## Step 2: Agent Delegationを実行

### 基本実行

```bash
mixseek team "最新のAI技術トレンドを分析し、重要なポイントをまとめてください" \
  --config team-example.toml
```

**出力例**:
```
⚠️  Development/Testing only - Not for production use

=== Leader Agent Execution ===
Team: Quick Start Team (quickstart-team-001)
Round: 1

Selected Member Agents: 2/2
✓ analyst (SUCCESS) - 150 input, 300 output tokens, 1234ms
✓ summarizer (SUCCESS) - 100 input, 200 output tokens, 987ms

Total Usage: 250 input, 500 output tokens, 2 requests
```

**Agent Delegationの動作**:
1. Leader AgentがLLMでタスク分析
2. 必要なMember Agentを自律的に選択（analyst + summarizer）
3. Toolを通じて順次実行
4. 応答を構造化データとして記録

---

### JSON出力

```bash
mixseek team "タスク" \
  --config team-example.toml \
  --output-format json > result.json
```

**result.json**:
```json
{
  "team_id": "quickstart-team-001",
  "round_number": 1,
  "submissions": [
    {
      "agent_name": "analyst",
      "content": "...",
      "status": "SUCCESS",
      "usage": {"input_tokens": 150, "output_tokens": 300}
    }
  ],
  "total_usage": {
    "input_tokens": 250,
    "output_tokens": 500,
    "requests": 2
  }
}
```

---

## Step 3: データベースに保存

```bash
mixseek team "タスク" \
  --config team-example.toml \
  --save-db
```

**確認**:
```bash
uv run python -c "
import duckdb, os
conn = duckdb.connect(f'{os.environ[\"MIXSEEK_WORKSPACE\"]}/mixseek.db')
print(conn.execute('SELECT * FROM round_history LIMIT 1').df())
"
```

---

## Step 4: Round 2シミュレーション

### JSONファイルから読み込み

```bash
# Round 1
mixseek team "初期分析" \
  --config team-example.toml \
  --output-format json > round1.json

# Round 2
mixseek team "追加分析" \
  --previous-round round1.json \
  --evaluation-feedback "さらに深掘りしてください"
```

### DuckDBから読み込み

```bash
# Round 1（DB保存）
mixseek team "初期分析" --save-db

# Round 2（DB読み込み、team-id:round形式）
mixseek team "追加分析" \
  --load-from-db quickstart-team-001:1 \
  --evaluation-feedback "さらに深掘りしてください"
```

---

## Agent Delegation動作確認

### 単純なタスク（1つのMember Agentのみ選択）

```bash
mixseek team "Pythonとは何ですか？" \
  --config team-example.toml \
  --output-format json
```

**期待**: 1つのMember Agentのみ実行（リソース節約）

---

### 複雑なタスク（複数のMember Agent選択）

```bash
mixseek team "AI技術を分析し、3つのポイントにまとめてください" \
  --config team-example.toml \
  --output-format json
```

**期待**: 複数のMember Agent順次実行（analyst → summarizer）

---

## Troubleshooting

### エラー1: 環境変数未設定
```
EnvironmentError: MIXSEEK_WORKSPACE environment variable is not set.
```
**解決**: `export MIXSEEK_WORKSPACE=/path/to/workspace`

### エラー2: tool_name重複
```
ValueError: Duplicate tool_name detected: ['delegate_to_analyst']
```
**解決**: 各Member Agentの`tool_name`を一意にする

### エラー3: 前ラウンドファイル不存在
```
FileNotFoundError: Previous round file not found: round1.json
```
**解決**: Round 1を先に実行

---

## Next Steps

1. `/speckit.tasks`でタスク分解・実装開始
2. テスト作成（TDD、Article 3）
3. Leader Board可視化（Jupyter Notebook）

---

## References

- 仕様書: `specs/008-leader/spec.md`
- データモデル: `specs/008-leader/data-model.md`
- API契約: `specs/008-leader/contracts/leader-agent-api.md`
