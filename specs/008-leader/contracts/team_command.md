# Contract: `mixseek team` コマンド

**Date**: 2025-10-22
**Feature**: 026-mixseek-core-leader
**Type**: CLI Command Contract

## Overview

`mixseek team`は開発・テスト用のCLIコマンドで、チーム設定TOMLを指定して複数Member Agentを実行し、集約結果を出力します。specs/027の`mixseek member`コマンドと同様のパターンに従います。

**重要**: 本コマンドは開発・テスト専用です。本番環境ではOrchestration Layerを使用してください。

---

## Command Signature

```bash
mixseek team PROMPT [OPTIONS]
```

### Arguments

- `PROMPT`: ユーザープロンプト（必須、文字列）

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--config PATH, -c` | Path | - | チーム設定TOMLファイルパス |
| `--output-format FORMAT, -f` | Choice | text | 出力形式（json/text） |
| `--save-db` | Flag | False | DuckDBに保存（デバッグ用） |
| `--verbose` | Flag | False | 詳細ログ出力 |
| `--timeout SECONDS` | Integer | 60 | チーム全体のタイムアウト（秒） |

---

## Command Behavior

### Normal Flow (FR-022, FR-023)

```bash
$ mixseek team "データを分析してください" --config team.toml

⚠️  WARNING: This is a development/testing command only.
⚠️  For production use, use Orchestration Layer instead.

Executing team 'Analysis Team' with 3 Member Agents...
✓ data-analyst: Success (1.2s, 350 tokens)
✓ web-searcher: Success (2.1s, 420 tokens)
✗ slow-agent: Failed (timeout)

Aggregation Summary:
- Total Agents: 3
- Successful: 2
- Failed: 1
- Total Tokens: 770 (input: 280, output: 490)

Aggregated Content:
==================

## data-analyst の応答:

データ分析の結果...

---

## web-searcher の応答:

Web検索により...

==================
```

### JSON Output (FR-024)

```bash
$ mixseek team "prompt" --config team.toml --output-format json

{
  "warning": "Development/testing command only",
  "team_name": "Analysis Team",
  "team_id": "team-dev-001",
  "round_number": 1,
  "total_count": 3,
  "success_count": 2,
  "failure_count": 1,
  "aggregated_content": "## data-analyst の応答:\n\n...",
  "total_usage": {
    "input_tokens": 280,
    "output_tokens": 490,
    "requests": 2
  },
  "successful_agents": [
    {
      "agent_name": "data-analyst",
      "agent_type": "code_execution",
      "execution_time_ms": 1200
    },
    {
      "agent_name": "web-searcher",
      "agent_type": "web_search",
      "execution_time_ms": 2100
    }
  ],
  "failed_agents": [
    {
      "agent_name": "slow-agent",
      "error_message": "Timeout exceeded: 60s"
    }
  ]
}
```

### Database Save (FR-025)

```bash
$ mixseek team "prompt" --config team.toml --save-db

⚠️  WARNING: Development/testing command only.

Executing team 'Analysis Team' with 3 Member Agents...
✓ Aggregation completed
✓ Saved to DuckDB: $MIXSEEK_WORKSPACE/mixseek.db
  - Table: round_history (team-dev-001, round 1)
  - Table: leader_board (score: 0.0, no evaluation)

Query saved data:
  SELECT * FROM round_history WHERE team_id='team-dev-001'
```

---

## Error Handling

### 環境変数未設定 (FR-021, 憲章Article 9)

```bash
$ mixseek team "prompt" --config team.toml

ERROR: MIXSEEK_WORKSPACE environment variable is not set.

Please set it:
  export MIXSEEK_WORKSPACE=/path/to/workspace

Then run 'mixseek init' to initialize the workspace.
```

**Exit Code**: 1

### チーム設定ファイル不存在

```bash
$ mixseek team "prompt" --config missing.toml

ERROR: Team config file not found: missing.toml

Please check:
  - File path is correct
  - File exists and is readable
  - Use absolute path or relative to current directory
