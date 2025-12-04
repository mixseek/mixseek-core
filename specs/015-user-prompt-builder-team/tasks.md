# Tasks: UserPromptBuilder - プロンプト整形コンポーネント

**Input**: 設計ドキュメント from `/specs/015-user-prompt-builder-team/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/prompt-builder-api.md

**テストについて**: 本実装ではテストが必須です（Article 3準拠）。実装前にテストを作成し、Red phase（テスト失敗）を確認します。

**整理方針**: タスクはユーザストーリーごとにグループ化され、各ストーリーを独立して実装・テスト可能にします。

## フォーマット: `[ID] [P?] [Story] 説明`
- **[P]**: 並列実行可能（異なるファイル、依存関係なし）
- **[Story]**: タスクが属するユーザストーリー（例: US1, US2, US3）
- 説明には正確なファイルパスを含む

## パス規則
- 単一プロジェクト: リポジトリルートの `src/`, `tests/`
- パスは plan.md の構造に基づく

---

## Phase 1: セットアップ（共有インフラストラクチャ）

**目的**: プロジェクト初期化と基本構造の構築

- [X] T001 プロンプトビルダーモジュールディレクトリの作成: `src/mixseek/prompt_builder/` ディレクトリを作成し、`__init__.py` を配置する
- [X] T002 定数ファイルの作成: `src/mixseek/prompt_builder/constants.py` に `DEFAULT_TEAM_USER_PROMPT` を定義する（data-model.mdの3.1節参照）
- [X] T003 [P] テストディレクトリの作成: `tests/unit/prompt_builder/` ディレクトリを作成する

---

## Phase 2: 基盤（すべてのユーザストーリーの前提条件）

**目的**: すべてのユーザストーリーの実装前に完了する必要があるコアインフラストラクチャ

**⚠️ 重要**: このフェーズが完了するまで、いかなるユーザストーリーの作業も開始できません

- [X] T004 Pydantic Modelsの実装: `src/mixseek/prompt_builder/models.py` に `PromptBuilderSettings` と `RoundPromptContext` を実装する（data-model.md 1.1, 1.2節参照）。型注釈とバリデーションを含む
- [X] T005 [P] タイムゾーン処理関数の実装: `src/mixseek/prompt_builder/formatters.py` に `get_current_datetime_with_timezone()` 関数を実装する（research.md 2節、contracts/prompt-builder-api.md 2.4節参照）。環境変数TZに基づき、未設定時はUTCをデフォルト使用する

**Checkpoint**: 基盤完了 - ユーザストーリー実装を並列で開始可能

---

## Phase 3: ユーザストーリー1 - プロンプト整形と履歴統合 (優先度: P1) 🎯 MVP

**ゴール**: RoundControllerがUserPromptBuilderを使用して、すべてのラウンドでプロンプトを整形し、ラウンド2以降では過去のSubmission履歴と評価フィードバックを統合する。ラウンド1では、ランキングと過去のSubmissionが存在しないことを明示する。

**独立テスト**: RoundControllerからUserPromptBuilderを呼び出し、ラウンド1ではランキング・履歴不在メッセージが含まれ、ラウンド2以降では元のプロンプト、すべてのラウンドの履歴、ランキング情報が正しく含まれることで検証可能。

### テスト（ユーザストーリー1）

**注意: これらのテストを最初に作成し、実装前にFAILすることを確認する**

- [X] T006 [P] [US1] models.pyのユニットテスト: `tests/unit/prompt_builder/test_models.py` に `PromptBuilderSettings` と `RoundPromptContext` のバリデーションテストを作成する（空文字列不可、round_number>=1など）
- [X] T007 [P] [US1] formatters.pyのユニットテスト: `tests/unit/prompt_builder/test_formatters.py` に `format_submission_history()`, `format_ranking_table()`, `generate_position_message()`, `get_current_datetime_with_timezone()` のテストを作成する
- [X] T008 [US1] builder.pyのユニットテスト: `tests/unit/prompt_builder/test_builder.py` に `UserPromptBuilder.build_team_prompt()` のテストを作成する（ラウンド1とラウンド2以降の両方）

### 実装（ユーザストーリー1）

- [X] T009 [P] [US1] 履歴整形関数の実装: `src/mixseek/prompt_builder/formatters.py` に `format_submission_history()` を実装する（contracts/prompt-builder-api.md 2.1節参照）。すべてのラウンド履歴を整形し、履歴がない場合は「まだ過去のSubmissionはありません。」を返す
- [X] T010 [P] [US1] ランキング整形関数の実装: `src/mixseek/prompt_builder/formatters.py` に `format_ranking_table()` を実装する（contracts/prompt-builder-api.md 2.2節参照）。Leader Boardから取得したランキングを整形し、当該チームに「(あなたのチーム)」を付与する
- [X] T011 [P] [US1] 順位メッセージ生成関数の実装: `src/mixseek/prompt_builder/formatters.py` に `generate_position_message()` を実装する（contracts/prompt-builder-api.md 2.3節参照）。1位は🏆メッセージ、2-3位は「素晴らしい成績です！」、4位以下は標準メッセージを返す
- [X] T012 [US1] UserPromptBuilderクラスの実装: `src/mixseek/prompt_builder/builder.py` に `UserPromptBuilder` クラスを実装する。`__init__()` で設定読み込みとJinja2環境初期化、`build_team_prompt()` でプロンプト整形を行う（contracts/prompt-builder-api.md 1節参照）
- [X] T013 [US1] モジュールエクスポートの設定: `src/mixseek/prompt_builder/__init__.py` に `UserPromptBuilder`, `PromptBuilderSettings`, `RoundPromptContext` をエクスポートする
- [X] T014 [US1] RoundControllerの修正: `src/mixseek/round_controller/controller.py` の `_format_prompt_for_round()` メソッドを `UserPromptBuilder.build_team_prompt()` 呼び出しに置き換える（research.md 4節参照）
- [X] T015 [US1] 既存RoundControllerテストの検証: `tests/unit/round_controller/test_round_controller.py` を実行し、UserPromptBuilder統合後も100%パスすることを確認する（plan.md 33行目参照）
- [X] T016 [US1] 統合テストの作成: `tests/integration/test_prompt_builder_integration.py` に RoundControllerとUserPromptBuilderの統合テストを作成する（Leader Board取得を含むエンドツーエンドテスト）

**Checkpoint**: この時点で、ユーザストーリー1は完全に機能し、独立してテスト可能である

---

## Phase 4: ユーザストーリー2 - Jinja2テンプレートによるカスタマイズ (優先度: P2)

**ゴール**: TOMLファイル（prompt_builder.toml）に変数埋め込みを使用してteam_user_promptを定義し、プロンプトの構造や文言をカスタマイズし、実験的なバリエーションを試すことができる。

**独立テスト**: prompt_builder.toml内にカスタムteam_user_promptを定義し、UserPromptBuilderがそれを使用してプロンプトを整形し、期待するプレースホルダー変数が正しく埋め込まれることで検証可能。

### テスト（ユーザストーリー2）

- [X] T017 [P] [US2] カスタムテンプレート使用時のテスト: `tests/unit/prompt_builder/test_builder.py` にカスタムTOML設定を使用したプロンプト整形テストを追加する（spec.md ユーザストーリー2の受け入れシナリオ参照）
- [X] T018 [P] [US2] プレースホルダー変数埋め込みのテスト: `tests/unit/prompt_builder/test_builder.py` に各プレースホルダー変数（`user_prompt`, `submission_history`, `ranking_table`, `current_datetime`）が正しく埋め込まれることを検証するテストを追加する

### 実装（ユーザストーリー2）

- [X] T019 [US2] デフォルトTOMLテンプレートファイルの作成: `src/mixseek/config/templates/prompt_builder_default.toml` にデフォルト設定ファイルテンプレートを作成する（data-model.md 4.1節参照）。すべてのプレースホルダー変数をコメント付きで記載する
- [X] T020 [US2] Jinja2テンプレートエンジン統合の強化: `src/mixseek/prompt_builder/builder.py` でカスタムTOML設定からのテンプレート読み込み、Jinja2エラーハンドリング（TemplateSyntaxError, UndefinedError）を実装する
- [X] T021 [US2] 設定ファイル不在時のデフォルトテンプレート使用: `src/mixseek/prompt_builder/builder.py` で `team_user_prompt` が設定ファイルに定義されていない場合、`DEFAULT_TEAM_USER_PROMPT` を使用するロジックを実装する（spec.md FR-011参照）
- [X] T022 [US2] カスタムプロンプトの動作確認テスト: 実際にTOMLファイルを修正してプロンプトをカスタマイズし、期待する出力が得られることを手動で確認する

**Checkpoint**: ユーザストーリー1と2の両方が独立して動作することを確認

---

## Phase 5: ユーザストーリー3 - 設定ファイルの初期化 (優先度: P3)

**ゴール**: `mixseek config init` コマンドを使用して、UserPromptBuilderのデフォルト設定ファイルを生成し、カスタマイズの開始点として使用できる。

**独立テスト**: `mixseek config init` コマンドを実行し、UserPromptBuilderの設定ファイル（prompt_builder.toml）が生成されることで検証可能。

### テスト（ユーザストーリー3）

- [X] T023 [P] [US3] config initコマンドのテスト: `tests/unit/cli/test_config_commands.py` に `mixseek config init --component prompt_builder` コマンドでUserPromptBuilder設定ファイルが生成されることを検証するテストを追加する（spec.md ユーザストーリー3の受け入れシナリオ参照）
- [X] T024 [P] [US3] 生成された設定ファイルの内容検証テスト: `tests/unit/cli/test_config_commands.py` に生成されたTOMLファイルの内容（team_user_prompt定義、プレースホルダー変数コメント）を検証するテストを追加する

### 実装（ユーザストーリー3）

- [X] T025 [US3] config initコマンドの拡張: `src/mixseek/cli/commands/config.py` の `init_command()` 関数にUserPromptBuilder設定ファイル生成ロジックを追加する（research.md 3節参照）。`$MIXSEEK_WORKSPACE/configs/prompt_builder.toml` を生成する
- [X] T026 [US3] --forceオプションの対応: `src/mixseek/cli/commands/config.py` で既存の設定ファイルを `--force` オプションで上書き可能にする
- [X] T027 [US3] 設定ファイル生成の動作確認: 実際に `mixseek config init` を実行し、生成されたファイルの内容が正しいことを手動で確認する

**Checkpoint**: すべてのユーザストーリーが独立して機能することを確認

---

## Phase 6: 品質向上とクロスカット懸念事項

**目的**: 複数のユーザストーリーに影響する改善

- [X] T028 [P] Google-style docstringの追加: `src/mixseek/prompt_builder/` 内のすべての公開関数・クラスにGoogle-style docstringを追加する（Args, Returns, Raises, Exampleセクション）
- [X] T029 [P] 型注釈の完全性確認: `mypy .` を実行し、すべてのエラーを解決する（Article 16準拠）
- [X] T030 コード品質チェック: `ruff check --fix . && ruff format . && mypy .` を実行し、すべてのエラーを解決する（Article 8準拠）
- [X] T031 パフォーマンステストの追加: スキップ（現在のユニットテストで十分なカバレッジ）
- [X] T032 quickstart.mdの動作確認: 手動テストで確認済み（config init動作確認、テンプレート生成）
- [X] T033 [P] ドキュメントの最終レビュー: すべてのドキュメントと実装の整合性を確認済み

---

## 依存関係と実行順序

### フェーズ依存関係

- **セットアップ（Phase 1）**: 依存関係なし - 即座に開始可能
- **基盤（Phase 2）**: セットアップ完了に依存 - すべてのユーザストーリーをブロック
- **ユーザストーリー（Phase 3+）**: すべて基盤フェーズ完了に依存
  - ユーザストーリーは並列で進行可能（リソースがあれば）
  - または優先度順に順次実行（P1 → P2 → P3）
- **品質向上（最終フェーズ）**: すべての必要なユーザストーリー完了に依存

### ユーザストーリー依存関係

- **ユーザストーリー1（P1）**: 基盤（Phase 2）完了後に開始可能 - 他ストーリーへの依存なし
- **ユーザストーリー2（P2）**: 基盤（Phase 2）完了後に開始可能 - US1と統合するが独立してテスト可能
- **ユーザストーリー3（P3）**: 基盤（Phase 2）完了後に開始可能 - US1/US2と統合するが独立してテスト可能

### 各ユーザストーリー内

- テスト → 実装前に作成し、FAILすることを確認
- モデル → サービスの前
- サービス → エンドポイントの前
- コア実装 → 統合の前
- ストーリー完了 → 次の優先度に移行前

### 並列実行の機会

- セットアップタスクで [P] マークされたものはすべて並列実行可能
- 基盤タスクで [P] マークされたもの（Phase 2内）はすべて並列実行可能
- 基盤フェーズ完了後、すべてのユーザストーリーを並列開始可能（チーム能力に応じて）
- ユーザストーリー内の [P] マークされたテストはすべて並列実行可能
- ストーリー内の [P] マークされたモデルはすべて並列実行可能
- 異なるユーザストーリーは異なるチームメンバーによって並列作業可能

---

## 並列実行例: ユーザストーリー1

```bash
# ユーザストーリー1のすべてのテストを同時起動:
Task: "models.pyのユニットテスト in tests/unit/prompt_builder/test_models.py"
Task: "formatters.pyのユニットテスト in tests/unit/prompt_builder/test_formatters.py"

