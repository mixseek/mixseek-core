# Contract: SKILL.md Format

**Feature**: 023-agent-skills-mixseek
**Date**: 2026-01-21
**Spec**: Agent Skills Specification (agentskills.io/specification)

## 概要

すべてのMixSeek Agent SkillsはこのフォーマットコントラクトにCHAPTER準拠する必要がある。

## YAML Frontmatter Contract

### Required Fields

```yaml
---
name: <skill-name>
description: <skill-description>
---
```

### Field Specifications

#### `name` (Required)

| Property | Value |
|----------|-------|
| Type | string |
| Min Length | 1 |
| Max Length | 64 |
| Pattern | `^[a-z0-9]+(-[a-z0-9]+)*$` |
| Constraints | Must match parent directory name |

**Valid Examples**:
```yaml
name: mixseek-workspace-init
name: mixseek-team-config
name: mixseek-model-list
```

**Invalid Examples**:
```yaml
name: MixSeek-Workspace-Init  # Uppercase not allowed
name: -mixseek-init           # Cannot start with hyphen
name: mixseek--config         # Consecutive hyphens not allowed
name: mixseek_config          # Underscore not allowed
```

#### `description` (Required)

| Property | Value |
|----------|-------|
| Type | string |
| Min Length | 1 |
| Max Length | 1024 |
| Constraints | Non-empty, describes skill function and usage timing |

**Requirements**:
- スキルの機能を明確に説明
- 使用タイミング（トリガーワード）を含める
- タスク識別用キーワードを含める（FR-012）

**Example**:
```yaml
description: MixSeekワークスペースを初期化し、設定ファイル用ディレクトリ構造を作成します。「ワークスペースを初期化」「mixseekのセットアップ」「設定ディレクトリを作成」といった依頼で使用してください。
```

### Forbidden Fields

以下のオプションフィールドは使用しない（仕様決定による）:

- `license`
- `compatibility`
- `metadata`
- `allowed-tools`

## Markdown Body Contract

### Structure

```markdown
# <Skill Title>

## 概要
[スキルの簡潔な説明]

## 前提条件
[必要な環境変数、ツール、権限等]

## 使用方法
[ステップバイステップの手順]

### Step 1: [手順名]
[詳細説明]

### Step 2: [手順名]
[詳細説明]

## 例
[具体的な使用例とコードブロック]

## トラブルシューティング
[よくあるエラーと解決方法]

## 参照
[references/ディレクトリへのリンク]
```

### Constraints

| Property | Value |
|----------|-------|
| Max Lines | 500 (recommended) |
| Format | Markdown (CommonMark) |
| Language | Japanese (primary) |

## Directory Structure Contract

### Minimum Structure

```
<skill-name>/
└── SKILL.md
```

### Full Structure

```
<skill-name>/
├── SKILL.md          # Required
├── scripts/          # Optional: Executable scripts
│   └── *.sh, *.py
├── references/       # Optional: Reference documentation
│   └── *.md
└── assets/           # Optional: Static resources (not used)
```

### Directory Name Contract

- Directory name MUST exactly match the `name` field in frontmatter
- Use kebab-case (lowercase with hyphens)

## Validation Contract

### Using skills-ref CLI

```bash
# Validate skill format
agentskills validate .skills/<skill-name>

# Expected output on success
# (no output, exit code 0)

# Expected output on failure
# Error: <field>: <error message>
```

### Validation Checklist

- [ ] `name` field present and valid
- [ ] `description` field present and non-empty
- [ ] Directory name matches `name` field
- [ ] SKILL.md file exists in directory
- [ ] Body content is valid Markdown
- [ ] No forbidden fields in frontmatter

## Example: Complete SKILL.md

```yaml
---
name: mixseek-workspace-init
description: MixSeekワークスペースを初期化し、設定ファイル用ディレクトリ構造を作成します。「ワークスペースを初期化」「mixseekのセットアップ」「設定ディレクトリを作成」といった依頼で使用してください。
---

# MixSeek ワークスペース初期化

## 概要

MixSeek-Coreのワークスペースディレクトリ構造を初期化します。

## 前提条件

- 環境変数 `MIXSEEK_WORKSPACE` が設定されている（推奨）
- または、対象ディレクトリへの書き込み権限

## 使用方法

### Step 1: ワークスペースパスの確認

ユーザーにワークスペースパスを確認してください。

### Step 2: ディレクトリ作成

以下のスクリプトを実行してディレクトリ構造を作成します:

\`\`\`bash
./scripts/init-workspace.sh <workspace-path>
\`\`\`

## 例

...

## トラブルシューティング

### 書き込み権限エラー

...
```
