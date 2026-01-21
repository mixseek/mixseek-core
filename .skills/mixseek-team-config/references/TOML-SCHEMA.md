# Team Configuration TOML Schema

## 概要

チーム設定ファイル（team.toml）のスキーマ定義です。Leader AgentとMember Agentの構成を定義します。

## ファイル配置

- パス: `$MIXSEEK_WORKSPACE/configs/agents/team-<team-id>.toml`
- 例: `configs/agents/team-web-research.toml`

## 必須フィールド

### [team] セクション

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `team_id` | string | チームの一意ID（kebab-case推奨） |
| `team_name` | string | チームの表示名 |

### [team.leader] セクション

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `system_instruction` | string | Leader Agentへのシステム指示 |
| `model` | string | 使用モデル（形式: `provider:model-name`） |

### [[team.members]] セクション（1つ以上必須）

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `agent_name` | string | エージェント名（チーム内で一意、内部識別用） |
| `agent_type` | enum | エージェントタイプ |
| `tool_name` | string | **Leaderが呼び出すツール名**（重要：後述） |
| `tool_description` | string | LLMに表示するツール説明 |
| `model` | string | 使用モデル |
| `system_instruction` | string | エージェントへのシステム指示 |

#### agent_name vs tool_name（重要）

| 項目 | agent_name | tool_name |
|-----|-----------|-----------|
| **用途** | 内部識別子（ログ、DB記録用） | **Leaderが呼び出すツール名** |
| **使用場所** | MemberSubmission記録、デバッグ | LLMのTool呼び出し |
| **必須** | Yes | No（省略時は`delegate_to_{agent_name}`） |

**重要**: Leaderの`system_instruction`でメンバーを参照する際は、**必ず`tool_name`を使用**してください。

```toml
# 例
[[team.members]]
agent_name = "web_searcher"     # 内部識別子（DB記録用）
tool_name = "search_web"        # Leaderが呼び出す名前 ← これを使う
```

```toml
# Leaderのsystem_instruction
[team.leader]
system_instruction = """
# ❌ 間違い（agent_nameを使用）
web_searcherエージェントに検索を依頼してください。

# ✅ 正しい（tool_nameを使用）
search_webツールで検索を実行してください。
"""
```

## オプションフィールド

### [team] セクション

| フィールド | 型 | デフォルト | 範囲 | 説明 |
|-----------|-----|----------|------|------|
| `max_concurrent_members` | integer | 15 | 1-50 | 同時実行可能なメンバー数 |

### [team.leader] セクション

| フィールド | 型 | デフォルト | 範囲 | 説明 |
|-----------|-----|----------|------|------|
| `temperature` | float | 0.7 | 0.0-2.0 | 生成の多様性 |
| `max_tokens` | integer | - | >0 | 最大トークン数 |
| `timeout_seconds` | integer | 300 | >0 | タイムアウト秒数 |
| `max_retries` | integer | 3 | >=0 | リトライ回数 |
| `top_p` | float | - | 0.0-1.0 | トップP |
| `seed` | integer | - | - | 乱数シード |
| `stop_sequences` | array[string] | - | - | 停止シーケンス |

### [[team.members]] セクション

| フィールド | 型 | デフォルト | 範囲 | 説明 |
|-----------|-----|----------|------|------|
| `tool_name` | string | `delegate_to_{agent_name}` | - | ツール名 |
| `temperature` | float | 0.2 | 0.0-2.0 | 生成の多様性 |
| `max_tokens` | integer | - | >0 | 最大トークン数 |
| `timeout_seconds` | integer | 30 | >0 | タイムアウト秒数 |
| `max_retries` | integer | 3 | >=0 | リトライ回数 |

## agent_type の値

| 値 | 説明 |
|----|------|
| `plain` | 基本テキスト生成 |
| `web_search` | Web検索機能付き |
| `code_execution` | コード実行機能付き |
| `web_fetch` | Webフェッチ機能付き |
| `custom` | カスタムプラグイン |

## モデル形式

```
provider:model-name
```

### 有効なプロバイダー

| プロバイダー | 内部ID | 代表モデル |
|-------------|--------|-----------|
| Google | `google-gla` | gemini-2.5-pro, gemini-2.5-flash |
| Anthropic | `anthropic` | claude-sonnet-4-5-20250929, claude-opus-4-1 |
| OpenAI | `openai` | gpt-5, gpt-4o, o3-mini |
| Grok | `grok` | grok-4-fast |

## バリデーションルール

1. **team_id**: 非空、一意である必要がある
2. **agent_name**: チーム内で一意
3. **tool_name**: チーム内で一意（未指定時は自動生成）
4. **members数**: `max_concurrent_members`以下
5. **model形式**: `provider:model-name` 形式に準拠

```python
# バリデーション例
assert len(team.members) <= team.max_concurrent_members
assert len(agent_names) == len(set(agent_names))  # 一意性
assert ":" in model  # モデル形式
```

## 完全な設定例

### 最小構成

```toml
[team]
team_id = "minimal-team"
team_name = "Minimal Team"

[team.leader]
system_instruction = "あなたはチームリーダーです。"
model = "google-gla:gemini-2.5-pro"

[[team.members]]
agent_name = "worker"
agent_type = "plain"
tool_description = "一般的なタスクを実行します"
model = "google-gla:gemini-2.5-flash"
system_instruction = "あなたはアシスタントです。"
```

### フル構成

```toml
[team]
team_id = "full-team"
team_name = "Full Configuration Team"
max_concurrent_members = 10

[team.leader]
system_instruction = """
あなたは高度なタスク管理を行うチームリーダーです。
各メンバーの専門性を理解し、適切にタスクを割り振ってください。
"""
model = "google-gla:gemini-2.5-pro"
temperature = 0.7
max_tokens = 4000
timeout_seconds = 600
max_retries = 5
top_p = 0.9
seed = 42
stop_sequences = ["[END]", "[DONE]"]

[[team.members]]
agent_name = "researcher"
agent_type = "web_search"
tool_name = "search_web"
tool_description = "最新のWeb情報を検索して取得します"
model = "google-gla:gemini-2.5-flash"
system_instruction = """
あなたはWeb検索の専門家です。
信頼性の高い情報源から最新情報を取得してください。
"""
temperature = 0.2
max_tokens = 2000
timeout_seconds = 60
max_retries = 3

[[team.members]]
agent_name = "coder"
agent_type = "code_execution"
tool_name = "execute_code"
tool_description = "Pythonコードを実行して計算やデータ処理を行います"
model = "anthropic:claude-sonnet-4-5-20250929"
system_instruction = """
あなたはPythonプログラマーです。
安全で効率的なコードを作成・実行してください。
"""
temperature = 0.0
max_tokens = 4000
timeout_seconds = 120
max_retries = 2

[[team.members]]
agent_name = "analyst"
agent_type = "plain"
tool_description = "データを分析し、洞察を提供します"
model = "google-gla:gemini-2.5-flash"
system_instruction = """
あなたはデータアナリストです。
提供されたデータを分析し、有益な洞察を導き出してください。
"""
temperature = 0.3
```

## 参照設定（外部ファイル参照）

メンバー設定を別ファイルで管理する場合:

```toml
[[team.members]]
config = "configs/agents/member-researcher.toml"
tool_name = "search_web"  # オプション: オーバーライド
tool_description = "Web検索を実行"  # tool_name指定時は必須
```
