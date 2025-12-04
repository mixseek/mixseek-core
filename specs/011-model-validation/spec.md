# Feature Specification: LLMモデル互換性検証

**Feature Branch**: `011-model-validation`
**Created**: 2025-10-22
**Status**: Draft (Implementation Removed)
**Input**: User description: "specs/011-model-validation/spec.md を現在の実装にあわせてください"

**⚠️ IMPORTANT NOTE (2025-11-27)**:
この機能の実装は削除されました。仕様ドキュメントは履歴として残されています。

**削除された実装**:
- `src/mixseek/cli/commands/validate_models.py` - CLIコマンド
- `src/mixseek/validation/` - 検証モジュール全体
- `tests/contract/test_cli_interface.py` - CLIインターフェーステスト
- `tests/e2e/test_real_api_validation.py` - E2Eテスト
- `tests/unit/validation/` - ユニットテスト
- `tests/integration/validation/` - 統合テスト

**削除理由**: メンテナンスされていないため

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 会話モデルの抽出とフィルタリング (Priority: P1)

mixseek運用担当者は、llm-discoveryで取得したモデル一覧(TOML/JSON/CSV形式)から会話モデルだけを抽出し、プロバイダーやモデルIDでフィルタリングして、検証対象を効率的に絞り込む。

**Why this priority**: 検証対象を正しく絞り込まなければ後続工程のコストと時間が無駄になるため。また、フィルタリング機能により段階的な検証が可能になり、特定のプロバイダーやモデルのみを対象とした迅速な検証ができる。

**Independent Test**: 既知のモダリティを含むテスト用ファイルを読み込み、出力された対象リストを確認するだけで完結する。フィルタリング機能も単独でテスト可能。

**Acceptance Scenarios**:

1. **Given** 複数プロバイダーの145モデルを含むファイルが提供されている, **When** 抽出処理を実行する, **Then** 会話モデル(chat modality)のみが抽出される。
2. **Given** モデルのメタデータにprovider・model_id・name・modality・versionが含まれている, **When** 抽出処理を実行する, **Then** 抽出後の各モデルに同じ情報が保持される。
3. **Given** `--filter-provider google` オプションを指定する, **When** 抽出処理を実行する, **Then** Googleプロバイダーのモデルのみが残る。
4. **Given** `--filter-model gemini` オプションを指定する, **When** 抽出処理を実行する, **Then** モデルIDに"gemini"を含むモデルのみが残る。
5. **Given** `--exact-model gemini-2.5-flash` オプションを指定する, **When** 抽出処理を実行する, **Then** 完全一致するモデルのみが残る。

---

### User Story 2 - 技術互換性の判定 (Priority: P1)

mixseek開発者は、抽出済みモデルがmixseekの各エージェント種別(plain/web-search/code-exec)およびPydantic AIのモデルカテゴリに適合しているかを判定し、事前に利用可否を把握する。

**Why this priority**: 技術的に利用できないモデルを早期に除外し、APIコールの失敗を防ぐため。

**Independent Test**: 互換性ルールを網羅したテストデータを用い、判定結果の真偽を確認するだけで検証できる。

**Acceptance Scenarios**:

1. **Given** Google・Anthropic・OpenAIの会話モデルが抽出済みである, **When** 技術互換性チェックを実行する, **Then** 各モデルに対してplain/web-search/code-exec対応状況とPydantic AIカテゴリが記録される。
2. **Given** Claudeモデルが含まれている, **When** 技術互換性チェックを実行する, **Then** Claudeモデルがplainとcode-exec対応、web-search非対応としてマークされる。
3. **Given** OpenAIモデルが含まれている, **When** 技術互換性チェックを実行する, **Then** OpenAIモデルがplainのみ対応として記録される。
4. **Given** いずれのエージェント種別にも対応しないモデルがある, **When** 技術互換性チェックを実行する, **Then** is_any_compatible=Falseとして記録される。

---

### User Story 3 - API動作検証とメトリクス取得 (Priority: P2)