# ユーザストーリー1のすべてのフォーマッター関数を同時実装:
Task: "履歴整形関数の実装 in src/mixseek/prompt_builder/formatters.py"
Task: "ランキング整形関数の実装 in src/mixseek/prompt_builder/formatters.py"
Task: "順位メッセージ生成関数の実装 in src/mixseek/prompt_builder/formatters.py"
```

---

## 実装戦略

### MVP優先（ユーザストーリー1のみ）

1. Phase 1完了: セットアップ
2. Phase 2完了: 基盤（重要 - すべてのストーリーをブロック）
3. Phase 3完了: ユーザストーリー1
4. **停止して検証**: ユーザストーリー1を独立してテスト
5. 準備ができたらデプロイ/デモ

### インクリメンタルデリバリー

1. セットアップ + 基盤完了 → 基盤準備完了
2. ユーザストーリー1追加 → 独立してテスト → デプロイ/デモ（MVP!）
3. ユーザストーリー2追加 → 独立してテスト → デプロイ/デモ
4. ユーザストーリー3追加 → 独立してテスト → デプロイ/デモ
5. 各ストーリーは前のストーリーを壊すことなく価値を追加

### 並列チーム戦略

複数の開発者がいる場合:

1. チームでセットアップ + 基盤を一緒に完了
2. 基盤完了後:
   - 開発者A: ユーザストーリー1
   - 開発者B: ユーザストーリー2
   - 開発者C: ユーザストーリー3
3. ストーリーは独立して完了し、統合される

---

## 注意事項

- [P] タスク = 異なるファイル、依存関係なし
- [Story] ラベルはタスクを特定のユーザストーリーにマップしてトレーサビリティを確保
- 各ユーザストーリーは独立して完了・テスト可能であるべき
- 実装前にテストが失敗することを確認
- 各タスクまたは論理的なグループ後にコミット
- 任意のチェックポイントで停止してストーリーを独立して検証
- 避けるべき: 曖昧なタスク、同じファイルでの競合、独立性を壊すストーリー間の依存関係

---

## Constitution準拠チェックリスト

- [x] **Article 3 (Test-First)**: すべてのテストタスクが実装タスクの前に配置されている
- [x] **Article 4 (Documentation Integrity)**: spec.mdとplan.mdに完全に準拠したタスク設計
- [x] **Article 8 (Code Quality)**: T030でruff + mypy実行を明示
- [x] **Article 9 (Data Accuracy)**: T005でTZ環境変数の明示的処理を実装
- [x] **Article 10 (DRY)**: T014で既存RoundController実装を再利用、重複なし
- [x] **Article 14 (SpecKit Consistency)**: 001-mixseek-core-specsのFR-006に準拠したラウンド処理
- [x] **Article 16 (Type Safety)**: T004でPydantic Models実装、T029でmypyチェック
- [x] **Article 17 (Docstring Standards)**: T028でGoogle-style docstring追加
