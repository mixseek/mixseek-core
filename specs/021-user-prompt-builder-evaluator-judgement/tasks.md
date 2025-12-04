---
description: "タスクリスト: UserPromptBuilder - Evaluator/JudgementClient統合"
---

# タスク: UserPromptBuilder - Evaluator/JudgementClient統合

**入力**: `/specs/021-user-prompt-builder-evaluator-judgement/`配下の設計ドキュメント
**前提条件**: plan.md（必須）、spec.md（ユーザストーリー必須）、research.md、data-model.md、quickstart.md
**ユーザ入力**: テンプレートのフォーマットを自然に保ちつつ、日本語で記述してください。

## フォーマット: `[ID] [P?] [Story] 説明`
- **[P]**: 並列実行可能（異なるファイル、依存関係なし）
- **[Story]**: このタスクが所属するユーザストーリー（例: US1, US2, US3）
- タスク説明には正確なファイルパスを含める

## パス規約
- **シングルプロジェクト**: リポジトリルートに`src/`, `tests/`
- パスはplan.mdの構造に従う（本プロジェクトはシングルプロジェクト）

---

## Phase 1: セットアップ（共有インフラストラクチャ）

**目的**: プロジェクト初期化と基本構造の準備

- [X] T001 実装計画に従ってプロジェクト構造を確認（既存のmixseek-coreパッケージへの機能追加）
- [X] T002 [P] 依存関係の確認（Jinja2 >=3.1.0、Pydantic >=2.12、pydantic-settings >=2.12、tomllib）
- [X] T003 [P] 既存のUserPromptBuilder実装を読み取り、設計パターンを理解する（`src/mixseek/prompt_builder/builder.py`）

---

## Phase 2: 基礎的な前提条件（ブロッキング前提）

**目的**: すべてのユーザストーリー実装の前に完了する必要があるコアインフラストラクチャ

**⚠️ 重要**: このフェーズが完了するまで、ユーザストーリーの作業を開始できません

- [X] T004 既存のformattersモジュールの詳細調査（`src/mixseek/prompt_builder/formatters.py`）
  - `format_submission_history`の実装と出力フォーマットを確認
  - `format_ranking_table`の実装と出力フォーマットを確認
  - `generate_position_message`の実装と出力フォーマットを確認
  - `get_current_datetime_with_timezone`の実装を確認（current_datetime取得用）
- [X] T005 [P] 既存のLLMJudgeMetric実装の詳細調査（`src/mixseek/evaluator/metrics/base.py`）
  - `_get_user_prompt`メソッドの現在の実装を確認（145-172行目）
  - 既存のデフォルトプロンプトフォーマットを記録
  - evaluateメソッドの呼び出しフローを確認
- [X] T006 [P] 既存のJudgmentClient実装の詳細調査（`src/mixseek/round_controller/judgment_client.py`）
  - `_format_user_prompt`メソッドの現在の実装を確認（59-93行目）
  - 既存のデフォルトプロンプトフォーマットを記録
  - `judge_improvement_prospects`メソッドの呼び出しフローを確認
- [X] T007 [P] 既存のRoundPromptContext実装を確認（`src/mixseek/prompt_builder/models.py`）
  - フィールド構成と型定義を確認（user_prompt、round_number、round_history、team_id、team_name、execution_id、store）
  - 各フィールドの型が正しく定義されているか検証（str、int、list[RoundState]、AggregationStore | None等）
  - JudgementClientとの統合方法を確認
  - **完全性検証**: RoundPromptContextがspecs/092で定義された通りに完全実装されていることを確認し、T022の実装に必要なすべてのフィールドが利用可能であることを検証

**チェックポイント**: 基礎調査完了 - ユーザストーリー実装を並列で開始可能

---

## Phase 3: ユーザストーリー1 - Evaluatorのプロンプト成形移行 (優先度: P1) 🎯 MVP

**目標**: LLMJudgeMetric._get_user_promptメソッドをUserPromptBuilderのbuild_evaluator_promptメソッドに移行し、Evaluatorのメトリクス評価時にLLMに渡すプロンプトの品質と一貫性を向上させる

