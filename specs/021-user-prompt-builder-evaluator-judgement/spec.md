# 機能仕様書: UserPromptBuilder - Evaluator/JudgementClient統合

**機能ブランチ**: `102-user-prompt-builder-evaluator-judgement`
**作成日**: 2025-11-20
**ステータス**: ドラフト
**入力**: ユーザ説明: "@specs/015-user-prompt-builder-team/ はUserPromptBuilderの親仕様です。この仕様においてPendingとなっていたEvaluator, JudgementClientのuser_prompt整形処理をUserPromptBuilderに移植します。親仕様に厳密に従ったうえで、以下の追加要件を加味して仕様を決定して下さい。

[追加要件]
- Evaluatorが呼び出すプロンプト成形メソッドは、引数としてオリジナルのuser_queryとTeamのSubmissionを受け取るようにする
- JudgementClientが呼び出すプロンプト成形メソッドは、Teamのプロンプト成形メソッドと同じコンテキストモデルを引数として受け取る
- Evaluator, JudgementCLientで既存実装されているユーザプロンプト成形ロジックを可能な限りそのまま移植する
- Evaluator, JudgementCLientで受け取るユーザプロンプトは、成形前のオリジナルの文字列を受け取り、それをPromptBuilderで加工する"

## Clarifications

### Session 2025-11-20

- Q: ブランチ名とspecディレクトリ名を変更すべきか？ → A: 102-user-prompt-builder-evaluator-judgementに変更
- Q: Evaluatorのプレースホルダー変数に現在時刻を追加すべきか？ → A: current_datetimeを追加（Teamプロンプトと同様）
- Q: Evaluatorのデフォルトプロンプトの英語部分を日本語化すべきか？ → A: Teamプロンプトを参考に日本語に変換
- Q: build_*_promptメソッドの引数仕様は？ → A: 対応するコンテキストモデル（EvaluatorPromptContext, RoundPromptContext）を引数に受け取る
- Q: JudgementClientのプレースホルダー変数のサポート範囲は？ → A: Teamで実装済みのすべてのプレースホルダー変数をサポート（user_prompt, round_number, submission_history, ranking_table, team_position_message, current_datetime）
- Q: JudgmentPromptContextは必要か？ → A: 不要。既存のRoundPromptContextを利用する

### Session 2025-11-25

- Q: FR-010のranking_tableとteam_position_messageの整形方法を明確化すべきか？ → A: prompt_builder.formattersの既存実装（format_ranking_table、generate_position_message）を使用することを明記する
- Q: FR-013（JudgementClientがUserPromptBuilderを呼び出す）を維持すべきか？ → A: 削除する。代わりにRoundControllerがプロンプト整形を担当することを明記する

## ユーザシナリオとテスト *(必須)*

### ユーザストーリー1 - Evaluatorのプロンプト成形移行 (優先度: P1)

開発者として、Evaluatorが受け取るuser_queryをUserPromptBuilderで整形できるようにし、Evaluatorのメトリクス評価時にLLMに渡すプロンプトの品質と一貫性を向上させたい。

**この優先度の理由**: Evaluatorは評価システムの中核コンポーネントであり、プロンプト品質の一元管理により、評価精度の実験と改善が可能になる。Teamプロンプト整形と同じ設計パターンを適用することで、コードの一貫性とメンテナンス性が向上する。

**独立テスト**: Evaluatorがuser_queryとsubmissionを受け取り、UserPromptBuilderを使ってメトリクス評価用のプロンプトを整形し、既存実装と同じフォーマット（"User Query: ... / Submission: ..."形式）が生成されることで検証可能である。

**受け入れシナリオ**:

1. **前提** EvaluatorがEvaluationRequestを受け取る、**実行** EvaluatorPromptContextを作成してUserPromptBuilderのbuild_evaluator_promptメソッドを呼び出す、**結果** user_queryとsubmissionが整形され、既存のLLMJudgeMetric._get_user_promptメソッドと同じフォーマットのプロンプトが返される
2. **前提** evaluator_user_promptがprompt_builder.tomlに定義されている、**実行** UserPromptBuilderがプロンプトを整形する、**結果** カスタムテンプレートが使用され、`{{ user_prompt }}`、`{{ submission }}`、`{{ current_datetime }}`プレースホルダーが正しく埋め込まれる
3. **前提** evaluator_user_promptが設定ファイルに定義されていない、**実行** UserPromptBuilderがプロンプトを整形する、**結果** デフォルトテンプレート（既存実装を日本語化したフォーマット）が使用される
4. **前提** LLMJudgeMetricのevaluateメソッドが呼び出される、**実行** UserPromptBuilderで整形されたプロンプトを使用してLLMを呼び出す、**結果** 既存のテストケースがすべてパスし、評価結果が既存実装と同等である
5. **前提** current_datetimeプレースホルダーが使用される、**実行** UserPromptBuilderがプロンプトを整形する、**結果** 現在日時がISO 8601形式（タイムゾーン付き）で埋め込まれる

