# Feature Specification: Custom Member Agent Development

**Feature Branch**: `018-custom-member`
**Created**: 2025-11-19
**Status**: Draft
**Input**: Custom member agent development guide specification
**Parent Spec**: `specs/009-member/spec.md`

## User Scenarios & Testing

### User Story 1 - Create Custom Agent (Priority: P1)

開発者は、既存の標準Member Agent（plain、web-search、code-exec）では満たせない独自の要件に対応するため、カスタムMember Agentを作成します。作成したエージェントは、標準エージェントと同様にLeader Agentから呼び出され、MixSeek-Coreフレームワークのオーケストレーションに統合されます。

**Why this priority**: カスタムエージェント作成は本機能の中核であり、開発者が独自のビジネスロジックやドメイン知識をMixSeekエコシステムに統合するための基盤となります。

**Independent Test**: 開発者がカスタムエージェントを作成し、開発・テスト用CLIコマンドで独立して実行できることで、Leader Agentとの統合前に動作確認が可能です。

**Acceptance Scenarios**:

1. **Given** 開発者が新しいカスタムエージェントを作成する、**When** 抽象基底クラスを継承し必須メソッドを実装する、**Then** エージェントが標準的な応答フォーマットで結果を返す
2. **Given** カスタムエージェントの設定ファイルを作成する、**When** 必須フィールド（名前、タイプ、説明）を定義する、**Then** 設定が正しく読み込まれエージェントが初期化される
3. **Given** カスタムエージェントが実装される、**When** 開発・テスト用CLIコマンドで実行する、**Then** エージェントが期待通りの応答を返す
4. **Given** カスタムエージェントがLeader Agentから呼び出される、**When** 標準的なインターフェースで実行される、**Then** Leader Agentが応答を受け取りオーケストレーションを継続できる

---

### User Story 2 - Add Custom Tools (Priority: P2)

開発者は、カスタムエージェントに独自のツール（外部API連携、データ処理、特殊な計算など）を追加します。ツールは設定ファイルで管理され、エージェントの実行時に自動的に利用可能になります。

**Why this priority**: カスタムツールの追加により、カスタムエージェントが標準エージェントでは実現できない高度な処理を実行できるようになります。基本的なエージェント作成の次に重要な機能です。

**Independent Test**: 開発者がカスタムツールを作成し、そのツールがエージェント実行時に正しく呼び出されることを、単体テストや統合テストで検証できます。

**Acceptance Scenarios**:

1. **Given** 開発者がカスタムツールを作成する、**When** ツールをエージェントに登録する、**Then** エージェント実行時にツールが利用可能になる
2. **Given** カスタムツールに設定パラメータが必要である、**When** 設定ファイルでパラメータを定義する、**Then** ツールが設定を読み込み正しく動作する
3. **Given** エージェントが複数のカスタムツールを持つ、**When** ユーザープロンプトを送信する、**Then** エージェントが適切なツールを選択し結果を統合する
4. **Given** カスタムツールが外部リソースにアクセスする、**When** ツールが実行される、**Then** エラーが適切にハンドリングされユーザーに通知される

---

### User Story 3 - Test and Debug Custom Agents (Priority: P3)

開発者は、カスタムエージェントの品質を保証するため、包括的なテストスイートを作成します。テストは、単体テスト、統合テスト、エンドツーエンドテストの3層で構成され、エージェントの動作を多角的に検証します。

**Why this priority**: テストはエージェントの信頼性を保証するために不可欠ですが、基本実装とツール追加の後に実施できます。

**Independent Test**: テストスイート自体が実行可能であり、開発者がテストを段階的に追加しながらエージェントの品質を向上できます。

**Acceptance Scenarios**:

1. **Given** カスタムエージェントが実装される、**When** 単体テストを作成する、**Then** エージェントのコアロジック（ツール実装、エージェント実行ロジック）の個々の機能が正しく動作することを確認できる
2. **Given** カスタムツールが統合される、**When** 統合テストを実行する、**Then** ツール連携が正しく機能することを確認できる
3. **Given** エージェントに問題が発生する、**When** エラーメッセージを確認する、**Then** 問題の原因が明確に示され解決策を推測できる
4. **Given** エンドツーエンドテストを実行する、**When** 実際のAPIを使用してテストする、**Then** 本番環境に近い条件でエージェントの動作を検証できる
5. **Given** コアロジックのテストカバレッジを測定する、**When** カバレッジレポートを確認する、**Then** 80%以上のカバレッジが達成されている

