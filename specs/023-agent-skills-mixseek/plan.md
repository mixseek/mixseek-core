# Implementation Plan: MixSeek Agent Skills - ワークスペース管理

**Branch**: `023-agent-skills-mixseek` | **Date**: 2026-01-21 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/023-agent-skills-mixseek/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

外部コーディングエージェント（Claude Code、Codex、Gemini CLI等）がMixSeek-Coreのワークスペースを自然言語で管理できるようにするAgent Skillsを実装する。Agent Skills仕様（agentskills.io/specification）に準拠した6つのスキル（workspace-init、team-config、orchestrator-config、evaluator-config、config-validate、model-list）をSKILL.md形式で作成する。

## Technical Context

**Language/Version**: N/A（Markdownベースのスキル定義、バンドルスクリプトはBash/Python 3.13）
**Primary Dependencies**: Agent Skills仕様（agentskills.io）、MixSeek-Core TOML設定スキーマ
**Storage**: N/A（ファイルシステムベース、`.skills/`ディレクトリ配下）
**Testing**: E2Eテスト（Claude Code、Gemini CLIでの動作確認）、skills-ref validate
**Target Platform**: 任意のOS（Agent Skills対応エージェントがインストールされた環境）
**Project Type**: Single（スキル定義ファイル群）
**Performance Goals**: N/A（LLMエージェントの応答速度に依存）
**Constraints**: SKILL.md本体は500行以下推奨、フロントマターはname/descriptionのみ必須
**Scale/Scope**: 6スキル、各スキルは独立して使用可能

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Article | Requirement | Status | Notes |
|---------|------------|--------|-------|
| **Article 3** (Test-First) | テスト駆動開発 | N/A | SKILL.mdはMarkdownファイル。E2Eテスト（Claude Code/Gemini CLIでの動作確認）で代替 |
| **Article 4** (Documentation) | ドキュメント整合性 | ✅ | spec.mdで仕様定義済み、plan.mdで設計 |
| **Article 8** (Code Quality) | 品質基準遵守 | N/A | Markdownファイルにはruff/mypy適用外。skills-ref validateで検証 |
| **Article 9** (Data Accuracy) | ハードコード禁止 | ✅ | 環境変数参照を推奨（FR-011）、認証情報埋め込み禁止 |
| **Article 10** (DRY) | 重複回避 | ✅ | 既存スキル実装なし（新規機能）。参照形式でTOMLテンプレート共有可能 |
| **Article 14** (SpecKit) | フレームワーク整合性 | ✅ | MixSeek-Core設定スキーマ（Leader/Member Agent、TUMIX）に準拠 |
| **Article 15** (Naming) | 命名規則 | ✅ | `023-agent-skills-mixseek`形式準拠 |
| **Article 16** (Type Safety) | 型安全性 | N/A | Markdownファイル、Pythonコードは最小限（スクリプトのみ） |

**Gate評価**: 全Article準拠または適用外。Phase 0進行可能。

## Project Structure

### Documentation (this feature)

```text
specs/023-agent-skills-mixseek/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
.skills/
├── mixseek-workspace-init/
│   ├── SKILL.md                    # ワークスペース初期化スキル
│   └── scripts/
│       └── init-workspace.sh       # ディレクトリ構造作成スクリプト
├── mixseek-team-config/
│   ├── SKILL.md                    # チーム設定生成スキル
│   └── references/
│       ├── TOML-SCHEMA.md          # TOMLスキーマリファレンス
│       └── MEMBER-TYPES.md         # Member Agentタイプ説明
├── mixseek-orchestrator-config/
│   ├── SKILL.md                    # オーケストレーター設定スキル
│   └── references/
│       └── TOML-SCHEMA.md          # オーケストレーターTOMLスキーマ
├── mixseek-evaluator-config/
│   ├── SKILL.md                    # 評価設定スキル
│   └── references/
│       ├── TOML-SCHEMA.md          # 評価者TOMLスキーマ
│       └── METRICS.md              # 標準メトリクス説明
├── mixseek-config-validate/
│   ├── SKILL.md                    # 設定検証スキル
│   └── scripts/
│       └── validate-config.py      # TOML検証Pythonスクリプト
└── mixseek-model-list/
    ├── SKILL.md                    # モデル一覧取得スキル
    └── references/
        └── VALID-MODELS.md         # 利用可能モデル一覧（docs/data/valid-models.csvベース）
```

**Structure Decision**: Agent Skills仕様に準拠したディレクトリ構造。各スキルは独立して動作し、必要に応じて`references/`や`scripts/`で補完資料・実行スクリプトを提供する。

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

該当なし - すべてのArticle準拠または適用外。

## Phase 0: Research (Completed)

調査結果は`research.md`にまとめ済み。主要な決定事項:

1. **Agent Skills仕様**: Progressive Disclosure 3段階パターンを採用
2. **TOML スキーマ**: `src/mixseek/config/schema.py`の既存Pydanticモデルに準拠
3. **skills-ref CLI**: `agentskills validate`コマンドで検証
4. **参考実装**: anthropics/skills リポジトリの構造パターンを採用

## Phase 1: Design (Completed)

生成成果物:

- `data-model.md` - エンティティ定義、ファイル構造、バリデーションルール
- `contracts/skill-format.md` - SKILL.mdフォーマットコントラクト
- `contracts/toml-schemas.md` - TOML設定スキーマコントラクト
- `quickstart.md` - インストール・使用方法ガイド

## Constitution Check (Post-Phase 1)

*Re-evaluated after Phase 1 design completion*

| Article | Requirement | Status | Notes |
|---------|------------|--------|-------|
| **Article 3** (Test-First) | テスト駆動開発 | N/A | SKILL.mdはMarkdownファイル。E2Eテスト（Claude Code/Gemini CLIでの動作確認）で代替 |
| **Article 4** (Documentation) | ドキュメント整合性 | ✅ | spec.md → plan.md → research.md → data-model.md → contracts/ → quickstart.md 完了 |
| **Article 8** (Code Quality) | 品質基準遵守 | ✅ | skills-ref validateで検証。validate-config.pyはruff/mypy適用予定 |
| **Article 9** (Data Accuracy) | ハードコード禁止 | ✅ | 環境変数参照を推奨（FR-011）、デフォルト値はcontracts/toml-schemas.mdで明示 |
| **Article 10** (DRY) | 重複回避 | ✅ | TOMLスキーマはcontracts/toml-schemas.mdで一元管理、各スキルから参照 |
| **Article 14** (SpecKit) | フレームワーク整合性 | ✅ | MixSeek-Core設定スキーマ（Leader/Member Agent、TUMIX）に準拠確認済み |
| **Article 15** (Naming) | 命名規則 | ✅ | `023-agent-skills-mixseek`形式準拠、スキル名は`mixseek-*`形式 |
| **Article 16** (Type Safety) | 型安全性 | ✅ | validate-config.pyは型注釈必須、既存Pydanticモデル使用 |

**Gate評価**: 全Article準拠。Phase 2（/speckit.tasks）進行可能
