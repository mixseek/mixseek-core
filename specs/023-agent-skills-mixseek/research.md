# Research: MixSeek Agent Skills

**Feature**: 023-agent-skills-mixseek
**Date**: 2026-01-21

## 1. Agent Skills仕様の詳細理解

### 1.1 SKILL.md フォーマット仕様

**Decision**: Agent Skills仕様（agentskills.io/specification）に厳密に準拠する

**Rationale**:
- FR-001で必須参照として明記
- 標準フォーマットに準拠することで、Claude Code、Codex、Gemini CLI等の複数エージェントで動作保証

**YAML Frontmatter構造**:

| フィールド | 必須 | 制約 |
|-----------|------|------|
| `name` | Yes | 1-64文字、小文字英数字とハイフンのみ、先頭/末尾ハイフン禁止、連続ハイフン禁止、親ディレクトリ名と一致必須 |
| `description` | Yes | 1-1024文字、非空、スキルの機能と使用タイミングを記述 |
| `license` | No | 使用しない（仕様で未使用と決定）|
| `compatibility` | No | 使用しない |
| `metadata` | No | 使用しない |
| `allowed-tools` | No | 使用しない |

**Markdownボディ要件**:
- 制限なし（自由形式）
- 推奨: 500行以下
- 詳細資料は`references/`ディレクトリに分離

### 1.2 Progressive Disclosure パターン

**Decision**: 3段階のコンテキスト管理パターンを採用

**Stage 1: Discovery（~100トークン）**
- エージェント起動時に`name`と`description`のみロード
- タスク識別用キーワードを`description`に含める（FR-012）

**Stage 2: Activation（<5000トークン推奨）**
- タスクがスキルのdescriptionにマッチした時にSKILL.md本体をロード
- メインの手順と例を含む

**Stage 3: Execution（必要時）**
- `scripts/`、`references/`、`assets/`のファイルをオンデマンドでロード

### 1.3 ディレクトリ構造

**Decision**: 以下の標準構造を採用

```
skill-name/
├── SKILL.md          # 必須: メタデータ + 手順
├── scripts/          # オプション: 実行可能スクリプト
├── references/       # オプション: 詳細ドキュメント
└── assets/           # オプション: テンプレート・リソース
```

**`scripts/`ディレクトリのベストプラクティス**:
- 自己完結型または依存関係を明記
- ヘルプフルなエラーメッセージを含める
- エッジケースを適切に処理
- サポート言語: Python、Bash、JavaScript

**`references/`ディレクトリの構造化**:
- `REFERENCE.md` - 詳細技術リファレンス
- ドメイン固有ファイル（例: `TOML-SCHEMA.md`）
- 各ファイルは焦点を絞り小さく保つ

**Alternatives considered**:
- 単一SKILL.mdファイルのみ: シンプルだが、TOMLスキーマ等の詳細情報を含めると500行を超過する可能性
- `assets/`でテンプレート提供: 検討したが、TOMLテンプレートはSKILL.md内のコードブロックで十分

## 2. MixSeek-Core TOMLスキーマの整理

### 2.1 Team設定スキーマ

**Decision**: 既存のPydanticスキーマ（`src/mixseek/config/schema.py`）に準拠

**必須フィールド**:
```toml
[team]
team_id = "unique-id"           # チームの一意ID
team_name = "Team Name"         # チーム表示名

[team.leader]
system_instruction = "..."      # Leader Agentの指示
model = "provider:model-name"   # LLMモデル指定

[[team.members]]
agent_name = "member-name"      # Member Agent名
agent_type = "plain"            # エージェントタイプ
tool_description = "..."        # ツール説明（必須）
model = "provider:model-name"   # LLMモデル
system_instruction = "..."      # システム指示
```

**オプションフィールド**:
- `max_concurrent_members` (デフォルト: 15、範囲: 1-50)
- `temperature` (0.0-2.0)
- `max_tokens` (正の整数)
- `timeout_seconds` (デフォルト: 300)
- `max_retries` (デフォルト: 3)
- `top_p`, `seed`, `stop_sequences`

**Member Agentタイプ（FR-004）**:
1. `plain` - 基本テキスト生成
2. `web_search` - Web検索機能付き
3. `code_execution` - コード実行機能付き
4. `web_fetch` - Webフェッチ機能付き
5. `custom` - カスタムプラグイン

### 2.2 Orchestrator設定スキーマ

**必須フィールド**:
```toml
[orchestrator]
# チーム参照（1つ以上必須）
[[orchestrator.teams]]
config = "configs/agents/team-*.toml"
```

