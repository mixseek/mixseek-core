# Feature Specification: Google ADK検索エージェントサンプル

**Feature Branch**: `134-custom-member-adk`
**Created**: 2025-11-25
**Status**: Draft
**Input**: 「Sample Agent - ADK Research」を specs/018-custom-member から独立仕様に切り出し
**Parent Spec**: `specs/018-custom-member/spec.md`

## User Scenarios & Testing

### User Story 1 - Web検索と情報要約 (Priority: P1)

開発者は、Google ADK（Agent Development Kit）のマルチエージェントシステムとgoogle_searchツールを使用して、Web検索クエリに対する情報収集・分析・要約を実行します。ユーザーからの自然言語クエリに対して、複数のソースから情報を取得し、統合された回答を提供します。

**Why this priority**: Web検索と情報要約は本サンプルエージェントの中核機能であり、他のAIフレームワーク（Google ADK）をMixSeek-Coreに統合するパターンを示すために最も重要です。

**Independent Test**: google_searchツールを内蔵したLlmAgentを呼び出し、検索結果の取得と要約処理が正常に動作することで、Leader Agentとの統合なしに独立してテスト可能です。

**Acceptance Scenarios**:

1. **Given** 開発者がエージェントに「AIエージェントフレームワークの最新トレンド」とプロンプトを送信する、**When** エージェントがgoogle_searchツールで検索を実行する、**Then** 関連する検索結果が取得され、要約が返される
2. **Given** 複数の検索トピック（例: 技術比較）を含むクエリを送信する、**When** エージェントが並列検索を実行する、**Then** 各トピックの結果が統合され、比較分析が返される
3. **Given** 検索結果に対して追加の深掘り質問をする、**When** エージェントが追加検索と分析を実行する、**Then** より詳細な情報と分析が返される
4. **Given** 検索結果を要約する、**When** LLMが検索結果を分析する、**Then** ソース情報を引用した構造化されたMarkdown形式の要約が返される

---

### User Story 2 - Deep Research パイプライン実行 (Priority: P2)

開発者は、Google Cloud公式ブログで紹介されているDeep Research Agentパターンを参考にした並列検索パイプラインを使用して、複数の検索エージェントによる並列情報収集と、その結果を統合する要約エージェントからなるパイプラインを実行します。複雑なリサーチクエリに対して、体系的で包括的な調査結果を提供します。

**Why this priority**: Deep Researchパイプラインは高度な使用パターンを示し、マルチエージェントオーケストレーションの実践例として重要です。基本的な検索機能の次に実装します。

**Independent Test**: ParallelAgentで複数のリサーチエージェントを並列実行し、SequentialAgentで要約エージェントと連携することで、パイプライン全体をテスト可能です。

**Acceptance Scenarios**:

1. **Given** 開発者がリサーチクエリ（例: 「再生可能エネルギーの最新技術動向」）を送信する、**When** パイプラインが複数の観点（技術、市場、規制など）で並列検索を実行する、**Then** 各観点の調査結果が収集される
2. **Given** 並列検索が完了する、**When** 要約エージェントが結果を統合する、**Then** パターン分析、共通テーマ、インサイトを含む構造化レポートが生成される
3. **Given** リサーチ結果にソース引用が必要である、**When** 要約エージェントがレポートを生成する、**Then** 各主張にソースURLが引用される

---

### User Story 3 - テストとデバッグ (Priority: P3)

開発者は、Google ADK検索エージェントの品質を保証するため、単体テスト・統合テスト・エンドツーエンドテストを作成します。Google ADKのモックを使用した単体テスト、実際のGemini APIを使用したE2Eテスト（`@pytest.mark.e2e`）により、エージェントの信頼性を確認します。

**Why this priority**: テストはエージェントの信頼性を保証するために重要ですが、基本実装の後に実施できます。

**Independent Test**: テストスイート自体が実行可能であり、開発者が段階的にテストを追加しながら品質を向上できます。

**Acceptance Scenarios**:

