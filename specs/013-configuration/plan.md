# Implementation Plan: Pydantic Settings based Configuration Manager

**Branch**: `051-configuration` | **Date**: 2025-11-11 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/013-configuration/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

統一的な設定管理システムをpydantic-settingsを基盤として実装します。4つの設計原則（明示性、階層的フォールバック、環境別設定、トレーサビリティ）に基づき、CLI引数、環境変数、.env、TOML、デフォルト値の優先順位を制御します。Article 9（Data Accuracy Mandate）違反箇所を80箇所から10箇所以下に削減し、すべてのモジュール（Leader, Member, Evaluator, Orchestrator, RoundController, UI, CLI）で統一的なConfiguration Managerを使用可能にします。

技術アプローチ: pydantic-settings（基盤） + カスタム設定ソース（CLISource, TracingSourceWrapper） + 薄いラッパー層（ConfigurationManager）のハイブリッドアーキテクチャを採用します。

## Technical Context

**Language/Version**: Python 3.13.9
**Primary Dependencies**: pydantic (>=2.12), pydantic-settings (>=2.12), typer (既存CLIフレームワーク), tomllib (Python 3.11+標準ライブラリ)
**Storage**: N/A（設定ファイルのみ: TOML, .env）
**Testing**: pytest (>=8.3.4), pytest-mock, pytest-asyncio
**Target Platform**: Linux/macOS/Windows（mixseek-coreと同じプラットフォーム）
**Project Type**: single（mixseek-coreパッケージの一部として実装）
**Performance Goals**: 設定読み込み時間 <100ms、トレース情報記録のメモリオーバーヘッド <1MB
**Constraints**: 既存TOMLファイルの後方互換性維持、破壊的変更の最小化、ruff/mypy品質基準準拠
**Scale/Scope**: 約120の設定項目（現在80箇所のArticle 9違反を解消）、6つのモジュール（Leader, Member, Evaluator, Orchestrator, RoundController, UI）統合

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Article 3: Test-First Imperative ✅ PASS
- テスト駆動開発（TDD）を厳格に適用
- 実装前にユニットテストを作成し、ユーザー承認を取得
- Redフェーズ（テスト失敗）を確認後、実装着手

### Article 4: Documentation Integrity ✅ PASS
- すべての実装は仕様書（spec.md）と完全に整合
- 仕様が曖昧な場合は実装を停止し、明確化を要求済み（10回の明確化セッション完了）
- ドキュメント変更時はユーザー承認を取得済み

### Article 8: Code Quality Standards ✅ PASS
- ruff check --fix . && ruff format . && mypy . を実装前に実行
- すべてのコードは品質基準に完全準拠
- CI/CDパイプラインで品質チェック自動実行

### Article 9: Data Accuracy Mandate ✅ PASS (This feature resolves violations)
- **現状**: 80箇所のArticle 9違反（ハードコードされたデフォルト値）が存在
- **本機能の目的**: Article 9違反箇所を10箇所以下に削減
- すべての設定値を明示的なソースから取得（ENV, TOML, CLI）
- ハードコード禁止、暗黙的フォールバック禁止を実現

### Article 10: DRY Principle ✅ PASS
- 実装前にGlob/Grepで既存実装を検索（完了）
- pydantic-settings-configuration-manager-evaluation.mdで既存パターンを調査済み
- 重複実装を回避

### Article 14: SpecKit Framework Consistency ⚠️ CONDITIONAL PASS
- MixSeek-Core仕様（specs/001-specs）との整合性を確認
- Configuration Managerは全コンポーネント（Leader, Member, Evaluator, Orchestrator, RoundController）の設定を統一的に管理
- **条件**: 各コンポーネントの設定スキーマがMixSeek-Core仕様のKey Entitiesと整合していること（Phase 1で検証）

### Article 16: Python Type Safety Mandate ✅ PASS
- すべての関数・メソッドに型注釈を付与
- mypy strict mode を使用（pyproject.toml設定済み）
- Pydantic Modelで型安全性を保証（BaseSettings継承）

### Article 17: Python Docstring Standards ✅ PASS (Recommended)
- Google-style docstringを強く推奨
- すべてのpublic API（ConfigurationManager, カスタムソース）にdocstringを記述

### Gate Status: ✅ ALL GATES PASSED
- 憲法違反なし
- Phase 0（research）に進行可能

## Project Structure

### Documentation (this feature)

```
specs/013-configuration/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── assets/              # Reference materials
│   └── pydantic-settings-configuration-manager.md
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```
src/mixseek/
├── config/                    # NEW: Configuration管理モジュール
│   ├── __init__.py
│   ├── manager.py            # ConfigurationManager（薄いラッパー）
│   ├── schema.py             # 設定スキーマ（BaseSettings継承）
│   └── sources/
│       ├── __init__.py
│       ├── cli_source.py     # CLISource（カスタムソース）
│       └── tracing_source.py # TracingSourceWrapper（トレーサビリティ）
│
├── agents/                    # EXISTING: Agent実装（設定を移行）
│   ├── leader.py             # LeaderAgentSettings使用に移行
│   ├── member.py             # MemberAgentSettings使用に移行
│   └── evaluator.py          # EvaluatorSettings使用に移行
│
├── core/                      # EXISTING: Core実装（設定を移行）
│   └── orchestrator.py       # OrchestratorSettings使用に移行
│
├── ui/                        # EXISTING: UI実装（設定を移行）
│   └── app.py                # UISettings使用に移行
│
└── cli/                       # EXISTING: CLI実装（ConfigurationManager統合）
    ├── commands/
    │   ├── team.py           # ConfigurationManager使用
    │   ├── exec.py           # ConfigurationManager使用
    │   ├── ui.py             # ConfigurationManager使用
    │   └── config.py         # NEW: mixseek config show/list/init コマンド
    └── main.py

tests/
├── unit/
│   └── config/               # NEW: Configuration Manager単体テスト
│       ├── test_schema.py
│       ├── test_sources.py
│       ├── test_manager.py
│       └── test_cli_source.py
│
├── integration/
│   └── config/               # NEW: 統合テスト
│       ├── test_priority.py  # 優先順位テスト
│       ├── test_tracing.py   # トレーサビリティテスト
│       └── test_migration.py # 既存コード移行テスト
│
└── e2e/                       # EXISTING: エンドツーエンドテスト
    └── test_config_workflow.py # NEW: 設定管理ワークフローE2Eテスト
```

**Structure Decision**: Single project（mixseek-coreパッケージ）に新規モジュール`config/`を追加し、既存モジュール（agents, core, ui, cli）の設定管理を統一します。Article 1（Library-First）に従い、config/モジュールは独立したライブラリとして設計され、他モジュールから参照されます。

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

N/A - すべての憲法チェックに合格しており、複雑性の正当化は不要です。