**オプションフィールド**:
- `timeout_per_team_seconds` (デフォルト: 300、範囲: 10-3600)
- `max_rounds` (デフォルト: 5、範囲: 1-10)
- `min_rounds` (デフォルト: 2、範囲: 1以上)
- `submission_timeout_seconds` (デフォルト: 300)
- `judgment_timeout_seconds` (デフォルト: 60)

**検証ルール**: `min_rounds <= max_rounds`

### 2.3 Evaluator設定スキーマ

**必須フィールド**:
```toml
default_model = "provider:model-name"

[[metrics]]
name = "ClarityCoherence"  # メトリクス名
# weightは省略可能（均等割り当て）
```

**標準メトリクス**:
1. `ClarityCoherence` - 明確性と一貫性
2. `Coverage` - カバレッジ
3. `Relevance` - 関連性

**重み付けルール**:
- すべて指定 or すべて省略
- 合計は1.0 ± 0.001

### 2.4 Judgment設定スキーマ

**必須フィールド**:
```toml
model = "provider:model-name"
```

**オプションフィールド**:
- `temperature` (デフォルト: 0.0、決定論的)
- `max_tokens`, `timeout_seconds`, `max_retries`

### 2.5 モデル指定形式

**Decision**: `"provider:model-name"` 形式を使用

**Rationale**:
- MixSeek-Core既存スキーマとの整合性
- 複数プロバイダーの明示的区別

**プロバイダー一覧** (`docs/data/valid-models.csv`より):
| プロバイダー | MixSeek内部ID | 代表モデル |
|-------------|---------------|-----------|
| Google | `google-gla` | gemini-2.5-pro, gemini-2.5-flash |
| Anthropic | `anthropic` | claude-sonnet-4-5-20250929, claude-opus-4-1 |
| OpenAI | `openai` | gpt-5, gpt-4o, o3-mini |
| Grok | `grok` | grok-4-fast |

**デフォルトモデル（仕様より）**:
- Leader Agent: `google-gla:gemini-2.5-pro`
- Member Agent: `google-gla:gemini-2.5-flash`

## 3. skills-ref CLIツールの使用方法

### 3.1 インストール

**Decision**: 開発者向けにインストール方法を`quickstart.md`に記載

```bash
# pip
pip install skills-ref

# uv
uv add skills-ref
```

**バージョン**: 0.1.1 (2026-01-10リリース)
**Python要件**: >=3.11 (3.11, 3.12, 3.13サポート)

### 3.2 検証コマンド

```bash
# スキルの検証
agentskills validate path/to/skill

# プロパティの読み取り（JSON出力）
agentskills read-properties path/to/skill

# プロンプトXML生成
agentskills to-prompt path/to/skill-a path/to/skill-b
```

### 3.3 検証項目

- YAMLフロントマターの有効性
- 命名規則準拠（name フィールド）
- 必須フィールドの存在
- フィールド制約（長さ、形式）

## 4. 既存Agent Skillsの参考実装

### 4.1 anthropics/skills リポジトリ分析

**リポジトリ**: https://github.com/anthropics/skills
- 47.3k stars, 4.5k forks
- Apache 2.0 ライセンス

**スキルカテゴリ**:
1. Creative & Design
2. Development & Technical
3. Enterprise & Communication
4. Document Skills (docx, pdf, pptx, xlsx)

### 4.2 効果的なSKILL.md構造パターン

**Decision**: 以下の構造を採用

```markdown
---
name: skill-identifier
description: スキルの機能と使用タイミングを明確に記述
---

# スキル名

## 概要
[スキルの簡潔な説明]

## 前提条件
[必要な環境変数、ツール等]

## 使用方法
[ステップバイステップの手順]

## 例
[具体的な使用例]

## トラブルシューティング
[よくあるエラーと解決方法]
```

**Rationale**:
- Progressive Disclosureに最適化
- エージェントが理解しやすい構造
- エッジケースの事前説明

## 5. 実装決定事項まとめ

| 決定項目 | 選択 | 理由 |
|---------|------|------|
| フロントマター | `name` + `description` のみ | FR-001、仕様準拠 |
| ディレクトリ構造 | `.skills/mixseek-*` | Agent Skills仕様準拠、仕様の命名規則 |
| スクリプト言語 | Bash（init）、Python（validate） | 環境依存最小化、MixSeek-Core統合 |
| TOML生成方式 | SKILL.md内テンプレート + エージェント生成 | 柔軟性と型安全性のバランス |
| 参照ファイル形式 | Markdown（TOML-SCHEMA.md等） | エージェント可読性 |
| 検証ツール | skills-ref + mixseekコマンド | 標準検証 + MixSeek固有検証 |