---

### ユーザストーリー2 - JudgementClientのプロンプト成形移行 (優先度: P2)

開発者として、RoundControllerがUserPromptBuilderを使用してjudgment用プロンプトを整形し、JudgementClientに渡すことで、改善判定プロンプトの実験と精度向上を容易にしたい。

**この優先度の理由**: JudgementClientはラウンド継続判定の中核であり、プロンプト品質がラウンド数と実行効率に直接影響する。Teamプロンプトと同じRoundPromptContextモデルを使用することで、コンテキスト情報の一貫性が保たれる。

**独立テスト**: RoundControllerがRoundPromptContextを作成してUserPromptBuilderでプロンプトを整形し、整形済みプロンプトをJudgementClientに渡し、既存実装と同じフォーマット（"# タスク / # ユーザクエリ / # ラウンド履歴"形式）が生成されることで検証可能である。

**受け入れシナリオ**:

1. **前提** RoundControllerが次ラウンド判定を開始する、**実行** RoundControllerがRoundPromptContextを作成し、UserPromptBuilderのbuild_judgment_promptメソッドを呼び出す、**結果** user_promptとround_historyが整形され、既存のJudgmentClient._format_user_promptメソッドと同じフォーマットのプロンプトが返される
2. **前提** judgment_user_promptがprompt_builder.tomlに定義されている、**実行** UserPromptBuilderがプロンプトを整形する、**結果** カスタムテンプレートが使用され、すべてのTeamプレースホルダー変数（user_prompt, round_number, submission_history, ranking_table, team_position_message, current_datetime）が正しく埋め込まれる
3. **前提** judgment_user_promptが設定ファイルに定義されていない、**実行** UserPromptBuilderがプロンプトを整形する、**結果** デフォルトテンプレート（既存実装と同じフォーマット）が使用される
4. **前提** round_historyに複数ラウンドのデータが含まれる、**実行** UserPromptBuilderがプロンプトを整形する、**結果** 各ラウンドの提出内容、スコア、スコア詳細（score_details）が既存フォーマットで整形される
5. **前提** RoundControllerが整形済みプロンプトをJudgementClientに渡す、**実行** JudgementClientがjudge_improvement_prospectsメソッドでLLMを呼び出す、**結果** 既存のテストケースがすべてパスし、判定結果が既存実装と同等である
6. **前提** RoundPromptContextにteam_id、team_name、execution_id、storeが含まれる、**実行** ランキング情報とチーム位置メッセージのプレースホルダーが使用される、**結果** Teamプロンプトと同じフォーマットでランキング情報が埋め込まれる

---

### ユーザストーリー3 - 設定ファイル初期化の拡張 (優先度: P3)

開発者・研究者として、`mixseek config init`コマンドでEvaluatorとJudgementClient用のデフォルトプロンプトテンプレートが生成され、カスタマイズの開始点として使用できるようにしたい。

**この優先度の理由**: 新規ユーザーが3つのコンポーネント（Team, Evaluator, JudgementClient）すべてのプロンプトテンプレートを一括で取得でき、実験の開始が容易になる。ドキュメントとしても機能する。

**独立テスト**: `mixseek config init`コマンドを実行し、prompt_builder.tomlにevaluator_user_promptとjudgment_user_promptが追加されることで検証可能である。

**受け入れシナリオ**:

1. **前提** `mixseek config init`を実行する、**実行** prompt_builder.tomlを確認する、**結果** evaluator_user_promptとjudgment_user_promptが変数埋め込み形式で定義され、利用可能なプレースホルダー変数がコメント付きで記載されている
2. **前提** 生成されたevaluator_user_promptを使用する、**実行** UserPromptBuilderでプロンプトを整形する、**結果** 既存のLLMJudgeMetric実装と同じ出力が生成される
3. **前提** 生成されたjudgment_user_promptを使用する、**実行** UserPromptBuilderでプロンプトを整形する、**結果** 既存のJudgmentClient実装と同じ出力が生成される