mixseek開発者は、互換性があると判定されたモデルにテストプロンプトを送信し、成功/失敗・レイテンシ(P50/P95/P99)・トークン消費・エラー種別を測定することで、実運用に耐えうるか確認する。API検証はオプション(`--skip-api-validation`で省略可能)であり、コスト上限(`--cost-limit`)を設定できる。

**Why this priority**: 実際のAPI挙動を確認することで、理論上は対応していても動作しないケースを早期に発見できる。ただしAPIコストが発生するためP2とする。

**Independent Test**: テスト用のダミーレスポンスまたはサンドボックス環境を用意し、検証メトリクスが正しく収集・保存されるか確認できる。

**Acceptance Scenarios**:

1. **Given** 互換性ありと判断されたモデル一覧がある, **When** API検証を実行する, **Then** 各モデルについて成功/失敗ステータス・P50/P95/P99レイテンシ・入出力トークン数が記録される。
2. **Given** レート制限や一時的な失敗が発生する, **When** API検証を実行する, **Then** 指数バックオフで最大3回まで再試行し、retry_countが記録される。
3. **Given** `--cost-limit 0.50` オプションを指定する, **When** API検証を実行する, **Then** 累計コストが$0.50を超える前に残処理が停止し、警告が表示される。
4. **Given** `--skip-api-validation` オプションを指定する, **When** コマンドを実行する, **Then** API検証がスキップされ、互換性チェックのみが実行される。
5. **Given** 検証が失敗したモデルがある, **When** API検証を実行する, **Then** error_type・error_messageが記録され、次のモデルの検証が継続される。

---

### User Story 4 - 検証結果の多様な出力形式 (Priority: P1)

mixseek利用チームは、検証結果を複数の出力形式(table/CSV/JSON/TOML/Markdown)で取得し、用途に応じて使い分ける。標準出力への表示、ファイル保存、複数形式の一括生成が可能。成功したモデルのみをフィルタリングする機能(`--only-successful`)も提供される。

**Why this priority**: 出力物が最終的な成果物であり、意思決定の直接的な材料になるため。柔軟な出力形式により、パイプライン連携やレポート生成など多様なユースケースに対応できる。

**Independent Test**: 検証済みのサンプルデータからレポート生成だけを実行し、出力内容が要件を満たすか確認できる。

**Acceptance Scenarios**:

1. **Given** 検証結果が揃っている, **When** `--output-format table`(デフォルト)で実行する, **Then** 標準出力に日本語の表形式で結果が表示される。
2. **Given** 検証結果が揃っている, **When** `--output-format csv --output results.csv`で実行する, **Then** CSVファイルが生成され、モデルID・プロバイダー・互換性・メトリクスが記録される。
3. **Given** 検証結果が揃っている, **When** `--output-format json --output results.json`で実行する, **Then** JSONファイルが生成され、メタデータ・モデル一覧・メトリクスが構造化される。
4. **Given** 検証結果が揃っている, **When** `--output-format toml --output matrix.toml`で実行する, **Then** TOMLファイルに互換性マトリクス・メトリクス・推奨度が階層構造で出力される。
5. **Given** 検証結果が揃っている, **When** `--output-format markdown --output report.md`で実行する, **Then** Markdownレポートにプロバイダー別サマリー・推奨順位・制約事項・検証日時が含まれる。
6. **Given** 検証結果が揃っている, **When** `--output-format all --output ./results/`で実行する, **Then** 指定ディレクトリにCSV・JSON・TOML・Markdown全形式が一括生成される。
7. **Given** `--only-successful` オプションを指定する, **When** API検証後にレポート生成する, **Then** success=Trueのモデルのみが出力に含まれる。
8. **Given** `--columns model_id,provider,rank` オプションを指定する, **When** CSV出力する, **Then** 指定された列のみがCSVに含まれる。

---

### Edge Cases