```

**Exit Code**: 1

### 全Member Agent失敗 (Edge Case)

```bash
$ mixseek team "prompt" --config team.toml

⚠️  WARNING: Development/testing command only.

Executing team 'Analysis Team' with 3 Member Agents...
✗ agent-1: Failed (timeout)
✗ agent-2: Failed (API error)
✗ agent-3: Failed (validation error)

ERROR: All 3 Member Agents failed. Team disqualified.

Failed agents:
  - agent-1: Timeout exceeded: 60s
  - agent-2: API connection error
  - agent-3: Invalid response format
```

**Exit Code**: 1

---

## Team Config TOML Format

### 方式1: インライン定義

全設定をteam.toml内に直接記述：

```toml
# team.toml (インライン定義)

[team]
name = "Analysis Team"
description = "Data analysis team"
team_id = "team-dev-001"

[[team.members]]
name = "data-analyst"
type = "code_execution"
model = "anthropic:claude-sonnet-4"

[team.members.instructions]
text = "You are a data analyst"
```

### 方式2: 参照形式（DRY準拠、FR-025）

既存のMember Agent TOMLファイルを参照：

```toml
# team.toml (参照形式)

[team]
name = "Analysis Team"

[[team.members]]
config = "agents/data-analyst.toml"  # Member Agent TOMLを参照

[[team.members]]
config = "agents/web-researcher.toml"
```

**agents/data-analyst.toml**:
```toml
[agent]
name = "data-analyst"
type = "code_execution"
model = "anthropic:claude-sonnet-4"

[agent.instructions]
text = "You are a data analyst"
```

### 方式3: 混在

```toml
[[team.members]]
config = "agents/analyst.toml"  # 参照

[[team.members]]
name = "custom"  # インライン
type = "plain"
model = "google-gla:gemini-2.5-flash-lite"

[team.members.instructions]
text = "Custom agent"
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0    | Success（集約完了、1つ以上の成功応答） |
| 1    | Error（環境変数未設定、全Agent失敗、設定エラー等） |
| 2    | Invalid arguments（--configと--agentの両方指定等） |

---

## Output Formats

### Structured Text (Default)

- 警告メッセージ
- 実行サマリー
- 集約コンテンツ（Markdown形式）
- リソース使用量

### JSON (--output-format json)

```json
{
  "warning": "...",
  "team_name": "...",
  "total_count": 3,
  "success_count": 2,
  "aggregated_content": "...",
  "total_usage": {...}
}
```

### Text (--output-format text)

- aggregated_contentのみ出力（自動化スクリプト用）

---

## Testing Contract

### Unit Tests

```python
class TestTeamCommand:
    def test_command_with_config(self) -> None:
        """正常系: チーム設定TOML指定"""
        # Given: 有効なteam.toml
        # When: mixseek team "prompt" --config team.toml
        # Then: 集約結果出力、exit code 0

    def test_all_agents_failed(self) -> None:
        """異常系: 全Agent失敗"""
        # Given: 全てタイムアウトする設定
        # When: コマンド実行
        # Then: エラーメッセージ、exit code 1

    def test_environment_variable_missing(self) -> None:
        """異常系: MIXSEEK_WORKSPACE未設定"""
        # Given: 環境変数未設定
        # When: コマンド実行
        # Then: EnvironmentError、exit code 1
```

---

## Comparison with `mixseek member`

| 項目 | `mixseek member` | `mixseek team` |
|------|-----------------|---------------|
| **対象** | 単一Member Agent | チーム（複数Member Agent） |
| **設定** | agent.toml | team.toml（members配列） |
| **出力** | Agent単一応答 | 集約結果（aggregated_content） |
| **用途** | Member Agent個別テスト | チーム全体テスト |
| **DB保存** | オプション | オプション（--save-db） |
| **警告** | 開発・テスト専用 | 開発・テスト専用 |

---

## References

- **仕様書**: `specs/008-leader/spec.md` (FR-022〜FR-025)
- **参考**: `specs/009-member/spec.md` (`mixseek member`コマンド)
- **憲章**: `.specify/memory/constitution.md` (Article 2)