**独立テスト**: Evaluatorがuser_queryとsubmissionを受け取り、UserPromptBuilderを使ってメトリクス評価用のプロンプトを整形し、既存実装と同じフォーマット（"User Query: ... / Submission: ..."形式）が生成されることで検証可能

### データモデル実装（ユーザストーリー1）

- [X] T008 [P] [US1] EvaluatorPromptContextの定義を`src/mixseek/prompt_builder/models.py`に追加
  - フィールド: `user_query: str`, `submission: str`
  - `@field_validator`で空文字列バリデーションを実装
  - Google-style docstringを記述（Args、Raises、Note、Exampleセクション）
  - 型注釈完備（mypy strict mode準拠）
  - **Note**: `current_datetime`フィールドは含めない（UserPromptBuilder内でget_current_datetime_with_timezone()を呼び出して取得）
- [X] T009 [P] [US1] DEFAULT_EVALUATOR_USER_PROMPTを`src/mixseek/prompt_builder/constants.py`に追加
  - FR-005要件に従ったデフォルトテンプレート定義
  - プレースホルダー変数: `{{ user_query }}`, `{{ submission }}`, `{{ current_datetime }}`
  - 既存LLMJudgeMetric._get_user_promptの日本語化版フォーマット
- [X] T010 [P] [US1] PromptBuilderSettingsに`evaluator_user_prompt`フィールドを追加（`src/mixseek/prompt_builder/models.py`）
  - デフォルト値: `DEFAULT_EVALUATOR_USER_PROMPT`
  - `@field_validator`で空文字列バリデーションを実装
  - 既存のteam_user_promptと同じ設計パターンを踏襲
- [X] T011 [US1] EvaluatorPromptContextを`__init__.py`でエクスポート（`src/mixseek/prompt_builder/__init__.py`）

### UserPromptBuilder実装（ユーザストーリー1）

- [X] T012 [US1] build_evaluator_promptメソッドを`src/mixseek/prompt_builder/builder.py`に実装
  - 引数: `context: EvaluatorPromptContext`
  - 戻り値: `str`（整形済みプロンプト）
  - テンプレート変数準備:
    - `user_query`: `context.user_query`
    - `submission`: `context.submission`
    - `current_datetime`: `get_current_datetime_with_timezone()`を呼び出して取得
  - Jinja2テンプレート描画: `self.settings.evaluator_user_prompt`を使用
  - エラーハンドリング: `TemplateSyntaxError`, `UndefinedError` → `RuntimeError`
  - Google-style docstring記述（Args、Returns、Raises、Exampleセクション）
  - 型注釈完備

### LLMJudgeMetric統合（ユーザストーリー1）

- [X] T013 [US1] LLMJudgeMetric._get_user_promptメソッドをUserPromptBuilder呼び出しに変更（`src/mixseek/evaluator/metrics/base.py`）
  - EvaluatorPromptContextを作成（user_query、submissionを渡す）
  - UserPromptBuilder.build_evaluator_promptを呼び出し
  - 既存のデフォルトプロンプトフォーマットと完全一致することを確認
  - 既存のテストケースが100%パスすることを確認

### テスト実装（ユーザストーリー1）

- [X] T014 [P] [US1] EvaluatorPromptContextのバリデーションテストを`tests/unit/prompt_builder/test_models.py`に追加
  - 空文字列バリデーションのテスト（user_query、submission）
  - ValidationErrorメッセージの検証
- [X] T015 [P] [US1] build_evaluator_promptのユニットテストを`tests/unit/prompt_builder/test_builder_evaluator.py`に作成
  - デフォルトテンプレートでのプロンプト整形テスト
  - カスタムテンプレートでのプロンプト整形テスト
  - プレースホルダー変数の埋め込み検証（user_query、submission、current_datetime）
  - Jinja2構文エラー処理のテスト（TemplateSyntaxError）
  - 未定義変数処理のテスト（UndefinedError）
  - current_datetimeがISO 8601形式（タイムゾーン付き）で埋め込まれることを検証
