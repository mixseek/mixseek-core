# Data Model: MixSeek Agent Skills

**Feature**: 023-agent-skills-mixseek
**Date**: 2026-01-21

## 概要

MixSeek Agent Skillsは、Agent Skills仕様（agentskills.io）に準拠したSKILL.mdファイルで定義される。この機能はMarkdownファイルとシェルスクリプト/Pythonスクリプトで構成され、Pydanticモデルの追加は不要。

## Entity定義

### 1. Skill (SKILL.md)

**ファイル形式**: YAML Frontmatter + Markdown Body

```yaml
---
name: string          # 1-64文字、kebab-case、親ディレクトリ名と一致
description: string   # 1-1024文字、スキルの機能と使用タイミング
---

# Markdown Body
[エージェント向け手順]
```

**制約**:
- `name`: `^[a-z0-9]+(-[a-z0-9]+)*$` (1-64文字)
- `description`: 非空、1-1024文字
- Body: 500行以下推奨

### 2. スキル一覧

| スキル名 | ディレクトリ | 目的 |
|---------|-------------|------|
| `mixseek-workspace-init` | `.skills/mixseek-workspace-init/` | ワークスペース初期化 |
| `mixseek-team-config` | `.skills/mixseek-team-config/` | チーム設定生成 |
| `mixseek-orchestrator-config` | `.skills/mixseek-orchestrator-config/` | オーケストレーター設定生成 |
| `mixseek-evaluator-config` | `.skills/mixseek-evaluator-config/` | 評価設定生成 |
| `mixseek-config-validate` | `.skills/mixseek-config-validate/` | 設定検証 |
| `mixseek-model-list` | `.skills/mixseek-model-list/` | モデル一覧取得 |

## ファイル構造

### 3. ワークスペース構造（FR-002）

`mixseek-workspace-init`スキルが作成するディレクトリ構造:

```
$MIXSEEK_WORKSPACE/
├── configs/
│   ├── agents/           # チーム・メンバーエージェント設定
│   ├── evaluators/       # 評価者設定
│   └── judgment/         # 判定設定
├── logs/                 # 実行ログ
└── templates/            # 設定テンプレート
```

**状態遷移**:
- 初期状態: 空ディレクトリまたは存在しない
- 初期化後: 上記ディレクトリ構造が存在
- 再初期化: 既存ファイルを保持、欠損ディレクトリのみ作成

### 4. TOML設定ファイル（生成対象）

#### 4.1 Team設定（team.toml）

```toml
[team]
team_id = "string"              # 必須: 一意ID
team_name = "string"            # 必須: 表示名
max_concurrent_members = 15     # オプション: 1-50

[team.leader]
system_instruction = "string"   # 必須
model = "provider:model-name"   # 必須: 例 "google-gla:gemini-2.5-pro"
temperature = 0.7               # オプション: 0.0-2.0
max_tokens = 2000               # オプション: 正の整数
timeout_seconds = 300           # オプション: デフォルト300
max_retries = 3                 # オプション: デフォルト3

[[team.members]]
agent_name = "string"           # 必須
agent_type = "plain"            # 必須: plain|web_search|code_execution|web_fetch|custom
tool_name = "string"            # オプション: デフォルト "delegate_to_{agent_name}"
tool_description = "string"     # 必須
model = "provider:model-name"   # 必須
system_instruction = "string"   # 必須
temperature = 0.2               # オプション
max_tokens = 2048               # オプション
```

#### 4.2 Orchestrator設定（orchestrator.toml）

```toml
[orchestrator]
timeout_per_team_seconds = 600  # オプション: 10-3600
max_rounds = 5                  # オプション: 1-10
min_rounds = 2                  # オプション: 1以上、max_rounds以下

[[orchestrator.teams]]
config = "configs/agents/team-*.toml"  # 必須: チーム設定へのパス
```

#### 4.3 Evaluator設定（evaluator.toml）

```toml
default_model = "provider:model-name"  # 必須
temperature = 0.0                       # オプション

[[metrics]]
name = "ClarityCoherence"               # 必須: メトリクスクラス名
weight = 0.334                          # オプション: 均等割り当て可

[[metrics]]
name = "Coverage"
weight = 0.333

[[metrics]]
name = "Relevance"
weight = 0.333
```

#### 4.4 Judgment設定（judgment.toml）

```toml
model = "provider:model-name"   # 必須
temperature = 0.0               # オプション: デフォルト0.0（決定論的）
timeout_seconds = 60            # オプション
```