---

### エッジケース

- **evaluator_user_promptが設定ファイルに定義されていない場合**: デフォルトテンプレート（既存LLMJudgeMetric._get_user_prompt実装と同じ形式）が使用される
- **judgment_user_promptが設定ファイルに定義されていない場合**: デフォルトテンプレート（既存JudgmentClient._format_user_prompt実装と同じ形式）が使用される
- **Jinja2テンプレート構文エラー**: Jinja2の解析エラーが発生し、エラー箇所を含む明確なエラーメッセージが表示される
- **存在しないプレースホルダー変数を使用**: Jinja2がエラーを発生させ、未定義の変数名を含むエラーメッセージが表示される
- **round_historyが空の場合（RoundController→UserPromptBuilder）**: ValidationErrorが発生する
- **user_queryまたはsubmissionが空の場合（Evaluator）**: Pydantic ValidationErrorが発生する（EvaluationRequestの既存バリデーションロジックを維持）
- **RoundControllerがstoreを保持していない場合**: ranking_tableとteam_position_messageが利用できない旨がプロンプトに埋め込まれる

## 要件 *(必須)*

### 機能要件

- **FR-001**: UserPromptBuilderは、Evaluatorのメトリクス評価用プロンプトを整形するbuild_evaluator_promptメソッドを提供しなければならない
- **FR-002**: build_evaluator_promptメソッドは、引数としてEvaluatorPromptContext（user_query、submissionを含む）を受け取り、整形されたプロンプト文字列を返さなければならない
- **FR-003**: build_evaluator_promptメソッドは、以下のプレースホルダー変数を提供しなければならない:
  - `user_prompt`: 元のユーザークエリ
  - `submission`: AIエージェントのSubmission
  - `current_datetime`: 現在日時（ISO 8601形式、タイムゾーン付き）
- **FR-004**: evaluator_user_promptが設定ファイル（prompt_builder.toml）に定義されていない場合、既存のLLMJudgeMetric._get_user_promptメソッドと同じデフォルトテンプレートが使用されなければならない
- **FR-005**: デフォルトのevaluator_user_promptは以下のフォーマットでなければならない（英語部分を日本語に変換）:
  ```
  ---
  現在日時: {{ current_datetime }}
  ---
  # タスク
  以下のユーザプロンプトに対するエージェントの提出内容を、あなたの役割に従って評価してください。

  # ユーザから指定されたタスク
  {{ user_prompt }}

  # 提出内容
  {{ submission }}
  ```
- **FR-006**: LLMJudgeMetricクラスの_get_user_promptメソッドは、UserPromptBuilderのbuild_evaluator_promptメソッドを呼び出すように変更されなければならない
- **FR-007**: UserPromptBuilderは、JudgementClientの改善判定用プロンプトを整形するbuild_judgment_promptメソッドを提供しなければならない
- **FR-008**: build_judgment_promptメソッドは、引数とし実装済みのRoundPromptContext（user_prompt、round_number、round_history、team_id、team_name、execution_id、storeを含む）を受け取り、整形されたプロンプト文字列を返さなければならない
- **FR-009**: build_judgment_promptメソッドは、Teamプロンプトで実装済みのすべてのプレースホルダー変数を提供しなければならない:
  - `user_prompt`: 元のユーザープロンプト（注: JudgementClientではuser_queryとして渡されるが、RoundPromptContextではuser_promptフィールド名を使用。RoundPromptContext側に統合）
  - `round_number`: 現在のラウンド番号
  - `submission_history`: 過去のSubmission履歴（整形済み文字列）
  - `ranking_table`: Leader Boardランキング情報（整形済み文字列）
  - `team_position_message`: 当該チームの順位メッセージ（整形済み文字列）
  - `current_datetime`: 現在日時（ISO 8601形式、タイムゾーン付き）
- **FR-010**: 以下のプレースホルダーは、prompt_builder.formattersの既存実装を利用しなければならない:
  - `submission_history`: `format_submission_history(round_history)` を呼び出し、各ラウンドのスコア、スコア詳細、提出内容を整形する
  - `ranking_table`: `format_ranking_table(ranking, team_id, team_name)` を呼び出し、Leader Boardのランキング情報を整形する
  - `team_position_message`: `generate_position_message(position, total_teams)` を呼び出し、チームの順位メッセージを生成する