1. **Given** エージェントのコアロジックをテストする、**When** モックを使用した単体テストを実行する、**Then** ADKラッパー、検索結果パース、要約ロジックが正しく動作することを確認できる
2. **Given** 実際のGemini APIを使用する、**When** E2Eテスト（`@pytest.mark.e2e`）を実行する、**Then** 本番環境に近い条件でエージェントの動作を検証できる
3. **Given** API認証エラー、レート制限、ネットワークタイムアウトが発生する、**When** エラーハンドリングをテストする、**Then** 構造化エラー情報（metadata）とLLMによる自然言語の原因説明・対処法（content、Markdown形式）がユーザーに返される
4. **Given** コアロジックのテストカバレッジを測定する、**When** カバレッジレポートを確認する、**Then** 80%以上のカバレッジが達成されている

---

### Edge Cases

- Gemini APIキーが未設定または無効な場合、明確な認証エラーメッセージが表示されるか？
- APIレート制限（Gemini API）に達した場合、リトライロジックとエクスポネンシャルバックオフが正しく機能するか？
- 検索結果が0件の場合、適切なメッセージが返されるか？
- 非常に長いクエリ（トークン制限を超える可能性）が送信された場合、適切にトランケーションまたはエラーが返されるか？
- 並列検索で一部のサブエージェントが失敗した場合、成功した結果のみで部分的なレポートが生成されるか？
- Google検索結果が一時的に利用不可の場合、フォールバック動作が機能するか？

## Requirements

### Functional Requirements

**注**: カスタムエージェントの基本要件（抽象基底クラス、TOML設定、動的ロード機構、CLI実行）は親仕様（`specs/009-member/spec.md`）と`specs/018-custom-member/spec.md`で定義されています。本仕様はGoogle ADK検索エージェント固有の要件に焦点を当てます。

#### Google ADK検索エージェント要件

- **FR-001**: システムは、Google ADK（Agent Development Kit）のLlmAgentとgoogle_searchツールを使用して、Web検索クエリを実行しなければならない
- **FR-002**: システムは、検索結果を取得し、LLMによる要約・分析を`MemberAgentResult.content`にMarkdown形式で提供しなければならない
- **FR-003**: システムは、Deep Research Agentパターンを参考にした並列検索パイプライン（ParallelAgent、SequentialAgent）を実装しなければならない
- **FR-004**: システムは、検索結果のソース情報（URL、タイトル）を構造化データとして`MemberAgentResult.metadata`に格納しなければならない
- **FR-005**: システムは、API認証エラー、レート制限、ネットワークエラー、タイムアウトを適切にハンドリングしなければならない
- **FR-006**: システムは、エラー発生時に構造化エラー情報（error_code、error_message、timestamp）を`MemberAgentResult.metadata`に格納し、LLMが自然言語でエラーの原因・対処法・推奨アクションを解釈した結果を`MemberAgentResult.content`にMarkdown形式で提供しなければならない
- **FR-007**: システムは、Gemini APIキーとモデル設定をTOML設定ファイルまたは環境変数で管理しなければならない（ハードコード禁止）
- **FR-008**: システムは、`BaseMemberAgent`インターフェースに準拠し、TOML設定で`type = "custom"`を使用しなければならない
- **FR-009**: システムは、単体テスト（ADKモック使用）、統合テスト、エンドツーエンドテスト（実際のGemini API使用、`@pytest.mark.e2e`）を提供しなければならない

### Key Entities

**注**: カスタムエージェントの基本エンティティ（`BaseMemberAgent`、`MemberAgentConfig`、`MemberAgentResult`、`Context Parameter`）は親仕様（`specs/009-member/spec.md`）で定義されています。

#### Google ADK検索エージェント固有のエンティティ

