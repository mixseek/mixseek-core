# Implementation Plan: GitHub Actions CI Pipeline

**Branch**: `102-ci-github-actions` | **Date**: 2025-11-19 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/017-ci-github-actions/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

GitHub Actions上でuvを活用したCI/CDパイプラインを構築する。developまたはmainブランチへのPR作成時に、コード品質チェック(ruff, mypy)、自動テスト(pytest)、ドキュメントビルド(Sphinx)を自動実行し、すべての必須チェックが成功するまでマージを禁止する。uvの公式ガイドに従ったキャッシング機能により、CI実行時間を通常5分以内に短縮する。

## Technical Context

**Language/Version**: Python 3.13.7 (プロジェクトルートの .python-version から読み取り)
**Primary Dependencies**: uv (GitHub Actions公式ガイド), ruff, mypy, pytest, Sphinx
**Storage**: N/A (CIはステートレス)
**Testing**: pytest (pyproject.toml設定済み)
**Target Platform**: GitHub Actions runner (ubuntu-latest)
**Project Type**: Single Python package with CLI
**Performance Goals**: CIパイプライン全体の実行時間5分以内(キャッシュ有効時)
**Constraints**: CI最大実行時間15分、全チェックが独立して並列実行可能であること
**Scale/Scope**: 単一リポジトリ、2つのターゲットブランチ(develop, main)、4つの独立したステータスチェック

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Article 1: Library-First Principle
**Status**: ✅ PASS
**Rationale**: CIパイプラインはインフラストラクチャであり、アプリケーション機能ではないため、Article 1は適用対象外。GitHub Actionsワークフローファイルとして実装される。

### Article 2: CLI Interface Mandate
**Status**: ✅ PASS
**Rationale**: CIパイプラインはCLIツール(uv, ruff, mypy, pytest, sphinx-build)を直接呼び出すが、それ自体がCLIインターフェースを提供する必要はない。Article 2は適用対象外。

### Article 3: Test-First Imperative
**Status**: ✅ PASS
**Rationale**: CIパイプライン自体のテストは、PRを作成し実際にCIが実行されることで検証される(E2Eテスト方式)。ワークフローファイルに対するユニットテストは実用性が低いため、実際のPRベースの検証を優先する。

### Article 4: Documentation Integrity
**Status**: ✅ PASS
**Rationale**: spec.mdとplan.mdで要件を明確化済み。実装はこれらのドキュメントに完全に準拠する。

### Article 5: Simplicity
**Status**: ✅ PASS
**Rationale**: 単一の `.github/workflows/ci.yml` ファイルのみを作成。新規プロジェクトは追加しない。

### Article 6: Anti-Abstraction
**Status**: ✅ PASS
**Rationale**: GitHub Actionsの標準機能とuvの公式ガイドをそのまま活用。カスタムラッパーや不必要な抽象化は行わない。

### Article 7: Integration-First Testing
**Status**: ✅ PASS
**Rationale**: CIパイプラインそのものが統合テストの一形態。実際のPR作成→CI実行のフローで検証する。

### Article 8: Code Quality Standards
**Status**: ✅ PASS
**Rationale**: YAMLワークフローファイルにはruff/mypyは適用されないが、CIパイプライン自体がこれらのツールを実行し、品質基準を強制する役割を持つ。

### Article 9: Data Accuracy Mandate
**Status**: ✅ PASS
**Rationale**: Pythonバージョンは `.python-version` から動的に読み取り、ハードコードを回避する。タイムアウト等の設定値は明示的に定義する。

### Article 10: DRY Principle
**Status**: ✅ PASS
**Rationale**: 既存のCI設定が存在しないことを確認済み(`.github/workflows/` ディレクトリが未作成)。重複は発生しない。

### Article 11: Refactoring Policy
**Status**: ✅ PASS
**Rationale**: 新規実装のため、既存コードのリファクタリングは不要。

### Article 12: Documentation Standards
**Status**: ✅ PASS
**Rationale**: spec.md, plan.md, quickstart.mdを `specs/017-ci-github-actions/` に配置。Markdown形式を使用。

### Article 13: Environment & Infrastructure
**Status**: ✅ PASS
**Rationale**: GitHub Actionsはクラウド実行環境であり、Dockerコンテナ化は不要。uvを使用した環境構築により再現性を保証する。

### Article 14: SpecKit Framework Consistency
**Status**: ✅ PASS
**Rationale**: CIパイプラインはMixSeek-Coreの機能実装ではなく、開発インフラストラクチャ。MixSeek-Core仕様(specs/001-specs)との整合性検証は不要。

### Article 15: SpecKit Naming Convention
**Status**: ✅ PASS
**Rationale**: ディレクトリ名 `102-ci-github-actions` は、MixSeek-Coreの機能ではないため `mixseek-core` プレフィックスは不要。インフラストラクチャ機能として正しい命名。

### Article 16: Python Type Safety Mandate
**Status**: ✅ PASS
**Rationale**: YAMLワークフローファイルにはPython型注釈は適用されないが、CIパイプライン自体がmypyを実行し、プロジェクト全体の型安全性を保証する役割を持つ。

### Article 17: Python Docstring Standards
**Status**: ✅ PASS
**Rationale**: YAMLワークフローファイルにはPython docstringは適用されないが、適切なコメントでワークフローの目的と動作を説明する。

## Project Structure

### Documentation (this feature)

```
specs/017-ci-github-actions/
├── plan.md              # This file (Phase 0-1 output)
├── spec.md              # Feature specification (pre-existing)
├── research.md          # Phase 0 output (technology research)
├── data-model.md        # Phase 1 output (conceptual data model)
├── quickstart.md        # Phase 1 output (implementation guide)
├── contracts/           # Phase 1 output (interface contracts)
│   ├── workflow.yml     # CI workflow contract definition
│   └── README.md        # Contract documentation
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT yet created)
```

### Source Code (repository root)

CIパイプラインはインフラストラクチャ機能であり、アプリケーションコードは含まれません。以下のファイルのみを作成します:

```
.github/
└── workflows/
    └── ci.yml           # GitHub Actions CI workflow (実装対象)

# 既存ファイル(CI実行時に参照)
.python-version           # Pythonバージョン定義
pyproject.toml            # ruff, mypy, pytest, Sphinx設定
uv.lock                   # 依存関係ロックファイル
docs/                     # Sphinxドキュメント
src/                      # ソースコード(チェック対象)
tests/                    # テストコード(実行対象)
```

**Structure Decision**: GitHub Actions標準のディレクトリ構造(`.github/workflows/`)を使用します。単一のワークフローファイル(`ci.yml`)のみを作成し、複雑性を最小限に抑えます(Article 5: Simplicity準拠)。

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