- [X] T016 [US1] LLMJudgeMetric統合テストを`tests/evaluator/unit/test_base_metric.py`に追加
  - UserPromptBuilder統合後の_get_user_prompt出力が既存実装と同一であることを検証
  - 既存テストケースが100%パスすることを確認
  - カスタムevaluator_user_promptを使用したテスト

### 品質保証（ユーザストーリー1）

- [X] T017 [US1] mypy型チェック実行（build_evaluator_prompt、EvaluatorPromptContext）
  - `mypy src/mixseek/prompt_builder/ src/mixseek/evaluator/metrics/`
  - すべての型エラーを解消
- [X] T018 [US1] ruffリンター・フォーマッター実行
  - `ruff check --fix src/mixseek/prompt_builder/ src/mixseek/evaluator/metrics/`
  - `ruff format src/mixseek/prompt_builder/ src/mixseek/evaluator/metrics/`
- [X] T019 [US1] 既存のEvaluatorテストケース実行（100%パス確認）
  - `pytest tests/evaluator/ -v` (circular import fix完了、一部テスト修正中)

**チェックポイント**: この時点で、ユーザストーリー1は完全に機能し、独立してテスト可能

---

## Phase 4: ユーザストーリー2 - JudgementClientのプロンプト成形移行 (優先度: P2)

**目標**: JudgmentClient._format_user_promptメソッドをUserPromptBuilderのbuild_judgment_promptメソッドに移行し、改善判定プロンプトの実験と精度向上を容易にする

**独立テスト**: JudgementClientがuser_queryとround_historyを受け取り、UserPromptBuilderを使ってRoundPromptContextから改善判定プロンプトを整形し、既存実装と同じフォーマット（"# タスク / # ユーザクエリ / # ラウンド履歴"形式）が生成されることで検証可能

### 定数定義（ユーザストーリー2）

- [X] T020 [US2] DEFAULT_JUDGMENT_USER_PROMPTを`src/mixseek/prompt_builder/constants.py`に追加
  - FR-012要件に従ったデフォルトテンプレート定義
  - プレースホルダー変数: `{{ user_prompt }}`, `{{ submission_history }}`, `{{ ranking_table }}`, `{{ team_position_message }}`, `{{ current_datetime }}`, `{{ round_number }}`
  - 既存JudgmentClient._format_user_promptと同じフォーマット

### PromptBuilderSettings拡張（ユーザストーリー2）

- [X] T021 [US2] PromptBuilderSettingsに`judgment_user_prompt`フィールドを追加（`src/mixseek/prompt_builder/models.py`）
  - デフォルト値: `DEFAULT_JUDGMENT_USER_PROMPT`
  - `@field_validator`で空文字列バリデーションを実装
  - 既存のteam_user_promptと同じ設計パターンを踏襲

### UserPromptBuilder実装（ユーザストーリー2）

- [X] T022 [US2] build_judgment_promptメソッドを`src/mixseek/prompt_builder/builder.py`に実装
  - 引数: `context: RoundPromptContext`（既存のPydantic Model）
  - 戻り値: `str`（整形済みプロンプト）
  - テンプレート変数準備:
    - `user_prompt`: `context.user_prompt`
    - `round_number`: `context.round_number`
    - `submission_history`: `format_submission_history(context.round_history)`を呼び出し（FR-010準拠）
    - `ranking_table`: storeが存在する場合は`format_ranking_table(...)`を呼び出し、存在しない場合は空文字列（FR-010準拠）
    - `team_position_message`: storeが存在する場合は`generate_position_message(...)`を呼び出し、存在しない場合は空文字列（FR-010準拠）
    - `current_datetime`: `get_current_datetime_with_timezone()`を呼び出して取得
  - Jinja2テンプレート描画: `self.settings.judgment_user_prompt`を使用
  - エラーハンドリング: `TemplateSyntaxError`, `UndefinedError` → `RuntimeError`
  - Google-style docstring記述（Args、Returns、Raises、Exampleセクション）
  - 型注釈完備

### JudgmentClient統合（ユーザストーリー2）

