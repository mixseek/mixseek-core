# Implementation Plan: LLMモデル互換性検証

**Branch**: `036-model-validation` | **Date**: 2025-10-22 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/011-model-validation/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

llm-discoveryコマンド（`uvx llm-discovery export`）で取得した最新のモデルリストから会話モデルを抽出し、mixseekの各エージェント種別およびPydantic AIモデル種別との技術互換性を判定する。さらに、互換性があると判定されたモデルに対してAPIテストプロンプトを送信し、接続成功率・レイテンシ・トークン消費・エラーレートを測定する。最終的に、検証結果をTOML互換性マトリクスとMarkdownレポートとして出力し、推奨モデルの選定を支援する。

**技術アプローチ**: Pydantic BaseModelによる堅牢なデータ検証、スケーラブルなvalidatorパッケージ構成、指数バックオフによる再試行機能、コスト上限管理機能を実装する。

## Technical Context

**Language/Version**: Python 3.13.9
**Primary Dependencies**: pydantic >=2.10.6, pydantic-ai >=0.0.18, google-adk >=1.5.0, claude-agent-sdk >=0.1.0
**Storage**: TOMLファイル(入力)、TOMLファイル+Markdownファイル(出力)
**Testing**: pytest >=8.3.4, pytest-mock, pytest-asyncio
**Target Platform**: Linux server (ローカル開発環境またはCI/CD環境)
**Project Type**: 単一Pythonパッケージ (CLIツール + ライブラリ)
**Performance Goals**: 最大70モデルの検証を2時間以内に完了、累計APIコストを$1.00未満に抑制
**Constraints**: API検証は実コスト発生、レート制限対応必須、累計コスト上限の厳格な管理
**Scale/Scope**: llm-discoveryで取得した全モデル（約143件、動的に変化）から会話モデル（45-70件想定）を抽出・検証、3種類のプロバイダー(Google/Anthropic/OpenAI)対応

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Article 1: Library-First Principle ✅
- **Status**: PASS
- **Rationale**: 本機能はmixseek-coreライブラリの一部として実装され、スタンドアロンライブラリとして機能する。

### Article 2: CLI Interface Mandate ✅
- **Status**: PASS
- **Rationale**: CLIコマンド経由で実行可能、JSON/TOML/CSV入力対応、TOML/Markdown出力対応、エラーはstderrに出力。

### Article 3: Test-First Imperative ✅
- **Status**: PASS
- **Rationale**: Phase 1でテストを先行作成し、ユーザー承認を得た後に実装を開始する。

### Article 4: Documentation Integrity ✅
- **Status**: PASS
- **Rationale**: spec.md、plan.md、data-model.md、quickstart.mdを整備し、実装前に仕様を確定する。

### Article 8: Code Quality Standards ✅
- **Status**: PASS
- **Rationale**: コミット前に `ruff check --fix . && ruff format . && mypy .` を実行し、品質基準を厳守する。

### Article 9: Data Accuracy Mandate ✅
- **Status**: PASS
- **Rationale**: 入力データは明示的なTOMLファイルから取得、コスト上限は環境変数またはCLI引数で指定、ハードコードは一切行わない。

### Article 10: DRY Principle ✅
- **Status**: PASS
- **Rationale**: 既存のConfigValidator(src/mixseek/config/validators.py)を`validators/config.py`に移行し、共通ロジックを`validators/base.py`に集約。

### Article 16: Python Type Safety Mandate ✅
- **Status**: PASS
- **Rationale**: すべてのデータモデルをPydantic BaseModelで定義し、mypy strict modeで型チェックを実施する。

**総合判定**: ✅ PASS - すべての必須Article要件を満たしている。Phase 0研究に進むことができる。

## Project Structure

### Documentation (this feature)

```
specs/[###-feature]/
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
├── validators/                         # 本機能で追加・拡張
│   ├── __init__.py                    # 公開APIをエクスポート
│   ├── base.py                        # BaseValidator (共通基底クラス)
│   ├── config.py                      # ConfigValidator (既存から移行)
│   ├── api.py                         # APIValidator (本機能で追加)
│   ├── model.py                       # ModelValidator (モデル構造検証)
│   └── compatibility.py               # CompatibilityValidator (互換性判定)
├── models/
│   ├── model_catalog.py               # モデルカタログ項目のPydanticモデル
│   ├── compatibility_result.py        # 互換性判定結果のPydanticモデル
│   ├── validation_metrics.py          # 検証メトリクスのPydanticモデル
│   └── recommendation_report.py       # 推奨レポートのPydanticモデル
├── services/
│   ├── model_extractor.py             # 会話モデル抽出サービス
│   ├── compatibility_checker.py       # 互換性判定サービス
│   ├── api_validator.py               # API検証サービス
│   └── report_generator.py            # レポート生成サービス
└── cli/
    └── model_validation.py            # CLI実装

tests/
├── unit/
│   ├── validators/
│   │   ├── test_api.py
│   │   ├── test_model.py
│   │   └── test_compatibility.py
│   ├── models/
│   │   └── test_model_catalog.py
│   └── services/
│       ├── test_model_extractor.py
│       ├── test_compatibility_checker.py
│       ├── test_api_validator.py
│       └── test_report_generator.py
├── integration/
│   └── test_full_validation_flow.py
└── fixtures/
    ├── sample_models.toml
    └── expected_output.toml
```

**Structure Decision**:
- **単一Pythonパッケージ構成** (Option 1)を選択
- **validators/パッケージ**: 既存のConfigValidatorを移行し、新規validator(API/Model/Compatibility)を追加
- **models/**: Pydantic BaseModelでデータモデルを定義
- **services/**: ビジネスロジックを責務ごとに分離
- **cli/**: CLIエントリーポイント
- **tests/**: ユニット・インテグレーションテストを分離、fixturesで共有テストデータを管理

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

**該当なし**: すべてのConstitution Check項目をPASSしており、違反はない。