---

### User Story 4 - Learn from Examples (Priority: P2)

開発者は、実装のリファレンスとして、実際に動作するサンプルコードにアクセスします。外部API連携エージェント（外部統合パターン）とGoogle ADK検索エージェント（他のAIフレームワーク統合パターン）の2つのサンプルにより、開発者が自分のユースケースに近い例から学べるようにします。

**Why this priority**: サンプルコードは開発時間を大幅に短縮し、ベストプラクティスを示します。基本的なエージェント作成の理解を補完し、カスタムツール追加と同等の優先度です。

**Independent Test**: サンプルコードを参照し、実際に実行して動作を確認できることで、開発者が独立して学習できます。

**Acceptance Scenarios**:

1. **Given** 開発者がカスタムエージェント作成を開始する、**When** サンプルコードを参照する、**Then** 外部API連携エージェントとGoogle ADK検索エージェントの2つの完全な実装例にアクセスできる
2. **Given** サンプルコードを実行する、**When** 必要な設定を行う、**Then** エラーなく動作し期待通りの結果を返す
3. **Given** 開発者が外部API連携のユースケースに関心がある、**When** 外部API連携エージェントのサンプルを確認する、**Then** 外部サービス統合とエラーハンドリングの実装例を学べる
4. **Given** 開発者が他のAIフレームワーク統合に関心がある、**When** Google ADK検索エージェントのサンプルを確認する、**Then** Google ADKなどの他のライブラリを内部的に活用しつつBaseMemberAgentインターフェースに準拠する実装パターンを学べる
5. **Given** サンプルコードが親仕様の標準インターフェースを使用する、**When** 開発者がサンプルを基に独自のエージェントを作成する、**Then** 標準インターフェースへの準拠が保証される

---

### Edge Cases

- カスタムエージェントが実行中にエラーを返した場合、Leader Agentがエラーを適切に処理できるか？
- 設定ファイルに無効な値（負の温度、範囲外のtop_p等）が含まれる場合、バリデーションエラーが発生するか？
- カスタムツールが長時間実行される場合、タイムアウトが正しく機能するか？
- contextパラメータが将来的に拡張された場合、既存のカスタムエージェントが引き続き動作するか？
- TOML設定ファイルに必須フィールドが欠けている場合、明確なエラーメッセージが表示されるか？
- カスタムツールが外部APIのレート制限に達した場合、適切にリトライまたはエラーを返すか？

## Requirements

### Functional Requirements

**注**: カスタムエージェントの基本要件（抽象基底クラス、TOML設定、動的ロード機構、CLI実行）は親仕様（`specs/009-member/spec.md`）で定義されています。本仕様は開発者リソース（サンプルコード、ドキュメント）に焦点を当てます。

#### 開発者リソース要件

- **FR-001**: システムは、外部API連携エージェントとGoogle ADK検索エージェントの2つのサンプルコードを提供しなければならない
- **FR-002**: サンプルコードは、親仕様で定義された標準インターフェース（`BaseMemberAgent`、TOML設定、動的ロード機構）に準拠しなければならない。すべてのサンプルコードのTOML設定では `type = "custom"` を使用し、独自の識別子を `type` フィールドに使用してはならない
- **FR-003**: サンプルコードは、必要な設定を行うことでエラーなく実行可能でなければならない
- **FR-004**: システムは、カスタムエージェント作成のステップバイステップガイド（Markdown形式、`docs/custom-agent-guide.md`）を提供しなければならない。ガイドはクイックスタート（10分で基本エージェント作成）と詳細ガイド（ツール追加、テスト、デバッグ）の2部構成とし、実際のコード例を含む
- **FR-005**: ドキュメントは、カスタムツールの追加方法とベストプラクティスを説明しなければならない
- **FR-006**: ドキュメントは、テストとデバッグの推奨アプローチを説明しなければならない

### Key Entities

**注**: カスタムエージェントの基本エンティティ（`BaseMemberAgent`、`MemberAgentConfig`、`MemberAgentResult`、`Context Parameter`）は親仕様（`specs/009-member/spec.md`）で定義されています。

**カスタムエージェントのタイプ設定規則**: すべてのカスタムエージェントのTOML設定では `type = "custom"` を使用しなければなりません。エージェントの識別は `name` フィールドで行い、独自の識別子（"data_analyst", "code_reviewer"等）を `type` フィールドに使用してはいけません。

#### 開発者リソース固有のエンティティ