- 入力ファイルが存在しない、またはTOML/JSON/CSV構文が壊れている場合は処理を即時中断し、FileNotFoundErrorまたはパースエラーをユーザーに通知する。
- 必須フィールド(provider・model_id・name・modality・version・source)が欠落しているモデルを検出した場合は、Pydanticのバリデーションエラーを発生させ、処理を中断する。
- いずれかのプロバイダーのAPI認証が失敗した場合は、成功したプロバイダーのみ検証を継続しつつ、失敗理由を結果に明示する。全プロバイダーが失敗した場合は検証全体を停止する。
- レート制限やタイムアウトが発生した場合は、指数バックオフで最大3回まで再試行し、それでも失敗したモデルは「未検証」として記録しながら残りの検証を続行する。
- モデルから異常なレスポンス(空応答、形式不一致、エラーコード)が返った場合は詳細をerror_type・error_messageに記録し、再試行条件を満たさない限り自動的に再実行しない。
- 累計APIコストがcost_limitに達した場合は、未処理モデルが残っていても追加検証を停止し、どこまで処理できたかをレポートに明記する。
- フィルタリング後にモデルが0件になった場合は、警告メッセージを表示してコード0で正常終了する。
- `--only-successful`を指定したがAPI検証をスキップした場合は、警告メッセージを表示する。
- 出力形式が無効な場合は、有効な形式一覧を表示してエラー終了する。

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: ツールはTOML・JSON・CSV形式のモデルリストを入力として受け取り、形式を自動検出して読み込まなければならない(ModelListLoader)。
- **FR-002**: 抽出処理ではtext-to-speech・image-generation・embedding・moderation・audioなどの非会話系モダリティを自動的に除外しなければならない(ConversationalModelExtractor)。
- **FR-003**: 抽出した各モデルについて、provider(google/openai/anthropic)・model_id・name・modality・version(stable/preview/experimental)・sourceを保持しなければならない(ModelInfo)。
- **FR-004**: プロバイダー名は小文字に正規化され、許可リスト(google/openai/anthropic)に含まれることを検証しなければならない。
- **FR-005**: モデルID・名前・モダリティは空文字列を許容せず、Pydanticバリデーションで拒否しなければならない。
- **FR-006**: CLI経由で`--filter-provider`オプションを指定し、特定プロバイダーのモデルのみに絞り込めなければならない。
- **FR-007**: CLI経由で`--filter-model`オプションを指定し、モデルIDの部分一致でフィルタリングできなければならない。
- **FR-008**: CLI経由で`--exact-model`オプションを指定し、モデルIDの完全一致でフィルタリングできなければならない。
- **FR-009**: 互換性判定では、mixseekエージェントのplain・web-search・code-exec種別ごとに利用可否を判定しなければならない(CompatibilityChecker, CompatibilityResult)。
- **FR-010**: 互換性判定では、Google系モデルはgoogleカテゴリ、Anthropic系モデルはanthropicカテゴリ、OpenAI系モデルはopenaiカテゴリとして認識されなければならない(pydantic_ai_category)。
- **FR-011**: CompatibilityResultはis_any_compatibleプロパティを提供し、いずれかのエージェント種別に対応しているかを判定できなければならない。
- **FR-012**: API検証では、各モデルに対して少なくとも1回のテストプロンプトを実行し、成功/失敗・レスポンス時間(P50/P95/P99)・入出力トークン数・エラー種別を記録しなければならない(APIValidator, ValidationMetrics)。
- **FR-013**: API検証では、レート制限や一時的失敗が発生した場合に指数バックオフ(ExponentialBackoff)で最大3回まで再試行し、retry_countを記録しなければならない。
- **FR-014**: 全体のAPI利用コストに上限値(デフォルト$1.00)を設け、超過前に残りの検証を停止しなければならない(CostTracker, ValidationConfig)。
- **FR-015**: 各プロバイダーのAPI資格情報が未設定または無効な場合は直ちにエラーを返し、成功したプロバイダーのみ処理を継続しなければならない。
- **FR-016**: すべての検証結果はvalidated_atタイムスタンプ(UTC)とともに記録されなければならない(ValidationMetrics)。
- **FR-017**: CLI経由で`--skip-api-validation`オプションを指定し、API検証をスキップして互換性チェックのみを実行できなければならない。
- **FR-018**: CLI経由で`--cost-limit`オプションを指定し、APIコストの上限を設定できなければならない。
- **FR-019**: 検証結果から推奨レポート(RecommendationReport)を生成し、モデルごとの互換性・メトリクス・推奨度ランク(⭐⭐⭐/⭐⭐/⭐)・コストパフォーマンス(high/medium/low)を含めなければならない。
- **FR-020**: 推奨度ランクは、code-exec対応かつplain対応なら⭐⭐⭐、plain対応のみなら⭐⭐、それ以外は⭐と判定されなければならない。
- **FR-021**: overall_statusとして、未検証・検証失敗・非互換・推奨のいずれかを算出しなければならない(RecommendationReport.overall_status)。
- **FR-022**: CLI経由で`--output-format table`(デフォルト)を指定し、標準出力に日本語の表形式で結果を表示できなければならない。
- **FR-023**: CLI経由で`--output-format csv`および`--output`を指定し、CSV形式でファイル保存できなければならない(または標準出力)。
- **FR-024**: CLI経由で`--output-format json`および`--output`を指定し、JSON形式でファイル保存できなければならない(または標準出力)。
- **FR-025**: CLI経由で`--output-format toml`および`--output`を指定し、TOML形式の互換性マトリクスをファイル保存できなければならない(TOMLMatrixGenerator)。
- **FR-026**: CLI経由で`--output-format markdown`および`--output`を指定し、Markdownレポートをファイル保存できなければならない(MarkdownReportGenerator)。
- **FR-027**: CLI経由で`--output-format all`および`--output`(ディレクトリ)を指定し、CSV・JSON・TOML・Markdown全形式を一括生成できなければならない。
- **FR-028**: CLI経由で`--only-successful`オプションを指定し、API検証に成功したモデルのみに出力を絞り込めなければならない。
- **FR-029**: CLI経由で`--columns`オプションを指定し、CSV出力の列を選択できなければならない。
- **FR-030**: 処理の実行中は、[INFO]/[WARNING]/[ERROR]/[SUCCESS]プレフィックスを付けた情報メッセージを標準出力/標準エラー出力に表示しなければならない。
- **FR-031**: 致命的エラー発生時は適切な終了コード(0=正常終了、1=エラー、2=ファイル未発見)を返さなければならない。