- **FR-011**: judgment_user_promptが設定ファイル（prompt_builder.toml）に定義されていない場合、既存のJudgmentClient._format_user_promptメソッドと同じデフォルトテンプレートが使用されなければならない
- **FR-012**: デフォルトのjudgment_user_promptは以下のフォーマットでなければならない:
  ```
  # タスク
  以下の提出履歴に基づいて、チームは次のラウンドに進むべきでしょうか？判定、理由、確信度を提供してください。

  # ユーザクエリ
  {{ user_prompt }}

  # 提出履歴
  {{ submission_history }}

  # リーダーボード
  {{ ranking_table }}
  ```
- **FR-013**: RoundControllerは、各ラウンドの評価後にRoundPromptContextを作成し、UserPromptBuilderのbuild_judgment_promptメソッドを呼び出してJudgementClient用の整形済みプロンプトを取得しなければならない
- **FR-014**: PromptBuilderSettingsクラスは、以下の設定項目を追加しなければならない:
  - `evaluator_user_prompt`: Evaluatorのプロンプトテンプレート文字列（デフォルト: FR-005に定義されたテンプレート）
  - `judgment_user_prompt`: JudgementClientのプロンプトテンプレート文字列（デフォルト: FR-012に定義されたテンプレート）
- **FR-015**: `mixseek config init`コマンドは、prompt_builder.tomlにevaluator_user_promptとjudgment_user_promptのデフォルト値を生成しなければならない
- **FR-016**: 生成されるprompt_builder.tomlには、各プロンプトテンプレートの利用可能なプレースホルダー変数がコメント付きで記載されなければならない
- **FR-017**: Evaluatorの既存テストケース（tests/unit/evaluator/配下）は、UserPromptBuilder統合後も100%パスしなければならない
- **FR-018**: JudgementClientの既存テストケース（tests/unit/round_controller/test_improvement_judgment.py）は、UserPromptBuilder統合後も100%パスしなければならない
- **FR-019**: UserPromptBuilderのインスタンス化は、Evaluatorのコンストラクタで行われ、workspace_pathを受け取らなければならない。JudgementClientはUserPromptBuilderのインスタンスを保持しない
- **FR-020**: Evaluatorは、成形前のオリジナルのuser_query文字列を受け取り、それをUserPromptBuilderで加工しなければならない
- **FR-021**: JudgmentClientクラスのjudge_improvement_prospectsメソッドは、整形済みプロンプト（formatted_prompt: str）を引数として受け取り、LLM呼び出しのみを行わなければならない。JudgmentClientはUserPromptBuilderへの依存を持たない

### 主要エンティティ

- **UserPromptBuilder**: プロンプト整形を担当するコンポーネント。Teamプロンプト整形（build_team_prompt）に加えて、Evaluatorプロンプト整形（build_evaluator_prompt）とJudgementClientプロンプト整形（build_judgment_prompt）の機能を持つ
- **PromptBuilderSettings**: UserPromptBuilderの設定を表すPydantic Model。team_user_prompt、evaluator_user_prompt、judgment_user_promptを保持する
- **EvaluatorPromptContext**: Evaluatorプロンプト生成に必要なコンテキスト情報を表すPydantic Model（新規）。user_prompt（str）、submission（str）を保持する
- **RoundPromptContext**: プロンプト生成に必要なコンテキスト情報を表すPydantic Model（既存、specs/092で定義）。RoundControllerがこのモデルを作成してUserPromptBuilderに渡す。user_prompt（str）、round_number（int）、round_history（list[RoundState]）、team_id（str）、team_name（str）、execution_id（str）、store（AggregationStore | None）を保持する
- **LLMJudgeMetric**: すべてのLLM-as-a-Judgeメトリクスの基底クラス。_get_user_promptメソッドがUserPromptBuilderを使用するように変更される
- **JudgmentClient**: ラウンド継続判定を担当するクライアント。judge_improvement_prospectsメソッドが整形済みプロンプト（str）を引数として受け取り、Pydantic AI Agentを使用してLLM呼び出しのみを行う。UserPromptBuilderへの依存を持たず、_format_user_promptメソッドは削除される

## 成功基準 *(必須)*

### 測定可能な成果