- **Sample Agent - API Integration**: 外部API連携に特化したサンプルエージェント（`type = "custom"`）。bitbank API（暗号資産のpublic API）から時系列データを取得し、簡単な分析を行う完全な実装例。外部統合パターン（REST API呼び出し、レスポンス処理、エラーハンドリング）、HTTPクライアント、リトライロジック、レート制限対応、取得データの統計分析を含む。認証不要で開発者がすぐに試せる。
- **Sample Agent - ADK Research**: Google ADK検索エージェント（`type = "custom"`）。Google ADK（Agent Development Kit）のマルチエージェントシステム（LlmAgent、ParallelAgent、SequentialAgent）とgoogle_searchツールを組み合わせ、MixSeek-CoreのBaseMemberAgentインターフェースに準拠する実装パターンを示す完全な実装例。Deep Research Agentパターン（Google Cloud公式ブログ参照）に基づく検索・分析・要約パイプラインを含む。
- **Development Guide**: カスタムエージェント作成のステップバイステップガイド（`docs/custom-agent-guide.md`、Markdown形式）。クイックスタート（10分で基本エージェント作成）と詳細ガイド（ツール追加、テスト、デバッグ）の2部構成。プロジェクト構成、クラス実装、TOML設定（`type = "custom"` の使用を含む）、動的ロード設定、テスト作成の手順を実際のコード例とともに説明。
- **Best Practices Document**: カスタムツール追加、エラーハンドリング、テスト戦略、パフォーマンス最適化の推奨アプローチを説明するドキュメント。

## Success Criteria

### Measurable Outcomes

**注**: カスタムエージェント実装の成功基準（互換性、バリデーション、エラーハンドリング、後方互換性）は親仕様（`specs/009-member/spec.md`）で定義されています。

#### 開発者リソースの成功基準

- **SC-001**: 外部API連携エージェントとGoogle ADK検索エージェントの2つの完全なサンプルコードが利用可能である
- **SC-002**: 開発者がサンプルコードを参考にすることで、独自のエージェント作成時間が50%短縮される
- **SC-003**: Python中級レベルの開発者が、ドキュメントを参照してカスタムエージェント（ツールなし）を30分以内に作成できる
- **SC-004**: 開発者ガイドに従うことで、作成されたカスタムエージェントがLeader Agentからのオーケストレーション呼び出しで100%の互換性を持つ
- **SC-005**: ベストプラクティスドキュメントに従うことで、カスタムエージェントのコアロジックのテストカバレッジが80%以上を達成できる
- **SC-006**: ドキュメントを参照することで、エラー発生時に開発者が問題の原因を3分以内に特定できる

## Out of Scope

本仕様では以下を扱いません（親仕様または他の仕様で定義）：

1. **カスタムエージェントの実装要件**: `BaseMemberAgent`抽象基底クラス、TOML設定構造、動的ロード機構（agent_module/path）、CLI実行（`mixseek member`）→ 親仕様（`specs/009-member/spec.md`）で定義
2. **本番環境での運用**: Leader Agentオーケストレーション、Round Controller統合、Evaluator連携 → MixSeek-Core Framework（`specs/001-specs/spec.md`）で定義
3. **UI統合**: Mixseek UIからのエージェント実行、UI操作手順 → UI仕様（`specs/014-ui/spec.md`）で定義
4. **実装コード**: Python実装、クラス設計、ファイル構造 → 実装フェーズ（plan.md、tasks.md）で定義
5. **詳細なデバッグ手法**: ログレベル設定、デバッガ統合、トレース出力 → 実装ドキュメント（docs/）で定義

## Assumptions

1. 開発者は、Python中級レベルのスキル（非同期処理の理解）とAIエージェントの基本概念（プロンプト、応答、ツール）を理解している
2. 開発者は、親仕様（`specs/009-member/spec.md`）で定義された標準Member Agentの概念と実装要件を理解している
3. MixSeek-Core Frameworkの基本概念（Leader Agent、Member Agent、オーケストレーション）を理解している
4. サンプルコードは、プロジェクトライセンス（Apache License 2.0）に従い、開発者が利用・変更できる
5. 開発者は、カスタムツールによる外部リソースアクセスのセキュリティに責任を持ち、推奨プラクティスに従う
6. 開発者は、ドキュメントを参照しながら自主的に学習・実装できる

## Dependencies

