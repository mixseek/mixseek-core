# 実装計画: UserPromptBuilder - Evaluator/JudgementClient統合

**ブランチ**: `140-user-prompt-builder-evaluator-judgement` | **日付**: 2025-11-25 | **仕様**: [spec.md](./spec.md)
**入力**: 機能仕様書 `/specs/021-user-prompt-builder-evaluator-judgement/spec.md`

**注記**: このテンプレートは `/speckit.plan` コマンドによって記入されます。実行ワークフローについては `.specify/templates/commands/plan.md` を参照してください。

## 概要

本機能は、既存のUserPromptBuilder（specs/015-user-prompt-builder-team）を拡張し、EvaluatorとJudgementClientのユーザプロンプト整形処理を統合します。主要要件：

- **Evaluatorプロンプト整形**: LLMJudgeMetric._get_user_promptメソッドをUserPromptBuilderのbuild_evaluator_promptメソッドに移行し、user_queryとsubmissionを受け取るEvaluatorPromptContextを導入
- **JudgementClientプロンプト整形**: JudgmentClient._format_user_promptメソッドをUserPromptBuilderのbuild_judgment_promptメソッドに移行し、既存のRoundPromptContextを利用
- **設定ファイル拡張**: prompt_builder.tomlにevaluator_user_promptとjudgment_user_promptを追加
- **デフォルトプロンプト**: 既存実装と同等のフォーマットをデフォルト値として提供

技術アプローチ：
- Jinja2テンプレートエンジンによるプロンプト整形
- Pydantic Modelによる型安全なコンテキスト定義
- 既存のTeamプロンプト整形パターンを踏襲した設計
- prompt_builder.formattersの既存実装（format_submission_history, format_ranking_table, generate_position_message）を再利用

## 技術コンテキスト

**言語/バージョン**: Python 3.13.9
**主要依存関係**: Jinja2 (>=3.1.0), Pydantic (>=2.12), pydantic-settings (>=2.12), tomllib (Python 3.11+標準ライブラリ)
**ストレージ**: N/A（設定ファイル: $MIXSEEK_WORKSPACE/configs/prompt_builder.toml）
**テスト**: pytest, pytest-mock, pytest-asyncio
**対象プラットフォーム**: Linux/macOS/Windows（Python実行環境）
**プロジェクトタイプ**: single（既存のmixseek-coreパッケージへの機能追加）
**パフォーマンス目標**:
  - build_evaluator_prompt: 10ms以内（95パーセンタイル）
  - build_judgment_prompt: 50ms以内（95パーセンタイル、複数ラウンド履歴を含む）
**制約**:
  - 既存実装との後方互換性維持（同一の出力フォーマット）
  - Evaluator、JudgementClientの既存テストケース100%パス
  - プレースホルダー変数の明示的エラーハンドリング（Jinja2 UndefinedError）
**スコープ**:
  - 新規メソッド: 2個（build_evaluator_prompt, build_judgment_prompt）
  - 新規Pydantic Model: 1個（EvaluatorPromptContext: user_query, submission）
    - **Note**: current_datetimeはコンテキストに含めず、UserPromptBuilder内でget_current_datetime_with_timezone()を呼び出して取得（RoundPromptContextと同じパターン）
  - 修正対象: 2ファイル（LLMJudgeMetric基底クラス、JudgmentClient）
  - 設定拡張: 1ファイル（PromptBuilderSettings）

## Constitution Check

*GATE: Phase 0リサーチ前に必ずパスする必要があります。Phase 1設計後に再チェックします。*

### 適用されるArticle

