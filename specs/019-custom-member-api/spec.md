# Feature Specification: bitbank Public API連携サンプルエージェント

**Feature Branch**: `133-custom-member-api`
**Created**: 2025-11-20
**Status**: Draft
**Input**: User description: "bitbank Public API連携サンプルエージェント - 時系列データ分析とパフォーマンス比較"
**Parent Spec**: `specs/018-custom-member/spec.md`

## User Scenarios & Testing

### User Story 1 - 暗号資産データ取得と分析 (Priority: P1)

開発者は、bitbank Public APIを利用してリアルタイムの暗号資産価格データ（BTC/JPY、XRP/JPYなどの通貨ペア）を取得し、投資家向け金融指標分析（年率リターン、年率ボラティリティ、シャープレシオ、最大ドローダウン、リターン分布など）を実行します。取得したデータは、カスタムエージェント内で処理され、分析結果が返されます。

**Why this priority**: データ取得と基本分析は本サンプルエージェントの中核機能であり、外部API連携パターンの基本を示すために最も重要です。

**Independent Test**: bitbank Public APIの/ticker エンドポイント（認証不要）を呼び出し、取得したJSON形式の価格データをパースして金融指標を計算することで、Leader Agentとの統合なしに独立してテスト可能です。

**Acceptance Scenarios**:

1. **Given** 開発者がエージェントに「btc_jpyの現在価格を取得」とプロンプトを送信する、**When** エージェントがbitbank APIの/tickerエンドポイントを呼び出す、**Then** 最新の買値・売値・出来高が返される
2. **Given** 複数の通貨ペア（btc_jpy、xrp_jpy）を指定する、**When** エージェントが各通貨ペアのデータを取得する、**Then** 各ペアの価格情報が整形されて返される
3. **Given** エージェントが時系列データ（candlestick情報）を取得する、**When** 指定期間（1日、1週間など）のロウソク足データを要求する、**Then** OHLCV（始値、高値、安値、終値、出来高）データが時系列順に返される
4. **Given** 取得したデータを金融指標分析する、**When** 年率リターン、年率ボラティリティ、シャープレシオ、最大ドローダウン、リターン分布（歪度・尖度）を計算する、**Then** LLMが金融指標を自然言語で解釈した分析結果（リスク調整後パフォーマンス、ドローダウンリスク評価、リターン分布特性）がMarkdown形式で返される

---

### User Story 2 - テストとデバッグ (Priority: P2)

開発者は、bitbank API連携エージェントの品質を保証するため、単体テスト・統合テスト・エンドツーエンドテストを作成します。APIモックを使用した単体テスト、実際のAPIを使用したE2Eテスト（`@pytest.mark.e2e`）により、エージェントの信頼性を確認します。

**Why this priority**: テストはエージェントの信頼性を保証するために重要ですが、基本実装の後に実施できます。

**Independent Test**: テストスイート自体が実行可能であり、開発者が段階的にテストを追加しながら品質を向上できます。

**Acceptance Scenarios**:

1. **Given** エージェントのコアロジックをテストする、**When** モックを使用した単体テストを実行する、**Then** APIクライアント、データパース、金融指標計算のロジックが正しく動作することを確認できる
2. **Given** 実際のbitbank APIを使用する、**When** E2Eテスト（`@pytest.mark.e2e`）を実行する、**Then** 本番環境に近い条件でエージェントの動作を検証できる
3. **Given** APIエラー（404、500、ネットワークタイムアウト）が発生する、**When** エラーハンドリングをテストする、**Then** 構造化エラー情報（metadata）とLLMによる自然言語の原因説明・対処法（content、Markdown形式）がユーザーに返される
4. **Given** コアロジックのテストカバレッジを測定する、**When** カバレッジレポートを確認する、**Then** 80%以上のカバレッジが達成されている

---

### Edge Cases

- APIレート制限（bitbank APIの制限は明示されていないが、一般的なREST APIの制限を考慮）に達した場合、リトライロジックとエクスポネンシャルバックオフが正しく機能するか？
- ネットワークタイムアウト、接続エラー、不正なJSON応答が発生した場合、エラーが適切にハンドリングされるか？
- 無効な通貨ペア（存在しないペア、タイポなど）が指定された場合、明確なエラーメッセージが表示されるか？
- 大量の時系列データ（数千件のロウソク足データ）を取得する場合、メモリ使用量が適切に管理されるか？
- APIレスポンスの構造が変更された場合、エージェントがエラーを検出し通知できるか？
- 複数の通貨ペアを並行して取得する場合、並行処理が正しく機能し、結果が正しく統合されるか？

## Requirements