- **ADKResearchAgent**: Google ADKのLlmAgentをラップし、BaseMemberAgentインターフェースに準拠するカスタムエージェント。内部でGoogle ADKのマルチエージェントシステムを使用しつつ、MixSeek-Coreの標準応答フォーマットで結果を返す。
- **SearchResult**: Web検索結果の構造化データ（url: ソースURL、title: ページタイトル、snippet: 抜粋テキスト、timestamp: 取得時刻）。google_searchツールのレスポンスから取得。
- **ResearchReport**: Deep Researchパイプラインの出力（summary: 要約テキスト、key_findings: 主要な発見リスト、sources: SearchResultのリスト、patterns: 検出されたパターン、recommendations: 推奨アクション）。
- **ADKAgentConfig**: Google ADK固有の設定（gemini_model: 使用するGeminiモデル名、temperature: 生成温度、max_output_tokens: 最大出力トークン数、search_result_limit: 検索結果の最大件数）。TOMLまたは環境変数から読み込み。

## Success Criteria

### Measurable Outcomes

**注**: カスタムエージェント実装の基本的な成功基準（互換性、バリデーション、エラーハンドリング）は親仕様（`specs/009-member/spec.md`）と`specs/018-custom-member/spec.md`で定義されています。

#### Google ADK検索エージェント固有の成功基準

- **SC-001**: エージェントは、単一のWeb検索クエリに対して10秒以内に要約結果を返すことができる（ネットワーク状態が正常な場合）
- **SC-002**: エージェントは、Deep Researchパイプライン（3つの並列検索エージェント + 要約エージェント）を30秒以内に完了できる
- **SC-003**: エージェントは、APIエラー（認証エラー、レート制限、タイムアウト）が発生した場合、100%の確率で構造化エラー情報（metadata）とLLMによる自然言語の原因説明・対処法（content、Markdown形式）をユーザーに返す
- **SC-004**: エージェントは、検索結果のソース情報（URL、タイトル）を`MemberAgentResult.metadata`に100%の確率で格納し、引用可能にする
- **SC-005**: エージェントのコアロジック（ADKラッパー、検索結果パース、要約ロジック）のテストカバレッジが80%以上を達成する
- **SC-006**: 開発者がサンプルコードを参考にすることで、他のAIフレームワーク統合エージェント作成時間が50%短縮される
- **SC-007**: エージェントは、Leader Agentから呼び出された際に100%の互換性を持ち、標準的な応答フォーマット（`MemberAgentResult`）で結果を返す

## Out of Scope

本仕様では以下を扱いません（親仕様または他の仕様で定義）：

1. **カスタムエージェントの実装要件**: `BaseMemberAgent`抽象基底クラス、TOML設定構造、動的ロード機構（agent_module/path）、CLI実行（`mixseek member`）→ 親仕様（`specs/009-member/spec.md`、`specs/018-custom-member/spec.md`）で定義
2. **Google ADK以外のAIフレームワーク統合**: LangChain、AutoGen、CrewAI等の統合 → 本サンプルエージェントの範囲外（別仕様で定義可能）
3. **本番環境での運用**: Leader Agentオーケストレーション、Round Controller統合、Evaluator連携 → MixSeek-Core Framework（`specs/001-specs/spec.md`）で定義
4. **UI統合**: Mixseek UIからのエージェント実行、UI操作手順 → UI仕様（`specs/014-ui/spec.md`）で定義
5. **実装コード**: Python実装、クラス設計、ファイル構造 → 実装フェーズ（plan.md、tasks.md）で定義。**実装場所は`examples/`ディレクトリ、`src/mixseek/`への変更は行わない**
6. **高度な検索機能**: 特定ドメインに特化した検索（学術論文、ニュース、法律文書など）、リアルタイムモニタリング → 本サンプルエージェントの範囲外

## Assumptions

1. 開発者は、Python中級レベルのスキル（非同期処理、AIライブラリの使用経験）を持っている
2. 開発者は、親仕様（`specs/009-member/spec.md`、`specs/018-custom-member/spec.md`）で定義された標準Member Agentとカスタムエージェントの概念を理解している
3. MixSeek-Core Frameworkの基本概念（Leader Agent、Member Agent、オーケストレーション）を理解している
4. 開発者は、有効なGemini APIキーを所持しており、Google Cloud利用規約に同意している
5. Google ADK（google-adk、最新版を使用）がプロジェクトの依存関係に含まれている。具体的なバージョンはplan時に確定
6. Gemini APIのレート制限は標準的な制限（RPM: 60、TPM: 120,000程度）に従うと仮定する
7. サンプルコードは、プロジェクトライセンス（Apache License 2.0）に従い、開発者が利用・変更できる
8. google_searchツール（Search grounding）はGemini 2.0以降のモデルで使用可能。対応モデル: gemini-2.0-flash、gemini-2.5-flash、gemini-2.5-flash-lite、gemini-2.5-pro、gemini-3-pro-preview。デフォルトはgemini-2.5-flashを推奨（性能とコストのバランス）