| Article | 要件 | 本機能での遵守状況 | Gate判定 |
|---------|------|------------------|---------|
| **Article 3: Test-First Imperative** | 実装前にテストを作成し、ユーザー承認を取得、Redフェーズ確認 | ✅ **遵守**: 既存テストケース（Evaluator、JudgementClient）が100%パスすることを要件として明記。新規機能（build_evaluator_prompt、build_judgment_prompt）のユニットテストを実装前に作成し、ユーザー承認を取得する。 | **PASS** |
| **Article 4: Documentation Integrity** | 実装は仕様書と完全に整合、曖昧な場合は停止して明確化要求 | ✅ **遵守**: spec.mdに詳細な機能要件（FR-001〜FR-020）、デフォルトプロンプトフォーマット（FR-005、FR-012）、プレースホルダー変数（FR-003、FR-009）が明記されている。実装前に既存コードを深く理解し、仕様との整合性を確認する。 | **PASS** |
| **Article 8: Code Quality Standards** | コミット前に `ruff check --fix . && ruff format . && mypy .` を実行、すべてのエラー解消 | ✅ **遵守**: 実装完了後、コミット前に品質チェックを実施。型注釈（EvaluatorPromptContext、メソッドシグネチャ）を完全に記述。 | **PASS** |
| **Article 9: Data Accuracy Mandate** | 明示的なデータソース、ハードコード禁止、フォールバック禁止 | ✅ **遵守**: デフォルトプロンプトはPromptBuilderSettings（Pydantic Settings）で管理。current_datetimeはget_current_datetime_with_timezone()で明示的取得。プレースホルダー変数の未定義時はJinja2 UndefinedErrorを明示的に発生させる。 | **PASS** |
| **Article 10: DRY Principle** | 実装前に既存コード検索、重複検出時は停止してリファクタリング提案 | ✅ **遵守**: 既存のUserPromptBuilder（specs/092）、LLMJudgeMetric._get_user_prompt、JudgmentClient._format_user_promptを深く調査済み。prompt_builder.formattersの既存実装（format_submission_history、format_ranking_table、generate_position_message）を再利用することを明記（FR-010）。 | **PASS** |
| **Article 14: SpecKit Framework Consistency** | specs/001-specsとの整合性検証、逸脱時は停止 | ✅ **遵守**: Evaluator（specs/022）とJudgmentClient（specs/037）はMixSeek-Coreフレームワークのコンポーネント。UserPromptBuilderはプロンプト品質を一元管理し、評価精度とラウンド継続判定の品質向上に寄与する。specs/001-specsのFR-009（Evaluator）、FR-007（Round Controller）との整合性を確認済み。 | **PASS** |
| **Article 16: Python Type Safety Mandate** | すべての関数・メソッド・変数に型注釈、mypy strict mode必須 | ✅ **遵守**: EvaluatorPromptContext（Pydantic Model）、build_evaluator_prompt、build_judgment_promptに完全な型注釈を記述。mypy strict modeでエラーゼロを確認。 | **PASS** |
| **Article 17: Python Docstring Standards** | Google-style docstring推奨（SHOULD） | ✅ **推奨遵守**: 新規メソッド、Pydantic Modelにdocstringを記述。Args、Returns、Raisesセクションを含む。 | **推奨準拠** |

### Constitution Gate判定

- **Article 3 (Test-First)**: ✅ PASS - 既存テスト100%パス要件、新規テストを実装前に作成
- **Article 4 (Documentation)**: ✅ PASS - 仕様書に詳細な要件定義、既存実装との整合性確認
- **Article 8 (Code Quality)**: ✅ PASS - コミット前の品質チェック、型注釈完備
- **Article 9 (Data Accuracy)**: ✅ PASS - 明示的データソース、エラーハンドリング明確
- **Article 10 (DRY)**: ✅ PASS - 既存実装調査済み、formatters再利用
- **Article 14 (Framework Consistency)**: ✅ PASS - MixSeek-Core仕様との整合性確認済み
- **Article 16 (Type Safety)**: ✅ PASS - 型注釈完備、mypy strict mode準拠

**総合判定**: ✅ **ALL GATES PASSED** - Phase 0リサーチに進むことができます。

## プロジェクト構造

### ドキュメント（本機能）

```
specs/021-user-prompt-builder-evaluator-judgement/
├── spec.md              # 機能仕様書（既存）
├── plan.md              # 本ファイル（/speckit.plan コマンド出力）
├── research.md          # Phase 0 出力（/speckit.plan コマンド）
├── data-model.md        # Phase 1 出力（/speckit.plan コマンド）
├── quickstart.md        # Phase 1 出力（/speckit.plan コマンド）
├── contracts/           # Phase 1 出力（/speckit.plan コマンド） - N/A（API契約なし）
└── tasks.md             # Phase 2 出力（/speckit.tasks コマンド - /speckit.planでは作成しない）
```

### ソースコード（リポジトリルート）

```
src/mixseek/prompt_builder/
├── __init__.py                    # モジュール初期化（EvaluatorPromptContextをエクスポート）
├── builder.py                     # [修正] build_evaluator_prompt、build_judgment_promptメソッド追加
├── models.py                      # [修正] EvaluatorPromptContext追加、PromptBuilderSettings拡張
├── constants.py                   # [修正] DEFAULT_EVALUATOR_USER_PROMPT、DEFAULT_JUDGMENT_USER_PROMPT追加
└── formatters.py                  # [既存] format_submission_history等（変更なし）

src/mixseek/evaluator/
└── metrics/
    └── base.py                    # [修正] LLMJudgeMetric._get_user_promptをUserPromptBuilder呼び出しに変更

src/mixseek/round_controller/
└── judgment_client.py             # [修正] JudgmentClient._format_user_promptをUserPromptBuilder呼び出しに変更

src/mixseek/config/
└── initializer.py                 # [修正] mixseek config initコマンドでevaluator/judgment_user_prompt生成

tests/unit/prompt_builder/
├── test_builder_evaluator.py     # [新規] build_evaluator_promptのユニットテスト
├── test_builder_judgment.py      # [新規] build_judgment_promptのユニットテスト
└── test_models.py                 # [修正] EvaluatorPromptContextのバリデーションテスト追加

tests/unit/evaluator/
└── metrics/
    └── test_base_metric.py        # [修正] LLMJudgeMetric._get_user_prompt統合テスト（既存テスト100%パス確認）

tests/unit/round_controller/
└── test_improvement_judgment.py   # [修正] JudgmentClient統合テスト（既存テスト100%パス確認）
```