### Functional Requirements

**注**: カスタムエージェントの基本要件（抽象基底クラス、TOML設定、動的ロード機構、CLI実行）は親仕様（`specs/009-member/spec.md`）と`specs/018-custom-member/spec.md`で定義されています。本仕様はbitbank API連携エージェント固有の要件に焦点を当てます。

#### bitbank API連携エージェント要件

- **FR-001**: システムは、bitbank Public API（https://github.com/bitbankinc/bitbank-api-docs）の/ticker エンドポイントを呼び出し、指定された通貨ペア（btc_jpy、xrp_jpy等）の最新価格情報を取得しなければならない
- **FR-002**: システムは、/candlestickエンドポイントを呼び出し、指定された期間（1日、1週間等）の時系列OHLCV（始値、高値、安値、終値、出来高）データを取得しなければならない
- **FR-003**: システムは、candlestickデータ（時系列OHLCV）から投資家向け金融指標（年率リターン、年率ボラティリティ、最大ドローダウン、シャープレシオ、ソルティーノレシオ、リターン分布の歪度・尖度）を計算し、完全な構造化データ（FinancialSummary）を`MemberAgentResult.metadata`にJSON形式で格納するとともに、LLMが金融指標を自然言語で解釈・分析した結果（リスク調整後パフォーマンス、ドローダウンリスク評価、リターン分布特性）を`MemberAgentResult.content`にMarkdown形式で提供しなければならない。年率換算は365日取引を前提とし、シャープレシオ計算には日本10年国債利回り（年率0.1%）をリスクフリーレートとして使用し、ソルティーノレシオの下方リスク閾値（MAR）は0（ゼロリターン）とする。最大ドローダウンはrunning maximum methodで計算する（注: tickerデータは最新価格の取得のみに使用し、金融分析の対象としない）
- **FR-004**: システムは、APIレート制限、ネットワークエラー、タイムアウト、無効なJSON応答を適切にハンドリングしなければならない
- **FR-005**: システムは、エラー発生時に構造化エラー情報（error_code、error_message、timestamp）を`MemberAgentResult.metadata`に格納し、LLMが自然言語でエラーの原因・対処法・推奨アクションを解釈した結果を`MemberAgentResult.content`にMarkdown形式で提供しなければならない
- **FR-006**: システムは、HTTP 429（レート制限）エラー発生時にエクスポネンシャルバックオフとリトライロジックを実装しなければならない
- **FR-007**: システムは、APIエンドポイントURLとリトライ設定をTOML設定ファイルで管理しなければならない（環境変数またはTOMLから読み込み、ハードコード禁止）
- **FR-008**: システムは、`BaseMemberAgent`インターフェースに準拠し、TOML設定で`type = "custom"`を使用しなければならない
- **FR-009**: システムは、単体テスト（APIモック使用）、統合テスト、エンドツーエンドテスト（実際のAPI使用、`@pytest.mark.e2e`）を提供しなければならない

### Key Entities

**注**: カスタムエージェントの基本エンティティ（`BaseMemberAgent`、`MemberAgentConfig`、`MemberAgentResult`、`Context Parameter`）は親仕様（`specs/009-member/spec.md`）で定義されています。

#### bitbank API連携エージェント固有のエンティティ

- **BitbankTickerData**: 通貨ペアの最新価格情報（buy: 買値、sell: 売値、high: 24時間高値、low: 24時間低値、last: 最終取引価格、vol: 24時間出来高、timestamp: タイムスタンプ）。bitbank APIの/ticker レスポンスから取得。
- **BitbankCandlestickData**: 時系列OHLCV（Open/High/Low/Close/Volume）データ。candlestick typeは1min、5min、15min、30min、1hour、4hour、8hour、12hour、1day、1weekをサポート。bitbank APIの/candlestick レスポンスから取得。
- **CurrencyPair**: 暗号資産の通貨ペア識別子（例: "btc_jpy", "xrp_jpy", "eth_btc"）。bitbank APIがサポートする通貨ペア形式（小文字、アンダースコア区切り）に準拠。
- **FinancialSummary**: 投資家向け金融指標分析結果。以下のフィールドを含む：`annualized_return`（年率リターン、複利計算）、`annualized_volatility`（年率ボラティリティ、日次リターンの標準偏差×√365）、`max_drawdown`（最大ドローダウン、running maximum methodで計算）、`sharpe_ratio`（シャープレシオ、リスクフリーレート0.1%使用）、`sortino_ratio`（ソルティーノレシオ、MAR=0）、`return_skewness`（リターン分布の歪度）、`return_kurtosis`（リターン分布の尖度）、`total_return`（期間全体のリターン）、`start_price`（期初価格）、`end_price`（期末価格）、`mean_price`（平均価格）、`total_volume`（総取引量）、`trading_days`（取引日数）。candlestickデータから計算。
- **BitbankAPIClient**: bitbank Public APIへのHTTPリクエストを管理するクライアント。レート制限、リトライロジック、エラーハンドリング、タイムアウト設定を含む。設定はTOMLファイルから読み込み（base_url、timeout_seconds、max_retries、retry_delay_seconds、risk_free_rate）。