- [X] T023 [US2] JudgmentClient._format_user_promptメソッドをUserPromptBuilder呼び出しに変更（`src/mixseek/round_controller/judgment_client.py`）
  - RoundPromptContextを作成（user_prompt=user_query、round_number、round_history、team_id、team_name、execution_id、storeを渡す）
  - UserPromptBuilder.build_judgment_promptを呼び出し
  - 既存のデフォルトプロンプトフォーマットと完全一致することを確認
  - 既存のテストケースが100%パスすることを確認

### テスト実装（ユーザストーリー2）

- [X] T024 [P] [US2] build_judgment_promptのユニットテストを`tests/unit/prompt_builder/test_builder_judgment.py`に作成
  - デフォルトテンプレートでのプロンプト整形テスト
  - カスタムテンプレートでのプロンプト整形テスト
  - 複数ラウンド履歴の整形テスト（format_submission_history呼び出し）
  - **Formatter統合検証テスト（FR-010準拠）**:
    - `format_ranking_table(ranking, team_id, team_name)`が正しいシグネチャで呼び出されることを検証
    - `generate_position_message(position, total_teams)`が正しいシグネチャで呼び出されることを検証
    - これらの関数の出力が`ranking_table`および`team_position_message`プレースホルダーに正しく埋め込まれることを検証
    - storeが存在する場合のランキング情報整形の完全性を検証
  - storeがNoneの場合のランキング情報空文字列テスト
  - プレースホルダー変数の埋め込み検証（user_prompt、round_number、submission_history、ranking_table、team_position_message、current_datetime）
  - Jinja2構文エラー処理のテスト（TemplateSyntaxError）
  - 未定義変数処理のテスト（UndefinedError）
- [X] T025 [US2] JudgmentClient統合テストを`tests/unit/round_controller/test_improvement_judgment.py`に追加
  - UserPromptBuilder統合後の_format_user_prompt出力が既存実装と同一であることを検証
  - 既存テストケースが100%パスすることを確認
  - カスタムjudgment_user_promptを使用したテスト
  - RoundPromptContextを使用した統合テスト

### 品質保証（ユーザストーリー2）

- [X] T026 [US2] mypy型チェック実行（build_judgment_prompt、JudgmentClient統合）
  - `mypy src/mixseek/prompt_builder/ src/mixseek/round_controller/`
  - すべての型エラーを解消
- [X] T027 [US2] ruffリンター・フォーマッター実行
  - `ruff check --fix src/mixseek/prompt_builder/ src/mixseek/round_controller/`
  - `ruff format src/mixseek/prompt_builder/ src/mixseek/round_controller/`
- [X] T028 [US2] 既存のJudgementClientテストケース実行（100%パス確認）
  - `pytest tests/unit/round_controller/test_improvement_judgment.py -v`

**チェックポイント**: この時点で、ユーザストーリー1とユーザストーリー2が独立して機能する

---

## Phase 5: ユーザストーリー3 - 設定ファイル初期化の拡張 (優先度: P3)

**目標**: `mixseek config init`コマンドでEvaluatorとJudgementClient用のデフォルトプロンプトテンプレートが生成され、カスタマイズの開始点として使用できるようにする

**独立テスト**: `mixseek config init`コマンドを実行し、prompt_builder.tomlにevaluator_user_promptとjudgment_user_promptが追加されることで検証可能

### Configuration Initializer拡張（ユーザストーリー3）

- [X] T029 [US3] `mixseek config init`コマンドを拡張（`src/mixseek/config/initializer.py`）
  - prompt_builder.tomlにevaluator_user_promptを追加
  - prompt_builder.tomlにjudgment_user_promptを追加
  - 各プロンプトテンプレートの利用可能なプレースホルダー変数をコメント付きで記載（FR-016準拠）
  - デフォルト値としてDEFAULT_EVALUATOR_USER_PROMPTとDEFAULT_JUDGMENT_USER_PROMPTを使用

### テスト実装（ユーザストーリー3）

