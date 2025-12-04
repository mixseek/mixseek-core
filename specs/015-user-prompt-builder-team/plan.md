# Implementation Plan: UserPromptBuilder - プロンプト整形コンポーネント

**Branch**: `092-user-prompt-builder-team` | **Date**: 2025-11-19 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/015-user-prompt-builder-team/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

UserPromptBuilderは、各コンポーネント（Team, Evaluator, JudgementClient）に入力するユーザプロンプトの整形を一元管理するコンポーネントです。現在はRoundControllerで実装されているプロンプト整形ロジックをUserPromptBuilderに移行し、Jinja2テンプレートとTOML設定ファイルを使用してカスタマイズ可能な設計を実現します。これにより、プロンプト精度改善の実験管理が容易になります。

本ブランチでは、各Teamに渡すユーザプロンプト整形のみを実装スコープとし、EvaluatorやJudgementClientへの入力プロンプトは今後の拡張として想定します。

## Technical Context

**Language/Version**: Python 3.13.9 (既存プロジェクト要件に準拠)
**Primary Dependencies**:
  - Jinja2 (>=3.1.0): テンプレートエンジン
  - Pydantic (>=2.12): データモデル・バリデーション
  - pydantic-settings (>=2.12): 設定管理（仕様051-configuration準拠）
  - tomllib (Python 3.13標準ライブラリ): TOML読み込み

**Storage**: N/A (Leader Board取得はDuckDB経由で既存実装を利用)
**Testing**: pytest (既存プロジェクトのテスト戦略に準拠)
**Target Platform**: Linux/macOS/Windows (Pythonクロスプラットフォーム)
**Project Type**: single (mixseek-coreパッケージ内の新規モジュール)
**Performance Goals**:
  - ラウンド1のプロンプト整形: <10ms (95パーセンタイル)
  - ラウンド2以降のプロンプト整形: <50ms (95パーセンタイル、履歴・ランキング情報含む)

**Constraints**:
  - RoundControllerの既存プロンプト整形ロジック（`_format_prompt_for_round`メソッド）と完全に同じ出力を生成すること
  - 既存RoundControllerテスト（`tests/unit/round_controller/test_round_controller.py`）が100%パスすること
  - Article 9 (Data Accuracy Mandate) 準拠: 環境変数TZに基づくtimezone処理、TZ未設定時はUTCをデフォルト使用

**Scale/Scope**:
  - 単一チームのプロンプト整形（本ブランチではTeamのみ、将来的にEvaluator/JudgementClientも対応）
  - ラウンド数制限なし（すべてのラウンド履歴を保持）
  - Leader Boardランキング情報の統合

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Article 1: Library-First Principle - ✅ 準拠
- UserPromptBuilderは独立したライブラリモジュール（`mixseek.prompt_builder`）として実装される
- RoundControllerから分離された再利用可能なコンポーネントとして設計

### Article 2: CLI Interface Mandate - ⚠️ 部分的準拠
- UserPromptBuilder自体は直接CLIを公開しないが、`mixseek config init`コマンドで設定ファイル生成をサポート
- **理由**: プロンプト整形は内部コンポーネントであり、RoundControllerから呼び出される設計のため、独立したCLIは不要

### Article 3: Test-First Imperative - ✅ 準拠予定
- 実装前にユニットテストを作成し、ユーザー承認を取得する
- 既存RoundControllerテストとの互換性を保証するテストを含む

### Article 4: Documentation Integrity - ✅ 準拠
- 仕様書（spec.md）との完全な整合性を保つ
- 実装前に仕様の曖昧性を明確化済み（Clarificationsセクション参照）

### Article 8: Code Quality Standards - ✅ 準拠予定
- コミット前に `ruff check --fix . && ruff format . && mypy .` を実行
- 型安全性とコード品質基準を100%遵守

### Article 9: Data Accuracy Mandate - ✅ 準拠
- **環境変数TZ**: 明示的に環境変数から取得、デフォルト値（UTC）を使用
- **テンプレート設定**: TOML設定ファイルで管理、ハードコード禁止
- **プレースホルダー変数**: 事前に整形された文字列として提供、暗黙的フォールバックなし

### Article 10: DRY Principle - ✅ 準拠
- RoundControllerの既存プロンプト整形ロジックを重複なく移行
- 既存のPydantic Modelを再利用（RoundState、LeaderBoardRankingなど）
- 新規実装ではなく、既存ロジックのリファクタリングとして扱う

### Article 14: SpecKit Framework Consistency - ✅ 準拠
- specs/001-specs のFR-006（ラウンドベース処理）に準拠
- RoundControllerとの統合を前提とした設計

### Article 16: Python Type Safety Mandate - ✅ 準拠予定
- すべての関数・メソッドに型注釈を付与
- mypy strict mode でエラーゼロを保証
- Pydantic Modelで型安全性を確保（PromptBuilderSettings、RoundPromptContextなど）

### Article 17: Python Docstring Standards - ✅ 推奨遵守予定
- Google-style docstringで公開関数・クラスをドキュメント化
- Args, Returns, Raisesセクションを含む包括的な説明を提供

### 🚦 Gate Status: **PASS**
すべての非交渉的原則（Article 3, 4, 8, 9）に準拠しています。Article 2のCLI要件については、内部コンポーネントの性質上、正当な理由で部分的準拠としています。

## Project Structure

### Documentation (this feature)

```
specs/015-user-prompt-builder-team/
├── spec.md              # 機能仕様書（既存）
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output: 技術調査結果
├── data-model.md        # Phase 1 output: データモデル定義
├── quickstart.md        # Phase 1 output: クイックスタートガイド
├── contracts/           # Phase 1 output: API契約定義
│   └── prompt-builder-api.md
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```
src/mixseek/
├── prompt_builder/           # 新規: UserPromptBuilderモジュール
│   ├── __init__.py          # モジュールエクスポート
│   ├── builder.py           # UserPromptBuilderクラス（メインロジック）
│   ├── models.py            # Pydantic Models (PromptBuilderSettings, RoundPromptContext)
│   └── formatters.py        # プレースホルダー変数の整形ロジック
│
├── round_controller/         # 既存: 修正対象
│   └── controller.py        # RoundController._format_prompt_for_roundをUserPromptBuilder呼び出しに置き換え
│
├── cli/
│   └── commands/
│       └── config.py        # 既存: `mixseek config init` コマンドにUserPromptBuilder設定生成を追加
│
└── config/
    └── templates/           # 新規: デフォルトTOMLテンプレート
        └── prompt_builder_default.toml

tests/
├── unit/
│   ├── prompt_builder/       # 新規: UserPromptBuilderユニットテスト
│   │   ├── test_builder.py  # プロンプト整形ロジックのテスト
│   │   ├── test_models.py   # Pydantic Modelのバリデーションテスト
│   │   └── test_formatters.py # フォーマッター関数のテスト
│   │
│   └── round_controller/     # 既存: 既存テストが100%パスすることを確認
│       └── test_round_controller.py
│
└── integration/
    └── test_prompt_builder_integration.py  # 新規: RoundControllerとUserPromptBuilderの統合テスト
```

**Structure Decision**:
- **単一プロジェクト構造** (mixseek-coreパッケージ): 既存のmixseek-core構造に新規モジュール `prompt_builder` を追加
- **責務分離**: プロンプト整形ロジックをRoundControllerから完全に分離し、独立したモジュールとして実装
- **再利用性**: 将来的にEvaluatorやJudgementClientでも利用可能な設計

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

**該当なし**: すべてのConstitution Article準拠。複雑性の正当化は不要です。