## Dependencies

- **親仕様**: `specs/009-member/spec.md` - 標準Member Agentバンドルとカスタムエージェント作成の基本要件
- **親仕様**: `specs/018-custom-member/spec.md` - カスタムメンバーエージェント開発ガイドとサンプルコード仕様
- **MixSeek-Core Framework**: `specs/001-specs/spec.md` - Leader Agent、Member Agent、オーケストレーションの基本概念
- **Google ADK**: google-adk（最新版、plan時に確定）- Agent Development Kit（LlmAgent、ParallelAgent、SequentialAgent、google_search）
- **Gemini API**: Google AI Gemini API - LLMバックエンド（認証キー必要）
- **Constitution**: `.specify/memory/constitution.md` - Article 3（Test-First Imperative）、Article 8（Code Quality Standards）、Article 9（Data Accuracy Mandate）、Article 16（Type Safety）

## Related Specifications

- **親仕様**: `specs/018-custom-member/spec.md` - カスタムメンバーエージェント開発ガイド（本仕様の親仕様）
- **親仕様**: `specs/009-member/spec.md` - 標準Member Agentバンドルとカスタムエージェント基本要件
- **兄弟仕様**: `specs/019-custom-member-api/spec.md` - bitbank API連携サンプルエージェント（外部API連携パターン）
- **MixSeek-Core Framework**: `specs/001-specs/spec.md` - フレームワーク全体のアーキテクチャと概念

## Clarifications

### Session 2025-11-27

- Q: 「Deep Research Agentパターン」という表現は過剰ではないか？ → A: 実装は簡略化された2段階パイプライン（ParallelAgent→Summarizer）であり、ブログ記事のフルパターン（5段階）とは異なる。「Deep Research Agentパターンを参考にした並列検索パイプライン」と表現を修正

### Session 2025-11-25

- Q: Google ADK検索エージェントにおける「Deep Research Agent」とは何ですか？ → A: Google ADKの組み込み機能ではなく、ADKのコンポーネント（LlmAgent、ParallelAgent、SequentialAgent、google_searchツール）を組み合わせて構築するマルチエージェントパターン。Google Cloud公式ブログで紹介されている設計パターンを参照
- Q: 使用するGeminiモデルは？ → A: Search grounding対応の安定版モデル（gemini-2.5-flash、gemini-2.5-pro等）。デフォルトはgemini-2.5-flashを推奨。-exp（experimental）版は不要
- Q: google_search以外のGoogle検索関連ツールは？ → A: enterprise_web_search（Gemini 2+、エンタープライズコンプライアンス対応）、VertexAiSearchTool（Vertex AIデータストア検索）、GoogleSearchRetrieval（グラウンディング）が利用可能
- Q: 実装場所とMixSeek-Core本体への影響は？ → A: `examples/`ディレクトリにサンプルコードとして実装。`src/mixseek/`への変更は行わない

### References

Google ADK検索エージェント実装の参考資料：

- [Build a deep research agent with Google ADK | Google Cloud Blog](https://cloud.google.com/blog/products/ai-machine-learning/build-a-deep-research-agent-with-google-adk) - Deep Research Agentパターンの公式ガイド
- [google/adk-python](https://github.com/google/adk-python) - Google ADK公式リポジトリ
- [Google AI Gemini API - Google Search Grounding](https://ai.google.dev/gemini-api/docs/google-search?hl=ja) - google_searchツールのグラウンディング機能
- [Gemini models](https://ai.google.dev/gemini-api/docs/models) - 利用可能なGeminiモデル一覧とSearch grounding対応状況