- **親仕様**: `specs/009-member/spec.md` - 標準Member Agentバンドルとカスタムエージェント作成の基本要件
- **MixSeek-Core Framework**: `specs/001-specs/spec.md` - Leader Agent、Member Agent、オーケストレーションの基本概念
- **Constitution**: `.specify/memory/constitution.md` - Article 3（Test-First Imperative）、Article 8（Code Quality Standards）、Article 9（Data Accuracy Mandate）、Article 16（Type Safety）

## Related Specifications

- **親仕様**: `specs/009-member/spec.md` - 本仕様の親仕様（「What」を定義）
- **MixSeek-Core Framework**: `specs/001-specs/spec.md` - フレームワーク全体のアーキテクチャと概念

## Clarifications

### Session 2025-11-19

- Q: サンプルコードのライセンスと配布ポリシーは？ → A: サンプルコードはプロジェクトリポジトリ内のexamplesなどに配置され、プロジェクトライセンス（Apache License, Version 2.0を予定）に従う
- Q: サンプルコードの具体的なユースケースは？ → A: 外部API連携エージェント（bitbank API）+ Google ADK検索エージェント（他のAIフレームワーク統合パターン）
- Q: カスタムツールによる外部リソースアクセスのセキュリティポリシーは？ → A: 開発者の責任でセキュリティを確保し、推奨プラクティスをドキュメントで提供
- Q: テストカバレッジ目標（SC-005: 80%以上）の測定対象は？ → A: カスタムエージェントのコアロジックのみ（ツール実装、エージェント実行ロジック）
- Q: カスタムエージェント作成時間の目標（SC-003: 30分以内）の前提条件は？ → A: Python中級レベルの開発者（非同期処理、AIエージェントの基本概念を理解）
- Q: 親仕様（027）と子仕様（114）のスコープ境界を明確化します。実装要件はどちらに含めるべきですか？ → A: 実装要件（`BaseMemberAgent`、TOML設定、動的ロード機構、CLI実行）は親仕様（027）で定義し、子仕様（114）は開発者リソース（サンプルコード、ドキュメント、ガイド）に焦点を当てる

### Session 2025-11-20

- Q: カスタムメンバーエージェントのTOML設定における `type` フィールドの値をどのように設定すべきですか？ → A: `"custom"` で固定。独自識別子（"data_analyst", "code_reviewer"等）は使用せず、エージェントの識別は `name` フィールドで行う
- Q: サンプルエージェントの種類を明確化します。どのような2つのサンプルを提供すべきですか？ → A: (1) 外部API連携エージェント（bitbank API使用、外部統合パターン）、(2) Google ADK検索エージェント（他のAIフレームワーク統合パターン）
- Q: 外部API連携エージェントが使用する具体的な外部APIサービスは？ → A: bitbank API（暗号資産のpublic API、https://github.com/bitbankinc/bitbank-api-docs）から時系列データを取得し、簡単な分析を行う。認証不要で開発者がすぐに試せる
- Q: Google ADK検索エージェントの具体的な実装パターンは？ → A: Google ADK（Agent Development Kit）などのライブラリを使った検索エージェント。カスタムエージェント内で他のAIフレームワーク・ライブラリを統合しつつ、MixSeek-CoreのBaseMemberAgentインターフェースに準拠する実装パターンを示す
- Q: 開発者ガイド（Development Guide）の提供形式と配置場所は？ → A: Markdown形式のステップバイステップガイドを`docs/custom-agent-guide.md`に配置。クイックスタート（10分で基本エージェント作成）+ 詳細ガイド（ツール追加、テスト、デバッグ）の2部構成とし、実際のコード例を含める

### Session 2025-11-25

- Q: Google ADK検索エージェントにおける「Deep Research Agent」とは何ですか？ → A: Google ADKの組み込み機能ではなく、ADKのコンポーネント（LlmAgent、ParallelAgent、SequentialAgent、google_searchツール）を組み合わせて構築するマルチエージェントパターン。Google Cloud公式ブログで紹介されている設計パターンを参照

### References

Google ADK検索エージェント実装の参考資料：

- [Build a deep research agent with Google ADK | Google Cloud Blog](https://cloud.google.com/blog/products/ai-machine-learning/build-a-deep-research-agent-with-google-adk) - Deep Research Agentパターンの公式ガイド
- [google/adk-python](https://github.com/google/adk-python) - Google ADK公式リポジトリ
- [Google AI Gemini API - Google Search Grounding](https://ai.google.dev/gemini-api/docs/google-search?hl=ja) - google_searchツールのグラウンディング機能