### Key Entities *(include if feature involves data)*

本仕様で扱う主要エンティティは`pydantic.BaseModel`を用いて実装し、堅牢なデータ検証を行う(Article 9, Article 16)。

- **ModelInfo**: プロバイダー・モデルID・表示名・モダリティ・バージョン属性・データソースを保持する入力データの1行を表す。extra="forbid"により未定義フィールドを拒否し、validate_assignment=Trueにより代入時もバリデーションを実行する。
- **CompatibilityResult**: 各モデルのエージェント種別(plain/web-search/code-exec)ごとの可否、Pydantic AIカテゴリ(google/openai/anthropic/unknown)、function calling対応状況、認証状態、ノートをまとめたレコード。is_any_compatibleプロパティでいずれかの種別に対応しているか判定できる。
- **ValidationMetrics**: API検証の成功状態・エラー種別・エラーメッセージ・レイテンシ統計(P50/P95/P99)・入出力トークン数・再試行回数・検証タイムスタンプ(UTC)・推定コストを含む測定値。
- **RecommendationReport**: TOML/Markdown出力に用いる集約データで、モデルID・プロバイダー・名前・互換性・メトリクス・推奨度ランク(⭐⭐⭐/⭐⭐/⭐)・コストパフォーマンス(high/medium/low)・制約事項・ノートを含む。overall_statusとestimated_cost_usdはcomputed_fieldとして自動算出される。
- **ValidationConfig**: 環境変数から読み込む検証設定(Pydantic Settings)で、コスト上限(MIXSEEK_COST_LIMIT_USD)・最大再試行回数(MIXSEEK_MAX_RETRIES)・再試行ベース遅延(MIXSEEK_RETRY_BASE_DELAY)・検証タイムアウト(MIXSEEK_VALIDATION_TIMEOUT)・最大並行検証数(MIXSEEK_MAX_CONCURRENT_VALIDATIONS)を管理する(Article 9: no hardcoding)。
- **ModelListInput**: TOML/JSON/CSV統一表現で、モデル一覧とメタデータを保持する。filter_conversationalメソッドで会話モデルのみを抽出できる。