- **SC-001**: LLMJudgeMetric._get_user_promptメソッドがUserPromptBuilderのbuild_evaluator_promptメソッドに100%移行され、同じ出力が生成される
- **SC-002**: RoundControllerがUserPromptBuilderのbuild_judgment_promptメソッドを呼び出し、JudgementClientに整形済みプロンプトを渡すフローが100%正確に動作し、既存のJudgmentClient._format_user_promptメソッドと同じ出力が生成される
- **SC-003**: Evaluatorのプロンプト整形が既存実装と同じ出力を生成し、すべてのユニットテストとインテグレーションテストがパスする
- **SC-004**: JudgementClientがRoundControllerから受け取った整形済みプロンプトを使用してLLM呼び出しを行い、既存実装と同じ判定結果を返し、すべてのユニットテストがパスする
- **SC-005**: カスタムevaluator_user_promptを使用したプロンプト整形が100%正確に動作する（プレースホルダー変数が正しく埋め込まれる）
- **SC-006**: カスタムjudgment_user_promptを使用したプロンプト整形が100%正確に動作する（プレースホルダー変数が正しく埋め込まれる）
- **SC-007**: `mixseek config init`コマンドで生成されるprompt_builder.tomlに、evaluator_user_promptとjudgment_user_promptが100%正確に含まれる
- **SC-008**: 生成された設定ファイルのevaluator_user_promptとjudgment_user_promptを使用してプロンプトを整形し、既存実装と同じ出力が生成される
- **SC-009**: UserPromptBuilderのbuild_evaluator_promptメソッドが10ms以内に完了する（95パーセンタイル）
- **SC-010**: UserPromptBuilderのbuild_judgment_promptメソッドが50ms以内に完了する（95パーセンタイル、複数ラウンド履歴を含む）
- **SC-011**: JudgementClientはUserPromptBuilderへの依存を持たず、整形済みプロンプトのみを受け取る設計により、単一責任の原則が100%遵守される

## 前提

- UserPromptBuilder（specs/015-user-prompt-builder-team）は既に実装済みであり、本仕様ではEvaluatorとJudgementClient用のメソッドを追加する
- Evaluator（specs/006-evaluator）は既に実装済みであり、LLMJudgeMetric._get_user_promptメソッドを修正する
- JudgmentClient（specs/012-round-controller）は既に実装済みであり、judge_improvement_prospectsメソッドのシグネチャを変更して整形済みプロンプトを受け取るように修正する。_format_user_promptメソッドは削除される
- RoundController（specs/012-round-controller）は既に実装済みであり、UserPromptBuilderを保持してjudgment用プロンプトを整形し、JudgementClientに渡す責務を追加する
- RoundState（specs/012-round-controller）は既に実装済みであり、score_detailsフィールドが存在する
- AggregationStore（specs/015-user-prompt-builder-team）は既に実装済みであり、RoundControllerが保持してRoundPromptContextに渡す
- Configuration Manager（specs/013-configuration）は既に実装済みであり、UserPromptBuilderはConfigurationManagerを使用して設定を読み込む
- 環境変数`MIXSEEK_WORKSPACE`は設定済みであり、設定ファイルは`$MIXSEEK_WORKSPACE`配下に配置される
- Jinja2ライブラリがプロジェクトに既にインストールされている
- EvaluatorはUserPromptBuilderのインスタンスを保持し、プロンプト整形時に呼び出す。JudgementClientはUserPromptBuilderのインスタンスを保持せず、RoundControllerから整形済みプロンプトを受け取る
- プレースホルダー変数（round_history）はUserPromptBuilder内で事前に整形され、テンプレートには整形済み文字列として渡される

## 依存関係

- **親仕様**: specs/015-user-prompt-builder-team（UserPromptBuilderの基本実装）
  - FR-001〜FR-017（Teamプロンプト整形の実装）
  - build_team_promptメソッドの設計パターンを踏襲
  - RoundPromptContext、AggregationStoreの定義
- **関連仕様**:
  - specs/006-evaluator（Evaluator実装、LLMJudgeMetric基底クラス）
  - specs/012-round-controller（RoundController、JudgmentClient、RoundState定義）
    - RoundControllerがUserPromptBuilderを保持してjudgmentプロンプトを整形する責務を追加
    - JudgmentClientは整形済みプロンプトのみを受け取るように変更
  - specs/013-configuration（Configuration Manager、Pydantic Settings）
- **技術依存**:
  - Jinja2 (>=3.1.0)
  - Pydantic (>=2.12)
  - pydantic-settings (>=2.12)
  - tomllib (Python 3.11+標準ライブラリ)