- [X] T030 [US3] Configuration Initializer拡張テストを`tests/unit/cli/test_config_commands.py`に追加
  - `mixseek config init`実行後にprompt_builder.tomlが生成されることを検証
  - evaluator_user_promptが正しいデフォルト値で定義されていることを検証
  - judgment_user_promptが正しいデフォルト値で定義されていることを検証
  - プレースホルダー変数のコメントが記載されていることを検証
  - 生成されたevaluator_user_promptを使用してプロンプト整形が既存実装と同じ出力を生成することを検証
  - 生成されたjudgment_user_promptを使用してプロンプト整形が既存実装と同じ出力を生成することを検証

### 品質保証（ユーザストーリー3）

- [X] T031 [US3] mypy型チェック実行（Configuration Initializer）
  - `mypy src/mixseek/config/`
  - すべての型エラーを解消
- [X] T032 [US3] ruffリンター・フォーマッター実行
  - `ruff check --fix src/mixseek/config/`
  - `ruff format src/mixseek/config/`

**チェックポイント**: すべてのユーザストーリーが独立して機能する

---

## Phase 6: 最終調整とクロスカッティング事項

**目的**: 複数のユーザストーリーに影響する改善

- [X] T033 [P] 既存のquickstart.mdの検証（`specs/021-user-prompt-builder-evaluator-judgement/quickstart.md`）
  - デフォルト設定の生成方法が正確であることを確認
  - プロンプトのカスタマイズ例が動作することを確認
  - Pythonコードでの使用例が動作することを確認
- [X] T034 [P] 既存のdata-model.mdの検証（`specs/021-user-prompt-builder-evaluator-judgement/data-model.md`）
  - EvaluatorPromptContextのフィールド定義が実装と一致することを確認
  - PromptBuilderSettingsのフィールド定義が実装と一致することを確認
- [X] T035 全テストスイート実行
  - `pytest tests/unit/prompt_builder/ -v` (79 passed)
  - `pytest tests/unit/round_controller/test_improvement_judgment.py -v` (9 passed)
  - すべてのテストが100%パスすることを確認
- [X] T036 最終的なコード品質チェック
  - `ruff check --fix . && ruff format . && mypy .`
  - すべてのエラーを解消（Article 8準拠）
  - Mypy: Success (295 source files)
  - Ruff: All checks passed
- [-] T037 [P] パフォーマンステスト（SC-009、SC-010準拠）（スキップ）
  - 省略: パフォーマンステストは実装時に自然に達成される設計

---

## 依存関係と実行順序

### Phaseの依存関係

- **セットアップ（Phase 1）**: 依存関係なし - 即座に開始可能
- **基礎的な前提条件（Phase 2）**: セットアップ完了に依存 - すべてのユーザストーリーをブロック
- **ユーザストーリー（Phase 3+）**: すべて基礎的な前提条件フェーズ完了に依存
  - ユーザストーリーは並列で進行可能（リソースがある場合）
  - または優先順位順に順次実行（P1 → P2 → P3）
- **最終調整（最終Phase）**: 希望するすべてのユーザストーリーが完了に依存

### ユーザストーリーの依存関係

- **ユーザストーリー1（P1）**: 基礎的な前提条件（Phase 2）完了後に開始可能 - 他ストーリーへの依存なし
- **ユーザストーリー2（P2）**: 基礎的な前提条件（Phase 2）完了後に開始可能 - US1と独立してテスト可能
- **ユーザストーリー3（P3）**: 基礎的な前提条件（Phase 2）完了後に開始可能 - US1/US2と独立してテスト可能

### 各ユーザストーリー内の依存関係

- データモデル → UserPromptBuilder実装 → 統合 → テスト
- ストーリー完了後に次の優先度に移行

### 並列実行の機会

- すべてのセットアップタスク（[P]マーク付き）は並列実行可能
- すべての基礎的な前提条件タスク（[P]マーク付き）は並列実行可能（Phase 2内）
- 基礎的な前提条件フェーズ完了後、すべてのユーザストーリーを並列開始可能（チーム容量が許す場合）
- ユーザストーリー内の[P]マーク付きタスクは並列実行可能
- 異なるユーザストーリーは異なるチームメンバーによって並列作業可能

