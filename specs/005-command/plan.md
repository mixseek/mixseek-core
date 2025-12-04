# Implementation Plan: mixseekコマンド初期化機能

**Branch**: `004-mixseek-core-command` | **Date**: 2025-10-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/app/specs/005-command/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

mixseek initコマンドは、MixSeekプロジェクトのワークスペース環境を自動的に初期化するCLIツールです。環境変数またはコマンドライン引数でワークスペースパスを指定し、必要なディレクトリ構造（logs、configs、templates）とTOML形式のサンプル設定ファイル（プロジェクト名フィールド含む）を生成します。Python 3.12+とTyperライブラリを使用し、クロスプラットフォーム対応（Linux、macOS、Windows）を実現します。

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: typer (CLI framework), toml/tomli_w (TOML file generation)
**Storage**: ファイルシステム（ディレクトリとTOMLファイルの作成）
**Testing**: pytest, pytest-mock
**Target Platform**: Linux、macOS、Windows (クロスプラットフォーム)
**Project Type**: single (CLI tool)
**Performance Goals**: ワークスペース作成完了まで5秒以内
**Constraints**: クロスプラットフォーム互換性、特殊文字を含むパスのサポート、シンボリックリンク解決
**Scale/Scope**: 単一コマンド実装、3つのサブディレクトリ作成、1つのTOMLサンプルファイル生成

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Article 1: Library-First Principle
✅ **PASS**: CLI機能はライブラリとして実装され、src/mixseek/cli/init.py で提供される

### Article 2: CLI Interface Mandate
✅ **PASS**: 
- stdin/引数/ファイル入力をサポート（--workspace オプション、環境変数MIXSEEK_WORKSPACE）
- stdout/stderrで出力を提供
- TOML形式（JSON互換）をサポート

### Article 3: Test-First Imperative
⚠️ **DEFERRED**: テストは実装フェーズで作成（TDD）

### Article 4: Documentation Integrity
✅ **PASS**: 仕様書（spec.md）との完全な整合性を確保

### Article 5: Simplicity
✅ **PASS**: 単一プロジェクト構造（src/、tests/）、3プロジェクト制限内

### Article 6: Anti-Abstraction
✅ **PASS**: Typerフレームワークを直接使用、不必要なラッパーなし

### Article 7: Integration-First Testing
✅ **PASS**: ファイルシステムを使用した統合テスト優先

### Article 8: Code Quality Standards
⚠️ **DEFERRED**: 実装時にruff check/format、mypy適用

### Article 9: Data Accuracy Mandate
✅ **PASS**: 
- プロジェクト名はプレースホルダー定数として定義
- 環境変数から明示的に取得
- ハードコードされた値なし

### Article 10: DRY Principle
✅ **PASS**: 既存実装の事前調査済み、新規機能

### Article 11: Refactoring Policy
N/A: 新規実装

### Article 12: Documentation Standards
✅ **PASS**: `docs/` ディレクトリでドキュメント管理

### Article 13: Environment & Infrastructure
⚠️ **DEFERRED**: Dockerコンテナ化は将来対応

### Article 14: SpecKit Framework Consistency
✅ **PASS**: MixSeek-Core仕様（specs/001-specs）との整合性を確認
- この機能はMixSeek-Coreフレームワークの一部として実装（D-001）
- Leader Agent/Member Agent/Round Controllerの直接的な実装ではないが、フレームワークのCLIエントリーポイントとして機能
- 将来のmixseek executeコマンドでエージェント実行機能を統合予定

### Article 15: SpecKit Naming Convention
✅ **PASS**: ブランチ名 `004-mixseek-core-command` は命名規則に準拠

**Gate Decision**: ✅ **PROCEED** - すべての必須要件をクリア、実装フェーズへ進行可能

## Project Structure

### Documentation (this feature)

```
specs/005-command/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```
src/mixseek/
├── cli/
│   ├── __init__.py
│   ├── main.py          # Typer app entry point
│   └── commands/
│       ├── __init__.py
│       └── init.py      # mixseek init command implementation
├── config/
│   ├── __init__.py
│   ├── constants.py     # Default values (PROJECT_NAME_PLACEHOLDER, etc.)
│   └── templates.py     # TOML template generation
└── utils/
    ├── __init__.py
    ├── filesystem.py    # Directory creation, path validation
    └── env.py           # Environment variable handling

tests/
├── contract/
│   └── test_init_contract.py    # Contract tests for CLI interface
├── integration/
│   └── test_init_integration.py # Integration tests with real filesystem
└── unit/
    ├── test_filesystem.py       # Unit tests for filesystem utils
    ├── test_env.py               # Unit tests for env handling
    └── test_templates.py         # Unit tests for TOML generation
```

**Structure Decision**: 単一プロジェクト構造を採用。これはCLIツールであり、フロントエンドやモバイルアプリの要素がないため、Option 1（Single project）が最適です。src/mixseek/ 配下にCLI機能を配置し、tests/ でテストを管理します。

## Complexity Tracking

*No constitution violations - this section is empty*