**構造決定**:
- **単一プロジェクト（Single Project）**: 既存のmixseek-coreパッケージへの機能追加
- **修正ファイル**: 5ファイル（builder.py、models.py、constants.py、base.py、judgment_client.py、initializer.py）
- **新規テストファイル**: 2ファイル（test_builder_evaluator.py、test_builder_judgment.py）
- **既存テスト修正**: 3ファイル（test_models.py、test_base_metric.py、test_improvement_judgment.py）

## 複雑性トラッキング

*Constitution Checkに違反がある場合のみ記入*

**該当なし** - すべてのConstitution Articleを遵守しており、複雑性の正当化は不要です。

---

## Phase完了サマリー

### Phase 0: Outline & Research ✅ 完了

**成果物**:
- ✅ `research.md` - 技術的決定、ベストプラクティス、実装パターンの調査完了
  - 既存実装の詳細分析（UserPromptBuilder、LLMJudgeMetric、JudgmentClient）
  - Jinja2テンプレートエンジンのベストプラクティス
  - Pydantic Modelの設計パターン
  - デフォルトプロンプトの設計
  - formatters.pyの既存実装再利用方針
  - エラーハンドリング戦略
  - テスト戦略

**重要な発見**:
- ✅ RoundPromptContextはJudgementClientとTeamで共通利用可能（DRY原則遵守）
- ✅ formatters.pyの既存実装（format_submission_history、format_ranking_table、generate_position_message）を完全再利用
- ✅ 既存のLLMJudgeMetric._get_user_promptとJudgmentClient._format_user_promptの実装を深く理解

### Phase 1: Design & Contracts ✅ 完了

**成果物**:
- ✅ `data-model.md` - データモデル詳細設計完了
  - EvaluatorPromptContext（新規Pydantic Model）の完全な設計
  - PromptBuilderSettings拡張（evaluator_user_prompt、judgment_user_prompt）
  - RoundPromptContext再利用の確認
  - デフォルト値定義（constants.py）
  - エンティティ関係図、バリデーション戦略、状態遷移図、データフロー図
- ✅ `quickstart.md` - ユーザー向けクイックスタートガイド完了
  - デフォルト設定の生成方法
  - プロンプトのカスタマイズ例
  - 利用可能なプレースホルダー変数の説明
  - Pythonコードでの使用例
  - トラブルシューティング
  - 高度な使用例
- ✅ `contracts/` - N/A（API契約なし、内部メソッドのみ）
- ✅ Agent Context更新 - `.specify/scripts/bash/update-agent-context.sh claude`実行完了

**Constitution Check再評価**: ✅ **ALL GATES PASSED**
- Phase 1設計後も全Articleを遵守
- データモデル設計、ドキュメント生成がすべて要件を満たす
- 型安全性、DRY原則、Data Accuracyすべて確保

### 次のステップ（Phase 2）

**注意**: Phase 2（tasks.md生成）は`/speckit.tasks`コマンドで実行してください。`/speckit.plan`コマンドはここまでで完了です。

**Phase 2で実行すること**:
1. `/speckit.tasks`コマンドを実行してtasks.mdを生成
2. タスク依存関係の定義
3. 実装順序の決定
4. テストファースト戦略の具体化

---

## 実装準備完了チェックリスト

- ✅ Phase 0: リサーチ完了
  - ✅ 既存実装の完全な理解
  - ✅ 技術的決定事項の文書化
  - ✅ ベストプラクティスの調査
- ✅ Phase 1: 設計完了
  - ✅ データモデル詳細設計
  - ✅ ユーザーガイド作成
  - ✅ Agent Context更新
- ✅ Constitution Check: すべてのArticle遵守確認
  - ✅ Article 3: Test-First
  - ✅ Article 4: Documentation Integrity
  - ✅ Article 8: Code Quality Standards
  - ✅ Article 9: Data Accuracy Mandate
  - ✅ Article 10: DRY Principle
  - ✅ Article 14: Framework Consistency
  - ✅ Article 16: Type Safety
  - ✅ Article 17: Docstring Standards（推奨）

**ステータス**: ✅ **実装準備完了** - `/speckit.tasks`コマンドで次のPhaseに進むことができます。

---

## 補足情報

### 関連ドキュメント
- 機能仕様書: [spec.md](./spec.md)
- リサーチドキュメント: [research.md](./research.md)
- データモデル設計: [data-model.md](./data-model.md)
- クイックスタートガイド: [quickstart.md](./quickstart.md)
- 親仕様: [specs/015-user-prompt-builder-team](../092-user-prompt-builder-team/)
- MixSeek-Coreフレームワーク: [specs/001-specs](../001-mixseek-core-specs/)

### 主要な技術選択
- **Jinja2テンプレートエンジン**: 柔軟なプロンプトカスタマイズ
- **Pydantic Model**: 型安全なコンテキスト定義
- **Pydantic Settings**: TOML/環境変数による設定管理
- **formatters.py再利用**: DRY原則遵守

### 成功基準
- Evaluator、JudgementClientの既存テストケース100%パス
- build_evaluator_prompt: 10ms以内（95パーセンタイル）
- build_judgment_prompt: 50ms以内（95パーセンタイル）
- 型注釈完備、mypy strict mode準拠
- コード品質チェック（ruff、mypy）すべてパス