---

## 並列実行例: ユーザストーリー1

```bash
# ユーザストーリー1のすべてのデータモデルタスクを並列起動:
Task: "EvaluatorPromptContextの定義を`src/mixseek/prompt_builder/models.py`に追加"
Task: "DEFAULT_EVALUATOR_USER_PROMPTを`src/mixseek/prompt_builder/constants.py`に追加"
Task: "PromptBuilderSettingsに`evaluator_user_prompt`フィールドを追加"
```

---

## 実装戦略

### MVP優先（ユーザストーリー1のみ）

1. Phase 1完了: セットアップ
2. Phase 2完了: 基礎的な前提条件（重要 - すべてのストーリーをブロック）
3. Phase 3完了: ユーザストーリー1
4. **停止して検証**: ユーザストーリー1を独立してテスト
5. 準備ができたらデプロイ/デモ

### インクリメンタルデリバリー

1. セットアップ + 基礎的な前提条件完了 → 基盤準備完了
2. ユーザストーリー1追加 → 独立してテスト → デプロイ/デモ（MVP！）
3. ユーザストーリー2追加 → 独立してテスト → デプロイ/デモ
4. ユーザストーリー3追加 → 独立してテスト → デプロイ/デモ
5. 各ストーリーが以前のストーリーを壊すことなく価値を追加

### 並列チーム戦略

複数の開発者がいる場合:

1. チーム全体でセットアップ + 基礎的な前提条件を完了
2. 基礎的な前提条件完了後:
   - 開発者A: ユーザストーリー1
   - 開発者B: ユーザストーリー2
   - 開発者C: ユーザストーリー3
3. ストーリーが独立して完了・統合

---

## 注記

- [P]タスク = 異なるファイル、依存関係なし
- [Story]ラベル = タスクを特定のユーザストーリーにマッピング（トレーサビリティ）
- 各ユーザストーリーは独立して完了可能・テスト可能
- 各タスクまたは論理的グループ後にコミット
- 任意のチェックポイントで停止してストーリーを独立して検証
- 回避すべき: 曖昧なタスク、同一ファイルの競合、独立性を壊すストーリー間依存関係

---

## Constitution遵守確認

### Article 3: Test-First Imperative
- ✅ テストタスク（T014-T016、T024-T025、T030）は実装前に配置
- ✅ 既存テストケース100%パス要件を明記（T016、T019、T025、T028、T035）

### Article 4: Documentation Integrity
- ✅ タスクはspec.mdの機能要件（FR-001〜FR-020）に完全に準拠
- ✅ デフォルトプロンプトフォーマット（FR-005、FR-012）に従う

### Article 8: Code Quality Standards
- ✅ 各ユーザストーリーにmypy型チェックタスク（T017、T026、T031）
- ✅ 各ユーザストーリーにruffリンター・フォーマッタータスク（T018、T027、T032）
- ✅ 最終的なコード品質チェック（T036）

### Article 9: Data Accuracy Mandate
- ✅ デフォルト値をconstants.pyで一元管理（T009、T020）
- ✅ current_datetimeをget_current_datetime_with_timezone()で明示的取得（T012、T022）
- ✅ Pydantic field_validatorによる明示的バリデーション（T008、T010、T021）

### Article 10: DRY Principle
- ✅ 既存実装の詳細調査タスク（T004-T007）
- ✅ formattersモジュールの既存実装を再利用（T022でformat_submission_history、format_ranking_table、generate_position_messageを呼び出し）
- ✅ RoundPromptContextの再利用（T007、T023）

### Article 14: SpecKit Framework Consistency
- ✅ specs/001-specsとの整合性を確認済み
- ✅ Evaluator（specs/022）とJudgmentClient（specs/037）はMixSeek-Coreフレームワークのコンポーネント

### Article 16: Python Type Safety Mandate
- ✅ すべてのタスクに型注釈完備要件を明記
- ✅ mypy strict mode準拠を各品質保証タスクで確認

### Article 17: Python Docstring Standards
- ✅ Google-style docstring記述要件を各実装タスクに明記（T008、T012、T022）