### Validation Module Structure

本機能で導入するバリデーションロジックは、スケーラビリティと保守性を考慮して以下のディレクトリ構造で実装済み(Article 10: DRY, Article 6: Anti-Abstraction):

```
src/mixseek/validation/
├── __init__.py              # 公開APIをエクスポート
├── models.py                # データモデル (ModelInfo, CompatibilityResult, ValidationMetrics, etc.)
├── loaders.py               # ModelListLoader (TOML/JSON/CSV読み込み)
├── extractors.py            # ConversationalModelExtractor (会話モデル抽出)
├── compatibility.py         # CompatibilityChecker (互換性判定)
├── api_validator.py         # APIValidator (API検証)
├── cost_tracker.py          # CostTracker (コスト追跡)
├── retry.py                 # ExponentialBackoff (再試行ロジック)
├── report_generator.py      # TOMLMatrixGenerator, MarkdownReportGenerator
└── exceptions.py            # カスタム例外
```

**設計原則**:
- 各モジュールは単一責務原則に従い、独立したモジュールとして管理される
- データモデルは`pydantic.BaseModel`で定義され、厳格な型チェックとバリデーションを実施
- 共通ロジック(エラーハンドリング、ログ記録)を適切に抽象化し、DRY原則を遵守
- フレームワーク機能(Pydantic, Typer)を直接利用し、不要なラッパーを作らない(Article 6)

## Assumptions

- llm-discoveryで生成されたモデルリストは最新状態であり、必要なメタデータ(provider・model_id・name・modality・version・source)が入力に含まれていると想定する。
- 運用チームが必要なプロバイダーのAPI資格情報を事前に環境変数またはデフォルト設定で用意し、検証環境は外部APIへアクセスできると想定する。
- コスト計算は各プロバイダーの公開料金表に準拠し、入出力トークン数から推定できると想定する。
- テストプロンプトは全モデルで共通の短文を使用し、モデル固有の追加設定は必要ないと想定する。
- ValidationConfigの環境変数が未設定の場合、合理的なデフォルト値(cost_limit=$1.00, max_retries=3, retry_base_delay=1.0秒, validation_timeout=120秒, max_concurrent_validations=5)が使用されると想定する。

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 145件の入力から会話モデルの抽出精度が95%以上(誤判定は全体の5%未満)である。
- **SC-002**: 会話モデルのうち少なくとも90%でAPI動作検証が成功し、残りは失敗理由がerror_type・error_messageに記録される。
- **SC-003**: 最大70モデルの検証を2時間以内に完了し、処理時間がメタデータに記録される。
- **SC-004**: 累計APIコストがcost_limit(デフォルト$1.00)未満で完了する。
- **SC-005**: すべての検証済みモデルにvalidated_atタイムスタンプと推奨度ランクが付与された互換性マトリクスをユーザーが取得できる。
- **SC-006**: レポート閲覧者の80%以上が3分以内に採用候補モデルを決定できたとユーザーテストで確認される。
- **SC-007**: 生成されたTOML・Markdown・JSON・CSVが既存のmixseek設定ワークフローや外部ツールにそのまま読み込めることを受入テストで確認する。
- **SC-008**: フィルタリングオプション(`--filter-provider`, `--filter-model`, `--exact-model`)により、検証対象を90%以上削減できるケースがあることを確認する。
- **SC-009**: `--only-successful`オプションにより、失敗モデルを除外した推奨リストが即座に得られることを確認する。
- **SC-010**: 複数の出力形式(`--output-format all`)を同時生成する場合、単一形式生成の合計時間+20%以内で完了することを確認する。