## Success Criteria

### Measurable Outcomes

**注**: カスタムエージェント実装の基本的な成功基準（互換性、バリデーション、エラーハンドリング）は親仕様（`specs/009-member/spec.md`）と`specs/018-custom-member/spec.md`で定義されています。

#### bitbank API連携エージェント固有の成功基準

- **SC-001**: エージェントは、指定された通貨ペア（btc_jpy、xrp_jpy）の最新価格情報を3秒以内に取得できる（ネットワーク状態が正常な場合）
- **SC-002**: エージェントは、時系列データ（最大1000件のロウソク足データ）を10秒以内に取得し、金融指標分析を完了できる
- **SC-003**: エージェントは、APIエラー（404、500、タイムアウト、無効なJSON）が発生した場合、100%の確率で構造化エラー情報（metadata）とLLMによる自然言語の原因説明・対処法（content、Markdown形式）をユーザーに返す
- **SC-004**: エージェントは、APIレート制限（HTTP 429）発生時にリトライロジックを実行し、最大3回まで自動的に再試行する
- **SC-005**: エージェントのコアロジック（APIクライアント、データパース、金融指標計算）のテストカバレッジが80%以上を達成する
- **SC-006**: 開発者がサンプルコードを参考にすることで、類似の外部API連携エージェント作成時間が40%短縮される
- **SC-007**: エージェントは、Leader Agentから呼び出された際に100%の互換性を持ち、標準的な応答フォーマット（`MemberAgentResult`）で結果を返す
- **SC-008**: エージェントは、金融指標分析結果に対してLLMが自然言語で解釈したObservationsセクション（リスク調整後パフォーマンス、年率ボラティリティ評価、最大ドローダウンリスク、リターン分布特性を含む）をMarkdown形式で100%の確率で提供する
- **SC-009**: エージェントは、金融指標分析結果（FinancialSummary）の完全な構造化データ（年率リターン、年率ボラティリティ、シャープレシオ、ソルティーノレシオ、最大ドローダウン、歪度、尖度等）を`MemberAgentResult.metadata`にJSON形式で100%の確率で格納し、プログラマティックな後処理を可能にする

## Out of Scope

本仕様では以下を扱いません（親仕様または他の仕様で定義）：

1. **カスタムエージェントの実装要件**: `BaseMemberAgent`抽象基底クラス、TOML設定構造、動的ロード機構（agent_module/path）、CLI実行（`mixseek member`）→ 親仕様（`specs/009-member/spec.md`、`specs/018-custom-member/spec.md`）で定義
2. **実際の取引実行機能**: bitbank Private API（認証付き）による売買注文、ポジション管理、資産管理 → 本サンプルエージェントの範囲外（将来的な拡張として別仕様で定義可能）
3. **本番環境での運用**: Leader Agentオーケストレーション、Round Controller統合、Evaluator連携 → MixSeek-Core Framework（`specs/001-specs/spec.md`）で定義
4. **UI統合**: Mixseek UIからのエージェント実行、UI操作手順 → UI仕様（`specs/014-ui/spec.md`）で定義
5. **実装コード**: Python実装、クラス設計、ファイル構造 → 実装フェーズ（plan.md、tasks.md）で定義
6. **高度な分析機能**: 機械学習による価格予測、テクニカル指標（RSI、MACD、ボリンジャーバンドなど）、バックテスト機能 → 本サンプルエージェントの範囲外（投資家向け金融指標分析のみを含む）

## Assumptions

1. 開発者は、Python中級レベルのスキル（非同期処理、HTTP通信の理解）を持っている
2. 開発者は、親仕様（`specs/009-member/spec.md`、`specs/018-custom-member/spec.md`）で定義された標準Member Agentとカスタムエージェントの概念を理解している
3. MixSeek-Core Frameworkの基本概念（Leader Agent、Member Agent、オーケストレーション）を理解している
4. bitbank Public APIは認証不要であり、開発者が無料で即座にアクセスできる
5. bitbank APIのレート制限は一般的なREST API標準（1秒あたり数リクエスト程度）に従うと仮定する（公式ドキュメントに明示された制限がない場合）
6. サンプルコードは、プロジェクトライセンス（Apache License 2.0）に従い、開発者が利用・変更できる
7. エージェントは、bitbank APIのレスポンス構造が変更されないことを前提とするが、エラー検出ロジックによりスキーマ変更を検知できる
8. 開発者は、暗号資産取引のリスクを理解しており、本サンプルエージェントを学習目的で使用する（実際の取引判断には使用しない）