### 5. 参照ファイル（references/）

各スキルの`references/`ディレクトリに配置する詳細ドキュメント:

| ファイル | 配置スキル | 内容 |
|---------|-----------|------|
| `TOML-SCHEMA.md` | team-config, orchestrator-config, evaluator-config | 該当設定のTOMLスキーマ詳細 |
| `MEMBER-TYPES.md` | team-config | Member Agentタイプの説明と使用例 |
| `METRICS.md` | evaluator-config | 標準メトリクスの説明 |
| `VALID-MODELS.md` | model-list | 利用可能モデル一覧 |

### 6. スクリプトファイル（scripts/）

| ファイル | 配置スキル | 言語 | 機能 |
|---------|-----------|------|------|
| `init-workspace.sh` | workspace-init | Bash | ディレクトリ構造作成 |
| `validate-config.py` | config-validate | Python | TOML検証（Pydanticスキーマ使用） |

## バリデーションルール

### SKILL.mdフロントマター

```python
# name フィールド
assert 1 <= len(name) <= 64
assert re.match(r'^[a-z0-9]+(-[a-z0-9]+)*$', name)
assert name == parent_directory_name

# description フィールド
assert 1 <= len(description) <= 1024
assert description.strip() != ""
```

### TOML設定

```python
# モデル形式
assert ":" in model
provider, model_name = model.split(":", 1)
assert provider != "" and model_name != ""

# Orchestrator
assert min_rounds <= max_rounds

# Evaluator weights
if any_weight_specified:
    assert all_weights_specified
    assert 0.999 <= sum(weights) <= 1.001
```

## 関連図

```
┌─────────────────────────────────────────────────────────────────┐
│                     AI Coding Agent                              │
│              (Claude Code / Codex / Gemini CLI)                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    .skills/ Directory                            │
├─────────────────────────────────────────────────────────────────┤
│  mixseek-workspace-init/   │  mixseek-team-config/              │
│  ├── SKILL.md              │  ├── SKILL.md                      │
│  └── scripts/              │  └── references/                   │
│      └── init-workspace.sh │      ├── TOML-SCHEMA.md            │
│                            │      └── MEMBER-TYPES.md           │
├────────────────────────────┼────────────────────────────────────┤
│  mixseek-orchestrator-config/ │  mixseek-evaluator-config/      │
│  ├── SKILL.md                 │  ├── SKILL.md                   │
│  └── references/              │  └── references/                │
│      └── TOML-SCHEMA.md       │      ├── TOML-SCHEMA.md         │
│                               │      └── METRICS.md             │
├───────────────────────────────┼─────────────────────────────────┤
│  mixseek-config-validate/  │  mixseek-model-list/               │
│  ├── SKILL.md              │  ├── SKILL.md                      │
│  └── scripts/              │  └── references/                   │
│      └── validate-config.py│      └── VALID-MODELS.md           │
└────────────────────────────┴────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  $MIXSEEK_WORKSPACE                              │
├─────────────────────────────────────────────────────────────────┤
│  configs/                                                        │
│  ├── agents/         # team-*.toml, member-*.toml               │
│  ├── evaluators/     # evaluator.toml                           │
│  └── judgment/       # judgment.toml                            │
│  orchestrator.toml   # オーケストレーター設定                    │
│  logs/               # 実行ログ                                  │
│  templates/          # 設定テンプレート                          │
│  mixseek.db          # 実行結果（Orchestrator生成）             │
└─────────────────────────────────────────────────────────────────┘
```

## 非Pydanticエンティティ

本機能はMarkdownとスクリプトファイルで構成されるため、新規Pydanticモデルの定義は不要。既存の`src/mixseek/config/schema.py`のスキーマを参照ドキュメントとして活用する。

### 参照する既存Pydanticモデル

| モデル | ファイル | 用途 |
|-------|---------|------|
| `TeamSettings` | `src/mixseek/config/schema.py:1076` | team.toml検証 |
| `LeaderAgentSettings` | `src/mixseek/config/schema.py` | Leader設定 |
| `MemberAgentSettings` | `src/mixseek/config/schema.py` | Member設定 |
| `OrchestratorSettings` | `src/mixseek/config/schema.py:812` | orchestrator.toml検証 |
| `EvaluatorSettings` | `src/mixseek/config/schema.py:614` | evaluator.toml検証 |
| `JudgmentSettings` | `src/mixseek/config/schema.py:721` | judgment.toml検証 |