## Dependencies

- **親仕様**: `specs/009-member/spec.md` - 標準Member Agentバンドルとカスタムエージェント作成の基本要件
- **親仕様**: `specs/018-custom-member/spec.md` - カスタムメンバーエージェント開発ガイドとサンプルコード仕様
- **MixSeek-Core Framework**: `specs/001-specs/spec.md` - Leader Agent、Member Agent、オーケストレーションの基本概念
- **bitbank Public API**: https://github.com/bitbankinc/bitbank-api-docs - 外部APIサービス（ticker、candlestickエンドポイント）
- **Constitution**: `.specify/memory/constitution.md` - Article 3（Test-First Imperative）、Article 8（Code Quality Standards）、Article 9（Data Accuracy Mandate）、Article 16（Type Safety）

## Related Specifications

- **親仕様**: `specs/018-custom-member/spec.md` - カスタムメンバーエージェント開発ガイド（本仕様の親仕様）
- **親仕様**: `specs/009-member/spec.md` - 標準Member Agentバンドルとカスタムエージェント基本要件
- **MixSeek-Core Framework**: `specs/001-specs/spec.md` - フレームワーク全体のアーキテクチャと概念
- **UI仕様**: `specs/014-ui/spec.md` - Mixseek UIとの統合（将来的な拡張として参照可能）

## Clarifications

### Session 2025-11-20

- Q: 使用する外部APIサービスは？ → A: bitbank Public API（https://github.com/bitbankinc/bitbank-api-docs）
- Q: ユースケースの具体例は？ → A: 時系列データ分析（価格推移、出来高推移、統計的トレンド分析）
- Q: サポートする通貨ペアは？ → A: btc_jpy、xrp_jpyを主要ターゲットとし、他のbitbankサポート通貨ペアも対応可能
- Q: 認証が必要な機能（売買注文など）は含むか？ → A: 含まない。Public API（認証不要）のみを使用し、データ取得・分析に特化
- Q: テストカバレッジ目標（SC-005: 80%以上）の測定対象は？ → A: カスタムエージェントのコアロジック（APIクライアント、データパース、金融指標計算ロジック）のみ
- Q: APIレート制限のリトライ回数は？ → A: 最大3回まで自動再試行（エクスポネンシャルバックオフ適用）
- Q: LLMによる自然言語分析の範囲は？ → A: LLMが金融指標を自然言語で解釈し、リスク調整後パフォーマンス、ドローダウンリスク評価、リターン分布特性をMarkdown形式で提供する
- Q: エラーメッセージの形式は？ → A: 構造化エラー（MemberAgentResult.metadataにerror_code/error_message/timestamp）+ LLMによる自然言語の原因説明・対処法・推奨アクション（MemberAgentResult.contentにMarkdown形式）のハイブリッド形式
- Q: MemberAgentResult.metadataに格納する構造化データの範囲は？ → A: 完全な構造化データ（FinancialSummary、エラー情報の全フィールド）をJSON形式でmetadataに格納し、プログラマティックな後処理や分析を可能にする
- Q: 金融指標分析の対象データは？ → A: candlestickデータ（時系列OHLCV）を金融指標分析の対象とし、tickerデータは最新価格の取得のみに使用する
- Q: 複数通貨ペア間の比較機能は必要か？ → A: 不要。異なる通貨ペア間の絶対価格比較は意味がないため、単一通貨ペアの時系列分析に特化する

### Session 2025-11-20 (Financial Metrics)

- Q: FinancialSummaryに含める金融指標の範囲は？ → A: 年率リターン、年率ボラティリティ、最大ドローダウン、シャープレシオ、ソルティーノレシオ、リターン分布（歪度、尖度）を含む
- Q: 年率リターンの計算方法は？ → A: 複利計算 `(1 + daily_mean)^365 - 1` を使用する
- Q: リスクフリーレート（シャープレシオ計算用）の具体的な値は？ → A: 0.001（年率0.1%）をTOML設定で管理する
- Q: 最大ドローダウンの計算方法は？ → A: Running maximum method `(price - running_max) / running_max` を使用する
- Q: ソルティーノレシオ計算時の下方リスク閾値（MAR）は？ → A: 0（ゼロリターン）を使用する
